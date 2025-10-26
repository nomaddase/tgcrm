"""Integration layer for AI powered workflows."""
from __future__ import annotations

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from tgcrm.config import get_settings

_settings = get_settings()
_client = AsyncOpenAI(api_key=_settings.openai.api_key)


@retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
async def get_advice(prompt: str) -> str:
    """Send a prompt to the OpenAI chat completion endpoint and return the answer."""

    response = await _client.chat.completions.create(
        model=_settings.openai.model,
        messages=[
            {"role": "system", "content": "You are an expert sales assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=_settings.openai.temperature,
    )
    return response.choices[0].message.content or ""


async def summarize_interaction(history: str, summary: str) -> str:
    """Generate a follow-up summary for an interaction."""

    prompt = (
        "You are assisting a sales manager. Given the past interaction history and the "
        "latest summary, produce a concise follow-up suggestion.\n\n"
        f"History:\n{history}\n\nLatest interaction:\n{summary}\n"
    )
    return await get_advice(prompt)


async def build_product_consultation_prompt(item_description: str, question: str) -> str:
    """Generate an answer based on the item description and manager question."""

    prompt = (
        "You are a helpful assistant who knows everything about the provided product description.\n"
        "Use the description to answer the manager's question succinctly and professionally.\n\n"
        f"Product: {item_description}\n"
        f"Question: {question}"
    )
    return await get_advice(prompt)


__all__ = ["get_advice", "summarize_interaction", "build_product_consultation_prompt"]
