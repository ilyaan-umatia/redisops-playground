from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class JobType(StrEnum):
    REPORT_GENERATION = "report_generation"


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreate(BaseModel):
    type: JobType = JobType.REPORT_GENERATION
    user_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    payload: dict[str, str | int | float | bool] = Field(default_factory=dict)


class Job(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: JobType
    user_id: str
    status: JobStatus
    payload: dict[str, str | int | float | bool]
    progress: int = Field(ge=0, le=100)
    result: dict[str, str | int | float | bool] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class JobList(BaseModel):
    items: list[Job]
    count: int
