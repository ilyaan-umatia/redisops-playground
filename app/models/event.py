from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from app.models.job import JobStatus


class JobEventType(StrEnum):
    CREATED = "job.created"
    STARTED = "job.started"
    COMPLETED = "job.completed"
    FAILED = "job.failed"
    RETRYING = "job.retrying"


class JobEvent(BaseModel):
    id: str
    type: JobEventType
    job_id: str
    status: JobStatus
    timestamp: datetime
    detail: dict[str, str | int | float | bool] | None = None


class JobEventList(BaseModel):
    items: list[JobEvent]
    count: int
