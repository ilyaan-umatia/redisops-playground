from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "RedisOps Playground"
    app_env: str = "development"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    job_queue_key: str = "queue:jobs:pending"
    job_processing_key: str = "queue:jobs:processing"
    job_index_key: str = "jobs:index"
    job_events_stream_key: str = "events:jobs"
    job_events_max_length: int = Field(default=1_000, ge=100, le=100_000)
    fixed_rate_limit: int = Field(default=5, ge=1, le=10_000)
    fixed_rate_window_seconds: int = Field(default=60, ge=1, le=86_400)
    sliding_rate_limit: int = Field(default=5, ge=1, le=10_000)
    sliding_rate_window_seconds: int = Field(default=60, ge=1, le=86_400)
    cache_demo_key: str = "cache:analytics:summary"
    cache_ttl_seconds: int = Field(default=30, ge=1, le=86_400)
    cache_demo_delay_seconds: float = Field(default=0.2, ge=0, le=10)
    session_ttl_seconds: int = Field(default=1_800, ge=1, le=604_800)
    session_rolling_expiration: bool = True
    job_ttl_seconds: int = Field(default=86_400, ge=60)
    worker_poll_timeout_seconds: int = Field(default=5, ge=1, le=60)
    worker_job_delay_seconds: float = Field(default=2, ge=0, le=60)


@lru_cache
def get_settings() -> Settings:
    return Settings()
