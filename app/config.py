import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # LLM Provider Configuration
    LLM_PROVIDER: str = "groq"  # "groq" or "openai"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Edge-case & Guardrail Thresholds
    MAX_INPUT_CHARACTERS: int = 40000
    MIN_INPUT_CHARACTERS: int = 10
    MAX_RETRIES: int = 2
    REQUEST_TIMEOUT_SECONDS: float = 30.0

    # Development & Testing Fallback
    ALLOW_MOCK_FALLBACK: bool = True

    # Server Configuration
    APP_NAME: str = "Document Data Extraction Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
