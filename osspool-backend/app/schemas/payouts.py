from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class PayoutResponse(BaseModel):
    id: UUID
    pool_id: UUID
    contributor_id: UUID
    amount_cents: int
    score_snapshot: float = 0.0
    status: str = "pending"
    razorpay_transfer_id: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class EarningsResponse(BaseModel):
    contributor_id: UUID
    total_earned_cents: int = 0
    pending_cents: int = 0
    payouts: list[PayoutResponse] = []


class RazorpayOnboard(BaseModel):
    user_id: UUID
    email: str