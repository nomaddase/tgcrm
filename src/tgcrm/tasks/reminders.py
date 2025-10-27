"""Celery tasks for reminders and proactive follow-ups."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, time

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from tgcrm.config import get_settings
from tgcrm.db.models import Deal, Reminder
from tgcrm.db.session import AsyncSessionFactory
from tgcrm.services.ai import build_advice_for_interaction
from tgcrm.services.notifications import send_notification
from tgcrm.services.settings import load_behaviour_overrides
from tgcrm.tasks.celery_app import celery_app

_env_settings = get_settings()


def _resolve_setting(overrides: dict[str, str], key: str, default: str) -> str:
    return overrides.get(key, default)


def _is_within_working_hours(timestamp: datetime, overrides: dict[str, str]) -> bool:
    start_raw = _resolve_setting(overrides, "workday_start", _env_settings.behaviour.workday_start)
    end_raw = _resolve_setting(overrides, "workday_end", _env_settings.behaviour.workday_end)
    lunch_start_raw = _resolve_setting(overrides, "lunch_start", _env_settings.behaviour.lunch_start)
    lunch_end_raw = _resolve_setting(overrides, "lunch_end", _env_settings.behaviour.lunch_end)

    start_hour, start_minute = map(int, start_raw.split(":"))
    end_hour, end_minute = map(int, end_raw.split(":"))
    lunch_start_hour, lunch_start_minute = map(int, lunch_start_raw.split(":"))
    lunch_end_hour, lunch_end_minute = map(int, lunch_end_raw.split(":"))

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
        overrides = await load_behaviour_overrides(session)
        query = (
            select(Reminder)
            .options(selectinload(Reminder.deal).selectinload(Deal.manager))
            .where(Reminder.is_sent.is_(False), Reminder.remind_at <= datetime.utcnow())
        )
        result = await session.execute(query)
        reminders = result.scalars().all()
        for reminder in reminders:
            deal = reminder.deal
            manager = deal.manager
            if manager.telegram_id is None:
                continue
            advice = "Попробуйте связаться с клиентом и уточнить статус переговоров."
            if deal.interactions:
                advice = await build_advice_for_interaction(deal, "reminder")
            await send_notification(
                manager.telegram_id,
                (
                    f"🔔 Напоминание по сделке #{deal.id} клиента {deal.client.name or deal.client.phone_number}.\n"
                    f"Совет: {advice}"
                ),
            )
            reminder.is_sent = True
        await session.commit()


async def _proactive_follow_up() -> None:
    async with AsyncSessionFactory() as session:
        overrides = await load_behaviour_overrides(session)
        now = datetime.utcnow()
        query = (
            select(Deal)
            .options(selectinload(Deal.manager), selectinload(Deal.client), selectinload(Deal.interactions))
            .where(Deal.last_interaction_at.isnot(None))
        )
        result = await session.execute(query)
        deals = result.scalars().all()
        for deal in deals:
            if deal.status in _env_settings.behaviour.proactive_excluded_statuses:
                continue
            if (now - deal.last_interaction_at).total_seconds() < 12 * 3600:
                continue
            if not _is_within_working_hours(now, overrides):
                continue
            manager = deal.manager
            if manager.telegram_id is None:
                continue
            advice = await build_advice_for_interaction(deal, "proactive")
            await send_notification(
                manager.telegram_id,
                (
                    "⚠️ Давно не было контакта с клиентом\n"
                    f"Клиент: {deal.client.name or deal.client.phone_number}\n"
                    f"Последняя связь: {deal.last_interaction_at:%Y-%m-%d %H:%M}\n"
                    f"Совет: {advice}"
                ),
            )
        await session.commit()


@celery_app.task
def send_due_reminders() -> None:
    asyncio.run(_send_due_reminders())


@celery_app.task
def proactive_follow_up() -> None:
    asyncio.run(_proactive_follow_up())


__all__ = ["send_due_reminders", "proactive_follow_up"]
