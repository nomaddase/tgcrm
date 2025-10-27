"""Lightweight natural language intent parser for the CRM bot."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class Intent(str, Enum):
    MAIN_MENU = "main_menu"
    CREATE_CLIENT = "create_client"
    DEAL_SEARCH = "deal_search"
    INTERACTION = "interaction"
    REMINDER = "reminder"
    STATUS_CHANGE = "status_change"
    SUPERVISOR_REPORT = "supervisor_report"
    SETTINGS = "settings"
    DEAL_SUMMARY = "deal_summary"
    INVOICE_REQUEST = "invoice_request"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    intent: Intent
    payload: Dict[str, Any]


PHONE_REGEX = re.compile(r"\+?7[\d\s\-()]{8,}")
FOUR_DIGITS = re.compile(r"^\D*(\d{4})\D*$")
STATUS_REGEX = re.compile(
    r"перев[ео]д[и]?\s+сделк[уы]?\s+(?P<identifier>\d{3,})?\s*(?:в|на)\s+(?P<status>[а-яё\s]+)",
    re.IGNORECASE,
)


def _normalise_text(text: str | None) -> str:
    return (text or "").strip().lower()


def parse_intent(text: str | None) -> IntentResult:
    """Return a best-effort intent parsed from manager input."""

    normalised = _normalise_text(text)
    if not normalised:
        return IntentResult(Intent.UNKNOWN, {})

    if "меню" in normalised:
        return IntentResult(Intent.MAIN_MENU, {})

    if PHONE_REGEX.fullmatch(normalised.replace(" ", "")):
        digits = re.sub(r"\D", "", normalised)
        if digits.startswith("7"):
            digits = "+" + digits
        elif digits.startswith("77"):
            digits = "+" + digits
        return IntentResult(Intent.CREATE_CLIENT, {"phone": digits})

    match = FOUR_DIGITS.match(normalised)
    if match:
        return IntentResult(Intent.DEAL_SEARCH, {"suffix": match.group(1)})

    if "напомни" in normalised:
        return IntentResult(Intent.REMINDER, {"text": text.strip()})

    if any(keyword in normalised for keyword in ("позвони", "звонок", "написал", "отправил", "письмо")):
        return IntentResult(Intent.INTERACTION, {"summary": text.strip()})

    status_match = STATUS_REGEX.search(normalised)
    if status_match:
        status = status_match.group("status").strip()
        identifier = status_match.group("identifier")
        payload: Dict[str, Any] = {"status": status}
        if identifier:
            payload["identifier"] = identifier
        return IntentResult(Intent.STATUS_CHANGE, payload)

    if "счёт" in normalised or "счет" in normalised:
        return IntentResult(Intent.INVOICE_REQUEST, {"text": text.strip()})

    if "отч" in normalised or "сводк" in normalised:
        return IntentResult(Intent.SUPERVISOR_REPORT, {})

    if "настрой" in normalised:
        return IntentResult(Intent.SETTINGS, {})

    if "мои сделки" in normalised or "список сделок" in normalised:
        return IntentResult(Intent.DEAL_SUMMARY, {})

    return IntentResult(Intent.INTERACTION, {"summary": text.strip()}) if len(normalised.split()) > 3 else IntentResult(Intent.UNKNOWN, {})


__all__ = ["Intent", "IntentResult", "parse_intent"]
