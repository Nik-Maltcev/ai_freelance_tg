"""Telethon client singleton for Telegram chat parsing.

Provides a singleton Telethon client for accessing Telegram chats
via the userbot API.
"""

from telethon import TelegramClient
from telethon.sessions import StringSession

from core.config import get_settings

# Global singleton client
_telethon_client: TelegramClient | None = None


async def get_telethon_client() -> TelegramClient:
    """Get or create the singleton Telethon client.
    
    Creates a new TelegramClient if one doesn't exist, connects it,
    and returns the connected client.
    
    Returns:
        Connected TelegramClient instance.
        
    Raises:
        Exception: If connection or authentication fails.
    """
    global _telethon_client
    
    if _telethon_client is None:
        settings = get_settings()
        
        # Create client with string session for Railway deployment
        _telethon_client = TelegramClient(
            StringSession(),
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH,
        )
    
    if not _telethon_client.is_connected():
        await _telethon_client.connect()
        
        # Start client if not authorized
        if not await _telethon_client.is_user_authorized():
            settings = get_settings()
            await _telethon_client.start(phone=settings.TELEGRAM_PHONE)
    
    return _telethon_client


async def close_telethon_client() -> None:
    """Close and disconnect the Telethon client."""
    global _telethon_client
    
    if _telethon_client is not None:
        await _telethon_client.disconnect()
        _telethon_client = None
