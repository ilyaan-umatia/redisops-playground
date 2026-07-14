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
    job_ttl_seconds: int = Field(default=86_400, ge=60)
    worker_poll_timeout_seconds: int = Field(default=5, ge=1, le=60)
    worker_job_delay_seconds: float = Field(default=2, ge=0, le=60)


@lru_cache
def get_settings() -> Settings:
    return Settings()
