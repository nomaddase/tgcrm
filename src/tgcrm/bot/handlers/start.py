"""
Обработка команды /start и приветствие с поддержкой ChatGPT.
"""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message, ai=None) -> None:
    """Приветствие и начало диалога с AI-подсказкой."""
    base_text = (
        "👋 Привет! Я CRM-бот для менеджеров.\n"
        "Отправьте номер телефона клиента или последние 4 цифры, чтобы начать работу."
    )

    if ai:
        try:
            advice = await ai.get_advice(
                "Создай дружелюбное приветственное сообщение для менеджера CRM, который только начал работу с ботом."
            )
            await message.answer(f"{base_text}\n\n💡 {advice}")
        except Exception:
            await message.answer(base_text)
    else:
        await message.answer(base_text)
