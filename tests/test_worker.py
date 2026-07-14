import json
from datetime import UTC, datetime
from unittest.mock import Mock

import fakeredis

from app.redis.keys import job_key
from worker.main import process_job


def test_worker_completes_demo_job() -> None:
    redis = fakeredis.FakeRedis(decode_responses=True)
    job_id = "demo-job"
    redis.hset(
        job_key(job_id),
        mapping={
            "id": job_id,
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
    assert stored["status"] == "completed"
    assert stored["progress"] == "100"
    assert json.loads(stored["result"]) == {
        "message": "Demo report generated",
        "records_processed": 100,
    }
    lock.acquire.assert_called_once_with(blocking=False)
    lock.release.assert_called_once_with()
