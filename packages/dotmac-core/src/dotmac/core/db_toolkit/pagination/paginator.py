"""
High-performance database pagination utilities.
"""

import base64
import json
import logging
from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query, Session

from dotmac.core.db_toolkit.types import (
    DatabaseError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DatabasePaginator:
    """
    High-performance database pagination with support for both
    offset-based and cursor-based pagination.
    """

    @staticmethod
    def paginate_query(
        session: Session,
        query: Query,
        page: int,
        per_page: int,
        count_query: Query | None = None,
    ) -> tuple[list[Any], int]:
        """
        Paginate synchronous query with efficient counting.

        Args:
            session: Database session
            query: Base query to paginate
            page: Page number (1-based)
            per_page: Items per page
            count_query: Optional separate count query for performance

        Returns:
            Tuple of (items, total_count)
        """
        try:
            # Calculate offset
            offset = (page - 1) * per_page

            # Get total count (use separate count query if provided for performance)
            if count_query is not None:
                total = count_query.scalar() or 0
            else:
                # Create count query from main query
                count_query = session.query(func.count()).select_from(query.subquery())
                total = count_query.scalar() or 0

            # Get items with pagination
            items = query.offset(offset).limit(per_page).all()

            return items, total

        except Exception as e:
            logger.error("Error in query pagination: %s", e)
            msg = f"Pagination failed: {e}"

            raise DatabaseError(msg) from e

    @staticmethod
    async def async_paginate_query(
        session: AsyncSession,
        query,
        page: int,
        per_page: int,
        count_query=None,
    ) -> tuple[list[Any], int]:
        """
        Paginate asynchronous query with efficient counting.

        Args:
            session: Async database session
            query: Base query to paginate
            page: Page number (1-based)
            per_page: Items per page
            count_query: Optional separate count query for performance

        Returns:
            Tuple of (items, total_count)
        """
        try:
            # Calculate offset
            offset = (page - 1) * per_page

            # Get total count
            if count_query is not None:
                count_result = await session.execute(count_query)
                total = count_result.scalar() or 0
            else:
                # Create count query from main query subquery
                count_query = select(func.count()).select_from(query.subquery())
                count_result = await session.execute(count_query)
                total = count_result.scalar() or 0

            # Get items with pagination
            items_query = query.offset(offset).limit(per_page)
            items_result = await session.execute(items_query)
            items = items_result.scalars().all()

            return items, total

        except Exception as e:
            logger.error("Error in async query pagination: %s", e)
            msg = f"Async pagination failed: {e}"

            raise DatabaseError(msg) from e

    @staticmethod
    def cursor_paginate_query(
        session: Session,
        query: Query,
        cursor_field: str,
        limit: int,
        cursor: str | None = None,
        ascending: bool = True,
    ) -> tuple[list[Any], str | None, bool]:
        """
        Cursor-based pagination for synchronous queries.

        Args:
            session: Database session
            query: Base query to paginate
            cursor_field: Field to use for cursor positioning
            limit: Maximum items to return
            cursor: Current cursor position
            ascending: Sort direction

        Returns:
            Tuple of (items, next_cursor, has_next)
        """
        try:
            # Get model class from query
            model_class = query.column_descriptions[0]["type"]
            cursor_column = getattr(model_class, cursor_field)

            # Apply cursor filtering if provided
            if cursor:
                cursor_value = PaginationHelper.decode_cursor(cursor)
                if ascending:
                    query = query.filter(cursor_column > cursor_value)
                    query = query.order_by(cursor_column.asc())
                else:
                    query = query.filter(cursor_column < cursor_value)
                    query = query.order_by(cursor_column.desc())
            else:
                if ascending:
                    query = query.order_by(cursor_column.asc())
                else:
                    query = query.order_by(cursor_column.desc())

            # Fetch items with one extra to determine if there are more
            items = query.limit(limit + 1).all()

            # Determine if there are more items
            has_next = len(items) > limit
            if has_next:
                items = items[:-1]

            # Generate next cursor
            next_cursor = None
            if has_next and items:
                last_item = items[-1]
                next_cursor = PaginationHelper.create_cursor_from_item(last_item, cursor_field)

            return items, next_cursor, has_next

        except Exception as e:
            logger.error("Error in cursor pagination: %s", e)
            msg = f"Cursor pagination failed: {e}"

            raise DatabaseError(msg) from e

    @staticmethod
    async def async_cursor_paginate_query(
        session: AsyncSession,
        query,
        cursor_field: str,
        limit: int,
        cursor: str | None = None,
        ascending: bool = True,
    ) -> tuple[list[Any], str | None, bool]:
        """
        Cursor-based pagination for asynchronous queries.

        Args:
            session: Async database session
            query: Base query to paginate
            cursor_field: Field to use for cursor positioning
            limit: Maximum items to return
            cursor: Current cursor position
            ascending: Sort direction

        Returns:
            Tuple of (items, next_cursor, has_next)
        """
        try:
            # Extract model class from query
            model_class = query.column_descriptions[0]["type"]
            cursor_column = getattr(model_class, cursor_field)

            # Apply cursor filtering if provided
            if cursor:
                cursor_value = PaginationHelper.decode_cursor(cursor)
                if ascending:
                    query = query.where(cursor_column > cursor_value)
                    query = query.order_by(cursor_column.asc())
                else:
                    query = query.where(cursor_column < cursor_value)
                    query = query.order_by(cursor_column.desc())
            else:
                if ascending:
                    query = query.order_by(cursor_column.asc())
                else:
                    query = query.order_by(cursor_column.desc())

            # Fetch items with one extra to determine if there are more
            items_query = query.limit(limit + 1)
            result = await session.execute(items_query)
            items = result.scalars().all()

            # Determine if there are more items
            has_next = len(items) > limit
            if has_next:
                items = items[:-1]

            # Generate next cursor
            next_cursor = None
            if has_next and items:
                last_item = items[-1]
                next_cursor = PaginationHelper.create_cursor_from_item(last_item, cursor_field)

            return items, next_cursor, has_next

        except Exception as e:
            logger.error("Error in async cursor pagination: %s", e)
            msg = f"Async cursor pagination failed: {e}"

            raise DatabaseError(msg) from e


class PerformancePaginator:
    """
    High-performance pagination optimizations for large datasets.
    """

    @staticmethod
    def paginate_with_count_estimate(
        session: Session,
        query: Query,
        page: int,
        per_page: int,
        count_threshold: int = 10000,
    ) -> tuple[list[Any], int | str]:
        """
        Paginate with count estimation for better performance on large datasets.

        Args:
            session: Database session
            query: Base query to paginate
            page: Page number (1-based)
            per_page: Items per page
            count_threshold: Threshold for switching to count estimation

        Returns:
            Tuple of (items, total_count_or_estimate)
        """
        try:
            # Get a sample count first
            sample_count = query.limit(count_threshold + 1).count()

            if sample_count <= count_threshold:
                # Use exact count for smaller datasets
                return DatabasePaginator.paginate_query(session, query, page, per_page)
            else:
                # Use estimation for larger datasets
                offset = (page - 1) * per_page
                items = query.offset(offset).limit(per_page).all()
                return items, f"{count_threshold}+"

        except Exception as e:
            logger.error("Error in performance pagination: %s", e)
            msg = f"Performance pagination failed: {e}"

            raise DatabaseError(msg) from e

    @staticmethod
    def deep_pagination_optimize(
        session: Session,
        query: Query,
        page: int,
        per_page: int,
        cursor_field: str = "id",
    ) -> tuple[list[Any], int]:
        """
        Optimize deep pagination using cursor-based approach.

        Deep offset pagination becomes inefficient. This method automatically
        switches to cursor-based pagination for deep pages.

        Args:
            session: Database session
            query: Base query to paginate
            page: Page number (1-based)
            per_page: Items per page
            cursor_field: Field to use for cursor optimization

        Returns:
            Tuple of (items, total_count)
        """
        try:
            deep_threshold = 100  # Switch to cursor optimization after page 100

            if page <= deep_threshold:
                # Use normal pagination for shallow pages
                return DatabasePaginator.paginate_query(session, query, page, per_page)
            else:
                # Use cursor optimization for deep pages
                # Calculate approximate cursor position
                target_offset = (page - 1) * per_page

                # Get the cursor value at target position
                model_class = query.column_descriptions[0]["type"]
                cursor_column = getattr(model_class, cursor_field)

                # Get cursor value at approximate position
                cursor_query = query.order_by(cursor_column).offset(target_offset).limit(1)
                cursor_item = cursor_query.first()

                if cursor_item:
                    cursor_value = getattr(cursor_item, cursor_field)
                    # Use cursor-based pagination from this point
                    optimized_query = query.filter(cursor_column >= cursor_value).order_by(
                        cursor_column
                    )
                    items = optimized_query.limit(per_page).all()
                else:
                    items = []

                # Get total count (expensive but necessary for page calculation)
                total = query.count()

                return items, total

        except Exception as e:
            logger.error("Error in deep pagination optimization: %s", e)
            msg = f"Deep pagination optimization failed: {e}"

            raise DatabaseError(msg) from e


class PaginationHelper:
    """
    Utility functions for pagination operations.
    """

    @staticmethod
    def encode_cursor(value: Any) -> str:
        """
        Encode cursor value to base64 string.

        Args:
            value: Cursor value (UUID, datetime, int, str, etc.)

        Returns:
            Base64 encoded cursor string
        """
        try:
            # Convert different types to JSON-serializable format
            if isinstance(value, UUID):
                cursor_data = {"type": "uuid", "value": str(value)}
            elif isinstance(value, datetime):
                cursor_data = {"type": "datetime", "value": value.isoformat()}
            elif isinstance(value, int | float | str):
                cursor_data = {"type": type(value).__name__, "value": value}
            else:
                cursor_data = {"type": "str", "value": str(value)}

            # Encode to JSON then base64
            json_str = json.dumps(cursor_data, default=str)
            return base64.b64encode(json_str.encode()).decode()

        except Exception as e:
            logger.error("Error encoding cursor: %s", e)
            msg = f"Failed to encode cursor: {e}"

            raise DatabaseError(msg) from e

    @staticmethod
    def decode_cursor(cursor: str) -> Any:
        """
        Decode base64 cursor string to original value.

        Args:
            cursor: Base64 encoded cursor string

        Returns:
            Original cursor value
        """
        try:
            # Decode from base64 then JSON
            json_str = base64.b64decode(cursor.encode()).decode()
            cursor_data = json.loads(json_str)

            value_type = cursor_data["type"]
            value = cursor_data["value"]

            # Convert back to original type
            if value_type == "uuid":
                return UUID(value)
            elif value_type == "datetime":
                return datetime.fromisoformat(value)
            elif value_type == "int":
                return int(value)
            elif value_type == "float":
                return float(value)
            else:
                return value

        except Exception as e:
            logger.error("Error decoding cursor: %s", e)
            msg = f"Failed to decode cursor: {e}"

            raise DatabaseError(msg) from e

    @staticmethod
    def create_cursor_from_item(item: Any, field_name: str) -> str:
        """
        Create cursor from database item.

        Args:
            item: Database model instance
            field_name: Field name to use for cursor

        Returns:
            Base64 encoded cursor string
        """
        try:
            field_value = getattr(item, field_name)
            return PaginationHelper.encode_cursor(field_value)
        except Exception as e:
            logger.error("Error creating cursor from item: %s", e)
            msg = f"Failed to create cursor: {e}"

            raise DatabaseError(msg) from e

    @staticmethod
    def calculate_pagination_info(total: int, page: int, per_page: int) -> dict[str, Any]:
        """
        Calculate comprehensive pagination metadata.

        Args:
            total: Total number of items
            page: Current page number
            per_page: Items per page

        Returns:
            Dictionary with pagination metadata
        """
        pages = (total + per_page - 1) // per_page if total > 0 else 0
        has_next = page < pages
        has_prev = page > 1

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev,
            "next_page": page + 1 if has_next else None,
            "prev_page": page - 1 if has_prev else None,
            "start_index": (page - 1) * per_page + 1 if total > 0 else 0,
            "end_index": min(page * per_page, total),
        }


