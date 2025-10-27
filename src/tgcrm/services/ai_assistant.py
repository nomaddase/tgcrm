"""Unified interface for communicating with the OpenAI ChatGPT API."""
from __future__ import annotations

import json
from typing import Any, Iterable

from aiogram import Dispatcher
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from tgcrm.config import Settings, get_settings
from tgcrm.db.session import AsyncSessionFactory
from tgcrm.services.settings import get_setting

AI_PROMPTS = {
    "client_summary": (
        "Ты — помощник отдела продаж. На основе имени, города и интереса клиента "
        "создай краткое описание профиля клиента и предложи шаг для начала диалога."
    ),
    "deal_followup": (
        "Проанализируй историю общения и статус сделки, предложи менеджеру лучший "
        "следующий шаг для закрытия."
    ),
    "invoice_summary": (
        "Ты — аналитик. На основе содержимого счёта опиши, что клиент заказал, и "
        "предложи товары/услуги для допродажи."
    ),
    "reminder_tip": (
        "Создай короткий текст напоминания менеджеру о следующем контакте с клиентом, "
        "добавь совет по контексту."
    ),
    "supervisor_report": (
        "Проанализируй сделки отдела, создай отчёт по количеству и суммам, добавь "
        "рекомендации по воронке."
    ),
    "welcome_message": (
        "Ты — дружелюбный ассистент для менеджеров по продажам. Приветствуй сотрудника, "
        "объясни чем может помочь CRM-бот и дай короткий совет по работе с клиентами."
    ),
}

ROLE_SYSTEM_MESSAGES = {
    "sales_assistant": (
        "Ты — продвинутый AI-ассистент менеджера по продажам. Отвечай кратко, по делу "
        "и на русском языке."
    ),
    "analyst": (
        "Ты — финансовый аналитик, который помогает менеджеру продаж делать выводы по "
        "документам и цифрам."
    ),
    "supervisor": (
        "Ты — AI-аналитик для руководителя отдела продаж. Формируй отчёты и советы на "
        "основе предоставленных данных."
    ),
}

DEFAULT_MAX_TOKENS = 800


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
async def _create_completion(
    client: AsyncOpenAI,
    model: str,
    temperature: float,
    max_tokens: int,
    messages: list[dict[str, str]],
) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


async def _resolve_api_key(settings: Settings) -> str:
    override: str | None = None
    try:  # pragma: no cover - DB overrides are optional
        async with AsyncSessionFactory() as session:
            override = await get_setting(session, "openai_api_key")
    except Exception:
        override = None
    return override or settings.openai.api_key


class AIAssistant:
    """High level helper around the OpenAI chat completions API."""

    def __init__(self, client: AsyncOpenAI, model: str, temperature: float, max_tokens: int):
        self._client = client
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def _complete(self, messages: list[dict[str, str]]) -> str:
        return await _create_completion(
            self._client,
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            messages=messages,
        )

    async def get_ai_advice(self, context: str, role: str = "sales_assistant") -> str:
        system_message = ROLE_SYSTEM_MESSAGES.get(role, ROLE_SYSTEM_MESSAGES["sales_assistant"])
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": context.strip()},
        ]
        return await self._complete(messages)

    async def summarize_invoice(self, text: str) -> str:
        context = f"{AI_PROMPTS['invoice_summary']}\n\n{text.strip()}"
        return await self.get_ai_advice(context, role="analyst")

    async def generate_followup_message(self, history: Iterable[Any], status: str) -> str:
        history_lines: list[str] = []
        for item in history:
            if isinstance(item, str):
                history_lines.append(item.strip())
            elif isinstance(item, dict):
                parts = [
                    str(item.get("time") or item.get("created_at") or item.get("date") or ""),
                    str(item.get("type") or item.get("interaction_type") or ""),
                    str(item.get("summary") or item.get("text") or item.get("details") or ""),
                ]
                history_lines.append(" ".join(part for part in parts if part).strip())
            else:
                history_lines.append(str(item))
        history_payload = "\n".join(line for line in history_lines if line)
        context = (
            f"{AI_PROMPTS['deal_followup']}\n\n"
            f"Текущий статус: {status or 'не указан'}.\n"
            f"История:\n{history_payload or 'нет взаимодействий'}"
        )
        return await self.get_ai_advice(context)

    async def generate_supervisor_summary(self, deals: Iterable[Any] | dict[str, Any]) -> str:
        if isinstance(deals, dict):
            payload = json.dumps(deals, ensure_ascii=False)
        else:
            payload = json.dumps(list(deals), ensure_ascii=False)
        context = f"{AI_PROMPTS['supervisor_report']}\n\nДанные:\n{payload}"
        return await self.get_ai_advice(context, role="supervisor")

    async def summarize_client_profile(self, client_data: dict[str, Any]) -> str:
        formatted = json.dumps(client_data, ensure_ascii=False)
        context = f"{AI_PROMPTS['client_summary']}\n\n{formatted}"
        return await self.get_ai_advice(context)

    async def build_reminder_tip(self, reminder_text: str) -> str:
        context = f"{AI_PROMPTS['reminder_tip']}\n\nЗапрос: {reminder_text.strip()}"
        return await self.get_ai_advice(context)


async def create_ai_assistant(settings: Settings | None = None) -> AIAssistant:
    resolved_settings = settings or get_settings()
    api_key = await _resolve_api_key(resolved_settings)
    client = AsyncOpenAI(api_key=api_key)
    return AIAssistant(
        client=client,
        model=resolved_settings.openai.model,
        temperature=resolved_settings.openai.temperature,
        max_tokens=DEFAULT_MAX_TOKENS,
    )


def get_ai_assistant() -> AIAssistant:
    dispatcher = Dispatcher.get_current()
    assistant = dispatcher.workflow_data.get("ai_assistant")
    if not isinstance(assistant, AIAssistant):  # pragma: no cover - runtime guard
        raise RuntimeError("AI assistant is not initialised in dispatcher context")
    return assistant


async def get_ai_advice(context: str, role: str = "sales_assistant") -> str:
    assistant = get_ai_assistant()
    return await assistant.get_ai_advice(context, role=role)


async def summarize_invoice(text: str) -> str:
    assistant = get_ai_assistant()
    return await assistant.summarize_invoice(text)


async def generate_followup_message(history: Iterable[Any], status: str) -> str:
    assistant = get_ai_assistant()
    return await assistant.generate_followup_message(history, status)


async def generate_supervisor_summary(deals: Iterable[Any] | dict[str, Any]) -> str:
    assistant = get_ai_assistant()
    return await assistant.generate_supervisor_summary(deals)


async def summarize_client_profile(client_data: dict[str, Any]) -> str:
    assistant = get_ai_assistant()
    return await assistant.summarize_client_profile(client_data)


async def build_reminder_tip(reminder_text: str) -> str:
    assistant = get_ai_assistant()
    return await assistant.build_reminder_tip(reminder_text)


__all__ = [
    "AI_PROMPTS",
    "AIAssistant",
    "create_ai_assistant",
    "generate_followup_message",
    "generate_supervisor_summary",
    "get_ai_advice",
    "get_ai_assistant",
    "build_reminder_tip",
    "summarize_client_profile",
    "summarize_invoice",
]

