import asyncio
import logging

from app.core.celery_app import celery
from app.schemas.rankings import TimePeriod
from app.services.ranking_service import RankingService

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery.task(bind=True, max_retries=2, default_retry_delay=30)
def recompute_rankings_for_period(self, period_value: str):
    try:
        period = TimePeriod(period_value)
    except ValueError:
        logger.error(f"Invalid period value: {period_value}")
        return {"error": f"Invalid period: {period_value}"}

    try:
        service = RankingService()
        rankings = _run_async(service.compute_rankings(period))
        logger.info(f"Computed {len(rankings)} rankings for {period.value}")
        return {"period": period.value, "count": len(rankings)}
    except Exception as exc:
        logger.exception(f"Failed to compute rankings for {period_value}")
        raise self.retry(exc=exc)


@celery.task
def recompute_all_rankings():
    for period in TimePeriod:
        recompute_rankings_for_period.delay(period.value)
    logger.info(f"Dispatched ranking recompute for {len(TimePeriod)} periods")
    return {"dispatched": [p.value for p in TimePeriod]}
