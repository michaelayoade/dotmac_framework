"""
Repository factory for creating appropriate repository instances.
Enforces DRY patterns and consistent repository usage across the framework.
"""

from typing import Optional, TypeVar, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

# Try to import from multiple possible database sources
try:
    from dotmac.database.base import Base, BaseModel
except ImportError:
    try:
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import DeclarativeBase

        Base = declarative_base()
        BaseModel = DeclarativeBase
    except ImportError:
        from sqlalchemy.ext.declarative import declarative_base

        Base = declarative_base()
        BaseModel = Base
from .async_base_repository import AsyncBaseRepository, AsyncTenantRepository
from .sync_base_repository import SyncBaseRepository, SyncTenantRepository

ModelType = TypeVar("ModelType", bound=Base)


class RepositoryFactory:
    """Factory for creating repository instances with consistent patterns."""

    @staticmethod
    def create_async_repository(
        db: AsyncSession, model: type[ModelType], tenant_id: Optional[str] = None, force_tenant: bool = False
    ) -> Union[AsyncBaseRepository[ModelType], AsyncTenantRepository[ModelType]]:
        """
        Create an async repository instance.

        Args:
            db: Async database session
            model: SQLAlchemy model class
            tenant_id: Tenant identifier
            force_tenant: Force tenant repository even without tenant_id

        Returns:
            Appropriate repository instance
        """
        if tenant_id and hasattr(model, "tenant_id"):
            return AsyncTenantRepository(db, model, tenant_id)
        elif force_tenant and hasattr(model, "tenant_id"):
            raise ValueError(f"Tenant ID required for tenant-aware model {model.__name__}")
        else:
            return AsyncBaseRepository(db, model, tenant_id)

    @staticmethod
    def create_sync_repository(
        db: Session, model_class: type[ModelType], tenant_id: Optional[str] = None, force_tenant: bool = False
    ) -> Union[SyncBaseRepository[ModelType], SyncTenantRepository[ModelType]]:
        """
        Create a sync repository instance.

        Args:
            db: Sync database session
            model_class: SQLAlchemy model class
            tenant_id: Tenant identifier
            force_tenant: Force tenant repository even without tenant_id

        Returns:
            Appropriate repository instance
        """
        if tenant_id and issubclass(model_class, BaseModel):
            return SyncTenantRepository(db, model_class, tenant_id)
        elif force_tenant and issubclass(model_class, BaseModel):
            raise ValueError(f"Tenant ID required for tenant-aware model {model_class.__name__}")
        else:
            return SyncBaseRepository(db, model_class, tenant_id)


# Convenience functions for common usage patterns
def create_repository(
    db: Union[Session, AsyncSession],
    model: type[ModelType],
    tenant_id: Optional[str] = None,
    force_tenant: bool = False,
) -> Union[
    AsyncBaseRepository[ModelType],
    AsyncTenantRepository[ModelType],
    SyncBaseRepository[ModelType],
    SyncTenantRepository[ModelType],
]:
    """
    Auto-detect session type and create appropriate repository.

    Args:
        db: Database session (sync or async)
        model: SQLAlchemy model class
        tenant_id: Tenant identifier
        force_tenant: Force tenant repository even without tenant_id

    Returns:
        Appropriate repository instance
    """
    if isinstance(db, AsyncSession):
        return RepositoryFactory.create_async_repository(db, model, tenant_id, force_tenant)
    elif isinstance(db, Session):
        return RepositoryFactory.create_sync_repository(db, model, tenant_id, force_tenant)
    else:
        raise ValueError(f"Unsupported database session type: {type(db)}")


def create_async_repository(
    db: AsyncSession, model: type[ModelType], tenant_id: Optional[str] = None
) -> Union[AsyncBaseRepository[ModelType], AsyncTenantRepository[ModelType]]:
    """Convenience function for creating async repositories."""
    return RepositoryFactory.create_async_repository(db, model, tenant_id)


def create_sync_repository(
    db: Session, model_class: type[ModelType], tenant_id: Optional[str] = None
) -> Union[SyncBaseRepository[ModelType], SyncTenantRepository[ModelType]]:
    """Convenience function for creating sync repositories."""
    return RepositoryFactory.create_sync_repository(db, model_class, tenant_id)
