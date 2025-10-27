"""Handlers for the settings panel."""
from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tgcrm.bot.menu import render_main_menu
from tgcrm.bot.states import BotStates
from tgcrm.bot.utils.history import delete_message_safe, purge_history, remember_message
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
    await delete_message_safe(message)
    await state.set_state(BotStates.settings_auth)
    await state.update_data({"auth_context": context})
    sent = await message.answer("Введите пароль для доступа")
    await remember_message(state, sent.message_id)


async def start_settings_flow(message: Message, state: FSMContext) -> None:
    await _authorize(message, state)


@router.message(Command("settings"))
async def open_settings_command(message: Message, state: FSMContext) -> None:
    await start_settings_flow(message, state)


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
    sent = await message.answer(
        "Пароль принят. Отправьте одну из команд: \n"
        "• рабочее время 09:00-18:00\n"
        "• обед 13:00-14:00\n"
        "• openai sk-...\n"
        "• пароль НовыйПароль"
    )
    await remember_message(state, sent.message_id)


def _parse_range(text: str) -> tuple[str, str] | None:
    match = re.match(r"^(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})$", text)
    if not match:
        return None
    return match.group(1), match.group(2)


@router.message(BotStates.settings_menu, F.text)
async def apply_setting(message: Message, state: FSMContext) -> None:
    await delete_message_safe(message)
    text = (message.text or "").strip()
    lowered = text.lower()

    async with get_session() as session:
        await ensure_manager(session, message.from_user.id, name=message.from_user.full_name)
        if lowered.startswith("рабочее время"):
            value = text.split(" ", 2)[-1]
            parsed = _parse_range(value)
            if not parsed:
                sent = await message.answer("Используйте формат HH:MM-HH:MM для рабочего времени.")
                await remember_message(state, sent.message_id)
                return
            start, end = parsed
            await set_setting(session, "workday_start", start)
            await set_setting(session, "workday_end", end)
        elif lowered.startswith("обед"):
            value = text.split(" ", 1)[-1]
            parsed = _parse_range(value)
            if not parsed:
                sent = await message.answer("Используйте формат HH:MM-HH:MM для обеда.")
                await remember_message(state, sent.message_id)
                return
            start, end = parsed
            await set_setting(session, "lunch_start", start)
            await set_setting(session, "lunch_end", end)
        elif lowered.startswith("openai"):
            token = text.split(" ", 1)[-1].strip()
            await set_setting(session, "openai_api_key", token)
        elif lowered.startswith("пароль"):
            new_password = text.split(" ", 1)[-1].strip()
            await set_setting(session, "supervisor_password", new_password)
        else:
            sent = await message.answer("Неизвестная команда. Попробуйте снова.")
            await remember_message(state, sent.message_id)
            return

    sent = await message.answer(f"Настройка обновлена.\n\n{render_main_menu()}")
    await remember_message(state, sent.message_id)
    await state.set_state(BotStates.idle)


__all__ = ["_authorize", "router", "start_settings_flow"]
