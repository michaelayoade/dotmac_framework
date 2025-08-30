"""
Pagination utilities for DotMac Framework APIs.
Provides consistent pagination across all platforms.
"""

import math
from typing import Any, Dict, List, Optional

from fastapi import Depends, Query
from pydantic import BaseModel, Field, validator


class PaginationParams(BaseModel):
    """Pagination parameters for API requests."""

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """Alias for size for database queries."""
        return self.size

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "page": self.page,
            "size": self.size,
            "offset": self.offset,
            "limit": self.limit,
        }


class PaginationMeta(BaseModel):
    """Pagination metadata for API responses."""

    page: int = Field(description="Current page number")
    size: int = Field(description="Items per page")
    total: int = Field(description="Total items count")
    pages: int = Field(description="Total pages count")
    has_next: bool = Field(description="Has next page")
    has_prev: bool = Field(description="Has previous page")

    @classmethod
    def create(cls, params: PaginationParams, total: int) -> "PaginationMeta":
        """Create pagination metadata from params and total count."""
        pages = max(1, math.ceil(total / params.size))

        return cls(
            page=params.page,
            size=params.size,
            total=total,
            pages=pages,
            has_next=params.page < pages,
            has_prev=params.page > 1,
        )


class PaginatedResponse(BaseModel):
    """Generic paginated response."""

    data: List[Any] = Field(description="Response data items")
    meta: PaginationMeta = Field(description="Pagination metadata")


def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    """
    FastAPI dependency for pagination parameters.

    Args:
        page: Page number (1-based)
        size: Items per page (max 100)

    Returns:
        PaginationParams: Validated pagination parameters

    Usage:
        @app.get("/users/")
        async def get_users(pagination: PaginationParams = Depends(get_pagination_params)):
            # Use pagination.offset and pagination.limit for database queries
            pass
    """
    return PaginationParams(page=page, size=size)


def paginate_query_results(
    results: List[Any], params: PaginationParams, total: int
) -> PaginatedResponse:
    """
    Create paginated response from query results.

    Args:
        results: Query results (already limited by offset/limit)
        params: Pagination parameters used for the query
        total: Total count of items (without pagination)

    Returns:
        PaginatedResponse: Paginated response with metadata
    """
    meta = PaginationMeta.create(params, total)

    return PaginatedResponse(data=results, meta=meta)


# Helper functions for common pagination scenarios
def calculate_pagination_bounds(
    params: PaginationParams, total_items: int
) -> Dict[str, int]:
    """
    Calculate pagination bounds and metadata.

    Returns:
        Dict with offset, limit, total_pages, has_next, has_prev
    """
    total_pages = max(1, math.ceil(total_items / params.size))

    return {
        "offset": params.offset,
        "limit": params.limit,
        "total_pages": total_pages,
        "has_next": params.page < total_pages,
        "has_prev": params.page > 1,
        "current_page": params.page,
        "total_items": total_items,
    }


# SQL query helpers
def apply_pagination_to_sql_query(base_query: str, params: PaginationParams) -> str:
    """
    Apply LIMIT and OFFSET to SQL query.

    Args:
        base_query: Base SQL query without pagination
        params: Pagination parameters

    Returns:
        SQL query with LIMIT and OFFSET applied
    """
    return f"{base_query} LIMIT {params.limit} OFFSET {params.offset}"
