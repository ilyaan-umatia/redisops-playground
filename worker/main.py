import json
import logging
import signal
import time
from datetime import UTC, datetime, timedelta

from redis import Redis

from app.config import get_settings
from app.logging import configure_logging
from app.models.event import JobEventType
from app.models.job import JobStatus, JobType
from app.redis.events import activity_event_fields, job_event_fields
from app.redis.keys import job_key, job_lock_key
from worker.processors import PROCESSORS, Processor

logger = logging.getLogger(__name__)
running = True


def stop_worker(_signum: int, _frame: object) -> None:
    global running
    running = False


def transition_job(
    redis: Redis,
    job_id: str,
    event_type: JobEventType,
    status: JobStatus,
    stream_key: str,
    stream_max_length: int,
    activity_stream_key: str,
    activity_max_length: int,
    *,
    detail: dict[str, str | int | float | bool] | None = None,
    leaderboard_key: str | None = None,
    leaderboard_user_id: str | None = None,
    retry_queue_key: str | None = None,
    retry_score: float | None = None,
    dead_letter_key: str | None = None,
    **fields: str | int,
) -> None:
    occurred_at = datetime.now(UTC)
    fields["status"] = status.value
    fields["updated_at"] = occurred_at.isoformat()
    with redis.pipeline(transaction=True) as pipeline:
        pipeline.hset(job_key(job_id), mapping=fields)
        pipeline.xadd(
            stream_key,
            job_event_fields(
                event_type,
                job_id,
                status,
                timestamp=occurred_at,
                detail=detail,
            ),
            maxlen=stream_max_length,
            approximate=True,
        )
        pipeline.xadd(
            activity_stream_key,
            activity_event_fields(
                event_type.value,
                f"Job status changed to {status.value}",
                job_id,
                timestamp=occurred_at,
            ),
            maxlen=activity_max_length,
            approximate=True,
        )
        if leaderboard_key is not None and leaderboard_user_id is not None:
            pipeline.zincrby(leaderboard_key, 1, leaderboard_user_id)
        if retry_queue_key is not None and retry_score is not None:
            pipeline.zadd(retry_queue_key, {job_id: retry_score})
        if dead_letter_key is not None:
            pipeline.lpush(dead_letter_key, job_id)
        pipeline.execute()


def promote_due_retries(
    redis: Redis,
    retry_queue_key: str,
    pending_queue_key: str,
    *,
    now: float | None = None,
    limit: int = 100,
) -> int:
    current_time = now if now is not None else time.time()
    promoted = 0
    for _ in range(limit):
        entries = redis.zpopmin(retry_queue_key, 1)
        if not entries:
            break
        job_id, score = entries[0]
        if score > current_time:
            redis.zadd(retry_queue_key, {job_id: score})
            break
        if redis.exists(job_key(job_id)):
            with redis.pipeline(transaction=True) as pipeline:
                pipeline.hset(
                    job_key(job_id),
                    mapping={
                        "status": JobStatus.QUEUED.value,
                        "next_retry_at": "",
                        "updated_at": datetime.now(UTC).isoformat(),
                    },
                )
                pipeline.lpush(pending_queue_key, job_id)
                pipeline.execute()
            promoted += 1
    return promoted


