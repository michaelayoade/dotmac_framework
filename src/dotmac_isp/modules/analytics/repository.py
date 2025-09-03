"""Analytics repository for data access operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session, joinedload

from dotmac_shared.db.repositories import BaseRepository

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
from .schemas import AlertSeverity, MetricType, ReportType


class MetricRepository(BaseRepository[Metric]):
    """Repository for metric operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, Metric, tenant_id)

    async def find_by_name(self, name: str) -> Optional[Metric]:
        """Find metric by name within tenant."""
        return self.db.query(Metric).filter(
            and_(Metric.tenant_id == self.tenant_id, Metric.name == name)
        ).first()

    async def find_by_type(self, metric_type: MetricType) -> List[Metric]:
        """Find metrics by type."""
        return self.db.query(Metric).filter(
            and_(
                Metric.tenant_id == self.tenant_id,
                Metric.metric_type == metric_type,
                Metric.is_active == True
            )
        ).all()

    async def get_active_metrics(self) -> List[Metric]:
        """Get all active metrics."""
        return self.db.query(Metric).filter(
            and_(Metric.tenant_id == self.tenant_id, Metric.is_active == True)
        ).all()

    async def update_latest_value(self, metric_id: UUID, value: float) -> bool:
        """Update the latest value for a metric."""
        result = self.db.query(Metric).filter(
            and_(Metric.tenant_id == self.tenant_id, Metric.id == metric_id)
        ).update({Metric.latest_value: value})
        return result > 0

    async def get_metrics_with_values(self, limit: int = 100) -> List[Metric]:
        """Get metrics with their latest values."""
        return self.db.query(Metric).options(
            joinedload(Metric.metric_values)
        ).filter(
            Metric.tenant_id == self.tenant_id
        ).limit(limit).all()


class MetricValueRepository(BaseRepository[MetricValue]):
    """Repository for metric value operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, MetricValue, tenant_id)

    async def create_value(self, metric_id: UUID, value: float, timestamp: datetime = None,
                          dimensions: Dict[str, Any] = None, context: Dict[str, Any] = None) -> MetricValue:
        """Create a new metric value."""
        metric_value = MetricValue(
            tenant_id=self.tenant_id,
            metric_id=metric_id,
            value=value,
            timestamp=timestamp or datetime.now(timezone.utc),
            dimensions=dimensions or {},
            context=context or {}
        )
        self.db.add(metric_value)
        self.db.commit()
        self.db.refresh(metric_value)
        return metric_value

    async def get_values_for_metric(
        self, metric_id: UUID, start_date: datetime = None, end_date: datetime = None,
        limit: int = 1000
    ) -> List[MetricValue]:
        """Get metric values for a specific metric within date range."""
        query = self.db.query(MetricValue).filter(
            and_(
                MetricValue.tenant_id == self.tenant_id,
                MetricValue.metric_id == metric_id
            )
        )
        
        if start_date:
            query = query.filter(MetricValue.timestamp >= start_date)
        if end_date:
            query = query.filter(MetricValue.timestamp <= end_date)
            
        return query.order_by(desc(MetricValue.timestamp)).limit(limit).all()

    async def get_latest_value(self, metric_id: UUID) -> Optional[MetricValue]:
        """Get the latest value for a metric."""
        return self.db.query(MetricValue).filter(
            and_(
                MetricValue.tenant_id == self.tenant_id,
                MetricValue.metric_id == metric_id
            )
        ).order_by(desc(MetricValue.timestamp)).first()

    async def get_value_statistics(
        self, metric_id: UUID, start_date: datetime = None, end_date: datetime = None
    ) -> Dict[str, float]:
        """Get statistical summary for metric values."""
        query = self.db.query(
            func.avg(MetricValue.value).label('avg'),
            func.min(MetricValue.value).label('min'),
            func.max(MetricValue.value).label('max'),
            func.count(MetricValue.value).label('count')
        ).filter(
            and_(
                MetricValue.tenant_id == self.tenant_id,
                MetricValue.metric_id == metric_id
            )
        )
        
        if start_date:
            query = query.filter(MetricValue.timestamp >= start_date)
        if end_date:
            query = query.filter(MetricValue.timestamp <= end_date)
            
        result = query.first()
        return {
            'average': float(result.avg or 0),
            'minimum': float(result.min or 0),
            'maximum': float(result.max or 0),
            'count': int(result.count or 0)
        }


class ReportRepository(BaseRepository[Report]):
    """Repository for report operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, Report, tenant_id)

    async def find_by_type(self, report_type: ReportType) -> List[Report]:
        """Find reports by type."""
        return self.db.query(Report).filter(
            and_(
                Report.tenant_id == self.tenant_id,
                Report.report_type == report_type
            )
        ).order_by(desc(Report.created_at)).all()

    async def get_public_reports(self) -> List[Report]:
        """Get all public reports."""
        return self.db.query(Report).filter(
            and_(Report.tenant_id == self.tenant_id, Report.is_public == True)
        ).order_by(desc(Report.created_at)).all()

    async def get_scheduled_reports(self) -> List[Report]:
        """Get all scheduled reports."""
        return self.db.query(Report).filter(
            and_(Report.tenant_id == self.tenant_id, Report.is_scheduled == True)
        ).all()

    async def find_reports_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Report]:
        """Find reports within date range."""
        return self.db.query(Report).filter(
            and_(
                Report.tenant_id == self.tenant_id,
                Report.start_date >= start_date,
                Report.end_date <= end_date
            )
        ).order_by(desc(Report.generated_at)).all()


