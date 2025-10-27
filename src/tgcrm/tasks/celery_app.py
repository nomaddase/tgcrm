"""Celery application configuration."""
from __future__ import annotations

import logging

from celery import Celery
from celery.schedules import crontab

from tgcrm.config import get_settings
from tgcrm.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery("tgcrm")

celery_app.conf.update(
    broker_url=settings.redis.dsn,
    result_backend=settings.redis.dsn,
    timezone="Asia/Almaty",
    enable_utc=False,
    beat_schedule={
        "send-due-reminders": {
            "task": "tgcrm.tasks.reminders.send_due_reminders",
            "schedule": crontab(minute="*/5"),
        },
        "proactive-follow-up": {
            "task": "tgcrm.tasks.reminders.proactive_follow_up",
            "schedule": crontab(minute=0, hour="10-17"),
        },
    },
)

logger.info("Celery configured with broker %s", settings.redis.dsn)

celery_app.autodiscover_tasks(["tgcrm.tasks"])


__all__ = ["celery_app"]
