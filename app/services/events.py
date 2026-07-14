import json
from collections.abc import AsyncIterator

from redis.asyncio import Redis

from app.config import Settings
from app.models.event import JobEvent


class EventService:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def recent(self, limit: int) -> list[JobEvent]:
        records = await self.redis.xrevrange(
            self.settings.job_events_stream_key,
            max="+",
            min="-",
            count=limit,
        )
        return [self._from_redis(event_id, fields) for event_id, fields in records]

    async def stream(self, last_event_id: str = "$") -> AsyncIterator[str]:
        cursor = last_event_id
        while True:
            streams = await self.redis.xread(
                {self.settings.job_events_stream_key: cursor},
                count=20,
                block=15_000,
            )
            if not streams:
                yield ": keep-alive\n\n"
                continue

            for _stream_name, records in streams:
                for event_id, fields in records:
                    cursor = event_id
                    yield self.to_sse(self._from_redis(event_id, fields))

    @staticmethod
    def to_sse(event: JobEvent) -> str:
        payload = json.dumps(event.model_dump(mode="json"), separators=(",", ":"))
        return f"id: {event.id}\nevent: {event.type.value}\ndata: {payload}\n\n"

    @staticmethod
    def _from_redis(event_id: str, fields: dict[str, str]) -> JobEvent:
        data = dict(fields)
        data["id"] = event_id
        data["detail"] = json.loads(data["detail"]) if data.get("detail") else None
        return JobEvent.model_validate(data)
