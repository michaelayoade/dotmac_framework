"""
Shared base service following ISP Framework standardization patterns.
"""

from abc import ABC
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import EntityNotFoundError
from ..models.base import BaseModel
from ..repositories.base import BaseRepository

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")
ResponseSchemaType = TypeVar("ResponseSchemaType")


class BaseManagementService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType], ABC):
    """Service layer - exceptions bubble up to router @standard_exception_handler."""

    """
    Base service class for management platform following ISP framework patterns.

    Provides:
    - Standardized CRUD operations
    - Business rule validation hooks
    - Consistent error handling
    - Audit logging
    - Tenant isolation (where applicable)
    """

    def __init__(
        self,
        db: AsyncSession,
        model_class: type[ModelType],
        create_schema: type[CreateSchemaType],
        update_schema: type[UpdateSchemaType],
        response_schema: type[ResponseSchemaType],
        tenant_id: Optional[str] = None,
    ):
        self.db = db
        self.model_class = model_class
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schema = response_schema
        self.tenant_id = tenant_id
        self.repository = BaseRepository(db, model_class)

    # Validation hooks for business rules
    async def _validate_create_rules(self, data: CreateSchemaType) -> None:
        """Override to implement create validation rules."""
        pass

    async def _validate_update_rules(self, entity: ModelType, data: UpdateSchemaType) -> None:
        """Override to implement update validation rules."""
        pass

    async def _validate_delete_rules(self, entity: ModelType) -> None:
        """Override to implement delete validation rules."""
        pass

    # Post-operation hooks for automated workflows
    async def _post_create_hook(self, entity: ModelType, data: CreateSchemaType) -> None:
        """Override to implement post-creation workflows."""
        pass

    async def _post_update_hook(self, entity: ModelType, data: UpdateSchemaType) -> None:
        """Override to implement post-update workflows."""
        pass

    async def _post_delete_hook(self, entity: ModelType) -> None:
        """Override to implement post-deletion workflows."""
        pass

    # Pre-operation hooks
    async def _pre_create_hook(self, data: CreateSchemaType) -> None:
        """Override to implement pre-creation setup."""
        pass

    async def _pre_update_hook(self, entity: ModelType, data: UpdateSchemaType) -> None:
        """Override to implement pre-update setup."""
        pass

    # Standard CRUD operations
    async def create(self, data: CreateSchemaType, user_id: Optional[str] = None) -> ModelType:
        """Create a new entity with validation and hooks."""
        # Pre-creation hook
        await self._pre_create_hook(data)

        # Business rule validation
        await self._validate_create_rules(data)

        # Convert schema to dict
        if hasattr(data, "model_dump"):
            entity_data = data.model_dump()
        elif hasattr(data, "dict"):
            entity_data = data.model_dump()
        else:
            entity_data = dict(data)

        # Add tenant context if applicable
        if self.tenant_id and hasattr(self.model_class, "tenant_id"):
            entity_data["tenant_id"] = self.tenant_id

        # Create entity
        entity = await self.repository.create(entity_data, user_id)

        # Post-creation hook
        await self._post_create_hook(entity, data)

        return entity

    async def get_by_id(self, entity_id: UUID, user_id: Optional[str] = None) -> Optional[ModelType]:
        """Get entity by ID with tenant filtering."""
        if self.tenant_id and hasattr(self.model_class, "tenant_id"):
            # Multi-tenant query
            query = select(self.model_class).where(
                and_(
                    self.model_class.id == entity_id,
                    self.model_class.tenant_id == self.tenant_id,
                    self.model_class.is_deleted is False,
                )
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        else:
            # Standard query
            return await self.repository.get_by_id(entity_id)

    async def update(
        self, entity_id: UUID, data: UpdateSchemaType, user_id: Optional[str] = None
    ) -> Optional[ModelType]:
        """Update entity with validation and hooks."""
        # Get existing entity
        entity = await self.get_by_id(entity_id, user_id)
        if not entity:
            raise EntityNotFoundError(f"{self.model_class.__name__} with ID {entity_id} not found")

        # Pre-update hook
        await self._pre_update_hook(entity, data)

        # Business rule validation
        await self._validate_update_rules(entity, data)

        # Convert schema to dict
        if hasattr(data, "model_dump"):
            update_data = data.model_dump(exclude_unset=True)
        elif hasattr(data, "dict"):
            update_data = data.model_dump(exclude_unset=True)
        else:
            update_data = dict(data)

        # Update entity
        updated_entity = await self.repository.update(entity_id, update_data, user_id)

        if updated_entity:
            # Post-update hook
            await self._post_update_hook(updated_entity, data)

        return updated_entity

    async def delete(self, entity_id: UUID, user_id: Optional[str] = None, soft_delete: bool = True) -> bool:
        """Delete entity with validation and hooks."""
        # Get existing entity
        entity = await self.get_by_id(entity_id, user_id)
        if not entity:
            raise EntityNotFoundError(f"{self.model_class.__name__} with ID {entity_id} not found")

        # Business rule validation
        await self._validate_delete_rules(entity)

        # Delete entity
        deleted = await self.repository.delete(entity_id, soft_delete, user_id)

        if deleted:
            # Post-deletion hook
            await self._post_delete_hook(entity)

        return deleted

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[ModelType]:
        """List entities with tenant filtering."""
        # Add tenant filtering if applicable
        if self.tenant_id and hasattr(self.model_class, "tenant_id"):
            filters = filters or {}
            filters["tenant_id"] = self.tenant_id

        return await self.repository.list(skip=skip, limit=limit, filters=filters, order_by=order_by)

    async def count(self, filters: Optional[dict[str, Any]] = None, user_id: Optional[str] = None) -> int:
        """Count entities with tenant filtering."""
        # Add tenant filtering if applicable
        if self.tenant_id and hasattr(self.model_class, "tenant_id"):
            filters = filters or {}
            filters["tenant_id"] = self.tenant_id

        return await self.repository.count(filters)

    async def exists(self, field_name: str, value: Any, exclude_id: Optional[UUID] = None) -> bool:
        """Check if entity exists with given field value."""
        entity = await self.repository.get_by_field(field_name, value)

        if entity and exclude_id and entity.id == exclude_id:
            return False

        # Check tenant isolation
        if entity and self.tenant_id and hasattr(entity, "tenant_id"):
            return entity.tenant_id == self.tenant_id

        return entity is not None
