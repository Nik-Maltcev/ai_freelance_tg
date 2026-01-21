"""Scheduler module for periodic parsing jobs.

Parses crypto chats and saves messages to database.
"""

import json
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.config import get_settings, load_chats_config
from core.database import get_async_session
from core.models import ParseLog
from worker.jobs.parser import ChatParser
from worker.telethon_client import get_telethon_client

logger = logging.getLogger(__name__)


async def parse_chats_job() -> int | None:
    """Main parsing job that parses chats and saves to database.
    
    Returns:
        ParseLog ID, or None on failure.
    """
    settings = get_settings()
    
    async_session = get_async_session()
    async with async_session() as session:
        # Create parse log
        log = ParseLog(status="running")
        session.add(log)
        await session.commit()
        await session.refresh(log)
        log_id = log.id
        logger.info(f"Started parsing job, log_id={log_id}")
        
        total_chats = 0
        total_messages = 0
        
        try:
            # Load chat configuration
            config = load_chats_config()
            chat_ids = config.get("chats", [])
            parse_days = config.get("settings", {}).get("parse_days", 2)
            
            if not chat_ids:
                raise ValueError("No chats configured")
            
            # Get Telethon client
            client = await get_telethon_client()
            parser = ChatParser(client)
            
            # Parse all chats
            messages = await parser.parse_all_chats(chat_ids, days=parse_days)
            total_chats = len(chat_ids)
            total_messages = len(messages)
            
            # Create JSON data
            export_data = {
                "parsed_at": datetime.now().isoformat(),
                "parse_days": parse_days,
                "chats_count": total_chats,
                "messages_count": total_messages,
                "messages": messages,
            }
            
            # Save to database
            log.finished_at = datetime.utcnow()
            log.status = "success"
            log.chats_parsed = total_chats
            log.messages_found = total_messages
            log.json_data = json.dumps(export_data, ensure_ascii=False)
            await session.commit()
            
            logger.info(f"Saved {total_messages} messages to database")
            logger.info(
                f"Parsing job completed: {total_chats} chats, {total_messages} messages"
            )
            
            return log_id
            
        except Exception as e:
            logger.error(f"Parsing job failed: {e}")
            log.finished_at = datetime.utcnow()
            log.status = "failed"
            log.chats_parsed = total_chats
            log.messages_found = total_messages
            log.error_message = str(e)
            await session.commit()
            raise


async def trigger_parse_job() -> int | None:
    """Trigger manual parsing job.
    
    Returns:
        ParseLog ID.
    """
    return await parse_chats_job()


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure APScheduler for periodic parsing."""
    scheduler = AsyncIOScheduler()
    
    # Run every 6 hours
    scheduler.add_job(
        parse_chats_job,
        trigger=IntervalTrigger(hours=6),
        id="parse_chats",
        name="Parse crypto Telegram chats",
        replace_existing=True,
    )
    
    logger.info("Scheduler configured with 6h interval")
    return scheduler
