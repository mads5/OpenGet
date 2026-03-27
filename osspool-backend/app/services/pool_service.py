import math
import logging
from datetime import datetime, timezone, timedelta
from calendar import monthrange
from uuid import UUID

from app.core.supabase import get_supabase_admin

logger = logging.getLogger(__name__)

_APPROX_TO_USD: dict[str, float] = {
    "usd": 1.0,
    "eur": 1.08,
    "gbp": 1.26,
    "inr": 0.012,
    "cad": 0.74,
    "aud": 0.65,
    "jpy": 0.0067,
    "sgd": 0.74,
    "brl": 0.20,
}


def _to_usd_cents(amount_minor: int, currency: str) -> int:
    """Approximate conversion to USD cents for pool totals.
    Stripe settles in the platform's local currency; this gives a
    consistent display unit until proper FX integration is added."""
    rate = _APPROX_TO_USD.get(currency.lower(), 1.0)
    return max(1, round(amount_minor * rate))


def _current_month_bounds() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    _, last_day = monthrange(now.year, now.month)
    end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=0)
    return start.isoformat(), end.isoformat()


class PoolService:
    def __init__(self):
        self.db = get_supabase_admin()

    async def ensure_active_pool(self) -> dict:
        """Return the active pool, creating a new monthly round if none exists."""
        pool = await self.get_active_pool()
        if pool:
            return pool

        round_start, round_end = _current_month_bounds()
        now = datetime.now(timezone.utc)
        month_name = now.strftime("%B %Y")

        result = self.db.table("pool").insert({
            "name": f"{month_name} Open Source Fund",
            "description": f"Monthly donation pool for {month_name}. Payouts distributed weekly.",
            "total_amount_cents": 0,
            "donor_count": 0,
            "status": "active",
            "round_start": round_start,
            "round_end": round_end,
        }).execute()

        if result.data:
            return result.data[0]
        raise ValueError("Failed to create monthly pool")

    async def get_active_pool(self) -> dict | None:
        result = (
            self.db.table("pool")
            .select("*")
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_pool(self, pool_id: UUID) -> dict | None:
        result = (
            self.db.table("pool")
            .select("*")
            .eq("id", str(pool_id))
            .single()
            .execute()
        )
        return result.data

    async def get_pool_detail(self, pool_id: UUID) -> dict:
        pool = await self.get_pool(pool_id)
        if not pool:
            raise ValueError("Pool not found")

        donations_result = (
            self.db.table("donations")
            .select("*")
            .eq("pool_id", str(pool_id))
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )

        repos_count = self.db.table("repos").select("id", count="exact").execute()
        contributors_count = (
            self.db.table("contributors")
            .select("id", count="exact")
            .gt("total_score", 0)
            .execute()
        )

        return {
            "pool": pool,
            "recent_donations": donations_result.data or [],
            "repos_count": repos_count.count or 0,
            "contributors_count": contributors_count.count or 0,
        }

    async def add_donation(
        self,
        pool_id: str,
        donor_id: str,
        amount_cents: int,
        message: str | None = None,
        currency: str = "usd",
    ) -> dict:
        pool = await self.get_pool(UUID(pool_id))
        if not pool:
            raise ValueError("Pool not found")
        if pool["status"] != "active":
            raise ValueError("Pool is not accepting donations")

        normalized_cents = _to_usd_cents(amount_cents, currency)

        donation_data: dict = {
            "pool_id": pool_id,
            "donor_id": donor_id,
            "amount_cents": amount_cents,
            "currency": currency.lower(),
        }
        if message:
            donation_data["message"] = message

        result = self.db.table("donations").insert(donation_data).execute()
        if not result.data:
            raise ValueError("Failed to record donation")

        existing_donors = (
            self.db.table("donations")
            .select("donor_id")
            .eq("pool_id", pool_id)
            .execute()
        )
        unique_donors = len(set(d["donor_id"] for d in (existing_donors.data or [])))

        self.db.table("pool").update({
            "total_amount_cents": pool["total_amount_cents"] + normalized_cents,
            "donor_count": unique_donors,
        }).eq("id", pool_id).execute()

        return result.data[0]

    async def distribute_pool(self, pool_id: UUID) -> list[dict]:
        """
        Two-tier distribution:
        Tier 1: Pool -> Repos based on sqrt(stars) * log2(1 + contributor_count)
        Tier 2: Repo share -> Contributors based on quality scores
        """
        pool = await self.get_pool(pool_id)
        if not pool:
            raise ValueError("Pool not found")

        total_pool_cents = pool["total_amount_cents"]
        if total_pool_cents <= 0:
            raise ValueError("Pool has no funds to distribute")

        repos_result = self.db.table("repos").select("id, stars, contributor_count, full_name").execute()
        repos = repos_result.data or []
        if not repos:
            raise ValueError("No repos listed")

        repo_weights = {}
        for r in repos:
            stars = max(r.get("stars", 0), 1)
            contribs = max(r.get("contributor_count", 0), 1)
            weight = math.sqrt(stars) * math.log2(1 + contribs)
            repo_weights[r["id"]] = weight

        total_weight = sum(repo_weights.values())
        if total_weight <= 0:
            raise ValueError("No valid repos for distribution")

        payouts: dict[str, int] = {}
        distributions = []

        allocated = 0
        sorted_repos = sorted(repo_weights.items(), key=lambda x: x[1], reverse=True)

        for i, (repo_id, weight) in enumerate(sorted_repos):
            if i == len(sorted_repos) - 1:
                repo_allocation = total_pool_cents - allocated
            else:
                repo_allocation = int(total_pool_cents * (weight / total_weight))
            allocated += repo_allocation

            if repo_allocation <= 0:
                continue

            rc_result = (
                self.db.table("repo_contributors")
                .select("contributor_id, score")
                .eq("repo_id", repo_id)
                .gt("score", 0)
                .execute()
            )
            contributors = rc_result.data or []
            if not contributors:
                continue

            total_score = sum(c["score"] for c in contributors)
            if total_score <= 0:
                continue

            sub_allocated = 0
            sorted_contribs = sorted(contributors, key=lambda c: c["score"], reverse=True)

            for j, c in enumerate(sorted_contribs):
                if j == len(sorted_contribs) - 1:
                    amount = repo_allocation - sub_allocated
                else:
                    amount = int(repo_allocation * (c["score"] / total_score))
                sub_allocated += amount

                cid = c["contributor_id"]
                payouts[cid] = payouts.get(cid, 0) + amount

            repo_obj = next((r for r in repos if r["id"] == repo_id), {})
            distributions.append({
                "repo_id": repo_id,
                "repo_name": repo_obj.get("full_name", ""),
                "allocation_cents": repo_allocation,
                "share_pct": round((weight / total_weight) * 100, 2),
                "contributor_count": len(contributors),
            })

        payout_records = []
        for cid, amount in payouts.items():
            if amount <= 0:
                continue
            record = {
                "pool_id": str(pool_id),
                "contributor_id": cid,
                "amount_cents": amount,
                "score_snapshot": 0,
                "status": "pending",
            }
            payout_records.append(record)

        if payout_records:
            for rec in payout_records:
                c_result = (
                    self.db.table("contributors")
                    .select("total_score")
                    .eq("id", rec["contributor_id"])
                    .single()
                    .execute()
                )
                if c_result.data:
                    rec["score_snapshot"] = c_result.data["total_score"]

            self.db.table("payouts").insert(payout_records).execute()

        self.db.table("pool").update({"status": "distributing"}).eq("id", str(pool_id)).execute()

        return distributions
