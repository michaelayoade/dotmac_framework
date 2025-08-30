"""
Database session management for DotMac Framework.
Provides async database session dependency injection.
"""

import logging
import os
from typing import AsyncGenerator, Optional

from sqlalchemy.engine.events import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool

logger = logging.getLogger(__name__)

# Global variables for session management
_async_engine = None
_async_session_factory = None


def get_database_url() -> str:
    """Get database URL from environment with fallback."""
    database_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

    # Convert postgres:// to postgresql+asyncpg:// for async support
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("sqlite://"):
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    return database_url


def create_async_database_engine():
    """Create async database engine with proper configuration."""
    global _async_engine, _async_session_factory

    if _async_engine is not None:
        return _async_engine

    database_url = get_database_url()

    # Engine configuration based on database type
    engine_kwargs = {
        "echo": os.environ.get("SQL_DEBUG", "false").lower() == "true",
        "future": True,
    }

    if "sqlite" in database_url:
        # SQLite configuration
        engine_kwargs.update(
            {"poolclass": NullPool, "connect_args": {"check_same_thread": False}}
        )
    else:
        # PostgreSQL configuration
        engine_kwargs.update(
            {
                "poolclass": QueuePool,
                "pool_size": int(os.environ.get("DB_POOL_SIZE", "10")),
                "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "20")),
                "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", "30")),
                "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", "3600")),
            }
        )

    try:
        _async_engine = create_async_engine(database_url, **engine_kwargs)

        # Create session factory
        _async_session_factory = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        logger.info(
            f"Created async database engine for: {database_url.split('@')[0]}..."
        )

        return _async_engine

    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides async database session.

    Yields:
        AsyncSession: Database session

    Usage:
        @app.get("/users/")
        async def get_users(db: AsyncSession = Depends(get_async_db)):
            # Use db session
            pass
    """
    global _async_session_factory

    # Ensure engine and session factory exist
    if _async_session_factory is None:
        create_async_database_engine()

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def get_async_db_session() -> AsyncSession:
    """
    Get a new async database session (not a dependency).

    Returns:
        AsyncSession: New database session

    Note:
        Caller is responsible for closing the session.
    """
    global _async_session_factory

    if _async_session_factory is None:
        create_async_database_engine()

    return _async_session_factory()


# Health check function
async def check_database_health() -> bool:
    """
    Check database connection health.

    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        async with _async_session_factory() as session:
            # Simple query to check connection
            result = await session.execute("SELECT 1")
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


# Initialize on import if environment is set
if os.environ.get("ENVIRONMENT") in ["production", "staging", "development"]:
    try:
        create_async_database_engine()
    except Exception as e:
        logger.warning(f"Failed to initialize database engine on import: {e}")
