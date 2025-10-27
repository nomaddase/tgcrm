"""Celery application configuration."""
from __future__ import annotations

import logging

from celery import Celery
from celery.schedules import crontab
from importlib import import_module

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
)

celery_app.conf.CELERY_BEAT_SCHEDULE = {
    "send-due-reminders": {
        "task": "tgcrm.tasks.reminders.send_due_reminders",
        "schedule": crontab(minute="*/5"),
    },
    "proactive-follow-up": {
        "task": "tgcrm.tasks.reminders.proactive_follow_up",
        "schedule": crontab(minute=0, hour="10-17"),
    },
}

logger.info("Celery configured with broker %s", settings.redis.dsn)

celery_app.autodiscover_tasks(["tgcrm.tasks"])

for module_name in ("tgcrm.tasks.reminders",):
    import_module(module_name)

REQUIRED_TASKS = {
    "tgcrm.tasks.reminders.send_due_reminders",
    "tgcrm.tasks.reminders.proactive_follow_up",
}

missing_tasks = sorted(REQUIRED_TASKS.difference(celery_app.tasks.keys()))
if missing_tasks:  # pragma: no cover - defensive guard for deployment issues
    raise RuntimeError(
        "Celery tasks are missing from the registry: %s. Ensure task modules are imported correctly."
        % ", ".join(missing_tasks)
    )


__all__ = ["celery_app"]
