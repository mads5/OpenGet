from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from enum import Enum


class PayoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PayoutCreate(BaseModel):
    pool_id: UUID
    project_id: UUID
    amount_cents: int
    stripe_connect_account_id: str


class PayoutResponse(BaseModel):
    id: UUID
    pool_id: UUID
    project_id: UUID
    recipient_id: UUID
    amount_cents: int
    matched_amount_cents: int
    total_payout_cents: int
    status: PayoutStatus
    stripe_transfer_id: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class MaintainerEarnings(BaseModel):
    user_id: UUID
    total_earned_cents: int
    pending_cents: int
    payouts: list[PayoutResponse]


class StripeConnectOnboard(BaseModel):
    user_id: UUID
    email: str
    return_url: str
    refresh_url: str


class StripeConnectOnboardResponse(BaseModel):
    onboarding_url: str
    account_id: str
