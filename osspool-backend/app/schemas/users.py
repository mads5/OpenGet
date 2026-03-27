from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class UserResponse(BaseModel):
    id: UUID
    github_id: str
    github_username: str
    avatar_url: str | None = None
    display_name: str | None = None
    email: str | None = None
    stripe_connect_account_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
