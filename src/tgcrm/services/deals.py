"""Domain services for client and deal workflows."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import joinedload

from tgcrm.db.models import Client, Deal, Interaction, Invoice, InvoiceItem, Manager, Reminder
from tgcrm.db.statuses import DealStatus, normalize_status, validate_status_transition
from tgcrm.services.pdf_processing import InvoiceData
from tgcrm.services.phones import extract_suffix, normalize_kz_phone


async def get_or_create_client(
    session: AsyncSession,
    phone_number: str,
    *,
    name: Optional[str] = None,
    city: Optional[str] = None,
) -> Client:
    normalized_phone = normalize_kz_phone(phone_number)
    phone_suffix = extract_suffix(normalized_phone)

    result = await session.execute(select(Client).where(Client.phone_number == normalized_phone))
    client = result.scalar_one_or_none()
    if client:
        return client

    client = Client(
        phone_number=normalized_phone,
        phone_suffix=phone_suffix,
        name=name,
        city=city,
    )
    session.add(client)
    await session.flush()
    return client


async def create_deal_for_manager(
    session: AsyncSession, client: Client, manager: Manager, status: str = "Новый"
) -> Deal:
    deal = Deal(client=client, manager=manager, status=normalize_status(status))
    session.add(deal)
    await session.flush()
    return deal


async def attach_invoice(
    session: AsyncSession, deal: Deal, invoice_data: InvoiceData, file_path: str
) -> Invoice:
    invoice = Invoice(deal=deal, file_path=file_path, total_amount=invoice_data.total_amount)
    session.add(invoice)
    await session.flush()

    deal.amount = invoice_data.total_amount
    validate_status_transition(deal.status, DealStatus.INVOICE_SENT.value)
    deal.status = DealStatus.INVOICE_SENT.value

    for line_number, description in invoice_data.line_items:
        item = InvoiceItem(invoice=invoice, line_number=line_number, item_description=description)
        session.add(item)

    await session.flush()
    return invoice


async def get_active_deal_by_phone_suffix(
    session: AsyncSession, *, phone_suffix: str, manager: Manager
) -> Optional[Deal]:
    suffix = phone_suffix[-4:]
    query = (
        select(Deal)
        .options(joinedload(Deal.client))
        .join(Deal.client)
        .where(Client.phone_suffix == suffix, Deal.manager_id == manager.id)
        .order_by(Deal.created_at.desc())
    )
    result = await session.execute(query)
    return result.scalars().first()


async def log_interaction(
    session: AsyncSession,
    deal: Deal,
    *,
    interaction_type: str,
    ai_advice: Optional[str],
    manager_summary: str,
) -> Interaction:
    deal.last_interaction_at = datetime.now(timezone.utc)
    interaction = Interaction(
        deal=deal,
        type=interaction_type,
        ai_advice=ai_advice,
        manager_summary=manager_summary,
    )
    session.add(interaction)
    await session.flush()
    return interaction


async def create_reminder(
    session: AsyncSession,
    deal: Deal,
    *,
    remind_at: datetime,
) -> Reminder:
    reminder = Reminder(deal=deal, remind_at=remind_at, is_sent=False)
    session.add(reminder)
    await session.flush()
    return reminder


async def change_deal_status(session: AsyncSession, deal: Deal, new_status: str) -> Deal:
    normalized = normalize_status(new_status)
    validate_status_transition(deal.status, normalized)
    deal.status = normalized
    await session.flush()
    return deal


async def ensure_manager(session: AsyncSession, telegram_id: int, *, name: Optional[str] = None) -> Manager:
    result = await session.execute(select(Manager).where(Manager.telegram_id == telegram_id))
    manager = result.scalar_one_or_none()
    if manager:
        if name and not manager.name:
            manager.name = name
            await session.flush()
        return manager

    manager = Manager(telegram_id=telegram_id, name=name, role="manager")
    session.add(manager)
    await session.flush()
    return manager


__all__ = [
    "attach_invoice",
    "change_deal_status",
    "create_deal_for_manager",
    "create_reminder",
    "ensure_manager",
    "get_active_deal_by_phone_suffix",
    "get_or_create_client",
    "log_interaction",
]
