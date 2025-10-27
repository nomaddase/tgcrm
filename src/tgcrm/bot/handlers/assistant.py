"""Router that interprets natural language commands from managers."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tgcrm.bot.menu import render_main_menu
from tgcrm.bot.nlu_parser import Intent, parse_intent
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import delete_message_safe, purge_history, remember_message
from tgcrm.db.session import get_session
from tgcrm.services.deals import ensure_manager

from .client import start_client_creation
from .deal import (
    handle_interaction,
    handle_reminder,
    handle_status_change,
    list_manager_deals,
    select_deal_by_suffix,
)
from .settings import start_settings_flow
from .supervisor import start_supervisor_report


router = Router()


@router.message(BotStates.idle)
async def interpret_message(message: Message, state: FSMContext) -> None:
    intent_result = parse_intent(message.text)
    intent = intent_result.intent

    if intent is Intent.MAIN_MENU:
        await purge_history(message.bot, message.chat.id, state)
        await delete_message_safe(message)
        sent = await message.answer(render_main_menu())
        await remember_message(state, sent.message_id)
        return

    if intent is Intent.CREATE_CLIENT:
        await start_client_creation(message, state, intent_result.payload.get("phone", message.text or ""))
        return

    if intent is Intent.DEAL_SEARCH:
        await select_deal_by_suffix(message, state, intent_result.payload["suffix"])
        return

    if intent is Intent.DEAL_SUMMARY:
        await list_manager_deals(message, state)
        return

    if intent is Intent.INTERACTION:
        await handle_interaction(message, state, intent_result.payload.get("summary", message.text or ""))
        return

    if intent is Intent.REMINDER:
        await handle_reminder(message, state, intent_result.payload.get("text", message.text or ""))
        return

    if intent is Intent.STATUS_CHANGE:
        identifier = intent_result.payload.get("identifier")
        if identifier and not (await state.get_data()).get("active_deal_id") and len(identifier) >= 4:
            await select_deal_by_suffix(message, state, identifier[-4:])
        await handle_status_change(message, state, intent_result.payload.get("status", ""))
        return

    if intent is Intent.INVOICE_REQUEST:
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

    if intent is Intent.SUPERVISOR_REPORT:
        await start_supervisor_report(message, state)
        return

    if intent is Intent.SETTINGS:
        await start_settings_flow(message, state)
        return

    # Unknown intent – ensure manager exists and remind about main menu.
    await delete_message_safe(message)
    async with get_session() as session:
        await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
    sent = await message.answer(
        "Я пока не понял запрос. Попробуйте сформулировать иначе или воспользуйтесь меню.\n\n"
        f"{render_main_menu()}"
    )
    await remember_message(state, sent.message_id)


__all__ = ["router"]
