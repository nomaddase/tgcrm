"""High level helpers that talk to the OpenAI API with caching support."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Awaitable, Callable, Dict, List

import redis.asyncio as aioredis
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from tgcrm.config import get_settings
from tgcrm.db.session import AsyncSessionFactory
from tgcrm.services.settings import get_setting

CACHE_TTL_SECONDS = 6 * 60 * 60

_settings = get_settings()
_redis_client: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis | None:
    """Return a lazily initialised Redis client or ``None`` if unavailable."""

    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        _redis_client = aioredis.from_url(
            _settings.redis.dsn,
            encoding="utf-8",
            decode_responses=True,
        )
    except Exception:  # pragma: no cover - connection errors handled gracefully
        _redis_client = None
    return _redis_client


async def _resolve_openai_client() -> AsyncOpenAI:
    """Return an AsyncOpenAI client taking DB overrides into account."""

    override: str | None = None
    try:
        async with AsyncSessionFactory() as session:
            override = await get_setting(session, "openai_api_key")
    except Exception:  # pragma: no cover - DB might be offline during tests
        override = None

    api_key = override or _settings.openai.api_key
    return AsyncOpenAI(api_key=api_key)


def _build_cache_key(messages: List[Dict[str, str]]) -> str:
    payload = json.dumps(messages, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"ai:{digest}"


async def _with_cache(key: str, builder: Callable[[], Awaitable[str]]) -> str:
    redis = await _get_redis()
    if redis is not None:
        cached = await redis.get(key)
        if cached:
            return cached

    result = await builder()
    if redis is not None:
        try:
            await redis.setex(key, CACHE_TTL_SECONDS, result)
        except Exception:  # pragma: no cover - redis failures should not break flows
            pass
    return result


@retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
async def _chat(messages: List[Dict[str, str]]) -> str:
    """Send a conversation to OpenAI and return the assistant response."""

    client = await _resolve_openai_client()
    response = await client.chat.completions.create(
        model=_settings.openai.model,
        messages=messages,
        temperature=_settings.openai.temperature,
    )
    return response.choices[0].message.content or ""


async def _ask(messages: List[Dict[str, str]]) -> str:
    cache_key = _build_cache_key(messages)
    return await _with_cache(cache_key, lambda: _chat(messages))


AI_PROMPTS: Dict[str, str] = {
    "deal_advice": (
        "На основе истории взаимодействий и статуса сделки предложи менеджеру "
        "оптимальный следующий шаг."
    ),
    "client_summary": "Сформулируй краткое описание клиента по данным имени, города и интереса.",
    "invoice_summary": "Опиши, что содержится в счёте и как можно использовать это для допродаж.",
    "reminder_tip": "Составь совет для менеджера при выполнении напоминания.",
    "status_change_tip": "Определи, что сделать после смены статуса, чтобы удержать клиента.",
}

SYSTEM_PROMPT = (
    "Ты — опытный ассистент по продажам. Отвечай по существу, лаконично и на русском "
    "языке, чтобы помочь менеджеру по продажам сделать следующий шаг."
)


async def get_ai_advice(context: str) -> str:
    """Return a generic piece of advice based on the provided context."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context.strip()},
    ]
    return await _ask(messages)


async def summarize_invoice(pdf_text: str) -> str:
    context = f"{AI_PROMPTS['invoice_summary']}\n\n{pdf_text.strip()}"
    return await get_ai_advice(context)


async def generate_followup_message(history: str) -> str:
    context = f"{AI_PROMPTS['deal_advice']}\n\nИстория:\n{history.strip()}"
    return await get_ai_advice(context)


async def generate_supervisor_summary(db_snapshot: str) -> str:
    context = (
        "Ты готовишь сводку для руководителя отдела продаж. Проанализируй данные "
        "ниже и выдели тренды, риски и рекомендации.\n\n"
        f"Данные:\n{db_snapshot.strip()}"
    )
    return await get_ai_advice(context)


async def build_client_summary(name: str | None, city: str | None, interest: str) -> str:
    payload = (
        f"Имя: {name or 'не указано'}\n"
        f"Город: {city or 'не указан'}\n"
        f"Интерес: {interest or 'не указан'}"
    )
    context = f"{AI_PROMPTS['client_summary']}\n\n{payload}"
    return await get_ai_advice(context)


async def build_deal_advice(history: str, status: str) -> str:
    context = (
        f"{AI_PROMPTS['deal_advice']}\n\nСтатус: {status}\nИстория:\n{history.strip() or 'Нет взаимодействий'}"
    )
    return await get_ai_advice(context)


async def build_reminder_tip(reminder_text: str) -> str:
    context = f"{AI_PROMPTS['reminder_tip']}\n\nНапоминание: {reminder_text.strip()}"
    return await get_ai_advice(context)


async def build_status_tip(status: str, client_overview: str) -> str:
    context = (
        f"{AI_PROMPTS['status_change_tip']}\n\nНовый статус: {status}\n"
        f"Контекст:\n{client_overview.strip()}"
    )
    return await get_ai_advice(context)


__all__ = [
    "AI_PROMPTS",
    "build_client_summary",
    "build_deal_advice",
    "build_reminder_tip",
    "build_status_tip",
    "generate_followup_message",
    "generate_supervisor_summary",
    "get_ai_advice",
    "summarize_invoice",
]
