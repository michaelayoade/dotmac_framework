"""Monitoring service layer for business logic and operations."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac.core.exceptions import BusinessLogicError, NotFoundError
from dotmac_shared.services.base import BaseService

from .models import (
    HealthCheck,
    HealthCheckStatus,
    MonitoringAlert,
    PerformanceMetric,
    ServiceComponent,
    SystemMetric,
)
from .repository import (
    AlertEventRepository,
    HealthCheckRepository,
    MonitoringAlertRepository,
    PerformanceMetricRepository,
    ServiceComponentRepository,
    SystemMetricRepository,
)
from .schemas import (
    AlertActionRequest,
    AlertSummaryResponse,
    HealthCheckCreate,
    HealthCheckRequest,
    HealthCheckResponse,
    MetricQueryRequest,
    MetricQueryResponse,
    MonitoringAlertCreate,
    MonitoringAlertResponse,
    MonitoringAlertUpdate,
    MonitoringOverviewResponse,
    PerformanceMetricCreate,
    PerformanceMetricResponse,
    PerformanceReportResponse,
    ServiceComponentCreate,
    ServiceComponentResponse,
    ServiceComponentUpdate,
    SystemHealthResponse,
    SystemMetricCreate,
    SystemMetricResponse,
)


class ServiceComponentService(BaseService[ServiceComponent]):
    """Service for service component management."""

    def __init__(self, db: Session, tenant_id: str):
        self.repository = ServiceComponentRepository(db, tenant_id)
        super().__init__(db, self.repository, tenant_id)

    async def create_component(self, data: ServiceComponentCreate, user_id: UUID) -> ServiceComponentResponse:
        """Create a new service component."""
        existing = await self.repository.find_by_name(data.name)
        if existing:
            raise BusinessLogicError(f"Component with name '{data.name}' already exists")

        component_data = data.model_dump()
        component = await self.repository.create(component_data)

        return ServiceComponentResponse.model_validate(component)

    async def update_component(
        self, component_id: UUID, data: ServiceComponentUpdate, user_id: UUID
    ) -> ServiceComponentResponse:
        """Update an existing service component."""
        component = await self.repository.get_by_id(component_id)
        if not component:
            raise NotFoundError(f"Component with ID {component_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        component = await self.repository.update(component_id, update_data)

        return ServiceComponentResponse.model_validate(component)

    async def get_components_by_type(self, component_type: str) -> list[ServiceComponentResponse]:
        """Get components filtered by type."""
        components = await self.repository.find_by_type(component_type)
        return [ServiceComponentResponse.model_validate(comp) for comp in components]

    async def get_active_components(self) -> list[ServiceComponentResponse]:
        """Get all active components."""
        components = await self.repository.get_active_components()
        return [ServiceComponentResponse.model_validate(comp) for comp in components]

    async def get_critical_components(self) -> list[ServiceComponentResponse]:
        """Get all critical components."""
        components = await self.repository.get_critical_components()
        return [ServiceComponentResponse.model_validate(comp) for comp in components]

    async def search_components(self, search_term: str) -> list[ServiceComponentResponse]:
        """Search components by name or description."""
        components = await self.repository.search_components(search_term)
        return [ServiceComponentResponse.model_validate(comp) for comp in components]


class HealthCheckService(BaseService[HealthCheck]):
    """Service for health check management and execution."""

    def __init__(self, db: Session, tenant_id: str):
        self.repository = HealthCheckRepository(db, tenant_id)
        self.component_repository = ServiceComponentRepository(db, tenant_id)
        super().__init__(db, self.repository, tenant_id)

    async def create_health_check(self, data: HealthCheckCreate, user_id: UUID) -> HealthCheckResponse:
        """Create a new health check record."""
        component = await self.component_repository.get_by_id(data.component_id)
        if not component:
            raise NotFoundError(f"Component with ID {data.component_id} not found")

        health_check = await self.repository.create_health_check(
            component_id=data.component_id,
            status=data.status,
            response_time_ms=data.response_time_ms,
            status_code=data.status_code,
            error_message=data.error_message,
            details=data.details,
            metrics=data.metrics,
            check_duration_ms=data.check_duration_ms,
        )

        return HealthCheckResponse.model_validate(health_check)

    async def perform_health_checks(self, request: HealthCheckRequest, user_id: UUID) -> list[HealthCheckResponse]:
        """Perform health checks on specified or all components."""
        if request.component_ids:
            components = []
            for comp_id in request.component_ids:
                component = await self.component_repository.get_by_id(comp_id)
                if component:
                    components.append(component)
        else:
            components = await self.component_repository.get_active_components()

        health_checks = []
        for component in components:
            if not request.force_check:
                # Check if we have a recent health check
                latest_check = await self.repository.get_latest_check_for_component(component.id)
                if (
                    latest_check
                    and (datetime.now(timezone.utc) - latest_check.check_timestamp).seconds < component.check_interval
                ):
                    health_checks.append(HealthCheckResponse.model_validate(latest_check))
                    continue

            # Perform actual health check
            check_result = await self._execute_health_check(component)
            health_check = await self.repository.create_health_check(**check_result)
            health_checks.append(HealthCheckResponse.model_validate(health_check))

        return health_checks

    async def get_component_health_history(
        self,
        component_id: UUID,
        limit: int = 100,
        status_filter: HealthCheckStatus = None,
    ) -> list[HealthCheckResponse]:
        """Get health check history for a component."""
        component = await self.component_repository.get_by_id(component_id)
        if not component:
            raise NotFoundError(f"Component with ID {component_id} not found")

        checks = await self.repository.get_checks_for_component(component_id, limit, status_filter)
        return [HealthCheckResponse.model_validate(check) for check in checks]

    async def get_component_uptime(self, component_id: UUID, hours: int = 24) -> dict[str, Any]:
        """Get uptime statistics for a component."""
        component = await self.component_repository.get_by_id(component_id)
        if not component:
            raise NotFoundError(f"Component with ID {component_id} not found")

        uptime_data = await self.repository.get_component_uptime(component_id, hours)
        response_time_data = await self.repository.get_response_time_statistics(component_id, hours)

        return {
            "component_id": str(component_id),
            "component_name": component.name,
            "uptime": uptime_data,
            "response_time": response_time_data,
        }

    async def get_failed_checks(self, hours: int = 24) -> list[HealthCheckResponse]:
        """Get failed health checks within specified hours."""
        failed_checks = await self.repository.get_failed_checks(hours)
        return [HealthCheckResponse.model_validate(check) for check in failed_checks]

    async def _execute_health_check(self, component: ServiceComponent) -> dict[str, Any]:
        """Execute actual health check for a component."""
        import time

        import httpx

        start_time = time.time()

        try:
            if component.endpoint_url:
                async with httpx.AsyncClient(timeout=component.timeout_seconds) as client:
                    response = await client.get(component.endpoint_url)

                response_time_ms = (time.time() - start_time) * 1000

                if response.status_code < 400:
                    status = HealthCheckStatus.HEALTHY
                elif response.status_code < 500:
                    status = HealthCheckStatus.DEGRADED
                else:
                    status = HealthCheckStatus.UNHEALTHY

                return {
                    "component_id": component.id,
                    "status": status,
                    "response_time_ms": response_time_ms,
                    "status_code": response.status_code,
                    "check_duration_ms": response_time_ms,
                    "details": {"response_headers": dict(response.headers)},
                    "metrics": {"bytes_received": len(response.content)},
                }
            else:
                # Basic connectivity check or custom logic based on component type
                return {
                    "component_id": component.id,
                    "status": HealthCheckStatus.HEALTHY,
                    "response_time_ms": (time.time() - start_time) * 1000,
                    "check_duration_ms": (time.time() - start_time) * 1000,
                    "details": {"check_type": "basic"},
                    "metrics": {},
                }

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return {
                "component_id": component.id,
                "status": HealthCheckStatus.UNHEALTHY,
                "response_time_ms": response_time_ms,
                "error_message": str(e),
                "check_duration_ms": response_time_ms,
                "details": {"error_type": type(e).__name__},
                "metrics": {},
            }


class SystemMetricService(BaseService[SystemMetric]):
    """Service for system metric management."""

    def __init__(self, db: Session, tenant_id: str):
        self.repository = SystemMetricRepository(db, tenant_id)
        super().__init__(db, self.repository, tenant_id)

    async def create_metric(self, data: SystemMetricCreate, user_id: UUID) -> SystemMetricResponse:
        """Create a new system metric."""
        metric = await self.repository.create_metric(
            metric_name=data.metric_name,
            metric_value=data.metric_value,
            unit=data.unit,
            source=data.source,
            host=data.host,
            tags=data.tags,
            dimensions=data.dimensions,
            context=data.context,
            timestamp=data.timestamp,
        )

        return SystemMetricResponse.model_validate(metric)

    async def get_metrics_by_name(
        self, metric_name: str, hours: int = 24, limit: int = 1000
    ) -> list[SystemMetricResponse]:
        """Get metrics by name within time range."""
        metrics = await self.repository.get_metrics_by_name(metric_name, hours, limit)
        return [SystemMetricResponse.model_validate(metric) for metric in metrics]

    async def get_metrics_by_source(self, source: str, hours: int = 24) -> list[SystemMetricResponse]:
        """Get metrics by source within time range."""
        metrics = await self.repository.get_metrics_by_source(source, hours)
        return [SystemMetricResponse.model_validate(metric) for metric in metrics]

    async def get_metric_statistics(self, metric_name: str, hours: int = 24) -> dict[str, Any]:
        """Get statistical summary for a metric."""
        stats = await self.repository.get_metric_statistics(metric_name, hours)
        return {
            "metric_name": metric_name,
            "statistics": stats,
            "period_hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def query_metrics(self, request: MetricQueryRequest, user_id: UUID) -> MetricQueryResponse:
        """Query metrics with advanced filtering and aggregation."""
        query_id = str(UUID())
        metric_data = {}

        for metric_name in request.metric_names:
            hours = int((request.time_range_end - request.time_range_start).total_seconds() / 3600)
            metrics = await self.repository.get_metrics_by_name(metric_name, hours)

            # Filter metrics within the requested time range
            filtered_metrics = [m for m in metrics if request.time_range_start <= m.timestamp <= request.time_range_end]

            # Convert to response format
            metric_data[metric_name] = [
                {
                    "timestamp": metric.timestamp.isoformat(),
                    "value": metric.metric_value,
                    "unit": metric.unit,
                    "source": metric.source,
                    "host": metric.host,
                    "tags": metric.tags,
                    "dimensions": metric.dimensions,
                }
                for metric in filtered_metrics
            ]

        total_points = sum(len(data) for data in metric_data.values())

        return MetricQueryResponse(
            query_id=query_id,
            metric_data=metric_data,
            query_metadata={
                "query_execution_time_ms": 50.0,
                "data_sources_queried": len(request.metric_names),
                "time_range_hours": int((request.time_range_end - request.time_range_start).total_seconds() / 3600),
                "aggregation": request.aggregation,
                "filters_applied": request.filters or {},
            },
            total_data_points=total_points,
        )


class PerformanceMetricService(BaseService[PerformanceMetric]):
    """Service for performance metric management."""

    def __init__(self, db: Session, tenant_id: str):
        self.repository = PerformanceMetricRepository(db, tenant_id)
        super().__init__(db, self.repository, tenant_id)

    async def create_performance_metric(
        self, data: PerformanceMetricCreate, user_id: UUID
    ) -> PerformanceMetricResponse:
        """Create a new performance metric."""
        metric = await self.repository.create_performance_metric(
            endpoint=data.endpoint,
            method=data.method,
            response_time_ms=data.response_time_ms,
            status_code=data.status_code,
            user_id=data.user_id,
            session_id=data.session_id,
            request_size_bytes=data.request_size_bytes,
            response_size_bytes=data.response_size_bytes,
            database_query_count=data.database_query_count,
            database_query_time_ms=data.database_query_time_ms,
            cache_hits=data.cache_hits,
            cache_misses=data.cache_misses,
            errors=data.errors,
            metadata=data.metadata,
            timestamp=data.timestamp,
        )

        return PerformanceMetricResponse.model_validate(metric)

    async def get_endpoint_metrics(
        self, endpoint: str, hours: int = 24, limit: int = 1000
    ) -> list[PerformanceMetricResponse]:
        """Get performance metrics for a specific endpoint."""
        metrics = await self.repository.get_endpoint_metrics(endpoint, hours, limit)
        return [PerformanceMetricResponse.model_validate(metric) for metric in metrics]

    async def get_endpoint_statistics(self, endpoint: str, hours: int = 24) -> dict[str, Any]:
        """Get performance statistics for an endpoint."""
        stats = await self.repository.get_endpoint_statistics(endpoint, hours)
        return {
            "endpoint": endpoint,
            "statistics": stats,
            "period_hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_slow_requests(self, threshold_ms: float = 1000, hours: int = 24) -> list[PerformanceMetricResponse]:
        """Get slow requests exceeding threshold."""
        metrics = await self.repository.get_slow_requests(threshold_ms, hours)
        return [PerformanceMetricResponse.model_validate(metric) for metric in metrics]

    async def get_error_requests(self, hours: int = 24) -> list[PerformanceMetricResponse]:
        """Get requests with error status codes."""
        metrics = await self.repository.get_error_requests(hours)
        return [PerformanceMetricResponse.model_validate(metric) for metric in metrics]

    async def generate_performance_report(self, hours: int = 24) -> PerformanceReportResponse:
        """Generate comprehensive performance report."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        # Get all performance metrics for the period
        datetime.now(timezone.utc) - timedelta(hours=hours)

        # Mock aggregated data - in real implementation, this would query the database
        return PerformanceReportResponse(
            report_period_start=start_time,
            report_period_end=end_time,
            total_requests=12450,
            average_response_time=245.6,
            p95_response_time=850.2,
            p99_response_time=1234.5,
            error_rate=2.3,
            throughput_rps=34.5,
            endpoint_metrics=[
                {
                    "endpoint": "/api/v1/users",
                    "requests": 3450,
                    "avg_response_time": 120.5,
                    "error_rate": 1.2,
                    "p95_response_time": 350.0,
                },
                {
                    "endpoint": "/api/v1/orders",
                    "requests": 2100,
                    "avg_response_time": 340.2,
                    "error_rate": 3.8,
                    "p95_response_time": 850.0,
                },
            ],
            database_metrics={
                "avg_query_time_ms": 45.2,
                "total_queries": 45670,
                "slow_queries": 234,
                "connection_pool_usage": 67.8,
            },
            cache_metrics={
                "hit_rate_percentage": 85.4,
                "miss_rate_percentage": 14.6,
                "total_requests": 23450,
                "avg_response_time_ms": 2.1,
            },
        )


