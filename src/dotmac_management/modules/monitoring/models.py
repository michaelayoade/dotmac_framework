"""Monitoring database models for system health, metrics and alerts."""

from dotmac_shared.db.mixins import AuditMixin, TenantMixin
from dotmac_shared.db.models import Base
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


class HealthCheckStatus(str, Enum):
    """Health check status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(str, Enum):
    """Monitoring alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ServiceComponent(Base, TenantMixin, AuditMixin):
    """Model for tracking monitored service components."""

    __tablename__ = "service_components"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(100), nullable=False)
    component_type = Column(String(50), nullable=False)
    description = Column(Text)
    endpoint_url = Column(String(500))
    check_interval = Column(Integer, nullable=False, default=60)
    timeout_seconds = Column(Integer, nullable=False, default=30)
    retry_count = Column(Integer, nullable=False, default=3)
    is_critical = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    configuration = Column(JSON, default=dict)
    tags = Column(JSON, default=list)

    health_checks = relationship("HealthCheck", back_populates="component", cascade="all, delete-orphan")
    monitoring_alerts = relationship("MonitoringAlert", back_populates="component", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_component_tenant_name"),
        Index("idx_component_type", "component_type"),
        Index("idx_component_active", "is_active"),
        Index("idx_component_critical", "is_critical"),
    )

    def __repr__(self):
        return f"<ServiceComponent(id={self.id}, name={self.name}, type={self.component_type})>"


class HealthCheck(Base, TenantMixin, AuditMixin):
    """Model for storing health check results."""

    __tablename__ = "health_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    component_id = Column(UUID(as_uuid=True), ForeignKey("service_components.id"), nullable=False)
    check_timestamp = Column(DateTime, nullable=False, default=func.now())
    status = Column(Enum(HealthCheckStatus), nullable=False)
    response_time_ms = Column(Float)
    status_code = Column(Integer)
    error_message = Column(Text)
    details = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)
    check_duration_ms = Column(Float)

    component = relationship("ServiceComponent", back_populates="health_checks")

    __table_args__ = (
        Index("idx_health_check_timestamp", "check_timestamp"),
        Index("idx_health_check_component", "component_id"),
        Index("idx_health_check_status", "status"),
        Index("idx_health_check_component_timestamp", "component_id", "check_timestamp"),
    )

    def __repr__(self):
        return f"<HealthCheck(id={self.id}, component_id={self.component_id}, status={self.status}, timestamp={self.check_timestamp})>"


class SystemMetric(Base, TenantMixin, AuditMixin):
    """Model for storing system performance metrics."""

    __tablename__ = "system_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    unit = Column(String(20))
    timestamp = Column(DateTime, nullable=False, default=func.now())
    source = Column(String(100))
    host = Column(String(100))
    tags = Column(JSON, default=dict)
    dimensions = Column(JSON, default=dict)
    context = Column(JSON, default=dict)

    __table_args__ = (
        Index("idx_system_metric_name", "metric_name"),
        Index("idx_system_metric_timestamp", "timestamp"),
        Index("idx_system_metric_source", "source"),
        Index("idx_system_metric_host", "host"),
        Index("idx_system_metric_name_timestamp", "metric_name", "timestamp"),
    )

    def __repr__(self):
        return f"<SystemMetric(id={self.id}, name={self.metric_name}, value={self.metric_value}, timestamp={self.timestamp})>"


class PerformanceMetric(Base, TenantMixin, AuditMixin):
    """Model for storing application performance metrics."""

    __tablename__ = "performance_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    response_time_ms = Column(Float, nullable=False)
    status_code = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now())
    user_id = Column(UUID(as_uuid=True))
    session_id = Column(String(100))
    request_size_bytes = Column(Integer)
    response_size_bytes = Column(Integer)
    database_query_count = Column(Integer)
    database_query_time_ms = Column(Float)
    cache_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)
    errors = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        Index("idx_perf_metric_endpoint", "endpoint"),
        Index("idx_perf_metric_timestamp", "timestamp"),
        Index("idx_perf_metric_status", "status_code"),
        Index("idx_perf_metric_endpoint_timestamp", "endpoint", "timestamp"),
        Index("idx_perf_metric_user", "user_id"),
    )

    def __repr__(self):
        return f"<PerformanceMetric(id={self.id}, endpoint={self.endpoint}, response_time={self.response_time_ms}ms)>"


class MonitoringAlert(Base, TenantMixin, AuditMixin):
    """Model for monitoring alerts and notifications."""

    __tablename__ = "monitoring_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    component_id = Column(UUID(as_uuid=True), ForeignKey("service_components.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    condition = Column(String(500), nullable=False)
    threshold = Column(Float)
    current_value = Column(Float)
    is_active = Column(Boolean, nullable=False, default=True)
    is_resolved = Column(Boolean, nullable=False, default=False)
    triggered_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    notification_channels = Column(JSON, default=list)
    escalation_policy = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)

    component = relationship("ServiceComponent", back_populates="monitoring_alerts")
    alert_events = relationship("AlertEvent", back_populates="alert", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_monitoring_alert_component", "component_id"),
        Index("idx_monitoring_alert_severity", "severity"),
        Index("idx_monitoring_alert_active", "is_active"),
        Index("idx_monitoring_alert_resolved", "is_resolved"),
        Index("idx_monitoring_alert_triggered", "triggered_at"),
    )

    def __repr__(self):
        return f"<MonitoringAlert(id={self.id}, title={self.title}, severity={self.severity}, active={self.is_active})>"