class DashboardRepository(BaseRepository[Dashboard]):
    """Repository for dashboard operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, Dashboard, tenant_id)

    async def find_by_name(self, name: str) -> Optional[Dashboard]:
        """Find dashboard by name within tenant."""
        return self.db.query(Dashboard).filter(
            and_(Dashboard.tenant_id == self.tenant_id, Dashboard.name == name)
        ).first()

    async def get_public_dashboards(self) -> List[Dashboard]:
        """Get all public dashboards."""
        return self.db.query(Dashboard).filter(
            and_(Dashboard.tenant_id == self.tenant_id, Dashboard.is_public == True)
        ).all()

    async def get_dashboard_with_widgets(self, dashboard_id: UUID) -> Optional[Dashboard]:
        """Get dashboard with all its widgets."""
        return self.db.query(Dashboard).options(
            joinedload(Dashboard.widgets)
        ).filter(
            and_(
                Dashboard.tenant_id == self.tenant_id,
                Dashboard.id == dashboard_id
            )
        ).first()

    async def update_widget_count(self, dashboard_id: UUID) -> bool:
        """Update the widget count for a dashboard."""
        count = self.db.query(Widget).filter(
            and_(
                Widget.tenant_id == self.tenant_id,
                Widget.dashboard_id == dashboard_id
            )
        ).count()
        
        result = self.db.query(Dashboard).filter(
            and_(Dashboard.tenant_id == self.tenant_id, Dashboard.id == dashboard_id)
        ).update({Dashboard.widget_count: count})
        
        return result > 0


class WidgetRepository(BaseRepository[Widget]):
    """Repository for widget operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, Widget, tenant_id)

    async def find_by_dashboard(self, dashboard_id: UUID) -> List[Widget]:
        """Find widgets by dashboard ID."""
        return self.db.query(Widget).filter(
            and_(
                Widget.tenant_id == self.tenant_id,
                Widget.dashboard_id == dashboard_id
            )
        ).order_by(Widget.position).all()

    async def find_by_type(self, widget_type: str) -> List[Widget]:
        """Find widgets by type."""
        return self.db.query(Widget).filter(
            and_(
                Widget.tenant_id == self.tenant_id,
                Widget.widget_type == widget_type,
                Widget.is_visible == True
            )
        ).all()

    async def get_visible_widgets(self, dashboard_id: UUID) -> List[Widget]:
        """Get visible widgets for a dashboard."""
        return self.db.query(Widget).filter(
            and_(
                Widget.tenant_id == self.tenant_id,
                Widget.dashboard_id == dashboard_id,
                Widget.is_visible == True
            )
        ).order_by(Widget.position).all()

    async def reorder_widgets(self, dashboard_id: UUID, widget_positions: Dict[UUID, int]) -> bool:
        """Reorder widgets by updating their positions."""
        try:
            for widget_id, position in widget_positions.items():
                self.db.query(Widget).filter(
                    and_(
                        Widget.tenant_id == self.tenant_id,
                        Widget.dashboard_id == dashboard_id,
                        Widget.id == widget_id
                    )
                ).update({Widget.position: position})
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False


