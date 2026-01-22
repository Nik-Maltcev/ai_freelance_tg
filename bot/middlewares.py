"""Middlewares for the Telegram bot."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

from core.config import get_settings


class AdminMiddleware(BaseMiddleware):
    """Middleware that restricts bot access to admin users only."""

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        import logging
        logger = logging.getLogger(__name__)
        
        settings = get_settings()
        
        # Get user from message or callback
        user = getattr(event, 'from_user', None)
        
        logger.info(f"User: {user.id if user else None}, ADMIN_IDS: {settings.ADMIN_IDS}")
        
        if user and user.id in settings.ADMIN_IDS:
            logger.info(f"User {user.id} is admin, allowing")
            return await handler(event, data)
        
        logger.info(f"User {user.id if user else None} is NOT admin, blocking")
        return None
