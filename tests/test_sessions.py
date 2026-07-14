import asyncio

from httpx import AsyncClient


async def test_create_read_and_delete_session(client: AsyncClient) -> None:
    created = await client.post(
        "/sessions",
        json={"user_id": "session-user", "data": {"theme": "light", "visits": 1}},
    )

    assert created.status_code == 201
    session = created.json()
    assert session["user_id"] == "session-user"
    assert session["data"] == {"theme": "light", "visits": 1}
    assert session["expires_in_seconds"] > 0

    fetched = await client.get(f"/sessions/{session['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == session["id"]

    deleted = await client.delete(f"/sessions/{session['id']}")
    missing = await client.get(f"/sessions/{session['id']}")
    assert deleted.status_code == 204
    assert missing.status_code == 404


async def test_session_expires_after_ttl(client: AsyncClient) -> None:
    created = await client.post("/sessions", json={"user_id": "expiring-user", "data": {}})

    await asyncio.sleep(1.05)
    response = await client.get(f"/sessions/{created.json()['id']}")

    assert response.status_code == 404


async def test_session_id_must_be_uuid(client: AsyncClient) -> None:
    response = await client.get("/sessions/not-a-uuid")

    assert response.status_code == 422
