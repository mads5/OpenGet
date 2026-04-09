import asyncio
import logging

from fastapi import APIRouter, HTTPException, Header
from uuid import UUID

from fastapi import Request
from app.core.auth import get_auth_user
from app.core.config import get_settings
from app.core.stripe_client import ensure_stripe_initialized
from app.schemas.pools import (
    DonationCreate,
    DonationResponse,
    PoolResponse,
    PoolDetailResponse,
    CheckoutRequest,
    UpiQrRequest,
    WeeklyDistributionResponse,
)
from app.services.pool_service import PoolService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pool", tags=["pool"])


@router.get("", response_model=PoolResponse | None)
async def get_active_pool():
    service = PoolService()
    pool = await service.ensure_active_pool()
    return pool


@router.get("/{pool_id}")
async def get_pool_detail(pool_id: UUID):
    service = PoolService()
    try:
        return await service.get_pool_detail(pool_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/create-checkout-session")
async def create_checkout_session(
    body: CheckoutRequest,
    authorization: str | None = Header(None),
):
    user = get_auth_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to donate")

    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Payment gateway not configured. Please ask the admin to set the Stripe secret key.",
        )

    ensure_stripe_initialized()
    import stripe

    service = PoolService()
    pool = await service.ensure_collecting_pool()

    currency = body.currency or settings.stripe_currency or "usd"

    try:
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": currency,
                    "unit_amount": body.amount_cents,
                    "product_data": {
                        "name": f"Donation to {pool['name']}",
                        "description": "Fund open-source contributors on OpenGet",
                    },
                },
                "quantity": 1,
            }],
            metadata={
                "pool_id": pool["id"],
                "donor_id": user.id,
                "message": body.message or "",
                "currency": currency,
            },
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
    except Exception as e:
        logger.exception("Stripe Checkout session creation failed")
        raise HTTPException(status_code=502, detail=f"Payment gateway error: {e}")

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/donate", response_model=DonationResponse, status_code=201)
async def donate(
    body: DonationCreate,
    authorization: str | None = Header(None),
):
    """Record a donation to the collecting pool (for next month's distribution)."""
    user = get_auth_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to donate")

    service = PoolService()
    pool = await service.ensure_collecting_pool()

    try:
        return await service.add_donation(
            pool["id"], user.id, body.amount_cents, body.message
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-upi-qr")
async def create_upi_qr(
    body: UpiQrRequest,
    authorization: str | None = Header(None),
):
    """Generate a Razorpay UPI QR code for INR donations."""
    user = get_auth_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to donate")

    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=503,
            detail="UPI payments not configured. Ask the admin to set Razorpay keys.",
        )

    service = PoolService()
    pool = await service.ensure_collecting_pool()

    try:
        import razorpay
        import time

        client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

        qr = await asyncio.to_thread(
            client.qrcode.create,
            {
                "type": "upi_qr",
                "name": "OpenGet Donation",
                "usage": "single_use",
                "fixed_amount": True,
                "payment_amount": body.amount_paisa,
                "description": f"Donation to {pool['name']}",
                "close_by": int(time.time()) + 900,
                "notes": {
                    "pool_id": pool["id"],
                    "donor_id": user.id,
                    "message": body.message or "",
                },
            },
        )

        return {
            "qr_id": qr["id"],
            "image_url": qr["image_url"],
            "amount_paisa": body.amount_paisa,
            "status": qr.get("status", "active"),
        }
    except Exception as e:
        logger.exception("Razorpay QR creation failed")
        raise HTTPException(status_code=502, detail=f"UPI QR error: {e}")


@router.post("/razorpay-webhook")
async def razorpay_webhook(request: Request):
    """Handle Razorpay webhook for QR code payments."""
    payload = await request.json()
    event = payload.get("event")

    if event == "qr_code.credited":
        qr_entity = payload.get("payload", {}).get("qr_code", {}).get("entity", {})
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

        notes = qr_entity.get("notes", {})
        pool_id = notes.get("pool_id")
        donor_id = notes.get("donor_id")
        message = notes.get("message") or None
        amount_paisa = payment_entity.get("amount", 0)

        if pool_id and donor_id and amount_paisa > 0:
            try:
                service = PoolService()
                await service.add_donation(pool_id, donor_id, amount_paisa, message, "inr")
                logger.info(
                    "Razorpay UPI donation recorded: pool=%s donor=%s amount=%d paisa",
                    pool_id, donor_id, amount_paisa,
                )
            except Exception:
                logger.exception("Failed to record Razorpay donation")

    return {"received": True, "event": event}


@router.get("/upi-qr-status/{qr_id}")
async def check_upi_qr_status(qr_id: str):
    """Poll the status of a Razorpay QR code payment."""
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="UPI not configured")

    try:
        import razorpay

        client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
        qr = await asyncio.to_thread(client.qrcode.fetch, qr_id)
        payments_count = qr.get("payments_count_received", 0)

        return {
            "qr_id": qr_id,
            "status": qr.get("status"),
            "paid": payments_count > 0,
            "payments_count": payments_count,
            "close_reason": qr.get("close_reason"),
        }
    except Exception as e:
        logger.exception("Failed to check QR status")
        raise HTTPException(status_code=502, detail=f"Could not check status: {e}")


@router.get("/collecting", response_model=PoolResponse | None)
async def get_collecting_pool():
    """Return the pool currently collecting donations for next month."""
    service = PoolService()
    pool = await service.ensure_collecting_pool()
    return pool


@router.post("/{pool_id}/distribute")
async def distribute_pool(pool_id: UUID):
    service = PoolService()
    try:
        distributions = await service.distribute_pool(pool_id)
        return {"distributions": distributions, "count": len(distributions)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{pool_id}/distribute-weekly")
async def distribute_weekly(pool_id: UUID):
    """Trigger a weekly distribution from the active pool."""
    service = PoolService()
    try:
        distributions = await service.distribute_weekly(is_month_end=False)
        return {"distributions": distributions, "count": len(distributions)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{pool_id}/finalize")
async def finalize_pool(pool_id: UUID):
    """End-of-month finalization: distribute remaining and mark completed."""
    service = PoolService()
    try:
        result = await service.finalize_month()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
