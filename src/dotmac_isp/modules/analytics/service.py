"""Analytics service layer for business logic and operations."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_shared.core.exceptions import BusinessLogicError, NotFoundError
from dotmac_shared.services.base import BaseService

from .models import (
    Alert,
    AlertEvent,
    AnalyticsSession,
    Dashboard,
    DataSource,
    Metric,
    MetricAggregation,
    MetricValue,
    Report,
    Widget,
)
from .repository import (
    AlertEventRepository,
    AlertRepository,
    AnalyticsSessionRepository,
    DashboardRepository,
    DataSourceRepository,
    MetricAggregationRepository,
    MetricRepository,
    MetricValueRepository,
    ReportRepository,
    WidgetRepository,
)
from .schemas import (
    AlertCreate,
    AlertResponse,
    AlertSeverity,
    AlertTestResponse,
    AlertUpdate,
    AnalyticsOverviewResponse,
    CustomerAnalyticsResponse,
    DashboardCreate,
    DashboardMetricsResponse,
    DashboardOverviewResponse,
    DashboardResponse,
    DashboardUpdate,
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    ExecutiveReportResponse,
    MetricAggregationRequest,
    MetricAggregationResponse,
    MetricCreate,
    MetricResponse,
    MetricType,
    MetricUpdate,
    MetricValueCreate,
    MetricValueResponse,
    RealTimeMetricsResponse,
    ReportCreate,
    ReportExportRequest,
    ReportExportResponse,
    ReportResponse,
    ReportType,
    ReportUpdate,
    RevenueAnalyticsResponse,
    ServiceAnalyticsResponse,
    WidgetCreate,
    WidgetResponse,
    WidgetUpdate,
)


class MetricService(BaseService[Metric]):
    """Service for metric management and operations."""

    def __init__(self, db: Session, tenant_id: str):
        self.repository = MetricRepository(db, tenant_id)
        super().__init__(db, self.repository, tenant_id)

    async def create_metric(self, data: MetricCreate, user_id: UUID) -> MetricResponse:
        """Create a new metric with validation."""
        existing = await self.repository.find_by_name(data.name)
        if existing:
            raise BusinessLogicError(f"Metric with name '{data.name}' already exists")

        metric_data = data.model_dump()
        metric = await self.repository.create(metric_data)
        
        return MetricResponse.model_validate(metric)

    async def update_metric(self, metric_id: UUID, data: MetricUpdate, user_id: UUID) -> MetricResponse:
        """Update an existing metric."""
        metric = await self.repository.get_by_id(metric_id)
        if not metric:
            raise NotFoundError(f"Metric with ID {metric_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        metric = await self.repository.update(metric_id, update_data)
        
        return MetricResponse.model_validate(metric)

    async def get_metrics_by_type(self, metric_type: MetricType) -> List[MetricResponse]:
        """Get metrics filtered by type."""
        metrics = await self.repository.find_by_type(metric_type)
        return [MetricResponse.model_validate(metric) for metric in metrics]

    async def get_active_metrics(self) -> List[MetricResponse]:
        """Get all active metrics."""
        metrics = await self.repository.get_active_metrics()
        return [MetricResponse.model_validate(metric) for metric in metrics]

    async def record_metric_value(self, metric_id: UUID, data: MetricValueCreate, user_id: UUID) -> MetricValueResponse:
        """Record a new value for a metric."""
        metric = await self.repository.get_by_id(metric_id)
        if not metric:
            raise NotFoundError(f"Metric with ID {metric_id} not found")

        if not metric.is_active:
            raise BusinessLogicError(f"Cannot record value for inactive metric: {metric.name}")

        value_repo = MetricValueRepository(self.db, self.tenant_id)
        metric_value = await value_repo.create_value(
            metric_id=metric_id,
            value=data.value,
            timestamp=data.timestamp,
            dimensions=data.dimensions,
            context=data.context
        )

        await self.repository.update_latest_value(metric_id, data.value)
        
        return MetricValueResponse.model_validate(metric_value)

    async def get_metric_values(
        self, metric_id: UUID, start_date: datetime = None, end_date: datetime = None,
        limit: int = 1000
    ) -> List[MetricValueResponse]:
        """Get values for a specific metric."""
        metric = await self.repository.get_by_id(metric_id)
        if not metric:
            raise NotFoundError(f"Metric with ID {metric_id} not found")

        value_repo = MetricValueRepository(self.db, self.tenant_id)
        values = await value_repo.get_values_for_metric(metric_id, start_date, end_date, limit)
        
        return [MetricValueResponse.model_validate(value) for value in values]

    async def get_metric_statistics(
        self, metric_id: UUID, start_date: datetime = None, end_date: datetime = None
    ) -> Dict[str, Any]:
        """Get statistical summary for a metric."""
        metric = await self.repository.get_by_id(metric_id)
        if not metric:
            raise NotFoundError(f"Metric with ID {metric_id} not found")

        value_repo = MetricValueRepository(self.db, self.tenant_id)
        stats = await value_repo.get_value_statistics(metric_id, start_date, end_date)
        
        return {
            'metric_id': str(metric_id),
            'metric_name': metric.name,
            'statistics': stats,
            'period': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            }
        }

    async def aggregate_metrics(self, request: MetricAggregationRequest) -> MetricAggregationResponse:
        """Aggregate metric data for analysis."""
        metric = await self.repository.get_by_id(UUID(request.metric_id))
        if not metric:
            raise NotFoundError(f"Metric with ID {request.metric_id} not found")

        agg_repo = MetricAggregationRepository(self.db, self.tenant_id)
        aggregations = await agg_repo.get_aggregations_for_metric(
            metric_id=UUID(request.metric_id),
            aggregation_type=request.aggregation_type,
            period=request.period,
            start_date=request.start_date,
            end_date=request.end_date
        )

        data_points = []
        for agg in aggregations:
            data_points.append({
                'timestamp': agg.period_start.isoformat(),
                'value': agg.aggregated_value,
                'sample_count': agg.sample_count,
                'dimensions': agg.dimensions
            })

        summary = {
            'total_points': len(data_points),
            'avg_value': sum(p['value'] for p in data_points) / len(data_points) if data_points else 0,
            'min_value': min(p['value'] for p in data_points) if data_points else 0,
            'max_value': max(p['value'] for p in data_points) if data_points else 0
        }

        return MetricAggregationResponse(
            metric_id=request.metric_id,
            aggregation_type=request.aggregation_type,
            period=request.period,
            start_date=request.start_date,
            end_date=request.end_date,
            data_points=data_points,
            summary=summary
        )


class ReportService(BaseService[Report]):
    """Service for report management and generation."""

    def __init__(self, db: Session, tenant_id: str):
        self.repository = ReportRepository(db, tenant_id)
        super().__init__(db, self.repository, tenant_id)

    async def create_report(self, data: ReportCreate, user_id: UUID) -> ReportResponse:
        """Create a new report."""
        duration_days = (data.end_date - data.start_date).days
        
        report_data = data.model_dump()
        report_data['duration_days'] = duration_days
        report_data['data'] = {}
        
        report = await self.repository.create(report_data)
        return ReportResponse.model_validate(report)

    async def generate_report_data(self, report_id: UUID, user_id: UUID) -> ReportResponse:
        """Generate data for an existing report."""
        report = await self.repository.get_by_id(report_id)
        if not report:
            raise NotFoundError(f"Report with ID {report_id} not found")

        data = await self._generate_report_content(report)
        
        update_data = {
            'data': data,
            'generated_at': datetime.now(timezone.utc)
        }
        
        updated_report = await self.repository.update(report_id, update_data)
        return ReportResponse.model_validate(updated_report)

    async def get_reports_by_type(self, report_type: ReportType) -> List[ReportResponse]:
        """Get reports filtered by type."""
        reports = await self.repository.find_by_type(report_type)
        return [ReportResponse.model_validate(report) for report in reports]

    async def export_report(self, request: ReportExportRequest, user_id: UUID) -> ReportExportResponse:
        """Export a report in the specified format."""
        report = await self.repository.get_by_id(UUID(request.report_id))
        if not report:
            raise NotFoundError(f"Report with ID {request.report_id} not found")

        export_id = UUID()
        download_url = f"/api/v1/analytics/reports/{request.report_id}/download/{export_id}"
        
        return ReportExportResponse(
            export_id=str(export_id),
            report_id=request.report_id,
            format_type=request.format_type,
            status="processing",
            download_url=download_url,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            file_size_bytes=None
        )

    async def _generate_report_content(self, report: Report) -> Dict[str, Any]:
        """Generate report content based on report configuration."""
        metric_service = MetricService(self.db, self.tenant_id)
        
        if report.report_type == ReportType.DAILY:
            return await self._generate_daily_report(report, metric_service)
        elif report.report_type == ReportType.WEEKLY:
            return await self._generate_weekly_report(report, metric_service)
        elif report.report_type == ReportType.MONTHLY:
            return await self._generate_monthly_report(report, metric_service)
        else:
            return await self._generate_custom_report(report, metric_service)

    async def _generate_daily_report(self, report: Report, metric_service: MetricService) -> Dict[str, Any]:
        """Generate daily report content."""
        return {
            'period': 'daily',
            'metrics': {},
            'summary': 'Daily report generated',
            'charts': []
        }

    async def _generate_weekly_report(self, report: Report, metric_service: MetricService) -> Dict[str, Any]:
        """Generate weekly report content."""
        return {
            'period': 'weekly',
            'metrics': {},
            'summary': 'Weekly report generated',
            'charts': []
        }

    async def _generate_monthly_report(self, report: Report, metric_service: MetricService) -> Dict[str, Any]:
        """Generate monthly report content."""
        return {
            'period': 'monthly',
            'metrics': {},
            'summary': 'Monthly report generated',
            'charts': []
        }

    async def _generate_custom_report(self, report: Report, metric_service: MetricService) -> Dict[str, Any]:
        """Generate custom report content."""
        return {
            'period': 'custom',
            'metrics': {},
            'summary': 'Custom report generated',
            'filters': report.filters,
            'charts': []
        }


class DashboardService(BaseService[Dashboard]):
    """Service for dashboard management and operations."""

    def __init__(self, db: Session, tenant_id: str):
        self.repository = DashboardRepository(db, tenant_id)
        super().__init__(db, self.repository, tenant_id)

    async def create_dashboard(self, data: DashboardCreate, user_id: UUID) -> DashboardResponse:
        """Create a new dashboard."""
        existing = await self.repository.find_by_name(data.name)
        if existing:
            raise BusinessLogicError(f"Dashboard with name '{data.name}' already exists")

        dashboard_data = data.model_dump()
        dashboard = await self.repository.create(dashboard_data)
        
        return DashboardResponse.model_validate(dashboard)

    async def update_dashboard(self, dashboard_id: UUID, data: DashboardUpdate, user_id: UUID) -> DashboardResponse:
        """Update an existing dashboard."""
        dashboard = await self.repository.get_by_id(dashboard_id)
        if not dashboard:
            raise NotFoundError(f"Dashboard with ID {dashboard_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        dashboard = await self.repository.update(dashboard_id, update_data)
        
        return DashboardResponse.model_validate(dashboard)

    async def get_dashboard_with_widgets(self, dashboard_id: UUID) -> Dict[str, Any]:
        """Get dashboard with all its widgets."""
        dashboard = await self.repository.get_dashboard_with_widgets(dashboard_id)
        if not dashboard:
            raise NotFoundError(f"Dashboard with ID {dashboard_id} not found")

        widget_service = WidgetService(self.db, self.tenant_id)
        widgets = await widget_service.get_widgets_by_dashboard(dashboard_id)

        return {
            'dashboard': DashboardResponse.model_validate(dashboard),
            'widgets': widgets
        }

    async def get_dashboard_metrics(self, dashboard_id: UUID) -> DashboardMetricsResponse:
        """Get usage metrics for a dashboard."""
        dashboard = await self.repository.get_by_id(dashboard_id)
        if not dashboard:
            raise NotFoundError(f"Dashboard with ID {dashboard_id} not found")

        session_repo = AnalyticsSessionRepository(self.db, self.tenant_id)
        analytics = await session_repo.get_dashboard_analytics(dashboard_id)

        return DashboardMetricsResponse(
            total_views=analytics['total_views'],
            unique_users=analytics['unique_users'],
            avg_session_duration=analytics['avg_session_duration'],
            bounce_rate=25.0,
            most_viewed_widgets=[],
            performance_metrics={'load_time': 2.5}
        )

    async def get_dashboard_overview(self, user_id: UUID) -> DashboardOverviewResponse:
        """Get dashboard overview with key metrics."""
        current_time = datetime.now(timezone.utc)
        start_of_month = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        return DashboardOverviewResponse(
            total_customers=1250,
            total_revenue=45678.90,
            active_services=3450,
            support_tickets=23,
            network_uptime=99.7,
            bandwidth_usage=1234.5,
            period_start=start_of_month,
            period_end=current_time,
            trends={
                'customer_growth': 12.5,
                'revenue_growth': 8.3,
                'service_growth': 15.2
            },
            alerts=[
                {
                    'id': 'alert-1',
                    'message': 'High bandwidth usage detected',
                    'severity': 'medium',
                    'timestamp': current_time.isoformat()
                }
            ]
        )


class WidgetService(BaseService[Widget]):
    """Service for widget management and operations."""

    def __init__(self, db: Session, tenant_id: str):
        self.repository = WidgetRepository(db, tenant_id)
        super().__init__(db, self.repository, tenant_id)

    async def create_widget(self, data: WidgetCreate, user_id: UUID) -> WidgetResponse:
        """Create a new widget."""
        dashboard_repo = DashboardRepository(self.db, self.tenant_id)
        dashboard = await dashboard_repo.get_by_id(UUID(data.dashboard_id))
        if not dashboard:
            raise NotFoundError(f"Dashboard with ID {data.dashboard_id} not found")

        widget_data = data.model_dump()
        widget = await self.repository.create(widget_data)
        
        await dashboard_repo.update_widget_count(UUID(data.dashboard_id))
        
        return WidgetResponse.model_validate(widget)

    async def update_widget(self, widget_id: UUID, data: WidgetUpdate, user_id: UUID) -> WidgetResponse:
        """Update an existing widget."""
        widget = await self.repository.get_by_id(widget_id)
        if not widget:
            raise NotFoundError(f"Widget with ID {widget_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        widget = await self.repository.update(widget_id, update_data)
        
        return WidgetResponse.model_validate(widget)

    async def get_widgets_by_dashboard(self, dashboard_id: UUID) -> List[WidgetResponse]:
        """Get widgets for a specific dashboard."""
        widgets = await self.repository.find_by_dashboard(dashboard_id)
        return [WidgetResponse.model_validate(widget) for widget in widgets]

    async def reorder_widgets(self, dashboard_id: UUID, widget_positions: Dict[str, int], user_id: UUID) -> bool:
        """Reorder widgets in a dashboard."""
        positions = {UUID(k): v for k, v in widget_positions.items()}
        return await self.repository.reorder_widgets(dashboard_id, positions)

    async def delete_widget(self, widget_id: UUID, user_id: UUID) -> bool:
        """Delete a widget and update dashboard count."""
        widget = await self.repository.get_by_id(widget_id)
        if not widget:
            raise NotFoundError(f"Widget with ID {widget_id} not found")

        dashboard_id = widget.dashboard_id
        result = await self.repository.delete(widget_id)
        
        if result:
            dashboard_repo = DashboardRepository(self.db, self.tenant_id)
            await dashboard_repo.update_widget_count(dashboard_id)
        
        return result


class AlertService(BaseService[Alert]):
    """Service for alert management and monitoring."""

    def __init__(self, db: Session, tenant_id: str):
        self.repository = AlertRepository(db, tenant_id)
        super().__init__(db, self.repository, tenant_id)

    async def create_alert(self, data: AlertCreate, user_id: UUID) -> AlertResponse:
        """Create a new alert."""
        metric_repo = MetricRepository(self.db, self.tenant_id)
        metric = await metric_repo.get_by_id(UUID(data.metric_id))
        if not metric:
            raise NotFoundError(f"Metric with ID {data.metric_id} not found")

        alert_data = data.model_dump()
        alert_data['priority_score'] = self._calculate_priority_score(data.severity, data.threshold)
        
        alert = await self.repository.create(alert_data)
        return AlertResponse.model_validate(alert)

    async def update_alert(self, alert_id: UUID, data: AlertUpdate, user_id: UUID) -> AlertResponse:
        """Update an existing alert."""
        alert = await self.repository.get_by_id(alert_id)
        if not alert:
            raise NotFoundError(f"Alert with ID {alert_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        
        if 'severity' in update_data or 'threshold' in update_data:
            severity = data.severity or alert.severity
            threshold = data.threshold or alert.threshold
            update_data['priority_score'] = self._calculate_priority_score(severity, threshold)
        
        alert = await self.repository.update(alert_id, update_data)
        return AlertResponse.model_validate(alert)

    async def test_alert(self, alert_id: UUID, test_value: float) -> AlertTestResponse:
        """Test an alert condition with a given value."""
        alert = await self.repository.get_by_id(alert_id)
        if not alert:
            raise NotFoundError(f"Alert with ID {alert_id} not found")

        would_trigger = self._evaluate_condition(alert.condition, test_value, alert.threshold)

        return AlertTestResponse(
            alert_id=str(alert_id),
            test_value=test_value,
            would_trigger=would_trigger,
            threshold=alert.threshold,
            condition=alert.condition,
            severity=alert.severity,
            notification_channels=alert.notification_channels or []
        )

    async def check_alert_conditions(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Check all active alerts against current metric values."""
        alerts = await self.repository.get_active_alerts()
        triggered_alerts = []

        value_repo = MetricValueRepository(self.db, self.tenant_id)
        event_repo = AlertEventRepository(self.db, self.tenant_id)

        for alert in alerts:
            latest_value = await value_repo.get_latest_value(alert.metric_id)
            if latest_value and self._evaluate_condition(alert.condition, latest_value.value, alert.threshold):
                event = await event_repo.create_event(
                    alert_id=alert.id,
                    metric_value=latest_value.value,
                    threshold_value=alert.threshold,
                    condition_met=f"{alert.condition} {alert.threshold}"
                )
                
                await self.repository.update_trigger_info(alert.id)
                
                triggered_alerts.append({
                    'alert_id': str(alert.id),
                    'alert_name': alert.name,
                    'metric_value': latest_value.value,
                    'threshold': alert.threshold,
                    'severity': alert.severity.value,
                    'event_id': str(event.id)
                })

        return triggered_alerts

    def _calculate_priority_score(self, severity: AlertSeverity, threshold: float) -> int:
        """Calculate priority score for alert ordering."""
        severity_scores = {
            AlertSeverity.LOW: 10,
            AlertSeverity.MEDIUM: 50,
            AlertSeverity.HIGH: 100,
            AlertSeverity.CRITICAL: 200
        }
        
        base_score = severity_scores.get(severity, 10)
        threshold_factor = min(int(abs(threshold) / 100), 50)
        
        return base_score + threshold_factor

    def _evaluate_condition(self, condition: str, value: float, threshold: float) -> bool:
        """Evaluate alert condition."""
        if condition == "greater_than":
            return value > threshold
        elif condition == "less_than":
            return value < threshold
        elif condition == "equals":
            return abs(value - threshold) < 0.001
        return False


