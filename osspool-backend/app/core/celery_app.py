import os
import logging

logger = logging.getLogger(__name__)

celery = None

try:
    from celery import Celery

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
    )

    celery.autodiscover_tasks(["app.tasks"])
except Exception as e:
    logger.warning(f"Celery unavailable, background tasks will run inline: {e}")
    celery = None
