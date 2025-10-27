"""Persistence helpers for runtime bot settings."""
from __future__ import annotations

from typing import Dict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from tgcrm.db.models import BotSetting


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    existing = await session.execute(select(BotSetting).where(BotSetting.key == key))
    record = existing.scalar_one_or_none()
    if record:
        record.value = value
    else:
        session.add(BotSetting(key=key, value=value))
    await session.flush()


async def get_setting(session: AsyncSession, key: str) -> str | None:
    result = await session.execute(select(BotSetting).where(BotSetting.key == key))
    record = result.scalar_one_or_none()
    return record.value if record else None


async def delete_setting(session: AsyncSession, key: str) -> None:
    await session.execute(delete(BotSetting).where(BotSetting.key == key))
    await session.flush()


async def load_behaviour_overrides(session: AsyncSession) -> Dict[str, str]:
    result = await session.execute(select(BotSetting))
    settings = {record.key: record.value for record in result.scalars()}
    return settings


__all__ = ["delete_setting", "get_setting", "load_behaviour_overrides", "set_setting"]
