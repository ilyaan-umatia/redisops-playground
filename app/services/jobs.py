import json
from datetime import UTC, datetime
from uuid import uuid4

from redis.asyncio import Redis

from app.config import Settings
from app.models.job import Job, JobCreate, JobStatus
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
            pipeline.lpush(self.settings.job_queue_key, job.id)
            await pipeline.execute()
        return job

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
