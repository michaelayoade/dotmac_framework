"""
Pagination helper utilities and convenience functions.
"""

from typing import Any

from dotmac.core.db_toolkit.pagination.paginator import PaginationHelper as CorePaginationHelper
from dotmac.core.db_toolkit.types import PaginationParams, PaginationResult, QueryOptions

PaginationHelper = CorePaginationHelper


def create_query_options(
    page: int = 1,
    per_page: int = 20,
    filters: dict[str, Any] | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    include_deleted: bool = False,
    relationships: list[str] | None = None,
) -> QueryOptions:
    """
    Create QueryOptions from simple parameters.

    Args:
        page: Page number (1-based)
        per_page: Items per page
        filters: Simple filter dictionary
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')
        include_deleted: Whether to include soft-deleted entities
        relationships: Related entities to eager load

    Returns:
        QueryOptions instance
    """
    from dotmac.core.db_toolkit.types import FilterOperator, QueryFilter, SortField, SortOrder

    # Convert simple filters to QueryFilter objects
    query_filters = []
    if filters:
        for field, value in filters.items():
            if isinstance(value, dict) and "operator" in value:
                # Advanced filter format
                operator = FilterOperator(value["operator"])
                filter_value = value["value"]
            else:
                # Simple equality filter
                operator = FilterOperator.EQ
                filter_value = value

            query_filters.append(QueryFilter(field=field, operator=operator, value=filter_value))

    # Convert simple sort to SortField objects
    sorts = []
    if sort_by:
        sort_order_enum = SortOrder.DESC if sort_order.lower() == "desc" else SortOrder.ASC
        sorts.append(SortField(field=sort_by, order=sort_order_enum))

    return QueryOptions(
        filters=query_filters,
        sorts=sorts,
        pagination=PaginationParams(page=page, per_page=per_page),
        include_deleted=include_deleted,
        relationships=relationships or [],
    )


def extract_pagination_metadata(result: PaginationResult) -> dict[str, Any]:
    """
    Extract pagination metadata from PaginationResult.

    Args:
        result: Pagination result

    Returns:
        Dictionary with pagination metadata
    """
    return {
        "pagination": {
            "total": result.total,
            "page": result.page,
            "per_page": result.per_page,
            "pages": result.pages,
            "has_next": result.has_next,
            "has_prev": result.has_prev,
            "next_page": result.page + 1 if result.has_next else None,
            "prev_page": result.page - 1 if result.has_prev else None,
        }
    }


def validate_pagination_params(page: int, per_page: int) -> None:
    """
    Validate pagination parameters.

    Args:
        page: Page number
        per_page: Items per page

    Raises:
        ValueError: If parameters are invalid
    """
    if page < 1:
        msg = "Page number must be >= 1"
        raise ValueError(msg)

    if per_page < 1:
        msg = "Items per page must be >= 1"
        raise ValueError(msg)

    if per_page > 1000:
        msg = "Items per page cannot exceed 1000"
        raise ValueError(msg)


def calculate_offset(page: int, per_page: int) -> int:
    """
    Calculate offset for pagination.

    Args:
        page: Page number (1-based)
        per_page: Items per page

    Returns:
        Offset for database query
    """
    return (page - 1) * per_page


def normalize_page_params(
    page: int | None = None,
    per_page: int | None = None,
    default_page: int = 1,
    default_per_page: int = 20,
    max_per_page: int = 1000,
) -> tuple[int, int]:
    """
    Normalize and validate pagination parameters.

    Args:
        page: Page number
        per_page: Items per page
        default_page: Default page if None provided
        default_per_page: Default per_page if None provided
        max_per_page: Maximum allowed per_page

    Returns:
        Tuple of (normalized_page, normalized_per_page)
    """
    # Apply defaults
    if page is None:
        page = default_page
    if per_page is None:
        per_page = default_per_page

    # Normalize values
    page = max(1, page)
    per_page = max(1, min(per_page, max_per_page))

    return page, per_page
