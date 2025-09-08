"""
Unified Base Service Architecture

Consolidates the best features from all existing base service implementations:
- dotmac_shared/services/base_service.py (434 lines)
- dotmac_isp/shared/base_service.py (495 lines)
- dotmac_management/shared/base_service.py (223 lines)

This implementation provides a single, consistent service architecture pattern
for the entire DotMac framework.
"""
from __future__ import annotations

import logging
from abc import ABC
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

# Import from core exception system
from ...core.exceptions import EntityNotFoundError

# Try to import database base from multiple sources for compatibility
try:
    from dotmac.database.base import Base
except ImportError:
    try:
        from ...database.base import Base
    except ImportError:
        try:
            from sqlalchemy.orm import DeclarativeBase as Base
        except ImportError:
            from sqlalchemy.ext.declarative import declarative_base

            Base = declarative_base()

logger = logging.getLogger(__name__)

# Generic type definitions
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticBaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticBaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=PydanticBaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType], ABC):
    """
    Unified base service providing common business logic operations.

    Consolidates functionality from all existing base service implementations
    to provide a single, consistent service architecture pattern.

    Features:
    - Repository pattern integration
    - Schema validation and transformation
    - Consistent error handling
    - Audit trail support
    - Tenant isolation
    - Business rule validation
    - Both sync and async operation support
    - Transaction management
    """

    def __init__(
        self,
        db_session: Session | AsyncSession,
        tenant_id: str | None = None,
        model_class: type[ModelType] | None = None,
        create_schema: type[CreateSchemaType] | None = None,
        update_schema: type[UpdateSchemaType] | None = None,
        response_schema: type[ResponseSchemaType] | None = None,
        **kwargs,
    ):
        """
        Initialize base service with database session and optional schemas.

        Args:
            db_session: Database session (sync or async)
            tenant_id: Tenant identifier for multi-tenant isolation
            model_class: SQLAlchemy model class
            create_schema: Pydantic schema for creation
            update_schema: Pydantic schema for updates
            response_schema: Pydantic schema for responses
            **kwargs: Additional service-specific configuration
        """
        self.db = db_session
        self.tenant_id = tenant_id
        self.model_class = model_class
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schema = response_schema

        # Store additional configuration
        self.config = kwargs

        # Initialize service-specific components
        self._initialize_service()

    def _initialize_service(self) -> None:
        """
        Initialize service-specific components.
        Override in subclasses for custom initialization.
        """
        pass

    # Core CRUD Operations

    async def create(self, data: CreateSchemaType, user_id: str | None = None) -> ResponseSchemaType:
        """
        Create a new entity with business rule validation.

        Args:
            data: Creation data following create schema
            user_id: User performing the operation (for audit)

        Returns:
            Created entity following response schema

        Raises:
            ValidationError: If business rules fail
            BusinessLogicError: If business logic constraints violated
        """
        # Pre-creation business rule validation
        await self._validate_create(data, user_id)

        # Transform schema to model data
        model_data = self._prepare_create_data(data, user_id)

        # Create entity
        entity = self.model_class(**model_data)

        # Apply tenant isolation if applicable
        if self.tenant_id and hasattr(entity, "tenant_id"):
            entity.tenant_id = self.tenant_id

        # Apply audit fields
        if hasattr(entity, "created_by") and user_id:
            entity.created_by = user_id
        if hasattr(entity, "created_at"):
            entity.created_at = datetime.now(timezone.utc)

        # Save to database
        if isinstance(self.db, AsyncSession):
            self.db.add(entity)
            await self.db.commit()
            await self.db.refresh(entity)
        else:
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)

        # Post-creation business logic
        await self._post_create(entity, user_id)

        # Transform to response schema
        return self._to_response_schema(entity)

    async def get_by_id(self, entity_id: UUID, user_id: str | None = None) -> ResponseSchemaType:
        """
        Get entity by ID with tenant isolation and access control.

        Args:
            entity_id: Entity identifier
            user_id: User performing the operation

        Returns:
            Entity following response schema

        Raises:
            EntityNotFoundError: If entity doesn't exist or not accessible
        """
        entity = await self._get_entity(entity_id)

        # Validate access permissions
        await self._validate_access(entity, user_id, "read")

        return self._to_response_schema(entity)

    async def update(self, entity_id: UUID, data: UpdateSchemaType, user_id: str | None = None) -> ResponseSchemaType:
        """
        Update entity with business rule validation.

        Args:
            entity_id: Entity identifier
            data: Update data following update schema
            user_id: User performing the operation

        Returns:
            Updated entity following response schema

        Raises:
            EntityNotFoundError: If entity doesn't exist
            ValidationError: If business rules fail
            BusinessLogicError: If business logic constraints violated
        """
        entity = await self._get_entity(entity_id)

        # Validate access permissions
        await self._validate_access(entity, user_id, "update")

        # Pre-update business rule validation
        await self._validate_update(entity, data, user_id)

        # Apply updates
        update_data = self._prepare_update_data(data, user_id)

        for field, value in update_data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)

        # Apply audit fields
        if hasattr(entity, "updated_by") and user_id:
            entity.updated_by = user_id
        if hasattr(entity, "updated_at"):
            entity.updated_at = datetime.now(timezone.utc)

        # Save changes
        if isinstance(self.db, AsyncSession):
            await self.db.commit()
            await self.db.refresh(entity)
        else:
            self.db.commit()
            self.db.refresh(entity)

        # Post-update business logic
        await self._post_update(entity, user_id)

        return self._to_response_schema(entity)

    async def delete(self, entity_id: UUID, user_id: str | None = None, soft_delete: bool = True) -> bool:
        """
        Delete entity with business rule validation.

        Args:
            entity_id: Entity identifier
            user_id: User performing the operation
            soft_delete: Whether to perform soft delete (default: True)

        Returns:
            True if successfully deleted

        Raises:
            EntityNotFoundError: If entity doesn't exist
            BusinessLogicError: If entity cannot be deleted
        """
        entity = await self._get_entity(entity_id)

        # Validate access permissions
        await self._validate_access(entity, user_id, "delete")

        # Pre-deletion business rule validation
        await self._validate_delete(entity, user_id)

        if soft_delete and hasattr(entity, "deleted_at"):
            # Soft delete
            entity.deleted_at = datetime.now(timezone.utc)
            if hasattr(entity, "deleted_by") and user_id:
                entity.deleted_by = user_id

            if isinstance(self.db, AsyncSession):
                await self.db.commit()
            else:
                self.db.commit()
        else:
            # Hard delete
            if isinstance(self.db, AsyncSession):
                await self.db.delete(entity)
                await self.db.commit()
            else:
                self.db.delete(entity)
                self.db.commit()

        # Post-deletion business logic
        await self._post_delete(entity, user_id)

        return True

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        user_id: str | None = None,
    ) -> list[ResponseSchemaType]:
        """
        List entities with filtering, pagination, and access control.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Filter criteria
            order_by: Field to order by
            user_id: User performing the operation

        Returns:
            List of entities following response schema
        """
        query = self._build_list_query(filters, order_by, user_id)

        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(query.offset(skip).limit(limit))
            entities = result.scalars().all()
        else:
            entities = query.offset(skip).limit(limit).all()

        return [self._to_response_schema(entity) for entity in entities]

    async def count(self, filters: dict[str, Any] | None = None, user_id: str | None = None) -> int:
        """
        Count entities matching filters with access control.

        Args:
            filters: Filter criteria
            user_id: User performing the operation

        Returns:
            Count of matching entities
        """
        query = self._build_count_query(filters, user_id)

        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(query)
            return result.scalar() or 0
        else:
            return query.scalar() or 0

    # Internal Helper Methods

    async def _get_entity(self, entity_id: UUID) -> ModelType:
        """Get entity by ID with tenant isolation."""
        if isinstance(self.db, AsyncSession):
            query = select(self.model_class).where(self.model_class.id == entity_id)
            if self.tenant_id and hasattr(self.model_class, "tenant_id"):
                query = query.where(self.model_class.tenant_id == self.tenant_id)
            result = await self.db.execute(query)
            entity = result.scalar_one_or_none()
        else:
            filters = [self.model_class.id == entity_id]
            if self.tenant_id and hasattr(self.model_class, "tenant_id"):
                filters.append(self.model_class.tenant_id == self.tenant_id)
            entity = self.db.query(self.model_class).filter(and_(*filters)).first()

        if not entity:
            raise EntityNotFoundError(f"{self.model_class.__name__} with ID {entity_id} not found")

        return entity

    def _build_list_query(self, filters: dict[str, Any] | None, order_by: str | None, user_id: str | None):
        """Build list query with filters and tenant isolation."""
        if isinstance(self.db, AsyncSession):
            query = select(self.model_class)
        else:
            query = self.db.query(self.model_class)

        # Apply tenant isolation
        if self.tenant_id and hasattr(self.model_class, "tenant_id"):
            if isinstance(self.db, AsyncSession):
                query = query.where(self.model_class.tenant_id == self.tenant_id)
            else:
                query = query.filter(self.model_class.tenant_id == self.tenant_id)

        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)

        # Apply ordering
        if order_by and hasattr(self.model_class, order_by):
            if isinstance(self.db, AsyncSession):
                query = query.order_by(getattr(self.model_class, order_by))
            else:
                query = query.order_by(getattr(self.model_class, order_by))

        return query

    def _build_count_query(self, filters: dict[str, Any] | None, user_id: str | None):
        """Build count query with filters and tenant isolation."""
        if isinstance(self.db, AsyncSession):
            from sqlalchemy import func

            query = select(func.count(self.model_class.id))
        else:
            query = self.db.query(self.model_class)

        # Apply tenant isolation
        if self.tenant_id and hasattr(self.model_class, "tenant_id"):
            if isinstance(self.db, AsyncSession):
                query = query.where(self.model_class.tenant_id == self.tenant_id)
            else:
                query = query.filter(self.model_class.tenant_id == self.tenant_id)

        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)

        if not isinstance(self.db, AsyncSession):
            query = query.count()

        return query

    def _apply_filters(self, query, filters: dict[str, Any]):
        """Apply filters to query."""
        for field, value in filters.items():
            if hasattr(self.model_class, field):
                if isinstance(self.db, AsyncSession):
                    query = query.where(getattr(self.model_class, field) == value)
                else:
                    query = query.filter(getattr(self.model_class, field) == value)
        return query

    def _to_response_schema(self, entity: ModelType) -> ResponseSchemaType:
        """Transform entity to response schema."""
        if self.response_schema:
            return self.response_schema.model_validate(entity)
        return entity

    def _prepare_create_data(self, data: CreateSchemaType, user_id: str | None) -> dict[str, Any]:
        """Prepare creation data from schema."""
        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=True)
        elif hasattr(data, "dict"):
            return data.dict(exclude_unset=True)
        return data

    def _prepare_update_data(self, data: UpdateSchemaType, user_id: str | None) -> dict[str, Any]:
        """Prepare update data from schema."""
        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=True)
        elif hasattr(data, "dict"):
            return data.dict(exclude_unset=True)
        return data

    # Abstract Business Logic Methods - Override in subclasses

    async def _validate_create(self, data: CreateSchemaType, user_id: str | None) -> None:
        """Validate business rules for creation. Override in subclasses."""
        pass

    async def _validate_update(self, entity: ModelType, data: UpdateSchemaType, user_id: str | None) -> None:
        """Validate business rules for updates. Override in subclasses."""
        pass

    async def _validate_delete(self, entity: ModelType, user_id: str | None) -> None:
        """Validate business rules for deletion. Override in subclasses."""
        pass

    async def _validate_access(self, entity: ModelType, user_id: str | None, operation: str) -> None:
        """Validate access permissions. Override in subclasses."""
        pass

    async def _post_create(self, entity: ModelType, user_id: str | None) -> None:
        """Post-creation business logic. Override in subclasses."""
        pass

    async def _post_update(self, entity: ModelType, user_id: str | None) -> None:
        """Post-update business logic. Override in subclasses."""
        pass

    async def _post_delete(self, entity: ModelType, user_id: str | None) -> None:
        """Post-deletion business logic. Override in subclasses."""
        pass


class BaseManagementService(BaseService[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    """
    Management-specific base service with additional features for the management platform.

    Inherits all functionality from BaseService and adds management-specific features:
    - Enhanced audit logging
    - Approval workflows
    - Complex permission models
    - System-level operations
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_management_service = True

    async def _validate_access(self, entity: ModelType, user_id: str | None, operation: str) -> None:
        """Enhanced access validation for management operations."""
        # Management services may have different permission requirements
        # Override in specific management services as needed
        pass
