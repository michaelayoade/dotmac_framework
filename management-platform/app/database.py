"""
Database configuration and session management.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import Pool

from .config import settings

logger = logging.getLogger(__name__)

# Create async engine with optimized connection pooling
engine = create_async_engine(
    settings.get_database_url(async_driver=True),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle,
    pool_pre_ping=settings.database_pool_pre_ping,
    echo=settings.database_echo,
    future=True,
)

# Create session maker
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


@event.listens_for(Pool, "connect")
def set_postgres_pragma(dbapi_connection, connection_record):
    """Set PostgreSQL connection settings."""
    # Only apply PostgreSQL settings to PostgreSQL connections
    if hasattr(dbapi_connection, 'server_version'):  # PostgreSQL specific
        with dbapi_connection.cursor() as cursor:
            # Enable Row Level Security
            if settings.enable_tenant_isolation:
                cursor.execute("SET row_security = on")  # nosec B608


@asynccontextmanager
async def database_transaction(session: Optional[AsyncSession] = None) -> AsyncGenerator[AsyncSession, None]:
    """
    Database transaction context manager.
    
    Ensures ACID transactions with automatic rollback on exceptions.
    Can use existing session or create new one.
    """
    if session:
        # Use existing session - don't commit/rollback as it's managed elsewhere
        yield session
    else:
        # Create new session with transaction management
        async with async_session_maker() as new_session:
            try:
                await new_session.begin()
                yield new_session
                await new_session.commit()
                logger.debug("Database transaction committed successfully")
            except Exception as e:
                await new_session.rollback()
                logger.error(f"Database transaction rolled back due to error: {e}")
                raise
            finally:
                await new_session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Import all models to ensure they are registered
        from .models import tenant, billing, deployment, plugin, monitoring, user  # noqa
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        
        # Enable Row Level Security for multi-tenancy
        if settings.enable_tenant_isolation:
            await conn.execute(text("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY"))
            await conn.execute(text("ALTER TABLE tenant_subscriptions ENABLE ROW LEVEL SECURITY"))
            await conn.execute(text("ALTER TABLE tenant_deployments ENABLE ROW LEVEL SECURITY"))


async def close_database():
    """Close database connections."""
    await engine.dispose()


class TenantIsolationMiddleware:
    """Middleware to enforce tenant isolation at database level."""
    
    def __init__(self, session: AsyncSession, tenant_id: str = None):
        self.session = session
        self.tenant_id = tenant_id
    
    async def __aenter__(self):
        """Set tenant context."""
        if self.tenant_id and settings.enable_tenant_isolation:
            await self.session.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": self.tenant_id}
            )
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clear tenant context."""
        if self.tenant_id and settings.enable_tenant_isolation:
            await self.session.execute(
                text("SELECT set_config('app.current_tenant_id', '', true)")
            )