"""Main entry point for the Telegram bot.

Initializes the bot, registers handlers, and starts the dispatcher.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from core.config import get_settings, load_chats_config
from core.database import init_db
from core.models import Base
from bot.handlers import start, requests, admin
from bot.middlewares import WhitelistMiddleware
from services.category_service import CategoryService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def setup_database(settings) -> async_sessionmaker:
    """Initialize database and return session factory.
    
    Args:
        settings: Application settings.
        
    Returns:
        Async session maker factory.
    """
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    return async_session_factory


async def sync_categories(session_factory: async_sessionmaker, settings) -> None:
    """Sync categories from config file to database.
    
    Args:
        session_factory: Async session factory.
        settings: Application settings.
    """
    try:
        # Load config
        config = load_chats_config("config/chats.yaml")
        
        # Sync categories
        async with session_factory() as session:
            category_service = CategoryService(session)
            await category_service.sync_from_config(config)
            logger.info("Categories synced successfully")
    except FileNotFoundError:
        logger.warning("config/chats.yaml not found, skipping category sync")
    except Exception as e:
        logger.error(f"Error syncing categories: {e}")


async def main():
    """Main bot startup function.
    
    Initializes bot, registers handlers, and starts dispatcher.
    
    Requirements: 7.3
    """
    # Get settings
    settings = get_settings()
    
    # Setup database
    logger.info("Setting up database...")
    session_factory = await setup_database(settings)
    
    # Sync categories from config
    logger.info("Syncing categories...")
    await sync_categories(session_factory, settings)
    
    # Create bot and dispatcher
    logger.info("Initializing bot...")
    bot = Bot(token=settings.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register middlewares
    dp.message.middleware(WhitelistMiddleware())
    
    # Session middleware to inject database session into handlers
    from aiogram import BaseMiddleware
    from typing import Callable, Dict, Any, Awaitable
    from aiogram.types import TelegramObject
    
    class SessionMiddleware(BaseMiddleware):
        async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
        ) -> Any:
            async with session_factory() as session:
                data["session"] = session
                return await handler(event, data)
    
    dp.update.middleware(SessionMiddleware())
    
    # Register routers
    dp.include_router(start.router)
    dp.include_router(requests.router)
    dp.include_router(admin.router)
    
    # Start polling
    logger.info("Bot started, polling for updates...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
