"""Handlers related to deal selection and actions."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Document, Message
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from tgcrm.bot.keyboards.main import (
    MainMenuButtons,
    deal_actions_menu,
    deal_status_menu,
    interaction_menu,
    reminder_presets,
)
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import purge_history, remember_message
from tgcrm.db.models import Deal, Manager
from tgcrm.db.session import get_session
from tgcrm.services.ai import answer_item_question, build_advice_for_interaction
from tgcrm.services.deals import (
    attach_invoice,
    change_deal_status,
    create_reminder,
    ensure_manager,
    get_active_deal_by_phone_suffix,
    log_interaction,
)
from tgcrm.services.pdf_processing import parse_invoice


INVOICE_STORAGE = Path("var/invoices")
INVOICE_STORAGE.mkdir(parents=True, exist_ok=True)

router = Router()


async def _load_deal_for_manager(session, deal_id: int, manager: Manager) -> Deal | None:
    query = (
        select(Deal)
        .options(joinedload(Deal.client), joinedload(Deal.interactions), joinedload(Deal.invoices))
        .where(Deal.id == deal_id, Deal.manager_id == manager.id)
    )
    result = await session.execute(query)
    return result.scalars().first()


@router.message(F.text == MainMenuButtons.SEARCH_BY_SUFFIX)
async def request_deal_suffix(message: Message, state: FSMContext) -> None:
    await purge_history(message.bot, message.chat.id, state)
    await state.set_state(BotStates.selecting_deal)
    sent = await message.answer("Введите последние четыре цифры номера клиента")
    await remember_message(state, sent.message_id)


async def _ensure_deal_selected(message: Message, state: FSMContext) -> int | None:
    data = await state.get_data()
    deal_id = data.get("active_deal_id")
    if not deal_id:
        sent = await message.answer("Сначала выберите сделку по последним 4 цифрам")
        await remember_message(state, sent.message_id)
        return None
    return deal_id


@router.message(F.text == MainMenuButtons.ATTACH_INVOICE)
async def prompt_invoice_upload(message: Message, state: FSMContext) -> None:
    await purge_history(message.bot, message.chat.id, state)
    deal_id = await _ensure_deal_selected(message, state)
    if not deal_id:
        return
    await state.set_state(BotStates.awaiting_pdf)
    sent = await message.answer("Пришлите PDF-счёт для прикрепления")
    await remember_message(state, sent.message_id)


@router.message(F.text == MainMenuButtons.INTERACTION)
async def prompt_interaction_menu(message: Message, state: FSMContext) -> None:
    await purge_history(message.bot, message.chat.id, state)
    deal_id = await _ensure_deal_selected(message, state)
    if not deal_id:
        return
    await state.set_state(BotStates.choosing_interaction)
    sent = await message.answer("Выберите тип взаимодействия", reply_markup=interaction_menu())
    await remember_message(state, sent.message_id)


@router.message(F.text == MainMenuButtons.REMINDER)
async def prompt_reminder(message: Message, state: FSMContext) -> None:
    await purge_history(message.bot, message.chat.id, state)
    deal_id = await _ensure_deal_selected(message, state)
    if not deal_id:
        return
    await state.set_state(BotStates.entering_reminder_time)
    sent = await message.answer(
        "Выберите время напоминания или отправьте вручную в формате YYYY-MM-DD HH:MM",
        reply_markup=reminder_presets(),
    )
    await remember_message(state, sent.message_id)


@router.message(BotStates.selecting_deal, F.text)
async def handle_deal_suffix(message: Message, state: FSMContext) -> None:
    suffix = (message.text or "").strip()
    if not suffix.isdigit() or len(suffix) != 4:
        sent = await message.answer("Укажите ровно 4 цифры")
        await remember_message(state, sent.message_id)
        return

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        deal = await get_active_deal_by_phone_suffix(session, phone_suffix=suffix, manager=manager)
        if not deal:
            sent = await message.answer("Сделки не найдены. Убедитесь, что клиент относится к вам.")
            await remember_message(state, sent.message_id)
            return

    await state.update_data({"active_deal_id": deal.id})
    sent = await message.answer(
        (
            f"Выбран клиент {deal.client.name or deal.client.phone_number}.\n"
            f"Текущий статус: {deal.status}."
        ),
        reply_markup=deal_actions_menu(),
    )
    await remember_message(state, sent.message_id)
    await state.set_state(BotStates.idle)


@router.callback_query(F.data.startswith("deal:"))
async def handle_deal_action(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    deal_id = data.get("active_deal_id")
    if not deal_id:
        await callback.answer("Сначала выберите сделку по последним 4 цифрам", show_alert=True)
        return

    action = callback.data.split(":", 1)[1]
    if action == "attach_invoice":
        await state.set_state(BotStates.awaiting_pdf)
        sent = await callback.message.answer("Пришлите PDF-счёт для прикрепления")
        await remember_message(state, sent.message_id)
    elif action == "interaction":
        await state.set_state(BotStates.choosing_interaction)
        sent = await callback.message.answer(
            "Выберите тип взаимодействия", reply_markup=interaction_menu()
        )
        await remember_message(state, sent.message_id)
    elif action == "reminder":
        await state.set_state(BotStates.entering_reminder_time)
        sent = await callback.message.answer(
            "Выберите время напоминания или отправьте вручную в формате YYYY-MM-DD HH:MM",
            reply_markup=reminder_presets(),
        )
        await remember_message(state, sent.message_id)
    elif action == "status":
        sent = await callback.message.answer("Выберите новый статус", reply_markup=deal_status_menu())
        await remember_message(state, sent.message_id)
    await callback.answer()


@router.message(BotStates.awaiting_pdf, F.document)
async def handle_invoice_upload(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    deal_id = data.get("active_deal_id")
    document: Document = message.document

    if not document.file_name or not document.file_name.lower().endswith(".pdf"):
        sent = await message.answer("Пожалуйста, отправьте PDF-файл")
        await remember_message(state, sent.message_id)
        return

    destination = INVOICE_STORAGE / f"deal_{deal_id}_{document.file_unique_id}.pdf"
    await message.bot.download(document, destination=destination)
    invoice_data = parse_invoice(destination)

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        deal = await _load_deal_for_manager(session, deal_id, manager)
        if not deal:
            sent = await message.answer("Сделка не найдена или не принадлежит вам")
            await remember_message(state, sent.message_id)
            return
        invoice = await attach_invoice(session, deal, invoice_data, str(destination))
        await session.refresh(deal, attribute_names=["status", "amount"])

    sent = await message.answer(
        (
            "✅ Счёт прикреплён.\n"
            f"Сумма: {invoice.total_amount:.2f}."
            f" Позиции: {len(invoice_data.line_items)}."
        )
    )
    await remember_message(state, sent.message_id)
    await state.set_state(BotStates.idle)


@router.callback_query(BotStates.choosing_interaction, F.data.startswith("interaction:"))
async def choose_interaction(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    deal_id = data.get("active_deal_id")
    interaction_type = callback.data.split(":", 1)[1]

    async with get_session() as session:
        manager = await ensure_manager(
            session, callback.from_user.id, name=callback.from_user.full_name
        )
        deal = await _load_deal_for_manager(session, deal_id, manager)
        if not deal:
            await callback.answer("Сделка не найдена", show_alert=True)
            return
        advice = await build_advice_for_interaction(deal, interaction_type)

    sent = await callback.message.answer(
        f"Совет для взаимодействия ({interaction_type}):\n{advice}\nРасскажите, как прошла коммуникация."
    )
    await remember_message(state, sent.message_id)
    await state.update_data({"interaction_type": interaction_type, "interaction_advice": advice})
    await state.set_state(BotStates.choosing_interaction)
    await callback.answer()


@router.message(BotStates.choosing_interaction, F.text)
async def log_interaction_result(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    deal_id = data.get("active_deal_id")
    interaction_type = data.get("interaction_type", "interaction")

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        deal = await _load_deal_for_manager(session, deal_id, manager)
        if not deal:
            sent = await message.answer("Сделка не найдена")
            await remember_message(state, sent.message_id)
            return
        await log_interaction(
            session,
            deal,
            interaction_type=interaction_type,
            ai_advice=data.get("interaction_advice"),
            manager_summary=message.text or "",
        )

    await state.set_state(BotStates.idle)
    remaining = {
        key: value
        for key, value in data.items()
        if key not in {"interaction_type", "interaction_advice"}
    }
    await state.set_data(remaining)
    sent = await message.answer("✅ Взаимодействие сохранено")
    await remember_message(state, sent.message_id)


@router.callback_query(F.data.startswith("reminder:"))
async def reminder_preset(callback: CallbackQuery, state: FSMContext) -> None:
    preset = callback.data.split(":", 1)[1]
    data = await state.get_data()
    deal_id = data.get("active_deal_id")

    if preset == "calendar":
        await callback.answer("Введите дату вручную", show_alert=True)
        return

    target_time = datetime.utcnow()
    if preset == "+1h":
        target_time += timedelta(hours=1)
    elif preset == "next_morning":
        tomorrow = target_time + timedelta(days=1)
        target_time = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 0)

    await _create_reminder(callback.from_user.id, callback.from_user.full_name, deal_id, target_time)
    sent = await callback.message.answer(f"Напоминание на {target_time:%Y-%m-%d %H:%M} сохранено")
    await remember_message(state, sent.message_id)
    await state.set_state(BotStates.idle)
    await callback.answer()


async def _create_reminder(user_id: int, full_name: str, deal_id: int, remind_at: datetime) -> None:
    async with get_session() as session:
        manager = await ensure_manager(session, user_id, name=full_name)
        deal = await _load_deal_for_manager(session, deal_id, manager)
        if not deal:
            return
        await create_reminder(session, deal, remind_at=remind_at)


@router.message(BotStates.entering_reminder_time, F.text)
async def reminder_manual(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    deal_id = data.get("active_deal_id")
    try:
        remind_at = datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
    except Exception:
        sent = await message.answer("Не удалось распознать дату. Используйте формат YYYY-MM-DD HH:MM")
        await remember_message(state, sent.message_id)
        return

    await _create_reminder(message.from_user.id, message.from_user.full_name, deal_id, remind_at)
    await state.set_state(BotStates.idle)
    sent = await message.answer(f"Напоминание на {remind_at:%Y-%m-%d %H:%M} сохранено")
    await remember_message(state, sent.message_id)


@router.callback_query(F.data.startswith("status:"))
async def change_status(callback: CallbackQuery, state: FSMContext) -> None:
    new_status = callback.data.split(":", 1)[1]
    data = await state.get_data()
    deal_id = data.get("active_deal_id")

    async with get_session() as session:
        manager = await ensure_manager(
            session, callback.from_user.id, name=callback.from_user.full_name
        )
        deal = await _load_deal_for_manager(session, deal_id, manager)
        if not deal:
            await callback.answer("Сделка не найдена", show_alert=True)
            return
        await change_deal_status(session, deal, new_status)

    sent = await callback.message.answer(f"Статус обновлён на '{new_status}'")
    await remember_message(state, sent.message_id)
    await callback.answer()


@router.message(F.text.regexp(r"^(\d+)-\s*(.+)$"))
async def handle_item_question(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    deal_id = data.get("active_deal_id")
    if not deal_id:
        return

    match = re.match(r"^(\d+)-\s*(.+)$", message.text)
    if not match:
        return

    line_no = int(match.group(1))
    question = match.group(2)

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        deal = await _load_deal_for_manager(session, deal_id, manager)
        if not deal:
            sent = await message.answer("Сделка не найдена")
            await remember_message(state, sent.message_id)
            return
        try:
            answer = await answer_item_question(deal, line_no, question)
        except ValueError as exc:
            sent = await message.answer(str(exc))
            await remember_message(state, sent.message_id)
            return

    sent = await message.answer(answer)
    await remember_message(state, sent.message_id)