class CursorHelper:
    """
    Specialized helper for cursor-based pagination.
    """

    @staticmethod
    def validate_cursor_field(model_class: type, field_name: str) -> bool:
        """
        Validate if field is suitable for cursor pagination.

        Args:
            model_class: SQLAlchemy model class
            field_name: Field name to validate

        Returns:
            True if field is suitable for cursor pagination
        """
        try:
            if not hasattr(model_class, field_name):
                return False

            # Check if field has unique constraint or is part of unique index
            # This is a simplified check - in production, you'd inspect the schema
            field = getattr(model_class, field_name)

            # Basic checks for cursor suitability
            return (
                field.unique
                if hasattr(field, "unique")
                else False
                or field_name in ["id", "created_at", "updated_at"]  # Common cursor fields
            )

        except Exception:
            return False

    @staticmethod
    def get_optimal_cursor_field(model_class: type) -> str:
        """
        Determine the optimal field for cursor pagination.

        Args:
            model_class: SQLAlchemy model class

        Returns:
            Field name for cursor pagination
        """
        # Preferred fields in order of preference
        preferred_fields = ["id", "created_at", "updated_at"]

        for field_name in preferred_fields:
            if hasattr(model_class, field_name):
                return field_name

        # Fallback to first available field
        return "id"  # Assume all models have an id field
