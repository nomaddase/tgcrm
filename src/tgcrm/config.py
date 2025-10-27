"""Application configuration models."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_OPENAI_TEMPERATURE = 0.0
MAX_OPENAI_TEMPERATURE = 2.0


class AppBaseSettings(BaseSettings):
    """Base settings with shared configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class TelegramSettings(AppBaseSettings):
    """Settings related to the Telegram bot."""

    bot_token: str = Field(..., validation_alias="TELEGRAM_BOT_TOKEN")
    parse_mode: str = Field("HTML", validation_alias="TELEGRAM_PARSE_MODE")


class OpenAISettings(AppBaseSettings):
    """Settings for communicating with the OpenAI API."""

    api_key: str = Field(..., validation_alias="OPENAI_API_KEY")
    model: str = Field("gpt-4o", validation_alias="OPENAI_MODEL")
    temperature: float = Field(0.4, validation_alias="OPENAI_TEMPERATURE")

    @field_validator("temperature")
    def validate_temperature(cls, value: float) -> float:
        if not MIN_OPENAI_TEMPERATURE <= value <= MAX_OPENAI_TEMPERATURE:
            raise ValueError(
                "temperature must be between "
                f"{MIN_OPENAI_TEMPERATURE} and {MAX_OPENAI_TEMPERATURE}"
            )
        return value


class DatabaseSettings(AppBaseSettings):
    """Database connection configuration."""

    host: str = Field("postgres", validation_alias="POSTGRES_HOST")
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


class RedisSettings(AppBaseSettings):
    """Redis connection settings used by Celery and reminders."""

    url: str = Field("redis://redis:6379/0", validation_alias="REDIS_URL")

    @property
    def dsn(self) -> str:
        return self.url


class LoggingSettings(AppBaseSettings):
    """Logging configuration."""

    level: str = Field("INFO", validation_alias="LOG_LEVEL")


DEFAULT_PROACTIVE_EXCLUDED_STATUSES = ["долгосрочная", "отмененная", "оплаченная"]


class BotBehaviourSettings(AppBaseSettings):
    """Runtime configuration for bot behaviour rules."""

    workday_start: str = Field("10:00", validation_alias="WORKDAY_START")
    workday_end: str = Field("17:00", validation_alias="WORKDAY_END")
    lunch_start: str = Field("13:00", validation_alias="LUNCH_START")
    lunch_end: str = Field("14:00", validation_alias="LUNCH_END")
    supervisor_password: str = Field("878707Server", validation_alias="SUPERVISOR_PASSWORD")
    proactive_excluded_statuses: list[str] = Field(
        default_factory=lambda: DEFAULT_PROACTIVE_EXCLUDED_STATUSES.copy(),
        validation_alias="PROACTIVE_EXCLUDED_STATUSES",
    )

    @field_validator("proactive_excluded_statuses", mode="before")
    def parse_statuses(cls, value: Any) -> list[str]:
        if value is None:
            return DEFAULT_PROACTIVE_EXCLUDED_STATUSES.copy()
        if isinstance(value, str):
            cleaned = [status.strip() for status in value.split(",") if status.strip()]
            return cleaned or DEFAULT_PROACTIVE_EXCLUDED_STATUSES.copy()
        if isinstance(value, list):
            return value
        raise TypeError("proactive_excluded_statuses must be a list or a comma separated string")


def _build_telegram_settings() -> TelegramSettings:
    return TelegramSettings()  # type: ignore[call-arg]


def _build_openai_settings() -> OpenAISettings:
    return OpenAISettings()  # type: ignore[call-arg]


def _build_database_settings() -> DatabaseSettings:
    return DatabaseSettings()  # type: ignore[call-arg]


def _build_redis_settings() -> RedisSettings:
    return RedisSettings()  # type: ignore[call-arg]


def _build_logging_settings() -> LoggingSettings:
    return LoggingSettings()  # type: ignore[call-arg]


def _build_behaviour_settings() -> BotBehaviourSettings:
    return BotBehaviourSettings()  # type: ignore[call-arg]


class Settings(AppBaseSettings):
    """Full application configuration."""

    telegram: TelegramSettings = Field(default_factory=_build_telegram_settings)
    openai: OpenAISettings = Field(default_factory=_build_openai_settings)
    database: DatabaseSettings = Field(default_factory=_build_database_settings)
    redis: RedisSettings = Field(default_factory=_build_redis_settings)
    logging: LoggingSettings = Field(default_factory=_build_logging_settings)
    behaviour: BotBehaviourSettings = Field(default_factory=_build_behaviour_settings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def _find_missing(settings: Settings) -> list[str]:
    required_pairs: Iterable[tuple[str, str]] = (
        (settings.telegram.bot_token, "TELEGRAM_BOT_TOKEN"),
        (settings.openai.api_key, "OPENAI_API_KEY"),
    )
    missing = [env_name for value, env_name in required_pairs if not str(value).strip()]
    return missing


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""

    settings = Settings()
    missing = _find_missing(settings)
    if missing:
        env_list = ", ".join(sorted(missing))
        raise RuntimeError(
            "Missing required environment variables: "
            f"{env_list}. Please provide them before starting the application."
        )
    return settings


__all__ = [
    "BotBehaviourSettings",
    "DatabaseSettings",
    "LoggingSettings",
    "OpenAISettings",
    "RedisSettings",
    "Settings",
    "TelegramSettings",
    "get_settings",
]
