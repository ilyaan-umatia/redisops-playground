from fastapi import FastAPI

from app.api.routes import events, health, jobs, metrics
from app.config import get_settings
from app.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Learn production Redis patterns through a working job queue.",
    )
    application.include_router(health.router)
    application.include_router(jobs.router)
    application.include_router(events.router)
    application.include_router(metrics.router)
    return application


app = create_app()
