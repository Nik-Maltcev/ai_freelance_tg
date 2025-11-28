"""Request display handlers for the Telegram bot.

Implements showing requests with pagination and refresh functionality.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import get_pagination_keyboard, get_back_keyboard
from core.models import FreelanceRequest
from services.request_service import RequestService

router = Router()

# Page size for pagination
PAGE_SIZE = 5


def format_request(request: FreelanceRequest) -> str:
    """Format a FreelanceRequest for display.
    
    Displays title, description, budget, skills, contact, and urgency indicator.
    
    Args:
        request: FreelanceRequest object to format.
        
    Returns:
        Formatted string for display.
        
    Requirements: 1.4
    """
    # Build urgency indicator
    urgency_icon = "🔴" if request.urgency == "urgent" else "🟢"
    
    # Build skills list
    skills_text = ""
    if request.skills:
        skills_str = ", ".join(str(skill) for skill in request.skills)
        skills_text = f"\n💼 Навыки: {skills_str}"
    
    # Build contact info
    contact_text = ""
    if request.contact:
        contact_text = f"\n📞 Контакт: {request.contact}"
    
    # Format the complete request
    formatted = (
        f"{urgency_icon} <b>{request.title}</b>\n\n"
        f"{request.description}\n"
        f"\n💰 Бюджет: {request.budget}"
        f"{skills_text}"
        f"{contact_text}"
        f"\n\n📅 {request.message_date.strftime('%d.%m.%Y %H:%M')}"
    )
    
    return formatted


@router.callback_query(F.data.startswith("period_"))
async def show_requests(callback: CallbackQuery, session: AsyncSession):
    """Handle period selection and show requests with pagination.
    
    Retrieves and displays paginated freelance requests from the database.
    
    Requirements: 1.3, 1.4, 1.5, 1.6
    """
    # Parse callback data: period_{days}_{category_slug}
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("❌ Ошибка обработки запроса", show_alert=True)
        return
    
    period_days = int(parts[1])
    category_slug = "_".join(parts[2:])  # Handle slugs with underscores
    
    # Get requests
    request_service = RequestService(session)
    
    # Handle "all categories" case
    category_filter = None if category_slug == "all" else category_slug
    
    requests, total_count = await request_service.get_requests(
        category=category_filter,
        days=period_days,
        offset=0,
        limit=PAGE_SIZE,
    )
    
    # Handle no results case
    if not requests:
        no_results_text = (
            f"😔 По вашему запросу не найдено фриланс-запросов.\n\n"
            f"Попробуйте:\n"
            f"• Выбрать другой период\n"
            f"• Выбрать другую категорию\n"
            f"• Вернуться в главное меню"
        )
        keyboard = get_back_keyboard()
        await callback.message.edit_text(no_results_text, reply_markup=keyboard)
        await callback.answer()
        return
    
    # Format first request
    request_text = format_request(requests[0])
    
    # Add pagination info
    request_text += f"\n\n📊 Запрос 1 из {total_count}"
    
    # Get pagination keyboard
    keyboard = get_pagination_keyboard(
        category_slug=category_slug,
        period_days=period_days,
        page=0,
        total_count=total_count,
        page_size=PAGE_SIZE,
    )
    
    # Send message with request
    await callback.message.edit_text(
        request_text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("page_"))
async def paginate_requests(callback: CallbackQuery, session: AsyncSession):
    """Handle pagination button clicks.
    
    Displays the next or previous request in the paginated list.
    
    Requirements: 1.5
    """
    # Parse callback data: page_{page_num}_{category_slug}_{period_days}
    parts = callback.data.split("_")
    
    if len(parts) < 4:
        await callback.answer("❌ Ошибка обработки запроса", show_alert=True)
        return
    
    try:
        page = int(parts[1])
        period_days = int(parts[-1])  # Last part is period_days
        category_slug = "_".join(parts[2:-1])  # Everything between page and period
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка обработки запроса", show_alert=True)
        return
    
    # Get requests for this page
    request_service = RequestService(session)
    
    # Handle "all categories" case
    category_filter = None if category_slug == "all" else category_slug
    
    offset = page * PAGE_SIZE
    requests, total_count = await request_service.get_requests(
        category=category_filter,
        days=period_days,
        offset=offset,
        limit=PAGE_SIZE,
    )
    
    # Handle edge case: page out of range
    if not requests:
        await callback.answer("❌ Страница не найдена", show_alert=True)
        return
    
    # Format first request on this page
    request_text = format_request(requests[0])
    
    # Add pagination info
    request_number = offset + 1
    request_text += f"\n\n📊 Запрос {request_number} из {total_count}"
    
    # Get pagination keyboard
    keyboard = get_pagination_keyboard(
        category_slug=category_slug,
        period_days=period_days,
        page=page,
        total_count=total_count,
        page_size=PAGE_SIZE,
    )
    
    # Edit message with new request
    await callback.message.edit_text(
        request_text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "page_info")
async def page_info_callback(callback: CallbackQuery):
    """Handle page info button click (non-clickable button).
    
    This is a non-interactive button that just shows the current page.
    """
    await callback.answer()
