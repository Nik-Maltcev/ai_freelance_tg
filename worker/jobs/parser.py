"""Chat parser module for parsing Telegram crypto chats.

Parses messages from the last N days and returns raw message data.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from telethon import TelegramClient
from telethon.tl.types import User

from core.config import get_settings

logger = logging.getLogger(__name__)


class ChatParser:
    """Parser for retrieving messages from Telegram chats."""
    
    def __init__(self, client: TelegramClient):
        """Initialize parser with Telethon client."""
        self.client = client
        self.settings = get_settings()
    
    async def parse_chat(
        self,
        chat_id: str,
        days: int = 2,
    ) -> list[dict[str, Any]]:
        """Parse messages from a single chat.
        
        Args:
            chat_id: Chat username (without @).
            days: Number of days to look back (default 2 = today + yesterday).
            
        Returns:
            List of message dictionaries.
        """
        messages = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        min_length = self.settings.MIN_MESSAGE_LENGTH
        
        try:
            entity = await self.client.get_entity(chat_id)
            chat_title = getattr(entity, 'title', chat_id)
            
            async for message in self.client.iter_messages(
                entity,
                offset_date=datetime.now(timezone.utc),
                reverse=False,
            ):
                # Stop if message is older than cutoff
                if message.date < cutoff_date:
                    break
                
                # Skip messages without text or too short
                if not message.text or len(message.text) < min_length:
                    continue
                
                # Get sender info
                sender_name = None
                sender_username = None
                is_bot = False
                
                if message.sender:
                    if isinstance(message.sender, User):
                        is_bot = message.sender.bot or False
                        sender_name = f"{message.sender.first_name or ''} {message.sender.last_name or ''}".strip()
                        sender_username = message.sender.username
                
                # Skip bot messages
                if is_bot:
                    continue
                
                messages.append({
                    "chat": chat_id,
                    "chat_title": chat_title,
                    "message_id": message.id,
                    "date": message.date.isoformat(),
                    "text": message.text,
                    "sender_name": sender_name,
                    "sender_username": sender_username,
                })
            
            logger.info(f"Parsed {len(messages)} messages from {chat_id}")
            
        except Exception as e:
            logger.error(f"Error parsing chat {chat_id}: {e}")
            return []
        
        return messages
    
    async def parse_all_chats(
        self,
        chat_ids: list[str],
        days: int = 2,
    ) -> list[dict[str, Any]]:
        """Parse messages from all chats.
        
        Args:
            chat_ids: List of chat usernames.
            days: Number of days to look back.
            
        Returns:
            Combined list of all messages sorted by date (newest first).
        """
        all_messages = []
        delay = self.settings.REQUEST_DELAY_SEC
        
        for i, chat_id in enumerate(chat_ids):
            # Add delay between chats (except for first one)
            if i > 0:
                await asyncio.sleep(delay)
            
            logger.info(f"Parsing chat {i + 1}/{len(chat_ids)}: {chat_id}")
            messages = await self.parse_chat(chat_id, days)
            all_messages.extend(messages)
        
        # Sort by date (newest first)
        all_messages.sort(key=lambda x: x["date"], reverse=True)
        
        logger.info(f"Total: {len(all_messages)} messages from {len(chat_ids)} chats")
        return all_messages
