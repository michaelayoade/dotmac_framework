"""
Unified service layer pattern for DotMac Framework.
Consolidates service logic from ISP and Management modules.
"""
from __future__ import annotations

import logging
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..core.exceptions import EntityNotFoundError, ValidationError

# Try to import from multiple possible database sources
try:
    from dotmac.database.base import Base
except ImportError:
    try:
        from sqlalchemy.orm import DeclarativeBase as Base
    except ImportError:
        from sqlalchemy.ext.declarative import declarative_base

        Base = declarative_base()
from ..repositories import create_repository

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticBaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticBaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=PydanticBaseModel)


class BaseService(
    Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]
):
    """
    Unified base service providing common business logic operations.

    Features:
    - Repository pattern integration
    - Schema validation
    - Consistent error handling
    - Audit trail support
    - Tenant isolation
    - Business rule validation
    """

    def __init__(
        self,
        db: Session | AsyncSession,
        model_class: type[ModelType],
        create_schema: type[CreateSchemaType],
        update_schema: type[UpdateSchemaType],
        response_schema: type[ResponseSchemaType],
        tenant_id: str | None = None,
    ):
        self.db = db
        self.model_class = model_class
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schema = response_schema
        self.tenant_id = tenant_id

        # Create repository instance
        self.repository = create_repository(db, model_class, tenant_id)

        self._logger = logging.getLogger(f"{__name__}.{model_class.__name__}")

    async def create(
        self, data: CreateSchemaType, user_id: str | None = None, **kwargs
    ) -> ResponseSchemaType:
        """Create a new entity with validation and business rules."""
        try:
            # Convert Pydantic model to dict
            if isinstance(data, PydanticBaseModel):
                data_dict = data.model_dump(exclude_unset=True)
            else:
                data_dict = data

            # Apply business rules before creation
            data_dict = await self._apply_create_business_rules(
                data_dict, user_id, **kwargs
            )

            # Create entity through repository
            if isinstance(self.db, AsyncSession):
                entity = await self.repository.create(data_dict, user_id)
            else:
                entity = self.repository.create(data_dict, user_id=user_id)

            # Convert to response schema
            return self._to_response_schema(entity)

        except Exception as e:
            self._logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise

    async def get_by_id(
        self, entity_id: UUID, user_id: str | None = None, **kwargs
    ) -> ResponseSchemaType:
        """Get entity by ID with authorization check."""
        try:
            # Get entity through repository
            if isinstance(self.db, AsyncSession):
                entity = await self.repository.get_by_id(entity_id)
            else:
                entity = self.repository.get_by_id(entity_id)

            if not entity:
                raise EntityNotFoundError(
                    f"{self.model_class.__name__} not found with ID: {entity_id}"
                )

            # Apply authorization rules
            await self._check_read_authorization(entity, user_id, **kwargs)

            # Convert to response schema
            return self._to_response_schema(entity)

        except EntityNotFoundError:
            raise
        except Exception as e:
            self._logger.error(
                f"Error getting {self.model_class.__name__} by ID {entity_id}: {e}"
            )
            raise

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> list[ResponseSchemaType]:
        """List entities with filtering and authorization."""
        try:
            # Apply authorization filters
            filters = await self._apply_list_authorization(filters, user_id, **kwargs)

            # Get entities through repository
            if isinstance(self.db, AsyncSession):
                entities = await self.repository.list(
                    skip=skip, limit=limit, filters=filters, order_by=order_by
                )
            else:
                entities = self.repository.list(
                    offset=skip, limit=limit, filters=filters, sort_by=order_by
                )

            # Convert to response schemas
            return [self._to_response_schema(entity) for entity in entities]

        except Exception as e:
            self._logger.error(f"Error listing {self.model_class.__name__}: {e}")
            raise

    async def list_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> tuple[list[ResponseSchemaType], int]:
        """List entities with pagination and total count."""
        try:
            # Apply authorization filters
            filters = await self._apply_list_authorization(filters, user_id, **kwargs)

            # Get entities through repository
            if isinstance(self.db, AsyncSession):
                entities, total = await self.repository.list_paginated(
                    page=page, per_page=per_page, filters=filters, order_by=order_by
                )
            else:
                entities, total = self.repository.list_paginated(
                    page=page, per_page=per_page, filters=filters, sort_by=order_by
                )

            # Convert to response schemas
            response_items = [self._to_response_schema(entity) for entity in entities]
            return response_items, total

        except Exception as e:
            self._logger.error(f"Error paginating {self.model_class.__name__}: {e}")
            raise

    async def count(
        self,
        filters: dict[str, Any] | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> int:
        """Count entities with filtering and authorization."""
        try:
            # Apply authorization filters
            filters = await self._apply_list_authorization(filters, user_id, **kwargs)

            # Count entities through repository
            if isinstance(self.db, AsyncSession):
                return await self.repository.count(filters)
            else:
                return self.repository.count(filters)

        except Exception as e:
            self._logger.error(f"Error counting {self.model_class.__name__}: {e}")
            raise

    async def update(
        self,
        entity_id: UUID,
        data: UpdateSchemaType,
        user_id: str | None = None,
        **kwargs,
    ) -> ResponseSchemaType:
        """Update entity with validation and business rules."""
        try:
            # Check if entity exists and user has permission
            if isinstance(self.db, AsyncSession):
                existing_entity = await self.repository.get_by_id(entity_id)
            else:
                existing_entity = self.repository.get_by_id(entity_id)

            if not existing_entity:
                raise EntityNotFoundError(
                    f"{self.model_class.__name__} not found with ID: {entity_id}"
                )

            # Apply authorization check
            await self._check_update_authorization(existing_entity, user_id, **kwargs)

            # Convert Pydantic model to dict
            if isinstance(data, PydanticBaseModel):
                data_dict = data.model_dump(exclude_unset=True)
            else:
                data_dict = data

            # Apply business rules before update
            data_dict = await self._apply_update_business_rules(
                existing_entity, data_dict, user_id, **kwargs
            )

            # Update entity through repository
            if isinstance(self.db, AsyncSession):
                entity = await self.repository.update(entity_id, data_dict, user_id)
            else:
                entity = self.repository.update(entity_id, data_dict, user_id=user_id)

            if not entity:
                raise EntityNotFoundError(
                    f"{self.model_class.__name__} not found with ID: {entity_id}"
                )

            # Convert to response schema
            return self._to_response_schema(entity)

        except EntityNotFoundError:
            raise
        except Exception as e:
            self._logger.error(
                f"Error updating {self.model_class.__name__} {entity_id}: {e}"
            )
            raise

    async def delete(
        self,
        entity_id: UUID,
        user_id: str | None = None,
        soft_delete: bool = True,
        **kwargs,
    ) -> bool:
        """Delete entity with authorization check."""
        try:
            # Check if entity exists and user has permission
            if isinstance(self.db, AsyncSession):
                existing_entity = await self.repository.get_by_id(entity_id)
            else:
                existing_entity = self.repository.get_by_id(entity_id)

            if not existing_entity:
                raise EntityNotFoundError(
                    f"{self.model_class.__name__} not found with ID: {entity_id}"
                )

            # Apply authorization check
            await self._check_delete_authorization(existing_entity, user_id, **kwargs)

            # Apply business rules before deletion
            await self._apply_delete_business_rules(existing_entity, user_id, **kwargs)

            # Delete entity through repository
            if isinstance(self.db, AsyncSession):
                return await self.repository.delete(entity_id, soft_delete, user_id)
            else:
                return self.repository.delete(
                    entity_id, soft_delete=soft_delete, user_id=user_id
                )

        except EntityNotFoundError:
            raise
        except Exception as e:
            self._logger.error(
                f"Error deleting {self.model_class.__name__} {entity_id}: {e}"
            )
            raise

    async def search(
        self,
        search_term: str,
        search_fields: list[str],
        limit: int = 100,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> list[ResponseSchemaType]:
        """Search entities with authorization."""
        try:
            # Apply authorization filters
            filters = await self._apply_list_authorization(filters, user_id, **kwargs)

            # Search entities through repository
            if isinstance(self.db, AsyncSession):
                entities = await self.repository.search(
                    search_term=search_term,
                    search_fields=search_fields,
                    skip=offset,
                    limit=limit,
                    filters=filters,
                )
            else:
                entities = self.repository.search(
                    search_term=search_term,
                    search_fields=search_fields,
                    limit=limit,
                    offset=offset,
                    filters=filters,
                )

            # Convert to response schemas
            return [self._to_response_schema(entity) for entity in entities]

        except Exception as e:
            self._logger.error(f"Error searching {self.model_class.__name__}: {e}")
            raise

    def _to_response_schema(self, entity: ModelType) -> ResponseSchemaType:
        """Convert entity to response schema."""
        try:
            # Convert SQLAlchemy model to dict
            if hasattr(entity, "__dict__"):
                entity_dict = {}
                for key, value in entity.__dict__.items():
                    if not key.startswith("_"):
                        entity_dict[key] = value
            else:
                entity_dict = entity

            # Create response schema instance
            return self.response_schema(**entity_dict)

        except Exception as e:
            self._logger.error(
                f"Error converting {self.model_class.__name__} to response schema: {e}"
            )
            raise ValidationError(f"Failed to serialize entity: {e}") from e

    # Business rule hooks (override in subclasses)
    async def _apply_create_business_rules(
        self, data: dict[str, Any], user_id: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """Apply business rules before entity creation. Override in subclasses."""
        return data

    async def _apply_update_business_rules(
        self,
        existing_entity: ModelType,
        data: dict[str, Any],
        user_id: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Apply business rules before entity update. Override in subclasses."""
        return data

    async def _apply_delete_business_rules(
        self, entity: ModelType, user_id: str | None = None, **kwargs
    ) -> None:
        """Apply business rules before entity deletion. Override in subclasses."""
        pass

    # Authorization hooks (override in subclasses)
    async def _check_read_authorization(
        self, entity: ModelType, user_id: str | None = None, **kwargs
    ) -> None:
        """Check if user can read entity. Override in subclasses."""
        pass

    async def _check_update_authorization(
        self, entity: ModelType, user_id: str | None = None, **kwargs
    ) -> None:
        """Check if user can update entity. Override in subclasses."""
        pass

    async def _check_delete_authorization(
        self, entity: ModelType, user_id: str | None = None, **kwargs
    ) -> None:
        """Check if user can delete entity. Override in subclasses."""
        pass

    async def _apply_list_authorization(
        self,
        filters: dict[str, Any] | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> dict[str, Any] | None:
        """Apply authorization filters to list queries. Override in subclasses."""
        return filters
