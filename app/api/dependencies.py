from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.config import Settings, get_settings
from app.redis.client import get_redis
from app.services.events import EventService
from app.services.jobs import JobService

RedisDependency = Annotated[Redis, Depends(get_redis)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_job_service(redis: RedisDependency, settings: SettingsDependency) -> JobService:
    return JobService(redis, settings)


JobServiceDependency = Annotated[JobService, Depends(get_job_service)]


def get_event_service(redis: RedisDependency, settings: SettingsDependency) -> EventService:
    return EventService(redis, settings)


EventServiceDependency = Annotated[EventService, Depends(get_event_service)]
