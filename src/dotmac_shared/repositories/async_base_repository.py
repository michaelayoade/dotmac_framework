"""
Unified async repository pattern for DotMac Framework.
Consolidates repository logic from ISP and Management modules.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.exceptions import DatabaseError, ValidationError

# Import Base from the proper location
try:
    from dotmac.database.base import Base
except ImportError:
    try:
        from sqlalchemy.ext.declarative import declarative_base

        Base = declarative_base()
    except ImportError:
        from sqlalchemy.orm import DeclarativeBase

        class Base(DeclarativeBase):
            pass


logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class AsyncBaseRepository(Generic[ModelType]):
    """
    Unified async repository providing common CRUD operations.

    Features:
    - Generic CRUD operations with type safety
    - Tenant isolation support
    - Soft delete support
    - Advanced filtering and pagination
    - Bulk operations
    - Search capabilities
    - Consistent error handling
    """

    def __init__(self, db: AsyncSession, model: type[ModelType], tenant_id: str | None = None):
        self.db = db
        self.model = model
        self.tenant_id = tenant_id
        self._logger = logging.getLogger(f"{__name__}.{model.__name__}")

    async def create(self, obj_data: dict[str, Any], user_id: str | None = None) -> ModelType:
        """Create a new record with audit fields."""
        try:
            # Add audit fields
            if user_id:
                obj_data["created_by"] = user_id
                obj_data["updated_by"] = user_id

            # Add tenant isolation
            if self.tenant_id and hasattr(self.model, "tenant_id"):
                obj_data["tenant_id"] = self.tenant_id

            db_obj = self.model(**obj_data)
            self.db.add(db_obj)
            await self.db.flush()
            await self.db.refresh(db_obj)

            self._logger.info(f"Created {self.model.__name__} with ID: {db_obj.id}")
            return db_obj

        except SQLAlchemyError as e:
            await self.db.rollback()
            self._logger.exception(f"Error creating {self.model.__name__}")
            raise DatabaseError(f"Failed to create entity: {e}") from e

    async def get_by_id(
        self,
        id: UUID,
        include_deleted: bool = False,
        relationships: list[str] | None = None,
    ) -> ModelType | None:
        """Get record by ID with optional relationships."""
        try:
            query = select(self.model).where(self.model.id == id)

            # Apply tenant filtering
            if self.tenant_id and hasattr(self.model, "tenant_id"):
                query = query.where(self.model.tenant_id == self.tenant_id)

            # Apply soft delete filtering
            if not include_deleted and hasattr(self.model, "is_deleted"):
                query = query.where(self.model.is_deleted.is_(False))

            # Load relationships
            if relationships:
                for rel in relationships:
                    if hasattr(self.model, rel):
                        query = query.options(selectinload(getattr(self.model, rel)))

            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            self._logger.exception(f"Error getting {self.model.__name__} by ID {id}")
            raise DatabaseError(f"Failed to retrieve entity: {e}") from e

    async def get_by_field(self, field_name: str, value: Any, include_deleted: bool = False) -> ModelType | None:
        """Get record by any field."""
        try:
            if not hasattr(self.model, field_name):
                raise ValidationError(f"Field {field_name} does not exist on {self.model.__name__}")

            field = getattr(self.model, field_name)
            query = select(self.model).where(field == value)

            # Apply tenant filtering
            if self.tenant_id and hasattr(self.model, "tenant_id"):
                query = query.where(self.model.tenant_id == self.tenant_id)

            # Apply soft delete filtering
            if not include_deleted and hasattr(self.model, "is_deleted"):
                query = query.where(self.model.is_deleted.is_(False))

            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            self._logger.exception(f"Error getting {self.model.__name__} by {field_name}")
            raise DatabaseError(f"Failed to retrieve entity by {field_name}: {e}") from e

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        include_deleted: bool = False,
        relationships: list[str] | None = None,
    ) -> list[ModelType]:
        """List records with filtering, sorting, and pagination."""
        try:
            query = select(self.model)

            # Apply tenant filtering
            if self.tenant_id and hasattr(self.model, "tenant_id"):
                query = query.where(self.model.tenant_id == self.tenant_id)

            # Apply soft delete filtering
            if not include_deleted and hasattr(self.model, "is_deleted"):
                query = query.where(self.model.is_deleted.is_(False))

            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)

            # Apply ordering
            if order_by:
                query = self._apply_ordering(query, order_by)
            elif hasattr(self.model, "created_at"):
                query = query.order_by(self.model.created_at.desc())

            # Load relationships
            if relationships:
                for rel in relationships:
                    if hasattr(self.model, rel):
                        query = query.options(selectinload(getattr(self.model, rel)))

            # Apply pagination
            query = query.offset(skip).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except SQLAlchemyError as e:
            self._logger.exception(f"Error listing {self.model.__name__}")
            raise DatabaseError(f"Failed to list entities: {e}") from e

    async def list_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        include_deleted: bool = False,
        relationships: list[str] | None = None,
    ) -> tuple[list[ModelType], int]:
        """List records with proper pagination and total count."""
        try:
            # Build base query
            query = select(self.model)

            # Apply tenant filtering
            if self.tenant_id and hasattr(self.model, "tenant_id"):
                query = query.where(self.model.tenant_id == self.tenant_id)

            # Apply soft delete filtering
            if not include_deleted and hasattr(self.model, "is_deleted"):
                query = query.where(self.model.is_deleted.is_(False))

            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)

            # Get total count before pagination
            count_query = select(func.count()).select_from(query.alias())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()

            # Apply ordering
            if order_by:
                query = self._apply_ordering(query, order_by)
            elif hasattr(self.model, "created_at"):
                query = query.order_by(self.model.created_at.desc())

            # Load relationships
            if relationships:
                for rel in relationships:
                    if hasattr(self.model, rel):
                        query = query.options(selectinload(getattr(self.model, rel)))

            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)

            result = await self.db.execute(query)
            items = result.scalars().all()

            return items, total

        except SQLAlchemyError as e:
            self._logger.exception(f"Error paginating {self.model.__name__}")
            raise DatabaseError(f"Failed to paginate entities: {e}") from e

    async def count(self, filters: dict[str, Any] | None = None, include_deleted: bool = False) -> int:
        """Count records with filtering."""
        try:
            query = select(func.count(self.model.id))

            # Apply tenant filtering
            if self.tenant_id and hasattr(self.model, "tenant_id"):
                query = query.where(self.model.tenant_id == self.tenant_id)

            # Apply soft delete filtering
            if not include_deleted and hasattr(self.model, "is_deleted"):
                query = query.where(self.model.is_deleted.is_(False))

            # Apply filters
            if filters:
                # Create a subquery for complex filtering
                base_query = select(self.model)
                if self.tenant_id and hasattr(self.model, "tenant_id"):
                    base_query = base_query.where(self.model.tenant_id == self.tenant_id)
                if not include_deleted and hasattr(self.model, "is_deleted"):
                    base_query = base_query.where(self.model.is_deleted.is_(False))

                base_query = self._apply_filters(base_query, filters)
                query = select(func.count()).select_from(base_query.alias())

            result = await self.db.execute(query)
            return result.scalar()

        except SQLAlchemyError as e:
            self._logger.exception(f"Error counting {self.model.__name__}")
            raise DatabaseError(f"Failed to count entities: {e}") from e

    async def update(self, id: UUID, obj_data: dict[str, Any], user_id: str | None = None) -> ModelType | None:
        """Update a record with audit fields."""
        try:
            # Set audit fields
            obj_data["updated_at"] = datetime.now(timezone.utc)
            if user_id:
                obj_data["updated_by"] = user_id

            # Build update query with tenant filtering
            query = update(self.model).where(self.model.id == id)

            if self.tenant_id and hasattr(self.model, "tenant_id"):
                query = query.where(self.model.tenant_id == self.tenant_id)

            if hasattr(self.model, "is_deleted"):
                query = query.where(self.model.is_deleted.is_(False))

            query = query.values(**obj_data).execution_options(synchronize_session="fetch")
            result = await self.db.execute(query)

            if result.rowcount == 0:
                return None

            self._logger.info(f"Updated {self.model.__name__} with ID: {id}")
            return await self.get_by_id(id)

        except SQLAlchemyError as e:
            await self.db.rollback()
            self._logger.exception(f"Error updating {self.model.__name__} {id}")
            raise DatabaseError(f"Failed to update entity: {e}") from e

    async def delete(self, id: UUID, soft_delete: bool = True, user_id: str | None = None) -> bool:
        """Delete a record (soft or hard delete)."""
        try:
            if soft_delete and hasattr(self.model, "is_deleted"):
                obj_data = {"is_deleted": True, "deleted_at": func.now()}
                if user_id:
                    obj_data["updated_by"] = user_id

                query = update(self.model).where(self.model.id == id)

                if self.tenant_id and hasattr(self.model, "tenant_id"):
                    query = query.where(self.model.tenant_id == self.tenant_id)

                query = query.where(self.model.is_deleted.is_(False)).values(**obj_data)
            else:
                query = delete(self.model).where(self.model.id == id)

                if self.tenant_id and hasattr(self.model, "tenant_id"):
                    query = query.where(self.model.tenant_id == self.tenant_id)

            result = await self.db.execute(query)
            success = result.rowcount > 0

            if success:
                self._logger.info(f"Deleted {self.model.__name__} with ID: {id} (soft: {soft_delete})")

            return success

        except SQLAlchemyError as e:
            await self.db.rollback()
            self._logger.exception(f"Error deleting {self.model.__name__} {id}")
            raise DatabaseError(f"Failed to delete entity: {e}") from e

    async def bulk_create(self, objects_data: list[dict[str, Any]], user_id: str | None = None) -> list[ModelType]:
        """Create multiple records in bulk."""
        try:
            # Add audit fields and tenant isolation to all objects
            for obj_data in objects_data:
                if user_id:
                    obj_data["created_by"] = user_id
                    obj_data["updated_by"] = user_id
                if self.tenant_id and hasattr(self.model, "tenant_id"):
                    obj_data["tenant_id"] = self.tenant_id

            db_objects = [self.model(**obj_data) for obj_data in objects_data]
            self.db.add_all(db_objects)
            await self.db.flush()

            for db_obj in db_objects:
                await self.db.refresh(db_obj)

            self._logger.info(f"Bulk created {len(db_objects)} {self.model.__name__} entities")
            return db_objects

        except SQLAlchemyError as e:
            await self.db.rollback()
            self._logger.exception(f"Error bulk creating {self.model.__name__}")
            raise DatabaseError(f"Failed to bulk create entities: {e}") from e

    async def exists(self, id: UUID) -> bool:
        """Check if record exists."""
        try:
            query = select(func.count(self.model.id)).where(self.model.id == id)

            if self.tenant_id and hasattr(self.model, "tenant_id"):
                query = query.where(self.model.tenant_id == self.tenant_id)

            if hasattr(self.model, "is_deleted"):
                query = query.where(self.model.is_deleted.is_(False))

            result = await self.db.execute(query)
            return result.scalar() > 0

        except SQLAlchemyError as e:
            self._logger.exception(f"Error checking existence of {self.model.__name__} {id}")
            raise DatabaseError(f"Failed to check entity existence: {e}") from e

    async def search(
        self,
        search_term: str,
        search_fields: list[str],
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> list[ModelType]:
        """Search records across multiple fields."""
        try:
            query = select(self.model)

            # Apply tenant filtering
            if self.tenant_id and hasattr(self.model, "tenant_id"):
                query = query.where(self.model.tenant_id == self.tenant_id)

            # Apply soft delete filtering
            if hasattr(self.model, "is_deleted"):
                query = query.where(self.model.is_deleted.is_(False))

            # Add search conditions
            search_conditions = []
            for field_name in search_fields:
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    search_conditions.append(field.ilike(f"%{search_term}%"))

            if search_conditions:
                from sqlalchemy import or_

                query = query.where(or_(*search_conditions))

            # Apply additional filters
            if filters:
                query = self._apply_filters(query, filters)

            # Apply ordering and pagination
            if hasattr(self.model, "created_at"):
                query = query.order_by(self.model.created_at.desc())
            query = query.offset(skip).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except SQLAlchemyError as e:
            self._logger.exception(f"Error searching {self.model.__name__}")
            raise DatabaseError(f"Failed to search entities: {e}") from e

    def _apply_filters(self, query, filters: dict[str, Any]):
        """Apply filters to query with support for advanced operators."""
        for field_name, value in filters.items():
            if not hasattr(self.model, field_name):
                continue

            field = getattr(self.model, field_name)

            # Handle different filter types
            if isinstance(value, dict):
                # Advanced filters (e.g., {'gt': 10}, {'in': [1,2,3]})
                for operator, filter_value in value.items():
                    if operator == "gt":
                        query = query.where(field > filter_value)
                    elif operator == "gte":
                        query = query.where(field >= filter_value)
                    elif operator == "lt":
                        query = query.where(field < filter_value)
                    elif operator == "lte":
                        query = query.where(field <= filter_value)
                    elif operator == "in":
                        query = query.where(field.in_(filter_value))
                    elif operator == "not_in":
                        query = query.where(~field.in_(filter_value))
                    elif operator == "like":
                        query = query.where(field.like(f"%{filter_value}%"))
                    elif operator == "ilike":
                        query = query.where(field.ilike(f"%{filter_value}%"))
                    elif operator == "is_null":
                        if filter_value:
                            query = query.where(field.is_(None))
                        else:
                            query = query.where(field.isnot(None))
            elif isinstance(value, list):
                # IN filter
                query = query.where(field.in_(value))
            else:
                # Equality filter
                query = query.where(field == value)

        return query

    def _apply_ordering(self, query, order_by: str):
        """Apply ordering to query."""
        if order_by.startswith("-"):
            field_name = order_by[1:]
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                query = query.order_by(field.desc())
        else:
            if hasattr(self.model, order_by):
                field = getattr(self.model, order_by)
                query = query.order_by(field.asc())
        return query


class AsyncTenantRepository(AsyncBaseRepository[ModelType]):
    """
    Async repository for tenant-aware entities.
    Extends AsyncBaseRepository with additional tenant-specific functionality.
    """

    def __init__(self, db: AsyncSession, model: type[ModelType], tenant_id: str):
        if not tenant_id:
            raise ValidationError("tenant_id is required for tenant repositories")

        if not hasattr(model, "tenant_id"):
            raise ValidationError(f"Model {model.__name__} must have tenant_id field")

        super().__init__(db, model, tenant_id)

    async def get_tenant_stats(self) -> dict[str, Any]:
        """Get statistics for current tenant."""
        try:
            total_count = await self.count()

            stats = {
                "total_entities": total_count,
                "tenant_id": self.tenant_id,
                "entity_type": self.model.__name__,
            }

            # Add timestamp-based stats if supported
            if hasattr(self.model, "created_at"):
                # Entities created today
                today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                today_count = await self.count({"created_at": {"gte": today_start}})
                stats["created_today"] = today_count

                # Entities created this month
                month_start = today_start.replace(day=1)
                month_count = await self.count({"created_at": {"gte": month_start}})
                stats["created_this_month"] = month_count

            return stats

        except SQLAlchemyError as e:
            self._logger.exception(f"Error getting tenant stats for {self.model.__name__}")
            raise DatabaseError(f"Failed to get tenant statistics: {e}") from e
