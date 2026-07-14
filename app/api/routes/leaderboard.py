from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.api.dependencies import LeaderboardServiceDependency
from app.models.leaderboard import ActivityFeed, Leaderboard, LeaderboardEntry

router = APIRouter(tags=["leaderboard"])
UserId = Annotated[str, Path(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")]


@router.get("/leaderboard", response_model=Leaderboard)
async def top_users(
    service: LeaderboardServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> Leaderboard:
    return Leaderboard(items=await service.top(limit))


@router.get("/leaderboard/{user_id}", response_model=LeaderboardEntry)
async def user_rank(user_id: UserId, service: LeaderboardServiceDependency) -> LeaderboardEntry:
    entry = await service.rank(user_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not ranked")
    return entry


@router.get("/activity", response_model=ActivityFeed)
async def recent_activity(
    service: LeaderboardServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ActivityFeed:
    return ActivityFeed(items=await service.activity(limit))
