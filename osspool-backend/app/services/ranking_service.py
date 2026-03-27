import logging
import math
from datetime import datetime, timezone
from uuid import UUID

from app.core.supabase import get_supabase_admin
from app.schemas.rankings import TimePeriod, RankingScoreBreakdown

logger = logging.getLogger(__name__)

WEIGHTS = {
    "dependents": 0.30,
    "download_velocity": 0.25,
    "commit_recency": 0.20,
    "issue_close_rate": 0.15,
    "stars_growth": 0.10,
}

PERIOD_DECAY = {
    TimePeriod.DAILY: 1.0,
    TimePeriod.WEEKLY: 7.0,
    TimePeriod.MONTHLY: 30.0,
    TimePeriod.YEARLY: 365.0,
    TimePeriod.ALL_TIME: 0.0,
}


def _normalize(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return min(value / max_value, 1.0)


def _time_decay(days_since_last_activity: float, period: TimePeriod) -> float:
    decay_window = PERIOD_DECAY[period]
    if decay_window == 0:
        return 1.0
    half_life = decay_window / 2
    return math.exp(-0.693 * days_since_last_activity / max(half_life, 1))


class RankingService:
    def __init__(self):
        self.db = get_supabase_admin()

    def compute_project_score(
        self,
        stats: dict,
        max_values: dict,
        period: TimePeriod,
    ) -> tuple[float, RankingScoreBreakdown]:
        dependents_score = _normalize(stats.get("dependents_count", 0), max_values.get("dependents", 1))
        download_score = _normalize(stats.get("download_count", 0), max_values.get("downloads", 1))
        issue_score = min(float(stats.get("issue_close_rate", 0.0)), 1.0)
        stars_growth_score = _normalize(stats.get("stars_growth_rate", 0), max_values.get("stars_growth", 1))

        last_commit = stats.get("last_commit_at")
        if last_commit:
            if isinstance(last_commit, str):
                last_commit = datetime.fromisoformat(last_commit.replace("Z", "+00:00"))
            days_since = (datetime.now(timezone.utc) - last_commit).total_seconds() / 86400
        else:
            days_since = 365.0

        commit_freq = float(stats.get("commit_frequency", 0.0))
        commit_recency_score = max(1.0 - (days_since / 365.0), 0.0)
        if commit_freq > 0:
            commit_recency_score = min(commit_recency_score + (commit_freq / 100.0), 1.0)

        decay = _time_decay(days_since, period)

        raw_score = (
            WEIGHTS["dependents"] * dependents_score
            + WEIGHTS["download_velocity"] * download_score
            + WEIGHTS["commit_recency"] * commit_recency_score
            + WEIGHTS["issue_close_rate"] * issue_score
            + WEIGHTS["stars_growth"] * stars_growth_score
        )

        total_score = round(raw_score * decay * 1000, 2)

        breakdown = RankingScoreBreakdown(
            dependents_score=round(dependents_score * WEIGHTS["dependents"] * 1000, 2),
            download_velocity_score=round(download_score * WEIGHTS["download_velocity"] * 1000, 2),
            commit_recency_score=round(commit_recency_score * WEIGHTS["commit_recency"] * 1000, 2),
            issue_close_rate_score=round(issue_score * WEIGHTS["issue_close_rate"] * 1000, 2),
            stars_growth_score=round(stars_growth_score * WEIGHTS["stars_growth"] * 1000, 2),
            time_decay_factor=round(decay, 4),
        )

        return total_score, breakdown

    async def compute_rankings(self, period: TimePeriod) -> list[dict]:
        result = self.db.table("projects").select("*").eq("is_active", True).execute()
        projects = result.data or []

        if not projects:
            return []

        max_values = {
            "dependents": max((p.get("dependents_count", 0) for p in projects), default=1) or 1,
            "downloads": max((p.get("download_count", 0) for p in projects), default=1) or 1,
            "stars_growth": max((p.get("stars_growth_rate", 0) for p in projects), default=1) or 1,
        }

        scored = []
        for project in projects:
            total_score, breakdown = self.compute_project_score(project, max_values, period)
            scored.append({
                "project_id": project["id"],
                "project_name": project["name"],
                "github_url": project["github_url"],
                "total_score": total_score,
                "breakdown": breakdown.model_dump(),
                "period": period.value,
                "computed_at": datetime.now(timezone.utc).isoformat(),
            })

        scored.sort(key=lambda x: x["total_score"], reverse=True)

        for rank, entry in enumerate(scored, 1):
            entry["rank"] = rank

        self.db.table("rankings").delete().eq("period", period.value).execute()
        self.db.table("rankings").insert(scored).execute()

        return scored

    async def get_leaderboard(
        self, period: TimePeriod, page: int = 1, per_page: int = 50
    ) -> dict:
        offset = (page - 1) * per_page
        result = (
            self.db.table("rankings")
            .select("*", count="exact")
            .eq("period", period.value)
            .order("rank", desc=False)
            .range(offset, offset + per_page - 1)
            .execute()
        )

        return {
            "rankings": result.data or [],
            "total": result.count or 0,
            "page": page,
            "per_page": per_page,
            "period": period,
            "computed_at": result.data[0]["computed_at"] if result.data else None,
        }
