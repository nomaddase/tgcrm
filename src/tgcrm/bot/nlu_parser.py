"""Natural language utilities for recognising manager intents."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional


INTENT_KEYWORDS = {
    "upload_invoice": ("pdf", "счёт", "счет", "инвойс", "документ"),
    "set_reminder": ("напомни", "напоминание", "не забудь"),
    "change_status": ("статус", "переведи", "обнови", "изменил", "оплачено", "отмен"),
    "supervisor_summary": ("отчёт", "отчет", "сводк", "все сделки", "аналитику"),
    "add_interaction": ("позвон", "отправил", "написал", "связался", "созвонились", "встретились"),
    "settings": ("настрой", "token", "токен"),
    "main_menu": ("меню", "главное меню"),
    "list_deals": ("мои сделки", "список сделок"),
}

PHONE_PATTERN = re.compile(r"\+?7[\d\s\-()]{8,}")
FOUR_DIGITS_PATTERN = re.compile(r"\b(\d{4})\b")
STATUS_PATTERN = re.compile(
    r"(?:(?:перев[ео]д[и]?|измени|поставь|статус|стало)\s*(?:сделк[аи]?\s*)?)"
    r"(?:на|в)?\s*([а-яё\s]+)",
    re.IGNORECASE,
)
RELATIVE_TIME_PATTERN = re.compile(
    r"через\s*(?P<value>\d+)\s*(?P<unit>минут[уы]?|час[ауов]*|дн(?:я|ей)?)",
    re.IGNORECASE,
)


def _normalise(text: str) -> str:
    return text.strip().lower()


def detect_intent(message_text: str) -> str:
    text = _normalise(message_text)
    if not text:
        return "add_interaction"

    if PHONE_PATTERN.fullmatch(text.replace(" ", "")):
        return "create_client"

    digits_match = FOUR_DIGITS_PATTERN.findall(text)
    if digits_match and len(text) <= 10:
        return "search_deal_by_last4"

    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return intent

    if text.isdigit() and len(text) >= 4:
        return "search_deal_by_last4"

    return "add_interaction"


def _parse_phone(text: str) -> Optional[str]:
    digits = re.sub(r"\D", "", text)
    if digits.startswith("7") and len(digits) >= 11:
        return "+" + digits
    if digits.startswith("77") and len(digits) >= 11:
        return "+" + digits
    return None


def _parse_status(text: str) -> Optional[str]:
    match = STATUS_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return None


def _parse_relative_time(text: str) -> Optional[datetime]:
    now = datetime.now(timezone.utc)
    match = RELATIVE_TIME_PATTERN.search(text)
    if match:
        value = int(match.group("value"))
        unit = match.group("unit")
        if unit.startswith("мин"):
            return now + timedelta(minutes=value)
        if unit.startswith("час"):
            return now + timedelta(hours=value)
        return now + timedelta(days=value)
    if "завтра" in text:
        target = now + timedelta(days=1)
        return target.replace(hour=10, minute=0, second=0, microsecond=0)
    if "послезавтра" in text:
        target = now + timedelta(days=2)
        return target.replace(hour=10, minute=0, second=0, microsecond=0)
    return None


def extract_entities(message_text: str) -> Dict[str, object]:
    intent = detect_intent(message_text)
    text = _normalise(message_text)

    if intent == "create_client":
        phone = _parse_phone(message_text)
        return {"intent": intent, "phone": phone or message_text.strip()}

    if intent == "search_deal_by_last4":
        match = FOUR_DIGITS_PATTERN.search(text)
        return {"intent": intent, "last4": match.group(1) if match else text[-4:]}

    if intent == "change_status":
        status = _parse_status(text)
        identifier = None
        digits = re.findall(r"\d{4,}", text)
        if digits:
            identifier = digits[-1][-4:]
        return {"intent": intent, "status": status or text.strip(), "identifier": identifier}

    if intent == "set_reminder":
        remind_at = _parse_relative_time(text)
        return {
            "intent": intent,
            "reminder_text": message_text.strip(),
            "remind_at": remind_at,
        }

    if intent == "add_interaction":
        return {"intent": intent, "interaction": message_text.strip()}

    if intent == "main_menu":
        return {"intent": intent}

    if intent == "settings":
        return {"intent": intent}

    if intent == "list_deals":
        return {"intent": intent}

    if intent == "upload_invoice":
        return {"intent": intent, "comment": message_text.strip()}

    return {"intent": intent}


__all__ = ["detect_intent", "extract_entities"]

