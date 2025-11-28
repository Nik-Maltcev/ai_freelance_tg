"""Property-based tests for admin middleware.

Tests that admin middleware correctly filters non-admin users.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from bot.middlewares import WhitelistMiddleware


# Strategy for generating user IDs
user_id_strategy = st.integers(min_value=1, max_value=2147483647)

# Strategy for generating admin ID lists
admin_ids_strategy = st.lists(
    st.integers(min_value=1, max_value=2147483647),
    min_size=0,
    max_size=10,
    unique=True,
)

# Strategy for generating admin commands
admin_command_strategy = st.sampled_from(["/status", "/parse", "/stats"])


# **Feature: freelance-parser-bot, Property 13: Admin middleware filtering**
@given(
    user_id=user_id_strategy,
    admin_ids=admin_ids_strategy,
    command=admin_command_strategy,
)
@settings(max_examples=100, deadline=None)
def test_admin_middleware_filtering(
    user_id: int,
    admin_ids: list[int],
    command: str,
):
    """
    Property 13: Admin middleware filtering

    *For any* user_id not in ADMIN_IDS list, admin command handlers SHALL not execute.

    **Validates: Requirements 5.4**
    """
    async def run_test():
        # Create middleware
        middleware = WhitelistMiddleware()
        
        # Create mock handler
        handler = AsyncMock(return_value="handler_result")
        
        # Create mock message with command
        message = MagicMock()
        message.text = command
        message.from_user.id = user_id
        
        # Create mock update
        update = MagicMock()
        update.message = message
        
        # Mock settings
        with patch("bot.middlewares.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.ADMIN_IDS = admin_ids
            mock_get_settings.return_value = mock_settings
            
            # Call middleware
            result = await middleware(handler, update, {})
            
            # Check if user is admin
            is_admin = user_id in admin_ids
            
            if is_admin:
                # Admin users should have handler called
                handler.assert_called_once()
                assert result == "handler_result"
            else:
                # Non-admin users should NOT have handler called
                handler.assert_not_called()
                assert result is None
    
    import asyncio
    asyncio.run(run_test())


@pytest.mark.asyncio
async def test_admin_middleware_allows_non_admin_commands():
    """Test that non-admin commands are always allowed."""
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="handler_result")
    
    # Create mock message with non-admin command
    message = MagicMock()
    message.text = "/start"
    message.from_user.id = 12345
    
    # Create mock update
    update = MagicMock()
    update.message = message
    
    # Mock settings with empty admin list
    with patch("bot.middlewares.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.ADMIN_IDS = []
        mock_get_settings.return_value = mock_settings
        
        # Call middleware
        result = await middleware(handler, update, {})
        
        # Non-admin commands should always be allowed
        handler.assert_called_once()
        assert result == "handler_result"


@pytest.mark.asyncio
async def test_admin_middleware_handles_no_message():
    """Test that middleware handles updates without messages."""
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="handler_result")
    
    # Create mock update without message
    update = MagicMock()
    update.message = None
    
    # Mock settings
    with patch("bot.middlewares.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.ADMIN_IDS = [123]
        mock_get_settings.return_value = mock_settings
        
        # Call middleware
        result = await middleware(handler, update, {})
        
        # Handler should be called for non-message updates
        handler.assert_called_once()
        assert result == "handler_result"
