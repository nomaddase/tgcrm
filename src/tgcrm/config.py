"""Application configuration models."""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import BaseSettings, Field, validator


class TelegramSettings(BaseSettings):
    """Settings related to the Telegram bot."""

    bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    parse_mode: str = Field("HTML", env="TELEGRAM_PARSE_MODE")


class OpenAISettings(BaseSettings):
    """Settings for communicating with the OpenAI API."""

    api_key: str = Field(..., env="OPENAI_API_KEY")
    model: str = Field("gpt-4o", env="OPENAI_MODEL")
    temperature: float = Field(0.4, env="OPENAI_TEMPERATURE")

    @validator("temperature")
    def validate_temperature(cls, value: float) -> float:
        if not 0 <= value <= 2:
            raise ValueError("temperature must be between 0 and 2")
        return value


class DatabaseSettings(BaseSettings):
    """Database connection configuration."""

    host: str = Field("localhost", env="POSTGRES_HOST")
    port: int = Field(5432, env="POSTGRES_PORT")
    user: str = Field("postgres", env="POSTGRES_USER")
    password: str = Field("postgres", env="POSTGRES_PASSWORD")
    name: str = Field("tgcrm", env="POSTGRES_DB")
    echo: bool = Field(False, env="DB_ECHO")

    @property
    def async_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        )

    @property
    def sync_dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis connection settings used by Celery and reminders."""

    host: str = Field("localhost", env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    db: int = Field(0, env="REDIS_DB")

    @property
    def dsn(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class BotBehaviourSettings(BaseSettings):
    """Runtime configuration for bot behaviour rules."""

    workday_start: str = Field("10:00", env="WORKDAY_START")
    workday_end: str = Field("17:00", env="WORKDAY_END")
    lunch_start: str = Field("13:00", env="LUNCH_START")
    lunch_end: str = Field("14:00", env="LUNCH_END")
    supervisor_password: str = Field("878707Server", env="SUPERVISOR_PASSWORD")
    proactive_excluded_statuses: List[str] = Field(
        default_factory=lambda: ["долгосрочная", "отмененная", "оплаченная"],
        env="PROACTIVE_EXCLUDED_STATUSES",
    )

    @validator("proactive_excluded_statuses", pre=True)
    def parse_statuses(cls, value: Optional[str]) -> List[str]:
        if value is None:
            return ["долгосрочная", "отмененная", "оплаченная"]
        if isinstance(value, str):
            return [status.strip() for status in value.split(",") if status.strip()]
        return value


class Settings(BaseSettings):
    """Full application configuration."""

    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    behaviour: BotBehaviourSettings = Field(default_factory=BotBehaviourSettings)


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()


__all__ = [
    "BotBehaviourSettings",
    "DatabaseSettings",
    "OpenAISettings",
    "RedisSettings",
    "Settings",
    "TelegramSettings",
    "get_settings",
]
