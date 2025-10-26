"""Factory helpers for aiogram bot and dispatcher instances."""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from tgcrm.config import get_settings


def create_bot() -> Bot:
    settings = get_settings()
    return Bot(token=settings.telegram.bot_token, parse_mode=settings.telegram.parse_mode)


def create_dispatcher() -> Dispatcher:
    return Dispatcher(storage=MemoryStorage())


__all__ = ["create_bot", "create_dispatcher"]
