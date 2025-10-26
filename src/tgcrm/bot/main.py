"""Main entrypoint for the Telegram bot."""
from __future__ import annotations

import asyncio

from aiogram import Dispatcher

from tgcrm.bot.bot_factory import create_bot, create_dispatcher
from tgcrm.bot.handlers import settings as settings_handlers
from tgcrm.bot.handlers import start as start_handlers


async def on_startup(dispatcher: Dispatcher) -> None:
    # Register routers and any startup tasks.
    dispatcher.include_router(start_handlers.router)
    dispatcher.include_router(settings_handlers.router)


async def main() -> None:
    bot = create_bot()
    dispatcher = create_dispatcher()
    await on_startup(dispatcher)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
