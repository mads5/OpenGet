import math
import logging
from datetime import datetime, timezone

from app.core.supabase import get_supabase_admin

logger = logging.getLogger(__name__)

WEIGHTS = {
    "total_contributions": 0.20,
    "prs_raised": 0.15,
    "prs_merged": 0.55,
    "repo_count": 0.10,
}

PR_RAISED_CAP = 50
PR_MERGED_CAP = 30
QUALIFIED_REPO_CAP = 20
MIN_REPO_SCORE = 5


def _normalize(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return min(value / max_value, 1.0)


class ContributorService:
    def __init__(self):
        self.db = get_supabase_admin()

    # ------------------------------------------------------------------
    # 4-factor contributor scoring
    # ------------------------------------------------------------------

    def _get_current_month(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _get_monthly_pr_totals(
        self, contributor_id: str, month: str
    ) -> tuple[int, int]:
        """Sum raised and merged PRs across all repos for a contributor in a month."""
        result = (
            self.db.table("monthly_contributor_stats")
            .select("prs_raised, prs_merged")
            .eq("contributor_id", contributor_id)
            .eq("month", month)
            .execute()
        )
        total_raised = 0
        total_merged = 0
        for row in result.data or []:
            total_raised += row.get("prs_raised", 0)
            total_merged += row.get("prs_merged", 0)
        return total_raised, total_merged

    def _get_qualified_repo_count(self, contributor_id: str) -> int:
        """Count repos that pass anti-fraud filters for this contributor.

        A repo qualifies only if:
        1. Contributor is NOT the repo owner
        2. Repo has stars + forks >= MIN_REPO_SCORE
        3. Contributor has at least 1 merged PR in the repo
        """
        rc_result = (
            self.db.table("repo_contributors")
            .select("repo_id, prs_merged")
            .eq("contributor_id", contributor_id)
            .gt("prs_merged", 0)
            .execute()
        )
        if not rc_result.data:
            return 0

        contributor_row = (
            self.db.table("contributors")
            .select("github_username")
            .eq("id", contributor_id)
            .single()
            .execute()
        )
        username = (contributor_row.data or {}).get("github_username", "").lower()

        repo_ids = [r["repo_id"] for r in rc_result.data]
        repos_result = (
            self.db.table("repos")
            .select("id, owner, stars, forks")
            .in_("id", repo_ids)
            .execute()
        )

        count = 0
        for repo in repos_result.data or []:
            if repo.get("owner", "").lower() == username:
                continue
            repo_score = (repo.get("stars", 0) or 0) + (repo.get("forks", 0) or 0)
            if repo_score < MIN_REPO_SCORE:
                continue
            count += 1

        return min(count, QUALIFIED_REPO_CAP)

    async def compute_contributor_monthly_score(
        self, contributor_id: str, month: str, max_vals: dict
    ) -> float:
        """Compute the 4-factor score for a single contributor.

        max_vals is pre-computed across all contributors for normalization:
        {
            "log_contributions": float,
            "prs_raised": int,
            "prs_merged": int,
            "log_repo_count": float,
        }
        """
        contributor = (
            self.db.table("contributors")
            .select("total_contributions")
            .eq("id", contributor_id)
            .single()
            .execute()
        )
        total_contributions = (contributor.data or {}).get("total_contributions", 0)

        raised, merged = self._get_monthly_pr_totals(contributor_id, month)
        raised = min(raised, PR_RAISED_CAP)
        merged = min(merged, PR_MERGED_CAP)

        qualified_repos = self._get_qualified_repo_count(contributor_id)

        # Factor 1: total contributions (log-scaled)
        f1 = _normalize(
            math.log(1 + total_contributions),
            max_vals.get("log_contributions", 1),
        )

        # Factor 2: raised PRs with merge-ratio penalty
        merge_penalty = 1.0
        if raised > 0:
            merge_penalty = min(1.0, merged / raised)
        f2 = _normalize(raised, max_vals.get("prs_raised", 1)) * merge_penalty

        # Factor 3: merged PRs
        f3 = _normalize(merged, max_vals.get("prs_merged", 1))

        # Factor 4: qualified repo count (log-scaled)
        f4 = _normalize(
            math.log(1 + qualified_repos),
            max_vals.get("log_repo_count", 1),
        )

        score = (
            WEIGHTS["total_contributions"] * f1
            + WEIGHTS["prs_raised"] * f2
            + WEIGHTS["prs_merged"] * f3
            + WEIGHTS["repo_count"] * f4
        )
        return round(score * 1000, 2)

    async def recompute_all_monthly_scores(self, month: str | None = None) -> int:
        """Recompute scores for every contributor using the 4-factor formula.

        Returns number of contributors processed.
        """
        month = month or self._get_current_month()

        contributors = (
            self.db.table("contributors")
            .select("id, total_contributions")
            .execute()
        )
        all_contributors = contributors.data or []
        if not all_contributors:
            return 0

        # Pre-compute max values across all contributors for normalization
        max_log_contributions = 0.0
        max_raised = 0
        max_merged = 0
        max_log_repo_count = 0.0

        contributor_data: list[dict] = []
        for c in all_contributors:
            cid = c["id"]
            total_c = c.get("total_contributions", 0)
            raised, merged = self._get_monthly_pr_totals(cid, month)
            raised = min(raised, PR_RAISED_CAP)
            merged = min(merged, PR_MERGED_CAP)
            qualified = self._get_qualified_repo_count(cid)

            log_c = math.log(1 + total_c)
            log_r = math.log(1 + qualified)

            max_log_contributions = max(max_log_contributions, log_c)
            max_raised = max(max_raised, raised)
            max_merged = max(max_merged, merged)
            max_log_repo_count = max(max_log_repo_count, log_r)

            contributor_data.append({
                "id": cid,
                "log_contributions": log_c,
                "raised": raised,
                "merged": merged,
                "log_repo_count": log_r,
            })

        max_vals = {
            "log_contributions": max_log_contributions or 1,
            "prs_raised": max_raised or 1,
            "prs_merged": max_merged or 1,
            "log_repo_count": max_log_repo_count or 1,
        }

        for cd in contributor_data:
            merge_penalty = 1.0
            if cd["raised"] > 0:
                merge_penalty = min(1.0, cd["merged"] / cd["raised"])

            f1 = _normalize(cd["log_contributions"], max_vals["log_contributions"])
            f2 = _normalize(cd["raised"], max_vals["prs_raised"]) * merge_penalty
            f3 = _normalize(cd["merged"], max_vals["prs_merged"])
            f4 = _normalize(cd["log_repo_count"], max_vals["log_repo_count"])

            score = (
                WEIGHTS["total_contributions"] * f1
                + WEIGHTS["prs_raised"] * f2
                + WEIGHTS["prs_merged"] * f3
                + WEIGHTS["repo_count"] * f4
            )
            total_score = round(score * 1000, 2)

            rc_result = (
                self.db.table("repo_contributors")
                .select("score, repo_id")
                .eq("contributor_id", cd["id"])
                .execute()
            )
            repo_count = len(rc_result.data or [])

            self.db.table("contributors").update(
                {"total_score": total_score, "repo_count": repo_count}
            ).eq("id", cd["id"]).execute()

        return len(contributor_data)

    # ------------------------------------------------------------------
    # Per-repo scoring (kept for backward-compatible per-repo display)
    # ------------------------------------------------------------------

    def compute_repo_contributor_score(self, rc: dict, max_vals: dict) -> float:
        """Score a single contributor within a repo context (for display)."""
        commits_s = _normalize(rc.get("commits", 0), max_vals.get("commits", 1))
        prs_s = _normalize(rc.get("prs_merged", 0), max_vals.get("prs_merged", 1))
        lines_s = _normalize(
            rc.get("lines_added", 0) + rc.get("lines_removed", 0),
            max_vals.get("lines", 1),
        )
        reviews_s = _normalize(rc.get("reviews", 0), max_vals.get("reviews", 1))
        issues_s = _normalize(
            rc.get("issues_closed", 0), max_vals.get("issues_closed", 1)
        )

        score = (
            0.25 * commits_s
            + 0.30 * prs_s
            + 0.15 * lines_s
            + 0.15 * reviews_s
            + 0.15 * issues_s
        )
        return round(score * 1000, 2)

    async def recompute_scores_for_repo(self, repo_id: str) -> None:
        """Recompute per-repo contributor scores (for display/ranking within a repo)."""
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
            "prs_merged": max(
                (e.get("prs_merged", 0) for e in entries), default=1
            )
            or 1,
            "lines": max(
                (
                    e.get("lines_added", 0) + e.get("lines_removed", 0)
                    for e in entries
                ),
                default=1,
            )
            or 1,
            "reviews": max((e.get("reviews", 0) for e in entries), default=1) or 1,
            "issues_closed": max(
                (e.get("issues_closed", 0) for e in entries), default=1
            )
            or 1,
        }

        for entry in entries:
            score = self.compute_repo_contributor_score(entry, max_vals)
            self.db.table("repo_contributors").update({"score": score}).eq(
                "id", entry["id"]
            ).execute()

    async def recompute_total_scores(self) -> None:
        """Recompute total_score and repo_count using the 4-factor formula."""
        await self.recompute_all_monthly_scores()

    # ------------------------------------------------------------------
    # Leaderboard / detail / registration (unchanged logic)
    # ------------------------------------------------------------------

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
            repos.append(
                {
                    **rc,
                    "repo_full_name": repo_info.get("full_name", ""),
                }
            )

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
            .insert(
                {
                    "github_username": github_username,
                    "user_id": user_id,
                    "total_score": 0,
                    "repo_count": 0,
                    "total_contributions": 0,
                }
            )
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to create contributor record")
        c = result.data[0]
        c["is_registered"] = True
        return c
