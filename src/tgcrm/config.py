"""
Конфигурация проекта с поддержкой OpenAI.
"""

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class TelegramSettings(BaseModel):
    bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    parse_mode: str = Field("HTML", alias="TELEGRAM_PARSE_MODE")


class OpenAISettings(BaseModel):
    api_key: str = Field(..., alias="OPENAI_API_KEY")
    model: str = Field("gpt-4o", alias="OPENAI_MODEL")
    temperature: float = Field(0.4, alias="OPENAI_TEMPERATURE")


class Settings(BaseSettings):
    telegram: TelegramSettings
    openai: OpenAISettings
    supervisor_password: str = Field("878707Server", alias="SUPERVISOR_PASSWORD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore
    return _settings
