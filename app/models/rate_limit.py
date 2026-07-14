from enum import StrEnum

from pydantic import BaseModel, Field


class RateLimitStrategy(StrEnum):
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class RateLimitResult(BaseModel):
    strategy: RateLimitStrategy
    allowed: bool
    limit: int
    remaining: int = Field(ge=0)
    retry_after_seconds: int = Field(ge=0)
