"""Utilities for working with phone numbers."""
from __future__ import annotations

import re

KZ_COUNTRY_CODE = "+7"


class PhoneValidationError(ValueError):
    """Raised when a phone number cannot be normalized."""


def normalize_kz_phone(raw_phone: str) -> str:
    """Normalize Kazakhstan phone numbers to the format +7XXXXXXXXXX."""

    digits = re.sub(r"\D", "", raw_phone)
    if not digits:
        raise PhoneValidationError("Номер телефона не должен быть пустым")

    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    elif digits.startswith("7") and len(digits) == 11:
        pass
    elif len(digits) == 10:
        digits = "7" + digits
    else:
        raise PhoneValidationError("Введите номер в формате +7XXXXXXXXXX")

    normalized = f"{KZ_COUNTRY_CODE}{digits[1:]}"
    if len(normalized) != 12:
        raise PhoneValidationError("Введите корректный казахстанский номер телефона")
    return normalized


def extract_suffix(phone_number: str, length: int = 4) -> str:
    """Return the last N digits of a normalized phone number."""

    digits = re.sub(r"\D", "", phone_number)
    return digits[-length:]


__all__ = ["normalize_kz_phone", "extract_suffix", "PhoneValidationError"]
