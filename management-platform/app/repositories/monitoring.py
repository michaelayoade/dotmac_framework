"""
Monitoring repository for health checks, alerts, and SLA tracking.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from models.monitoring import (
    HealthCheck,
    Metric,
    Alert,
    SLARecord,
    HealthStatus,
    AlertSeverity,
    AlertStatus,
    MetricType
)
from repositories.base import BaseRepository


class MonitoringRepository(BaseRepository[HealthCheck]):
    """Repository for monitoring operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, HealthCheck)
    
    async def get_tenant_health_checks(
        self,
        tenant_id: UUID,
        limit: int = 10,
        check_type: Optional[str] = None
    ) -> List[HealthCheck]:
        """Get recent health checks for a tenant."""
        query = select(HealthCheck).where(
            HealthCheck.tenant_id == tenant_id
        ).order_by(desc(HealthCheck.created_at)).limit(limit)
        
        if check_type:
            query = query.where(HealthCheck.check_type == check_type)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_active_alerts(self, tenant_id: UUID) -> List[Alert]:
        """Get active alerts for a tenant."""
        query = select(Alert).where(
            and_(
                Alert.tenant_id == tenant_id,
                Alert.status == AlertStatus.ACTIVE
            )
        ).order_by(desc(Alert.severity), desc(Alert.first_triggered_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_latest_sla_record(self, tenant_id: UUID) -> Optional[SLARecord]:
        """Get the latest SLA record for a tenant."""
        query = select(SLARecord).where(
            SLARecord.tenant_id == tenant_id
        ).order_by(desc(SLARecord.period_end)).limit(1)
        
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_tenant_metrics(
        self,
        tenant_id: UUID,
        metric_names: List[str],
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000
    ) -> List[Metric]:
        """Get metrics for a tenant within a time range."""
        query = select(Metric).where(
            and_(
                Metric.tenant_id == tenant_id,
                Metric.metric_name.in_(metric_names),
                Metric.timestamp >= start_time,
                Metric.timestamp <= end_time
            )
        ).order_by(Metric.timestamp.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def record_health_check(
        self,
        tenant_id: UUID,
        check_name: str,
        check_type: str,
        status: HealthStatus,
        success: bool,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
        endpoint_url: Optional[str] = None
    ) -> HealthCheck:
        """Record a new health check result."""
        health_check_data = {
            "tenant_id": tenant_id,
            "check_name": check_name,
            "check_type": check_type,
            "status": status,
            "success": success,
            "response_time_ms": response_time_ms,
            "error_message": error_message,
            "response_data": response_data or {},
            "endpoint_url": endpoint_url
        }
        
        return await self.create(health_check_data)
    
    async def record_metric(
        self,
        tenant_id: UUID,
        metric_name: str,
        metric_type: MetricType,
        value: float,
        unit: Optional[str] = None,
        labels: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        host: Optional[str] = None
    ) -> Metric:
        """Record a new metric value."""
        metric_data = {
            "tenant_id": tenant_id,
            "metric_name": metric_name,
            "metric_type": metric_type,
            "value": value,
            "unit": unit,
            "labels": labels or {},
            "source": source,
            "host": host,
            "timestamp": datetime.now(timezone.utc)
        }
        
        # Create metric using raw SQLAlchemy since it's a different model
        metric = Metric(**metric_data)
        self.db.add(metric)
        await self.db.flush()
        await self.db.refresh(metric)
        return metric
    
    async def create_alert(
        self,
        tenant_id: UUID,
        alert_name: str,
        alert_type: str,
        severity: AlertSeverity,
        title: str,
        description: Optional[str] = None,
        metric_name: Optional[str] = None,
        threshold_value: Optional[float] = None,
        current_value: Optional[float] = None,
        labels: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Create a new alert."""
        alert_data = {
            "tenant_id": tenant_id,
            "alert_name": alert_name,
            "alert_type": alert_type,
            "severity": severity,
            "title": title,
            "description": description,
            "metric_name": metric_name,
            "threshold_value": threshold_value,
            "current_value": current_value,
            "labels": labels or {}
        }
        
        alert = Alert(**alert_data)
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)
        return alert
    
    async def resolve_alert(self, alert_id: UUID, user_id: Optional[UUID] = None) -> bool:
        """Resolve an active alert."""
        query = select(Alert).where(Alert.id == alert_id)
        result = await self.db.execute(query)
        alert = result.scalars().first()
        
        if alert:
            alert.resolve(str(user_id) if user_id else None)
            await self.db.flush()
            return True
        return False
    
    async def get_tenant_alert_summary(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get alert summary for a tenant."""
        query = select(
            Alert.severity,
            Alert.status,
            func.count(Alert.id).label('count')
        ).where(
            Alert.tenant_id == tenant_id
        ).group_by(Alert.severity, Alert.status)
        
        result = await self.db.execute(query)
        summary = {}
        
        for row in result:
            severity_key = row.severity.value if hasattr(row.severity, 'value') else str(row.severity)
            status_key = row.status.value if hasattr(row.status, 'value') else str(row.status)
            
            if severity_key not in summary:
                summary[severity_key] = {}
            summary[severity_key][status_key] = row.count
        
        return summary


class HealthCheckRepository(BaseRepository[HealthCheck]):
    """Repository for health check operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, HealthCheck)


class MetricRepository(BaseRepository[Metric]):
    """Repository for metric operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Metric)
    
    async def get_metrics_aggregate(
        self,
        tenant_id: UUID,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        aggregation: str = "avg"  # avg, sum, min, max, count
    ) -> Optional[float]:
        """Get aggregated metric value for a time range."""
        agg_func = {
            "avg": func.avg,
            "sum": func.sum,
            "min": func.min,
            "max": func.max,
            "count": func.count
        }.get(aggregation, func.avg)
        
        query = select(agg_func(Metric.value)).where(
            and_(
                Metric.tenant_id == tenant_id,
                Metric.metric_name == metric_name,
                Metric.timestamp >= start_time,
                Metric.timestamp <= end_time
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar()


class AlertRepository(BaseRepository[Alert]):
    """Repository for alert operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Alert)
    
    async def get_alert_history(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get alert history for a date range."""
        query = select(Alert).where(
            and_(
                Alert.tenant_id == tenant_id,
                Alert.first_triggered_at >= start_date,
                Alert.first_triggered_at <= end_date
            )
        ).order_by(desc(Alert.first_triggered_at))
        
        if severity:
            query = query.where(Alert.severity == severity)
        
        result = await self.db.execute(query)
        return result.scalars().all()


class SLARecordRepository(BaseRepository[SLARecord]):
    """Repository for SLA record operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, SLARecord)
    
    async def get_sla_history(
        self,
        tenant_id: UUID,
        period_type: str = "monthly",
        limit: int = 12
    ) -> List[SLARecord]:
        """Get SLA history for a tenant."""
        query = select(SLARecord).where(
            and_(
                SLARecord.tenant_id == tenant_id,
                SLARecord.period_type == period_type
            )
        ).order_by(desc(SLARecord.period_end)).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_sla_compliance_summary(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get SLA compliance summary for a tenant."""
        # Get last 12 monthly records
        sla_records = await self.get_sla_history(tenant_id, "monthly", 12)
        
        if not sla_records:
            return {
                "compliance_rate": 100.0,
                "average_uptime": 99.9,
                "average_response_time": 0,
                "total_incidents": 0,
                "total_downtime_minutes": 0
            }
        
        total_records = len(sla_records)
        compliant_records = len([r for r in sla_records if r.overall_sla_met])
        
        avg_uptime = sum(float(r.uptime_percentage) for r in sla_records) / total_records
        avg_response_time = sum(r.response_time_avg_ms for r in sla_records) / total_records
        total_incidents = sum(r.incident_count for r in sla_records)
        total_downtime = sum(r.total_downtime_minutes for r in sla_records)
        
        return {
            "compliance_rate": (compliant_records / total_records) * 100,
            "average_uptime": avg_uptime,
            "average_response_time": avg_response_time,
            "total_incidents": total_incidents,
            "total_downtime_minutes": total_downtime,
            "periods_analyzed": total_records
        }