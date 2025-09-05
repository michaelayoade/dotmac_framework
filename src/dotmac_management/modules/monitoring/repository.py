"""Monitoring repository for data access operations."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from dotmac_shared.db.repositories import BaseRepository

from .models import (
    AlertEvent,
    HealthCheck,
    HealthCheckStatus,
    MetricThreshold,
    MonitoringAlert,
    MonitoringDashboard,
    PerformanceMetric,
    ServiceComponent,
    SystemMetric,
)


class ServiceComponentRepository(BaseRepository[ServiceComponent]):
    """Repository for service component operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, ServiceComponent, tenant_id)

    async def find_by_name(self, name: str) -> Optional[ServiceComponent]:
        """Find component by name within tenant."""
        return (
            self.db.query(ServiceComponent)
            .filter(
                and_(
                    ServiceComponent.tenant_id == self.tenant_id,
                    ServiceComponent.name == name,
                )
            )
            .first()
        )

    async def find_by_type(self, component_type: str) -> list[ServiceComponent]:
        """Find components by type."""
        return (
            self.db.query(ServiceComponent)
            .filter(
                and_(
                    ServiceComponent.tenant_id == self.tenant_id,
                    ServiceComponent.component_type == component_type,
                    ServiceComponent.is_active is True,
                )
            )
            .all()
        )

    async def get_active_components(self) -> list[ServiceComponent]:
        """Get all active components."""
        return (
            self.db.query(ServiceComponent)
            .filter(
                and_(
                    ServiceComponent.tenant_id == self.tenant_id,
                    ServiceComponent.is_active is True,
                )
            )
            .all()
        )

    async def get_critical_components(self) -> list[ServiceComponent]:
        """Get all critical components."""
        return (
            self.db.query(ServiceComponent)
            .filter(
                and_(
                    ServiceComponent.tenant_id == self.tenant_id,
                    ServiceComponent.is_critical is True,
                    ServiceComponent.is_active is True,
                )
            )
            .all()
        )

    async def get_components_with_health_checks(
        self, limit: int = 100
    ) -> list[ServiceComponent]:
        """Get components with their latest health checks."""
        return (
            self.db.query(ServiceComponent)
            .options(joinedload(ServiceComponent.health_checks))
            .filter(ServiceComponent.tenant_id == self.tenant_id)
            .limit(limit)
            .all()
        )

    async def search_components(self, search_term: str) -> list[ServiceComponent]:
        """Search components by name or description."""
        return (
            self.db.query(ServiceComponent)
            .filter(
                and_(
                    ServiceComponent.tenant_id == self.tenant_id,
                    or_(
                        ServiceComponent.name.ilike(f"%{search_term}%"),
                        ServiceComponent.description.ilike(f"%{search_term}%"),
                    ),
                )
            )
            .all()
        )


