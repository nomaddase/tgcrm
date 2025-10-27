"""Tests that verify the bot can be started and shut down gracefully."""
from __future__ import annotations

import asyncio
from importlib import import_module, reload
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from tgcrm.config import get_settings


def _load_bot_main_module() -> ModuleType:
    module = import_module("tgcrm.bot.main")
    return reload(module)


def test_bot_can_start_polling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:test-token")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()

    bot_main = _load_bot_main_module()

    dispatcher = SimpleNamespace(start_polling=AsyncMock())
    bot = SimpleNamespace(session=SimpleNamespace(close=AsyncMock()))

    monkeypatch.setattr(bot_main, "create_bot", Mock(return_value=bot))
    monkeypatch.setattr(bot_main, "create_dispatcher", Mock(return_value=dispatcher))
    monkeypatch.setattr(bot_main, "on_startup", AsyncMock())

    asyncio.run(bot_main.main())

    bot_main.on_startup.assert_awaited_once_with(dispatcher)
    dispatcher.start_polling.assert_awaited_once_with(bot)
    bot.session.close.assert_awaited_once()
