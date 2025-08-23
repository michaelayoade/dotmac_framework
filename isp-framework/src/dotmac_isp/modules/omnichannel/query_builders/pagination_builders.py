"""
Pagination builders for query results.
"""

from typing import Optional
from sqlalchemy.orm import Query


class PaginationBuilder:
    """Handles pagination logic for queries."""
    
    def __init__(self):
        self._page = 1
        self._per_page = 20
        self._max_per_page = 1000
    
    def configure(self, page: int = 1, per_page: int = 20) -> 'PaginationBuilder':
        """Configure pagination parameters."""
        self._page = max(1, page)  # Ensure page is at least 1
        self._per_page = min(max(1, per_page), self._max_per_page)  # Clamp between 1 and max
        return self
    
    def apply_pagination(self, query: Query) -> Query:
        """Apply pagination to the query."""
        offset = (self._page - 1) * self._per_page
        return query.offset(offset).limit(self._per_page)
    
    @property
    def page(self) -> int:
        """Current page number."""
        return self._page
    
    @property
    def per_page(self) -> int:
        """Items per page."""
        return self._per_page
    
    @property
    def offset(self) -> int:
        """Calculate offset for current page."""
        return (self._page - 1) * self._per_page
    
    def calculate_total_pages(self, total_count: int) -> int:
        """Calculate total pages given a total count."""
        return (total_count + self._per_page - 1) // self._per_page