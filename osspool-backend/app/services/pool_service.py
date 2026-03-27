import math
import logging
from uuid import UUID

from app.core.supabase import get_supabase_admin

logger = logging.getLogger(__name__)


class PoolService:
    def __init__(self):
        self.db = get_supabase_admin()

    async def create_pool(self, pool_data: dict) -> dict:
        result = self.db.table("money_pools").insert(pool_data).execute()
        if not result.data:
            raise ValueError("Failed to create pool")
        return result.data[0]

    async def get_pool(self, pool_id: UUID) -> dict | None:
        result = self.db.table("money_pools").select("*").eq("id", str(pool_id)).single().execute()
        return result.data

    async def list_pools(self, status: str | None = None, page: int = 1, per_page: int = 20) -> dict:
        query = self.db.table("money_pools").select("*", count="exact")
        if status:
            query = query.eq("status", status)
        offset = (page - 1) * per_page
        result = query.order("created_at", desc=True).range(offset, offset + per_page - 1).execute()
        return {"pools": result.data or [], "total": result.count or 0, "page": page, "per_page": per_page}

    async def add_donation(self, donation_data: dict) -> dict:
        pool = await self.get_pool(donation_data["pool_id"])
        if not pool:
            raise ValueError("Pool not found")
        if pool["status"] != "active":
            raise ValueError("Pool is not accepting donations")

        matched = self._quadratic_match(donation_data["amount_cents"], pool)
        donation_data["matched_amount_cents"] = matched

        result = self.db.table("donations").insert(donation_data).execute()
        if not result.data:
            raise ValueError("Failed to record donation")

        new_amount = pool["current_amount_cents"] + donation_data["amount_cents"]
        new_matched = pool["matched_pool_cents"] + matched

        is_new_project = not any(
            d["project_id"] == donation_data["project_id"]
            for d in (self.db.table("donations")
                      .select("project_id")
                      .eq("pool_id", str(donation_data["pool_id"]))
                      .neq("id", result.data[0]["id"])
                      .execute().data or [])
        )

        is_new_donor = not any(
            d["donor_id"] == donation_data["donor_id"]
            for d in (self.db.table("donations")
                      .select("donor_id")
                      .eq("pool_id", str(donation_data["pool_id"]))
                      .neq("id", result.data[0]["id"])
                      .execute().data or [])
        )

        update_payload: dict = {
            "current_amount_cents": new_amount,
            "matched_pool_cents": new_matched,
        }
        if is_new_donor:
            update_payload["donor_count"] = pool["donor_count"] + 1
        if is_new_project:
            update_payload["project_count"] = pool["project_count"] + 1

        self.db.table("money_pools").update(update_payload).eq("id", str(donation_data["pool_id"])).execute()

        return result.data[0]

    def _quadratic_match(self, amount_cents: int, pool: dict) -> int:
        """
        Per-donation matching: proportional to sqrt(donation) so that many
        small donations receive more total match than fewer large ones.
        Capped by remaining pool capacity.
        """
        sqrt_dollars = math.sqrt(amount_cents / 100)
        match_ratio = pool.get("match_ratio", 1.0)
        ideal_match = int(sqrt_dollars * match_ratio * 100)

        remaining_capacity = max(
            0,
            pool["target_amount_cents"] - pool["current_amount_cents"] - pool["matched_pool_cents"],
        )
        return min(ideal_match, remaining_capacity)

    async def distribute_pool(self, pool_id: UUID) -> list[dict]:
        """
        Quadratic funding distribution:
        Each project's share = (sum of sqrt of each donation)^2 / total_qf_score
        """
        pool = await self.get_pool(pool_id)
        if not pool:
            raise ValueError("Pool not found")

        donations_result = (
            self.db.table("donations")
            .select("*")
            .eq("pool_id", str(pool_id))
            .execute()
        )
        donations = donations_result.data or []

        project_contributions: dict[str, list[int]] = {}
        for d in donations:
            pid = d["project_id"]
            project_contributions.setdefault(pid, []).append(d["amount_cents"])

        qf_scores: dict[str, float] = {}
        for pid, amounts in project_contributions.items():
            sqrt_sum = sum(math.sqrt(a / 100) for a in amounts)
            qf_scores[pid] = sqrt_sum ** 2

        total_qf = sum(qf_scores.values())
        if total_qf == 0:
            return []

        total_pool = pool["current_amount_cents"] + pool["matched_pool_cents"]

        distributions = []
        allocated = 0
        sorted_scores = sorted(qf_scores.items(), key=lambda x: x[1], reverse=True)

        for i, (pid, score) in enumerate(sorted_scores):
            share = score / total_qf
            direct = sum(project_contributions[pid])

            if i == len(sorted_scores) - 1:
                payout_amount = total_pool - allocated
            else:
                payout_amount = int(total_pool * share)

            matched = max(0, payout_amount - direct)
            allocated += payout_amount

            distributions.append({
                "pool_id": str(pool_id),
                "project_id": pid,
                "amount_cents": direct,
                "matched_amount_cents": matched,
                "total_payout_cents": payout_amount,
                "qf_score": round(score, 4),
                "share_percentage": round(share * 100, 2),
            })

        self.db.table("money_pools").update({"status": "distributing"}).eq("id", str(pool_id)).execute()

        return distributions

    async def get_pool_donations(self, pool_id: UUID) -> list[dict]:
        result = (
            self.db.table("donations")
            .select("*")
            .eq("pool_id", str(pool_id))
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
