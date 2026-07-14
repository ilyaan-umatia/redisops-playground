import json
from datetime import UTC, datetime
from uuid import uuid4

from redis.asyncio import Redis

from app.config import Settings
from app.models.session import Session, SessionCreate


class SessionNotFoundError(Exception):
    pass


class SessionService:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def create(self, request: SessionCreate) -> Session:
        now = datetime.now(UTC)
        session_id = str(uuid4())
        key = self.key(session_id)
        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.hset(
                key,
                mapping={
                    "id": session_id,
                    "user_id": request.user_id,
                    "data": json.dumps(request.data),
                    "created_at": now.isoformat(),
                    "last_seen_at": now.isoformat(),
                },
            )
            pipeline.expire(key, self.settings.session_ttl_seconds)
            await pipeline.execute()
        return await self.get(session_id)

    async def get(self, session_id: str) -> Session:
        key = self.key(session_id)
        data = await self.redis.hgetall(key)
        if not data:
            raise SessionNotFoundError(session_id)

        now = datetime.now(UTC)
        if self.settings.session_rolling_expiration:
            async with self.redis.pipeline(transaction=True) as pipeline:
                pipeline.hset(key, "last_seen_at", now.isoformat())
                pipeline.expire(key, self.settings.session_ttl_seconds)
                await pipeline.execute()
            data["last_seen_at"] = now.isoformat()

        ttl = max(0, await self.redis.ttl(key))
        return Session(
            id=data["id"],
            user_id=data["user_id"],
            data=json.loads(data["data"]),
            created_at=data["created_at"],
            last_seen_at=data["last_seen_at"],
            expires_in_seconds=ttl,
        )

    async def delete(self, session_id: str) -> None:
        if not await self.redis.delete(self.key(session_id)):
            raise SessionNotFoundError(session_id)

    @staticmethod
    def key(session_id: str) -> str:
        return f"session:{session_id}"
