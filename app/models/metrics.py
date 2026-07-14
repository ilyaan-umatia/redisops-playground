from pydantic import BaseModel


class QueueMetrics(BaseModel):
    pending_jobs: int
    processing_jobs: int
    recorded_events: int
    cache_hits: int
    cache_misses: int
    retrying_jobs: int
    dead_letter_jobs: int
