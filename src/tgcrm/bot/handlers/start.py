"""Start command handler."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()

# Собираем основное меню (пример)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📞 Найти клиента")],
        [KeyboardButton(text="🕒 Мои задачи"), KeyboardButton(text="📊 Отчёт")],
        [KeyboardButton(text="⚙️ Настройки")],
    ],
    resize_keyboard=True
)

@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(
        (
            "👋 Привет! Я CRM-бот для менеджеров.\n"
            "Выберите действие ниже 👇"
        ),
        reply_markup=main_menu
    )
