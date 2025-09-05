"""Enhanced ISP Base Service with common patterns."""

from typing import Any, Optional
from uuid import UUID

from dotmac_shared.services.base import BaseService
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from dotmac.application import standard_exception_handler


class ISPBaseService(BaseService):
    """Enhanced base service for ISP modules with common DRY patterns."""

    def __init__(self, tenant_id: str, db: AsyncSession):
        super().__init__()
        self.tenant_id = tenant_id
        self.db = db

    @standard_exception_handler
    async def get_by_id_for_tenant(
        self,
        model_class: type,
        record_id: UUID,
        load_relationships: Optional[list[str]] = None,
    ) -> Optional[Any]:
        """Get record by ID ensuring tenant isolation."""

        query = select(model_class).where(
            and_(model_class.id == record_id, model_class.tenant_id == self.tenant_id)
        )

        if load_relationships:
            for rel in load_relationships:
                query = query.options(selectinload(getattr(model_class, rel)))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    @standard_exception_handler
    async def list_for_tenant(
        self,
        model_class: type,
        filters: Optional[dict] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: Optional[str] = "created_at",
    ) -> list[Any]:
        """List records for tenant with common filtering."""

        query = select(model_class).where(model_class.tenant_id == self.tenant_id)

        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if hasattr(model_class, key):
                    query = query.where(getattr(model_class, key) == value)

        # Apply ordering
        if order_by and hasattr(model_class, order_by):
            query = query.order_by(getattr(model_class, order_by))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def count_for_tenant(
        self, model_class: type, filters: Optional[dict] = None
    ) -> int:
        """Count records for tenant."""

        query = select(model_class).where(model_class.tenant_id == self.tenant_id)

        if filters:
            for key, value in filters.items():
                if hasattr(model_class, key):
                    query = query.where(getattr(model_class, key) == value)

        result = await self.db.execute(query)
        return len(result.scalars().all())

    @standard_exception_handler
    async def create_for_tenant(self, model_class: type, data: dict) -> Any:
        """Create record with tenant isolation."""

        # Ensure tenant_id is set
        data["tenant_id"] = self.tenant_id

        instance = model_class(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)

        return instance

    @standard_exception_handler
    async def update_for_tenant(
        self, model_class: type, record_id: UUID, data: dict
    ) -> Optional[Any]:
        """Update record ensuring tenant isolation."""

        instance = await self.get_by_id_for_tenant(model_class, record_id)
        if not instance:
            return None

        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.db.flush()
        await self.db.refresh(instance)

        return instance

    @standard_exception_handler
    async def delete_for_tenant(self, model_class: type, record_id: UUID) -> bool:
        """Delete record ensuring tenant isolation."""

        instance = await self.get_by_id_for_tenant(model_class, record_id)
        if not instance:
            return False

        await self.db.delete(instance)
        await self.db.flush()

        return True
