from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    data: dict[str, str | int | float | bool] = Field(default_factory=dict)


class Session(BaseModel):
    id: str
    user_id: str
    data: dict[str, str | int | float | bool]
    created_at: datetime
    last_seen_at: datetime
    expires_in_seconds: int = Field(ge=0)
