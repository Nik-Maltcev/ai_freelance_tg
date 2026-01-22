"""Configuration module for the crypto parser bot.

Loads settings from environment variables and YAML config files.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram Bot (optional for worker)
    BOT_TOKEN: str = ""
    ADMIN_IDS: list[int] = []

    # Telegram Userbot (Telethon)
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_PHONE: str

    # Database
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def convert_database_url(cls, v: str) -> str:
        """Convert postgres:// to postgresql+asyncpg:// for async support."""
        if not v:
            return v
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Worker settings
    PARSE_DAYS: int = 2  # Today + yesterday
    REQUEST_DELAY_SEC: float = 1.5
    MIN_MESSAGE_LENGTH: int = 10

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Any) -> list[int]:
        """Parse ADMIN_IDS from comma-separated string or list."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Parsing ADMIN_IDS: {v} (type: {type(v)})")
        
        if v is None:
            return []
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            result = [int(x.strip()) for x in v.split(",") if x.strip()]
            logger.info(f"Parsed ADMIN_IDS: {result}")
            return result
        if isinstance(v, list):
            return [int(x) for x in v]
        if isinstance(v, int):
            return [v]
        return []


def load_chats_config(config_path: str | Path = "config/chats.yaml") -> dict[str, Any]:
    """Load chat configuration from YAML file.

    Returns:
        Dictionary with "chats" list and "settings".
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError("Configuration file is empty")

    if "chats" not in config:
        raise ValueError("Configuration must contain 'chats' key")

    return config


# Global settings instance (lazy loaded)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
