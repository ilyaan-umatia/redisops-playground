import json
from datetime import UTC, datetime
from unittest.mock import Mock

import fakeredis

from app.models.job import JobType
from app.redis.keys import job_key
from worker.main import process_job, promote_due_retries
from worker.processors.report import generate_report


def test_worker_completes_demo_job() -> None:
    redis = fakeredis.FakeRedis(decode_responses=True)
    job_id = "demo-job"
    redis.hset(
        job_key(job_id),
        mapping={
            "id": job_id,
            "type": "report_generation",
            "user_id": "test-user",
            "payload": json.dumps({"record_count": 25}),
            "status": "queued",
            "progress": "0",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )
    lock = Mock()
    lock.acquire.return_value = True
    lock.owned.return_value = True
    redis.lock = Mock(return_value=lock)
    observed_statuses: list[str] = []

    def observe_processing(
        payload: dict[str, str | int | float | bool],
    ) -> dict[str, str | int | float | bool]:
        observed_statuses.append(redis.hget(job_key(job_id), "status"))
        return generate_report(payload)

    process_job(
        redis,
        job_id,
        delay_seconds=0,
        processors={JobType.REPORT_GENERATION: observe_processing},
    )

    stored = redis.hgetall(job_key(job_id))
    assert stored["status"] == "completed"
    assert stored["progress"] == "100"
    assert json.loads(stored["result"]) == {
        "message": "Demo report generated",
        "records_processed": 25,
    }
    lock.acquire.assert_called_once_with(blocking=False)
    lock.release.assert_called_once_with()
    assert observed_statuses == ["processing"]
    events = redis.xrange("events:jobs")
    assert [fields["type"] for _, fields in events] == ["job.started", "job.completed"]
    assert redis.zscore("leaderboard:users", "test-user") == 1


def test_worker_marks_processor_failure() -> None:
    redis = fakeredis.FakeRedis(decode_responses=True)
    job_id = "failing-job"
    redis.hset(
        job_key(job_id),
        mapping={
            "id": job_id,
            "type": "report_generation",
            "user_id": "failing-user",
            "payload": json.dumps({"force_failure": True}),
            "status": "queued",
            "progress": "0",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )
    lock = Mock()
    lock.acquire.return_value = True
    lock.owned.return_value = True
    redis.lock = Mock(return_value=lock)

    process_job(redis, job_id, delay_seconds=0)

    stored = redis.hgetall(job_key(job_id))
    assert stored["status"] == "failed"
    assert stored["result"] == ""
    assert stored["error"] == "Demo report generation failed"
    events = redis.xrange("events:jobs")
    assert [fields["type"] for _, fields in events] == ["job.started", "job.failed"]
    assert redis.lrange("queue:jobs:dead-letter", 0, -1) == [job_id]


def test_worker_schedules_and_promotes_retry() -> None:
    redis = fakeredis.FakeRedis(decode_responses=True)
    job_id = "retrying-job"
    redis.hset(
        job_key(job_id),
        mapping={
            "id": job_id,
            "type": "report_generation",
            "user_id": "retry-user",
            "payload": json.dumps({"force_failure": True}),
            "status": "queued",
            "progress": "0",
            "retry_count": "0",
            "max_retries": "2",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )
    lock = Mock()
    lock.acquire.return_value = True
    lock.owned.return_value = True
    redis.lock = Mock(return_value=lock)

    process_job(redis, job_id, delay_seconds=0, retry_backoff_seconds=2)

    stored = redis.hgetall(job_key(job_id))
    retry_at = redis.zscore("queue:jobs:retry", job_id)
    assert stored["status"] == "retrying"
    assert stored["retry_count"] == "1"
    assert retry_at is not None

    promoted = promote_due_retries(
        redis,
        "queue:jobs:retry",
        "queue:jobs:pending",
        now=retry_at + 1,
    )
    assert promoted == 1
    assert redis.hget(job_key(job_id), "status") == "queued"
    assert redis.lrange("queue:jobs:pending", 0, -1) == [job_id]


def test_worker_skips_job_when_lock_is_owned() -> None:
    redis = fakeredis.FakeRedis(decode_responses=True)
    redis.hset(job_key("owned-job"), mapping={"status": "processing"})
    lock = Mock()
    lock.acquire.return_value = False
    redis.lock = Mock(return_value=lock)

    process_job(redis, "owned-job", delay_seconds=0)

    assert redis.hget(job_key("owned-job"), "status") == "processing"
    lock.release.assert_not_called()
