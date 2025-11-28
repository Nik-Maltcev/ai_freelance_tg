"""Database module for async PostgreSQL connection.

Provides async engine, session factory, and database initialization.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import get_settings
from core.models import Base

# Global engine and session factory (lazy initialized)
_async_engine: AsyncEngine | None = None
_async_session: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """Get or create the async database engine.

    Returns:
        AsyncEngine instance connected to PostgreSQL.
    """
    global _async_engine
    if _async_engine is None:
        settings = get_settings()
        _async_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _async_engine


def get_async_session() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory.

    Returns:
        async_sessionmaker for creating AsyncSession instances.
    """
    global _async_session
    if _async_session is None:
        engine = get_async_engine()
        _async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session


async def init_db() -> None:
    """Initialize the database by creating all tables.

    Creates all tables defined in the models if they don't exist.
    """
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close the database connection and dispose of the engine."""
    global _async_engine, _async_session
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session = None
