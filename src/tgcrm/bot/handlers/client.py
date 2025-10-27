"""
Handler для работы с клиентами.
"""

from aiogram import Router, types
from aiogram.filters import Command
from tgcrm.services.ai_assistant import AIService

router = Router()


@router.message(Command("newclient"))
async def create_client(message: types.Message, ai: AIService | None = None):
    """Создание нового клиента с AI-подсказкой."""
    await message.answer("📞 Введите номер телефона клиента:")

    if ai:
        tip = await ai.get_advice(
            "Подскажи менеджеру, что стоит уточнить при первом разговоре с новым клиентом."
        )
        await message.answer(f"💡 Совет: {tip}")

    # Логическое завершение
    await message.answer("✅ Клиент создан. Возвращаюсь в главное меню.")
    try:
        await message.delete()
    except Exception:
        pass
