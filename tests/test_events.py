import json
from datetime import UTC, datetime

import fakeredis.aioredis
from httpx import AsyncClient

from app.models.event import JobEvent, JobEventType
from app.models.job import JobStatus
from app.services.events import EventService


async def test_job_creation_emits_recent_event(client: AsyncClient) -> None:
    created = await client.post("/jobs", json={"user_id": "event-learner", "payload": {}})

    response = await client.get("/events")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["type"] == "job.created"
    assert body["items"][0]["job_id"] == created.json()["id"]
    assert body["items"][0]["status"] == "queued"


async def test_metrics_report_queue_and_event_depth(
    client: AsyncClient,
    fake_redis: fakeredis.aioredis.FakeRedis,
) -> None:
    await client.post("/jobs", json={"user_id": "metrics-learner", "payload": {}})
    await fake_redis.lpush("queue:jobs:processing", "in-flight-job")

    response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.json() == {
        "pending_jobs": 1,
        "processing_jobs": 1,
        "recorded_events": 1,
    }


def test_sse_message_contains_resume_id_and_json_payload() -> None:
    event = JobEvent(
        id="123-0",
        type=JobEventType.COMPLETED,
        job_id="demo-job",
        status=JobStatus.COMPLETED,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        detail={"records_processed": 100},
    )

    message = EventService.to_sse(event)
    lines = message.strip().splitlines()

    assert lines[0] == "id: 123-0"
    assert lines[1] == "event: job.completed"
    assert json.loads(lines[2].removeprefix("data: "))["job_id"] == "demo-job"
