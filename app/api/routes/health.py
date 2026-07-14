from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import RedisDependency

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(redis: RedisDependency) -> dict[str, str]:
    try:
        await redis.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is unavailable",
        ) from exc
    return {"status": "ok", "redis": "connected"}
