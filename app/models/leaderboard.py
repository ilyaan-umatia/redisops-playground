from datetime import datetime

from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    user_id: str
    score: int = Field(ge=0)
    rank: int = Field(ge=1)


class Leaderboard(BaseModel):
    items: list[LeaderboardEntry]


class ActivityEvent(BaseModel):
    id: str
    type: str
    message: str
    reference_id: str
    timestamp: datetime


class ActivityFeed(BaseModel):
    items: list[ActivityEvent]
