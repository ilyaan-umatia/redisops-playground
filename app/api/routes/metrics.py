from fastapi import APIRouter

from app.api.dependencies import RedisDependency, SettingsDependency
from app.models.metrics import QueueMetrics

router = APIRouter(tags=["system"])


@router.get("/metrics", response_model=QueueMetrics)
async def queue_metrics(redis: RedisDependency, settings: SettingsDependency) -> QueueMetrics:
    async with redis.pipeline(transaction=False) as pipeline:
        pipeline.llen(settings.job_queue_key)
        pipeline.llen(settings.job_processing_key)
        pipeline.xlen(settings.job_events_stream_key)
        pending, processing, events = await pipeline.execute()
    return QueueMetrics(
        pending_jobs=pending,
        processing_jobs=processing,
        recorded_events=events,
    )