class AlertEvent(Base, TenantMixin, AuditMixin):
    """Model for alert event history and state changes."""

    __tablename__ = "alert_events"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    alert_id = Column(UUID(as_uuid=True), ForeignKey("monitoring_alerts.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_timestamp = Column(DateTime, nullable=False, default=func.now())
    previous_state = Column(String(50))
    new_state = Column(String(50))
    metric_value = Column(Float)
    threshold_value = Column(Float)
    message = Column(Text)
    notification_sent = Column(Boolean, nullable=False, default=False)
    notification_channels = Column(JSON, default=list)
    event_context = Column(JSON, default=dict)

    alert = relationship("MonitoringAlert", back_populates="alert_events")

    __table_args__ = (
        Index("idx_alert_event_alert", "alert_id"),
        Index("idx_alert_event_timestamp", "event_timestamp"),
        Index("idx_alert_event_type", "event_type"),
    )

    def __repr__(self):
        return f"<AlertEvent(id={self.id}, alert_id={self.alert_id}, type={self.event_type}, timestamp={self.event_timestamp})>"


class MonitoringDashboard(Base, TenantMixin, AuditMixin):
    """Model for monitoring dashboards and visualizations."""

    __tablename__ = "monitoring_dashboards"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(100), nullable=False)
    description = Column(Text)
    dashboard_type = Column(String(50), nullable=False)
    layout_config = Column(JSON, default=dict)
    widget_config = Column(JSON, default=dict)
    refresh_interval = Column(Integer, nullable=False, default=60)
    is_public = Column(Boolean, nullable=False, default=False)
    is_default = Column(Boolean, nullable=False, default=False)
    access_permissions = Column(JSON, default=list)
    filters = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_monitoring_dashboard_tenant_name"),
        Index("idx_monitoring_dashboard_type", "dashboard_type"),
        Index("idx_monitoring_dashboard_public", "is_public"),
        Index("idx_monitoring_dashboard_default", "is_default"),
    )

    def __repr__(self):
        return f"<MonitoringDashboard(id={self.id}, name={self.name}, type={self.dashboard_type})>"


class ServiceDependency(Base, TenantMixin, AuditMixin):
    """Model for tracking service dependencies and relationships."""

    __tablename__ = "service_dependencies"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    parent_component_id = Column(UUID(as_uuid=True), ForeignKey("service_components.id"), nullable=False)
    child_component_id = Column(UUID(as_uuid=True), ForeignKey("service_components.id"), nullable=False)
    dependency_type = Column(String(50), nullable=False)
    criticality = Column(String(20), nullable=False, default="medium")
    is_active = Column(Boolean, nullable=False, default=True)
    metadata = Column(JSON, default=dict)

    parent_component = relationship("ServiceComponent", foreign_keys=[parent_component_id])
    child_component = relationship("ServiceComponent", foreign_keys=[child_component_id])

    __table_args__ = (
        UniqueConstraint("parent_component_id", "child_component_id", name="uq_service_dependency"),
        Index("idx_service_dependency_parent", "parent_component_id"),
        Index("idx_service_dependency_child", "child_component_id"),
        Index("idx_service_dependency_type", "dependency_type"),
    )

    def __repr__(self):
        return f"<ServiceDependency(id={self.id}, parent={self.parent_component_id}, child={self.child_component_id})>"


class MonitoringReport(Base, TenantMixin, AuditMixin):
    """Model for monitoring reports and scheduled exports."""

    __tablename__ = "monitoring_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    report_name = Column(String(100), nullable=False)
    report_type = Column(String(50), nullable=False)
    date_range_start = Column(DateTime, nullable=False)
    date_range_end = Column(DateTime, nullable=False)
    components = Column(JSON, default=list)
    metrics = Column(JSON, default=list)
    report_data = Column(JSON, default=dict)
    generated_at = Column(DateTime, default=func.now())
    format_type = Column(String(20), nullable=False, default="json")
    is_scheduled = Column(Boolean, nullable=False, default=False)
    schedule_config = Column(JSON, default=dict)
    export_path = Column(String(500))
    status = Column(String(20), nullable=False, default="pending")

    __table_args__ = (
        Index("idx_monitoring_report_type", "report_type"),
        Index("idx_monitoring_report_generated", "generated_at"),
        Index("idx_monitoring_report_scheduled", "is_scheduled"),
        Index("idx_monitoring_report_status", "status"),
    )

    def __repr__(self):
        return (
            f"<MonitoringReport(id={self.id}, name={self.report_name}, type={self.report_type}, status={self.status})>"
        )


class MetricThreshold(Base, TenantMixin, AuditMixin):
    """Model for metric thresholds and alerting rules."""

    __tablename__ = "metric_thresholds"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    metric_name = Column(String(100), nullable=False)
    component_id = Column(UUID(as_uuid=True), ForeignKey("service_components.id"))
    threshold_type = Column(String(50), nullable=False)
    warning_threshold = Column(Float)
    critical_threshold = Column(Float)
    comparison_operator = Column(String(20), nullable=False)
    evaluation_period = Column(Integer, nullable=False, default=300)
    is_active = Column(Boolean, nullable=False, default=True)
    notification_config = Column(JSON, default=dict)
    escalation_config = Column(JSON, default=dict)

    component = relationship("ServiceComponent")

    __table_args__ = (
        Index("idx_metric_threshold_name", "metric_name"),
        Index("idx_metric_threshold_component", "component_id"),
        Index("idx_metric_threshold_type", "threshold_type"),
        Index("idx_metric_threshold_active", "is_active"),
    )

    def __repr__(self):
        return f"<MetricThreshold(id={self.id}, metric={self.metric_name}, type={self.threshold_type})>"
