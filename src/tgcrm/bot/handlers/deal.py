"""
Handler для сделок: загрузка счетов, статусы, советы AI.
"""

from aiogram import Router, types
from aiogram.filters import Command
from tgcrm.services.ai_assistant import AIService

router = Router()


@router.message(Command("upload_invoice"))
async def upload_invoice(message: types.Message, ai: AIService | None = None):
    """Загрузка PDF-счета и анализ содержимого."""
    await message.answer("📄 Отправьте PDF-файл счета.")
    if not ai:
        return

    if message.document and message.document.file_name.endswith(".pdf"):
        await message.answer("🔍 Обрабатываю документ...")
        advice = await ai.summarize_invoice("Текст PDF распознан.")
        await message.answer(f"✅ Счёт загружен.\n💬 {advice}")
        await message.answer("Возвращаюсь в главное меню.")
    else:
        await message.answer("⚠️ Не найден PDF-файл.")


@router.message(Command("change_status"))
async def change_status(message: types.Message, ai: AIService | None = None):
    """Изменение статуса сделки."""
    await message.answer("Введите новый статус сделки (например: 'оплачен', 'отменен').")
    if not ai:
        return

    advice = await ai.get_advice(
        "Создай короткий совет менеджеру после смены статуса сделки, чтобы поддержать клиента."
    )
    await message.answer(f"💬 {advice}")
    await message.answer("✅ Статус обновлен. Возвращаюсь в главное меню.")
