"""Database engine and session management."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from tgcrm.config import get_settings
from tgcrm.db import models

_settings = get_settings()

engine: AsyncEngine = create_async_engine(
    _settings.database.async_dsn,
    echo=_settings.database.echo,
    future=True,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def init_models() -> None:
    """Create database tables based on the SQLAlchemy models."""

    async with engine.begin() as connection:
        await connection.run_sync(models.Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional scope around a series of operations."""

    session = AsyncSessionFactory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


__all__ = ["engine", "AsyncSessionFactory", "get_session", "init_models"]
