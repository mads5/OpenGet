from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class ContributorScoreBreakdown(BaseModel):
    commits_score: float = 0.0
    prs_score: float = 0.0
    lines_score: float = 0.0
    reviews_score: float = 0.0
    issues_score: float = 0.0
    recency_score: float = 0.0


class ContributorResponse(BaseModel):
    id: UUID
    github_username: str
    github_id: str | None = None
    avatar_url: str | None = None
    user_id: UUID | None = None
    total_score: float = 0.0
    repo_count: int = 0
    is_registered: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class ContributorDetailResponse(ContributorResponse):
    repos: list["RepoContributionResponse"] = []


class RepoContributionResponse(BaseModel):
    repo_id: UUID
    repo_full_name: str
    commits: int = 0
    prs_merged: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    reviews: int = 0
    issues_closed: int = 0
    score: float = 0.0
    last_contribution_at: datetime | None = None

    model_config = {"from_attributes": True}


class ContributorListResponse(BaseModel):
    contributors: list[ContributorResponse]
    total: int
    page: int
    per_page: int
