from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class PoolResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    total_amount_cents: int = 0
    donor_count: int = 0
    status: str = "active"
    round_start: datetime
    round_end: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class DonationCreate(BaseModel):
    amount_cents: int
    message: str | None = None


class CheckoutRequest(BaseModel):
    amount_cents: int
    currency: str | None = None
    message: str | None = None
    success_url: str
    cancel_url: str


class DonationResponse(BaseModel):
    id: UUID
    pool_id: UUID
    donor_id: UUID
    amount_cents: int
    currency: str = "usd"
    message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UpiQrRequest(BaseModel):
    amount_paisa: int
    message: str | None = None


class PoolDetailResponse(BaseModel):
    pool: PoolResponse
    recent_donations: list[DonationResponse] = []
    repos_count: int = 0
    contributors_count: int = 0
