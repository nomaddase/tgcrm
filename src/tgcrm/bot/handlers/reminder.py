"""Reminder related handlers powered by AI suggestions."""
from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tgcrm.bot.menu import render_main_menu
from tgcrm.bot.nlu_parser import extract_entities
from tgcrm.bot.utils.history import delete_message_safe, purge_history, remember_message
from tgcrm.db.models import Deal
from tgcrm.db.session import get_session
from tgcrm.services.ai_assistant import build_reminder_tip
from tgcrm.services.deals import create_reminder, ensure_manager

from .deal import _get_active_deal as _get_active_deal_id, _load_deal_for_manager


async def handle_reminder(message: Message, state: FSMContext) -> None:
    entities = extract_entities(message.text or "")
    if entities.get("intent") != "set_reminder":
        return

    await purge_history(message.bot, message.chat.id, state)
    await delete_message_safe(message)

    deal_id = await _get_active_deal_id(state)
    if not deal_id:
        sent = await message.answer("Сначала выберите сделку, чтобы привязать напоминание.")
        await remember_message(state, sent.message_id)
        return

    remind_at = entities.get("remind_at")
    if remind_at is None:
        sent = await message.answer(
            "Не понял время напоминания. Укажите, например: 'напомни через 2 часа позвонить клиенту'."
        )
        await remember_message(state, sent.message_id)
        return

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        deal: Deal | None = await _load_deal_for_manager(session, deal_id, manager)
        if not deal:
            sent = await message.answer("Сделка не найдена. Повторите поиск клиента.")
            await remember_message(state, sent.message_id)
            return
        await create_reminder(session, deal, remind_at=remind_at)

    reminder_text = entities.get("reminder_text") or ""
    tip = await build_reminder_tip(reminder_text)

    response = (
        "⏰ Напоминание создано.\n"
        f"Совет: {tip}\n\n{render_main_menu()}"
    )
    sent = await message.answer(response)
    await remember_message(state, sent.message_id)


__all__ = ["handle_reminder"]

