import os
from celery import Celery

_broker = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery = Celery(
    "osspool",
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
        "crawl-all-projects": {
            "task": "app.tasks.crawler_tasks.crawl_all_projects",
            "schedule": 3600.0,
        },
        "recompute-rankings": {
            "task": "app.tasks.ranking_tasks.recompute_all_rankings",
            "schedule": 1800.0,
        },
    },
)

celery.autodiscover_tasks(["app.tasks"])
