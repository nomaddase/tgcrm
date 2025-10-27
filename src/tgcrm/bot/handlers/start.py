"""Start command handler."""
from __future__ import annotations

from contextlib import suppress

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tgcrm.bot.menu import render_main_menu
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import delete_previous, purge_history, remember_message
from tgcrm.services.ai_assistant import AI_PROMPTS, get_ai_advice

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    await purge_history(message.bot, message.chat.id, state)
    await state.clear()
    await state.set_state(BotStates.idle)

    await delete_previous(message.bot, message.chat.id, message.message_id)
    tip = ""
    with suppress(Exception):
        tip = await get_ai_advice(AI_PROMPTS["welcome_message"])

    lines = ["👋 Привет! Я CRM-бот для менеджеров."]
    if tip:
        lines.append(f"🤖 Совет дня: {tip}")
    lines.append(render_main_menu())
    sent = await message.answer("\n".join(lines))
    await remember_message(state, sent.message_id)
