from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tgcrm.bot.menu import render_main_menu
from tgcrm.bot.nlu_parser import detect_intent, extract_entities
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import delete_message_safe, purge_history, remember_message
from tgcrm.db.session import get_session
from tgcrm.services.deals import ensure_manager

from .client import start_client_creation
from .deal import handle_interaction, handle_status_change, list_manager_deals, select_deal_by_suffix
from .reminder import handle_reminder
from .settings import start_settings_flow
from .supervisor import start_supervisor_report


router = Router()


@router.message(BotStates.idle)
async def interpret_message(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    intent = detect_intent(text)
    entities = extract_entities(text)

    if intent == "main_menu":
        await purge_history(message.bot, message.chat.id, state)
        await delete_message_safe(message)
        sent = await message.answer(render_main_menu())
        await remember_message(state, sent.message_id)
        return

    if intent == "create_client":
        await start_client_creation(message, state, entities.get("phone", text))
        return

    if intent == "search_deal_by_last4":
        suffix = str(entities.get("last4") or text[-4:])
        await select_deal_by_suffix(message, state, suffix)
        return

    if intent == "list_deals":
        await list_manager_deals(message, state)
        return

    if intent == "add_interaction":
        summary = entities.get("interaction") or text
        if summary.strip():
            await handle_interaction(message, state, summary)
            return

    if intent == "set_reminder":
        await handle_reminder(message, state)
        return

    if intent == "change_status":
        identifier = entities.get("identifier")
        if identifier and not (await state.get_data()).get("active_deal_id") and len(str(identifier)) >= 4:
            await select_deal_by_suffix(message, state, str(identifier)[-4:])
        await handle_status_change(message, state, entities.get("status", text))
        return

    if intent == "upload_invoice":
        data = await state.get_data()
        if not data.get("active_deal_id"):
            await delete_message_safe(message)
            sent = await message.answer("Сначала выберите сделку по последним 4 цифрам клиента.")
            await remember_message(state, sent.message_id)
            return
        await state.set_state(BotStates.awaiting_pdf)
        await purge_history(message.bot, message.chat.id, state)
        await delete_message_safe(message)
        sent = await message.answer("Отправьте PDF-файл счёта для анализа")
        await remember_message(state, sent.message_id)
        return

    if intent == "supervisor_summary":
        await start_supervisor_report(message, state)
        return

    if intent == "settings":
        await start_settings_flow(message, state)
        return

    await _unknown_intent_response(message, state)


async def _unknown_intent_response(message: Message, state: FSMContext) -> None:
    await delete_message_safe(message)
    async with get_session() as session:
        await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
    sent = await message.answer(
        "Я пока не понял запрос. Попробуйте сформулировать иначе или воспользуйтесь меню.\n\n"
        f"{render_main_menu()}"
    )
    await remember_message(state, sent.message_id)


__all__ = ["router"]

