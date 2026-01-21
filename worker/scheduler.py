"""Scheduler module for periodic parsing jobs.

Parses crypto chats and saves messages to JSON files.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.config import get_settings, load_chats_config
from core.database import get_async_session
from core.models import ParseLog
from worker.jobs.parser import ChatParser
from worker.telethon_client import get_telethon_client

logger = logging.getLogger(__name__)

# Directory for JSON exports
EXPORT_DIR = Path("exports")


async def parse_chats_job() -> str | None:
    """Main parsing job that parses chats and saves to JSON.
    
    Returns:
        Path to the generated JSON file, or None on failure.
    """
    settings = get_settings()
    
    # Ensure export directory exists
    EXPORT_DIR.mkdir(exist_ok=True)
    
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
        json_file = None
        
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
            
            # Generate JSON filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file = EXPORT_DIR / f"crypto_messages_{timestamp}.json"
            
            # Save to JSON
            export_data = {
                "parsed_at": datetime.now().isoformat(),
                "parse_days": parse_days,
                "chats_count": total_chats,
                "messages_count": total_messages,
                "messages": messages,
            }
            
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {total_messages} messages to {json_file}")
            
            # Update parse log
            log.finished_at = datetime.utcnow()
            log.status = "success"
            log.chats_parsed = total_chats
            log.messages_found = total_messages
            log.json_file = str(json_file)
            await session.commit()
            
            logger.info(
                f"Parsing job completed: {total_chats} chats, {total_messages} messages"
            )
            
            return str(json_file)
            
        except Exception as e:
            logger.error(f"Parsing job failed: {e}")
            log.finished_at = datetime.utcnow()
            log.status = "failed"
            log.chats_parsed = total_chats
            log.messages_found = total_messages
            log.error_message = str(e)
            await session.commit()
            raise


async def trigger_parse_job() -> str | None:
    """Trigger manual parsing job.
    
    Returns:
        Path to the generated JSON file.
    """
    return await parse_chats_job()


def get_latest_export() -> Path | None:
    """Get the most recent JSON export file.
    
    Returns:
        Path to the latest export file, or None if no exports exist.
    """
    if not EXPORT_DIR.exists():
        return None
    
    json_files = list(EXPORT_DIR.glob("crypto_messages_*.json"))
    if not json_files:
        return None
    
    # Sort by modification time, newest first
    json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return json_files[0]


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure APScheduler for periodic parsing.
    
    Returns:
        Configured AsyncIOScheduler instance (not started).
    """
    settings = get_settings()
    
    scheduler = AsyncIOScheduler()
    
    # Add parsing job - run every 6 hours by default
    scheduler.add_job(
        parse_chats_job,
        trigger=IntervalTrigger(hours=6),
        id="parse_chats",
        name="Parse crypto Telegram chats",
        replace_existing=True,
    )
    
    logger.info("Scheduler configured with 6h interval")
    
    return scheduler