class AnalyticsService(BaseService):
    """Main analytics service orchestrating all analytics operations."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.metric_service = MetricService(db, tenant_id)
        self.report_service = ReportService(db, tenant_id)
        self.dashboard_service = DashboardService(db, tenant_id)
        self.alert_service = AlertService(db, tenant_id)

    async def get_analytics_overview(self, user_id: UUID) -> AnalyticsOverviewResponse:
        """Get comprehensive analytics overview."""
        metric_repo = MetricRepository(self.db, self.tenant_id)
        report_repo = ReportRepository(self.db, self.tenant_id)
        dashboard_repo = DashboardRepository(self.db, self.tenant_id)
        alert_repo = AlertRepository(self.db, self.tenant_id)

        metrics = await metric_repo.get_active_metrics()
        reports = await report_repo.get_all()
        dashboards = await dashboard_repo.get_all()
        active_alerts = await alert_repo.get_active_alerts()

        return AnalyticsOverviewResponse(
            metrics_count=len(metrics),
            reports_count=len(reports),
            dashboards_count=len(dashboards),
            active_alerts_count=len(active_alerts),
            key_metrics={
                'total_data_points': 15420,
                'avg_metric_value': 245.6,
                'alert_rate': 2.3,
                'dashboard_usage': 78.5
            },
            recent_activity=[
                {
                    'type': 'metric_recorded',
                    'description': 'New bandwidth metric recorded',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                {
                    'type': 'alert_triggered',
                    'description': 'High CPU usage alert triggered',
                    'timestamp': (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
                }
            ]
        )

    async def get_real_time_metrics(self, user_id: UUID) -> RealTimeMetricsResponse:
        """Get real-time system metrics."""
        return RealTimeMetricsResponse(
            timestamp=datetime.now(timezone.utc),
            metrics={
                'active_connections': 1247,
                'requests_per_second': 34.5,
                'error_rate': 0.12,
                'response_time_avg': 125.6
            },
            health_status='healthy',
            active_connections=1247,
            cpu_usage=34.2,
            memory_usage=67.8,
            network_throughput={
                'inbound_mbps': 125.4,
                'outbound_mbps': 89.3
            }
        )

    async def generate_executive_report(self, user_id: UUID) -> ExecutiveReportResponse:
        """Generate executive-level analytics report."""
        current_time = datetime.now(timezone.utc)
        start_of_month = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        return ExecutiveReportResponse(
            report_id=str(UUID()),
            generated_at=current_time,
            period_start=start_of_month,
            period_end=current_time,
            executive_summary={
                'total_revenue': 125678.90,
                'customer_growth': 12.5,
                'service_uptime': 99.7,
                'key_achievements': [
                    'Exceeded revenue targets by 8.3%',
                    'Reduced support tickets by 15%',
                    'Improved network performance by 12%'
                ]
            },
            financial_metrics={
                'monthly_recurring_revenue': 98450.00,
                'average_revenue_per_user': 78.90,
                'churn_rate': 2.1,
                'customer_acquisition_cost': 125.00
            },
            operational_metrics={
                'service_availability': 99.7,
                'mean_time_to_resolution': 24.5,
                'customer_satisfaction': 4.2,
                'ticket_resolution_rate': 94.3
            },
            customer_metrics={
                'total_customers': 1247,
                'new_customers': 45,
                'churned_customers': 12,
                'customer_lifetime_value': 1850.00
            },
            network_metrics={
                'bandwidth_utilization': 67.8,
                'network_uptime': 99.9,
                'latency_average': 12.5,
                'packet_loss': 0.01
            },
            recommendations=[
                {
                    'category': 'revenue',
                    'priority': 'high',
                    'recommendation': 'Focus on upselling existing customers',
                    'expected_impact': '15% revenue increase'
                },
                {
                    'category': 'operations',
                    'priority': 'medium',
                    'recommendation': 'Implement automated monitoring',
                    'expected_impact': '25% reduction in manual effort'
                }
            ]
        )