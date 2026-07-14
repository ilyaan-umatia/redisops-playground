from pydantic import BaseModel


class QueueMetrics(BaseModel):
    pending_jobs: int
    processing_jobs: int
    recorded_events: int
