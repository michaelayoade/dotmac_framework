"""
Base Service Classes

ARCHITECTURE IMPROVEMENT: Provides reusable business logic patterns
to eliminate code duplication across modules. Implements Service pattern
with consistent error handling, validation, and transaction management.
"""

import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar

if TYPE_CHECKING:
    pass
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from .base_repository import BaseTenantRepository, create_repository
from .database.base import Base
from .exceptions import EntityNotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Generic types
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType], ABC):
    """Service layer - exceptions bubble up to router @standard_exception_handler."""

    """
    Base service providing common business logic patterns.

    PATTERN: Service Layer with Generic Types
    - Encapsulates business logic and validation
    - Provides consistent error handling
    - Manages transactions and repository interactions
    - Reduces code duplication across modules

    Features:
    - CRUD operations with business logic
    - Schema validation and transformation
    - Transaction management
    - Event handling hooks
    - Consistent error handling
    - Caching support
    """

    def __init__(
        self,
        db: Session,
        model_class: type[ModelType],
        create_schema: type[CreateSchemaType],
        update_schema: type[UpdateSchemaType],
        response_schema: type[ResponseSchemaType],
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize service.

        Args:
            db: Database session
            model_class: SQLAlchemy model class
            create_schema: Pydantic schema for creation
            update_schema: Pydantic schema for updates
            response_schema: Pydantic schema for responses
            tenant_id: Tenant identifier for multi-tenancy
        """
        self.db = db
        self.model_class = model_class
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schema = response_schema
        self.tenant_id = tenant_id

        # Initialize repository
        self.repository = create_repository(db, model_class, tenant_id)

        # Set up logging
        self._logger = logging.getLogger(f"{__name__}.{model_class.__name__}Service")

    async def create(self, data: CreateSchemaType, commit: bool = True) -> ResponseSchemaType:
        """
        Create new entity with business logic validation.

        Args:
            data: Creation data
            commit: Whether to commit transaction

        Returns:
            Created entity response

        Raises:
            ValidationError: If data is invalid
            BusinessRuleError: If business rules are violated
            ServiceError: If creation fails
        """
        # Validate input data
        if isinstance(data, dict):
            data = self.create_schema(**data)

        # Execute pre-creation hooks
        await self._pre_create_hook(data)

        # Validate business rules
        await self._validate_create_rules(data)

        # Convert to dict for repository
        create_data = (
            data.model_dump() if hasattr(data, "model_dump") else (data.model_dump() if hasattr(data, "dict") else data)
        )

        # Create entity via repository
        entity = self.repository.create(create_data, commit=commit)

        # Execute post-creation hooks
        await self._post_create_hook(entity, data)

        # Convert to response schema
        response = self._to_response_schema(entity)

        self._logger.info(f"Created {self.model_class.__name__} with ID: {entity.id}")
        return response

    async def get_by_id(self, entity_id: UUID) -> Optional[ResponseSchemaType]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity response if found, None otherwise
        """
        entity = self.repository.get_by_id(entity_id)
        if entity:
            return self._to_response_schema(entity)
        return None

    async def get_by_id_or_raise(self, entity_id: UUID) -> ResponseSchemaType:
        """
        Get entity by ID or raise exception.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity response

        Raises:
            EntityNotFoundError: If entity not found
        """
        entity = await self.get_by_id(entity_id)
        if not entity:
            raise EntityNotFoundError(f"{self.model_class.__name__} not found with ID: {entity_id}")
        return entity

    async def update(self, entity_id: UUID, data: UpdateSchemaType, commit: bool = True) -> ResponseSchemaType:
        """
        Update entity with business logic validation.

        Args:
            entity_id: Entity identifier
            data: Update data
            commit: Whether to commit transaction

        Returns:
            Updated entity response

        Raises:
            EntityNotFoundError: If entity not found
            ValidationError: If data is invalid
            BusinessRuleError: If business rules are violated
            ServiceError: If update fails
        """
        # Get existing entity
        existing_entity = self.repository.get_by_id_or_raise(entity_id)

        # Validate input data
        if isinstance(data, dict):
            data = self.update_schema(**data)

        # Execute pre-update hooks
        await self._pre_update_hook(existing_entity, data)

        # Validate business rules
        await self._validate_update_rules(existing_entity, data)

        # Convert to dict for repository, excluding None values
        update_data = {}
        if hasattr(data, "dict"):
            update_data = data.model_dump(exclude_none=True)
        else:
            update_data = {k: v for k, v in data.items() if v is not None}

        # Update entity via repository
        updated_entity = self.repository.update(entity_id, update_data, commit=commit)

        # Execute post-update hooks
        await self._post_update_hook(updated_entity, data)

        # Convert to response schema
        response = self._to_response_schema(updated_entity)

        self._logger.info(f"Updated {self.model_class.__name__} with ID: {entity_id}")
        return response

    async def delete(self, entity_id: UUID, commit: bool = True) -> bool:
        """
        Delete entity with business logic validation.

        Args:
            entity_id: Entity identifier
            commit: Whether to commit transaction

        Returns:
            True if deleted successfully

        Raises:
            EntityNotFoundError: If entity not found
            BusinessRuleError: If deletion is not allowed
            ServiceError: If deletion fails
        """
        # Get existing entity
        existing_entity = self.repository.get_by_id_or_raise(entity_id)

        # Execute pre-deletion hooks
        await self._pre_delete_hook(existing_entity)

        # Validate business rules
        await self._validate_delete_rules(existing_entity)

        # Delete entity via repository
        success = self.repository.delete(entity_id, commit=commit)

        # Execute post-deletion hooks
        await self._post_delete_hook(existing_entity)

        self._logger.info(f"Deleted {self.model_class.__name__} with ID: {entity_id}")
        return success

    async def list(
        self,
        filters: Optional[dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[ResponseSchemaType]:
        """
        List entities with filtering, sorting, and pagination.

        Args:
            filters: Filter criteria
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of entity responses
        """
        # Apply access control filters
        authorized_filters = await self._apply_access_control_filters(filters or {})

        # Get entities from repository
        entities = self.repository.list(
            filters=authorized_filters,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
        # Convert to response schemas
        return [self._to_response_schema(entity) for entity in entities]

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """
        Count entities with optional filtering.

        Args:
            filters: Filter criteria

        Returns:
            Number of entities
        """
        # Apply access control filters
        authorized_filters = await self._apply_access_control_filters(filters or {})

        return self.repository.count(authorized_filters)

    def _to_response_schema(self, entity: ModelType) -> ResponseSchemaType:
        """
        Convert entity to response schema.

        Args:
            entity: Database entity

        Returns:
            Response schema instance
        """
        # Convert SQLAlchemy model to dict
        entity_dict = {}
        for column in entity.__table__.columns:
            value = getattr(entity, column.name)
            entity_dict[column.name] = value

        # Handle relationships if needed (can be overridden in subclasses)
        entity_dict = self._add_relationship_data(entity, entity_dict)

        return self.response_schema(**entity_dict)

    # Hooks that can be overridden in subclasses
    async def _pre_create_hook(self, data: CreateSchemaType) -> None:
        """Hook called before entity creation."""
        pass

    async def _post_create_hook(self, entity: ModelType, data: CreateSchemaType) -> None:
        """Hook called after entity creation."""
        pass

    async def _pre_update_hook(self, entity: ModelType, data: UpdateSchemaType) -> None:
        """Hook called before entity update."""
        pass

    async def _post_update_hook(self, entity: ModelType, data: UpdateSchemaType) -> None:
        """Hook called after entity update."""
        pass

    async def _pre_delete_hook(self, entity: ModelType) -> None:
        """Hook called before entity deletion."""
        pass

    async def _post_delete_hook(self, entity: ModelType) -> None:
        """Hook called after entity deletion."""
        pass

    async def _validate_create_rules(self, data: CreateSchemaType) -> None:
        """Validate business rules for creation. Override in subclasses."""
        pass

    async def _validate_update_rules(self, entity: ModelType, data: UpdateSchemaType) -> None:
        """Validate business rules for updates. Override in subclasses."""
        pass

    async def _validate_delete_rules(self, entity: ModelType) -> None:
        """Validate business rules for deletion. Override in subclasses."""
        pass

    async def _apply_access_control_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Apply access control filters. Override in subclasses."""
        return filters

    def _add_relationship_data(self, entity: ModelType, entity_dict: dict[str, Any]) -> dict[str, Any]:
        """Add relationship data to entity dict. Override in subclasses."""
        return entity_dict


class BaseTenantService(BaseService[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    """
    Base service for tenant-aware entities.

    Extends BaseService with additional tenant-specific functionality.
    """

    def __init__(
        self,
        db: Session,
        model_class: type[ModelType],
        create_schema: type[CreateSchemaType],
        update_schema: type[UpdateSchemaType],
        response_schema: type[ResponseSchemaType],
        tenant_id: str,
    ):
        """
        Initialize tenant service.

        Args:
            db: Database session
            model_class: SQLAlchemy model class (must inherit from TenantMixin)
            create_schema: Pydantic schema for creation
            update_schema: Pydantic schema for updates
            response_schema: Pydantic schema for responses
            tenant_id: Required tenant identifier
        """
        if not tenant_id:
            raise ValidationError("tenant_id is required for tenant services")

        if not hasattr(model_class, "tenant_id"):
            raise ValidationError(f"Model {model_class.__name__} must inherit from TenantMixin")

        super().__init__(db, model_class, create_schema, update_schema, response_schema, tenant_id)

    async def get_tenant_stats(self) -> dict[str, Any]:
        """
        Get statistics for current tenant.

        Returns:
            Statistics dictionary
        """
        if isinstance(self.repository, BaseTenantRepository):
            return self.repository.get_tenant_stats()
        else:
            # Fallback for basic repository
            return {
                "tenant_id": self.tenant_id,
                "entity_type": self.model_class.__name__,
                "total_entities": await self.count(),
            }

    async def _apply_access_control_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Apply tenant isolation filters."""
        # Tenant filtering is handled by the repository, but we can add additional filters here
        return filters


class BaseReadOnlyService(Generic[ModelType, ResponseSchemaType], ABC):
    """
    Base service for read-only operations.

    Useful for reporting, analytics, and view-only services.
    """

    def __init__(
        self,
        db: Session,
        model_class: type[ModelType],
        response_schema: type[ResponseSchemaType],
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize read-only service.

        Args:
            db: Database session
            model_class: SQLAlchemy model class
            response_schema: Pydantic schema for responses
            tenant_id: Tenant identifier for multi-tenancy
        """
        self.db = db
        self.model_class = model_class
        self.response_schema = response_schema
        self.tenant_id = tenant_id

        # Initialize repository
        self.repository = create_repository(db, model_class, tenant_id)

        # Set up logging
        self._logger = logging.getLogger(f"{__name__}.{model_class.__name__}ReadOnlyService")

    async def get_by_id(self, entity_id: UUID) -> Optional[ResponseSchemaType]:
        """Get entity by ID."""
        entity = self.repository.get_by_id(entity_id)
        if entity:
            return self._to_response_schema(entity)
        return None

    async def list(
        self,
        filters: Optional[dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[ResponseSchemaType]:
        """List entities with filtering, sorting, and pagination."""
        entities = self.repository.list(
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
        return [self._to_response_schema(entity) for entity in entities]

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """Count entities with optional filtering."""
        return self.repository.count(filters)

    def _to_response_schema(self, entity: ModelType) -> ResponseSchemaType:
        """Convert entity to response schema."""
        entity_dict = {}
        for column in entity.__table__.columns:
            value = getattr(entity, column.name)
            entity_dict[column.name] = value

        return self.response_schema(**entity_dict)
