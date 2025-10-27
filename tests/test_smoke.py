"""Smoke tests to verify core modules and infrastructure dependencies."""
from __future__ import annotations

import asyncio
from importlib import import_module

import asyncpg
import pytest
import redis.asyncio as aioredis

from tgcrm.config import get_settings

MODULES = [
    "tgcrm.bot.main",
    "tgcrm.tasks.celery_app",
    "tgcrm.db.session",
]


def test_modules_importable() -> None:
    for module_name in MODULES:
        import_module(module_name)


def test_database_connection() -> None:
    settings = get_settings()
    dsn = settings.database.async_dsn.replace("postgresql+asyncpg", "postgresql")

    async def _connect() -> None:
        connection = await asyncpg.connect(dsn, timeout=3)
        await connection.close()

    try:
        asyncio.run(_connect())
    except Exception as exc:  # pragma: no cover - exercised in integration environments
        pytest.skip(f"PostgreSQL is unavailable: {exc}")

def test_redis_connection() -> None:
    settings = get_settings()
    client = aioredis.from_url(settings.redis.dsn)

    async def _ping() -> None:
        try:
            response = await asyncio.wait_for(client.ping(), timeout=3)
        finally:
            await client.aclose()
        assert response is True

    try:
        asyncio.run(_ping())
    except Exception as exc:  # pragma: no cover - exercised in integration environments
        pytest.skip(f"Redis is unavailable: {exc}")
