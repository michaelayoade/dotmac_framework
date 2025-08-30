"""
Synchronous repository implementations.

Unified repository pattern combining the best features from both
ISP Framework and Management Platform implementations.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, Union
from uuid import UUID

from sqlalchemy import and_, asc, delete, desc, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Query, Session, selectinload

from ..types import (
    AuditMixin,
    CursorPaginationParams,
    CursorPaginationResult,
    DatabaseError,
    DuplicateEntityError,
    EntityNotFoundError,
    FilterOperator,
    FilterValue,
    ModelType,
    PaginationParams,
    PaginationResult,
    QueryFilter,
    QueryOptions,
    RepositoryProtocol,
    SoftDeleteMixin,
    SortField,
    SortOrder,
    TenantMixin,
    TransactionError,
    ValidationError,
    dotmac_shared.api.exception_handlers,
    from,
    import,
    standard_exception_handler,
)

logger = logging.getLogger(__name__)


class BaseRepository(Generic[ModelType], RepositoryProtocol[ModelType]):
    """
    Unified synchronous repository providing comprehensive CRUD operations.

    Combines features from both existing implementations:
    - ISP Framework's advanced filtering and tenant support
    - Management Platform's structured query building

    Features:
    - Generic CRUD operations with type safety
    - Advanced filtering with multiple operators
    - Flexible sorting and pagination
    - Tenant isolation support
    - Soft delete support
    - Audit trail support
    - Bulk operations
    - Query optimization
    - Consistent error handling
    """

    def __init__(
        self,
        db: Session,
        model_class: Type[ModelType],
        tenant_id: Optional[str] = None,
        auto_commit: bool = True,
    ):
        """
        Initialize repository.

        Args:
            db: Database session
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

    def create(self, data: Dict[str, Any], user_id: Optional[str] = None) -> ModelType:
        """
        Create a new entity.

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
                self.db.commit()
                self.db.refresh(entity)

            self._logger.info(f"Created {self.model_class.__name__} with ID: {entity.id}")
            return entity

        except IntegrityError as e:
            self.db.rollback()
            self._logger.error(f"Integrity error creating {self.model_class.__name__}: {e}")
            raise DuplicateEntityError(f"Entity already exists: {e.orig}")
        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to create entity: {e}")

    def get_by_id(
        self,
        entity_id: UUID,
        include_deleted: bool = False,
        relationships: Optional[List[str]] = None,
    ) -> Optional[ModelType]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity identifier
            include_deleted: Whether to include soft-deleted entities
            relationships: Related entities to eager load

        Returns:
            Entity if found, None otherwise
        """
        try:
            query = self._build_base_query(include_deleted).filter(
                self.model_class.id == entity_id
            )

            # Add relationship loading
            if relationships:
                for rel in relationships:
                    if hasattr(self.model_class, rel):
                        query = query.options(selectinload(getattr(self.model_class, rel)))

            return query.first()

        except Exception as e:
            self._logger.error(f"Error getting {self.model_class.__name__} by ID {entity_id}: {e}")
            raise DatabaseError(f"Failed to retrieve entity: {e}")

    def get_by_id_or_raise(
        self,
        entity_id: UUID,
        include_deleted: bool = False,
        relationships: Optional[List[str]] = None,
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
        entity = self.get_by_id(entity_id, include_deleted, relationships)
        if not entity:
            raise EntityNotFoundError(f"{self.model_class.__name__} not found with ID: {entity_id}")
        return entity

    def get_by_field(
        self,
        field_name: str,
        value: Any,
        include_deleted: bool = False,
        relationships: Optional[List[str]] = None,
    ) -> Optional[ModelType]:
        """
        Get entity by any field.

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
                raise ValidationError(f"Field {field_name} not found on model {self.model_class.__name__}")

            field = getattr(self.model_class, field_name)
            query = self._build_base_query(include_deleted).filter(field == value)

            # Add relationship loading
            if relationships:
                for rel in relationships:
                    if hasattr(self.model_class, rel):
                        query = query.options(selectinload(getattr(self.model_class, rel)))

            return query.first()

        except Exception as e:
            self._logger.error(f"Error getting {self.model_class.__name__} by field {field_name}: {e}")
            raise DatabaseError(f"Failed to retrieve entity: {e}")

    def update(
        self,
        entity_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> ModelType:
        """
        Update entity.

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
            entity = self.get_by_id_or_raise(entity_id)

            # Update entity attributes
            for key, value in data.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            # Update audit fields if supported
            if self._supports_audit:
                entity.updated_at = datetime.now(timezone.utc)
                if user_id:
                    entity.updated_by = user_id

            if self.auto_commit:
                self.db.commit()
                self.db.refresh(entity)

            self._logger.info(f"Updated {self.model_class.__name__} with ID: {entity_id}")
            return entity

        except EntityNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Error updating {self.model_class.__name__} {entity_id}: {e}")
            raise DatabaseError(f"Failed to update entity: {e}")

    def delete(
        self,
        entity_id: UUID,
        soft_delete: bool = True,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Delete entity.

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
            entity = self.get_by_id_or_raise(entity_id)

            if soft_delete and self._supports_soft_delete:
                # Soft delete
                entity.is_deleted = True
                if hasattr(entity, "deleted_at"):
                    entity.deleted_at = datetime.now(timezone.utc)
                if user_id and self._supports_audit:
                    entity.updated_by = user_id
            else:
                # Hard delete
                self.db.delete(entity)

            if self.auto_commit:
                self.db.commit()

            self._logger.info(f"Deleted {self.model_class.__name__} with ID: {entity_id}")
            return True

        except EntityNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Error deleting {self.model_class.__name__} {entity_id}: {e}")
            raise DatabaseError(f"Failed to delete entity: {e}")

    def list(self, options: QueryOptions) -> List[ModelType]:
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

            return query.all()

        except Exception as e:
            self._logger.error(f"Error listing {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to list entities: {e}")

    def list_paginated(self, options: QueryOptions) -> PaginationResult[ModelType]:
        """
        List entities with full pagination metadata.

        Args:
            options: Query options with pagination parameters

        Returns:
            Paginated result with metadata
        """
        if not options.pagination:
            raise ValidationError("Pagination parameters required for paginated listing")

        try:
            # Get total count
            total = self.count(options.filters, options.include_deleted)

            # Calculate pagination metadata
            pages = (total + options.pagination.per_page - 1) // options.pagination.per_page
            has_next = options.pagination.page < pages
            has_prev = options.pagination.page > 1

            # Get items
            items = self.list(options)

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
            self._logger.error(f"Error in paginated listing {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to list entities with pagination: {e}")

    def count(
        self,
        filters: Optional[List[QueryFilter]] = None,
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
            query = self.db.query(func.count(self.model_class.id))

            # Apply tenant filtering
            if self.tenant_id and self._supports_tenant:
                query = query.filter(self.model_class.tenant_id == self.tenant_id)

            # Apply soft delete filtering
            if not include_deleted and self._supports_soft_delete:
                query = query.filter(self.model_class.is_deleted == False)

            # Apply filters
            if filters:
                query = self._apply_filters_to_count(query, filters)

            return query.scalar() or 0

        except Exception as e:
            self._logger.error(f"Error counting {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to count entities: {e}")

    def exists(self, entity_id: UUID, include_deleted: bool = False) -> bool:
        """
        Check if entity exists.

        Args:
            entity_id: Entity identifier
            include_deleted: Whether to include soft-deleted entities

        Returns:
            True if entity exists
        """
        try:
            query = self.db.query(func.count(self.model_class.id)).filter(
                self.model_class.id == entity_id
            )

            # Apply tenant filtering
            if self.tenant_id and self._supports_tenant:
                query = query.filter(self.model_class.tenant_id == self.tenant_id)

            # Apply soft delete filtering
            if not include_deleted and self._supports_soft_delete:
                query = query.filter(self.model_class.is_deleted == False)

            return query.scalar() > 0

        except Exception as e:
            self._logger.error(f"Error checking existence of {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to check entity existence: {e}")

    def bulk_create(
        self,
        data_list: List[Dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> List[ModelType]:
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
                self.db.commit()
                for entity in entities:
                    self.db.refresh(entity)

            self._logger.info(f"Bulk created {len(entities)} {self.model_class.__name__} entities")
            return entities

        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Error bulk creating {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to bulk create entities: {e}")

    def _build_base_query(self, include_deleted: bool = False) -> Query:
        """
        Build base query with tenant filtering and soft delete handling.

        Args:
            include_deleted: Whether to include soft-deleted entities

        Returns:
            Base query
        """
        query = self.db.query(self.model_class)

        # Apply tenant filtering if supported
        if self.tenant_id and self._supports_tenant:
            query = query.filter(self.model_class.tenant_id == self.tenant_id)

        # Filter out soft-deleted entities if supported
        if not include_deleted and self._supports_soft_delete:
            query = query.filter(self.model_class.is_deleted == False)

        return query

    def _apply_filters(self, query: Query, filters: List[QueryFilter]) -> Query:
        """
        Apply filters to query with comprehensive operator support.

        Args:
            query: Base query
            filters: Filter specifications

        Returns:
            Filtered query
        """
        for filter_spec in filters:
            if not hasattr(self.model_class, filter_spec.field):
                continue

            column = getattr(self.model_class, filter_spec.field)
            query = self._apply_single_filter(query, column, filter_spec.operator, filter_spec.value)

        return query

    def _apply_filters_to_count(self, query, filters: List[QueryFilter]):
        """Apply filters to count query."""
        for filter_spec in filters:
            if not hasattr(self.model_class, filter_spec.field):
                continue

            column = getattr(self.model_class, filter_spec.field)
            query = self._apply_single_filter_to_count(query, column, filter_spec.operator, filter_spec.value)

        return query

    def _apply_single_filter(self, query: Query, column, operator: FilterOperator, value: Any) -> Query:
        """Apply a single filter to query."""
        if operator == FilterOperator.EQ:
            return query.filter(column == value)
        elif operator == FilterOperator.NE:
            return query.filter(column != value)
        elif operator == FilterOperator.GT:
            return query.filter(column > value)
        elif operator == FilterOperator.GTE:
            return query.filter(column >= value)
        elif operator == FilterOperator.LT:
            return query.filter(column < value)
        elif operator == FilterOperator.LTE:
            return query.filter(column <= value)
        elif operator == FilterOperator.IN:
            return query.filter(column.in_(value))
        elif operator == FilterOperator.NOT_IN:
            return query.filter(~column.in_(value))
        elif operator == FilterOperator.LIKE:
            return query.filter(column.like(f"%{value}%"))
        elif operator == FilterOperator.ILIKE:
            return query.filter(column.ilike(f"%{value}%"))
        elif operator == FilterOperator.IS_NULL:
            if value:
                return query.filter(column.is_(None))
            else:
                return query.filter(column.isnot(None))
        elif operator == FilterOperator.IS_NOT_NULL:
            if value:
                return query.filter(column.isnot(None))
            else:
                return query.filter(column.is_(None))
        else:
            return query

    def _apply_single_filter_to_count(self, query, column, operator: FilterOperator, value: Any):
        """Apply a single filter to count query."""
        # Same logic as _apply_single_filter but for count queries
        return self._apply_single_filter(query, column, operator, value)

    def _apply_sorting(self, query: Query, sorts: List[SortField]) -> Query:
        """
        Apply sorting to query.

        Args:
            query: Base query
            sorts: Sort specifications

        Returns:
            Sorted query
        """
        for sort_spec in sorts:
            if not hasattr(self.model_class, sort_spec.field):
                continue

            column = getattr(self.model_class, sort_spec.field)
            if sort_spec.order == SortOrder.DESC:
                query = query.order_by(desc(column))
            else:
                query = query.order_by(asc(column))

        # Default sort by ID if no sorting specified
        if not sorts:
            query = query.order_by(desc(self.model_class.id))

        return query


class BaseTenantRepository(BaseRepository[ModelType]):
    """
    Base repository for tenant-aware entities.

    Extends BaseRepository with additional tenant-specific functionality
    and enforces tenant_id requirement.
    """

    def __init__(self, db: Session, model_class: Type[ModelType], tenant_id: str, auto_commit: bool = True):
        """
        Initialize tenant repository.

        Args:
            db: Database session
            model_class: SQLAlchemy model class
            tenant_id: Required tenant identifier
            auto_commit: Whether to auto-commit transactions

        Raises:
            ValidationError: If tenant_id is not provided or model doesn't support tenancy
        """
        if not tenant_id:
            raise ValidationError("tenant_id is required for tenant repositories")

        if not issubclass(model_class, TenantMixin):
            raise ValidationError(f"Model {model_class.__name__} must implement TenantMixin")

        super().__init__(db, model_class, tenant_id, auto_commit)

    def get_tenant_stats(self) -> Dict[str, Any]:
        """
        Get statistics for current tenant.

        Returns:
            Statistics dictionary with entity counts and metadata
        """
        try:
            query = self._build_base_query()

            total_count = query.count()

            stats = {
                "total_entities": total_count,
                "tenant_id": self.tenant_id,
                "entity_type": self.model_class.__name__,
            }

            # Add timestamp-based stats if supported
            if self._supports_audit:
                # Entities created today
                today_start = datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                today_count = query.filter(self.model_class.created_at >= today_start).count()
                stats["created_today"] = today_count

                # Entities created this month
                month_start = today_start.replace(day=1)
                month_count = query.filter(self.model_class.created_at >= month_start).count()
                stats["created_this_month"] = month_count

            # Add soft delete stats if supported
            if self._supports_soft_delete:
                deleted_count = self.db.query(func.count(self.model_class.id)).filter(
                    and_(
                        self.model_class.tenant_id == self.tenant_id,
                        self.model_class.is_deleted == True,
                    )
                ).scalar()
                stats["deleted_entities"] = deleted_count

            return stats

        except Exception as e:
            self._logger.error(f"Error getting tenant stats for {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to get tenant statistics: {e}")

    def switch_tenant(self, new_tenant_id: str) -> "BaseTenantRepository[ModelType]":
        """
        Create a new repository instance for a different tenant.

        Args:
            new_tenant_id: New tenant identifier

        Returns:
            New repository instance for the specified tenant
        """
        return BaseTenantRepository(self.db, self.model_class, new_tenant_id, self.auto_commit)