class HealthCheckRepository(BaseRepository[HealthCheck]):
    """Repository for health check operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, HealthCheck, tenant_id)

    async def create_health_check(
        self,
        component_id: UUID,
        status: HealthCheckStatus,
        response_time_ms: Optional[float] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        metrics: Optional[dict[str, Any]] = None,
        check_duration_ms: Optional[float] = None,
    ) -> HealthCheck:
        """Create a new health check record."""
        health_check = HealthCheck(
            tenant_id=self.tenant_id,
            component_id=component_id,
            status=status,
            response_time_ms=response_time_ms,
            status_code=status_code,
            error_message=error_message,
            details=details or {},
            metrics=metrics or {},
            check_duration_ms=check_duration_ms,
        )
        self.db.add(health_check)
        self.db.commit()
        self.db.refresh(health_check)
        return health_check

    async def get_latest_check_for_component(
        self, component_id: UUID
    ) -> Optional[HealthCheck]:
        """Get the latest health check for a component."""
        return (
            self.db.query(HealthCheck)
            .filter(
                and_(
                    HealthCheck.tenant_id == self.tenant_id,
                    HealthCheck.component_id == component_id,
                )
            )
            .order_by(desc(HealthCheck.check_timestamp))
            .first()
        )

    async def get_checks_for_component(
        self,
        component_id: UUID,
        limit: int = 100,
        status_filter: HealthCheckStatus = None,
    ) -> list[HealthCheck]:
        """Get health checks for a specific component."""
        query = self.db.query(HealthCheck).filter(
            and_(
                HealthCheck.tenant_id == self.tenant_id,
                HealthCheck.component_id == component_id,
            )
        )

        if status_filter:
            query = query.filter(HealthCheck.status == status_filter)

        return query.order_by(desc(HealthCheck.check_timestamp)).limit(limit).all()

    async def get_failed_checks(self, hours: int = 24) -> list[HealthCheck]:
        """Get failed health checks within specified hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (
            self.db.query(HealthCheck)
            .filter(
                and_(
                    HealthCheck.tenant_id == self.tenant_id,
                    HealthCheck.status == HealthCheckStatus.UNHEALTHY,
                    HealthCheck.check_timestamp >= cutoff_time,
                )
            )
            .order_by(desc(HealthCheck.check_timestamp))
            .all()
        )

    async def get_component_uptime(
        self, component_id: UUID, hours: int = 24
    ) -> dict[str, Any]:
        """Calculate uptime percentage for a component."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        total_checks = (
            self.db.query(HealthCheck)
            .filter(
                and_(
                    HealthCheck.tenant_id == self.tenant_id,
                    HealthCheck.component_id == component_id,
                    HealthCheck.check_timestamp >= cutoff_time,
                )
            )
            .count()
        )

        healthy_checks = (
            self.db.query(HealthCheck)
            .filter(
                and_(
                    HealthCheck.tenant_id == self.tenant_id,
                    HealthCheck.component_id == component_id,
                    HealthCheck.check_timestamp >= cutoff_time,
                    HealthCheck.status == HealthCheckStatus.HEALTHY,
                )
            )
            .count()
        )

        uptime_percentage = (
            (healthy_checks / total_checks * 100) if total_checks > 0 else 0
        )

        return {
            "uptime_percentage": uptime_percentage,
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "failed_checks": total_checks - healthy_checks,
            "period_hours": hours,
        }

    async def get_response_time_statistics(
        self, component_id: UUID, hours: int = 24
    ) -> dict[str, float]:
        """Get response time statistics for a component."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = (
            self.db.query(
                func.avg(HealthCheck.response_time_ms).label("avg"),
                func.min(HealthCheck.response_time_ms).label("min"),
                func.max(HealthCheck.response_time_ms).label("max"),
                func.count(HealthCheck.response_time_ms).label("count"),
            )
            .filter(
                and_(
                    HealthCheck.tenant_id == self.tenant_id,
                    HealthCheck.component_id == component_id,
                    HealthCheck.check_timestamp >= cutoff_time,
                    HealthCheck.response_time_ms.isnot(None),
                )
            )
            .first()
        )

        return {
            "average_ms": float(result.avg or 0),
            "minimum_ms": float(result.min or 0),
            "maximum_ms": float(result.max or 0),
            "sample_count": int(result.count or 0),
        }


