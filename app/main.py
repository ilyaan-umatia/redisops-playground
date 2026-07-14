from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.routes import cache, events, health, jobs, leaderboard, metrics, rate_limit, sessions
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
    application.include_router(rate_limit.router)
    application.include_router(cache.router)
    application.include_router(sessions.router)
    application.include_router(leaderboard.router)

    @application.get("/", include_in_schema=False, response_class=FileResponse)
    async def dashboard() -> FileResponse:
        return FileResponse(Path(__file__).parent / "static" / "dashboard.html")

    return application


app = create_app()
