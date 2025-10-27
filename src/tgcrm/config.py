"""Application configuration models."""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class TelegramSettings(BaseSettings):
    """Settings related to the Telegram bot."""

    bot_token: str = Field(..., validation_alias="TELEGRAM_BOT_TOKEN")
    parse_mode: str = Field("HTML", validation_alias="TELEGRAM_PARSE_MODE")


class OpenAISettings(BaseSettings):
    """Settings for communicating with the OpenAI API."""

    api_key: str = Field(..., validation_alias="OPENAI_API_KEY")
    model: str = Field("gpt-4o", validation_alias="OPENAI_MODEL")
    temperature: float = Field(0.4, validation_alias="OPENAI_TEMPERATURE")

    @field_validator("temperature")
    def validate_temperature(cls, value: float) -> float:
        if not 0 <= value <= 2:
            raise ValueError("temperature must be between 0 and 2")
        return value


class DatabaseSettings(BaseSettings):
    """Database connection configuration."""

    host: str = Field("localhost", validation_alias="POSTGRES_HOST")
    port: int = Field(5432, validation_alias="POSTGRES_PORT")
    user: str = Field("postgres", validation_alias="POSTGRES_USER")
    password: str = Field("postgres", validation_alias="POSTGRES_PASSWORD")
    name: str = Field("tgcrm", validation_alias="POSTGRES_DB")
    echo: bool = Field(False, validation_alias="DB_ECHO")

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

    host: str = Field("localhost", validation_alias="REDIS_HOST")
    port: int = Field(6379, validation_alias="REDIS_PORT")
    db: int = Field(0, validation_alias="REDIS_DB")

    @property
    def dsn(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class BotBehaviourSettings(BaseSettings):
    """Runtime configuration for bot behaviour rules."""

    workday_start: str = Field("10:00", validation_alias="WORKDAY_START")
    workday_end: str = Field("17:00", validation_alias="WORKDAY_END")
    lunch_start: str = Field("13:00", validation_alias="LUNCH_START")
    lunch_end: str = Field("14:00", validation_alias="LUNCH_END")
    supervisor_password: str = Field("878707Server", validation_alias="SUPERVISOR_PASSWORD")
    proactive_excluded_statuses: List[str] | str = Field(
        default_factory=lambda: ["долгосрочная", "отмененная", "оплаченная"],
        validation_alias="PROACTIVE_EXCLUDED_STATUSES",
    )

    @field_validator("proactive_excluded_statuses", mode="before")
    def parse_statuses(cls, value: Optional[List[str] | str]) -> List[str]:
        if value is None:
            return ["долгосрочная", "отмененная", "оплаченная"]
        if isinstance(value, str):
            return [status.strip() for status in value.split(",") if status.strip()]
        if isinstance(value, list):
            return value
        raise TypeError("proactive_excluded_statuses must be a list or a comma separated string")


class Settings(BaseSettings):
    """Full application configuration."""

    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    behaviour: BotBehaviourSettings = Field(default_factory=BotBehaviourSettings)

    model_config = SettingsConfigDict(extra="ignore")


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
