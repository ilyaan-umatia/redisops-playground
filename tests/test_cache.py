from httpx import AsyncClient


async def test_cache_miss_then_hit_preserves_generated_data(client: AsyncClient) -> None:
    first = await client.get("/cache-demo")
    second = await client.get("/cache-demo")

    assert first.status_code == 200
    assert first.json()["cache_status"] == "miss"
    assert second.json()["cache_status"] == "hit"
    assert second.json()["data"] == first.json()["data"]
    assert second.json()["ttl_seconds"] > 0

    metrics = await client.get("/metrics")
    assert metrics.json()["cache_misses"] == 1
    assert metrics.json()["cache_hits"] == 1


async def test_invalidation_forces_fresh_cache_miss(client: AsyncClient) -> None:
    await client.get("/cache-demo")

    invalidated = await client.post("/cache-demo/invalidate")
    refreshed = await client.get("/cache-demo")

    assert invalidated.status_code == 200
    assert invalidated.json() == {"invalidated": True}
    assert refreshed.json()["cache_status"] == "miss"


async def test_invalidation_reports_when_cache_is_absent(client: AsyncClient) -> None:
    response = await client.post("/cache-demo/invalidate")

    assert response.json() == {"invalidated": False}
