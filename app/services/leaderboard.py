from redis.asyncio import Redis

from app.config import Settings
from app.models.leaderboard import ActivityEvent, LeaderboardEntry


class LeaderboardService:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def top(self, limit: int) -> list[LeaderboardEntry]:
        members = await self.redis.zrevrange(
            self.settings.leaderboard_key,
            0,
            limit - 1,
            withscores=True,
        )
        return [
            LeaderboardEntry(user_id=user_id, score=int(score), rank=index + 1)
            for index, (user_id, score) in enumerate(members)
        ]

    async def rank(self, user_id: str) -> LeaderboardEntry | None:
        async with self.redis.pipeline(transaction=False) as pipeline:
            pipeline.zrevrank(self.settings.leaderboard_key, user_id)
            pipeline.zscore(self.settings.leaderboard_key, user_id)
            rank, score = await pipeline.execute()
        if rank is None or score is None:
            return None
        return LeaderboardEntry(user_id=user_id, score=int(score), rank=int(rank) + 1)

    async def activity(self, limit: int) -> list[ActivityEvent]:
        records = await self.redis.xrevrange(
            self.settings.activity_stream_key,
            max="+",
            min="-",
            count=limit,
        )
        return [ActivityEvent(id=event_id, **fields) for event_id, fields in records]
