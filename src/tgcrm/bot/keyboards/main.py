"""Keyboard builders for the CRM bot."""
from __future__ import annotations

from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup)

from tgcrm.db.statuses import DealStatus


class MainMenuButtons:
    SEARCH_CLIENT = "Поиск клиента по номеру"
    SEARCH_BY_SUFFIX = "Последние 4 цифры"
    ATTACH_INVOICE = "Приложить счёт"
    INTERACTION = "Взаимодействие"
    REMINDER = "Напоминание"
    SETTINGS = "Настройки"
    ALL_DEALS = "Все сделки"


class InteractionButtons:
    MESSAGE = "Сообщение"
    CALL = "Звонок"
    EMAIL = "Электронная почта"


def main_menu() -> ReplyKeyboardMarkup:
    """Return the main reply keyboard markup."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MainMenuButtons.SEARCH_CLIENT)],
            [KeyboardButton(text=MainMenuButtons.SEARCH_BY_SUFFIX)],
            [KeyboardButton(text=MainMenuButtons.ATTACH_INVOICE)],
            [KeyboardButton(text=MainMenuButtons.INTERACTION)],
            [KeyboardButton(text=MainMenuButtons.REMINDER)],
            [KeyboardButton(text=MainMenuButtons.SETTINGS)],
            [KeyboardButton(text=MainMenuButtons.ALL_DEALS)],
        ],
        resize_keyboard=True,
        selective=True,
    )


def interaction_menu() -> InlineKeyboardMarkup:
    """Return inline keyboard for interaction types."""

    buttons = [
        [
            InlineKeyboardButton(text=InteractionButtons.MESSAGE, callback_data="interaction:message"),
        ],
        [
            InlineKeyboardButton(text=InteractionButtons.CALL, callback_data="interaction:call"),
        ],
        [
            InlineKeyboardButton(text=InteractionButtons.EMAIL, callback_data="interaction:email"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def deal_status_menu() -> InlineKeyboardMarkup:
    """Return inline keyboard for deal statuses."""

    buttons = []
    for status in DealStatus:
        buttons.append([InlineKeyboardButton(text=status.value, callback_data=f"status:{status.value}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def deal_actions_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Приложить счёт", callback_data="deal:attach_invoice")],
        [InlineKeyboardButton(text="Добавить взаимодействие", callback_data="deal:interaction")],
        [InlineKeyboardButton(text="Добавить напоминание", callback_data="deal:reminder")],
        [InlineKeyboardButton(text="Изменить статус сделки", callback_data="deal:status")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_menu() -> InlineKeyboardMarkup:
    """Return inline keyboard for settings options."""

    buttons = [
        [InlineKeyboardButton(text="Рабочее время", callback_data="settings:hours")],
        [InlineKeyboardButton(text="Обед", callback_data="settings:lunch")],
        [InlineKeyboardButton(text="OpenAI ключ", callback_data="settings:openai")],
        [InlineKeyboardButton(text="Пароль", callback_data="settings:password")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def reminder_presets() -> InlineKeyboardMarkup:
    """Return inline keyboard with reminder presets."""

    buttons = [
        [
            InlineKeyboardButton(text="Через 1 час", callback_data="reminder:+1h"),
            InlineKeyboardButton(text="Завтра утром", callback_data="reminder:next_morning"),
        ],
        [
            InlineKeyboardButton(text="Выбрать дату", callback_data="reminder:calendar"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


__all__ = [
    "InteractionButtons",
    "MainMenuButtons",
    "deal_actions_menu",
    "deal_status_menu",
    "interaction_menu",
    "main_menu",
    "reminder_presets",
    "settings_menu",
]
