"""Chat parser module for parsing Telegram chats.

Provides ChatParser class for retrieving and filtering messages
from Telegram chats using Telethon.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from telethon import TelegramClient
from telethon.tl.types import User

from core.config import get_settings

logger = logging.getLogger(__name__)


def filter_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter messages by length and sender type.
    
    Filters out messages that:
    - Have text length < 50 characters
    - Are from bot accounts
    
    Args:
        messages: List of message dictionaries with 'text' and 'is_bot' fields.
        
    Returns:
        Filtered list of messages meeting the criteria.
    """
    return [
        msg for msg in messages
        if len(msg.get("text", "")) >= 50 and not msg.get("is_bot", False)
    ]


class ChatParser:
    """Parser for retrieving messages from Telegram chats."""
    
    def __init__(self, client: TelegramClient):
        """Initialize parser with Telethon client.
        
        Args:
            client: Connected TelegramClient instance.
        """
        self.client = client
        self.settings = get_settings()
    
    async def parse_chat(
        self,
        chat_id: str | int,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Parse messages from a single chat.
        
        Retrieves messages from the last N days, filters by length
        and sender type.
        
        Args:
            chat_id: Chat ID or username (e.g., "@channel_name" or -100123456).
            days: Number of days to look back (default 7).
            
        Returns:
            List of filtered message dictionaries with fields:
            - text: Message text
            - message_id: Telegram message ID
            - message_date: Message datetime
            - chat_id: Source chat identifier
            - is_bot: Whether sender is a bot
        """
        messages = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        try:
            entity = await self.client.get_entity(chat_id)
            
            async for message in self.client.iter_messages(
                entity,
                offset_date=datetime.now(timezone.utc),
                reverse=False,
            ):
                # Stop if message is older than cutoff
                if message.date < cutoff_date:
                    break
                
                # Skip messages without text
                if not message.text:
                    continue
                
                # Check if sender is a bot
                is_bot = False
                if message.sender and isinstance(message.sender, User):
                    is_bot = message.sender.bot or False
                
                messages.append({
                    "text": message.text,
                    "message_id": message.id,
                    "message_date": message.date.replace(tzinfo=None),
                    "chat_id": str(chat_id),
                    "is_bot": is_bot,
                })
            
            logger.info(f"Parsed {len(messages)} messages from {chat_id}")
            
        except Exception as e:
            logger.error(f"Error parsing chat {chat_id}: {e}")
            return []
        
        # Filter messages by length and sender
        filtered = filter_messages(messages)
        logger.info(f"Filtered to {len(filtered)} messages from {chat_id}")
        
        return filtered
    
    async def parse_category(
        self,
        category_slug: str,
        chat_ids: list[str | int],
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Parse messages from all chats in a category.
        
        Parses each chat with a configurable delay between requests
        to prevent rate limiting.
        
        Args:
            category_slug: Category identifier for tagging messages.
            chat_ids: List of chat IDs or usernames to parse.
            days: Number of days to look back (default 7).
            
        Returns:
            Combined list of messages from all chats with category field added.
        """
        all_messages = []
        delay = self.settings.REQUEST_DELAY_SEC
        
        for i, chat_id in enumerate(chat_ids):
            # Add delay between chats (except for first one)
            if i > 0:
                await asyncio.sleep(delay)
            
            messages = await self.parse_chat(chat_id, days)
            
            # Add category to each message
            for msg in messages:
                msg["category"] = category_slug
            
            all_messages.extend(messages)
        
        logger.info(
            f"Category '{category_slug}': parsed {len(all_messages)} messages "
            f"from {len(chat_ids)} chats"
        )
        
        return all_messages
