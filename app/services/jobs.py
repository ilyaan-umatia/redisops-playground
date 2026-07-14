import json
from datetime import UTC, datetime
from uuid import uuid4

from redis.asyncio import Redis

from app.config import Settings
from app.models.event import JobEventType
from app.models.job import Job, JobCreate, JobStatus
from app.redis.events import job_event_fields
from app.redis.keys import job_key


class JobNotFoundError(Exception):
    pass


class JobService:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def create(self, request: JobCreate) -> Job:
        now = datetime.now(UTC)
        job = Job(
            id=str(uuid4()),
            type=request.type,
            user_id=request.user_id,
            status=JobStatus.QUEUED,
            payload=request.payload,
            progress=0,
            created_at=now,
            updated_at=now,
        )
        key = job_key(job.id)

        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.hset(key, mapping=self._to_redis(job))
            pipeline.expire(key, self.settings.job_ttl_seconds)
            pipeline.zadd(self.settings.job_index_key, {job.id: now.timestamp()})
            pipeline.lpush(self.settings.job_queue_key, job.id)
            pipeline.xadd(
                self.settings.job_events_stream_key,
                job_event_fields(JobEventType.CREATED, job.id, JobStatus.QUEUED, timestamp=now),
                maxlen=self.settings.job_events_max_length,
                approximate=True,
            )
            await pipeline.execute()
        return job

    async def list_recent(self, limit: int) -> list[Job]:
        job_ids = await self.redis.zrevrange(self.settings.job_index_key, 0, limit - 1)
        if not job_ids:
            return []

        async with self.redis.pipeline(transaction=False) as pipeline:
            for job_id in job_ids:
                pipeline.hgetall(job_key(job_id))
            stored_jobs = await pipeline.execute()

        jobs = [self._from_redis(data) for data in stored_jobs if data]
        stale_ids = [job_id for job_id, data in zip(job_ids, stored_jobs, strict=True) if not data]
        if stale_ids:
            await self.redis.zrem(self.settings.job_index_key, *stale_ids)
        return jobs

    async def get(self, job_id: str) -> Job:
        data = await self.redis.hgetall(job_key(job_id))
        if not data:
            raise JobNotFoundError(job_id)
        return self._from_redis(data)

    @staticmethod
    def _to_redis(job: Job) -> dict[str, str]:
        data = job.model_dump(mode="json")
        data["payload"] = json.dumps(data["payload"])
        data["result"] = json.dumps(data["result"]) if data["result"] is not None else ""
        data["error"] = data["error"] or ""
        return {key: str(value) for key, value in data.items()}

    @staticmethod
    def _from_redis(data: dict[str, str]) -> Job:
        normalized = dict(data)
        normalized["payload"] = json.loads(normalized["payload"])
        normalized["result"] = json.loads(normalized["result"]) if normalized["result"] else None
        normalized["error"] = normalized["error"] or None
        normalized["progress"] = int(normalized["progress"])
        return Job.model_validate(normalized)
