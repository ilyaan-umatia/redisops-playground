import math
import time
from collections.abc import Callable
from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import WatchError

from app.models.rate_limit import RateLimitResult, RateLimitStrategy


class RateLimitService:
    def __init__(self, redis: Redis, clock: Callable[[], float] = time.time) -> None:
        self.redis = redis
        self.clock = clock

    async def fixed_window(
        self,
        route: str,
        client_id: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        now = self.clock()
        bucket = int(now // window_seconds)
        key = f"rate_limit:fixed:{route}:{client_id}:{bucket}"
        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            pipeline.expire(key, window_seconds * 2)
            count, _ = await pipeline.execute()

        retry_after = max(1, math.ceil(window_seconds - (now % window_seconds)))
        return RateLimitResult(
            strategy=RateLimitStrategy.FIXED_WINDOW,
            allowed=count <= limit,
            limit=limit,
            remaining=max(0, limit - count),
            retry_after_seconds=0 if count <= limit else retry_after,
        )

    async def sliding_window(
        self,
        route: str,
        client_id: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        key = f"rate_limit:sliding:{route}:{client_id}"

        while True:
            now = self.clock()
            cutoff = now - window_seconds
            await self.redis.zremrangebyscore(key, "-inf", cutoff)
            pipeline = self.redis.pipeline(transaction=True)
            try:
                await pipeline.watch(key)
                count = await pipeline.zcard(key)
                if count >= limit:
                    oldest = await pipeline.zrange(key, 0, 0, withscores=True)
                    await pipeline.unwatch()
                    retry_after = self._sliding_retry_after(oldest, now, window_seconds)
                    return RateLimitResult(
                        strategy=RateLimitStrategy.SLIDING_WINDOW,
                        allowed=False,
                        limit=limit,
                        remaining=0,
                        retry_after_seconds=retry_after,
                    )

                pipeline.multi()
                pipeline.zadd(key, {f"{now}:{uuid4()}": now})
                pipeline.expire(key, window_seconds)
                await pipeline.execute()
                return RateLimitResult(
                    strategy=RateLimitStrategy.SLIDING_WINDOW,
                    allowed=True,
                    limit=limit,
                    remaining=limit - count - 1,
                    retry_after_seconds=0,
                )
            except WatchError:
                continue
            finally:
                await pipeline.reset()

    @staticmethod
    def _sliding_retry_after(
        oldest: list[tuple[str, float]],
        now: float,
        window_seconds: int,
    ) -> int:
        if not oldest:
            return 1
        return max(1, math.ceil(oldest[0][1] + window_seconds - now))
