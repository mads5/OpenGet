from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from enum import Enum


class TimePeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ALL_TIME = "all_time"


class RankingScoreBreakdown(BaseModel):
    dependents_score: float
    download_velocity_score: float
    commit_recency_score: float
    issue_close_rate_score: float
    stars_growth_score: float
    time_decay_factor: float


class RankingResponse(BaseModel):
    id: UUID
    project_id: UUID
    project_name: str
    github_url: str
    rank: int
    total_score: float
    breakdown: RankingScoreBreakdown
    period: TimePeriod
    computed_at: datetime

    model_config = {"from_attributes": True}


class LeaderboardResponse(BaseModel):
    rankings: list[RankingResponse]
    period: TimePeriod
    total: int
    page: int
    per_page: int
    computed_at: datetime | None = None
