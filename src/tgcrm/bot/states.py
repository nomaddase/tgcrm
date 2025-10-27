"""Finite state machine definitions for the Telegram bot."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    idle = State()
    entering_client_phone = State()
    entering_new_client_name = State()
    entering_new_client_city = State()
    entering_new_client_demand = State()
    selecting_deal = State()
    awaiting_pdf = State()
    choosing_interaction = State()
    entering_reminder_time = State()
    settings_auth = State()
    settings_menu = State()


__all__ = ["BotStates"]