def process_job(
    redis: Redis,
    job_id: str,
    delay_seconds: float,
    processors: dict[JobType, Processor] | None = None,
    stream_key: str = "events:jobs",
    stream_max_length: int = 1_000,
    activity_stream_key: str = "events:activity",
    activity_max_length: int = 500,
    leaderboard_key: str = "leaderboard:users",
    retry_queue_key: str = "queue:jobs:retry",
    dead_letter_key: str = "queue:jobs:dead-letter",
    retry_backoff_seconds: int = 2,
) -> None:
    key = job_key(job_id)
    if not redis.exists(key):
        logger.warning("job_missing job_id=%s", job_id)
        return

    lock = redis.lock(job_lock_key(job_id), timeout=max(30, int(delay_seconds) + 10))
    if not lock.acquire(blocking=False):
        logger.info("job_already_owned job_id=%s", job_id)
        return

    stored_job: dict[str, str] = {}
    try:
        stored_job = redis.hgetall(key)
        job_type = JobType(stored_job["type"])
        payload = json.loads(stored_job["payload"])
        registry = processors if processors is not None else PROCESSORS
        processor = registry.get(job_type)
        if processor is None:
            raise ValueError(f"No processor registered for job type: {job_type}")

        transition_job(
            redis,
            job_id,
            JobEventType.STARTED,
            JobStatus.PROCESSING,
            stream_key,
            stream_max_length,
            activity_stream_key,
            activity_max_length,
            progress=10,
            result="",
            error="",
        )
        logger.info("job_started job_id=%s", job_id)
        time.sleep(delay_seconds)
        result = processor(payload)
        transition_job(
            redis,
            job_id,
            JobEventType.COMPLETED,
            JobStatus.COMPLETED,
            stream_key,
            stream_max_length,
            activity_stream_key,
            activity_max_length,
            detail=result,
            leaderboard_key=leaderboard_key,
            leaderboard_user_id=stored_job["user_id"],
            progress=100,
            result=json.dumps(result),
        )
        logger.info("job_completed job_id=%s", job_id)
    except Exception as exc:
        retry_count = int(stored_job.get("retry_count", 0)) + 1
        max_retries = int(stored_job.get("max_retries", 0))
        if retry_count <= max_retries:
            backoff = retry_backoff_seconds * (2 ** (retry_count - 1))
            next_retry = datetime.now(UTC) + timedelta(seconds=backoff)
            transition_job(
                redis,
                job_id,
                JobEventType.RETRYING,
                JobStatus.RETRYING,
                stream_key,
                stream_max_length,
                activity_stream_key,
                activity_max_length,
                detail={"error": str(exc), "retry_count": retry_count},
                retry_queue_key=retry_queue_key,
                retry_score=next_retry.timestamp(),
                retry_count=retry_count,
                next_retry_at=next_retry.isoformat(),
                result="",
                error=str(exc),
            )
            logger.warning(
                "job_retry_scheduled job_id=%s retry_count=%s backoff_seconds=%s",
                job_id,
                retry_count,
                backoff,
                exc_info=True,
            )
        else:
            transition_job(
                redis,
                job_id,
                JobEventType.FAILED,
                JobStatus.FAILED,
                stream_key,
                stream_max_length,
                activity_stream_key,
                activity_max_length,
                detail={"error": str(exc), "retry_count": retry_count},
                dead_letter_key=dead_letter_key,
                retry_count=retry_count,
                next_retry_at="",
                result="",
                error=str(exc),
            )
            logger.exception("job_dead_lettered job_id=%s retry_count=%s", job_id, retry_count)
    finally:
        if lock.owned():
            lock.release()


def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    signal.signal(signal.SIGINT, stop_worker)
    signal.signal(signal.SIGTERM, stop_worker)
    logger.info("worker_started queue=%s", settings.job_queue_key)

    while running:
        promote_due_retries(
            redis,
            settings.job_retry_queue_key,
            settings.job_queue_key,
        )
        job_id = redis.brpoplpush(
            settings.job_queue_key,
            settings.job_processing_key,
            timeout=settings.worker_poll_timeout_seconds,
        )
        if job_id is None:
            continue
        try:
            process_job(
                redis,
                job_id,
                settings.worker_job_delay_seconds,
                stream_key=settings.job_events_stream_key,
                stream_max_length=settings.job_events_max_length,
                activity_stream_key=settings.activity_stream_key,
                activity_max_length=settings.activity_max_length,
                leaderboard_key=settings.leaderboard_key,
                retry_queue_key=settings.job_retry_queue_key,
                dead_letter_key=settings.job_dead_letter_key,
                retry_backoff_seconds=settings.job_retry_backoff_seconds,
            )
        finally:
            redis.lrem(settings.job_processing_key, 1, job_id)

    redis.close()
    logger.info("worker_stopped")


if __name__ == "__main__":
    run()
