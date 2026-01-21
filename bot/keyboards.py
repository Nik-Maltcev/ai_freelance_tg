"""Keyboard builders for the Telegram bot.

Simplified - no keyboards needed for basic commands.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard with a single back button."""
    buttons = [
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="back_to_start"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
