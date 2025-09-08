"""
Pagination utilities for API endpoints.
"""
from typing import Optional


class PaginationParams:
    """Pagination parameters for API endpoints."""

    def __init__(
        self,
        page: Optional[int] = None,
        size: Optional[int] = None,
    ):
        self.page = page or 1
        self.size = size or 20

    @property
    def skip(self) -> int:
        """Calculate skip value for database queries."""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """Get limit value for database queries."""
        return self.size


def create_pagination_response(items: list, total: int, page: int, size: int) -> dict:
    """Create standardized pagination response."""
    pages = (total + size - 1) // size if total > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }
