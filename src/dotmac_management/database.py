"""
Database configuration and session management for DotMac Management Platform.

This module provides the database engine, session factory, and dependency injection
functions for the management platform's multi-tenant SaaS operations.
"""

import os
from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from dotmac.database.base import Base

# Database URL - use environment variable or fallback to default
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://dotmac:dotmac@localhost:5432/dotmac_framework"
)

# Convert to async URL if not already
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
elif DATABASE_URL.startswith("postgresql+asyncpg://"):
    ASYNC_DATABASE_URL = DATABASE_URL
else:
    ASYNC_DATABASE_URL = "NOT_YET_IMPLEMENTED_ExprJoinedStr"


# Use DRY shared base from dotmac_shared

_engine: Optional[AsyncEngine] = None
_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def _init_engine() -> None:
    """Initialize the async engine and session maker lazily."""
    global _engine, _session_maker
    if _engine is not None and _session_maker is not None:
        return

    _engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
        pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
        pool_pre_ping=True,
        pool_recycle=3600,  # Recycle connections after 1 hour
    )
    _session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False,
    )


def get_engine() -> AsyncEngine:
    """Get the initialized async engine, initializing if necessary."""
    _init_engine()
    assert _engine is not None
    return _engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection function for getting database sessions.

    Yields:
        AsyncSession: Database session for request handling
    """
    _init_engine()
    assert _session_maker is not None
    async with _session_maker() as session:
        try:
            yield session
        except (
            Exception
        ):  # noqa: BLE001 - rollback on any consumer error using the session
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """
    Get a database session for manual session management.

    Returns:
        AsyncSession: Database session (caller responsible for closing)
    """
    _init_engine()
    assert _session_maker is not None
    return _session_maker()


# Export commonly used items
__all__ = [
    "Base",
    "get_engine",
    "get_db",
    "get_db_session",
    "DATABASE_URL",
    "ASYNC_DATABASE_URL",
]
