"""Handlers for supervisor level operations."""
from __future__ import annotations

import json

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import func, select

from tgcrm.bot.menu import render_main_menu
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import remember_message
from tgcrm.db.models import Deal
from tgcrm.db.session import get_session
from tgcrm.services.ai_assistant import generate_supervisor_summary
from tgcrm.services.deals import ensure_manager

from .settings import _authorize


router = Router()


async def start_supervisor_report(message: Message, state: FSMContext) -> None:
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

    snapshot = {
        "total_deals": sum(row[1] for row in rows),
        "statuses": {status: {"count": count, "amount": float(total or 0)} for status, count, total in rows},
    }
    analysis = await generate_supervisor_summary(json.dumps(snapshot, ensure_ascii=False))

    lines = ["📈 AI-отчёт для руководителя", analysis, "", render_main_menu()]
    sent = await message.answer("\n".join(lines))
    await remember_message(state, sent.message_id)
    await state.set_state(BotStates.idle)


__all__ = ["router", "send_overview", "start_supervisor_report"]
