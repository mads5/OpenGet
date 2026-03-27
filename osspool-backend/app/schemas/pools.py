from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from enum import Enum


class PoolStatus(str, Enum):
    ACTIVE = "active"
    DISTRIBUTING = "distributing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PoolCreate(BaseModel):
    name: str
    description: str | None = None
    target_amount_cents: int
    start_date: datetime
    end_date: datetime
    match_ratio: float = 1.0


class PoolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: PoolStatus | None = None


class DonationCreate(BaseModel):
    project_id: UUID
    amount_cents: int
    stripe_payment_intent_id: str | None = None


class DonationResponse(BaseModel):
    id: UUID
    pool_id: UUID
    project_id: UUID
    donor_id: UUID
    amount_cents: int
    matched_amount_cents: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PoolResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    target_amount_cents: int
    current_amount_cents: int
    matched_pool_cents: int
    status: PoolStatus
    start_date: datetime
    end_date: datetime
    match_ratio: float
    donor_count: int
    project_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PoolListResponse(BaseModel):
    pools: list[PoolResponse]
    total: int
    page: int
    per_page: int


class PoolProgressResponse(BaseModel):
    pool: PoolResponse
    funding_percentage: float
    donations: list[DonationResponse]
