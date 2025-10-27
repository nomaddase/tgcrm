"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from tgcrm.config import get_settings


@pytest.fixture(autouse=True)
def _ensure_test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Populate required environment variables for tests and reset cached settings."""

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:test-token")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("POSTGRES_HOST", "127.0.0.1")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "postgres")
    monkeypatch.setenv("POSTGRES_DB", "tgcrm")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
