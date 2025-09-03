"""
Database engine and session management for dotmac-database.

Provides async engine creation, session factories, and context managers
with proper lifecycle management and error handling.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, AsyncIterator, Union, Callable

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine as sa_create_async_engine,
)
from sqlalchemy.pool import QueuePool, StaticPool, NullPool

from .types import DatabaseURL

logger = logging.getLogger(__name__)


def create_async_engine(
    database_url: DatabaseURL,
    *,
    echo: Optional[bool] = None,
    pool_size: Optional[int] = None,
    max_overflow: Optional[int] = None,
    pool_recycle: Optional[int] = None,
    pool_pre_ping: Optional[bool] = None,
    pool_timeout: Optional[int] = None,
    connect_args: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine with sensible defaults.
    
    Args:
        database_url: Database URL or SQLAlchemy URL object
        echo: Enable SQL logging (defaults to SQLALCHEMY_ECHO env var)
        pool_size: Connection pool size (default: 20)
        max_overflow: Maximum pool overflow (default: 30) 
        pool_recycle: Pool recycle time in seconds (default: 3600)
        pool_pre_ping: Enable connection health checks (default: True)
        pool_timeout: Pool checkout timeout (default: 30)
        connect_args: Additional connection arguments
        **kwargs: Additional engine arguments
        
    Returns:
        Configured AsyncEngine instance
    """
    # Convert URL if needed and handle async driver mapping
    url = _normalize_database_url(database_url)
    
    # Set defaults from environment or sensible values
    if echo is None:
        echo = os.getenv("SQLALCHEMY_ECHO", "false").lower() in ("true", "1", "on")
    
    if pool_size is None:
        pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
    
    if max_overflow is None:
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "30"))
    
    if pool_recycle is None:
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    
    if pool_pre_ping is None:
        pool_pre_ping = True
    
    if pool_timeout is None:
        pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    
    # Prepare connection args
    final_connect_args = {}
    
    # Add PostgreSQL-specific optimizations
    if "postgresql" in str(url):
        final_connect_args.update({
            "command_timeout": 60,
            "server_settings": {
                "jit": "off",  # Disable JIT for shorter queries
                "application_name": os.getenv("APP_NAME", "dotmac-app"),
            }
        })
    
    # Merge with user-provided connect_args
    if connect_args:
        final_connect_args.update(connect_args)
    
    # Choose appropriate poolclass
    poolclass = _get_poolclass(url)
    
    # Engine configuration
    engine_kwargs = {
        "echo": echo,
        "poolclass": poolclass,
        "connect_args": final_connect_args,
        **kwargs
    }
    
    # Only add pool settings for engines that support pooling
    if poolclass != StaticPool:
        engine_kwargs.update({
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_recycle": pool_recycle,
            "pool_pre_ping": pool_pre_ping,
            "pool_timeout": pool_timeout,
        })
    
    logger.info(f"Creating async engine for {_mask_password(str(url))}")
    
    return sa_create_async_engine(url, **engine_kwargs)


