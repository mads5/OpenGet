import asyncio
import logging

from app.core.supabase import get_supabase_admin
from app.core.stripe_client import ensure_stripe_initialized

logger = logging.getLogger(__name__)


class PayoutService:
    def __init__(self):
        self.db = get_supabase_admin()

    async def get_contributor_earnings(self, contributor_id: str) -> dict:
        payouts_result = (
            self.db.table("payouts")
            .select("*")
            .eq("contributor_id", contributor_id)
            .order("created_at", desc=True)
            .execute()
        )
        payouts = payouts_result.data or []

        total_earned = sum(p["amount_cents"] for p in payouts if p["status"] == "completed")
        pending = sum(p["amount_cents"] for p in payouts if p["status"] in ("pending", "processing"))

        return {
            "contributor_id": contributor_id,
            "total_earned_cents": total_earned,
            "pending_cents": pending,
            "payouts": payouts,
        }

    async def onboard_stripe_connect(self, user_id: str, email: str) -> dict:
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.stripe_secret_key:
            raise ValueError(
                "Stripe is not configured. Ask the admin to add the STRIPE_SECRET_KEY to the backend."
            )

        ensure_stripe_initialized()
        import stripe

        existing = (
            self.db.table("users")
            .select("stripe_connect_account_id")
            .eq("id", user_id)
            .single()
            .execute()
        )
        existing_account_id = (existing.data or {}).get("stripe_connect_account_id")

        if existing_account_id:
            try:
                account_link = await asyncio.to_thread(
                    stripe.AccountLink.create,
                    account=existing_account_id,
                    refresh_url="http://localhost:3000/dashboard?stripe=refresh",
                    return_url="http://localhost:3000/dashboard?stripe=complete",
                    type="account_onboarding",
                )
                return {"account_id": existing_account_id, "onboarding_url": account_link.url}
            except Exception:
                logger.warning("Existing Connect account %s invalid, creating new one", existing_account_id)

        try:
            account = await asyncio.to_thread(
                stripe.Account.create,
                type="express",
                email=email,
                capabilities={"transfers": {"requested": True}},
                metadata={"openget_user_id": user_id},
            )
        except stripe.error.InvalidRequestError as e:
            raise ValueError(f"Cannot create payout account: {e.user_message or e}")

        self.db.table("users").update(
            {"stripe_connect_account_id": account.id}
        ).eq("id", user_id).execute()

        account_link = await asyncio.to_thread(
            stripe.AccountLink.create,
            account=account.id,
            refresh_url="http://localhost:3000/dashboard?stripe=refresh",
            return_url="http://localhost:3000/dashboard?stripe=complete",
            type="account_onboarding",
        )

        return {"account_id": account.id, "onboarding_url": account_link.url}

    async def process_payout(self, payout_id: str) -> dict:
        ensure_stripe_initialized()
        import stripe

        payout_result = (
            self.db.table("payouts")
            .select("*, contributors(user_id)")
            .eq("id", payout_id)
            .single()
            .execute()
        )
        if not payout_result.data:
            raise ValueError("Payout not found")

        payout = payout_result.data
        contributor_info = payout.pop("contributors", {}) or {}
        user_id = contributor_info.get("user_id")

        if not user_id:
            raise ValueError("Contributor not registered -- no user_id linked")

        user_result = (
            self.db.table("users")
            .select("stripe_connect_account_id")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if not user_result.data or not user_result.data.get("stripe_connect_account_id"):
            raise ValueError("User has no Stripe Connect account")

        stripe_account_id = user_result.data["stripe_connect_account_id"]

        self.db.table("payouts").update({"status": "processing"}).eq("id", payout_id).execute()

        try:
            from app.core.config import get_settings
            currency = get_settings().stripe_currency or "usd"
            transfer = await asyncio.to_thread(
                stripe.Transfer.create,
                amount=payout["amount_cents"],
                currency=currency,
                destination=stripe_account_id,
                metadata={"payout_id": payout_id},
            )

            self.db.table("payouts").update({
                "status": "completed",
                "stripe_transfer_id": transfer.id,
                "completed_at": "now()",
            }).eq("id", payout_id).execute()

            return {"status": "completed", "transfer_id": transfer.id}
        except Exception as e:
            self.db.table("payouts").update({"status": "failed"}).eq("id", payout_id).execute()
            raise ValueError(f"Stripe transfer failed: {e}")
