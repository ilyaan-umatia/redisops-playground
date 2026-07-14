import fakeredis.aioredis
from httpx import AsyncClient


async def test_create_and_read_job(
    client: AsyncClient, fake_redis: fakeredis.aioredis.FakeRedis
) -> None:
    created = await client.post(
        "/jobs",
        json={"type": "report_generation", "user_id": "learner-1", "payload": {"month": 7}},
    )

    assert created.status_code == 202
    job = created.json()
    assert job["status"] == "queued"
    assert job["progress"] == 0
    assert await fake_redis.lrange("queue:jobs:pending", 0, -1) == [job["id"]]
    assert await fake_redis.ttl(f"job:{job['id']}") > 0

    fetched = await client.get(f"/jobs/{job['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == job


async def test_get_unknown_job_returns_404(client: AsyncClient) -> None:
    response = await client.get("/jobs/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


async def test_list_jobs_returns_newest_first(client: AsyncClient) -> None:
    first = await client.post("/jobs", json={"user_id": "learner-1", "payload": {}})
    second = await client.post("/jobs", json={"user_id": "learner-2", "payload": {}})

    response = await client.get("/jobs", params={"limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["id"] == second.json()["id"]
    assert body["items"][0]["id"] != first.json()["id"]


async def test_create_job_validates_user_id(client: AsyncClient) -> None:
    response = await client.post(
        "/jobs",
        json={"type": "report_generation", "user_id": "not allowed!", "payload": {}},
    )

    assert response.status_code == 422


async def test_failed_job_can_be_manually_retried(
    client: AsyncClient, fake_redis: fakeredis.aioredis.FakeRedis
) -> None:
    created = await client.post(
        "/jobs",
        json={"user_id": "retry-user", "payload": {}, "max_retries": 0},
    )
    job_id = created.json()["id"]
    await fake_redis.hset(f"job:{job_id}", mapping={"status": "failed", "error": "boom"})
    await fake_redis.lpush("queue:jobs:dead-letter", job_id)

    response = await client.post(f"/jobs/{job_id}/retry")

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["retry_count"] == 0
    assert await fake_redis.lrange("queue:jobs:dead-letter", 0, -1) == []


async def test_queued_job_cannot_be_manually_retried(client: AsyncClient) -> None:
    created = await client.post("/jobs", json={"user_id": "queued-user", "payload": {}})

    response = await client.post(f"/jobs/{created.json()['id']}/retry")

    assert response.status_code == 409


async def test_dead_letter_endpoint_lists_failed_jobs(
    client: AsyncClient, fake_redis: fakeredis.aioredis.FakeRedis
) -> None:
    created = await client.post(
        "/jobs",
        json={"user_id": "dead-letter-user", "payload": {}, "max_retries": 0},
    )
    job_id = created.json()["id"]
    await fake_redis.hset(f"job:{job_id}", "status", "failed")
    await fake_redis.lpush("queue:jobs:dead-letter", job_id)

    response = await client.get("/jobs/dead-letter")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == job_id
