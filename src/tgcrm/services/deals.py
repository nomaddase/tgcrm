"""Domain services for client and deal workflows."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tgcrm.db.models import Client, Deal, Interaction, Invoice, InvoiceItem, Manager
from tgcrm.services.pdf_processing import InvoiceData


async def get_or_create_client(
    session: AsyncSession,
    phone_number: str,
    *,
    name: Optional[str] = None,
    city: Optional[str] = None,
) -> Client:
    result = await session.execute(select(Client).where(Client.phone_number == phone_number))
    client = result.scalar_one_or_none()
    if client:
        return client

    client = Client(phone_number=phone_number, name=name, city=city)
    session.add(client)
    await session.flush()
    return client


async def create_deal_for_manager(
    session: AsyncSession, client: Client, manager: Manager, status: str = "Новый"
) -> Deal:
    deal = Deal(client=client, manager=manager, status=status)
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
    deal.status = "отправлен счет"

    for line_number, description in invoice_data.line_items:
        item = InvoiceItem(invoice=invoice, line_number=line_number, item_description=description)
        session.add(item)

    await session.flush()
    return invoice


async def get_active_deal_by_phone_suffix(
    session: AsyncSession, *, phone_suffix: str, manager: Manager
) -> Optional[Deal]:
    phone_suffix = phone_suffix[-4:]
    query = (
        select(Deal)
        .join(Deal.client)
        .where(Client.phone_number.like(f"%{phone_suffix}"), Deal.manager_id == manager.id)
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
    deal.last_interaction_at = datetime.utcnow()
    interaction = Interaction(
        deal=deal,
        type=interaction_type,
        ai_advice=ai_advice,
        manager_summary=manager_summary,
    )
    session.add(interaction)
    await session.flush()
    return interaction


__all__ = [
    "attach_invoice",
    "create_deal_for_manager",
    "get_active_deal_by_phone_suffix",
    "get_or_create_client",
    "log_interaction",
]
