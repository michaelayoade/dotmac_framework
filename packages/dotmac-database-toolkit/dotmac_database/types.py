"""
Type definitions and interfaces for the database toolkit.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Protocol, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

# Type variables
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

# Database session types
DatabaseSession = Union[Session, AsyncSession]


class SortOrder(str, Enum):
    """Sort order enumeration."""

    ASC = "asc"
    DESC = "desc"


class FilterOperator(str, Enum):
    """Filter operator enumeration."""

    EQ = "eq"  # Equal
    NE = "ne"  # Not equal
    GT = "gt"  # Greater than
    GTE = "gte"  # Greater than or equal
    LT = "lt"  # Less than
    LTE = "lte"  # Less than or equal
    IN = "in"  # In list
    NOT_IN = "not_in"  # Not in list
    LIKE = "like"  # SQL LIKE
    ILIKE = "ilike"  # Case-insensitive LIKE
    IS_NULL = "is_null"  # IS NULL
    IS_NOT_NULL = "is_not_null"  # IS NOT NULL
    CONTAINS = "contains"  # Array contains
    CONTAINED_BY = "contained_by"  # Array contained by


class FilterValue(BaseModel):
    """Filter value with operator."""

    operator: FilterOperator
    value: Any

    class Config:
        use_enum_values = True


class QueryFilter(BaseModel):
    """Query filter specification."""

    field: str
    operator: FilterOperator = FilterOperator.EQ
    value: Any

    class Config:
        use_enum_values = True


class SortField(BaseModel):
    """Sort field specification."""

    field: str
    order: SortOrder = SortOrder.ASC

    class Config:
        use_enum_values = True


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    per_page: int = Field(20, ge=1, le=1000, description="Items per page")


class CursorPaginationParams(BaseModel):
    """Cursor-based pagination parameters."""

    limit: int = Field(20, ge=1, le=1000, description="Maximum items to return")
    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    cursor_field: str = Field("id", description="Field to use for cursor")
    ascending: bool = Field(True, description="Sort order")


class PaginationResult(BaseModel, Generic[ModelType]):
    """Paginated result container."""

    items: List[ModelType]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool


class CursorPaginationResult(BaseModel, Generic[ModelType]):
    """Cursor-based pagination result."""

    items: List[ModelType]
    next_cursor: Optional[str]
    has_next: bool


class QueryOptions(BaseModel):
    """Query execution options."""

    filters: List[QueryFilter] = Field(default_factory=list)
    sorts: List[SortField] = Field(default_factory=list)
    pagination: Optional[PaginationParams] = None
    cursor_pagination: Optional[CursorPaginationParams] = None
    include_deleted: bool = False
    relationships: List[str] = Field(default_factory=list)


class TenantMixin(Protocol):
    """Protocol for tenant-aware models."""

    tenant_id: Column[str]


class SoftDeleteMixin(Protocol):
    """Protocol for soft-deletable models."""

    is_deleted: Column[bool]
    deleted_at: Optional[Column[datetime]]


class AuditMixin(Protocol):
    """Protocol for auditable models."""

    created_at: Column[datetime]
    updated_at: Column[datetime]
    created_by: Optional[Column[str]]
    updated_by: Optional[Column[str]]


class DatabaseError(Exception):
    """Base database error."""

    pass


class EntityNotFoundError(DatabaseError):
    """Entity not found error."""

    pass


class DuplicateEntityError(DatabaseError):
    """Duplicate entity error."""

    pass


class ValidationError(DatabaseError):
    """Validation error."""

    pass


class TransactionError(DatabaseError):
    """Transaction error."""

    pass


class RepositoryProtocol(Protocol, Generic[ModelType]):
    """Repository protocol defining the interface."""

    @abstractmethod
    def create(self, data: Dict[str, Any], **kwargs) -> ModelType:
        """Create a new entity."""
        pass

    @abstractmethod
    def get_by_id(self, entity_id: UUID, **kwargs) -> Optional[ModelType]:
        """Get entity by ID."""
        pass

    @abstractmethod
    def update(self, entity_id: UUID, data: Dict[str, Any], **kwargs) -> ModelType:
        """Update entity."""
        pass

    @abstractmethod
    def delete(self, entity_id: UUID, **kwargs) -> bool:
        """Delete entity."""
        pass

    @abstractmethod
    def list(self, options: QueryOptions, **kwargs) -> List[ModelType]:
        """List entities with options."""
        pass

    @abstractmethod
    def count(self, filters: List[QueryFilter], **kwargs) -> int:
        """Count entities."""
        pass


class AsyncRepositoryProtocol(Protocol, Generic[ModelType]):
    """Async repository protocol."""

    @abstractmethod
    async def create(self, data: Dict[str, Any], **kwargs) -> ModelType:
        """Create a new entity."""
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: UUID, **kwargs) -> Optional[ModelType]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def update(
        self, entity_id: UUID, data: Dict[str, Any], **kwargs
    ) -> ModelType:
        """Update entity."""
        pass

    @abstractmethod
    async def delete(self, entity_id: UUID, **kwargs) -> bool:
        """Delete entity."""
        pass

    @abstractmethod
    async def list(self, options: QueryOptions, **kwargs) -> List[ModelType]:
        """List entities with options."""
        pass

    @abstractmethod
    async def count(self, filters: List[QueryFilter], **kwargs) -> int:
        """Count entities."""
        pass
