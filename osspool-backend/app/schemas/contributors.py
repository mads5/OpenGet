from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class ContributorScoreBreakdown(BaseModel):
    total_contributions_score: float = 0.0
    prs_raised_score: float = 0.0
    prs_merged_score: float = 0.0
    qualified_repo_count_score: float = 0.0
    merge_ratio_penalty: float = 1.0


class ContributorResponse(BaseModel):
    id: UUID
    github_username: str
    github_id: str | None = None
    avatar_url: str | None = None
    user_id: UUID | None = None
    total_score: float = 0.0
    repo_count: int = 0
    total_contributions: int = 0
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


class MonthlyContributorStatsResponse(BaseModel):
    id: UUID
    contributor_id: UUID
    repo_id: UUID
    month: str
    prs_raised: int = 0
    prs_merged: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
