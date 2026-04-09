import os
import logging

logger = logging.getLogger(__name__)

celery = None

try:
    from celery import Celery
    from celery.schedules import crontab

    _broker = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
    _backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

    celery = Celery(
        "openget",
        broker=_broker,
        backend=_backend,
    )

    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        beat_schedule={
            "friday-score-calculation": {
                "task": "calculate_weekly_scores",
                "schedule": crontab(day_of_week=5, hour=0, minute=0),
            },
            "saturday-pool-distribution": {
                "task": "distribute_weekly_pool",
                "schedule": crontab(day_of_week=6, hour=0, minute=0),
            },
            "sunday-money-deposit": {
                "task": "process_weekly_payouts",
                "schedule": crontab(day_of_week=0, hour=0, minute=0),
            },
            "month-end-check": {
                "task": "finalize_monthly_pool",
                "schedule": crontab(hour=23, minute=55),
            },
        },
    )

    celery.autodiscover_tasks(["app.tasks"])
except Exception as e:
    logger.warning(f"Celery unavailable, background tasks will run inline: {e}")
    celery = None
