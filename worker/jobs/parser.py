"""Chat parser module for parsing Telegram crypto chats."""

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
        self.client = client
        self.settings = get_settings()
    
    async def ensure_connected(self):
        """Ensure client is connected, reconnect if needed."""
        if not self.client.is_connected():
            logger.info("Reconnecting to Telegram...")
            await self.client.connect()
            if not await self.client.is_user_authorized():
                raise RuntimeError("Telethon not authorized")
    
    async def parse_chat(
        self,
        chat_id: str,
        days: int = 2,
    ) -> list[dict[str, Any]]:
        """Parse messages from a single chat."""
        messages = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        min_length = self.settings.MIN_MESSAGE_LENGTH
        
        try:
            # Ensure connected before each chat
            await self.ensure_connected()
            
            entity = await self.client.get_entity(chat_id)
            chat_title = getattr(entity, 'title', chat_id)
            
            async for message in self.client.iter_messages(
                entity,
                offset_date=datetime.now(timezone.utc),
                reverse=False,
            ):
                if message.date < cutoff_date:
                    break
                
                if not message.text or len(message.text) < min_length:
                    continue
                
                sender_name = None
                sender_username = None
                is_bot = False
                
                if message.sender:
                    if isinstance(message.sender, User):
                        is_bot = message.sender.bot or False
                        sender_name = f"{message.sender.first_name or ''} {message.sender.last_name or ''}".strip()
                        sender_username = message.sender.username
                
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
            # Try to reconnect for next chat
            try:
                await self.client.disconnect()
                await asyncio.sleep(2)
                await self.client.connect()
            except:
                pass
            return []
        
        return messages
    
    async def parse_all_chats(
        self,
        chat_ids: list[str],
        days: int = 2,
    ) -> list[dict[str, Any]]:
        """Parse messages from all chats."""
        all_messages = []
        delay = self.settings.REQUEST_DELAY_SEC
        
        for i, chat_id in enumerate(chat_ids):
            if i > 0:
                await asyncio.sleep(delay)
            
            # Reconnect every 100 chats to avoid disconnection
            if i > 0 and i % 100 == 0:
                logger.info(f"Reconnecting after {i} chats...")
                try:
                    await self.client.disconnect()
                    await asyncio.sleep(3)
                    await self.client.connect()
                except Exception as e:
                    logger.error(f"Reconnect failed: {e}")
            
            logger.info(f"Parsing chat {i + 1}/{len(chat_ids)}: {chat_id}")
            messages = await self.parse_chat(chat_id, days)
            all_messages.extend(messages)
        
        all_messages.sort(key=lambda x: x["date"], reverse=True)
        
        logger.info(f"Total: {len(all_messages)} messages from {len(chat_ids)} chats")
        return all_messages
