"""
Asynchronous repository implementations.

High-performance async repositories with the same comprehensive feature set
as the synchronous versions.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Generic

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from dotmac.core.database import TenantMixin
from dotmac.core.db_toolkit.types import (
    AsyncRepositoryProtocol,
    DatabaseError,
    DuplicateEntityError,
    EntityNotFoundError,
    FilterOperator,
    ModelType,
    PaginationResult,
    QueryFilter,
    QueryOptions,
    SortField,
    SortOrder,
    ValidationError,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AsyncRepository(Generic[ModelType], AsyncRepositoryProtocol[ModelType]):
    """
    Unified asynchronous repository providing high-performance database operations.

    Async version of BaseRepository with identical API but optimized for
    high-concurrency scenarios and non-blocking I/O.

    Features:
    - Full async/await support
    - Identical API to sync repository
    - Optimized query execution
    - Connection pooling support
    - Concurrent operation safety
    """

    def __init__(
        self,
        db: AsyncSession,
        model_class: type[ModelType],
        tenant_id: str | None = None,
        auto_commit: bool = True,
    ):
        """
        Initialize async repository.

        Args:
            db: Async database session
            model_class: SQLAlchemy model class
            tenant_id: Tenant identifier for multi-tenancy
            auto_commit: Whether to auto-commit transactions
        """
        self.db = db
        self.model_class = model_class
        self.tenant_id = tenant_id
        self.auto_commit = auto_commit
        self._logger = logging.getLogger(f"{__name__}.{model_class.__name__}")

        # Check model capabilities
        self._supports_tenant = issubclass(model_class, TenantMixin)
        self._supports_soft_delete = hasattr(model_class, "is_deleted")
        self._supports_audit = hasattr(model_class, "created_at")

    async def create(self, data: dict[str, Any], user_id: str | None = None) -> ModelType:
        """
        Create a new entity asynchronously.

        Args:
            data: Entity data
            user_id: User performing the operation

        Returns:
            Created entity

        Raises:
            DuplicateEntityError: If entity already exists
            ValidationError: If data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Add tenant_id if model supports multi-tenancy
            if self.tenant_id and self._supports_tenant:
                data["tenant_id"] = self.tenant_id

            # Add audit fields if supported
            if user_id and self._supports_audit:
                data["created_by"] = user_id
                data["updated_by"] = user_id

            # Create entity
            entity = self.model_class(**data)
            self.db.add(entity)

            if self.auto_commit:
                await self.db.commit()
                await self.db.refresh(entity)
            else:
                await self.db.flush()
                await self.db.refresh(entity)

            self._logger.info("Created {self.model_class.__name__} with ID: %s", entity.id)
            return entity

        except IntegrityError as e:
            await self.db.rollback()
            self._logger.error("Integrity error creating {self.model_class.__name__}: %s", e)
            msg = f"Entity already exists: {e.orig}"

            raise DuplicateEntityError(msg) from e
        except Exception as e:
            await self.db.rollback()
            self._logger.error("Error creating {self.model_class.__name__}: %s", e)
            msg = f"Failed to create entity: {e}"

            raise DatabaseError(msg) from e

    async def get_by_id(
        self,
        entity_id: UUID,
        include_deleted: bool = False,
        relationships: list[str] | None = None,
    ) -> ModelType | None:
        """
        Get entity by ID asynchronously.

        Args:
            entity_id: Entity identifier
            include_deleted: Whether to include soft-deleted entities
            relationships: Related entities to eager load

        Returns:
            Entity if found, None otherwise
        """
        try:
            query = self._build_base_query(include_deleted).filter(self.model_class.id == entity_id)

            # Add relationship loading
            if relationships:
                for rel in relationships:
                    if hasattr(self.model_class, rel):
                        query = query.options(selectinload(getattr(self.model_class, rel)))

            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            self._logger.error("Error getting {self.model_class.__name__} by ID {entity_id}: %s", e)
            msg = f"Failed to retrieve entity: {e}"

            raise DatabaseError(msg) from e

    async def get_by_id_or_raise(
        self,
        entity_id: UUID,
        include_deleted: bool = False,
        relationships: list[str] | None = None,
    ) -> ModelType:
        """
        Get entity by ID or raise exception.

        Args:
            entity_id: Entity identifier
            include_deleted: Whether to include soft-deleted entities
            relationships: Related entities to eager load

        Returns:
            Entity

        Raises:
            EntityNotFoundError: If entity not found
        """
        entity = await self.get_by_id(entity_id, include_deleted, relationships)
        if not entity:
            msg = f"{self.model_class.__name__} not found with ID: {entity_id}"

            raise EntityNotFoundError(msg)
        return entity

    async def get_by_field(
        self,
        field_name: str,
        value: Any,
        include_deleted: bool = False,
        relationships: list[str] | None = None,
    ) -> ModelType | None:
        """
        Get entity by any field asynchronously.

        Args:
            field_name: Field name to search by
            value: Field value
            include_deleted: Whether to include soft-deleted entities
            relationships: Related entities to eager load

        Returns:
            Entity if found, None otherwise
        """
        try:
            if not hasattr(self.model_class, field_name):
                raise ValidationError(
                    f"Field {field_name} not found on model {self.model_class.__name__}"
                )

            field = getattr(self.model_class, field_name)
            query = self._build_base_query(include_deleted).filter(field == value)

            # Add relationship loading
            if relationships:
                for rel in relationships:
                    if hasattr(self.model_class, rel):
                        query = query.options(selectinload(getattr(self.model_class, rel)))

            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            self._logger.error(
                f"Error getting {self.model_class.__name__} by field {field_name}: {e}"
            )
            msg = f"Failed to retrieve entity: {e}"

            raise DatabaseError(msg) from e

    async def update(
        self,
        entity_id: UUID,
        data: dict[str, Any],
        user_id: str | None = None,
    ) -> ModelType:
        """
        Update entity asynchronously.

        Args:
            entity_id: Entity identifier
            data: Update data
            user_id: User performing the operation

        Returns:
            Updated entity

        Raises:
            EntityNotFoundError: If entity not found
            ValidationError: If data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Add audit fields if supported
            if self._supports_audit:
                data["updated_at"] = datetime.now(UTC)
                if user_id:
                    data["updated_by"] = user_id

            # Build update query with conditions
            update_query = (
                update(self.model_class)
                .where(self.model_class.id == entity_id)
                .values(**data)
                .execution_options(synchronize_session="fetch")
            )

            # Add tenant filtering if supported
            if self.tenant_id and self._supports_tenant:
                update_query = update_query.where(self.model_class.tenant_id == self.tenant_id)

            # Add soft delete filtering if supported
            if self._supports_soft_delete:
                update_query = update_query.where(self.model_class.is_deleted is False)

            result = await self.db.execute(update_query)

            if result.rowcount == 0:
                raise EntityNotFoundError(
                    f"{self.model_class.__name__} not found with ID: {entity_id}"
                )

            if self.auto_commit:
                await self.db.commit()

            # Return updated entity
            updated_entity = await self.get_by_id(entity_id)
            if not updated_entity:
                msg = f"Entity not found after update: {entity_id}"

                raise EntityNotFoundError(msg)

            self._logger.info("Updated {self.model_class.__name__} with ID: %s", entity_id)
            return updated_entity

        except EntityNotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            self._logger.error("Error updating {self.model_class.__name__} {entity_id}: %s", e)
            msg = f"Failed to update entity: {e}"

            raise DatabaseError(msg) from e

    async def delete(
        self,
        entity_id: UUID,
        soft_delete: bool = True,
        user_id: str | None = None,
    ) -> bool:
        """
        Delete entity asynchronously.

        Args:
            entity_id: Entity identifier
            soft_delete: Whether to perform soft delete
            user_id: User performing the operation

        Returns:
            True if deleted successfully

        Raises:
            EntityNotFoundError: If entity not found
            DatabaseError: If database operation fails
        """
        try:
            if soft_delete and self._supports_soft_delete:
                # Soft delete using update
                update_data = {
                    "is_deleted": True,
                    "deleted_at": datetime.now(UTC),
                }
                if user_id and self._supports_audit:
                    update_data["updated_by"] = user_id

                update_query = (
                    update(self.model_class)
                    .where(self.model_class.id == entity_id)
                    .where(self.model_class.is_deleted is False)
                    .values(**update_data)
                )

                # Add tenant filtering if supported
                if self.tenant_id and self._supports_tenant:
                    update_query = update_query.where(self.model_class.tenant_id == self.tenant_id)

                result = await self.db.execute(update_query)
            else:
                # Hard delete
                delete_query = delete(self.model_class).where(self.model_class.id == entity_id)

                # Add tenant filtering if supported
                if self.tenant_id and self._supports_tenant:
                    delete_query = delete_query.where(self.model_class.tenant_id == self.tenant_id)

                result = await self.db.execute(delete_query)

            if result.rowcount == 0:
                raise EntityNotFoundError(
                    f"{self.model_class.__name__} not found with ID: {entity_id}"
                )

            if self.auto_commit:
                await self.db.commit()

            self._logger.info("Deleted {self.model_class.__name__} with ID: %s", entity_id)
            return True

        except EntityNotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            self._logger.error("Error deleting {self.model_class.__name__} {entity_id}: %s", e)
            msg = f"Failed to delete entity: {e}"

            raise DatabaseError(msg) from e

    async def list(self, options: QueryOptions) -> list[ModelType]:
        """
        List entities with comprehensive filtering and sorting.

        Args:
            options: Query options including filters, sorts, pagination

        Returns:
            List of entities
        """
        try:
            query = self._build_base_query(options.include_deleted)

            # Apply filters
            query = self._apply_filters(query, options.filters)

            # Apply sorting
            query = self._apply_sorting(query, options.sorts)

            # Add relationship loading
            if options.relationships:
                for rel in options.relationships:
                    if hasattr(self.model_class, rel):
                        query = query.options(selectinload(getattr(self.model_class, rel)))

            # Apply pagination
            if options.pagination:
                offset = (options.pagination.page - 1) * options.pagination.per_page
                query = query.offset(offset).limit(options.pagination.per_page)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            self._logger.error("Error listing {self.model_class.__name__}: %s", e)
            msg = f"Failed to list entities: {e}"

            raise DatabaseError(msg) from e

    async def list_paginated(self, options: QueryOptions) -> PaginationResult[ModelType]:
        """
        List entities with full pagination metadata.

        Args:
            options: Query options with pagination parameters

        Returns:
            Paginated result with metadata
        """
        if not options.pagination:
            msg = "Pagination parameters required for paginated listing"

            raise ValidationError(msg)

        try:
            # Get total count and items concurrently
            total_task = self.count(options.filters, options.include_deleted)
            items_task = self.list(options)

            total = await total_task
            items = await items_task

            # Calculate pagination metadata
            pages = (total + options.pagination.per_page - 1) // options.pagination.per_page
            has_next = options.pagination.page < pages
            has_prev = options.pagination.page > 1

            return PaginationResult(
                items=items,
                total=total,
                page=options.pagination.page,
                per_page=options.pagination.per_page,
                pages=pages,
                has_next=has_next,
                has_prev=has_prev,
            )

        except Exception as e:
            self._logger.error("Error in paginated listing {self.model_class.__name__}: %s", e)
            msg = f"Failed to list entities with pagination: {e}"

            raise DatabaseError(msg) from e

    async def count(
        self,
        filters: list[QueryFilter] | None = None,
        include_deleted: bool = False,
    ) -> int:
        """
        Count entities with filtering.

        Args:
            filters: Filter criteria
            include_deleted: Whether to include soft-deleted entities

        Returns:
            Number of entities
        """
        try:
            query = select(func.count(self.model_class.id))

            # Apply tenant filtering
            if self.tenant_id and self._supports_tenant:
                query = query.where(self.model_class.tenant_id == self.tenant_id)

            # Apply soft delete filtering
            if not include_deleted and self._supports_soft_delete:
                query = query.where(self.model_class.is_deleted is False)

            # Apply filters
            if filters:
                query = self._apply_filters_to_count(query, filters)

            result = await self.db.execute(query)
            return result.scalar() or 0

        except Exception as e:
            self._logger.error("Error counting {self.model_class.__name__}: %s", e)
            msg = f"Failed to count entities: {e}"

            raise DatabaseError(msg) from e

    async def exists(self, entity_id: UUID, include_deleted: bool = False) -> bool:
        """
        Check if entity exists.

        Args:
            entity_id: Entity identifier
            include_deleted: Whether to include soft-deleted entities

        Returns:
            True if entity exists
        """
        try:
            query = select(func.count(self.model_class.id)).where(self.model_class.id == entity_id)

            # Apply tenant filtering
            if self.tenant_id and self._supports_tenant:
                query = query.where(self.model_class.tenant_id == self.tenant_id)

            # Apply soft delete filtering
            if not include_deleted and self._supports_soft_delete:
                query = query.where(self.model_class.is_deleted is False)

            result = await self.db.execute(query)
            return result.scalar() > 0

        except Exception as e:
            self._logger.error("Error checking existence of {self.model_class.__name__}: %s", e)
            msg = f"Failed to check entity existence: {e}"

            raise DatabaseError(msg) from e

    async def bulk_create(
        self,
        data_list: list[dict[str, Any]],
        user_id: str | None = None,
    ) -> list[ModelType]:
        """
        Create multiple entities in bulk.

        Args:
            data_list: List of entity data
            user_id: User performing the operation

        Returns:
            List of created entities
        """
        try:
            entities = []
            for data in data_list:
                # Add tenant_id if model supports multi-tenancy
                if self.tenant_id and self._supports_tenant:
                    data["tenant_id"] = self.tenant_id

                # Add audit fields if supported
                if user_id and self._supports_audit:
                    data["created_by"] = user_id
                    data["updated_by"] = user_id

                entity = self.model_class(**data)
                entities.append(entity)
                self.db.add(entity)

            if self.auto_commit:
                await self.db.commit()
                for entity in entities:
                    await self.db.refresh(entity)
            else:
                await self.db.flush()
                for entity in entities:
                    await self.db.refresh(entity)

            self._logger.info("Bulk created {len(entities)} %s entities", self.model_class.__name__)
            return entities

        except Exception as e:
            await self.db.rollback()
            self._logger.error("Error bulk creating {self.model_class.__name__}: %s", e)
            msg = f"Failed to bulk create entities: {e}"

            raise DatabaseError(msg) from e

    def _build_base_query(self, include_deleted: bool = False):
        """
        Build base query with tenant filtering and soft delete handling.

        Args:
            include_deleted: Whether to include soft-deleted entities

        Returns:
            Base query
        """
        query = select(self.model_class)

        # Apply tenant filtering if supported
        if self.tenant_id and self._supports_tenant:
            query = query.where(self.model_class.tenant_id == self.tenant_id)

        # Filter out soft-deleted entities if supported
        if not include_deleted and self._supports_soft_delete:
            query = query.where(self.model_class.is_deleted is False)

        return query

    def _apply_filters(self, query, filters: list[QueryFilter]):
        """Apply filters to query with comprehensive operator support."""
        for filter_spec in filters:
            if not hasattr(self.model_class, filter_spec.field):
                continue

            column = getattr(self.model_class, filter_spec.field)
            query = self._apply_single_filter(
                query, column, filter_spec.operator, filter_spec.value
            )

        return query

    def _apply_filters_to_count(self, query, filters: list[QueryFilter]):
        """Apply filters to count query."""
        for filter_spec in filters:
            if not hasattr(self.model_class, filter_spec.field):
                continue

            column = getattr(self.model_class, filter_spec.field)
            query = self._apply_single_filter(
                query, column, filter_spec.operator, filter_spec.value
            )

        return query

    def _apply_single_filter(self, query, column, operator: FilterOperator, value: Any):
        """Apply a single filter to query."""
        if operator == FilterOperator.EQ:
            return query.where(column == value)
        elif operator == FilterOperator.NE:
            return query.where(column != value)
        elif operator == FilterOperator.GT:
            return query.where(column > value)
        elif operator == FilterOperator.GTE:
            return query.where(column >= value)
        elif operator == FilterOperator.LT:
            return query.where(column < value)
        elif operator == FilterOperator.LTE:
            return query.where(column <= value)
        elif operator == FilterOperator.IN:
            return query.where(column.in_(value))
        elif operator == FilterOperator.NOT_IN:
            return query.where(~column.in_(value))
        elif operator == FilterOperator.LIKE:
            return query.where(column.like(f"%{value}%"))
        elif operator == FilterOperator.ILIKE:
            return query.where(column.ilike(f"%{value}%"))
        elif operator == FilterOperator.IS_NULL:
            if value:
                return query.where(column.is_(None))
            else:
                return query.where(column.isnot(None))
        elif operator == FilterOperator.IS_NOT_NULL:
            if value:
                return query.where(column.isnot(None))
            else:
                return query.where(column.is_(None))
        else:
            return query

    def _apply_sorting(self, query, sorts: list[SortField]):
        """Apply sorting to query."""
        for sort_spec in sorts:
            if not hasattr(self.model_class, sort_spec.field):
                continue

            column = getattr(self.model_class, sort_spec.field)
            if sort_spec.order == SortOrder.DESC:
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())

        # Default sort by ID if no sorting specified
        if not sorts:
            query = query.order_by(self.model_class.id.desc())

        return query


class AsyncTenantRepository(AsyncRepository[ModelType]):
    """
    Async repository for tenant-aware entities.

    Extends AsyncRepository with additional tenant-specific functionality
    and enforces tenant_id requirement.
    """

    def __init__(
        self,
        db: AsyncSession,
        model_class: type[ModelType],
        tenant_id: str,
        auto_commit: bool = True,
    ):
        """
        Initialize async tenant repository.

        Args:
            db: Async database session
            model_class: SQLAlchemy model class
            tenant_id: Required tenant identifier
            auto_commit: Whether to auto-commit transactions

        Raises:
            ValidationError: If tenant_id is not provided or model doesn't support tenancy
        """
        if not tenant_id:
            msg = "tenant_id is required for tenant repositories"

            raise ValidationError(msg)

        if not issubclass(model_class, TenantMixin):
            msg = f"Model {model_class.__name__} must implement TenantMixin"

            raise ValidationError(msg)

        super().__init__(db, model_class, tenant_id, auto_commit)

    async def get_tenant_stats(self) -> dict[str, Any]:
        """
        Get statistics for current tenant.

        Returns:
            Statistics dictionary with entity counts and metadata
        """
        try:
            # Base count query
            base_query = select(func.count(self.model_class.id)).where(
                self.model_class.tenant_id == self.tenant_id
            )

            # Apply soft delete filtering
            if self._supports_soft_delete:
                total_query = base_query.where(self.model_class.is_deleted is False)
            else:
                total_query = base_query

            total_result = await self.db.execute(total_query)
            total_count = total_result.scalar() or 0

            stats = {
                "total_entities": total_count,
                "tenant_id": self.tenant_id,
                "entity_type": self.model_class.__name__,
            }

            # Add timestamp-based stats if supported
            if self._supports_audit:
                # Entities created today
                today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                today_query = total_query.where(self.model_class.created_at >= today_start)
                today_result = await self.db.execute(today_query)
                stats["created_today"] = today_result.scalar() or 0

                # Entities created this month
                month_start = today_start.replace(day=1)
                month_query = total_query.where(self.model_class.created_at >= month_start)
                month_result = await self.db.execute(month_query)
                stats["created_this_month"] = month_result.scalar() or 0

            # Add soft delete stats if supported
            if self._supports_soft_delete:
                deleted_query = base_query.where(self.model_class.is_deleted is True)
                deleted_result = await self.db.execute(deleted_query)
                stats["deleted_entities"] = deleted_result.scalar() or 0

            return stats

        except Exception as e:
            self._logger.error("Error getting tenant stats for {self.model_class.__name__}: %s", e)
            msg = f"Failed to get tenant statistics: {e}"

            raise DatabaseError(msg) from e

    def switch_tenant(self, new_tenant_id: str) -> AsyncTenantRepository[ModelType]:
        """
        Create a new repository instance for a different tenant.

        Args:
            new_tenant_id: New tenant identifier

        Returns:
            New repository instance for the specified tenant
        """
        return AsyncTenantRepository(self.db, self.model_class, new_tenant_id, self.auto_commit)
