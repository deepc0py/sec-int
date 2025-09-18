"""Centralized configuration and secrets management using pydantic-settings."""

from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    # Application settings
    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # Database configuration
    DATABASE_URL: str  # e.g., postgresql+asyncpg://user:pass@localhost:54320/rag_db
    POSTGRES_USER: str = "rag_user"
    POSTGRES_PASSWORD: str = "rag_pass"
    POSTGRES_DB: str = "rag_db"

    # OpenAI configuration
    OPENAI_API_KEY: str
    LLM_MODEL_NAME: str = "gpt-4o"


@lru_cache
def get_settings(**kwargs: Any) -> Settings:
    """Get application settings. Cached for performance."""
    return Settings(**kwargs)
