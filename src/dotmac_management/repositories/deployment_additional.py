"""
Additional deployment repository methods.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.deployment import Deployment, InfrastructureTemplate
from ..repositories.base import BaseRepository


class DeploymentTemplateRepository(BaseRepository[InfrastructureTemplate]):
    """Repository for deployment template operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, InfrastructureTemplate)


class InfrastructureRepository(BaseRepository[Deployment]):
    """Repository for infrastructure operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Deployment)

    async def update_status(self, infrastructure_id: UUID, status: str, updated_by: str) -> Optional[Deployment]:
        """Update infrastructure status."""
        return await self.update(infrastructure_id, {"status": status}, updated_by)

    async def get_by_tenant_and_environment(self, tenant_id: UUID, environment: str) -> list[Deployment]:
        """Get infrastructure by tenant and environment."""
        return await self.list(
            filters={
                "tenant_id": tenant_id,
                "environment": environment,
                "is_deleted": False,
            }
        )

    async def get_by_tenant(self, tenant_id: UUID) -> list[Deployment]:
        """Get all infrastructure for a tenant."""
        return await self.list(filters={"tenant_id": tenant_id, "is_deleted": False})

    async def get_active_infrastructure(self) -> list[Deployment]:
        """Get all active infrastructure."""
        return await self.list(filters={"status": "active", "is_deleted": False})


class DeploymentRepository(BaseRepository[Deployment]):
    """Repository for deployment operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Deployment)

    async def update_status(self, deployment_id: UUID, status: str, updated_by: str) -> Optional[Deployment]:
        """Update deployment status."""
        return await self.update(deployment_id, {"status": status}, updated_by)

    async def get_with_relations(self, deployment_id: UUID) -> Optional[Deployment]:
        """Get deployment with related data."""
        # For now, just get the deployment - would implement joins in full implementation
        return await self.get_by_id(deployment_id)

    async def get_by_infrastructure(self, infrastructure_id: UUID) -> list[Deployment]:
        """Get deployments by infrastructure."""
        return await self.list(filters={"infrastructure_id": infrastructure_id, "is_deleted": False})

    async def get_by_tenant(self, tenant_id: UUID) -> list[Deployment]:
        """Get deployments by tenant."""
        return await self.list(filters={"tenant_id": tenant_id, "is_deleted": False})

    async def get_old_failed_deployments(self, cutoff_date: datetime) -> list[Deployment]:
        """Get old failed deployments."""
        stmt = select(self.model).where(
            and_(
                self.model.status == "failed",
                self.model.created_at <= cutoff_date,
                self.model.is_deleted is False,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


# ServiceInstance and DeploymentLog models don't exist in the current schema
# These repositories would need to be implemented when those models are created
