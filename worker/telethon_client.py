"""Telethon client singleton for Telegram chat parsing."""

from pathlib import Path
from telethon import TelegramClient

from core.config import get_settings

# Global singleton client
_telethon_client: TelegramClient | None = None

# Session file name (without .session extension)
SESSION_NAME = "crypto_parser"


async def get_telethon_client() -> TelegramClient:
    """Get or create the singleton Telethon client.
    
    Uses file-based session (crypto_parser.session).
    """
    global _telethon_client
    
    if _telethon_client is None:
        settings = get_settings()
        
        _telethon_client = TelegramClient(
            SESSION_NAME,
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH,
        )
    
    if not _telethon_client.is_connected():
        await _telethon_client.connect()
        
        if not await _telethon_client.is_user_authorized():
            raise RuntimeError(
                "Telethon not authorized. Run auth_telethon.py locally first."
            )
    
    return _telethon_client


async def close_telethon_client() -> None:
    """Close and disconnect the Telethon client."""
    global _telethon_client
    
    if _telethon_client is not None:
        await _telethon_client.disconnect()
        _telethon_client = None
