"""Utilities for managing bot message history."""
from __future__ import annotations

from typing import Iterable, List

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


HISTORY_KEY = "sent_messages"


async def remember_message(state: FSMContext, message_id: int) -> None:
    data = await state.get_data()
    history: List[int] = list(data.get(HISTORY_KEY, []))
    history.append(message_id)
    await state.update_data({HISTORY_KEY: history[-20:]})


async def purge_history(bot: Bot, chat_id: int, state: FSMContext) -> None:
    data = await state.get_data()
    history: Iterable[int] = data.get(HISTORY_KEY, [])
    for message_id in history:
        try:
            await bot.delete_message(chat_id, message_id)
        except TelegramBadRequest:
            continue
    await state.update_data({HISTORY_KEY: []})


async def delete_previous(bot: Bot, chat_id: int, message_id: int) -> None:
    target = message_id - 1
    try:
        await bot.delete_message(chat_id, target)
    except TelegramBadRequest:
        return


async def delete_message_safe(message: Message) -> None:
    """Attempt to delete a message, ignoring Telegram errors."""

    try:
        await message.delete()
    except TelegramBadRequest:
        return


__all__ = ["delete_message_safe", "delete_previous", "purge_history", "remember_message"]
