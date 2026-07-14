from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.config import Settings, get_settings
from app.redis.client import get_redis
from app.services.cache import CacheService
from app.services.events import EventService
from app.services.jobs import JobService
from app.services.rate_limit import RateLimitService

RedisDependency = Annotated[Redis, Depends(get_redis)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_job_service(redis: RedisDependency, settings: SettingsDependency) -> JobService:
    return JobService(redis, settings)


JobServiceDependency = Annotated[JobService, Depends(get_job_service)]


def get_event_service(redis: RedisDependency, settings: SettingsDependency) -> EventService:
    return EventService(redis, settings)


EventServiceDependency = Annotated[EventService, Depends(get_event_service)]


def get_rate_limit_service(redis: RedisDependency) -> RateLimitService:
    return RateLimitService(redis)


RateLimitServiceDependency = Annotated[RateLimitService, Depends(get_rate_limit_service)]


def get_cache_service(redis: RedisDependency, settings: SettingsDependency) -> CacheService:
    return CacheService(redis, settings)


CacheServiceDependency = Annotated[CacheService, Depends(get_cache_service)]
