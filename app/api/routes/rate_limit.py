from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from app.api.dependencies import RateLimitServiceDependency, SettingsDependency
from app.models.rate_limit import RateLimitResult

router = APIRouter(prefix="/rate-limit-demo", tags=["rate limiting"])
ClientId = Annotated[
    str,
    Header(alias="X-Client-ID", min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$"),
]


def ensure_allowed(result: RateLimitResult) -> RateLimitResult:
    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(result.retry_after_seconds),
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": "0",
            },
        )
    return result


@router.get("/fixed", response_model=RateLimitResult)
async def fixed_window_demo(
    client_id: ClientId,
    service: RateLimitServiceDependency,
    settings: SettingsDependency,
) -> RateLimitResult:
    result = await service.fixed_window(
        "fixed-demo",
        client_id,
        settings.fixed_rate_limit,
        settings.fixed_rate_window_seconds,
    )
    return ensure_allowed(result)


@router.get("/sliding", response_model=RateLimitResult)
async def sliding_window_demo(
    client_id: ClientId,
    service: RateLimitServiceDependency,
    settings: SettingsDependency,
) -> RateLimitResult:
    result = await service.sliding_window(
        "sliding-demo",
        client_id,
        settings.sliding_rate_limit,
        settings.sliding_rate_window_seconds,
    )
    return ensure_allowed(result)
