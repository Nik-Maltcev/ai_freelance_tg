"""Start command handler for the Telegram bot.

Implements /start command and category selection callbacks.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import get_categories_keyboard, get_period_keyboard
from services.category_service import CategoryService

router = Router()


@router.message(Command("start"))
async def start_command(message: Message, session: AsyncSession):
    """Handle /start command.
    
    Displays welcome message with inline keyboard containing all available categories.
    
    Requirements: 1.1
    """
    # Get all active categories
    category_service = CategoryService(session)
    categories = await category_service.get_all_active()
    
    # Build welcome message
    welcome_text = (
        "👋 Добро пожаловать в Freelance Parser Bot!\n\n"
        "Выберите категорию фриланс-запросов, которая вас интересует:"
    )
    
    # Get keyboard with categories
    keyboard = get_categories_keyboard(categories)
    
    # Send welcome message
    await message.answer(welcome_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("cat_"))
async def category_selected(callback: CallbackQuery, session: AsyncSession):
    """Handle category selection callback.
    
    Displays period selection options (7 days, 30 days) when a category is selected.
    
    Requirements: 1.2
    """
    # Extract category slug from callback data
    category_slug = callback.data.replace("cat_", "")
    
    # Get category info
    category_service = CategoryService(session)
    category = await category_service.get_by_slug(category_slug)
    
    if category_slug == "all":
        # Special case: "All categories" selected
        category_text = "📊 Все категории"
    elif category:
        category_text = f"📁 {category.name}"
    else:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return
    
    # Build message with period selection
    period_text = (
        f"{category_text}\n\n"
        "Выберите период для поиска запросов:"
    )
    
    # Get keyboard with period options
    keyboard = get_period_keyboard(category_slug)
    
    # Edit message with period selection
    await callback.message.edit_text(period_text, reply_markup=keyboard)
    await callback.answer()
