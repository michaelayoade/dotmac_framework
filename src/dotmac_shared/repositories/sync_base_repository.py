"""
Unified sync repository pattern for DotMac Framework.
Consolidates synchronous repository logic with consistent API.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import asc, desc, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Query, Session

from ..core.exceptions import DatabaseError, DuplicateEntityError, EntityNotFoundError, ValidationError

# Import Base from the proper location
try:
    from dotmac.database.base import Base, BaseModel
except ImportError:
    try:
        from sqlalchemy.ext.declarative import declarative_base

        Base = declarative_base()
        BaseModel = Base  # Fallback assumption
    except ImportError:
        from sqlalchemy.orm import DeclarativeBase

        class Base(DeclarativeBase):
            pass

        BaseModel = Base

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class SyncBaseRepository(Generic[ModelType]):
    """
    Unified sync repository providing common CRUD operations.

    Features:
    - Generic CRUD operations with type safety
    - Tenant isolation support
    - Soft delete support
    - Advanced filtering and pagination
    - Bulk operations
    - Search capabilities
    - Consistent error handling
    """

    def __init__(self, db: Session, model_class: type[ModelType], tenant_id: str | None = None):
        self.db = db
        self.model_class = model_class
        self.tenant_id = tenant_id
        self._logger = logging.getLogger(f"{__name__}.{model_class.__name__}")

    def create(self, data: dict[str, Any], commit: bool = True, user_id: str | None = None) -> ModelType:
        """Create a new entity with audit fields."""
        try:
            # Add audit fields
            if user_id:
                data["created_by"] = user_id
                data["updated_by"] = user_id

            # Add tenant_id if model supports multi-tenancy
            if self.tenant_id and issubclass(self.model_class, BaseModel):
                data["tenant_id"] = self.tenant_id

            # Create entity
            entity = self.model_class(**data)
            self.db.add(entity)

            if commit:
                self.db.commit()
                self.db.refresh(entity)

            self._logger.info(f"Created {self.model_class.__name__} with ID: {entity.id}")
            return entity

        except IntegrityError as e:
            self.db.rollback()
            self._logger.error(f"Integrity error creating {self.model_class.__name__}: {e}")
            raise DuplicateEntityError(f"Entity already exists: {e.orig}") from e
        except SQLAlchemyError as e:
            self.db.rollback()
            self._logger.exception(f"Error creating {self.model_class.__name__}")
            raise DatabaseError(f"Failed to create entity: {e}") from e

    def get_by_id(self, entity_id: UUID, include_deleted: bool = False) -> ModelType | None:
        """Get entity by ID with tenant and soft delete filtering."""
        try:
            query = self._build_base_query(include_deleted).filter(self.model_class.id == entity_id)
            return query.first()
        except SQLAlchemyError as e:
            self._logger.exception(f"Error getting {self.model_class.__name__} by ID {entity_id}")
            raise DatabaseError(f"Failed to retrieve entity: {e}") from e

    def get_by_id_or_raise(self, entity_id: UUID, include_deleted: bool = False) -> ModelType:
        """Get entity by ID or raise exception."""
        entity = self.get_by_id(entity_id, include_deleted)
        if not entity:
            raise EntityNotFoundError(f"{self.model_class.__name__} not found with ID: {entity_id}")
        return entity

    def get_by_field(self, field_name: str, value: Any, include_deleted: bool = False) -> ModelType | None:
        """Get entity by any field."""
        try:
            if not hasattr(self.model_class, field_name):
                raise ValidationError(f"Field {field_name} does not exist on {self.model_class.__name__}")

            field = getattr(self.model_class, field_name)
            query = self._build_base_query(include_deleted).filter(field == value)
            return query.first()

        except SQLAlchemyError as e:
            self._logger.exception(f"Error getting {self.model_class.__name__} by {field_name}")
            raise DatabaseError(f"Failed to retrieve entity by {field_name}: {e}") from e

    def list(
        self,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        limit: int | None = None,
        offset: int | None = None,
        include_deleted: bool = False,
    ) -> list[ModelType]:
        """List entities with filtering, sorting, and pagination."""
        try:
            query = self._build_base_query(include_deleted)

            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)

            # Apply sorting
            if sort_by:
                if hasattr(self.model_class, sort_by):
                    sort_column = getattr(self.model_class, sort_by)
                    if sort_order.lower() == "desc":
                        query = query.order_by(desc(sort_column))
                    else:
                        query = query.order_by(asc(sort_column))
            elif hasattr(self.model_class, "created_at"):
                query = query.order_by(desc(self.model_class.created_at))

            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            return query.all()

        except SQLAlchemyError as e:
            self._logger.exception(f"Error listing {self.model_class.__name__}")
            raise DatabaseError(f"Failed to list entities: {e}") from e

    def list_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        include_deleted: bool = False,
    ) -> tuple[list[ModelType], int]:
        """List entities with pagination and total count."""
        try:
            query = self._build_base_query(include_deleted)

            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)

            # Get total count
            total = query.count()

            # Apply sorting
            if sort_by:
                if hasattr(self.model_class, sort_by):
                    sort_column = getattr(self.model_class, sort_by)
                    if sort_order.lower() == "desc":
                        query = query.order_by(desc(sort_column))
                    else:
                        query = query.order_by(asc(sort_column))
            elif hasattr(self.model_class, "created_at"):
                query = query.order_by(desc(self.model_class.created_at))

            # Apply pagination
            offset = (page - 1) * per_page
            items = query.offset(offset).limit(per_page).all()

            return items, total

        except SQLAlchemyError as e:
            self._logger.exception(f"Error paginating {self.model_class.__name__}")
            raise DatabaseError(f"Failed to paginate entities: {e}") from e

    def count(self, filters: dict[str, Any] | None = None, include_deleted: bool = False) -> int:
        """Count entities with optional filtering."""
        try:
            query = self._build_base_query(include_deleted)

            if filters:
                query = self._apply_filters(query, filters)

            return query.count()

        except SQLAlchemyError as e:
            self._logger.exception(f"Error counting {self.model_class.__name__}")
            raise DatabaseError(f"Failed to count entities: {e}") from e

    def update(
        self, entity_id: UUID, data: dict[str, Any], commit: bool = True, user_id: str | None = None
    ) -> ModelType:
        """Update entity with audit fields."""
        try:
            entity = self.get_by_id_or_raise(entity_id)

            # Update entity attributes
            for key, value in data.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            # Update audit fields
            if hasattr(entity, "updated_at"):
                entity.updated_at = datetime.now(timezone.utc)
            if user_id and hasattr(entity, "updated_by"):
                entity.updated_by = user_id

            if commit:
                self.db.commit()
                self.db.refresh(entity)

            self._logger.info(f"Updated {self.model_class.__name__} with ID: {entity_id}")
            return entity

        except EntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            self._logger.exception(f"Error updating {self.model_class.__name__} {entity_id}")
            raise DatabaseError(f"Failed to update entity: {e}") from e

    def delete(
        self, entity_id: UUID, commit: bool = True, soft_delete: bool = True, user_id: str | None = None
    ) -> bool:
        """Delete entity (soft or hard delete)."""
        try:
            entity = self.get_by_id_or_raise(entity_id)

            if soft_delete and hasattr(entity, "is_deleted"):
                # Soft delete
                entity.is_deleted = True
                if hasattr(entity, "deleted_at"):
                    entity.deleted_at = datetime.now(timezone.utc)
                if user_id and hasattr(entity, "updated_by"):
                    entity.updated_by = user_id
            else:
                # Hard delete
                self.db.delete(entity)

            if commit:
                self.db.commit()

            self._logger.info(f"Deleted {self.model_class.__name__} with ID: {entity_id} (soft: {soft_delete})")
            return True

        except EntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            self._logger.exception(f"Error deleting {self.model_class.__name__} {entity_id}")
            raise DatabaseError(f"Failed to delete entity: {e}") from e

    def bulk_create(
        self, data_list: list[dict[str, Any]], commit: bool = True, user_id: str | None = None
    ) -> list[ModelType]:
        """Create multiple entities in bulk."""
        try:
            entities = []
            for data in data_list:
                # Add audit fields
                if user_id:
                    data["created_by"] = user_id
                    data["updated_by"] = user_id

                # Add tenant_id if model supports multi-tenancy
                if self.tenant_id and issubclass(self.model_class, BaseModel):
                    data["tenant_id"] = self.tenant_id

                entity = self.model_class(**data)
                entities.append(entity)
                self.db.add(entity)

            if commit:
                self.db.commit()
                for entity in entities:
                    self.db.refresh(entity)

            self._logger.info(f"Bulk created {len(entities)} {self.model_class.__name__} entities")
            return entities

        except SQLAlchemyError as e:
            self.db.rollback()
            self._logger.exception(f"Error bulk creating {self.model_class.__name__}")
            raise DatabaseError(f"Failed to bulk create entities: {e}") from e

    def bulk_update(self, updates: list[dict[str, Any]], commit: bool = True, user_id: str | None = None) -> int:
        """Update multiple entities in bulk."""
        try:
            updated_count = 0

            for update_data in updates:
                entity_id = update_data.pop("id")
                entity = self.get_by_id(entity_id)

                if entity:
                    for key, value in update_data.items():
                        if hasattr(entity, key):
                            setattr(entity, key, value)

                    if hasattr(entity, "updated_at"):
                        entity.updated_at = datetime.now(timezone.utc)
                    if user_id and hasattr(entity, "updated_by"):
                        entity.updated_by = user_id

                    updated_count += 1

            if commit:
                self.db.commit()

            self._logger.info(f"Bulk updated {updated_count} {self.model_class.__name__} entities")
            return updated_count

        except SQLAlchemyError as e:
            self.db.rollback()
            self._logger.exception(f"Error bulk updating {self.model_class.__name__}")
            raise DatabaseError(f"Failed to bulk update entities: {e}") from e

    def exists(self, filters: dict[str, Any], include_deleted: bool = False) -> bool:
        """Check if entity exists with given filters."""
        try:
            query = self._build_base_query(include_deleted)
            query = self._apply_filters(query, filters)
            return query.first() is not None

        except SQLAlchemyError as e:
            self._logger.exception(f"Error checking existence of {self.model_class.__name__}")
            raise DatabaseError(f"Failed to check entity existence: {e}") from e

    def search(
        self,
        search_term: str,
        search_fields: list[str],
        limit: int | None = None,
        offset: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[ModelType]:
        """Search entities across multiple fields."""
        try:
            query = self._build_base_query()

            # Add search conditions
            search_conditions = []
            for field_name in search_fields:
                if hasattr(self.model_class, field_name):
                    field = getattr(self.model_class, field_name)
                    search_conditions.append(field.ilike(f"%{search_term}%"))

            if search_conditions:
                query = query.filter(or_(*search_conditions))

            # Apply additional filters
            if filters:
                query = self._apply_filters(query, filters)

            # Apply ordering
            if hasattr(self.model_class, "created_at"):
                query = query.order_by(desc(self.model_class.created_at))

            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            return query.all()

        except SQLAlchemyError as e:
            self._logger.exception(f"Error searching {self.model_class.__name__}")
            raise DatabaseError(f"Failed to search entities: {e}") from e

    def _build_base_query(self, include_deleted: bool = False) -> Query:
        """Build base query with tenant and soft delete filtering."""
        query = self.db.query(self.model_class)

        # Apply tenant filtering if supported
        if self.tenant_id and issubclass(self.model_class, BaseModel):
            query = query.filter(self.model_class.tenant_id == self.tenant_id)

        # Filter out soft-deleted entities if supported
        if not include_deleted and hasattr(self.model_class, "is_deleted"):
            query = query.filter(self.model_class.is_deleted.is_(False))

        return query

    def _apply_filters(self, query: Query, filters: dict[str, Any]) -> Query:
        """Apply filters to query with support for advanced operators."""
        for key, value in filters.items():
            if not hasattr(self.model_class, key):
                continue

            column = getattr(self.model_class, key)

            # Handle different filter types
            if isinstance(value, dict):
                # Advanced filters (e.g., {'gt': 10}, {'in': [1,2,3]})
                for operator, filter_value in value.items():
                    if operator == "gt":
                        query = query.filter(column > filter_value)
                    elif operator == "gte":
                        query = query.filter(column >= filter_value)
                    elif operator == "lt":
                        query = query.filter(column < filter_value)
                    elif operator == "lte":
                        query = query.filter(column <= filter_value)
                    elif operator == "in":
                        query = query.filter(column.in_(filter_value))
                    elif operator == "not_in":
                        query = query.filter(~column.in_(filter_value))
                    elif operator == "like":
                        query = query.filter(column.like(f"%{filter_value}%"))
                    elif operator == "ilike":
                        query = query.filter(column.ilike(f"%{filter_value}%"))
                    elif operator == "is_null":
                        if filter_value:
                            query = query.filter(column.is_(None))
                        else:
                            query = query.filter(column.isnot(None))
            elif isinstance(value, list):
                # IN filter
                query = query.filter(column.in_(value))
            else:
                # Equality filter
                query = query.filter(column == value)

        return query


class SyncTenantRepository(SyncBaseRepository[ModelType]):
    """
    Sync repository for tenant-aware entities.
    Extends SyncBaseRepository with additional tenant-specific functionality.
    """

    def __init__(self, db: Session, model_class: type[ModelType], tenant_id: str):
        if not tenant_id:
            raise ValidationError("tenant_id is required for tenant repositories")

        if not issubclass(model_class, BaseModel):
            raise ValidationError(f"Model {model_class.__name__} must inherit from BaseModel")

        super().__init__(db, model_class, tenant_id)

    def get_tenant_stats(self) -> dict[str, Any]:
        """Get statistics for current tenant."""
        try:
            total_count = self.count()

            stats = {
                "total_entities": total_count,
                "tenant_id": self.tenant_id,
                "entity_type": self.model_class.__name__,
            }

            # Add timestamp-based stats if supported
            if hasattr(self.model_class, "created_at"):
                # Entities created today
                today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                today_count = self.count({"created_at": {"gte": today_start}})
                stats["created_today"] = today_count

                # Entities created this month
                month_start = today_start.replace(day=1)
                month_count = self.count({"created_at": {"gte": month_start}})
                stats["created_this_month"] = month_count

            return stats

        except SQLAlchemyError as e:
            self._logger.exception(f"Error getting tenant stats for {self.model_class.__name__}")
            raise DatabaseError(f"Failed to get tenant statistics: {e}") from e
