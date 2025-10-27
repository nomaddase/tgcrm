"""Smoke tests covering core domain workflows."""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sqlalchemy import select

from tgcrm.db.models import Base, InvoiceItem
from tgcrm.db.statuses import DealStatus
from tgcrm.services.deals import (
    attach_invoice,
    change_deal_status,
    create_deal_for_manager,
    create_reminder,
    ensure_manager,
    get_or_create_client,
    log_interaction,
)
from tgcrm.services.pdf_processing import InvoiceData


def test_full_workflow() -> None:
    async def runner() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        async with session_factory() as session:
            manager = await ensure_manager(session, telegram_id=1, name="Менеджер")
            client = await get_or_create_client(
                session, phone_number="+7 (777) 123-45-67", name="Иван", city="Алматы"
            )
            deal = await create_deal_for_manager(session, client, manager)

            invoice_data = InvoiceData(1000.0, [(1, "Товар A"), (2, "Товар B")])
            invoice = await attach_invoice(session, deal, invoice_data, "invoice.pdf")
            assert float(invoice.total_amount) == 1000.0
            items_result = await session.execute(
                select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
            )
            assert len(items_result.scalars().all()) == 2
            assert deal.status == DealStatus.INVOICE_SENT.value

            interaction = await log_interaction(
                session,
                deal,
                interaction_type="сообщение",
                ai_advice="Будьте вежливы",
                manager_summary="Клиент заинтересован",
            )
            assert interaction.id is not None
            assert deal.last_interaction_at is not None

            reminder = await create_reminder(
                session,
                deal,
                remind_at=interaction.created_at,
            )
            assert reminder.id is not None

            await change_deal_status(session, deal, DealStatus.PAYMENT_PENDING.value)
            assert deal.status == DealStatus.PAYMENT_PENDING.value

        await engine.dispose()

    asyncio.run(runner())
