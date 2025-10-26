"""Handlers for the settings panel."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from tgcrm.config import get_settings

router = Router()


@router.message(Command("settings"))
async def open_settings(message: Message) -> None:
    await message.answer(
        "Настройки доступны после ввода пароля.\n"
        "Отправьте пароль одним сообщением, чтобы продолжить."
    )


@router.message(F.text)
async def check_password(message: Message) -> None:
    settings = get_settings()
    if message.text != settings.behaviour.supervisor_password:
        await message.answer("❌ Неверный пароль. Попробуйте снова.")
        return

    await message.answer(
        "✅ Пароль принят. Вы можете обновить рабочее время, пароль доступа и ключ OpenAI через БД."
    )
