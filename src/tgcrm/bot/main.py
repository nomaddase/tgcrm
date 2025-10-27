"""Main entrypoint for the Telegram bot."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from tgcrm.bot.bot_factory import create_bot, create_dispatcher
from tgcrm.bot.handlers import (
    assistant as assistant_handlers,
    start as start_handlers,
    client as client_handlers,
    deal as deal_handlers,
    settings as settings_handlers,
    supervisor as supervisor_handlers,
)
from tgcrm.config import get_settings
from tgcrm.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


def _ensure_token_present() -> None:
    try:
        settings = get_settings()
    except RuntimeError as exc:
        logger.error("Configuration error: %s", exc)
        raise

    if not settings.telegram.bot_token.strip():
        message = (
            "TELEGRAM_BOT_TOKEN is empty. Please provide a valid token in the environment before starting the bot."
        )
        logger.error(message)
        raise RuntimeError(message)


async def on_startup(dispatcher: Dispatcher) -> None:
    """Hook that runs when the bot starts polling."""
    logger.info("🤖 Bot successfully started and polling Telegram API.")


async def main() -> None:
    _ensure_token_present()
    bot = create_bot()
    dispatcher = create_dispatcher(
        start_handlers.router,
        settings_handlers.router,
        client_handlers.router,
        deal_handlers.router,
        supervisor_handlers.router,
        assistant_handlers.router,
    )

    # Правильный хук запуска (учитываем тестовые заглушки)
    startup_registered = False
    if hasattr(dispatcher, "startup") and hasattr(dispatcher.startup, "register"):
        dispatcher.startup.register(on_startup)
        startup_registered = True
    else:
        await on_startup(dispatcher)

    logger.info("🚀 Starting Telegram polling...")
    try:
        await dispatcher.start_polling(bot)
    except Exception as e:
        logger.exception("Polling failed: %s", e)
    finally:
        await bot.session.close()
        logger.info("Bot session closed.")


if __name__ == "__main__":
    asyncio.run(main())
