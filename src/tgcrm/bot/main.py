"""
Главная точка входа Telegram-бота с инициализацией ChatGPT-ассистента.
"""

from __future__ import annotations
import asyncio
import logging
from aiogram import Bot, Dispatcher

from tgcrm.config import get_settings
from tgcrm.logging import configure_logging
from tgcrm.services.ai_assistant import AIService
from tgcrm.bot.handlers import (
    start as start_handlers,
    client as client_handlers,
    deal as deal_handlers,
    reminder as reminder_handlers,
    supervisor as supervisor_handlers,
    settings as settings_handlers
)

configure_logging()
logger = logging.getLogger(__name__)


async def main() -> None:
    """Запуск Telegram-бота."""
    settings = get_settings()

    if not settings.telegram.bot_token.strip():
        raise RuntimeError("❌ TELEGRAM_BOT_TOKEN не указан в .env")

    bot = Bot(token=settings.telegram.bot_token, parse_mode=settings.telegram.parse_mode)
    dp = Dispatcher()

    # Инициализация ChatGPT-сервиса
    ai = AIService(api_key=settings.openai.api_key, model=settings.openai.model)
    dp["ai"] = ai  # Контекстный доступ к AI в любом handler

    # Регистрация всех router’ов
    dp.include_router(start_handlers.router)
    dp.include_router(client_handlers.router)
    dp.include_router(deal_handlers.router)
    dp.include_router(reminder_handlers.router)
    dp.include_router(supervisor_handlers.router)
    dp.include_router(settings_handlers.router)

    logger.info("🚀 Бот запущен и готов к работе.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Остановка бота.")
