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
    RETRYING = "retrying"


class JobCreate(BaseModel):
    type: JobType = JobType.REPORT_GENERATION
    user_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    payload: dict[str, str | int | float | bool] = Field(default_factory=dict)
    max_retries: int = Field(default=3, ge=0, le=10)


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
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    next_retry_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class JobList(BaseModel):
    items: list[Job]
    count: int


class DeadLetterList(BaseModel):
    items: list[Job]
    count: int
