"""Celery application configuration."""
from __future__ import annotations

from celery import Celery

from tgcrm.config import get_settings

settings = get_settings()

celery_app = Celery(
    "tgcrm",
    broker=settings.redis.dsn,
    backend=settings.redis.dsn,
)

celery_app.conf.beat_schedule = {}
celery_app.conf.timezone = "Europe/Moscow"
celery_app.autodiscover_tasks(["tgcrm.tasks"])


__all__ = ["celery_app"]
