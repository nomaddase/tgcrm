"""Handlers related to deal selection and AI-assisted actions."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Document, Message
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from tgcrm.bot.menu import render_deal_context, render_main_menu
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import delete_message_safe, purge_history, remember_message
from tgcrm.db.models import Deal, Manager
from tgcrm.db.session import get_session
from tgcrm.services.ai_assistant import (
    build_deal_advice,
    build_reminder_tip,
    build_status_tip,
    summarize_invoice,
)
from tgcrm.services.deals import (
    attach_invoice,
    change_deal_status,
    create_reminder,
    ensure_manager,
    get_active_deal_by_phone_suffix,
    log_interaction,
)
from tgcrm.services.pdf_processing import extract_text_from_pdf, parse_invoice


INVOICE_STORAGE = Path("var/invoices")
INVOICE_STORAGE.mkdir(parents=True, exist_ok=True)

router = Router()


async def _load_deal_for_manager(session, deal_id: int, manager: Manager) -> Deal | None:
    query = (
        select(Deal)
        .options(
            joinedload(Deal.client),
            joinedload(Deal.interactions),
            joinedload(Deal.invoices).joinedload("items"),
        )
        .where(Deal.id == deal_id, Deal.manager_id == manager.id)
    )
    result = await session.execute(query)
    return result.scalars().first()


def _format_history(deal: Deal) -> str:
    interactions = sorted(deal.interactions, key=lambda item: item.created_at or datetime.min)
    if not interactions:
        return "Пока нет взаимодействий"
    lines = []
    for interaction in interactions[-5:]:
        lines.append(
            f"[{interaction.created_at:%Y-%m-%d %H:%M}] {interaction.type}: {interaction.manager_summary}"
        )
    return "\n".join(lines)


async def select_deal_by_suffix(message: Message, state: FSMContext, suffix: str) -> None:
    await purge_history(message.bot, message.chat.id, state)
    await delete_message_safe(message)

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        deal = await get_active_deal_by_phone_suffix(session, phone_suffix=suffix, manager=manager)
        if not deal:
            sent = await message.answer(
                "Не удалось найти сделку по этим цифрам. Убедитесь, что клиент относится к вам."
            )
            await remember_message(state, sent.message_id)
            return

        history = _format_history(deal)
        advice = await build_deal_advice(history, deal.status)
        summary = (
            f"👤 {deal.client.name or deal.client.phone_number}\n"
            f"Статус: {deal.status}\n"
            f"Рекомендация: {advice}"
        )

    await state.update_data({"active_deal_id": deal.id})
    response = f"{summary}\n\n{render_deal_context()}"
    sent = await message.answer(response)
    await remember_message(state, sent.message_id)


async def _get_active_deal(state: FSMContext) -> int | None:
    data = await state.get_data()
    return data.get("active_deal_id")


async def handle_interaction(message: Message, state: FSMContext, summary: str) -> None:
    await purge_history(message.bot, message.chat.id, state)
    await delete_message_safe(message)
    deal_id = await _get_active_deal(state)
    if not deal_id:
        sent = await message.answer("Сначала выберите сделку по последним 4 цифрам клиента.")
        await remember_message(state, sent.message_id)
        return

    interaction_type = "взаимодействие"
    lowered = summary.lower()
    if "позвон" in lowered or "звон" in lowered:
        interaction_type = "звонок"
    elif "письм" in lowered or "email" in lowered:
        interaction_type = "письмо"
    elif "whatsapp" in lowered or "напис" in lowered:
        interaction_type = "сообщение"

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        deal = await _load_deal_for_manager(session, deal_id, manager)
        if not deal:
            sent = await message.answer("Сделка не найдена. Повторите поиск клиента.")
            await remember_message(state, sent.message_id)
            return
        await log_interaction(
            session,
            deal,
            interaction_type=interaction_type,
            ai_advice=None,
            manager_summary=summary,
        )
        await session.refresh(deal, attribute_names=["last_interaction_at"])
        history = _format_history(deal)
        advice = await build_deal_advice(history, deal.status)

    response = (
        "✅ Взаимодействие сохранено.\n"
        f"Совет: {advice}\n\n{render_main_menu()}"
    )
    sent = await message.answer(response)
    await remember_message(state, sent.message_id)


def _parse_reminder_time(text: str) -> datetime | None:
    lowered = text.lower()
    now = datetime.now(timezone.utc)
    match = re.search(r"через\s+(\d+)\s*(час|минут|дн)", lowered)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("час"):
            return now + timedelta(hours=value)
        if unit.startswith("минут"):
            return now + timedelta(minutes=value)
        return now + timedelta(days=value)
    if "завтра" in lowered:
        return (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    return None


async def handle_reminder(message: Message, state: FSMContext, request: str) -> None:
    await purge_history(message.bot, message.chat.id, state)
    await delete_message_safe(message)
    deal_id = await _get_active_deal(state)
    if not deal_id:
        sent = await message.answer("Сначала выберите сделку, чтобы привязать напоминание.")
        await remember_message(state, sent.message_id)
        return

    remind_at = _parse_reminder_time(request)
    if not remind_at:
        sent = await message.answer(
            "Не понял время напоминания. Укажите, например: 'напомни через 2 часа позвонить клиенту'."
        )
        await remember_message(state, sent.message_id)
        return

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        deal = await _load_deal_for_manager(session, deal_id, manager)
        if not deal:
            sent = await message.answer("Сделка не найдена. Повторите поиск клиента.")
            await remember_message(state, sent.message_id)
            return
        await create_reminder(session, deal, remind_at=remind_at)
        history = _format_history(deal)
        tip = await build_reminder_tip(request)

    response = (
        "⏰ Напоминание создано.\n"
        f"Совет: {tip}\n\n{render_main_menu()}"
    )
    sent = await message.answer(response)
    await remember_message(state, sent.message_id)


async def handle_status_change(message: Message, state: FSMContext, status: str) -> None:
    await purge_history(message.bot, message.chat.id, state)
    await delete_message_safe(message)
    deal_id = await _get_active_deal(state)
    if not deal_id:
        sent = await message.answer("Сначала активируйте сделку, указав 4 последние цифры телефона.")
        await remember_message(state, sent.message_id)
        return

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        deal = await _load_deal_for_manager(session, deal_id, manager)
        if not deal:
            sent = await message.answer("Сделка не найдена. Повторите поиск клиента.")
            await remember_message(state, sent.message_id)
            return
        await change_deal_status(session, deal, status)
        overview = _format_history(deal)
        tip = await build_status_tip(deal.status, overview)

    response = (
        "📌 Статус сделки обновлён.\n"
        f"Совет: {tip}\n\n{render_main_menu()}"
    )
    sent = await message.answer(response)
    await remember_message(state, sent.message_id)


async def list_manager_deals(message: Message, state: FSMContext) -> None:
    await purge_history(message.bot, message.chat.id, state)
    await delete_message_safe(message)

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        query = (
            select(Deal.status, func.count(Deal.id))
            .where(Deal.manager_id == manager.id)
            .group_by(Deal.status)
        )
        result = await session.execute(query)
        rows = result.all()

    if not rows:
        summary = "У вас пока нет сделок."
    else:
        summary_lines = ["📊 Ваши сделки по статусам:"]
        for status, count in rows:
            summary_lines.append(f"• {status}: {count}")
        summary = "\n".join(summary_lines)

    sent = await message.answer(f"{summary}\n\n{render_main_menu()}")
    await remember_message(state, sent.message_id)


@router.message(BotStates.awaiting_pdf)
async def handle_invoice_upload(message: Message, state: FSMContext) -> None:
    await purge_history(message.bot, message.chat.id, state)
    await delete_message_safe(message)
    document: Document | None = message.document
    if document is None:
        sent = await message.answer("Пришлите PDF-файл счёта.")
        await remember_message(state, sent.message_id)
        return

    data = await state.get_data()
    deal_id = data.get("active_deal_id")
    if not deal_id:
        sent = await message.answer("Сначала выберите сделку для счёта.")
        await remember_message(state, sent.message_id)
        return

    if not document.file_name or not document.file_name.lower().endswith(".pdf"):
        sent = await message.answer("Нужен PDF-файл. Попробуйте снова.")
        await remember_message(state, sent.message_id)
        return

    destination = INVOICE_STORAGE / f"deal_{deal_id}_{document.file_unique_id}.pdf"
    await message.bot.download(document, destination=destination)
    invoice_data = parse_invoice(destination)
    raw_text = extract_text_from_pdf(destination)

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        deal = await _load_deal_for_manager(session, deal_id, manager)
        if not deal:
            sent = await message.answer("Сделка не найдена. Повторите поиск клиента.")
            await remember_message(state, sent.message_id)
            return
        invoice = await attach_invoice(session, deal, invoice_data, str(destination))
        await session.refresh(deal, attribute_names=["status", "amount"])
        analysis = await summarize_invoice(raw_text)

    response = (
        "✅ Счёт загружен и добавлен к сделке.\n"
        f"Сумма: {float(invoice.total_amount):.2f}. Позиции: {len(invoice_data.line_items)}.\n"
        f"Анализ: {analysis}\n\n{render_main_menu()}"
    )
    await state.set_state(BotStates.idle)
    sent = await message.answer(response)
    await remember_message(state, sent.message_id)


__all__ = [
    "handle_interaction",
    "handle_invoice_upload",
    "handle_reminder",
    "handle_status_change",
    "list_manager_deals",
    "router",
    "select_deal_by_suffix",
]

