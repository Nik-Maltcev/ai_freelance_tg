"""Worker main entry point.

Starts the worker process with APScheduler for periodic parsing jobs.
Executes an initial parsing job on startup, then runs on configured interval.
"""

import asyncio
import logging
import signal
import sys

from core.config import get_settings
from core.database import init_db
from worker.scheduler import create_scheduler, parse_and_analyze_job
from worker.telethon_client import close_telethon_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main worker entry point.
    
    1. Initializes database
    2. Runs initial parsing job
    3. Starts scheduler for periodic jobs
    4. Handles graceful shutdown
    
    Requirements: 2.1
    """
    logger.info("Starting worker...")
    
    # Validate settings
    try:
        settings = get_settings()
        logger.info(f"Parse interval: {settings.PARSE_INTERVAL_HOURS} hours")
        logger.info(f"TTL: {settings.MESSAGES_TTL_DAYS} days")
        logger.info(f"Batch size: {settings.BATCH_SIZE}")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
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
            await parse_and_analyze_job()
        except Exception as e:
            logger.error(f"Initial parsing job failed: {e}")
            # Continue anyway, scheduler will retry
        
        # Start scheduler
        scheduler.start()
        logger.info("Scheduler started")
        
        # Wait for shutdown signal
        if sys.platform == "win32":
            # On Windows, just run forever until Ctrl+C
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
        else:
            await shutdown_event.wait()
        
    finally:
        # Cleanup
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        
        logger.info("Closing Telethon client...")
        await close_telethon_client()
        
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
