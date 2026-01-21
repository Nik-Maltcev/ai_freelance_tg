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
        settings = get_settings()
        
        # Check if user is admin
        if event.from_user and event.from_user.id in settings.ADMIN_IDS:
            return await handler(event, data)
        
        # Ignore non-admin users silently
        return None
