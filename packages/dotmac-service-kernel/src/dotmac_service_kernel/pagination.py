"""
Pagination utilities for consistent paginated results.

This module provides utilities for handling paginated data in a consistent way
across all services and repositories.
"""

from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    """Generic page container for paginated results.

    This container provides a consistent structure for paginated data across
    all services and repositories, including metadata about the pagination state.

    Attributes:
        items: List of items in this page
        total: Total number of items across all pages
        page: Current page number (1-based)
        page_size: Number of items per page
        total_pages: Total number of pages
        has_next: Whether there is a next page
        has_prev: Whether there is a previous page
    """

    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1

    @property
    def start_index(self) -> int:
        """Get the starting index of items in this page (0-based)."""
        return (self.page - 1) * self.page_size

    @property
    def end_index(self) -> int:
        """Get the ending index of items in this page (0-based, exclusive)."""
        return min(self.start_index + self.page_size, self.total)

    def to_dict(self) -> dict[str, int | bool | list[T]]:
        """Convert page to dictionary representation."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
            "start_index": self.start_index,
            "end_index": self.end_index,
        }


class PaginationParams(BaseModel):
    """Pydantic model for pagination parameters.

    This model provides validation and defaults for pagination parameters,
    commonly used in API endpoints.

    Attributes:
        page: Page number (1-based, minimum 1)
        size: Page size (minimum 1, maximum 1000, default 20)
        skip: Number of items to skip (computed from page and size)
        limit: Number of items to return (alias for size)
    """

    page: int = 1
    size: int = 20

    model_config = ConfigDict(validate_assignment=True)

    def __init__(self, page: int = 1, size: int = 20, **kwargs) -> None:
        """Initialize pagination parameters with validation.

        Args:
            page: Page number (minimum 1)
            size: Page size (minimum 1, maximum 1000)
            **kwargs: Additional keyword arguments
        """
        # Validate page
        if page < 1:
            page = 1

        # Validate size
        if size < 1:
            size = 1
        elif size > 1000:
            size = 1000

        super().__init__(page=page, size=size, **kwargs)

    @property
    def skip(self) -> int:
        """Calculate number of items to skip."""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """Alias for size (common in database queries)."""
        return self.size


def create_page(
    items: list[T],
    total: int,
    page: int = 1,
    page_size: int = 20
) -> Page[T]:
    """Create a page from items and pagination info.

    Convenience function to create a Page instance with validation.

    Args:
        items: List of items in this page
        total: Total number of items across all pages
        page: Current page number (minimum 1)
        page_size: Number of items per page (minimum 1)

    Returns:
        Page instance with the provided data
    """
    # Validate parameters
    page = max(1, page)
    page_size = max(1, page_size)
    total = max(0, total)

    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


def get_pagination_bounds(page: int, page_size: int) -> tuple[int, int]:
    """Get skip and limit values for database queries.

    Args:
        page: Page number (1-based)
        page_size: Number of items per page

    Returns:
        Tuple of (skip, limit) for database queries
    """
    page = max(1, page)
    page_size = max(1, page_size)

    skip = (page - 1) * page_size
    limit = page_size

    return skip, limit


__all__ = [
    "Page",
    "PaginationParams",
    "create_page",
    "get_pagination_bounds",
]
