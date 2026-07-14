import json
import logging
import signal
import time
from datetime import UTC, datetime

from redis import Redis

from app.config import get_settings
from app.logging import configure_logging
from app.models.event import JobEventType
from app.models.job import JobStatus, JobType
from app.redis.events import job_event_fields
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
    *,
    detail: dict[str, str | int | float | bool] | None = None,
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
        pipeline.execute()


def process_job(
    redis: Redis,
    job_id: str,
    delay_seconds: float,
    processors: dict[JobType, Processor] | None = None,
    stream_key: str = "events:jobs",
    stream_max_length: int = 1_000,
) -> None:
    key = job_key(job_id)
    if not redis.exists(key):
        logger.warning("job_missing job_id=%s", job_id)
        return

    lock = redis.lock(job_lock_key(job_id), timeout=max(30, int(delay_seconds) + 10))
    if not lock.acquire(blocking=False):
        logger.info("job_already_owned job_id=%s", job_id)
        return

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
            detail=result,
            progress=100,
            result=json.dumps(result),
        )
        logger.info("job_completed job_id=%s", job_id)
    except Exception as exc:
        transition_job(
            redis,
            job_id,
            JobEventType.FAILED,
            JobStatus.FAILED,
            stream_key,
            stream_max_length,
            detail={"error": str(exc)},
            result="",
            error=str(exc),
        )
        logger.exception("job_failed job_id=%s", job_id)
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
            )
        finally:
            redis.lrem(settings.job_processing_key, 1, job_id)

    redis.close()
    logger.info("worker_stopped")


if __name__ == "__main__":
    run()
