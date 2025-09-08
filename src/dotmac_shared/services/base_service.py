"""
Enhanced Base Service implementing standardized business logic patterns.
Provides consistent service operations, validation, and error handling.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Generic, Sequence, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import (
    ServiceError, 
    EntityNotFoundError, 
    ValidationError,
    BusinessRuleError
)

logger = logging.getLogger(__name__)

# Type variables for generic service  
RepositoryType = TypeVar('RepositoryType')
CreateSchemaType = TypeVar('CreateSchemaType')
UpdateSchemaType = TypeVar('UpdateSchemaType')
ResponseSchemaType = TypeVar('ResponseSchemaType')


class BaseService(Generic[RepositoryType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    """
    Base service providing standardized business logic operations.
    
    Implements:
    - Consistent CRUD operations with business rules
    - Validation and error handling
    - Tenant isolation support
    - Audit logging
    - Transaction management
    """
    
    def __init__(
        self, 
        repository: RepositoryType,
        session: AsyncSession,
        tenant_id: str | None = None
    ):
        self.repository = repository
        self.session = session
        self.tenant_id = tenant_id
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @asynccontextmanager
    async def error_handling(self, operation: str, entity_type: str = "entity"):
        """Context manager for consistent error handling and logging."""
        try:
            self.logger.debug(f"Starting {operation} for {entity_type}")
            yield
            self.logger.debug(f"Completed {operation} for {entity_type}")
        except EntityNotFoundError as e:
            self.logger.warning(f"{operation} failed - {entity_type} not found: {e}")
            raise
        except ValidationError as e:
            self.logger.warning(f"{operation} failed - validation error: {e}")
            raise
        except BusinessRuleError as e:
            self.logger.warning(f"{operation} failed - business rule violation: {e}")
            raise
        except Exception as e:
            self.logger.error(f"{operation} failed for {entity_type}: {e}")
            raise ServiceError(f"{operation} operation failed: {str(e)}") from e
    
    async def validate_create_input(self, obj_in: CreateSchemaType) -> None:
        """Override to add custom validation rules for creation."""
        pass
    
    async def validate_update_input(
        self, 
        entity_id: UUID | str | int,
        obj_in: UpdateSchemaType
    ) -> None:
        """Override to add custom validation rules for updates."""
        pass
    
    async def before_create(self, obj_in: CreateSchemaType) -> CreateSchemaType:
        """Hook called before entity creation. Override for custom logic."""
        return obj_in
    
    async def after_create(self, entity, obj_in: CreateSchemaType):
        """Hook called after entity creation. Override for custom logic."""
        pass
    
    async def before_update(
        self, 
        entity, 
        obj_in: UpdateSchemaType
    ) -> UpdateSchemaType:
        """Hook called before entity update. Override for custom logic."""
        return obj_in
    
    async def after_update(self, entity, obj_in: UpdateSchemaType):
        """Hook called after entity update. Override for custom logic."""
        pass
    
    async def before_delete(self, entity):
        """Hook called before entity deletion. Override for custom logic."""
        pass
    
    async def after_delete(self, entity_id: UUID | str | int):
        """Hook called after entity deletion. Override for custom logic."""
        pass
    
    async def create(
        self, 
        obj_in: CreateSchemaType,
        commit: bool = True
    ):
        """Create a new entity with validation and hooks."""
        async with self.error_handling("create"):
            # Validate input
            await self.validate_create_input(obj_in)
            
            # Pre-creation hook
            validated_input = await self.before_create(obj_in)
            
            # Create entity
            entity = await self.repository.create(
                validated_input, 
                tenant_id=self.tenant_id,
                commit=commit
            )
            
            # Post-creation hook
            await self.after_create(entity, validated_input)
            
            return entity
    
    async def get(self, entity_id: UUID | str | int):
        """Get entity by ID with tenant isolation."""
        async with self.error_handling("get"):
            entity = await self.repository.get(entity_id, tenant_id=self.tenant_id)
            if not entity:
                raise EntityNotFoundError("Entity", str(entity_id))
            return entity
    
    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None
    ) -> Sequence:
        """Get multiple entities with pagination and filtering."""
        async with self.error_handling("get_multi"):
            return await self.repository.get_multi(
                skip=skip,
                limit=limit,
                tenant_id=self.tenant_id,
                filters=filters,
                order_by=order_by
            )
    
    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities with filtering."""
        async with self.error_handling("count"):
            return await self.repository.count(
                tenant_id=self.tenant_id,
                filters=filters
            )
    
    async def exists(self, entity_id: UUID | str | int) -> bool:
        """Check if entity exists."""
        async with self.error_handling("exists"):
            return await self.repository.exists(entity_id, tenant_id=self.tenant_id)
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for manual transaction control."""
        try:
            yield self.session
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise


class TenantAwareService(BaseService):
    """Base service that requires tenant context."""
    
    def __init__(
        self, 
        repository: RepositoryType,
        session: AsyncSession,
        tenant_id: str
    ):
        if not tenant_id:
            raise ValueError("Tenant ID is required for TenantAwareService")
        super().__init__(repository, session, tenant_id)


class ReadOnlyService(BaseService):
    """Service that only supports read operations."""
    
    async def create(self, *args, **kwargs):
        raise ServiceError("Create operation not supported")
    
    async def update(self, *args, **kwargs):
        raise ServiceError("Update operation not supported")
    
    async def delete(self, *args, **kwargs):
        raise ServiceError("Delete operation not supported")
    
    async def bulk_create(self, *args, **kwargs):
        raise ServiceError("Bulk create operation not supported")


# Export service classes
__all__ = [
    'BaseService', 
    'TenantAwareService', 
    'ReadOnlyService',
]