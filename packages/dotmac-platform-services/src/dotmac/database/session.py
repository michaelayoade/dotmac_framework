"""
Database session utilities for DotMac platform.

Provides canonical sync and async session helpers used across services.

Design:
- Uses environment variables for configuration when available.
  - DOTMAC_DATABASE_URL (sync)
  - DOTMAC_DATABASE_URL_ASYNC (async)
- Falls back to reasonable defaults for development (SQLite) if not set.

Exposed helpers:
- get_database_session()  -> context manager yielding sync Session
- get_db_session()        -> async dependency yielding AsyncSession
- get_async_db_session()  -> alias of get_db_session()
- get_async_db()          -> alias of get_db_session()
- create_async_database_engine(url: str, **kwargs) -> AsyncEngine
- check_database_health() -> async bool
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy.orm import sessionmaker as sync_sessionmaker

_sync_engine: Engine | None = None
_async_engine: AsyncEngine | None = None


def _get_sync_url() -> str:
    url = os.getenv("DOTMAC_DATABASE_URL")
    if url:
        return url
    # Development fallback
    return "sqlite:///./dotmac_dev.sqlite"


def _get_async_url() -> str:
    url = os.getenv("DOTMAC_DATABASE_URL_ASYNC")
    if url:
        return url
    # Attempt to derive async URL from sync URL
    base = _get_sync_url()
    if base.startswith("postgresql://"):
        return base.replace("postgresql://", "postgresql+asyncpg://", 1)
    if base.startswith("sqlite://"):
        return base.replace("sqlite://", "sqlite+aiosqlite://", 1)
    # As a last resort, keep as-is; driver may support async
    return base


def _ensure_sync_engine() -> Engine:
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(_get_sync_url(), future=True)
    return _sync_engine


def _ensure_async_engine() -> AsyncEngine:
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(_get_async_url(), future=True)
    return _async_engine


@contextmanager
def get_database_session() -> Iterator[SyncSession]:
    """Context manager yielding a synchronous SQLAlchemy session."""
    engine = _ensure_sync_engine()
    maker = sync_sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session: SyncSession = maker()
    try:
        yield session
        session.close()
    except Exception:
        try:
            session.rollback()
        finally:
            session.close()
        raise


@asynccontextmanager
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Async dependency that yields an AsyncSession (FastAPI-friendly)."""
    engine = _ensure_async_engine()
    maker = async_sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session: AsyncSession = maker()
    try:
        yield session
    except Exception:
        try:
            await session.rollback()
        finally:
            await session.close()
        raise
    else:
        await session.close()


# Aliases commonly referenced across the codebase
get_async_db = get_db_session
get_async_db_session = get_db_session


def create_async_database_engine(url: str, **kwargs) -> AsyncEngine:
    """Create and return an AsyncEngine for the provided URL."""
    return create_async_engine(url, **kwargs)


async def check_database_health() -> bool:
    """Lightweight async health check by opening and closing a connection."""
    try:
        engine = _ensure_async_engine()
        async with engine.connect() as conn:  # type: ignore[call-arg]
            await conn.close()
        return True
    except Exception:
        return False