class AlertRepository(BaseRepository[Alert]):
    """Repository for alert operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, Alert, tenant_id)

    async def find_by_metric(self, metric_id: UUID) -> List[Alert]:
        """Find alerts by metric ID."""
        return self.db.query(Alert).filter(
            and_(
                Alert.tenant_id == self.tenant_id,
                Alert.metric_id == metric_id,
                Alert.is_active == True
            )
        ).all()

    async def find_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Find alerts by severity level."""
        return self.db.query(Alert).filter(
            and_(
                Alert.tenant_id == self.tenant_id,
                Alert.severity == severity,
                Alert.is_active == True
            )
        ).order_by(desc(Alert.last_triggered)).all()

    async def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return self.db.query(Alert).filter(
            and_(Alert.tenant_id == self.tenant_id, Alert.is_active == True)
        ).order_by(desc(Alert.priority_score)).all()

    async def update_trigger_info(self, alert_id: UUID, triggered_at: datetime = None) -> bool:
        """Update alert trigger information."""
        updates = {
            Alert.last_triggered: triggered_at or datetime.now(timezone.utc),
            Alert.trigger_count: Alert.trigger_count + 1
        }
        
        result = self.db.query(Alert).filter(
            and_(Alert.tenant_id == self.tenant_id, Alert.id == alert_id)
        ).update(updates)
        
        return result > 0

    async def get_alerts_with_events(self, limit: int = 100) -> List[Alert]:
        """Get alerts with their recent events."""
        return self.db.query(Alert).options(
            joinedload(Alert.alert_events)
        ).filter(
            Alert.tenant_id == self.tenant_id
        ).order_by(desc(Alert.last_triggered)).limit(limit).all()


class AlertEventRepository(BaseRepository[AlertEvent]):
    """Repository for alert event operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, AlertEvent, tenant_id)

    async def create_event(
        self, alert_id: UUID, metric_value: float, threshold_value: float,
        condition_met: str, context: Dict[str, Any] = None
    ) -> AlertEvent:
        """Create a new alert event."""
        event = AlertEvent(
            tenant_id=self.tenant_id,
            alert_id=alert_id,
            metric_value=metric_value,
            threshold_value=threshold_value,
            condition_met=condition_met,
            event_context=context or {}
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    async def find_by_alert(self, alert_id: UUID, limit: int = 100) -> List[AlertEvent]:
        """Find events by alert ID."""
        return self.db.query(AlertEvent).filter(
            and_(
                AlertEvent.tenant_id == self.tenant_id,
                AlertEvent.alert_id == alert_id
            )
        ).order_by(desc(AlertEvent.triggered_at)).limit(limit).all()

    async def get_unresolved_events(self) -> List[AlertEvent]:
        """Get all unresolved alert events."""
        return self.db.query(AlertEvent).filter(
            and_(
                AlertEvent.tenant_id == self.tenant_id,
                AlertEvent.resolution_timestamp.is_(None)
            )
        ).order_by(desc(AlertEvent.triggered_at)).all()

    async def resolve_event(self, event_id: UUID, resolution_notes: str = None) -> bool:
        """Mark an alert event as resolved."""
        updates = {
            AlertEvent.resolution_timestamp: datetime.now(timezone.utc),
            AlertEvent.resolution_notes: resolution_notes
        }
        
        result = self.db.query(AlertEvent).filter(
            and_(AlertEvent.tenant_id == self.tenant_id, AlertEvent.id == event_id)
        ).update(updates)
        
        return result > 0


class DataSourceRepository(BaseRepository[DataSource]):
    """Repository for data source operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, DataSource, tenant_id)

    async def find_by_name(self, name: str) -> Optional[DataSource]:
        """Find data source by name within tenant."""
        return self.db.query(DataSource).filter(
            and_(DataSource.tenant_id == self.tenant_id, DataSource.name == name)
        ).first()

    async def find_by_type(self, source_type: str) -> List[DataSource]:
        """Find data sources by type."""
        return self.db.query(DataSource).filter(
            and_(
                DataSource.tenant_id == self.tenant_id,
                DataSource.source_type == source_type,
                DataSource.is_active == True
            )
        ).all()

    async def get_active_sources(self) -> List[DataSource]:
        """Get all active data sources."""
        return self.db.query(DataSource).filter(
            and_(DataSource.tenant_id == self.tenant_id, DataSource.is_active == True)
        ).all()

    async def update_sync_status(self, source_id: UUID, status: str, last_sync: datetime = None) -> bool:
        """Update sync status for a data source."""
        updates = {
            DataSource.sync_status: status,
            DataSource.last_sync: last_sync or datetime.now(timezone.utc)
        }
        
        result = self.db.query(DataSource).filter(
            and_(DataSource.tenant_id == self.tenant_id, DataSource.id == source_id)
        ).update(updates)
        
        return result > 0


