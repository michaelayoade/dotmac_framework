"""
Type definitions and interfaces for the database toolkit.
"""

from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from uuid import UUID

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

# Database session types
DatabaseSession = Session | AsyncSession


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

    model_config = ConfigDict(use_enum_values=True)


class QueryFilter(BaseModel):
    """Query filter specification."""

    field: str
    operator: FilterOperator = FilterOperator.EQ
    value: Any

    model_config = ConfigDict(use_enum_values=True)


class SortField(BaseModel):
    """Sort field specification."""

    field: str
    order: SortOrder = SortOrder.ASC

    model_config = ConfigDict(use_enum_values=True)


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    per_page: int = Field(20, ge=1, le=1000, description="Items per page")


class CursorPaginationParams(BaseModel):
    """Cursor-based pagination parameters."""

    limit: int = Field(20, ge=1, le=1000, description="Maximum items to return")
    cursor: str | None = Field(None, description="Cursor for pagination")
    cursor_field: str = Field("id", description="Field to use for cursor")
    ascending: bool = Field(True, description="Sort order")


class PaginationResult(BaseModel, Generic[ModelType]):
    """Paginated result container."""

    items: list[ModelType]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool


class CursorPaginationResult(BaseModel, Generic[ModelType]):
    """Cursor-based pagination result."""

    items: list[ModelType]
    next_cursor: str | None
    has_next: bool


class QueryOptions(BaseModel):
    """Query execution options."""

    filters: list[QueryFilter] = Field(default_factory=list)
    sorts: list[SortField] = Field(default_factory=list)
    pagination: PaginationParams | None = None
    cursor_pagination: CursorPaginationParams | None = None
    include_deleted: bool = False
    relationships: list[str] = Field(default_factory=list)


class DatabaseError(Exception):
    """Base database error."""


class EntityNotFoundError(DatabaseError):
    """Entity not found error."""


class DuplicateEntityError(DatabaseError):
    """Duplicate entity error."""


class ValidationError(DatabaseError):
    """Validation error."""


class TransactionError(DatabaseError):
    """Transaction error."""


class RepositoryProtocol(Protocol, Generic[ModelType]):
    """Repository protocol defining the interface."""

    @abstractmethod
    def create(self, data: dict[str, Any], **kwargs) -> ModelType:
        """Create a new entity."""

    @abstractmethod
    def get_by_id(self, entity_id: UUID, **kwargs) -> ModelType | None:
        """Get entity by ID."""

    @abstractmethod
    def update(self, entity_id: UUID, data: dict[str, Any], **kwargs) -> ModelType:
        """Update entity."""

    @abstractmethod
    def delete(self, entity_id: UUID, **kwargs) -> bool:
        """Delete entity."""

    @abstractmethod
    def list(self, options: QueryOptions, **kwargs) -> list[ModelType]:
        """List entities with options."""

    @abstractmethod
    def count(self, filters: list[QueryFilter], **kwargs) -> int:
        """Count entities."""


class AsyncRepositoryProtocol(Protocol, Generic[ModelType]):
    """Async repository protocol."""

    @abstractmethod
    async def create(self, data: dict[str, Any], **kwargs) -> ModelType:
        """Create a new entity."""

    @abstractmethod
    async def get_by_id(self, entity_id: UUID, **kwargs) -> ModelType | None:
        """Get entity by ID."""

    @abstractmethod
    async def update(self, entity_id: UUID, data: dict[str, Any], **kwargs) -> ModelType:
        """Update entity."""

    @abstractmethod
    async def delete(self, entity_id: UUID, **kwargs) -> bool:
        """Delete entity."""

    @abstractmethod
    async def list(self, options: QueryOptions, **kwargs) -> list[ModelType]:
        """List entities with options."""

    @abstractmethod
    async def count(self, filters: list[QueryFilter], **kwargs) -> int:
        """Count entities."""