class SystemMetricRepository(BaseRepository[SystemMetric]):
    """Repository for system metric operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, SystemMetric, tenant_id)

    async def create_metric(
        self,
        metric_name: str,
        metric_value: float,
        unit: Optional[str] = None,
        source: Optional[str] = None,
        host: Optional[str] = None,
        tags: Optional[dict[str, Any]] = None,
        dimensions: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> SystemMetric:
        """Create a new system metric."""
        metric = SystemMetric(
            tenant_id=self.tenant_id,
            metric_name=metric_name,
            metric_value=metric_value,
            unit=unit,
            source=source,
            host=host,
            tags=tags or {},
            dimensions=dimensions or {},
            context=context or {},
            timestamp=timestamp or datetime.now(timezone.utc),
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    async def get_metrics_by_name(
        self, metric_name: str, hours: int = 24, limit: int = 1000
    ) -> list[SystemMetric]:
        """Get metrics by name within time range."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (
            self.db.query(SystemMetric)
            .filter(
                and_(
                    SystemMetric.tenant_id == self.tenant_id,
                    SystemMetric.metric_name == metric_name,
                    SystemMetric.timestamp >= cutoff_time,
                )
            )
            .order_by(desc(SystemMetric.timestamp))
            .limit(limit)
            .all()
        )

    async def get_metrics_by_source(
        self, source: str, hours: int = 24
    ) -> list[SystemMetric]:
        """Get metrics by source within time range."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (
            self.db.query(SystemMetric)
            .filter(
                and_(
                    SystemMetric.tenant_id == self.tenant_id,
                    SystemMetric.source == source,
                    SystemMetric.timestamp >= cutoff_time,
                )
            )
            .order_by(desc(SystemMetric.timestamp))
            .all()
        )

    async def get_metric_statistics(
        self, metric_name: str, hours: int = 24
    ) -> dict[str, float]:
        """Get statistical summary for a metric."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = (
            self.db.query(
                func.avg(SystemMetric.metric_value).label("avg"),
                func.min(SystemMetric.metric_value).label("min"),
                func.max(SystemMetric.metric_value).label("max"),
                func.count(SystemMetric.metric_value).label("count"),
            )
            .filter(
                and_(
                    SystemMetric.tenant_id == self.tenant_id,
                    SystemMetric.metric_name == metric_name,
                    SystemMetric.timestamp >= cutoff_time,
                )
            )
            .first()
        )

        return {
            "average": float(result.avg or 0),
            "minimum": float(result.min or 0),
            "maximum": float(result.max or 0),
            "count": int(result.count or 0),
        }

    async def get_latest_metrics_by_host(self, host: str) -> list[SystemMetric]:
        """Get latest metrics for a specific host."""
        return (
            self.db.query(SystemMetric)
            .filter(
                and_(
                    SystemMetric.tenant_id == self.tenant_id, SystemMetric.host == host
                )
            )
            .order_by(desc(SystemMetric.timestamp))
            .all()
        )


