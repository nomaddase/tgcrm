"""Main entrypoint for the Telegram bot."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Dispatcher

from tgcrm.bot.bot_factory import create_bot, create_dispatcher
from tgcrm.bot.handlers import settings as settings_handlers
from tgcrm.bot.handlers import start as start_handlers
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
            "TELEGRAM_BOT_TOKEN is empty. Please provide a valid token in the environment before "
            "starting the bot."
        )
        logger.error(message)
        raise RuntimeError(message)


async def on_startup(dispatcher: Dispatcher) -> None:
    # Register routers and any startup tasks.
    dispatcher.include_router(start_handlers.router)
    dispatcher.include_router(settings_handlers.router)


async def main() -> None:
    _ensure_token_present()
    bot = create_bot()
    dispatcher = create_dispatcher()
    await on_startup(dispatcher)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
