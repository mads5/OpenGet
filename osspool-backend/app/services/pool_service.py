import math
import logging
from datetime import datetime, timezone, timedelta, date
from calendar import monthrange
from uuid import UUID

from app.core.supabase import get_supabase_admin

logger = logging.getLogger(__name__)

PLATFORM_FEE_RATE = 0.01
MIN_PAYOUT_CENTS = 50

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
    rate = _APPROX_TO_USD.get(currency.lower(), 1.0)
    return max(1, round(amount_minor * rate))


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    _, last_day = monthrange(year, month)
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start.isoformat(), end.isoformat()


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


class PoolService:
    def __init__(self):
        self.db = get_supabase_admin()

    # ------------------------------------------------------------------
    # Pool queries
    # ------------------------------------------------------------------

    async def get_active_pool(self) -> dict | None:
        """Return the pool currently being distributed (status='active')."""
        result = (
            self.db.table("pool")
            .select("*")
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_collecting_pool(self) -> dict | None:
        """Return the pool currently accepting donations (status='collecting')."""
        result = (
            self.db.table("pool")
            .select("*")
            .eq("status", "collecting")
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

    # ------------------------------------------------------------------
    # Dual-pool lifecycle
    # ------------------------------------------------------------------

    async def ensure_collecting_pool(self) -> dict:
        """Ensure a 'collecting' pool exists for next month. Create one if not."""
        pool = await self.get_collecting_pool()
        if pool:
            return pool

        now = datetime.now(timezone.utc)
        ny, nm = _next_month(now.year, now.month)
        month_name = datetime(ny, nm, 1).strftime("%B %Y")
        round_start, round_end = _month_bounds(ny, nm)

        result = (
            self.db.table("pool")
            .insert(
                {
                    "name": f"{month_name} Open Source Fund",
                    "description": (
                        f"Monthly donation pool for {month_name}. "
                        "Payouts distributed weekly."
                    ),
                    "total_amount_cents": 0,
                    "donor_count": 0,
                    "status": "collecting",
                    "round_start": round_start,
                    "round_end": round_end,
                    "platform_fee_cents": 0,
                    "daily_budget_cents": 0,
                    "remaining_cents": 0,
                }
            )
            .execute()
        )
        if result.data:
            return result.data[0]
        raise ValueError("Failed to create collecting pool")

    async def ensure_active_pool(self) -> dict:
        """Return the active pool. If none, try to activate a collecting pool
        whose month has arrived, or create one for the current month."""
        pool = await self.get_active_pool()
        if pool:
            return pool

        # Check if there's a collecting pool whose month has started
        now = datetime.now(timezone.utc)
        all_collecting = (
            self.db.table("pool")
            .select("*")
            .eq("status", "collecting")
            .order("round_start", desc=False)
            .execute()
        )
        for p in all_collecting.data or []:
            round_start = datetime.fromisoformat(
                p["round_start"].replace("Z", "+00:00")
            )
            if round_start <= now:
                return await self.activate_pool(UUID(p["id"]))

        # Fallback: create a pool for the current month
        round_start, round_end = _month_bounds(now.year, now.month)
        month_name = now.strftime("%B %Y")
        result = (
            self.db.table("pool")
            .insert(
                {
                    "name": f"{month_name} Open Source Fund",
                    "description": (
                        f"Monthly donation pool for {month_name}. "
                        "Payouts distributed weekly."
                    ),
                    "total_amount_cents": 0,
                    "donor_count": 0,
                    "status": "active",
                    "round_start": round_start,
                    "round_end": round_end,
                    "platform_fee_cents": 0,
                    "daily_budget_cents": 0,
                    "remaining_cents": 0,
                }
            )
            .execute()
        )
        if result.data:
            return result.data[0]
        raise ValueError("Failed to create active pool")

    async def activate_pool(self, pool_id: UUID) -> dict:
        """Transition a collecting pool to active: deduct 1% fee, compute daily budget."""
        pool = await self.get_pool(pool_id)
        if not pool:
            raise ValueError("Pool not found")

        total = pool["total_amount_cents"]
        fee = int(total * PLATFORM_FEE_RATE)
        effective = total - fee

        round_start = datetime.fromisoformat(
            pool["round_start"].replace("Z", "+00:00")
        )
        _, last_day = monthrange(round_start.year, round_start.month)
        daily_budget = effective // last_day if last_day > 0 else 0

        self.db.table("pool").update(
            {
                "status": "active",
                "platform_fee_cents": fee,
                "daily_budget_cents": daily_budget,
                "remaining_cents": effective,
            }
        ).eq("id", str(pool_id)).execute()

        updated = await self.get_pool(pool_id)
        return updated  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Donations (target the collecting pool)
    # ------------------------------------------------------------------

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
        if pool["status"] not in ("collecting", "active"):
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

        self.db.table("pool").update(
            {
                "total_amount_cents": pool["total_amount_cents"] + normalized_cents,
                "donor_count": unique_donors,
            }
        ).eq("id", pool_id).execute()

        return result.data[0]

    # ------------------------------------------------------------------
    # Weekly distribution
    # ------------------------------------------------------------------

    async def distribute_weekly(self, is_month_end: bool = False) -> list[dict]:
        """Distribute the weekly (or remaining) budget from the active pool.

        Two-tier split:
          Tier 1: pool -> repos by sqrt(repo_score)
          Tier 2: repo share -> contributors by contributor total_score
        """
        pool = await self.get_active_pool()
        if not pool:
            raise ValueError("No active pool to distribute")

        remaining = pool.get("remaining_cents", 0)
        daily_budget = pool.get("daily_budget_cents", 0)

        if remaining <= 0:
            logger.info("Pool %s has no remaining funds", pool["id"])
            return []

        today = date.today()
        if is_month_end:
            budget = remaining
        else:
            budget = min(daily_budget * 7, remaining)

        if budget <= 0:
            return []

        pool_id = UUID(pool["id"])

        # Tier 1: repos weighted by sqrt(repo_score)
        repos_result = (
            self.db.table("repos")
            .select("id, stars, forks, repo_score, full_name, contributor_count")
            .execute()
        )
        repos = repos_result.data or []
        if not repos:
            raise ValueError("No repos listed")

        repo_weights: dict[str, float] = {}
        for r in repos:
            rs = (r.get("stars", 0) or 0) + (r.get("forks", 0) or 0)
            weight = math.sqrt(max(rs, 1))
            repo_weights[r["id"]] = weight

        total_weight = sum(repo_weights.values())
        if total_weight <= 0:
            raise ValueError("No valid repos for distribution")

        payouts: dict[str, int] = {}
        distributions: list[dict] = []

        allocated = 0
        sorted_repos = sorted(repo_weights.items(), key=lambda x: x[1], reverse=True)

        for i, (repo_id, weight) in enumerate(sorted_repos):
            if i == len(sorted_repos) - 1:
                repo_allocation = budget - allocated
            else:
                repo_allocation = int(budget * (weight / total_weight))
            allocated += repo_allocation

            if repo_allocation <= 0:
                continue

            # Tier 2: contributors by total_score
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
            sorted_contribs = sorted(
                contributors, key=lambda c: c["score"], reverse=True
            )

            for j, c in enumerate(sorted_contribs):
                if j == len(sorted_contribs) - 1:
                    amount = repo_allocation - sub_allocated
                else:
                    amount = int(repo_allocation * (c["score"] / total_score))
                sub_allocated += amount

                cid = c["contributor_id"]
                payouts[cid] = payouts.get(cid, 0) + amount

            repo_obj = next((r for r in repos if r["id"] == repo_id), {})
            distributions.append(
                {
                    "repo_id": repo_id,
                    "repo_name": repo_obj.get("full_name", ""),
                    "allocation_cents": repo_allocation,
                    "share_pct": round((weight / total_weight) * 100, 2),
                    "contributor_count": len(contributors),
                }
            )

        # Create payout records (skip below minimum threshold)
        payout_records = []
        actually_distributed = 0
        for cid, amount in payouts.items():
            if amount < MIN_PAYOUT_CENTS:
                continue
            actually_distributed += amount
            c_result = (
                self.db.table("contributors")
                .select("total_score")
                .eq("id", cid)
                .single()
                .execute()
            )
            score_snapshot = (c_result.data or {}).get("total_score", 0)
            payout_records.append(
                {
                    "pool_id": str(pool_id),
                    "contributor_id": cid,
                    "amount_cents": amount,
                    "score_snapshot": score_snapshot,
                    "status": "pending",
                }
            )

        if payout_records:
            self.db.table("payouts").insert(payout_records).execute()

        # Record weekly distribution
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = today
        self.db.table("weekly_distributions").insert(
            {
                "pool_id": str(pool_id),
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "budget_cents": budget,
                "distributed_cents": actually_distributed,
                "is_month_end": is_month_end,
                "status": "distributed",
            }
        ).execute()

        # Deduct from remaining
        new_remaining = max(remaining - budget, 0)
        update_data: dict = {"remaining_cents": new_remaining}
        if is_month_end or new_remaining == 0:
            update_data["status"] = "completed"
            update_data["remaining_cents"] = 0

        self.db.table("pool").update(update_data).eq(
            "id", str(pool_id)
        ).execute()

        return distributions

    # ------------------------------------------------------------------
    # Legacy one-shot distribution (kept for backward compat / manual use)
    # ------------------------------------------------------------------

    async def distribute_pool(self, pool_id: UUID) -> list[dict]:
        """Full one-shot distribution (original behavior)."""
        pool = await self.get_pool(pool_id)
        if not pool:
            raise ValueError("Pool not found")

        total_pool_cents = pool["total_amount_cents"]
        if total_pool_cents <= 0:
            raise ValueError("Pool has no funds to distribute")

        repos_result = (
            self.db.table("repos")
            .select("id, stars, forks, full_name, contributor_count")
            .execute()
        )
        repos = repos_result.data or []
        if not repos:
            raise ValueError("No repos listed")

        repo_weights = {}
        for r in repos:
            rs = (r.get("stars", 0) or 0) + (r.get("forks", 0) or 0)
            weight = math.sqrt(max(rs, 1))
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
            sorted_contribs = sorted(
                contributors, key=lambda c: c["score"], reverse=True
            )

            for j, c in enumerate(sorted_contribs):
                if j == len(sorted_contribs) - 1:
                    amount = repo_allocation - sub_allocated
                else:
                    amount = int(repo_allocation * (c["score"] / total_score))
                sub_allocated += amount

                cid = c["contributor_id"]
                payouts[cid] = payouts.get(cid, 0) + amount

            repo_obj = next((r for r in repos if r["id"] == repo_id), {})
            distributions.append(
                {
                    "repo_id": repo_id,
                    "repo_name": repo_obj.get("full_name", ""),
                    "allocation_cents": repo_allocation,
                    "share_pct": round((weight / total_weight) * 100, 2),
                    "contributor_count": len(contributors),
                }
            )

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

        self.db.table("pool").update({"status": "completed"}).eq(
            "id", str(pool_id)
        ).execute()

        return distributions

    # ------------------------------------------------------------------
    # Month-end finalization
    # ------------------------------------------------------------------

    async def finalize_month(self) -> dict:
        """End-of-month: distribute all remaining funds and activate next month's pool."""
        pool = await self.get_active_pool()
        if not pool:
            return {"status": "no_active_pool"}

        remaining = pool.get("remaining_cents", 0)
        result = {"pool_id": pool["id"], "remaining_before": remaining}

        if remaining > 0:
            distributions = await self.distribute_weekly(is_month_end=True)
            result["distributions"] = distributions

        # Ensure the pool is marked completed
        self.db.table("pool").update(
            {"status": "completed", "remaining_cents": 0}
        ).eq("id", pool["id"]).execute()

        # Activate next month's collecting pool if it exists
        collecting = await self.get_collecting_pool()
        if collecting:
            now = datetime.now(timezone.utc)
            round_start = datetime.fromisoformat(
                collecting["round_start"].replace("Z", "+00:00")
            )
            if round_start.year == now.year and round_start.month == now.month + 1:
                pass  # Will be activated when its month arrives
            elif round_start <= now + timedelta(days=1):
                await self.activate_pool(UUID(collecting["id"]))

        # Ensure a collecting pool exists for the month after next
        await self.ensure_collecting_pool()

        result["status"] = "finalized"
        return result
