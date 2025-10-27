"""Start command handler."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(
        (
            "👋 Привет! Я CRM-бот для менеджеров.\n"
            "Отправьте номер телефона клиента, чтобы начать работу."
        )
    )
