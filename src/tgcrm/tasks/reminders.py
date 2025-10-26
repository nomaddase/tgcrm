"""Celery tasks for reminders and proactive follow-ups."""
from __future__ import annotations

import asyncio
from datetime import datetime, time

from sqlalchemy import select

from tgcrm.config import get_settings
from tgcrm.db.models import Deal, Reminder
from tgcrm.db.session import AsyncSessionFactory
from tgcrm.tasks.celery_app import celery_app

settings = get_settings()


def _is_within_working_hours(timestamp: datetime) -> bool:
    start_hour, start_minute = map(int, settings.behaviour.workday_start.split(":"))
    end_hour, end_minute = map(int, settings.behaviour.workday_end.split(":"))
    lunch_start_hour, lunch_start_minute = map(int, settings.behaviour.lunch_start.split(":"))
    lunch_end_hour, lunch_end_minute = map(int, settings.behaviour.lunch_end.split(":"))

    start = time(start_hour, start_minute)
    end = time(end_hour, end_minute)
    lunch_start = time(lunch_start_hour, lunch_start_minute)
    lunch_end = time(lunch_end_hour, lunch_end_minute)

    current_time = timestamp.time()
    within_hours = start <= current_time <= end
    in_lunch = lunch_start <= current_time <= lunch_end
    return within_hours and not in_lunch


async def _send_due_reminders() -> None:
    async with AsyncSessionFactory() as session:
        query = select(Reminder).where(Reminder.is_sent.is_(False), Reminder.remind_at <= datetime.utcnow())
        result = await session.execute(query)
        reminders = result.scalars().all()
        for reminder in reminders:
            reminder.is_sent = True
        await session.commit()


async def _proactive_follow_up() -> None:
    async with AsyncSessionFactory() as session:
        now = datetime.utcnow()
        query = select(Deal).where(Deal.last_interaction_at.isnot(None))
        result = await session.execute(query)
        deals = result.scalars().all()
        for deal in deals:
            if deal.status.lower() in settings.behaviour.proactive_excluded_statuses:
                continue
            if (now - deal.last_interaction_at).total_seconds() < 12 * 3600:
                continue
            if not _is_within_working_hours(now):
                continue
            # Placeholder: send Telegram notification to manager.
        await session.commit()


@celery_app.task
def send_due_reminders() -> None:
    asyncio.run(_send_due_reminders())


@celery_app.task
def proactive_follow_up() -> None:
    asyncio.run(_proactive_follow_up())


__all__ = ["send_due_reminders", "proactive_follow_up"]
