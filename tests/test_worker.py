import json
from datetime import UTC, datetime
from unittest.mock import Mock

import fakeredis

from app.models.job import JobType
from app.redis.keys import job_key
from worker.main import process_job
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
