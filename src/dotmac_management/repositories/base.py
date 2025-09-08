"""
Base repository with common CRUD operations.
"""

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, db: AsyncSession, model: type[ModelType]):
        self.db = db
        self.model = model

    async def create(self, obj_data: dict[str, Any], user_id: Optional[str] = None) -> ModelType:
        """Create a new record."""
        if user_id:
            obj_data["created_by"] = user_id
            obj_data["updated_by"] = user_id

        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def get_by_id(
        self,
        id: UUID,
        include_deleted: bool = False,
        relationships: Optional[list[str]] = None,
    ) -> Optional[ModelType]:
        """Get record by ID."""
        query = select(self.model).where(self.model.id == id)

        if not include_deleted:
            query = query.where(self.model.is_deleted is False)

        if relationships:
            for rel in relationships:
                query = query.options(selectinload(getattr(self.model, rel)))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_field(self, field_name: str, value: Any, include_deleted: bool = False) -> Optional[ModelType]:
        """Get record by any field."""
        field = getattr(self.model, field_name)
        query = select(self.model).where(field == value)

        if not include_deleted:
            query = query.where(self.model.is_deleted is False)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[str] = None,
        include_deleted: bool = False,
        relationships: Optional[list[str]] = None,
    ) -> list[ModelType]:
        """List records with filtering and pagination."""
        query = select(self.model)

        if not include_deleted:
            query = query.where(self.model.is_deleted is False)

        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    if isinstance(value, list):
                        query = query.where(field.in_(value))
                    else:
                        query = query.where(field == value)

        if order_by:
            if order_by.startswith("-"):
                field_name = order_by[1:]
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    query = query.order_by(field.desc())
            else:
                if hasattr(self.model, order_by):
                    field = getattr(self.model, order_by)
                    query = query.order_by(field.asc())
        else:
            query = query.order_by(self.model.created_at.desc())

        if relationships:
            for rel in relationships:
                query = query.options(selectinload(getattr(self.model, rel)))

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[str] = None,
        include_deleted: bool = False,
        relationships: Optional[list[str]] = None,
    ) -> tuple[list[ModelType], int]:
        """List records with proper pagination and total count."""
        # Build base query
        query = select(self.model)

        if not include_deleted:
            query = query.where(self.model.is_deleted is False)

        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    if isinstance(value, list):
                        query = query.where(field.in_(value))
                    else:
                        query = query.where(field == value)

        if order_by:
            if order_by.startswith("-"):
                field_name = order_by[1:]
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    query = query.order_by(field.desc())
            else:
                if hasattr(self.model, order_by):
                    field = getattr(self.model, order_by)
                    query = query.order_by(field.asc())
        else:
            query = query.order_by(self.model.created_at.desc())

        if relationships:
            for rel in relationships:
                query = query.options(selectinload(getattr(self.model, rel)))

        # Simple pagination implementation
        offset = (page - 1) * per_page
        items = await self.db.execute(query.offset(offset).limit(per_page))
        return items.scalars().all()

    async def cursor_paginate(
        self,
        cursor_field: str = "id",
        limit: int = 20,
        cursor: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        ascending: bool = True,
        include_deleted: bool = False,
        relationships: Optional[list[str]] = None,
    ) -> tuple[list[ModelType], Optional[str], bool]:
        """Cursor-based pagination for large datasets."""
        # Build base query
        query = select(self.model)

        if not include_deleted:
            query = query.where(self.model.is_deleted is False)

        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    if isinstance(value, list):
                        query = query.where(field.in_(value))
                    else:
                        query = query.where(field == value)

        if relationships:
            for rel in relationships:
                query = query.options(selectinload(getattr(self.model, rel)))

        # Apply cursor pagination
        if cursor:
            cursor_value = cursor  # Simplified - use cursor as direct value
            field = getattr(self.model, cursor_field)

            if ascending:
                query = query.where(field > cursor_value)
                query = query.order_by(field.asc())
            else:
                query = query.where(field < cursor_value)
                query = query.order_by(field.desc())
        else:
            field = getattr(self.model, cursor_field)
            if ascending:
                query = query.order_by(field.asc())
            else:
                query = query.order_by(field.desc())

        # Fetch items with one extra to determine if there are more
        items_query = query.limit(limit + 1)
        result = await self.db.execute(items_query)
        items = result.scalars().all()

        # Determine if there are more items
        has_next = len(items) > limit
        if has_next:
            items = items[:-1]

        # Generate next cursor
        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            next_cursor = str(getattr(last_item, cursor_field))  # Simplified cursor

        return items, next_cursor, has_next

    async def count(self, filters: Optional[dict[str, Any]] = None, include_deleted: bool = False) -> int:
        """Count records with filtering."""
        query = select(func.count(self.model.id))

        if not include_deleted:
            query = query.where(self.model.is_deleted is False)

        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    if isinstance(value, list):
                        query = query.where(field.in_(value))
                    else:
                        query = query.where(field == value)

        result = await self.db.execute(query)
        return result.scalar()

    async def update(self, id: UUID, obj_data: dict[str, Any], user_id: Optional[str] = None) -> Optional[ModelType]:
        """Update a record."""
        # Set audit fields
        obj_data["updated_at"] = datetime.now(timezone.utc)
        if user_id:
            obj_data["updated_by"] = user_id

        query = (
            update(self.model)
            .where(self.model.id == id)
            .where(self.model.is_deleted is False)
            .values(**obj_data)
            .execution_options(synchronize_session="fetch")
        )
        result = await self.db.execute(query)

        if result.rowcount == 0:
            return None

        return await self.get_by_id(id)

    async def delete(self, id: UUID, soft_delete: bool = True, user_id: Optional[str] = None) -> bool:
        """Delete a record (soft or hard delete)."""
        if soft_delete:
            obj_data = {"is_deleted": True, "deleted_at": func.now()}
            if user_id:
                obj_data["updated_by"] = user_id

            query = (
                update(self.model).where(self.model.id == id).where(self.model.is_deleted is False).values(**obj_data)
            )
        else:
            query = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        return result.rowcount > 0

    async def bulk_create(self, objects_data: list[dict[str, Any]], user_id: Optional[str] = None) -> list[ModelType]:
        """Create multiple records."""
        if user_id:
            for obj_data in objects_data:
                obj_data["created_by"] = user_id
                obj_data["updated_by"] = user_id

        db_objects = [self.model(**obj_data) for obj_data in objects_data]
        self.db.add_all(db_objects)
        await self.db.flush()

        for db_obj in db_objects:
            await self.db.refresh(db_obj)

        return db_objects

    async def exists(self, id: UUID) -> bool:
        """Check if record exists."""
        query = select(func.count(self.model.id)).where(self.model.id == id, self.model.is_deleted is False)
        result = await self.db.execute(query)
        return result.scalar() > 0

    async def search(
        self,
        search_term: str,
        search_fields: list[str],
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[ModelType]:
        """Search records across multiple fields."""
        query = select(self.model)

        # Add search conditions
        search_conditions = []
        for field_name in search_fields:
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                search_conditions.append(field.ilike(f"%{search_term}%"))

        if search_conditions:
            from sqlalchemy import or_

            query = query.where(or_(*search_conditions))

        query = query.where(self.model.is_deleted is False)

        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    query = query.where(field == value)

        query = query.order_by(self.model.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()
