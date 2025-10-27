"""Start command handler."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tgcrm.bot.keyboards.main import main_menu
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import delete_previous, purge_history, remember_message

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    await purge_history(message.bot, message.chat.id, state)
    await state.clear()
    await state.set_state(BotStates.idle)

    await delete_previous(message.bot, message.chat.id, message.message_id)
    sent = await message.answer(
        "👋 Привет! Я CRM-бот для менеджеров.\nВыберите действие ниже 👇",
        reply_markup=main_menu(),
    )
    await remember_message(state, sent.message_id)
