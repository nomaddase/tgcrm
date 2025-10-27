"""Handlers for supervisor level operations."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import func, select

from tgcrm.bot.handlers.settings import _authorize
from tgcrm.bot.keyboards.main import MainMenuButtons
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import remember_message
from tgcrm.db.models import Deal
from tgcrm.db.session import get_session
from tgcrm.services.deals import ensure_manager


router = Router()


@router.message(F.text == MainMenuButtons.ALL_DEALS)
async def supervisor_overview(message: Message, state: FSMContext) -> None:
    await _authorize(message, state, context="supervisor")


async def send_overview(message: Message, state: FSMContext) -> None:
    async with get_session() as session:
        await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        query = select(
            Deal.status,
            func.count(Deal.id),
            func.coalesce(func.sum(Deal.amount), 0),
        ).group_by(Deal.status)
        result = await session.execute(query)
        rows = result.all()

    total_count = sum(row[1] for row in rows)
    lines = ["📊 Сводка по всем сделкам"]
    for status, count, total in rows:
        lines.append(f"{status}: {count} шт. | Сумма: {float(total or 0):.2f}")
    lines.append(f"Всего сделок: {total_count}")

    sent = await message.answer("\n".join(lines))
    await remember_message(state, sent.message_id)
    await state.set_state(BotStates.idle)


__all__ = ["router", "send_overview"]
