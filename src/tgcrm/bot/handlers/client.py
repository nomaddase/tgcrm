"""Handlers for client lookup and creation flows."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from tgcrm.bot.keyboards.main import MainMenuButtons
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import purge_history, remember_message
from tgcrm.db.models import Client, Deal
from tgcrm.db.session import get_session
from tgcrm.services.deals import (
    create_deal_for_manager,
    ensure_manager,
    get_or_create_client,
    log_interaction,
)
from tgcrm.services.phones import PhoneValidationError, normalize_kz_phone


router = Router()


@router.message(F.text == MainMenuButtons.SEARCH_CLIENT)
async def request_client_phone(message: Message, state: FSMContext) -> None:
    await purge_history(message.bot, message.chat.id, state)
    await state.set_state(BotStates.entering_client_phone)
    sent = await message.answer("Введите номер телефона клиента (Казахстан, +7XXXXXXXXXX)")
    await remember_message(state, sent.message_id)


@router.message(BotStates.entering_client_phone, F.text)
async def handle_client_phone(message: Message, state: FSMContext) -> None:
    try:
        normalized = normalize_kz_phone(message.text or "")
    except PhoneValidationError:
        sent = await message.answer("❌ Неверный формат. Укажите номер в виде +7XXXXXXXXXX")
        await remember_message(state, sent.message_id)
        return

    async with get_session() as session:
        manager = await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        client_result = await session.execute(select(Client).where(Client.phone_number == normalized))
        client = client_result.scalar_one_or_none()

        if client:
            deals_result = await session.execute(
                select(Deal).where(Deal.client_id == client.id, Deal.manager_id == manager.id)
            )
            deals = deals_result.scalars().all()
            deals_info = ", ".join(f"#{deal.id} ({deal.status})" for deal in deals)
            summary = (
                f"Клиент найден: {client.name or 'Без имени'}, город {client.city or 'не указан'}."
            )
            if deals_info:
                summary += f"\nВаши сделки: {deals_info}"
            else:
                summary += "\nУ вас пока нет сделок с этим клиентом."
            sent = await message.answer(summary)
            await remember_message(state, sent.message_id)
            await state.set_state(BotStates.idle)
            return

    await state.update_data({"new_client_phone": normalized})
    await state.set_state(BotStates.entering_new_client_name)
    sent = await message.answer("Клиент не найден. Укажите имя клиента")
    await remember_message(state, sent.message_id)


@router.message(BotStates.entering_new_client_name, F.text)
async def handle_new_client_name(message: Message, state: FSMContext) -> None:
    await state.update_data({"new_client_name": (message.text or "").strip()})
    await state.set_state(BotStates.entering_new_client_city)
    sent = await message.answer("Введите город клиента")
    await remember_message(state, sent.message_id)


@router.message(BotStates.entering_new_client_city, F.text)
async def handle_new_client_city(message: Message, state: FSMContext) -> None:
    await state.update_data({"new_client_city": (message.text or "").strip()})
    await state.set_state(BotStates.entering_new_client_demand)
    sent = await message.answer("Опишите первичный запрос клиента")
    await remember_message(state, sent.message_id)


@router.message(BotStates.entering_new_client_demand, F.text)
async def handle_new_client_demand(message: Message, state: FSMContext) -> None:
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

    await state.set_state(BotStates.idle)
    await state.set_data({})
    sent = await message.answer(
        (
            "✅ Клиент создан и привязан к вам.\n"
            f"Имя: {name or 'не указано'}\nГород: {city or 'не указан'}\n"
            "Создана сделка в статусе 'Новый'."
        )
    )
    await remember_message(state, sent.message_id)
