"""Admin handlers for parsing and export."""

import asyncio
import json
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import get_result_keyboard, get_back_keyboard, get_main_keyboard
from core.config import get_settings, load_chats_config
from core.database import get_async_session
from core.models import ParseLog
from worker.jobs.parser import ChatParser
from worker.telethon_client import get_telethon_client

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "start_parsing")
async def start_parsing(callback: CallbackQuery, session: AsyncSession):
    """Start parsing process."""
    await callback.message.edit_text(
        "⏳ Начинаю парсинг...\n\n"
        "Это займёт 20-30 минут.\n"
        "Я отправлю уведомление когда закончу."
    )
    await callback.answer()
    
    # Run parsing in background
    asyncio.create_task(run_parsing_task(callback.from_user.id, callback.message))


async def run_parsing_task(user_id: int, message):
    """Background task for parsing."""
    from datetime import datetime
    from aiogram import Bot
    
    settings = get_settings()
    bot = Bot(token=settings.BOT_TOKEN)
    
    async_session = get_async_session()
    async with async_session() as session:
        log = ParseLog(status="running")
        session.add(log)
        await session.commit()
        await session.refresh(log)
        
        total_chats = 0
        total_messages = 0
        
        try:
            config = load_chats_config()
            chat_ids = config.get("chats", [])
            parse_days = config.get("settings", {}).get("parse_days", 2)
            
            client = await get_telethon_client()
            parser = ChatParser(client)
            
            messages = await parser.parse_all_chats(chat_ids, days=parse_days)
            total_chats = len(chat_ids)
            total_messages = len(messages)
            
            export_data = {
                "parsed_at": datetime.now().isoformat(),
                "parse_days": parse_days,
                "chats_count": total_chats,
                "messages_count": total_messages,
                "messages": messages,
            }
            
            json_data = json.dumps(export_data, ensure_ascii=False)
            
            log.finished_at = datetime.utcnow()
            log.status = "success"
            log.chats_parsed = total_chats
            log.messages_found = total_messages
            log.json_data = json_data
            await session.commit()
            
            # Notify user
            size_mb = len(json_data.encode('utf-8')) / (1024 * 1024)
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=message.message_id,
                text=(
                    f"✅ Парсинг завершён!\n\n"
                    f"📁 Чатов: {total_chats}\n"
                    f"💬 Сообщений: {total_messages}\n"
                    f"📦 Размер: {size_mb:.1f} MB\n\n"
                    f"Нажми кнопку чтобы скачать:"
                ),
                reply_markup=get_result_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            log.finished_at = datetime.utcnow()
            log.status = "failed"
            log.error_message = str(e)
            await session.commit()
            
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=message.message_id,
                text=f"❌ Ошибка парсинга:\n{str(e)}",
                reply_markup=get_back_keyboard()
            )
        finally:
            await bot.session.close()


@router.callback_query(F.data == "get_json")
async def get_json(callback: CallbackQuery, session: AsyncSession):
    """Send JSON file to user."""
    result = await session.execute(
        select(ParseLog)
        .where(ParseLog.status == "success")
        .where(ParseLog.json_data.isnot(None))
        .order_by(ParseLog.started_at.desc())
        .limit(1)
    )
    last_log = result.scalar_one_or_none()
    
    if not last_log or not last_log.json_data:
        await callback.answer("❌ Нет данных для экспорта", show_alert=True)
        return
    
    try:
        json_bytes = last_log.json_data.encode('utf-8')
        filename = f"crypto_{last_log.started_at.strftime('%Y%m%d_%H%M%S')}.json"
        document = BufferedInputFile(json_bytes, filename=filename)
        
        await callback.message.answer_document(
            document,
            caption=(
                f"📄 Экспорт сообщений\n"
                f"📅 {last_log.started_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"💬 {last_log.messages_found} сообщений"
            )
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Export failed: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "status")
async def show_status(callback: CallbackQuery, session: AsyncSession):
    """Show last parse status."""
    result = await session.execute(
        select(ParseLog).order_by(ParseLog.started_at.desc()).limit(1)
    )
    last_log = result.scalar_one_or_none()
    
    if not last_log:
        await callback.message.edit_text(
            "📊 Статус\n\n❌ Парсинг ещё не запускался",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return
    
    status_emoji = "✅" if last_log.status == "success" else "⏳" if last_log.status == "running" else "❌"
    status_text = {
        "success": "Завершён",
        "running": "В процессе",
        "failed": "Ошибка"
    }.get(last_log.status, last_log.status)
    
    text = (
        f"📊 Статус последнего парсинга\n\n"
        f"{status_emoji} Статус: {status_text}\n"
        f"📅 Начало: {last_log.started_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"📁 Чатов: {last_log.chats_parsed}\n"
        f"💬 Сообщений: {last_log.messages_found}"
    )
    
    if last_log.status == "success" and last_log.json_data:
        await callback.message.edit_text(text, reply_markup=get_result_keyboard())
    else:
        await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    
    await callback.answer()


@router.callback_query(F.data == "parsing_status")
async def parsing_status(callback: CallbackQuery):
    """Handle click on parsing status button."""
    await callback.answer("⏳ Парсинг ещё идёт, подожди...")
