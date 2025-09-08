"""Analytics database models for metrics, reports, dashboards and alerting."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from dotmac.database.base import Base
from dotmac.database.mixins import ISPModelMixin

from .schemas import AlertSeverity, MetricType, ReportType


class Metric(Base, ISPModelMixin):
    """Model for storing metric definitions and metadata."""

    __tablename__ = "metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    metric_type = Column(Enum(MetricType), nullable=False)
    unit = Column(String(50))
    calculation_config = Column(JSON, default=dict)
    dimensions = Column(JSON, default=list)
    tags = Column(JSON, default=dict)
    latest_value = Column(Float)
    is_active = Column(Boolean, nullable=False, default=True)
    refresh_interval = Column(Integer, default=300)
    retention_days = Column(Integer, default=90)

    metric_values = relationship("MetricValue", back_populates="metric", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="metric", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_metric_tenant_name"),
        Index("idx_metric_type", "metric_type"),
        Index("idx_metric_active", "is_active"),
    )

    def __repr__(self):
        return f"<Metric(id={self.id}, name={self.name}, type={self.metric_type})>"


class MetricValue(Base, ISPModelMixin):
    """Model for storing individual metric data points."""

    __tablename__ = "metric_values"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    metric_id = Column(UUID(as_uuid=True), ForeignKey("metrics.id"), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now())
    dimensions = Column(JSON, default=dict)
    context = Column(JSON, default=dict)

    metric = relationship("Metric", back_populates="metric_values")

    __table_args__ = (
        Index("idx_metric_value_timestamp", "timestamp"),
        Index("idx_metric_value_metric_timestamp", "metric_id", "timestamp"),
    )

    def __repr__(self):
        return (
            f"<MetricValue(id={self.id}, metric_id={self.metric_id}, value={self.value}, timestamp={self.timestamp})>"
        )


class Report(Base, ISPModelMixin):
    """Model for storing report definitions and metadata."""

    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    title = Column(String(200), nullable=False)
    description = Column(Text)
    report_type = Column(Enum(ReportType), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    filters = Column(JSON, default=dict)
    format_config = Column(JSON, default=dict)
    data = Column(JSON, default=dict)
    generated_at = Column(DateTime, default=func.now())
    is_scheduled = Column(Boolean, nullable=False, default=False)
    schedule_config = Column(JSON, default=dict)
    is_public = Column(Boolean, nullable=False, default=False)
    duration_days = Column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_report_type", "report_type"),
        Index("idx_report_public", "is_public"),
        Index("idx_report_scheduled", "is_scheduled"),
        Index("idx_report_dates", "start_date", "end_date"),
    )

    def __repr__(self):
        return f"<Report(id={self.id}, title={self.title}, type={self.report_type})>"


class Dashboard(Base, ISPModelMixin):
    """Model for storing dashboard definitions and configurations."""

    __tablename__ = "dashboards"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(100), nullable=False)
    description = Column(Text)
    layout = Column(JSON, default=dict)
    is_public = Column(Boolean, nullable=False, default=False)
    refresh_rate = Column(Integer, nullable=False, default=30)
    theme_config = Column(JSON, default=dict)
    access_permissions = Column(JSON, default=list)
    widget_count = Column(Integer, nullable=False, default=0)

    widgets = relationship("Widget", back_populates="dashboard", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_dashboard_tenant_name"),
        Index("idx_dashboard_public", "is_public"),
    )

    def __repr__(self):
        return f"<Dashboard(id={self.id}, name={self.name}, widget_count={self.widget_count})>"


class Widget(Base, ISPModelMixin):
    """Model for storing individual dashboard widgets."""

    __tablename__ = "widgets"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    dashboard_id = Column(UUID(as_uuid=True), ForeignKey("dashboards.id"), nullable=False)
    widget_type = Column(String(50), nullable=False)
    title = Column(String(100), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    config = Column(JSON, default=dict)
    data_source = Column(JSON, default=dict)
    style_config = Column(JSON, default=dict)
    is_visible = Column(Boolean, nullable=False, default=True)
    refresh_interval = Column(Integer, nullable=False, default=60)

    dashboard = relationship("Dashboard", back_populates="widgets")

    __table_args__ = (
        Index("idx_widget_dashboard", "dashboard_id"),
        Index("idx_widget_type", "widget_type"),
        Index("idx_widget_position", "position"),
    )

    def __repr__(self):
        return f"<Widget(id={self.id}, title={self.title}, type={self.widget_type})>"


class Alert(Base, ISPModelMixin):
    """Model for storing metric-based alert definitions."""

    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    metric_id = Column(UUID(as_uuid=True), ForeignKey("metrics.id"), nullable=False)
    name = Column(String(100), nullable=False)
    condition = Column(String(20), nullable=False)
    threshold = Column(Float, nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    notification_channels = Column(JSON, default=list)
    condition_config = Column(JSON, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    last_triggered = Column(DateTime)
    trigger_count = Column(Integer, nullable=False, default=0)
    priority_score = Column(Integer, nullable=False, default=0)

    metric = relationship("Metric", back_populates="alerts")
    alert_events = relationship("AlertEvent", back_populates="alert", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_alert_metric", "metric_id"),
        Index("idx_alert_severity", "severity"),
        Index("idx_alert_active", "is_active"),
    )

    def __repr__(self):
        return f"<Alert(id={self.id}, name={self.name}, severity={self.severity})>"


class AlertEvent(Base, ISPModelMixin):
    """Model for storing alert trigger events and history."""

    __tablename__ = "alert_events"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=False)
    triggered_at = Column(DateTime, nullable=False, default=func.now())
    metric_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    condition_met = Column(String(100), nullable=False)
    notification_sent = Column(Boolean, nullable=False, default=False)
    resolution_timestamp = Column(DateTime)
    resolution_notes = Column(Text)
    event_context = Column(JSON, default=dict)

    alert = relationship("Alert", back_populates="alert_events")

    __table_args__ = (
        Index("idx_alert_event_triggered", "triggered_at"),
        Index("idx_alert_event_alert", "alert_id"),
    )

    def __repr__(self):
        return f"<AlertEvent(id={self.id}, alert_id={self.alert_id}, triggered_at={self.triggered_at})>"


class DataSource(Base, ISPModelMixin):
    """Model for storing data source configurations for metrics and widgets."""

    __tablename__ = "data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(100), nullable=False)
    source_type = Column(String(50), nullable=False)
    connection_config = Column(JSON, default=dict)
    query_config = Column(JSON, default=dict)
    refresh_schedule = Column(String(100))
    data_mapping = Column(JSON, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    last_sync = Column(DateTime)
    sync_status = Column(String(20), nullable=False, default="pending")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_data_source_tenant_name"),
        Index("idx_data_source_type", "source_type"),
        Index("idx_data_source_active", "is_active"),
        Index("idx_data_source_sync", "last_sync"),
    )

    def __repr__(self):
        return f"<DataSource(id={self.id}, name={self.name}, type={self.source_type})>"


class AnalyticsSession(Base, ISPModelMixin):
    """Model for tracking analytics dashboard usage and sessions."""

    __tablename__ = "analytics_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), nullable=False)
    dashboard_id = Column(UUID(as_uuid=True), ForeignKey("dashboards.id"))
    session_start = Column(DateTime, nullable=False, default=func.now())
    session_end = Column(DateTime)
    duration_seconds = Column(Integer)
    page_views = Column(Integer, nullable=False, default=1)
    interactions = Column(JSON, default=list)
    user_agent = Column(String(500))
    ip_address = Column(String(45))

    __table_args__ = (
        Index("idx_analytics_session_user", "user_id"),
        Index("idx_analytics_session_dashboard", "dashboard_id"),
        Index("idx_analytics_session_start", "session_start"),
    )

    def __repr__(self):
        return f"<AnalyticsSession(id={self.id}, user_id={self.user_id}, start={self.session_start})>"


class MetricAggregation(Base, ISPModelMixin):
    """Model for storing pre-computed metric aggregations for performance."""

    __tablename__ = "metric_aggregations"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    metric_id = Column(UUID(as_uuid=True), ForeignKey("metrics.id"), nullable=False)
    aggregation_type = Column(String(10), nullable=False)
    period = Column(String(10), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    aggregated_value = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False, default=1)
    dimensions = Column(JSON, default=dict)
    computed_at = Column(DateTime, nullable=False, default=func.now())

    metric = relationship("Metric")

    __table_args__ = (
        UniqueConstraint(
            "metric_id",
            "aggregation_type",
            "period",
            "period_start",
            name="uq_metric_aggregation_unique",
        ),
        Index("idx_metric_agg_metric_period", "metric_id", "period"),
        Index("idx_metric_agg_period_range", "period_start", "period_end"),
    )

    def __repr__(self):
        return (
            f"<MetricAggregation(id={self.id}, metric_id={self.metric_id}, "
            f"type={self.aggregation_type}, period={self.period})>"
        )
