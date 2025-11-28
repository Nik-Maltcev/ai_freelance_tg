"""Configuration module for the freelance parser bot.

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

    # Telegram Bot
    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []

    # Telegram Userbot (Telethon)
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_PHONE: str

    # Gemini AI
    GEMINI_API_KEY: str

    # Database
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def convert_database_url(cls, v: str) -> str:
        """Convert postgresql:// to postgresql+asyncpg:// for async support."""
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Worker settings
    PARSE_INTERVAL_HOURS: int = 2
    REQUEST_DELAY_SEC: float = 1.5
    MESSAGES_TTL_DAYS: int = 30
    BATCH_SIZE: int = 50

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Any) -> list[int]:
        """Parse ADMIN_IDS from comma-separated string or list."""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",")]
        if isinstance(v, list):
            return [int(x) for x in v]
        return []


def load_chats_config(config_path: str | Path = "config/chats.yaml") -> dict[str, Any]:
    """Load chat categories configuration from YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Dictionary with "categories" key containing category objects.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        yaml.YAMLError: If the YAML syntax is invalid.
        ValueError: If required fields are missing.
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError("Configuration file is empty")

    if "categories" not in config:
        raise ValueError("Configuration must contain 'categories' key")

    # Validate each category has required fields
    for slug, category in config["categories"].items():
        if not isinstance(category, dict):
            raise ValueError(f"Category '{slug}' must be a dictionary")
        if "name" not in category:
            raise ValueError(f"Category '{slug}' must have 'name' field")
        if "chats" not in category:
            raise ValueError(f"Category '{slug}' must have 'chats' field")

    return config


# Global settings instance (lazy loaded)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance.

    Returns:
        Settings instance loaded from environment.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
