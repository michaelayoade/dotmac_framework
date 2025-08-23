"""
Additional monitoring repository methods.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, and_, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.monitoring import (
    Metric, Alert, HealthCheck, SLARecord
)
from .base import BaseRepository


class MetricRepository(BaseRepository[Metric]):
    """Repository for metric operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Metric)
    
    async def delete_old_metrics(self, cutoff_date: datetime) -> int:
        """Delete old metrics."""
        stmt = select(self.model).where(
            and_(
                self.model.timestamp <= cutoff_date,
                self.model.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        old_metrics = result.scalars().all()
        
        count = 0
        for metric in old_metrics:
            await self.delete(metric.id)
            count += 1
        
        return count
    
    async def get_metrics_for_aggregation(self, start_time: datetime, end_time: datetime) -> List[Metric]:
        """Get metrics for aggregation."""
        stmt = select(self.model).where(
            and_(
                self.model.timestamp >= start_time,
                self.model.timestamp <= end_time,
                self.model.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_tenant_services(self, tenant_id: UUID) -> List[str]:
        """Get unique service names for a tenant."""
        stmt = select(distinct(self.model.service_name)).where(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.fetchall()]
    
    async def get_tenants_with_services(self) -> List[UUID]:
        """Get tenants that have services."""
        stmt = select(distinct(self.model.tenant_id)).where(
            self.model.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.fetchall()]
    
    async def count_tenant_metrics(self, tenant_id: UUID) -> int:
        """Count metrics for a tenant."""
        return await self.count({"tenant_id": tenant_id, "is_deleted": False})
    
    async def get_service_metrics(self, tenant_id: UUID, service_name: str, metric_name: str, start_time: datetime, end_time: datetime) -> List[Metric]:
        """Get metrics for a specific service."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.service_name == service_name,
                self.model.metric_name == metric_name,
                self.model.timestamp >= start_time,
                self.model.timestamp <= end_time,
                self.model.is_deleted == False
            )
        ).order_by(self.model.timestamp)
        result = await self.db.execute(stmt)
        return result.scalars().all()


class AlertRepository(BaseRepository[Alert]):
    """Repository for alert operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Alert)
    
    async def get_active_alerts(self, tenant_id: UUID = None) -> List[Alert]:
        """Get active alerts."""
        filters = {"status": "active", "is_deleted": False}
        if tenant_id:
            filters["tenant_id"] = tenant_id
        return await self.list(filters=filters)
    
    async def resolve_alert(self, alert_id: UUID, resolved_by: str) -> Optional[Alert]:
        """Resolve an alert."""
        return await self.update(
            alert_id, 
            {"status": "resolved", "resolved_at": datetime.utcnow()}, 
            resolved_by
        )


class HealthCheckRepository(BaseRepository[HealthCheck]):
    """Repository for health check operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, HealthCheck)
    
    async def get_by_tenant_and_service(self, tenant_id: UUID, service_name: str) -> List[HealthCheck]:
        """Get health checks for a tenant and service."""
        return await self.list(filters={
            "tenant_id": tenant_id,
            "service_name": service_name,
            "is_deleted": False
        })
    
    async def get_failing_checks(self) -> List[HealthCheck]:
        """Get failing health checks."""
        return await self.list(filters={
            "status": "unhealthy",
            "is_deleted": False
        })


class SLARecordRepository(BaseRepository[SLARecord]):
    """Repository for SLA record operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, SLARecord)
    
    async def get_by_tenant(self, tenant_id: UUID) -> List[SLARecord]:
        """Get SLA records for a tenant."""
        return await self.list(filters={
            "tenant_id": tenant_id,
            "is_deleted": False
        })
    
    async def get_by_service(self, tenant_id: UUID, service_name: str) -> List[SLARecord]:
        """Get SLA records for a service."""
        return await self.list(filters={
            "tenant_id": tenant_id,
            "service_name": service_name,
            "is_deleted": False
        })