class PerformanceMetricRepository(BaseRepository[PerformanceMetric]):
    """Repository for performance metric operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, PerformanceMetric, tenant_id)

    async def create_performance_metric(
        self,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        request_size_bytes: Optional[int] = None,
        response_size_bytes: Optional[int] = None,
        database_query_count: Optional[int] = None,
        database_query_time_ms: Optional[float] = None,
        cache_hits: int = 0,
        cache_misses: int = 0,
        errors: Optional[list[dict[str, Any]]] = None,
        metadata: Optional[dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> PerformanceMetric:
        """Create a new performance metric."""
        metric = PerformanceMetric(
            tenant_id=self.tenant_id,
            endpoint=endpoint,
            method=method,
            response_time_ms=response_time_ms,
            status_code=status_code,
            user_id=user_id,
            session_id=session_id,
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
            database_query_count=database_query_count,
            database_query_time_ms=database_query_time_ms,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            errors=errors or [],
            metadata=metadata or {},
            timestamp=timestamp or datetime.now(timezone.utc),
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    async def get_endpoint_metrics(
        self, endpoint: str, hours: int = 24, limit: int = 1000
    ) -> list[PerformanceMetric]:
        """Get performance metrics for a specific endpoint."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (
            self.db.query(PerformanceMetric)
            .filter(
                and_(
                    PerformanceMetric.tenant_id == self.tenant_id,
                    PerformanceMetric.endpoint == endpoint,
                    PerformanceMetric.timestamp >= cutoff_time,
                )
            )
            .order_by(desc(PerformanceMetric.timestamp))
            .limit(limit)
            .all()
        )

    async def get_endpoint_statistics(
        self, endpoint: str, hours: int = 24
    ) -> dict[str, Any]:
        """Get performance statistics for an endpoint."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = (
            self.db.query(
                func.avg(PerformanceMetric.response_time_ms).label("avg_response_time"),
                func.min(PerformanceMetric.response_time_ms).label("min_response_time"),
                func.max(PerformanceMetric.response_time_ms).label("max_response_time"),
                func.count(PerformanceMetric.id).label("total_requests"),
                func.count(
                    func.nullif(PerformanceMetric.status_code >= 400, False)
                ).label("error_count"),
                func.avg(PerformanceMetric.database_query_time_ms).label("avg_db_time"),
                func.sum(PerformanceMetric.cache_hits).label("total_cache_hits"),
                func.sum(PerformanceMetric.cache_misses).label("total_cache_misses"),
            )
            .filter(
                and_(
                    PerformanceMetric.tenant_id == self.tenant_id,
                    PerformanceMetric.endpoint == endpoint,
                    PerformanceMetric.timestamp >= cutoff_time,
                )
            )
            .first()
        )

        total_requests = int(result.total_requests or 0)
        error_count = int(result.error_count or 0)
        cache_hits = int(result.total_cache_hits or 0)
        cache_misses = int(result.total_cache_misses or 0)

        return {
            "average_response_time_ms": float(result.avg_response_time or 0),
            "min_response_time_ms": float(result.min_response_time or 0),
            "max_response_time_ms": float(result.max_response_time or 0),
            "total_requests": total_requests,
            "error_rate_percentage": (error_count / total_requests * 100)
            if total_requests > 0
            else 0,
            "requests_per_hour": total_requests / hours if hours > 0 else 0,
            "average_db_time_ms": float(result.avg_db_time or 0),
            "cache_hit_rate": (cache_hits / (cache_hits + cache_misses) * 100)
            if (cache_hits + cache_misses) > 0
            else 0,
        }

    async def get_slow_requests(
        self, threshold_ms: float = 1000, hours: int = 24
    ) -> list[PerformanceMetric]:
        """Get slow requests exceeding threshold."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (
            self.db.query(PerformanceMetric)
            .filter(
                and_(
                    PerformanceMetric.tenant_id == self.tenant_id,
                    PerformanceMetric.response_time_ms >= threshold_ms,
                    PerformanceMetric.timestamp >= cutoff_time,
                )
            )
            .order_by(desc(PerformanceMetric.response_time_ms))
            .all()
        )

    async def get_error_requests(self, hours: int = 24) -> list[PerformanceMetric]:
        """Get requests with error status codes."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (
            self.db.query(PerformanceMetric)
            .filter(
                and_(
                    PerformanceMetric.tenant_id == self.tenant_id,
                    PerformanceMetric.status_code >= 400,
                    PerformanceMetric.timestamp >= cutoff_time,
                )
            )
            .order_by(desc(PerformanceMetric.timestamp))
            .all()
        )


class MonitoringAlertRepository(BaseRepository[MonitoringAlert]):
    """Repository for monitoring alert operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, MonitoringAlert, tenant_id)

    async def find_by_component(self, component_id: UUID) -> list[MonitoringAlert]:
        """Find alerts by component ID."""
        return (
            self.db.query(MonitoringAlert)
            .filter(
                and_(
                    MonitoringAlert.tenant_id == self.tenant_id,
                    MonitoringAlert.component_id == component_id,
                )
            )
            .all()
        )

    async def get_active_alerts(self) -> list[MonitoringAlert]:
        """Get all active (unresolved) alerts."""
        return (
            self.db.query(MonitoringAlert)
            .filter(
                and_(
                    MonitoringAlert.tenant_id == self.tenant_id,
                    MonitoringAlert.is_active is True,
                    MonitoringAlert.is_resolved is False,
                )
            )
            .order_by(desc(MonitoringAlert.triggered_at))
            .all()
        )

    async def get_critical_alerts(self) -> list[MonitoringAlert]:
        """Get all critical alerts."""
        return (
            self.db.query(MonitoringAlert)
            .filter(
                and_(
                    MonitoringAlert.tenant_id == self.tenant_id,
                    MonitoringAlert.severity == "critical",
                    MonitoringAlert.is_resolved is False,
                )
            )
            .order_by(desc(MonitoringAlert.triggered_at))
            .all()
        )

    async def resolve_alert(
        self, alert_id: UUID, resolution_notes: Optional[str] = None
    ) -> bool:
        """Mark an alert as resolved."""
        result = (
            self.db.query(MonitoringAlert)
            .filter(
                and_(
                    MonitoringAlert.tenant_id == self.tenant_id,
                    MonitoringAlert.id == alert_id,
                )
            )
            .update(
                {
                    MonitoringAlert.is_resolved: True,
                    MonitoringAlert.resolved_at: datetime.now(timezone.utc),
                    MonitoringAlert.resolution_notes: resolution_notes,
                    MonitoringAlert.is_active: False,
                }
            )
        )

        self.db.commit()
        return result > 0

    async def get_alert_statistics(self, days: int = 7) -> dict[str, Any]:
        """Get alert statistics for the specified period."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

        total_alerts = (
            self.db.query(MonitoringAlert)
            .filter(
                and_(
                    MonitoringAlert.tenant_id == self.tenant_id,
                    MonitoringAlert.triggered_at >= cutoff_time,
                )
            )
            .count()
        )

        active_alerts = (
            self.db.query(MonitoringAlert)
            .filter(
                and_(
                    MonitoringAlert.tenant_id == self.tenant_id,
                    MonitoringAlert.is_active is True,
                    MonitoringAlert.is_resolved is False,
                )
            )
            .count()
        )

        critical_alerts = (
            self.db.query(MonitoringAlert)
            .filter(
                and_(
                    MonitoringAlert.tenant_id == self.tenant_id,
                    MonitoringAlert.severity == "critical",
                    MonitoringAlert.triggered_at >= cutoff_time,
                )
            )
            .count()
        )

        resolved_alerts = (
            self.db.query(MonitoringAlert)
            .filter(
                and_(
                    MonitoringAlert.tenant_id == self.tenant_id,
                    MonitoringAlert.is_resolved is True,
                    MonitoringAlert.resolved_at >= cutoff_time,
                )
            )
            .count()
        )

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "resolved_alerts": resolved_alerts,
            "critical_alerts": critical_alerts,
            "resolution_rate": (resolved_alerts / total_alerts * 100)
            if total_alerts > 0
            else 0,
            "period_days": days,
        }


class AlertEventRepository(BaseRepository[AlertEvent]):
    """Repository for alert event operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, AlertEvent, tenant_id)

    async def create_event(
        self,
        alert_id: UUID,
        event_type: str,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        metric_value: Optional[float] = None,
        threshold_value: Optional[float] = None,
        message: Optional[str] = None,
        notification_sent: bool = False,
        notification_channels: Optional[list[str]] = None,
        event_context: Optional[dict[str, Any]] = None,
    ) -> AlertEvent:
        """Create a new alert event."""
        event = AlertEvent(
            tenant_id=self.tenant_id,
            alert_id=alert_id,
            event_type=event_type,
            previous_state=previous_state,
            new_state=new_state,
            metric_value=metric_value,
            threshold_value=threshold_value,
            message=message,
            notification_sent=notification_sent,
            notification_channels=notification_channels or [],
            event_context=event_context or {},
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    async def get_events_for_alert(
        self, alert_id: UUID, limit: int = 100
    ) -> list[AlertEvent]:
        """Get events for a specific alert."""
        return (
            self.db.query(AlertEvent)
            .filter(
                and_(
                    AlertEvent.tenant_id == self.tenant_id,
                    AlertEvent.alert_id == alert_id,
                )
            )
            .order_by(desc(AlertEvent.event_timestamp))
            .limit(limit)
            .all()
        )

    async def get_recent_events(
        self, hours: int = 24, limit: int = 100
    ) -> list[AlertEvent]:
        """Get recent alert events."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (
            self.db.query(AlertEvent)
            .filter(
                and_(
                    AlertEvent.tenant_id == self.tenant_id,
                    AlertEvent.event_timestamp >= cutoff_time,
                )
            )
            .order_by(desc(AlertEvent.event_timestamp))
            .limit(limit)
            .all()
        )


class MonitoringDashboardRepository(BaseRepository[MonitoringDashboard]):
    """Repository for monitoring dashboard operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, MonitoringDashboard, tenant_id)

    async def find_by_name(self, name: str) -> Optional[MonitoringDashboard]:
        """Find dashboard by name within tenant."""
        return (
            self.db.query(MonitoringDashboard)
            .filter(
                and_(
                    MonitoringDashboard.tenant_id == self.tenant_id,
                    MonitoringDashboard.name == name,
                )
            )
            .first()
        )

    async def get_public_dashboards(self) -> list[MonitoringDashboard]:
        """Get all public dashboards."""
        return (
            self.db.query(MonitoringDashboard)
            .filter(
                and_(
                    MonitoringDashboard.tenant_id == self.tenant_id,
                    MonitoringDashboard.is_public is True,
                )
            )
            .all()
        )

    async def get_default_dashboard(self) -> Optional[MonitoringDashboard]:
        """Get the default dashboard."""
        return (
            self.db.query(MonitoringDashboard)
            .filter(
                and_(
                    MonitoringDashboard.tenant_id == self.tenant_id,
                    MonitoringDashboard.is_default is True,
                )
            )
            .first()
        )

    async def set_as_default(self, dashboard_id: UUID) -> bool:
        """Set a dashboard as the default."""
        # First, unset any existing default
        self.db.query(MonitoringDashboard).filter(
            and_(
                MonitoringDashboard.tenant_id == self.tenant_id,
                MonitoringDashboard.is_default is True,
            )
        ).update({MonitoringDashboard.is_default: False})

        # Set the new default
        result = (
            self.db.query(MonitoringDashboard)
            .filter(
                and_(
                    MonitoringDashboard.tenant_id == self.tenant_id,
                    MonitoringDashboard.id == dashboard_id,
                )
            )
            .update({MonitoringDashboard.is_default: True})
        )

        self.db.commit()
        return result > 0


