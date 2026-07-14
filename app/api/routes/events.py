from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Header, Query
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from app.api.dependencies import EventServiceDependency, SettingsDependency
from app.config import Settings
from app.models.event import JobEventList
from app.services.events import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=JobEventList)
async def recent_events(
    service: EventServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JobEventList:
    events = await service.recent(limit)
    return JobEventList(items=events, count=len(events))


@router.get("/stream", response_class=StreamingResponse)
async def stream_events(
    settings: SettingsDependency,
    last_event_id: Annotated[
        str | None,
        Header(alias="Last-Event-ID", pattern=r"^(\$|\d+-\d+)$"),
    ] = None,
) -> StreamingResponse:
    return StreamingResponse(
        _stream_with_owned_connection(settings, last_event_id or "$"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_with_owned_connection(
    settings: Settings,
    last_event_id: str,
) -> AsyncIterator[str]:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        async for message in EventService(redis, settings).stream(last_event_id):
            yield message
    finally:
        await redis.aclose()
