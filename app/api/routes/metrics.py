from fastapi import APIRouter

from app.api.dependencies import RedisDependency, SettingsDependency
from app.models.metrics import QueueMetrics
from app.services.cache import CACHE_HITS_KEY, CACHE_MISSES_KEY

router = APIRouter(tags=["system"])


@router.get("/metrics", response_model=QueueMetrics)
async def queue_metrics(redis: RedisDependency, settings: SettingsDependency) -> QueueMetrics:
    async with redis.pipeline(transaction=False) as pipeline:
        pipeline.llen(settings.job_queue_key)
        pipeline.llen(settings.job_processing_key)
        pipeline.xlen(settings.job_events_stream_key)
        pipeline.get(CACHE_HITS_KEY)
        pipeline.get(CACHE_MISSES_KEY)
        pending, processing, events, hits, misses = await pipeline.execute()
    return QueueMetrics(
        pending_jobs=pending,
        processing_jobs=processing,
        recorded_events=events,
        cache_hits=int(hits or 0),
        cache_misses=int(misses or 0),
    )
