"""Handlers for client lookup and AI-assisted creation flows."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from tgcrm.bot.menu import render_main_menu
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import delete_message_safe, purge_history, remember_message
from tgcrm.db.models import Client, Deal
from tgcrm.db.session import get_session
from tgcrm.services.ai_assistant import generate_followup_message, summarize_client_profile
from tgcrm.services.deals import (
    create_deal_for_manager,
    ensure_manager,
    get_or_create_client,
    log_interaction,
)
from tgcrm.services.phones import PhoneValidationError, normalize_kz_phone


router = Router()


async def start_client_creation(message: Message, state: FSMContext, phone: str) -> None:
    """Entry point for the AI assisted client creation flow."""

    await purge_history(message.bot, message.chat.id, state)
    await delete_message_safe(message)

    try:
        normalized = normalize_kz_phone(phone)
    except PhoneValidationError:
        sent = await message.answer("❌ Неверный номер. Пришлите его в формате +7XXXXXXXXXX")
        await remember_message(state, sent.message_id)
        return

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        query = select(Client).where(Client.phone_number == normalized)
        result = await session.execute(query)
        client = result.scalar_one_or_none()

        if client:
            deals_result = await session.execute(
                select(Deal).where(Deal.client_id == client.id, Deal.manager_id == manager.id)
            )
            deals = deals_result.scalars().all()
            deals_info = ", ".join(f"#{deal.id} ({deal.status})" for deal in deals) or "нет сделок"
            summary = (
                f"ℹ️ Клиент уже в базе: {client.name or 'Без имени'}, {client.city or 'город не указан'}.\n"
                f"Ваши сделки: {deals_info}."
            )
            sent = await message.answer(f"{summary}\n\n{render_main_menu()}")
            await remember_message(state, sent.message_id)
            await state.set_state(BotStates.idle)
            return

    await state.set_state(BotStates.entering_new_client_name)
    await state.update_data({"new_client_phone": normalized})
    sent = await message.answer("Клиент не найден. Как зовут клиента?")
    await remember_message(state, sent.message_id)


@router.message(BotStates.entering_new_client_name)
async def handle_new_client_name(message: Message, state: FSMContext) -> None:
    await delete_message_safe(message)
    await state.update_data({"new_client_name": (message.text or "").strip()})
    await state.set_state(BotStates.entering_new_client_city)
    sent = await message.answer("Укажите город клиента")
    await remember_message(state, sent.message_id)


@router.message(BotStates.entering_new_client_city)
async def handle_new_client_city(message: Message, state: FSMContext) -> None:
    await delete_message_safe(message)
    await state.update_data({"new_client_city": (message.text or "").strip()})
    await state.set_state(BotStates.entering_new_client_demand)
    sent = await message.answer("Что интересует клиента?")
    await remember_message(state, sent.message_id)


@router.message(BotStates.entering_new_client_demand)
async def handle_new_client_demand(message: Message, state: FSMContext) -> None:
    await delete_message_safe(message)
    data = await state.get_data()
    demand = (message.text or "").strip()
    phone = data.get("new_client_phone")
    name = data.get("new_client_name")
    city = data.get("new_client_city")

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        client = await get_or_create_client(session, phone_number=phone, name=name, city=city)
        deal = await create_deal_for_manager(session, client, manager)
        await log_interaction(
            session,
            deal,
            interaction_type="первичный спрос",
            ai_advice=None,
            manager_summary=demand,
        )

    summary = await summarize_client_profile({"name": name, "city": city, "interest": demand})
    advice_history = [
        {
            "time": "",
            "type": "первичный спрос",
            "summary": demand or "интерес не указан",
        }
    ]
    advice = await generate_followup_message(advice_history, "Новый клиент")
    response = (
        "✅ Клиент создан и сделка закреплена за вами.\n"
        f"{summary}\n\nСовет: {advice}\n\n{render_main_menu()}"
    )
    await state.set_state(BotStates.idle)
    await state.set_data({})
    sent = await message.answer(response)
    await remember_message(state, sent.message_id)


__all__ = ["router", "start_client_creation"]
