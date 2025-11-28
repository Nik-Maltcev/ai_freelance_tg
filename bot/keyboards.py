"""Keyboard builders for the Telegram bot.

Provides functions to create inline keyboards for category selection,
period selection, pagination, and navigation.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from core.models import Category


def get_categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    """Build inline keyboard with all available categories.
    
    Creates a keyboard with one button per category plus an "All categories" button.
    Each category button has callback_data in format "cat_{slug}".
    
    Args:
        categories: List of active Category objects.
        
    Returns:
        InlineKeyboardMarkup with category buttons arranged in 2 columns.
        
    Requirements: 1.1
    """
    buttons = []
    
    # Add category buttons (2 per row)
    for i, category in enumerate(categories):
        button = InlineKeyboardButton(
            text=category.name,
            callback_data=f"cat_{category.slug}"
        )
        
        if i % 2 == 0:
            buttons.append([button])
        else:
            buttons[-1].append(button)
    
    # Add "All categories" button
    if len(categories) == 0:
        # If no categories, create a new row with just the "All categories" button
        buttons.append([
            InlineKeyboardButton(
                text="📊 All categories",
                callback_data="cat_all"
            )
        ])
    elif len(categories) % 2 == 1:
        # If odd number of categories, add on a new row
        buttons.append([
            InlineKeyboardButton(
                text="📊 All categories",
                callback_data="cat_all"
            )
        ])
    else:
        # If even number of categories, add to the last row
        buttons[-1].append(
            InlineKeyboardButton(
                text="📊 All categories",
                callback_data="cat_all"
            )
        )
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_period_keyboard(category_slug: str) -> InlineKeyboardMarkup:
    """Build inline keyboard for period selection.
    
    Creates a keyboard with period options (7 days, 30 days).
    Each button has callback_data in format "period_{days}_{category_slug}".
    
    Args:
        category_slug: The selected category slug.
        
    Returns:
        InlineKeyboardMarkup with period selection buttons.
        
    Requirements: 1.2
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📅 Last 7 days",
                callback_data=f"period_7_{category_slug}"
            ),
            InlineKeyboardButton(
                text="📅 Last 30 days",
                callback_data=f"period_30_{category_slug}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Back",
                callback_data="back_to_categories"
            ),
        ],
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pagination_keyboard(
    category_slug: str,
    period_days: int,
    page: int,
    total_count: int,
    page_size: int = 5,
) -> InlineKeyboardMarkup:
    """Build inline keyboard for pagination controls.
    
    Creates navigation buttons based on current page and total count.
    - Shows "Previous" button if page > 0
    - Shows "Next" button if there are more pages
    - Shows current page info
    
    Args:
        category_slug: The selected category slug.
        period_days: The selected period in days.
        page: Current page number (0-indexed).
        total_count: Total number of requests.
        page_size: Number of requests per page (default 5).
        
    Returns:
        InlineKeyboardMarkup with pagination controls.
        
    Requirements: 1.5
    """
    buttons = []
    
    # Calculate pagination info
    total_pages = (total_count + page_size - 1) // page_size
    has_previous = page > 0
    has_next = (page + 1) * page_size < total_count
    
    # Previous and Next buttons
    nav_buttons = []
    
    if has_previous:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=f"page_{page - 1}_{category_slug}_{period_days}"
            )
        )
    
    # Page info button (non-clickable)
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"Page {page + 1}/{total_pages}",
            callback_data="page_info"
        )
    )
    
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"page_{page + 1}_{category_slug}_{period_days}"
            )
        )
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Back button
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Back to categories",
            callback_data="back_to_categories"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard with a single back button.
    
    Returns:
        InlineKeyboardMarkup with a back button.
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🔙 Back",
                callback_data="back_to_categories"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