class AnalyticsSessionRepository(BaseRepository[AnalyticsSession]):
    """Repository for analytics session tracking."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, AnalyticsSession, tenant_id)

    async def create_session(
        self, user_id: UUID, dashboard_id: UUID = None, user_agent: str = None,
        ip_address: str = None
    ) -> AnalyticsSession:
        """Create a new analytics session."""
        session = AnalyticsSession(
            tenant_id=self.tenant_id,
            user_id=user_id,
            dashboard_id=dashboard_id,
            user_agent=user_agent,
            ip_address=ip_address
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    async def end_session(self, session_id: UUID) -> bool:
        """End an analytics session."""
        session = await self.get_by_id(session_id)
        if session and not session.session_end:
            end_time = datetime.now(timezone.utc)
            duration = int((end_time - session.session_start).total_seconds())
            
            result = self.db.query(AnalyticsSession).filter(
                and_(AnalyticsSession.tenant_id == self.tenant_id, AnalyticsSession.id == session_id)
            ).update({
                AnalyticsSession.session_end: end_time,
                AnalyticsSession.duration_seconds: duration
            })
            return result > 0
        return False

    async def get_dashboard_analytics(self, dashboard_id: UUID, days: int = 30) -> Dict[str, Any]:
        """Get analytics data for a specific dashboard."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        stats = self.db.query(
            func.count(AnalyticsSession.id).label('total_views'),
            func.count(func.distinct(AnalyticsSession.user_id)).label('unique_users'),
            func.avg(AnalyticsSession.duration_seconds).label('avg_duration')
        ).filter(
            and_(
                AnalyticsSession.tenant_id == self.tenant_id,
                AnalyticsSession.dashboard_id == dashboard_id,
                AnalyticsSession.session_start >= start_date
            )
        ).first()
        
        return {
            'total_views': int(stats.total_views or 0),
            'unique_users': int(stats.unique_users or 0),
            'avg_session_duration': float(stats.avg_duration or 0),
            'period_days': days
        }


class MetricAggregationRepository(BaseRepository[MetricAggregation]):
    """Repository for metric aggregation operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, MetricAggregation, tenant_id)

    async def find_aggregation(
        self, metric_id: UUID, aggregation_type: str, period: str, period_start: datetime
    ) -> Optional[MetricAggregation]:
        """Find a specific metric aggregation."""
        return self.db.query(MetricAggregation).filter(
            and_(
                MetricAggregation.tenant_id == self.tenant_id,
                MetricAggregation.metric_id == metric_id,
                MetricAggregation.aggregation_type == aggregation_type,
                MetricAggregation.period == period,
                MetricAggregation.period_start == period_start
            )
        ).first()

    async def get_aggregations_for_metric(
        self, metric_id: UUID, aggregation_type: str = None, period: str = None,
        start_date: datetime = None, end_date: datetime = None
    ) -> List[MetricAggregation]:
        """Get aggregations for a metric with optional filters."""
        query = self.db.query(MetricAggregation).filter(
            and_(
                MetricAggregation.tenant_id == self.tenant_id,
                MetricAggregation.metric_id == metric_id
            )
        )
        
        if aggregation_type:
            query = query.filter(MetricAggregation.aggregation_type == aggregation_type)
        if period:
            query = query.filter(MetricAggregation.period == period)
        if start_date:
            query = query.filter(MetricAggregation.period_start >= start_date)
        if end_date:
            query = query.filter(MetricAggregation.period_end <= end_date)
            
        return query.order_by(MetricAggregation.period_start).all()

    async def create_or_update_aggregation(
        self, metric_id: UUID, aggregation_type: str, period: str,
        period_start: datetime, period_end: datetime, aggregated_value: float,
        sample_count: int = 1, dimensions: Dict[str, Any] = None
    ) -> MetricAggregation:
        """Create or update a metric aggregation."""
        existing = await self.find_aggregation(metric_id, aggregation_type, period, period_start)
        
        if existing:
            existing.aggregated_value = aggregated_value
            existing.sample_count = sample_count
            existing.dimensions = dimensions or {}
            existing.computed_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            aggregation = MetricAggregation(
                tenant_id=self.tenant_id,
                metric_id=metric_id,
                aggregation_type=aggregation_type,
                period=period,
                period_start=period_start,
                period_end=period_end,
                aggregated_value=aggregated_value,
                sample_count=sample_count,
                dimensions=dimensions or {}
            )
            self.db.add(aggregation)
            self.db.commit()
            self.db.refresh(aggregation)
            return aggregation