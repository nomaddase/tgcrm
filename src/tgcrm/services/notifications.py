"""Notification helpers for Celery tasks and bot workflows."""
from __future__ import annotations

from contextlib import asynccontextmanager

from aiogram import Bot

from tgcrm.bot.bot_factory import create_bot


@asynccontextmanager
async def _bot_context() -> Bot:
    bot = create_bot()
    try:
        yield bot
    finally:
        await bot.session.close()


async def send_notification(telegram_id: int, text: str) -> None:
    async with _bot_context() as bot:
        await bot.send_message(telegram_id, text)


__all__ = ["send_notification"]
