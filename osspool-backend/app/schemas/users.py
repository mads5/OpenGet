from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class UserResponse(BaseModel):
    id: UUID
    github_id: str
    github_username: str
    avatar_url: str | None
    email: str | None
    stripe_connect_account_id: str | None
    is_maintainer: bool
    created_at: datetime

    model_config = {"from_attributes": True}
