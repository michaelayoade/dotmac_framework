"""
Pagination utilities for consistent paginated responses.
"""

from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar
from math import ceil

from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.per_page
    
    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.per_page


class CursorPaginationParams(BaseModel):
    """Cursor-based pagination for large datasets."""
    
    cursor: Optional[str] = Field(None, description="Cursor for next page")
    limit: int = Field(default=20, ge=1, le=100, description="Number of items")
    

class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response format."""
    
    data: List[T]
    pagination: Dict[str, Any]
    
    @classmethod
    def create(
        cls,
        data: List[T],
        total: int,
        page: int,
        per_page: int,
        **extra_metadata
    ) -> 'PaginatedResponse[T]':
        """Create paginated response with metadata."""
        pages = ceil(total / per_page) if per_page > 0 else 0
        
        pagination = {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1,
            "next_page": page + 1 if page < pages else None,
            "prev_page": page - 1 if page > 1 else None,
            **extra_metadata
        }
        
        return cls(data=data, pagination=pagination)


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based paginated response."""
    
    data: List[T]
    has_next: bool
    next_cursor: Optional[str]
    
    @classmethod
    def create(
        cls,
        data: List[T],
        has_next: bool,
        next_cursor: Optional[str] = None
    ) -> 'CursorPaginatedResponse[T]':
        """Create cursor paginated response."""
        return cls(
            data=data,
            has_next=has_next,
            next_cursor=next_cursor
        )


class PaginationHelper:
    """Helper class for pagination operations."""
    
    @staticmethod
    def validate_pagination_params(
        page: int = 1,
        per_page: int = 20,
        max_per_page: int = 100
    ) -> PaginationParams:
        """Validate and normalize pagination parameters."""
        page = max(1, page)
        per_page = min(max(1, per_page), max_per_page)
        
        return PaginationParams(page=page, per_page=per_page)
    
    @staticmethod
    def calculate_pagination_metadata(
        total: int,
        page: int,
        per_page: int
    ) -> Dict[str, Any]:
        """Calculate pagination metadata."""
        pages = ceil(total / per_page) if per_page > 0 else 0
        
        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1,
            "next_page": page + 1 if page < pages else None,
            "prev_page": page - 1 if page > 1 else None,
            "showing_from": ((page - 1) * per_page + 1) if total > 0 else 0,
            "showing_to": min(page * per_page, total)
        }
    
    @staticmethod
    def get_safe_pagination_bounds(
        page: int,
        per_page: int,
        max_items: int = 10000
    ) -> Tuple[int, int]:
        """Get safe pagination bounds to prevent resource exhaustion."""
        offset = (page - 1) * per_page
        
        # Prevent excessive offset that could cause performance issues
        if offset > max_items:
            raise ValueError(f"Offset {offset} exceeds maximum allowed {max_items}")
        
        return offset, per_page
    
    @staticmethod
    def create_cursor_from_item(
        item: Any,
        cursor_field: str = "id"
    ) -> str:
        """Create cursor from an item."""
        import base64
        
        cursor_value = getattr(item, cursor_field, None)
        if cursor_value is None:
            raise ValueError(f"Cursor field '{cursor_field}' not found on item")
        
        # Convert to string and encode
        cursor_str = str(cursor_value)
        cursor_bytes = cursor_str.encode('utf-8')
        return base64.b64encode(cursor_bytes).decode('utf-8')
    
    @staticmethod
    def decode_cursor(cursor: str) -> str:
        """Decode cursor to get the actual value."""
        import base64
        
        try:
            cursor_bytes = base64.b64decode(cursor.encode('utf-8'))
            return cursor_bytes.decode('utf-8')
        except Exception:
            raise ValueError("Invalid cursor format")


class DatabasePaginator:
    """Database-specific pagination helper."""
    
    @staticmethod
    async def paginate_query(
        db_session,
        base_query,
        page: int = 1,
        per_page: int = 20,
        count_query=None
    ) -> tuple[List[Any], int]:
        """
        Paginate a SQLAlchemy query efficiently.
        
        Args:
            db_session: Database session
            base_query: Base SQLAlchemy query
            page: Page number (1-based)
            per_page: Items per page
            count_query: Optional separate count query for performance
            
        Returns:
            Tuple of (items, total_count)
        """
        # Validate pagination params
        pagination = PaginationHelper.validate_pagination_params(page, per_page)
        
        # Get total count
        if count_query:
            count_result = await db_session.execute(count_query)
            total = count_result.scalar()
        else:
            # Create count query from base query
            from sqlalchemy import func, select
            count_query = select(func.count()).select_from(base_query.subquery())
            count_result = await db_session.execute(count_query)
            total = count_result.scalar()
        
        # Get paginated items
        items_query = base_query.offset(pagination.offset).limit(pagination.limit)
        items_result = await db_session.execute(items_query)
        items = items_result.scalars().all()
        
        return items, total
    
    @staticmethod
    async def cursor_paginate_query(
        db_session,
        base_query,
        cursor_field: str,
        limit: int = 20,
        cursor: Optional[str] = None,
        ascending: bool = True
    ) -> tuple[List[Any], Optional[str], bool]:
        """
        Cursor-based pagination for large datasets.
        
        Args:
            db_session: Database session
            base_query: Base SQLAlchemy query
            cursor_field: Field to use for cursor pagination
            limit: Number of items to fetch
            cursor: Current cursor position
            ascending: Sort direction
            
        Returns:
            Tuple of (items, next_cursor, has_next)
        """
        query = base_query
        
        # Apply cursor filter if provided
        if cursor:
            cursor_value = PaginationHelper.decode_cursor(cursor)
            # This assumes the cursor field is sortable
            # You might need to adapt this based on your field type
            if ascending:
                query = query.where(getattr(query.column_descriptions[0]['type'], cursor_field) > cursor_value)
            else:
                query = query.where(getattr(query.column_descriptions[0]['type'], cursor_field) < cursor_value)
        
        # Fetch one extra item to determine if there are more pages
        items_query = query.limit(limit + 1)
        items_result = await db_session.execute(items_query)
        items = items_result.scalars().all()
        
        # Determine if there are more items
        has_next = len(items) > limit
        if has_next:
            items = items[:-1]  # Remove the extra item
        
        # Generate next cursor
        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            next_cursor = PaginationHelper.create_cursor_from_item(last_item, cursor_field)
        
        return items, next_cursor, has_next