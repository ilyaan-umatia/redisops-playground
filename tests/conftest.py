from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.main import app
from app.redis.client import get_redis


@pytest.fixture
async def fake_redis() -> AsyncIterator[fakeredis.aioredis.FakeRedis]:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.aclose()


@pytest.fixture
async def client(fake_redis: fakeredis.aioredis.FakeRedis) -> AsyncIterator[AsyncClient]:
    async def override_redis() -> AsyncIterator[fakeredis.aioredis.FakeRedis]:
        yield fake_redis

    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[get_settings] = lambda: Settings(
        job_ttl_seconds=300,
        cache_demo_delay_seconds=0,
        session_ttl_seconds=1,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()
