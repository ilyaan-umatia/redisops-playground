from httpx import AsyncClient


async def test_health_reports_redis_connection(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "redis": "connected"}
