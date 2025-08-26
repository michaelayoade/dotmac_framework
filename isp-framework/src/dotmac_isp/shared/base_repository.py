"""
Base Repository Classes

ARCHITECTURE IMPROVEMENT: Provides reusable CRUD operations and patterns
to eliminate code duplication across modules. Implements Repository pattern
with consistent error handling and tenant isolation.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session, Query
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_, or_, desc, asc, func, text

from .exceptions import (
    EntityNotFoundError,
    DuplicateEntityError,
    ValidationError,
    DatabaseError
)
from datetime import datetime, timezone
from .models import Base, TenantMixin

logger = logging.getLogger(__name__)

# Generic type for model classes
ModelType = TypeVar('ModelType', bound=Base)


class BaseRepository(Generic[ModelType], ABC):
    """
    Base repository providing common CRUD operations.
    
    PATTERN: Repository Pattern with Generic Types
    - Encapsulates database access logic
    - Provides consistent error handling
    - Supports tenant isolation
    - Reduces code duplication across modules
    
    Features:
    - Generic CRUD operations
    - Query building with filters, sorting, pagination
    - Tenant-aware operations
    - Bulk operations
    - Consistent error handling
    - Audit trail support
    """
    
    def __init__(self, db: Session, model_class: Type[ModelType], tenant_id: Optional[str] = None):
        """
        Initialize repository.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            tenant_id: Tenant identifier for multi-tenancy
        """
        self.db = db
        self.model_class = model_class
        self.tenant_id = tenant_id
        self._logger = logging.getLogger(f"{__name__}.{model_class.__name__}")
    
    def create(self, data: Dict[str, Any], commit: bool = True) -> ModelType:
        """
        Create a new entity.
        
        Args:
            data: Entity data
            commit: Whether to commit transaction
            
        Returns:
            Created entity
            
        Raises:
            DuplicateEntityError: If entity already exists
            ValidationError: If data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Add tenant_id if model supports multi-tenancy
            if self.tenant_id and issubclass(self.model_class, TenantMixin):
                data['tenant_id'] = self.tenant_id
            
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
            raise DuplicateEntityError(f"Entity already exists: {e.orig}")
        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to create entity: {e}")
    
    def get_by_id(self, entity_id: UUID) -> Optional[ModelType]:
        """
        Get entity by ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Entity if found, None otherwise
        """
        try:
            query = self._build_base_query().filter(self.model_class.id == entity_id)
            return query.first()
        except Exception as e:
            self._logger.error(f"Error getting {self.model_class.__name__} by ID {entity_id}: {e}")
            raise DatabaseError(f"Failed to retrieve entity: {e}")
    
    def get_by_id_or_raise(self, entity_id: UUID) -> ModelType:
        """
        Get entity by ID or raise exception.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Entity
            
        Raises:
            EntityNotFoundError: If entity not found
        """
        entity = self.get_by_id(entity_id)
        if not entity:
            raise EntityNotFoundError(f"{self.model_class.__name__} not found with ID: {entity_id}")
        return entity
    
    def update(self, entity_id: UUID, data: Dict[str, Any], commit: bool = True) -> ModelType:
        """
        Update entity.
        
        Args:
            entity_id: Entity identifier
            data: Update data
            commit: Whether to commit transaction
            
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
            
            # Update timestamp if supported
            if hasattr(entity, 'updated_at'):
                entity.updated_at = datetime.now(timezone.utc)
            
            if commit:
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
    
    def delete(self, entity_id: UUID, commit: bool = True) -> bool:
        """
        Delete entity.
        
        Args:
            entity_id: Entity identifier
            commit: Whether to commit transaction
            
        Returns:
            True if deleted successfully
            
        Raises:
            EntityNotFoundError: If entity not found
            DatabaseError: If database operation fails
        """
        try:
            entity = self.get_by_id_or_raise(entity_id)
            
            # Soft delete if supported
            if hasattr(entity, 'is_deleted'):
                entity.is_deleted = True
                if hasattr(entity, 'deleted_at'):
                    entity.deleted_at = datetime.now(timezone.utc)
            else:
                # Hard delete
                self.db.delete(entity)
            
            if commit:
                self.db.commit()
            
            self._logger.info(f"Deleted {self.model_class.__name__} with ID: {entity_id}")
            return True
            
        except EntityNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Error deleting {self.model_class.__name__} {entity_id}: {e}")
            raise DatabaseError(f"Failed to delete entity: {e}")
    
    def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = 'asc',
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[ModelType]:
        """
        List entities with filtering, sorting, and pagination.
        
        Args:
            filters: Filter criteria
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of entities
        """
        try:
            query = self._build_base_query()
            
            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)
            
            # Apply sorting
            if sort_by:
                if hasattr(self.model_class, sort_by):
                    sort_column = getattr(self.model_class, sort_by)
                    if sort_order.lower() == 'desc':
                        query = query.order_by(desc(sort_column))
                    else:
                        query = query.order_by(asc(sort_column))
            
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            return query.all()
            
        except Exception as e:
            self._logger.error(f"Error listing {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to list entities: {e}")
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities with optional filtering.
        
        Args:
            filters: Filter criteria
            
        Returns:
            Number of entities
        """
        try:
            query = self._build_base_query()
            
            if filters:
                query = self._apply_filters(query, filters)
            
            return query.count()
            
        except Exception as e:
            self._logger.error(f"Error counting {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to count entities: {e}")
    
    def bulk_create(self, data_list: List[Dict[str, Any]], commit: bool = True) -> List[ModelType]:
        """
        Create multiple entities in bulk.
        
        Args:
            data_list: List of entity data
            commit: Whether to commit transaction
            
        Returns:
            List of created entities
        """
        try:
            entities = []
            for data in data_list:
                # Add tenant_id if model supports multi-tenancy
                if self.tenant_id and issubclass(self.model_class, TenantMixin):
                    data['tenant_id'] = self.tenant_id
                
                entity = self.model_class(**data)
                entities.append(entity)
                self.db.add(entity)
            
            if commit:
                self.db.commit()
                for entity in entities:
                    self.db.refresh(entity)
            
            self._logger.info(f"Bulk created {len(entities)} {self.model_class.__name__} entities")
            return entities
            
        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Error bulk creating {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to bulk create entities: {e}")
    
    def bulk_update(self, updates: List[Dict[str, Any]], commit: bool = True) -> int:
        """
        Update multiple entities in bulk.
        
        Args:
            updates: List of update data with 'id' field
            commit: Whether to commit transaction
            
        Returns:
            Number of updated entities
        """
        try:
            updated_count = 0
            
            for update_data in updates:
                entity_id = update_data.pop('id')
                entity = self.get_by_id(entity_id)
                
                if entity:
                    for key, value in update_data.items():
                        if hasattr(entity, key):
                            setattr(entity, key, value)
                    
                    if hasattr(entity, 'updated_at'):
                        entity.updated_at = datetime.now(timezone.utc)
                    
                    updated_count += 1
            
            if commit:
                self.db.commit()
            
            self._logger.info(f"Bulk updated {updated_count} {self.model_class.__name__} entities")
            return updated_count
            
        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Error bulk updating {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to bulk update entities: {e}")
    
    def exists(self, filters: Dict[str, Any]) -> bool:
        """
        Check if entity exists with given filters.
        
        Args:
            filters: Filter criteria
            
        Returns:
            True if entity exists
        """
        try:
            query = self._build_base_query()
            query = self._apply_filters(query, filters)
            return query.first() is not None
            
        except Exception as e:
            self._logger.error(f"Error checking existence of {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to check entity existence: {e}")
    
    def _build_base_query(self) -> Query:
        """
        Build base query with tenant filtering.
        
        Returns:
            Base query
        """
        query = self.db.query(self.model_class)
        
        # Apply tenant filtering if supported
        if self.tenant_id and issubclass(self.model_class, TenantMixin):
            query = query.filter(self.model_class.tenant_id == self.tenant_id)
        
        # Filter out soft-deleted entities if supported
        if hasattr(self.model_class, 'is_deleted'):
            query = query.filter(self.model_class.is_deleted == False)
        
        return query
    
    def _apply_filters(self, query: Query, filters: Dict[str, Any]) -> Query:
        """
        Apply filters to query.
        
        Args:
            query: Base query
            filters: Filter criteria
            
        Returns:
            Filtered query
        """
        for key, value in filters.items():
            if not hasattr(self.model_class, key):
                continue
            
            column = getattr(self.model_class, key)
            
            # Handle different filter types
            if isinstance(value, dict):
                # Advanced filters (e.g., {'gt': 10}, {'in': [1,2,3]})
                for operator, filter_value in value.items():
                    if operator == 'gt':
                        query = query.filter(column > filter_value)
                    elif operator == 'gte':
                        query = query.filter(column >= filter_value)
                    elif operator == 'lt':
                        query = query.filter(column < filter_value)
                    elif operator == 'lte':
                        query = query.filter(column <= filter_value)
                    elif operator == 'in':
                        query = query.filter(column.in_(filter_value))
                    elif operator == 'not_in':
                        query = query.filter(~column.in_(filter_value))
                    elif operator == 'like':
                        query = query.filter(column.like(f"%{filter_value}%"))
                    elif operator == 'ilike':
                        query = query.filter(column.ilike(f"%{filter_value}%"))
                    elif operator == 'is_null':
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


class BaseTenantRepository(BaseRepository[ModelType]):
    """
    Base repository for tenant-aware entities.
    
    Extends BaseRepository with additional tenant-specific functionality.
    """
    
    def __init__(self, db: Session, model_class: Type[ModelType], tenant_id: str):
        """
        Initialize tenant repository.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            tenant_id: Required tenant identifier
        """
        if not tenant_id:
            raise ValidationError("tenant_id is required for tenant repositories")
        
        if not issubclass(model_class, TenantMixin):
            raise ValidationError(f"Model {model_class.__name__} must inherit from TenantMixin")
        
        super().__init__(db, model_class, tenant_id)
    
    def get_tenant_stats(self) -> Dict[str, Any]:
        """
        Get statistics for current tenant.
        
        Returns:
            Statistics dictionary
        """
        try:
            query = self._build_base_query()
            
            total_count = query.count()
            
            stats = {
                'total_entities': total_count,
                'tenant_id': self.tenant_id,
                'entity_type': self.model_class.__name__
            }
            
            # Add timestamp-based stats if supported
            if hasattr(self.model_class, 'created_at'):
                # Entities created today
                today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                today_count = query.filter(self.model_class.created_at >= today_start).count()
                stats['created_today'] = today_count
                
                # Entities created this month
                month_start = today_start.replace(day=1)
                month_count = query.filter(self.model_class.created_at >= month_start).count()
                stats['created_this_month'] = month_count
            
            return stats
            
        except Exception as e:
            self._logger.error(f"Error getting tenant stats for {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to get tenant statistics: {e}")


def create_repository(
    db: Session,
    model_class: Type[ModelType], 
    tenant_id: Optional[str] = None
) -> BaseRepository[ModelType]:
    """
    Factory function to create appropriate repository.
    
    Args:
        db: Database session
        model_class: SQLAlchemy model class
        tenant_id: Tenant identifier
        
    Returns:
        Repository instance
    """
    if issubclass(model_class, TenantMixin) and tenant_id:
        return BaseTenantRepository(db, model_class, tenant_id)
    else:
        return BaseRepository(db, model_class, tenant_id)