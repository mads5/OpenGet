from fastapi import APIRouter, HTTPException, Request
from uuid import UUID

import stripe

from app.core.config import get_settings
from app.schemas.payouts import (
    MaintainerEarnings,
    StripeConnectOnboard,
    StripeConnectOnboardResponse,
)
from app.services.payout_service import PayoutService

router = APIRouter(prefix="/payouts", tags=["payouts"])


@router.post("/connect/onboard", response_model=StripeConnectOnboardResponse)
async def onboard_maintainer(body: StripeConnectOnboard):
    service = PayoutService()
    account = await service.create_connect_account(body.user_id, body.email)
    url = await service.create_onboarding_link(
        account["account_id"], body.return_url, body.refresh_url
    )
    return {"onboarding_url": url, "account_id": account["account_id"]}


@router.get("/earnings/{user_id}", response_model=MaintainerEarnings)
async def get_earnings(user_id: UUID):
    service = PayoutService()
    return await service.get_maintainer_earnings(user_id)


@router.post("/pools/{pool_id}/process")
async def process_pool_payouts(pool_id: UUID):
    from app.services.pool_service import PoolService

    pool_service = PoolService()
    distributions = await pool_service.distribute_pool(pool_id)

    payout_service = PayoutService()
    results = await payout_service.process_pool_payouts(pool_id, distributions)
    return {"results": results, "count": len(results)}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    settings = get_settings()

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "transfer.failed":
        transfer = event["data"]["object"]
        from app.core.supabase import get_supabase_admin
        db = get_supabase_admin()
        db.table("payouts").update({"status": "failed"}).eq(
            "stripe_transfer_id", transfer["id"]
        ).execute()

    return {"received": True}
