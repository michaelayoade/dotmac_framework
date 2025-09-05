"""
Base repository implementation for the DotMac Billing Package.

Provides common database operations with multi-tenant support and
platform-agnostic implementation using SQLAlchemy.
"""

from typing import Any, Generic, Optional, TypeVar, Union
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload

from ..core.models import BillingModelMixin
from ..services.protocols import DatabaseSessionProtocol

ModelType = TypeVar("ModelType", bound=BillingModelMixin)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseBillingRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository providing common CRUD operations for billing models."""

    def __init__(self, model: type[ModelType], db: DatabaseSessionProtocol):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    async def create(
        self, obj_in: CreateSchemaType, tenant_id: Optional[UUID] = None, **kwargs
    ) -> ModelType:
        """
        Create a new record.

        Args:
            obj_in: Create schema with data
            tenant_id: Tenant ID for multi-tenant support
            **kwargs: Additional fields to set

        Returns:
            Created model instance
        """
        # Convert Pydantic model to dict
        if hasattr(obj_in, "model_dump"):
            obj_data = obj_in.model_dump(exclude_unset=True)
        else:
            obj_data = obj_in.model_dump(exclude_unset=True)

        # Add tenant_id if provided
        if tenant_id is not None:
            obj_data["tenant_id"] = tenant_id

        # Add any additional kwargs
        obj_data.update(kwargs)

        # Create model instance
        db_obj = self.model(**obj_data)

        # Add to session
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)

        return db_obj

    async def get(
        self,
        id: UUID,
        tenant_id: Optional[UUID] = None,
        load_relationships: Optional[list[str]] = None,
    ) -> Optional[ModelType]:
        """
        Get record by ID.

        Args:
            id: Record ID
            tenant_id: Tenant ID for filtering
            load_relationships: List of relationships to eager load

        Returns:
            Model instance or None
        """
        query = select(self.model).where(self.model.id == id)

        # Add tenant filtering if provided
        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        # Add relationship loading
        if load_relationships:
            for relationship in load_relationships:
                if hasattr(self.model, relationship):
                    query = query.options(
                        selectinload(getattr(self.model, relationship))
                    )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        tenant_id: Optional[UUID] = None,
        load_relationships: Optional[list[str]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[ModelType]:
        """
        Get multiple records with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            tenant_id: Tenant ID for filtering
            load_relationships: List of relationships to eager load
            order_by: Field name to order by
            order_desc: Whether to order in descending order
            filters: Additional filters to apply

        Returns:
            List of model instances
        """
        query = select(self.model)

        # Add tenant filtering
        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        # Add custom filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if isinstance(value, list):
                        query = query.where(getattr(self.model, field).in_(value))
                    elif isinstance(value, dict):
                        # Support for range filters
                        if "gte" in value:
                            query = query.where(
                                getattr(self.model, field) >= value["gte"]
                            )
                        if "lte" in value:
                            query = query.where(
                                getattr(self.model, field) <= value["lte"]
                            )
                        if "gt" in value:
                            query = query.where(
                                getattr(self.model, field) > value["gt"]
                            )
                        if "lt" in value:
                            query = query.where(
                                getattr(self.model, field) < value["lt"]
                            )
                    else:
                        query = query.where(getattr(self.model, field) == value)

        # Add ordering
        if order_by and hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            if order_desc:
                query = query.order_by(desc(order_field))
            else:
                query = query.order_by(order_field)
        else:
            # Default ordering by creation date
            query = query.order_by(desc(self.model.created_at))

        # Add relationship loading
        if load_relationships:
            for relationship in load_relationships:
                if hasattr(self.model, relationship):
                    query = query.options(
                        selectinload(getattr(self.model, relationship))
                    )

        # Add pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update(
        self, db_obj: ModelType, obj_in: Union[UpdateSchemaType, dict[str, Any]]
    ) -> ModelType:
        """
        Update a record.

        Args:
            db_obj: Existing model instance
            obj_in: Update schema or dict with new data

        Returns:
            Updated model instance
        """
        # Convert to dict if needed
        if hasattr(obj_in, "model_dump"):
            update_data = obj_in.model_dump(exclude_unset=True)
        elif hasattr(obj_in, "dict"):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = obj_in

        # Update fields
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await self.db.commit()
        await self.db.refresh(db_obj)

        return db_obj

    async def delete(self, id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record ID
            tenant_id: Tenant ID for filtering

        Returns:
            True if deleted, False if not found
        """
        db_obj = await self.get(id, tenant_id)
        if db_obj:
            await self.db.delete(db_obj)
            await self.db.commit()
            return True
        return False

    async def count(
        self, tenant_id: Optional[UUID] = None, filters: Optional[dict[str, Any]] = None
    ) -> int:
        """
        Count records with optional filtering.

        Args:
            tenant_id: Tenant ID for filtering
            filters: Additional filters to apply

        Returns:
            Number of matching records
        """
        query = select(func.count(self.model.id))

        # Add tenant filtering
        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        # Add custom filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if isinstance(value, list):
                        query = query.where(getattr(self.model, field).in_(value))
                    else:
                        query = query.where(getattr(self.model, field) == value)

        result = await self.db.execute(query)
        return result.scalar()

    async def exists(self, id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        """
        Check if a record exists.

        Args:
            id: Record ID
            tenant_id: Tenant ID for filtering

        Returns:
            True if exists, False otherwise
        """
        query = select(self.model.id).where(self.model.id == id)

        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        result = await self.db.execute(query)
        return result.scalar() is not None

    async def get_by_field(
        self,
        field_name: str,
        field_value: Any,
        tenant_id: Optional[UUID] = None,
        load_relationships: Optional[list[str]] = None,
    ) -> Optional[ModelType]:
        """
        Get record by specific field value.

        Args:
            field_name: Name of the field to search by
            field_value: Value to search for
            tenant_id: Tenant ID for filtering
            load_relationships: List of relationships to eager load

        Returns:
            Model instance or None
        """
        if not hasattr(self.model, field_name):
            raise ValueError(f"Model {self.model.__name__} has no field '{field_name}'")

        query = select(self.model).where(getattr(self.model, field_name) == field_value)

        # Add tenant filtering
        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        # Add relationship loading
        if load_relationships:
            for relationship in load_relationships:
                if hasattr(self.model, relationship):
                    query = query.options(
                        selectinload(getattr(self.model, relationship))
                    )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def bulk_create(
        self, objects_in: list[CreateSchemaType], tenant_id: Optional[UUID] = None
    ) -> list[ModelType]:
        """
        Create multiple records in bulk.

        Args:
            objects_in: List of create schemas
            tenant_id: Tenant ID for all records

        Returns:
            List of created model instances
        """
        db_objects = []

        for obj_in in objects_in:
            # Convert to dict
            if hasattr(obj_in, "model_dump"):
                obj_data = obj_in.model_dump(exclude_unset=True)
            else:
                obj_data = obj_in.model_dump(exclude_unset=True)

            # Add tenant_id if provided
            if tenant_id is not None:
                obj_data["tenant_id"] = tenant_id

            db_obj = self.model(**obj_data)
            db_objects.append(db_obj)

        # Add all objects to session
        self.db.add_all(db_objects)
        await self.db.commit()

        # Refresh all objects
        for db_obj in db_objects:
            await self.db.refresh(db_obj)

        return db_objects

    async def soft_delete(self, id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        """
        Soft delete a record (if model supports it).

        Args:
            id: Record ID
            tenant_id: Tenant ID for filtering

        Returns:
            True if soft deleted, False if not found or not supported
        """
        db_obj = await self.get(id, tenant_id)
        if db_obj and hasattr(db_obj, "is_active"):
            db_obj.is_active = False
            await self.db.commit()
            return True
        return False
