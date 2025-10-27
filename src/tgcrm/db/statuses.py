"""Constants and helpers for deal status management."""
from __future__ import annotations

from enum import Enum


class DealStatus(str, Enum):
    """Allowed statuses for deals."""

    NEW = "Новый"
    INVOICE_SENT = "отправлен счёт"
    PAYMENT_PENDING = "ожидается оплата"
    PAID = "оплачен"
    CANCELLED = "отменен"
    LONG_TERM = "долгосрочный"


TERMINAL_STATUSES = {
    DealStatus.PAID,
    DealStatus.CANCELLED,
    DealStatus.LONG_TERM,
}


VALID_TRANSITIONS: dict[DealStatus, set[DealStatus]] = {
    DealStatus.NEW: {
        DealStatus.NEW,
        DealStatus.INVOICE_SENT,
        DealStatus.PAYMENT_PENDING,
        DealStatus.CANCELLED,
        DealStatus.LONG_TERM,
    },
    DealStatus.INVOICE_SENT: {
        DealStatus.INVOICE_SENT,
        DealStatus.PAYMENT_PENDING,
        DealStatus.PAID,
        DealStatus.CANCELLED,
        DealStatus.LONG_TERM,
    },
    DealStatus.PAYMENT_PENDING: {
        DealStatus.PAYMENT_PENDING,
        DealStatus.PAID,
        DealStatus.CANCELLED,
        DealStatus.LONG_TERM,
    },
    DealStatus.PAID: {DealStatus.PAID},
    DealStatus.CANCELLED: {DealStatus.CANCELLED},
    DealStatus.LONG_TERM: {DealStatus.LONG_TERM},
}


def validate_status_transition(current: str, new: str) -> None:
    """Raise ValueError when a transition is not allowed."""

    try:
        current_status = DealStatus(current)
        new_status = DealStatus(new)
    except ValueError as exc:
        raise ValueError("Unknown deal status") from exc

    allowed = VALID_TRANSITIONS[current_status]
    if new_status not in allowed:
        raise ValueError(
            f"Transition from '{current_status.value}' to '{new_status.value}' is not allowed"
        )


def normalize_status(value: str) -> str:
    """Return the canonical representation of a status string."""

    try:
        return DealStatus(value).value
    except ValueError as exc:
        raise ValueError(f"Unsupported deal status: {value}") from exc


__all__ = ["DealStatus", "normalize_status", "validate_status_transition", "VALID_TRANSITIONS"]
