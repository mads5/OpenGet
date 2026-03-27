import asyncio
import logging
from uuid import UUID
from datetime import datetime, timezone

import stripe

from app.core.supabase import get_supabase_admin
from app.core.stripe_client import ensure_stripe_initialized

logger = logging.getLogger(__name__)


class PayoutService:
    def __init__(self):
        self.db = get_supabase_admin()
        ensure_stripe_initialized()

    async def create_connect_account(self, user_id: UUID, email: str) -> dict:
        account = await asyncio.to_thread(
            stripe.Account.create,
            type="express",
            email=email,
            capabilities={"transfers": {"requested": True}},
            metadata={"user_id": str(user_id)},
        )

        self.db.table("users").update({
            "stripe_connect_account_id": account.id,
        }).eq("id", str(user_id)).execute()

        return {"account_id": account.id}

    async def create_onboarding_link(
        self, account_id: str, return_url: str, refresh_url: str
    ) -> str:
        link = await asyncio.to_thread(
            stripe.AccountLink.create,
            account=account_id,
            return_url=return_url,
            refresh_url=refresh_url,
            type="account_onboarding",
        )
        return link.url

    async def process_payout(self, payout_data: dict) -> dict:
        project = (
            self.db.table("projects")
            .select("*, project_owners(user_id)")
            .eq("id", payout_data["project_id"])
            .single()
            .execute()
        )

        if not project.data:
            raise ValueError("Project not found")

        owners = project.data.get("project_owners") or []
        if not owners:
            raise ValueError("Project has no registered owners for payout")

        owner_id = owners[0]["user_id"]
        owner = self.db.table("users").select("*").eq("id", owner_id).single().execute()

        if not owner.data or not owner.data.get("stripe_connect_account_id"):
            raise ValueError("Project owner has no Stripe Connect account")

        connect_account_id = owner.data["stripe_connect_account_id"]

        try:
            transfer = await asyncio.to_thread(
                stripe.Transfer.create,
                amount=payout_data["total_payout_cents"],
                currency="usd",
                destination=connect_account_id,
                metadata={
                    "pool_id": payout_data["pool_id"],
                    "project_id": payout_data["project_id"],
                },
            )

            payout_record = {
                "pool_id": payout_data["pool_id"],
                "project_id": payout_data["project_id"],
                "recipient_id": owner_id,
                "amount_cents": payout_data["amount_cents"],
                "matched_amount_cents": payout_data["matched_amount_cents"],
                "total_payout_cents": payout_data["total_payout_cents"],
                "status": "completed",
                "stripe_transfer_id": transfer.id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

            result = self.db.table("payouts").insert(payout_record).execute()
            if not result.data:
                raise ValueError("Failed to record payout")
            return result.data[0]

        except stripe.StripeError as e:
            logger.error(f"Stripe transfer failed: {e}")
            payout_record = {
                "pool_id": payout_data["pool_id"],
                "project_id": payout_data["project_id"],
                "recipient_id": owner_id,
                "amount_cents": payout_data["amount_cents"],
                "matched_amount_cents": payout_data.get("matched_amount_cents", 0),
                "total_payout_cents": payout_data["total_payout_cents"],
                "status": "failed",
                "stripe_transfer_id": None,
            }
            self.db.table("payouts").insert(payout_record).execute()
            raise

    async def process_pool_payouts(self, pool_id: UUID, distributions: list[dict]) -> list[dict]:
        results = []
        has_failure = False
        for dist in distributions:
            try:
                result = await self.process_payout(dist)
                results.append(result)
            except Exception as e:
                has_failure = True
                logger.error(f"Failed payout for project {dist['project_id']}: {e}")
                results.append({"project_id": dist["project_id"], "status": "failed", "error": str(e)})

        final_status = "completed" if not has_failure else "distributing"
        self.db.table("money_pools").update({"status": final_status}).eq("id", str(pool_id)).execute()
        return results

    async def get_maintainer_earnings(self, user_id: UUID) -> dict:
        result = (
            self.db.table("payouts")
            .select("*")
            .eq("recipient_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )

        payouts = result.data or []
        total = sum(p["total_payout_cents"] for p in payouts if p["status"] == "completed")
        pending = sum(p["total_payout_cents"] for p in payouts if p["status"] == "pending")

        return {
            "user_id": str(user_id),
            "total_earned_cents": total,
            "pending_cents": pending,
            "payouts": payouts,
        }
