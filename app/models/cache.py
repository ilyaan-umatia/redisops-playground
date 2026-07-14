from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class CacheStatus(StrEnum):
    HIT = "hit"
    MISS = "miss"


class AnalyticsSummary(BaseModel):
    total_jobs: int
    queued_jobs: int
    generated_at: datetime


class CacheDemoResponse(BaseModel):
    cache_status: CacheStatus
    ttl_seconds: int
    data: AnalyticsSummary


class CacheInvalidationResponse(BaseModel):
    invalidated: bool
