"""Compatibility layer that proxies to the new AI assistant helpers."""
from __future__ import annotations

from tgcrm.db.models import Deal, InvoiceItem

from .ai_assistant import get_ai_advice


async def get_advice(prompt: str) -> str:
    """Backward compatible helper that forwards to :func:`get_ai_advice`."""

    return await get_ai_advice(prompt)


async def summarize_interaction(history: str, summary: str) -> str:
    """Generate a follow-up suggestion for a manager after an interaction."""

    prompt = (
        "You are assisting a sales manager. Given the past interaction history and the "
        "latest summary, produce a concise follow-up suggestion.\n\n"
        f"History:\n{history}\n\nLatest interaction:\n{summary}\n"
    )
    return await get_ai_advice(prompt)


async def build_product_consultation_prompt(item_description: str, question: str) -> str:
    """Generate an answer based on the item description and manager question."""

    prompt = (
        "You are a helpful assistant who knows everything about the provided product description.\n"
        "Use the description to answer the manager's question succinctly and professionally.\n\n"
        f"Product: {item_description}\n"
        f"Question: {question}"
    )
    return await get_ai_advice(prompt)


async def build_advice_for_interaction(deal: Deal, interaction_type: str) -> str:
    """Return a suggestion for the next interaction based on history."""

    history_parts = []
    sorted_history = sorted(deal.interactions, key=lambda item: item.created_at or 0)
    for interaction in sorted_history[-5:]:
        fragment = (
            f"[{interaction.created_at:%Y-%m-%d %H:%M}] {interaction.type}: {interaction.manager_summary}"
        )
        history_parts.append(fragment)

    history = "\n".join(history_parts) or "No previous interactions."
    prompt = (
        "Act as an experienced sales supervisor.\n"
        "Given the following interaction history and the requested channel, suggest a short tip.\n"
        f"Channel: {interaction_type}\n"
        f"History:\n{history}\n"
    )
    return await get_ai_advice(prompt)


async def answer_item_question(deal: Deal, line_no: int, question: str) -> str:
    """Return an AI generated answer about a specific invoice line."""

    latest_invoice = None
    if deal.invoices:
        latest_invoice = sorted(deal.invoices, key=lambda inv: inv.id)[-1]

    if not latest_invoice:
        raise ValueError("У сделки нет связанных счетов")

    matching_item: InvoiceItem | None = None
    for item in latest_invoice.items:
        if item.line_number == line_no:
            matching_item = item
            break

    if not matching_item:
        raise ValueError("Позиция с указанным номером строки не найдена")

    return await build_product_consultation_prompt(matching_item.item_description, question)


__all__ = [
    "answer_item_question",
    "build_advice_for_interaction",
    "build_product_consultation_prompt",
    "get_advice",
    "summarize_interaction",
]
