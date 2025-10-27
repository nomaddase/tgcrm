"""Shared pytest fixtures."""
from __future__ import annotations

import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src_path = str(root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:test-token")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DB", "tgcrm")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")

import pytest

from tgcrm.config import get_settings


@pytest.fixture(autouse=True)
def _ensure_test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Populate required environment variables for tests and reset cached settings."""

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", os.environ["TELEGRAM_BOT_TOKEN"])
    monkeypatch.setenv("OPENAI_API_KEY", os.environ["OPENAI_API_KEY"])
    monkeypatch.setenv("POSTGRES_HOST", os.environ["POSTGRES_HOST"])
    monkeypatch.setenv("POSTGRES_PORT", os.environ["POSTGRES_PORT"])
    monkeypatch.setenv("POSTGRES_USER", os.environ["POSTGRES_USER"])
    monkeypatch.setenv("POSTGRES_PASSWORD", os.environ["POSTGRES_PASSWORD"])
    monkeypatch.setenv("POSTGRES_DB", os.environ["POSTGRES_DB"])
    monkeypatch.setenv("REDIS_URL", os.environ["REDIS_URL"])

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
