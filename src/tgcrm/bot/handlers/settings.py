"""Handlers for the settings panel."""
from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from tgcrm.bot.keyboards.main import MainMenuButtons, settings_menu
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import purge_history, remember_message
from tgcrm.config import get_settings
from tgcrm.db.session import get_session
from tgcrm.services.deals import ensure_manager
from tgcrm.services.settings import get_setting, set_setting

router = Router()


async def _fetch_password() -> str:
    async with get_session() as session:
        stored = await get_setting(session, "supervisor_password")
    if stored:
        return stored
    return get_settings().behaviour.supervisor_password


async def _authorize(message: Message, state: FSMContext, *, context: str = "settings") -> None:
    await purge_history(message.bot, message.chat.id, state)
    await state.set_state(BotStates.settings_auth)
    await state.update_data({"auth_context": context})
    sent = await message.answer("Введите пароль для доступа к настройкам")
    await remember_message(state, sent.message_id)


@router.message(Command("settings"))
async def open_settings_command(message: Message, state: FSMContext) -> None:
    await _authorize(message, state)


@router.message(F.text == MainMenuButtons.SETTINGS)
async def open_settings_menu(message: Message, state: FSMContext) -> None:
    await _authorize(message, state)


@router.message(BotStates.settings_auth, F.text)
async def check_password(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    password = await _fetch_password()
    if (message.text or "").strip() != password:
        sent = await message.answer("❌ Неверный пароль. Попробуйте снова.")
        await remember_message(state, sent.message_id)
        return

    if data.get("auth_context") == "supervisor":
        await state.set_state(BotStates.idle)
        remaining = {key: value for key, value in data.items() if key != "auth_context"}
        await state.set_data(remaining)
        from tgcrm.bot.handlers.supervisor import send_overview  # local import to avoid cycle

        await send_overview(message, state)
        return

    await state.set_state(BotStates.settings_menu)
    await state.update_data({"settings_authorized": True, "auth_context": None})
    sent = await message.answer("Пароль принят. Выберите параметр для изменения.", reply_markup=settings_menu())
    await remember_message(state, sent.message_id)


@router.callback_query(BotStates.settings_menu, F.data.startswith("settings:"))
async def handle_settings_choice(callback: CallbackQuery, state: FSMContext) -> None:
    _, action = callback.data.split(":", 1)
    prompts = {
        "hours": "Введите рабочее время в формате HH:MM-HH:MM",
        "lunch": "Введите время обеда в формате HH:MM-HH:MM",
        "openai": "Введите новый OpenAI API ключ",
        "password": "Введите новый пароль для доступа",
    }
    prompt = prompts[action]
    await state.update_data({"settings_action": action})
    sent = await callback.message.answer(prompt)
    await remember_message(state, sent.message_id)
    await callback.answer()


@router.message(BotStates.settings_menu, F.text)
async def apply_setting(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    action = data.get("settings_action")
    if not action:
        return

    async with get_session() as session:
        await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        if action in {"hours", "lunch"}:
            match = re.match(r"^(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})$", message.text.strip())
            if not match:
                sent = await message.answer("Некорректный формат. Используйте HH:MM-HH:MM")
                await remember_message(state, sent.message_id)
                return
            start, end = match.groups()
            if action == "hours":
                await set_setting(session, "workday_start", start)
                await set_setting(session, "workday_end", end)
            else:
                await set_setting(session, "lunch_start", start)
                await set_setting(session, "lunch_end", end)
        elif action == "openai":
            await set_setting(session, "openai_api_key", message.text.strip())
        elif action == "password":
            await set_setting(session, "supervisor_password", message.text.strip())

    sent = await message.answer("Настройка обновлена")
    await remember_message(state, sent.message_id)
    await state.update_data({"settings_action": None})
