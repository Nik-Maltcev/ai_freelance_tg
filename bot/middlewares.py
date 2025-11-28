"""Middleware for the Telegram bot.

Implements admin command filtering and other middleware logic.
"""

from typing import Any, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, Update

from core.config import get_settings


class WhitelistMiddleware(BaseMiddleware):
    """Middleware to filter admin commands by user ID whitelist.
    
    Checks if the user is in the ADMIN_IDS list before allowing
    execution of admin commands.
    
    Requirements: 5.4
    """

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Any],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        """Process middleware.
        
        Args:
            handler: The next handler in the chain.
            event: The update event.
            data: Additional data.
            
        Returns:
            Result from the handler or None if filtered.
        """
        # Get the message from the update
        message = event.message
        
        if not message:
            return await handler(event, data)
        
        # Get settings
        settings = get_settings()
        
        # Check if this is an admin command
        if message.text and message.text.startswith("/"):
            command = message.text.split()[0].lstrip("/")
            admin_commands = {"status", "parse", "stats"}
            
            if command in admin_commands:
                # Check if user is admin
                if message.from_user.id not in settings.ADMIN_IDS:
                    # Silently ignore non-admin commands
                    return None
        
        # Call the next handler
        return await handler(event, data)
