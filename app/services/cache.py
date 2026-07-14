import asyncio
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.config import Settings
from app.models.cache import AnalyticsSummary, CacheDemoResponse, CacheStatus

CACHE_HITS_KEY = "metrics:cache:hits"
CACHE_MISSES_KEY = "metrics:cache:misses"


class CacheService:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def get_analytics(self) -> CacheDemoResponse:
        cached = await self.redis.get(self.settings.cache_demo_key)
        if cached is not None:
            await self.redis.incr(CACHE_HITS_KEY)
            return CacheDemoResponse(
                cache_status=CacheStatus.HIT,
                ttl_seconds=max(0, await self.redis.ttl(self.settings.cache_demo_key)),
                data=AnalyticsSummary.model_validate_json(cached),
            )

        await asyncio.sleep(self.settings.cache_demo_delay_seconds)
        total_jobs, queued_jobs = await self._analytics_counts()
        summary = AnalyticsSummary(
            total_jobs=total_jobs,
            queued_jobs=queued_jobs,
            generated_at=datetime.now(UTC),
        )
        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.set(
                self.settings.cache_demo_key,
                summary.model_dump_json(),
                ex=self.settings.cache_ttl_seconds,
            )
            pipeline.incr(CACHE_MISSES_KEY)
            await pipeline.execute()
        return CacheDemoResponse(
            cache_status=CacheStatus.MISS,
            ttl_seconds=self.settings.cache_ttl_seconds,
            data=summary,
        )

    async def invalidate(self) -> bool:
        return bool(await self.redis.delete(self.settings.cache_demo_key))

    async def _analytics_counts(self) -> tuple[int, int]:
        async with self.redis.pipeline(transaction=False) as pipeline:
            pipeline.zcard(self.settings.job_index_key)
            pipeline.llen(self.settings.job_queue_key)
            total, queued = await pipeline.execute()
        return int(total), int(queued)
