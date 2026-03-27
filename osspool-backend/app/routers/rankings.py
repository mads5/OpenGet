from fastapi import APIRouter, Query

from app.schemas.rankings import TimePeriod, LeaderboardResponse
from app.services.ranking_service import RankingService
from app.tasks.ranking_tasks import recompute_all_rankings

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    period: TimePeriod = TimePeriod.WEEKLY,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
):
    service = RankingService()
    return await service.get_leaderboard(period, page, per_page)


@router.post("/recompute")
async def trigger_recompute(period: TimePeriod | None = None):
    if period:
        from app.tasks.ranking_tasks import recompute_rankings_for_period
        task = recompute_rankings_for_period.delay(period.value)
    else:
        task = recompute_all_rankings.delay()
    return {"task_id": task.id, "status": "queued"}
