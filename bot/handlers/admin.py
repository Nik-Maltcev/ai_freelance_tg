"""Admin command handlers for the Telegram bot."""

import json
import logging
from io import BytesIO

from aiogram import Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ParseLog

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("status"))
async def status_command(message: Message, session: AsyncSession):
    """Handle /status command - show last parse log."""
    result = await session.execute(
        select(ParseLog).order_by(ParseLog.started_at.desc()).limit(1)
    )
    last_log = result.scalar_one_or_none()
    
    if not last_log:
        await message.answer("📊 Логов парсинга не найдено")
        return
    
    # Format timestamps
    started = last_log.started_at.strftime("%d.%m.%Y %H:%M:%S")
    finished = (
        last_log.finished_at.strftime("%d.%m.%Y %H:%M:%S")
        if last_log.finished_at
        else "В процессе..."
    )
    
    # Format status
    status_emoji = "✅" if last_log.status == "success" else "❌"
    status_display = "Успешно" if last_log.status == "success" else "Ошибка"
    
    status_text = (
        f"📊 Статус парсинга\n\n"
        f"{status_emoji} Статус: {status_display}\n"
        f"⏱️ Начало: {started}\n"
        f"⏱️ Окончание: {finished}\n"
        f"📁 Чатов обработано: {last_log.chats_parsed}\n"
        f"💬 Сообщений найдено: {last_log.messages_found}"
    )
    
    if last_log.json_data:
        # Calculate JSON size
        size_mb = len(last_log.json_data.encode('utf-8')) / (1024 * 1024)
        status_text += f"\n📦 Размер JSON: {size_mb:.1f} MB"
    
    if last_log.error_message:
        status_text += f"\n\n⚠️ Ошибка: {last_log.error_message}"
    
    await message.answer(status_text)


@router.message(Command("export"))
async def export_command(message: Message, session: AsyncSession):
    """Handle /export command - send latest JSON file."""
    result = await session.execute(
        select(ParseLog)
        .where(ParseLog.status == "success")
        .where(ParseLog.json_data.isnot(None))
        .order_by(ParseLog.started_at.desc())
        .limit(1)
    )
    last_log = result.scalar_one_or_none()
    
    if not last_log or not last_log.json_data:
        await message.answer(
            "📭 Нет доступных экспортов.\n\n"
            "Дождитесь завершения парсинга (каждые 6 часов)."
        )
        return
    
    try:
        # Create file from JSON data
        json_bytes = last_log.json_data.encode('utf-8')
        filename = f"crypto_messages_{last_log.started_at.strftime('%Y%m%d_%H%M%S')}.json"
        
        document = BufferedInputFile(json_bytes, filename=filename)
        
        await message.answer_document(
            document,
            caption=(
                f"📄 Экспорт сообщений\n"
                f"📅 {last_log.started_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"💬 {last_log.messages_found} сообщений"
            )
        )
    except Exception as e:
        logger.error(f"Export command failed: {e}")
        await message.answer(f"❌ Ошибка отправки файла: {str(e)}")


@router.message(Command("help"))
async def help_command(message: Message):
    """Handle /help command - show available commands."""
    help_text = (
        "🤖 Crypto Parser Bot\n\n"
        "Доступные команды:\n\n"
        "/export - Скачать последний JSON\n"
        "/status - Статус последнего парсинга\n"
        "/help - Показать эту справку\n\n"
        "⏰ Парсинг запускается автоматически каждые 6 часов."
    )
    await message.answer(help_text)
