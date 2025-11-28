"""Admin command handlers for the Telegram bot.

Implements /status, /parse, and /stats commands for administrators.
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import get_back_keyboard
from core.config import get_settings
from services.request_service import RequestService

router = Router()


@router.message(Command("status"))
async def status_command(message: Message, session: AsyncSession):
    """Handle /status command.
    
    Displays last parse log with timestamp, status, and metrics.
    
    Requirements: 5.1
    """
    request_service = RequestService(session)
    last_log = await request_service.get_last_parse_log()
    
    if not last_log:
        status_text = "📊 Статус парсинга\n\n❌ Логов парсинга не найдено"
    else:
        # Format timestamps
        started = last_log.started_at.strftime("%d.%m.%Y %H:%M:%S")
        finished = (
            last_log.finished_at.strftime("%d.%m.%Y %H:%M:%S")
            if last_log.finished_at
            else "В процессе..."
        )
        
        # Format status with emoji
        status_emoji = "✅" if last_log.status == "success" else "❌"
        status_display = "Успешно" if last_log.status == "success" else "Ошибка"
        
        # Build status message
        status_text = (
            f"📊 Статус парсинга\n\n"
            f"{status_emoji} Статус: {status_display}\n"
            f"⏱️ Начало: {started}\n"
            f"⏱️ Окончание: {finished}\n"
            f"📁 Чатов обработано: {last_log.chats_parsed}\n"
            f"💬 Сообщений найдено: {last_log.messages_found}\n"
            f"✨ Запросов извлечено: {last_log.requests_extracted}"
        )
        
        if last_log.error_message:
            status_text += f"\n\n⚠️ Ошибка: {last_log.error_message}"
    
    keyboard = get_back_keyboard()
    await message.answer(status_text, reply_markup=keyboard)


@router.message(Command("parse"))
async def parse_command(message: Message, session: AsyncSession):
    """Handle /parse command.
    
    Triggers manual parsing job.
    
    Requirements: 5.2
    """
    # Import here to avoid circular imports
    from worker.scheduler import trigger_parse_job
    
    try:
        # Trigger the parsing job
        await trigger_parse_job(session)
        
        parse_text = (
            "🚀 Парсинг запущен\n\n"
            "Фоновый процесс начал обработку чатов. "
            "Используйте /status для проверки прогресса."
        )
    except Exception as e:
        parse_text = (
            f"❌ Ошибка при запуске парсинга\n\n"
            f"Детали: {str(e)}"
        )
    
    keyboard = get_back_keyboard()
    await message.answer(parse_text, reply_markup=keyboard)


@router.message(Command("stats"))
async def stats_command(message: Message, session: AsyncSession):
    """Handle /stats command.
    
    Displays request counts grouped by category.
    
    Requirements: 5.3
    """
    request_service = RequestService(session)
    stats = await request_service.get_stats_by_category()
    
    if not stats:
        stats_text = "📈 Статистика\n\n❌ Запросов не найдено"
    else:
        # Build stats message
        stats_text = "📈 Статистика по категориям\n\n"
        
        total = sum(stats.values())
        
        for category, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            stats_text += f"📁 {category}: {count} ({percentage:.1f}%)\n"
        
        stats_text += f"\n📊 Всего запросов: {total}"
    
    keyboard = get_back_keyboard()
    await message.answer(stats_text, reply_markup=keyboard)
