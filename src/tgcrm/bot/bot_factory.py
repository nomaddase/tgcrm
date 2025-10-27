"""Factory helpers for aiogram bot and dispatcher instances."""
from __future__ import annotations

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from tgcrm.config import get_settings


def create_bot() -> Bot:
    """Create a :class:`Bot` configured for the current environment."""

    settings = get_settings()
    default_properties = DefaultBotProperties(parse_mode=settings.telegram.parse_mode)
    return Bot(token=settings.telegram.bot_token, default=default_properties)


def create_dispatcher(*routers: Router) -> Dispatcher:
    """Create a :class:`Dispatcher` and attach the provided routers."""

    dispatcher = Dispatcher(storage=MemoryStorage())
    if routers:
        dispatcher.include_routers(*routers)
    return dispatcher


__all__ = ["create_bot", "create_dispatcher"]
