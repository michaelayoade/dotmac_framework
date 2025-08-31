"""
Database configuration and session management for DotMac Management Platform.

This module provides the database engine, session factory, and dependency injection
functions for the management platform's multi-tenant SaaS operations.
"""

import os
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Database URL - use environment variable or fallback to default
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://dotmac:dotmac@localhost:5432/dotmac_framework"
)

# Convert to async URL if not already
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql+asyncpg://"):
    ASYNC_DATABASE_URL = DATABASE_URL
else:
    ASYNC_DATABASE_URL = f"postgresql+asyncpg://{DATABASE_URL}"


# Import the shared Base class instead of defining a new one
from .models.base import Base


# Create async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection function for getting database sessions.
    
    Yields:
        AsyncSession: Database session for request handling
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
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
    return async_session_maker()


# Export commonly used items
__all__ = [
    "Base",
    "engine", 
    "async_session_maker",
    "get_db",
    "get_db_session",
    "DATABASE_URL",
    "ASYNC_DATABASE_URL",
]