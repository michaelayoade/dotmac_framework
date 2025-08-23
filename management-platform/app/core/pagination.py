"""
Pagination utilities for API endpoints.
"""

from typing import Optional
from fastapi import Query


class PaginationParams:
    """Pagination parameters for API endpoints."""
    
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (starts from 1)"),
        size: int = Query(20, ge=1, le=100, description="Number of items per page")
    ):
        self.page = page
        self.size = size
        
    @property
    def skip(self) -> int:
        """Calculate skip value for database queries."""
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        """Get limit value for database queries."""
        return self.size


def create_pagination_response(
    items: list,
    total: int,
    page: int,
    size: int
) -> dict:
    """Create standardized pagination response."""
    pages = (total + size - 1) // size if total > 0 else 0
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1
    }