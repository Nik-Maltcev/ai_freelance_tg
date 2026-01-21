"""Worker main entry point.

Starts the worker process with APScheduler for periodic parsing.
"""

import asyncio
import logging
import signal
import sys

from core.config import get_settings
from core.database import init_db
from worker.scheduler import create_scheduler, parse_chats_job
from worker.telethon_client import close_telethon_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main worker entry point."""
    logger.info("Starting worker...")
    
    # Validate settings
    try:
        settings = get_settings()
        logger.info(f"Parse days: {settings.PARSE_DAYS}")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Initialize database (drop old tables to update schema)
    try:
        await init_db(drop_existing=True)
        logger.info("Database initialized (schema updated)")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)
    
    # Create scheduler
    scheduler = create_scheduler()
    
    # Setup shutdown handler
    shutdown_event = asyncio.Event()
    
    def handle_shutdown(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        shutdown_event.set()
    
    # Register signal handlers (Unix only)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)
    
    try:
        # Run initial parsing job
        logger.info("Running initial parsing job...")
        try:
            await parse_chats_job()
        except Exception as e:
            logger.error(f"Initial parsing job failed: {e}")
        
        # Start scheduler
        scheduler.start()
        logger.info("Scheduler started")
        
        # Wait for shutdown
        if sys.platform == "win32":
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
        else:
            await shutdown_event.wait()
        
    finally:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        
        logger.info("Closing Telethon client...")
        await close_telethon_client()
        
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
