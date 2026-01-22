"""Keyboard builders for the Telegram bot."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    buttons = [
        [InlineKeyboardButton(text="🚀 Начать парсинг", callback_data="start_parsing")],
        [InlineKeyboardButton(text="📊 Статус", callback_data="status")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_parsing_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown during parsing."""
    buttons = [
        [InlineKeyboardButton(text="⏳ Парсинг идёт...", callback_data="parsing_status")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_result_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown after parsing completes."""
    buttons = [
        [InlineKeyboardButton(text="📥 Получить JSON", callback_data="get_json")],
        [InlineKeyboardButton(text="🔄 Новый парсинг", callback_data="start_parsing")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Back to main menu keyboard."""
    buttons = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
