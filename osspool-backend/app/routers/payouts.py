import stripe
from fastapi import APIRouter, HTTPException, Header, Request

from app.core.auth import get_auth_user
from app.schemas.payouts import StripeConnectOnboard, EarningsResponse
from app.services.payout_service import PayoutService
from app.core.supabase import get_supabase_admin

router = APIRouter(prefix="/payouts", tags=["payouts"])


@router.get("/earnings", response_model=EarningsResponse)
async def get_earnings(authorization: str | None = Header(None)):
    user = get_auth_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to view earnings")

    db = get_supabase_admin()
    contributor_result = (
        db.table("contributors")
        .select("id")
        .eq("user_id", user.id)
        .execute()
    )
    if not contributor_result.data:
        return {
            "contributor_id": "00000000-0000-0000-0000-000000000000",
            "total_earned_cents": 0,
            "pending_cents": 0,
            "payouts": [],
        }

    contributor_id = contributor_result.data[0]["id"]
    service = PayoutService()
    return await service.get_contributor_earnings(contributor_id)


@router.post("/stripe-connect")
async def onboard_stripe(body: StripeConnectOnboard):
    service = PayoutService()
    try:
        return await service.onboard_stripe_connect(str(body.user_id), body.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{payout_id}/process")
async def process_single_payout(payout_id: str):
    """Process a single pending payout via Stripe transfer."""
    service = PayoutService()
    try:
        result = await service.process_payout(payout_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    import logging
    logger = logging.getLogger(__name__)

    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    if not sig:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature")

    try:
        from app.core.config import get_settings
        settings = get_settings()
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret or ""
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {e}")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        meta = session.get("metadata", {})
        pool_id = meta.get("pool_id")
        donor_id = meta.get("donor_id")
        message = meta.get("message") or None
        donation_currency = meta.get("currency") or session.get("currency") or "usd"
        amount_cents = session.get("amount_total", 0)

        if pool_id and donor_id and amount_cents > 0:
            try:
                from app.services.pool_service import PoolService
                service = PoolService()
                await service.add_donation(pool_id, donor_id, amount_cents, message, donation_currency)
                logger.info(
                    "Donation recorded: pool=%s donor=%s amount=%d %s",
                    pool_id, donor_id, amount_cents, donation_currency,
                )
            except Exception:
                logger.exception("Failed to record donation from Stripe webhook")

    return {"received": True, "type": event["type"]}