class MetricThresholdRepository(BaseRepository[MetricThreshold]):
    """Repository for metric threshold operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, MetricThreshold, tenant_id)

    async def find_by_metric_name(self, metric_name: str) -> list[MetricThreshold]:
        """Find thresholds by metric name."""
        return (
            self.db.query(MetricThreshold)
            .filter(
                and_(
                    MetricThreshold.tenant_id == self.tenant_id,
                    MetricThreshold.metric_name == metric_name,
                    MetricThreshold.is_active is True,
                )
            )
            .all()
        )

    async def find_by_component(self, component_id: UUID) -> list[MetricThreshold]:
        """Find thresholds by component ID."""
        return (
            self.db.query(MetricThreshold)
            .filter(
                and_(
                    MetricThreshold.tenant_id == self.tenant_id,
                    MetricThreshold.component_id == component_id,
                    MetricThreshold.is_active is True,
                )
            )
            .all()
        )

    async def get_active_thresholds(self) -> list[MetricThreshold]:
        """Get all active thresholds."""
        return (
            self.db.query(MetricThreshold)
            .filter(
                and_(
                    MetricThreshold.tenant_id == self.tenant_id,
                    MetricThreshold.is_active is True,
                )
            )
            .all()
        )

    async def evaluate_threshold(
        self, threshold: MetricThreshold, current_value: float
    ) -> tuple[bool, str]:
        """Evaluate if a threshold is breached."""
        operator = threshold.comparison_operator
        warning_threshold = threshold.warning_threshold
        critical_threshold = threshold.critical_threshold

        if operator == "gt":
            if critical_threshold and current_value > critical_threshold:
                return True, "critical"
            elif warning_threshold and current_value > warning_threshold:
                return True, "warning"
        elif operator == "lt":
            if critical_threshold and current_value < critical_threshold:
                return True, "critical"
            elif warning_threshold and current_value < warning_threshold:
                return True, "warning"
        elif operator == "gte":
            if critical_threshold and current_value >= critical_threshold:
                return True, "critical"
            elif warning_threshold and current_value >= warning_threshold:
                return True, "warning"
        elif operator == "lte":
            if critical_threshold and current_value <= critical_threshold:
                return True, "critical"
            elif warning_threshold and current_value <= warning_threshold:
                return True, "warning"
        elif operator == "eq":
            if critical_threshold and abs(current_value - critical_threshold) < 0.001:
                return True, "critical"
            elif warning_threshold and abs(current_value - warning_threshold) < 0.001:
                return True, "warning"
        elif operator == "ne":
            if critical_threshold and abs(current_value - critical_threshold) >= 0.001:
                return True, "critical"
            elif warning_threshold and abs(current_value - warning_threshold) >= 0.001:
                return True, "warning"

        return False, "ok"
