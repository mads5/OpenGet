import logging
import math
from datetime import datetime, timezone

from app.core.supabase import get_supabase_admin

logger = logging.getLogger(__name__)

WEIGHTS = {
    "commits": 0.25,
    "prs": 0.25,
    "lines": 0.15,
    "reviews": 0.15,
    "issues": 0.10,
    "recency": 0.10,
}


def _normalize(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return min(value / max_value, 1.0)


def _recency_score(last_contribution_at: str | None) -> float:
    """1.0 for today, decays to 0.0 over 365 days."""
    if not last_contribution_at:
        return 0.0
    try:
        if isinstance(last_contribution_at, str):
            dt = datetime.fromisoformat(last_contribution_at.replace("Z", "+00:00"))
        else:
            dt = last_contribution_at
        days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
        return max(1.0 - (days / 365.0), 0.0)
    except (ValueError, TypeError):
        return 0.0


class ContributorService:
    def __init__(self):
        self.db = get_supabase_admin()

    def compute_repo_contributor_score(self, rc: dict, max_vals: dict) -> float:
        """Score a single contributor within a repo context."""
        commits_s = _normalize(rc.get("commits", 0), max_vals.get("commits", 1))
        prs_s = _normalize(rc.get("prs_merged", 0), max_vals.get("prs_merged", 1))
        lines_s = _normalize(
            rc.get("lines_added", 0) + rc.get("lines_removed", 0),
            max_vals.get("lines", 1),
        )
        reviews_s = _normalize(rc.get("reviews", 0), max_vals.get("reviews", 1))
        issues_s = _normalize(rc.get("issues_closed", 0), max_vals.get("issues_closed", 1))
        recency_s = _recency_score(rc.get("last_contribution_at"))

        score = (
            WEIGHTS["commits"] * commits_s
            + WEIGHTS["prs"] * prs_s
            + WEIGHTS["lines"] * lines_s
            + WEIGHTS["reviews"] * reviews_s
            + WEIGHTS["issues"] * issues_s
            + WEIGHTS["recency"] * recency_s
        )
        return round(score * 1000, 2)

    async def recompute_scores_for_repo(self, repo_id: str) -> None:
        """Recompute all contributor scores within a single repo."""
        result = (
            self.db.table("repo_contributors")
            .select("*")
            .eq("repo_id", repo_id)
            .execute()
        )
        entries = result.data or []
        if not entries:
            return

        max_vals = {
            "commits": max((e.get("commits", 0) for e in entries), default=1) or 1,
            "prs_merged": max((e.get("prs_merged", 0) for e in entries), default=1) or 1,
            "lines": max(
                (e.get("lines_added", 0) + e.get("lines_removed", 0) for e in entries),
                default=1,
            ) or 1,
            "reviews": max((e.get("reviews", 0) for e in entries), default=1) or 1,
            "issues_closed": max((e.get("issues_closed", 0) for e in entries), default=1) or 1,
        }

        for entry in entries:
            score = self.compute_repo_contributor_score(entry, max_vals)
            self.db.table("repo_contributors").update({"score": score}).eq(
                "id", entry["id"]
            ).execute()

    async def recompute_total_scores(self) -> None:
        """Recompute total_score and repo_count for every contributor."""
        contributors = self.db.table("contributors").select("id").execute()
        for c in contributors.data or []:
            cid = c["id"]
            rc_result = (
                self.db.table("repo_contributors")
                .select("score, repo_id")
                .eq("contributor_id", cid)
                .execute()
            )
            entries = rc_result.data or []
            total_score = sum(e.get("score", 0) for e in entries)
            repo_count = len(entries)

            self.db.table("contributors").update(
                {"total_score": round(total_score, 2), "repo_count": repo_count}
            ).eq("id", cid).execute()

    async def get_contributor_leaderboard(
        self, page: int = 1, per_page: int = 50
    ) -> dict:
        offset = (page - 1) * per_page
        result = (
            self.db.table("contributors")
            .select("*", count="exact")
            .order("total_score", desc=True)
            .range(offset, offset + per_page - 1)
            .execute()
        )

        contributors = []
        for c in result.data or []:
            c["is_registered"] = c.get("user_id") is not None
            contributors.append(c)

        return {
            "contributors": contributors,
            "total": result.count or 0,
            "page": page,
            "per_page": per_page,
        }

    async def get_contributor_detail(self, contributor_id: str) -> dict | None:
        result = (
            self.db.table("contributors")
            .select("*")
            .eq("id", contributor_id)
            .single()
            .execute()
        )
        if not result.data:
            return None

        contributor = result.data
        contributor["is_registered"] = contributor.get("user_id") is not None

        rc_result = (
            self.db.table("repo_contributors")
            .select("*, repos(full_name)")
            .eq("contributor_id", contributor_id)
            .order("score", desc=True)
            .execute()
        )

        repos = []
        for rc in rc_result.data or []:
            repo_info = rc.pop("repos", {}) or {}
            repos.append({
                **rc,
                "repo_full_name": repo_info.get("full_name", ""),
            })

        contributor["repos"] = repos
        return contributor

    async def register_contributor(self, user_id: str, github_username: str) -> dict:
        """Link a signed-in user to their contributor record (or create one)."""
        existing = (
            self.db.table("contributors")
            .select("*")
            .eq("github_username", github_username)
            .execute()
        )

        if existing.data:
            contributor = existing.data[0]
            if not contributor.get("user_id"):
                self.db.table("contributors").update({"user_id": user_id}).eq(
                    "id", contributor["id"]
                ).execute()
                contributor["user_id"] = user_id
            contributor["is_registered"] = True
            return contributor

        result = (
            self.db.table("contributors")
            .insert({
                "github_username": github_username,
                "user_id": user_id,
                "total_score": 0,
                "repo_count": 0,
            })
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to create contributor record")
        c = result.data[0]
        c["is_registered"] = True
        return c
