from httpx import AsyncClient


async def test_learning_journey_across_core_features(client: AsyncClient) -> None:
    dashboard = await client.get("/")
    job = await client.post(
        "/jobs",
        json={"user_id": "journey-user", "payload": {"record_count": 10}},
    )
    session = await client.post(
        "/sessions",
        json={"user_id": "journey-user", "data": {"lesson": "redis"}},
    )
    cache_miss = await client.get("/cache-demo")
    cache_hit = await client.get("/cache-demo")
    events = await client.get("/events")
    activity = await client.get("/activity")
    metrics = await client.get("/metrics")

    assert dashboard.status_code == 200
    assert "RedisOps Field Console" in dashboard.text
    assert job.status_code == 202
    assert session.status_code == 201
    assert cache_miss.json()["cache_status"] == "miss"
    assert cache_hit.json()["cache_status"] == "hit"
    assert events.json()["items"][0]["job_id"] == job.json()["id"]
    assert activity.json()["items"][0]["reference_id"] == job.json()["id"]
    assert metrics.json()["pending_jobs"] == 1
