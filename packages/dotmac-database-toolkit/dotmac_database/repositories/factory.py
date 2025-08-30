"""
Repository factory functions for creating appropriate repository instances.
"""

from typing import Optional, Type, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..types import ModelType, TenantMixin, ValidationError
from .async_base import AsyncRepository, AsyncTenantRepository
from .base import BaseRepository, BaseTenantRepository


def create_repository(
    db: Session,
    model_class: Type[ModelType],
    tenant_id: Optional[str] = None,
    auto_commit: bool = True,
) -> Union[BaseRepository[ModelType], BaseTenantRepository[ModelType]]:
    """
    Factory function to create appropriate synchronous repository.

    Args:
        db: Database session
        model_class: SQLAlchemy model class
        tenant_id: Tenant identifier
        auto_commit: Whether to auto-commit transactions

    Returns:
        Repository instance (tenant-aware if applicable)

    Raises:
        ValidationError: If tenant configuration is invalid
    """
    is_tenant_model = issubclass(model_class, TenantMixin)

    if is_tenant_model and tenant_id:
        return BaseTenantRepository(db, model_class, tenant_id, auto_commit)
    elif is_tenant_model and not tenant_id:
        raise ValidationError(
            f"Model {model_class.__name__} requires tenant_id but none provided"
        )
    else:
        return BaseRepository(db, model_class, tenant_id, auto_commit)


def create_async_repository(
    db: AsyncSession,
    model_class: Type[ModelType],
    tenant_id: Optional[str] = None,
    auto_commit: bool = True,
) -> Union[AsyncRepository[ModelType], AsyncTenantRepository[ModelType]]:
    """
    Factory function to create appropriate asynchronous repository.

    Args:
        db: Async database session
        model_class: SQLAlchemy model class
        tenant_id: Tenant identifier
        auto_commit: Whether to auto-commit transactions

    Returns:
        Async repository instance (tenant-aware if applicable)

    Raises:
        ValidationError: If tenant configuration is invalid
    """
    is_tenant_model = issubclass(model_class, TenantMixin)

    if is_tenant_model and tenant_id:
        return AsyncTenantRepository(db, model_class, tenant_id, auto_commit)
    elif is_tenant_model and not tenant_id:
        raise ValidationError(
            f"Model {model_class.__name__} requires tenant_id but none provided"
        )
    else:
        return AsyncRepository(db, model_class, tenant_id, auto_commit)


def create_repository_from_session(
    session: Union[Session, AsyncSession],
    model_class: Type[ModelType],
    tenant_id: Optional[str] = None,
    auto_commit: bool = True,
) -> Union[
    BaseRepository[ModelType],
    BaseTenantRepository[ModelType],
    AsyncRepository[ModelType],
    AsyncTenantRepository[ModelType],
]:
    """
    Factory function that automatically detects session type and creates appropriate repository.

    Args:
        session: Database session (sync or async)
        model_class: SQLAlchemy model class
        tenant_id: Tenant identifier
        auto_commit: Whether to auto-commit transactions

    Returns:
        Repository instance matching session type

    Raises:
        ValidationError: If session type is not supported or tenant configuration is invalid
    """
    if isinstance(session, AsyncSession):
        return create_async_repository(session, model_class, tenant_id, auto_commit)
    elif isinstance(session, Session):
        return create_repository(session, model_class, tenant_id, auto_commit)
    else:
        raise ValidationError(
            f"Unsupported session type: {type(session)}. Must be Session or AsyncSession."
        )
