"""Scheduler module for periodic parsing jobs.

Provides APScheduler-based scheduling for parsing and analyzing
Telegram chats on a configurable interval.
"""

import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.config import get_settings, load_chats_config
from core.database import async_session
from services.category_service import CategoryService
from services.request_service import RequestService
from worker.jobs.analyzer import GeminiAnalyzer
from worker.jobs.parser import ChatParser
from worker.telethon_client import get_telethon_client

logger = logging.getLogger(__name__)


async def parse_and_analyze_job() -> None:
    """Main parsing job that parses chats and analyzes messages.
    
    This job:
    1. Creates a parse log entry
    2. Loads chat configuration
    3. Parses messages from all configured chats
    4. Analyzes messages using Gemini API
    5. Saves extracted requests to database
    6. Updates parse log with results
    
    Requirements: 2.1, 2.2, 2.6
    """
    settings = get_settings()
    
    async with async_session() as session:
        request_service = RequestService(session)
        category_service = CategoryService(session)
        
        # Create parse log
        log_id = await request_service.create_parse_log()
        logger.info(f"Started parsing job, log_id={log_id}")
        
        total_chats = 0
        total_messages = 0
        total_requests = 0
        
        try:
            # Load chat configuration
            config = load_chats_config()
            categories = config.get("categories", {})
            
            # Sync categories to database
            await category_service.sync_from_config(config)
            
            # Get Telethon client
            client = await get_telethon_client()
            parser = ChatParser(client)
            analyzer = GeminiAnalyzer()
            
            # Parse each category
            for slug, cat_data in categories.items():
                chat_ids = cat_data.get("chats", [])
                if not chat_ids:
                    continue
                
                logger.info(f"Parsing category '{slug}' with {len(chat_ids)} chats")
                
                # Parse messages from category chats
                messages = await parser.parse_category(slug, chat_ids, days=7)
                total_chats += len(chat_ids)
                total_messages += len(messages)

                
                if not messages:
                    logger.info(f"No messages found for category '{slug}'")
                    continue
                
                # Analyze messages with Gemini
                requests = await analyzer.analyze_all(messages)
                
                if requests:
                    # Add message text for hash computation
                    message_lookup = {m["message_id"]: m for m in messages}
                    for req in requests:
                        msg_id = req.get("source_message_id")
                        original = message_lookup.get(msg_id, {})
                        req["message_text"] = original.get("text", "")
                    
                    # Save requests
                    saved = await request_service.save_requests(requests)
                    total_requests += saved
                    logger.info(f"Saved {saved} requests for category '{slug}'")
                
                # Update category last_parsed_at
                await category_service.update_last_parsed(slug)
            
            # Cleanup old requests
            deleted = await request_service.cleanup_old_requests(
                days=settings.MESSAGES_TTL_DAYS
            )
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old requests")
            
            # Finish parse log with success
            await request_service.finish_parse_log(
                log_id=log_id,
                status="success",
                chats_parsed=total_chats,
                messages_found=total_messages,
                requests_extracted=total_requests,
            )
            logger.info(
                f"Parsing job completed: {total_chats} chats, "
                f"{total_messages} messages, {total_requests} requests"
            )
            
        except Exception as e:
            logger.error(f"Parsing job failed: {e}")
            await request_service.finish_parse_log(
                log_id=log_id,
                status="failed",
                chats_parsed=total_chats,
                messages_found=total_messages,
                requests_extracted=total_requests,
                error_message=str(e),
            )
            raise


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure APScheduler for periodic parsing.
    
    Creates an AsyncIOScheduler with an interval trigger based on
    PARSE_INTERVAL_HOURS setting.
    
    Returns:
        Configured AsyncIOScheduler instance (not started).
        
    Requirements: 2.1, 2.2
    """
    settings = get_settings()
    
    scheduler = AsyncIOScheduler()
    
    # Add parsing job with interval trigger
    scheduler.add_job(
        parse_and_analyze_job,
        trigger=IntervalTrigger(hours=settings.PARSE_INTERVAL_HOURS),
        id="parse_and_analyze",
        name="Parse and analyze Telegram chats",
        replace_existing=True,
    )
    
    logger.info(
        f"Scheduler configured with {settings.PARSE_INTERVAL_HOURS}h interval"
    )
    
    return scheduler
