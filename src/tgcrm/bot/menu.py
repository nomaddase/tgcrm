"""Utility helpers for rendering the textual main menu for the bot."""
from __future__ import annotations

MAIN_MENU_ITEMS = [
    "Добавить клиента (пришлите номер телефона)",
    "Найти клиента (введите последние 4 цифры)",
    "Мои сделки",
    "Добавить напоминание",
    "Настройки",
]

DEAL_CONTEXT_ITEMS = [
    "Добавить взаимодействие (например: 'позвонил клиенту')",
    "Загрузить счёт (отправьте PDF)",
    "Изменить статус (например: 'переведи сделку в оплачено')",
    "Вернуться в главное меню",
]


def render_main_menu() -> str:
    """Return the formatted main menu string."""

    lines = ["📋 Главное меню:"]
    lines.extend(f"• {item}" for item in MAIN_MENU_ITEMS)
    lines.append("")
    lines.append("Чтобы выполнить действие, просто опишите его естественным языком.")
    return "\n".join(lines)


def render_deal_context() -> str:
    """Return the contextual actions available for the active deal."""

    lines = ["🔧 Доступные действия по сделке:"]
    lines.extend(f"• {item}" for item in DEAL_CONTEXT_ITEMS)
    return "\n".join(lines)


__all__ = ["DEAL_CONTEXT_ITEMS", "MAIN_MENU_ITEMS", "render_deal_context", "render_main_menu"]