def create_async_sessionmaker(
    engine: AsyncEngine,
    *,
    expire_on_commit: bool = False,
    autoflush: bool = True,
    autocommit: bool = False,
    **kwargs: Any,
) -> async_sessionmaker[AsyncSession]:
    """
    Create an async session factory with sensible defaults.
    
    Args:
        engine: AsyncEngine instance
        expire_on_commit: Whether to expire objects after commit (default: False)
        autoflush: Enable automatic flushing (default: True)
        autocommit: Enable autocommit mode (default: False) 
        **kwargs: Additional sessionmaker arguments
        
    Returns:
        Configured async sessionmaker
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=expire_on_commit,
        autoflush=autoflush,
        autocommit=autocommit,
        **kwargs
    )


@asynccontextmanager
async def with_async_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    auto_commit: bool = True,
    auto_rollback: bool = True,
) -> AsyncIterator[AsyncSession]:
    """
    Async context manager for database sessions with automatic lifecycle management.
    
    Args:
        sessionmaker: Async sessionmaker instance
        auto_commit: Automatically commit successful transactions (default: True)
        auto_rollback: Automatically rollback failed transactions (default: True)
        
    Yields:
        AsyncSession instance with automatic cleanup
        
    Example:
        async with with_async_session(sessionmaker) as session:
            session.add(User(name="John"))
            # Automatic commit on success, rollback on exception
    """
    session = sessionmaker()
    
    try:
        yield session
        
        if auto_commit and session.in_transaction():
            await session.commit()
            logger.debug("Session committed successfully")
            
    except Exception as e:
        if auto_rollback and session.in_transaction():
            await session.rollback()
            logger.warning(f"Session rolled back due to error: {e}")
        raise
        
    finally:
        await session.close()
        logger.debug("Session closed")


class DatabaseManager:
    """
    High-level database manager for engine and session lifecycle.
    
    Provides centralized management of database connections with
    proper startup and shutdown procedures.
    """
    
    def __init__(
        self,
        database_url: DatabaseURL,
        engine_kwargs: Optional[Dict[str, Any]] = None,
        session_kwargs: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize database manager.
        
        Args:
            database_url: Database connection URL
            engine_kwargs: Additional engine configuration
            session_kwargs: Additional session configuration
        """
        self.database_url = database_url
        self.engine_kwargs = engine_kwargs or {}
        self.session_kwargs = session_kwargs or {}
        
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None
    
    @property
    def engine(self) -> AsyncEngine:
        """Get the async engine, creating it if needed."""
        if self._engine is None:
            raise RuntimeError("Database manager not initialized. Call startup() first.")
        return self._engine
    
    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """Get the session factory, creating it if needed."""
        if self._sessionmaker is None:
            raise RuntimeError("Database manager not initialized. Call startup() first.")
        return self._sessionmaker
    
    async def startup(self) -> None:
        """Initialize database engine and session factory."""
        if self._engine is not None:
            logger.warning("Database manager already initialized")
            return
        
        logger.info("Starting up database manager")
        
        self._engine = create_async_engine(self.database_url, **self.engine_kwargs)
        self._sessionmaker = create_async_sessionmaker(self._engine, **self.session_kwargs)
        
        # Test connection
        try:
            async with self._sessionmaker() as session:
                await session.execute(sa.text("SELECT 1"))
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.error(f"Failed to establish database connection: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self) -> None:
        """Shutdown database engine and cleanup connections."""
        if self._engine is not None:
            logger.info("Shutting down database manager")
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
    
    @asynccontextmanager
    async def session(self, **kwargs: Any) -> AsyncIterator[AsyncSession]:
        """Get a database session with context management."""
        async with with_async_session(self.sessionmaker, **kwargs) as session:
            yield session


def _normalize_database_url(database_url: DatabaseURL) -> sa.URL:
    """
    Normalize database URL for async usage.
    
    Converts postgresql:// to postgresql+asyncpg:// if no driver specified.
    """
    if isinstance(database_url, str):
        url = sa.make_url(database_url)
    else:
        url = database_url
    
    # Handle async driver mapping for PostgreSQL
    if url.drivername == "postgresql":
        # Default to asyncpg for async usage
        url = url.set(drivername="postgresql+asyncpg")
        logger.debug("Converted postgresql:// to postgresql+asyncpg:// for async usage")
    
    return url


def _get_poolclass(url: sa.URL) -> type:
    """
    Get appropriate pool class for the database URL.
    
    Returns:
        Pool class appropriate for the database type
    """
    if "sqlite" in url.drivername:
        # SQLite uses StaticPool for in-memory or single connection
        if url.database in (None, ":memory:", ""):
            return StaticPool
        else:
            return NullPool  # File-based SQLite doesn't need pooling
    else:
        # PostgreSQL and other databases use QueuePool
        return QueuePool


def _mask_password(url: str) -> str:
    """Mask password in database URL for logging."""
    try:
        parsed = sa.make_url(url)
        if parsed.password:
            masked = parsed.set(password="***")
            return str(masked)
    except Exception:
        pass
    return url


# Convenience function for common use case
async def get_database_url_from_env() -> str:
    """
    Get database URL from environment variables.
    
    Checks DATABASE_URL first, then falls back to individual components.
    
    Returns:
        Database URL string
        
    Raises:
        ValueError: If no database configuration found
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    # Build from components
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME")
    username = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    
    if not all([database, username]):
        raise ValueError(
            "No database configuration found. Set DATABASE_URL or "
            "DB_HOST, DB_NAME, DB_USER, and DB_PASSWORD environment variables."
        )
    
    # Default to PostgreSQL with asyncpg
    driver = os.getenv("DB_DRIVER", "postgresql+asyncpg")
    
    auth = f"{username}:{password}" if password else username
    return f"{driver}://{auth}@{host}:{port}/{database}"