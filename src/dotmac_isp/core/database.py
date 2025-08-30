"""Database configuration and session management."""

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from dotmac_isp.core.settings import get_settings
from dotmac_isp.shared.database.base import Base

settings = get_settings()

# Database engine configuration - adapt to database type
base_engine_kwargs = {
    "echo": settings.debug,
}

# Add pooling options only for databases that support them
if "sqlite" not in settings.database_url.lower():
    base_engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
        }
    )

# Synchronous database engine
engine = create_engine(settings.database_url, **base_engine_kwargs)

# Asynchronous database engine
async_engine_kwargs = base_engine_kwargs.copy()

# Convert sync URL to async URL based on database type
async_database_url = settings.database_url
if "postgresql" in settings.database_url:
    async_database_url = settings.database_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    if not async_database_url.startswith("postgresql+asyncpg://"):
        async_database_url = async_database_url.replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://"
        )
elif "sqlite" in settings.database_url and "aiosqlite" not in settings.database_url:
    async_database_url = settings.database_url.replace(
        "sqlite://", "sqlite+aiosqlite://"
    )

async_engine = create_async_engine(async_database_url, **async_engine_kwargs)

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """Dependency for synchronous database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for asynchronous database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)


async def create_tables_async():
    """Create all database tables asynchronously."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables_async():
    """Drop all database tables asynchronously."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def init_database() -> None:
    """Initialize database connection and create tables if needed."""
    # Import all module models to register them with SQLAlchemy
    try:
        from dotmac_isp.modules.analytics import (  # noqa: F401
            models as analytics_models,
        )
        from dotmac_isp.modules.billing import models as billing_models  # noqa: F401

        # Inventory models moved to dotmac_shared.inventory_management package
        from dotmac_isp.modules.compliance import (  # noqa: F401
            models as compliance_models,
        )

        # Support models moved to dotmac_shared.ticketing package
        # Project models moved to dotmac_shared.project_management package
        from dotmac_isp.modules.field_ops import (  # noqa: F401
            models as field_ops_models,
        )
        from dotmac_isp.modules.gis import models as gis_models  # noqa: F401
        from dotmac_isp.modules.identity import models as identity_models  # noqa: F401
        from dotmac_isp.modules.licensing import (  # noqa: F401
            models as licensing_models,
        )
        from dotmac_isp.modules.network_integration import (  # noqa: F401
            models as network_integration_models,
        )
        from dotmac_isp.modules.network_monitoring import (  # noqa: F401
            models as network_monitoring_models,
        )
        from dotmac_isp.modules.network_visualization import (  # noqa: F401
            models as network_visualization_models,
        )
        from dotmac_isp.modules.notifications import (  # noqa: F401
            models as notifications_models,
        )
        from dotmac_isp.modules.omnichannel import (  # noqa: F401
            models as omnichannel_models,
        )
        from dotmac_isp.modules.portal_management import (  # noqa: F401
            models as portal_management_models,
        )
        from dotmac_isp.modules.resellers import (  # noqa: F401
            models as resellers_models,
        )
        from dotmac_isp.modules.sales import models as sales_models  # noqa: F401
        from dotmac_isp.modules.services import models as services_models  # noqa: F401
    except ImportError:
        pass  # Some models may not exist yet

    # Configure cross-module relationships after all models are imported
    try:
        from dotmac_isp.shared.database.relationship_registry import (
            relationship_registry,
        )

        relationship_registry.configure_all_relationships()
    except ImportError:
        pass  # Relationship registry not available

    # Create tables for all modules - using sync engine for now
    Base.metadata.create_all(bind=engine)


async def close_database() -> None:
    """Close database connections."""
    if async_engine:
        await async_engine.dispose()
