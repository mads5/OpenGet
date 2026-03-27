from pydantic import BaseModel, HttpUrl
from datetime import datetime
from uuid import UUID


class ProjectBase(BaseModel):
    github_url: HttpUrl
    name: str
    description: str | None = None
    language: str | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    description: str | None = None
    language: str | None = None
    is_active: bool | None = None


class ProjectResponse(ProjectBase):
    id: UUID
    owner_github_id: str
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    commit_frequency: float = 0.0
    dependents_count: int = 0
    download_count: int = 0
    issue_close_rate: float = 0.0
    stars_growth_rate: int = 0
    last_commit_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int
    page: int
    per_page: int