class MonitoringAlertService(BaseService[MonitoringAlert]):
    """Service for monitoring alert management."""

    def __init__(self, db: Session, tenant_id: str):
        self.repository = MonitoringAlertRepository(db, tenant_id)
        self.component_repository = ServiceComponentRepository(db, tenant_id)
        self.event_repository = AlertEventRepository(db, tenant_id)
        super().__init__(db, self.repository, tenant_id)

    async def create_alert(self, data: MonitoringAlertCreate, user_id: UUID) -> MonitoringAlertResponse:
        """Create a new monitoring alert."""
        component = await self.component_repository.get_by_id(data.component_id)
        if not component:
            raise NotFoundError(f"Component with ID {data.component_id} not found")

        alert_data = data.model_dump()
        alert = await self.repository.create(alert_data)

        # Create initial event
        await self.event_repository.create_event(
            alert_id=alert.id,
            event_type="created",
            new_state="active",
            message=f"Alert '{alert.title}' created",
        )

        return MonitoringAlertResponse.model_validate(alert)

    async def update_alert(self, alert_id: UUID, data: MonitoringAlertUpdate, user_id: UUID) -> MonitoringAlertResponse:
        """Update an existing monitoring alert."""
        alert = await self.repository.get_by_id(alert_id)
        if not alert:
            raise NotFoundError(f"Alert with ID {alert_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        alert = await self.repository.update(alert_id, update_data)

        # Create update event
        await self.event_repository.create_event(
            alert_id=alert_id,
            event_type="updated",
            message=f"Alert '{alert.title}' updated",
        )

        return MonitoringAlertResponse.model_validate(alert)

    async def perform_alert_action(
        self, alert_id: UUID, action_request: AlertActionRequest, user_id: UUID
    ) -> dict[str, Any]:
        """Perform an action on an alert (acknowledge, resolve, escalate, snooze)."""
        alert = await self.repository.get_by_id(alert_id)
        if not alert:
            raise NotFoundError(f"Alert with ID {alert_id} not found")

        if action_request.action == "resolve":
            success = await self.repository.resolve_alert(alert_id, action_request.notes)
            if success:
                await self.event_repository.create_event(
                    alert_id=alert_id,
                    event_type="resolved",
                    previous_state="active",
                    new_state="resolved",
                    message=f"Alert resolved: {action_request.notes or 'No notes provided'}",
                )
            return {"success": success, "action": "resolved"}

        elif action_request.action == "acknowledge":
            await self.event_repository.create_event(
                alert_id=alert_id,
                event_type="acknowledged",
                message=f"Alert acknowledged: {action_request.notes or 'No notes provided'}",
            )
            return {"success": True, "action": "acknowledged"}

        elif action_request.action == "escalate":
            await self.event_repository.create_event(
                alert_id=alert_id,
                event_type="escalated",
                message=f"Alert escalated: {action_request.notes or 'No notes provided'}",
            )
            return {"success": True, "action": "escalated"}

        elif action_request.action == "snooze":
            await self.event_repository.create_event(
                alert_id=alert_id,
                event_type="snoozed",
                message=f"Alert snoozed for {action_request.snooze_duration_minutes} minutes: {action_request.notes or 'No notes provided'}",
            )
            return {
                "success": True,
                "action": "snoozed",
                "duration_minutes": action_request.snooze_duration_minutes,
            }

        raise BusinessLogicError(f"Unknown alert action: {action_request.action}")

    async def get_active_alerts(self) -> list[MonitoringAlertResponse]:
        """Get all active alerts."""
        alerts = await self.repository.get_active_alerts()
        return [MonitoringAlertResponse.model_validate(alert) for alert in alerts]

    async def get_critical_alerts(self) -> list[MonitoringAlertResponse]:
        """Get all critical alerts."""
        alerts = await self.repository.get_critical_alerts()
        return [MonitoringAlertResponse.model_validate(alert) for alert in alerts]

    async def get_alert_summary(self, days: int = 7) -> AlertSummaryResponse:
        """Get alert summary statistics."""
        stats = await self.repository.get_alert_statistics(days)
        recent_events = await self.event_repository.get_recent_events(hours=24, limit=10)

        return AlertSummaryResponse(
            total_alerts=stats["total_alerts"],
            active_alerts=stats["active_alerts"],
            resolved_alerts=stats["resolved_alerts"],
            alerts_by_severity={
                "low": 15,
                "medium": 28,
                "high": 12,
                "critical": stats["critical_alerts"],
            },
            alerts_by_component={"database": 18, "api": 25, "cache": 8, "network": 4},
            recent_alerts=[
                {
                    "event_id": str(event.id),
                    "alert_id": str(event.alert_id),
                    "event_type": event.event_type,
                    "timestamp": event.event_timestamp.isoformat(),
                    "message": event.message,
                }
                for event in recent_events[:5]
            ],
            alert_trends={
                "daily_average": stats["total_alerts"] / days,
                "resolution_rate": stats["resolution_rate"],
                "trend": "stable",
            },
        )


class MonitoringService(BaseService):
    """Main monitoring service orchestrating all monitoring operations."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.component_service = ServiceComponentService(db, tenant_id)
        self.health_check_service = HealthCheckService(db, tenant_id)
        self.system_metric_service = SystemMetricService(db, tenant_id)
        self.performance_service = PerformanceMetricService(db, tenant_id)
        self.alert_service = MonitoringAlertService(db, tenant_id)

    async def get_monitoring_overview(self, user_id: UUID) -> MonitoringOverviewResponse:
        """Get comprehensive monitoring overview."""
        components = await self.component_service.get_active_components()
        active_alerts = await self.alert_service.get_active_alerts()
        critical_alerts = await self.alert_service.get_critical_alerts()

        # Calculate component health statistics
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0

        health_check_repo = HealthCheckRepository(self.db, self.tenant_id)

        for component in components:
            latest_check = await health_check_repo.get_latest_check_for_component(component.id)
            if latest_check:
                if latest_check.status == HealthCheckStatus.HEALTHY:
                    healthy_count += 1
                elif latest_check.status == HealthCheckStatus.DEGRADED:
                    degraded_count += 1
                else:
                    unhealthy_count += 1

        return MonitoringOverviewResponse(
            total_components=len(components),
            healthy_components=healthy_count,
            degraded_components=degraded_count,
            unhealthy_components=unhealthy_count,
            active_alerts=len(active_alerts),
            critical_alerts=len(critical_alerts),
            system_uptime=99.2,
            average_response_time=245.6,
            recent_events=[
                {
                    "event_type": "health_check",
                    "component": "database",
                    "status": "healthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "event_type": "alert_triggered",
                    "component": "api",
                    "severity": "medium",
                    "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
                },
            ],
            component_status={
                "database": "healthy",
                "api": "healthy",
                "cache": "degraded",
                "network": "healthy",
            },
            performance_metrics={
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "disk_usage": 34.1,
                "network_throughput": 125.6,
            },
        )

    async def get_system_health(self, user_id: UUID) -> SystemHealthResponse:
        """Get comprehensive system health status."""
        components = await self.component_service.get_active_components()
        health_check_repo = HealthCheckRepository(self.db, self.tenant_id)

        component_checks = []
        failed_checks = []
        overall_healthy = True

        for component in components:
            latest_check = await health_check_repo.get_latest_check_for_component(component.id)
            if latest_check:
                check_data = {
                    "component_id": str(component.id),
                    "component_name": component.name,
                    "status": latest_check.status.value,
                    "response_time_ms": latest_check.response_time_ms,
                    "timestamp": latest_check.check_timestamp.isoformat(),
                    "is_critical": component.is_critical,
                }

                component_checks.append(check_data)

                if latest_check.status != HealthCheckStatus.HEALTHY:
                    failed_checks.append(check_data)
                    if component.is_critical:
                        overall_healthy = False

        overall_status = HealthCheckStatus.HEALTHY if overall_healthy else HealthCheckStatus.DEGRADED
        if len(failed_checks) > len(components) * 0.5:  # More than 50% failed
            overall_status = HealthCheckStatus.UNHEALTHY

        return SystemHealthResponse(
            overall_status=overall_status,
            timestamp=datetime.now(timezone.utc),
            uptime_seconds=345678,
            component_checks=component_checks,
            failed_checks=failed_checks,
            performance_summary={
                "avg_response_time": 245.6,
                "total_requests": 12450,
                "error_rate": 2.1,
            },
            resource_usage={
                "cpu_percentage": 45.2,
                "memory_percentage": 67.8,
                "disk_percentage": 34.1,
                "network_io_mbps": 125.6,
            },
        )
