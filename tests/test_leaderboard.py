import fakeredis.aioredis
from httpx import AsyncClient


async def test_leaderboard_returns_top_users_and_rank(
    client: AsyncClient,
    fake_redis: fakeredis.aioredis.FakeRedis,
) -> None:
    await fake_redis.zadd("leaderboard:users", {"alice": 3, "bob": 7, "carol": 5})

    top = await client.get("/leaderboard", params={"limit": 2})
    rank = await client.get("/leaderboard/alice")

    assert top.status_code == 200
    assert [item["user_id"] for item in top.json()["items"]] == ["bob", "carol"]
    assert rank.json() == {"user_id": "alice", "score": 3, "rank": 3}


async def test_unknown_user_has_no_rank(client: AsyncClient) -> None:
    response = await client.get("/leaderboard/unknown")

    assert response.status_code == 404


async def test_job_submission_appears_in_activity_feed(client: AsyncClient) -> None:
    created = await client.post("/jobs", json={"user_id": "active-user", "payload": {}})

    response = await client.get("/activity")

    assert response.status_code == 200
    event = response.json()["items"][0]
    assert event["type"] == "job.created"
    assert event["reference_id"] == created.json()["id"]
