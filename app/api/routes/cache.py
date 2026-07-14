from fastapi import APIRouter

from app.api.dependencies import CacheServiceDependency
from app.models.cache import CacheDemoResponse, CacheInvalidationResponse

router = APIRouter(prefix="/cache-demo", tags=["caching"])


@router.get("", response_model=CacheDemoResponse)
async def cached_analytics(service: CacheServiceDependency) -> CacheDemoResponse:
    return await service.get_analytics()


@router.post("/invalidate", response_model=CacheInvalidationResponse)
async def invalidate_analytics(service: CacheServiceDependency) -> CacheInvalidationResponse:
    return CacheInvalidationResponse(invalidated=await service.invalidate())
