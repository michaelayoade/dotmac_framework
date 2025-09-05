"""Monitoring schemas for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class ComponentType(str, Enum):
    """Service component types."""

    DATABASE = "database"
    API = "api"
    CACHE = "cache"
    QUEUE = "queue"
    STORAGE = "storage"
    NETWORK = "network"
    EXTERNAL = "external"
    CUSTOM = "custom"


class ReportType(str, Enum):
    """Monitoring report types."""

    UPTIME = "uptime"
    PERFORMANCE = "performance"
    ALERTS = "alerts"
    CAPACITY = "capacity"
    COMPREHENSIVE = "comprehensive"


# === SERVICE COMPONENT SCHEMAS ===


class ServiceComponentBase(BaseModel):
    """Base service component schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Component name")
    component_type: str = Field(..., description="Component type")
    description: Optional[str] = Field(None, description="Component description")
    endpoint_url: Optional[str] = Field(None, max_length=500, description="Health check endpoint URL")
    check_interval: int = Field(60, ge=10, le=3600, description="Check interval in seconds")
    timeout_seconds: int = Field(30, ge=1, le=300, description="Timeout in seconds")
    retry_count: int = Field(3, ge=0, le=10, description="Number of retries")
    is_critical: bool = Field(False, description="Critical component flag")
    is_active: bool = Field(True, description="Active monitoring flag")
    configuration: Optional[dict[str, Any]] = Field(None, description="Component configuration")
    tags: Optional[list[str]] = Field(None, description="Component tags")


class ServiceComponentCreate(ServiceComponentBase):
    """Schema for creating service components."""

    pass


class ServiceComponentUpdate(BaseModel):
    """Schema for updating service components."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    component_type: Optional[str] = None
    description: Optional[str] = None
    endpoint_url: Optional[str] = Field(None, max_length=500)
    check_interval: Optional[int] = Field(None, ge=10, le=3600)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    retry_count: Optional[int] = Field(None, ge=0, le=10)
    is_critical: Optional[bool] = None
    is_active: Optional[bool] = None
    configuration: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None


class ServiceComponentResponse(ServiceComponentBase):
    """Schema for service component responses."""

    id: UUID = Field(..., description="Component ID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# === HEALTH CHECK SCHEMAS ===


class HealthCheckBase(BaseModel):
    """Base health check schema."""

    status: HealthCheckStatus = Field(..., description="Health check status")
    response_time_ms: Optional[float] = Field(None, ge=0, description="Response time in milliseconds")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    error_message: Optional[str] = Field(None, description="Error message if any")
    details: Optional[dict[str, Any]] = Field(None, description="Additional details")
    metrics: Optional[dict[str, Any]] = Field(None, description="Health check metrics")
    check_duration_ms: Optional[float] = Field(None, ge=0, description="Check duration")


class HealthCheckCreate(HealthCheckBase):
    """Schema for creating health checks."""

    component_id: UUID = Field(..., description="Component ID")
    check_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")


class HealthCheckResponse(HealthCheckBase):
    """Schema for health check responses."""

    id: UUID = Field(..., description="Health check ID")
    component_id: UUID = Field(..., description="Component ID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    check_timestamp: datetime = Field(..., description="Check timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


# === SYSTEM METRIC SCHEMAS ===


class SystemMetricBase(BaseModel):
    """Base system metric schema."""

    metric_name: str = Field(..., min_length=1, max_length=100, description="Metric name")
    metric_value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, max_length=20, description="Unit of measurement")
    source: Optional[str] = Field(None, max_length=100, description="Metric source")
    host: Optional[str] = Field(None, max_length=100, description="Host name")
    tags: Optional[dict[str, Any]] = Field(None, description="Metric tags")
    dimensions: Optional[dict[str, Any]] = Field(None, description="Metric dimensions")
    context: Optional[dict[str, Any]] = Field(None, description="Additional context")


class SystemMetricCreate(SystemMetricBase):
    """Schema for creating system metrics."""

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metric timestamp")


class SystemMetricResponse(SystemMetricBase):
    """Schema for system metric responses."""

    id: UUID = Field(..., description="Metric ID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    timestamp: datetime = Field(..., description="Metric timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


# === PERFORMANCE METRIC SCHEMAS ===


class PerformanceMetricBase(BaseModel):
    """Base performance metric schema."""

    endpoint: str = Field(..., min_length=1, max_length=200, description="API endpoint")
    method: str = Field(..., pattern=r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$", description="HTTP method")
    response_time_ms: float = Field(..., ge=0, description="Response time in milliseconds")
    status_code: int = Field(..., ge=100, le=599, description="HTTP status code")
    user_id: Optional[UUID] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, max_length=100, description="Session ID")
    request_size_bytes: Optional[int] = Field(None, ge=0, description="Request size in bytes")
    response_size_bytes: Optional[int] = Field(None, ge=0, description="Response size in bytes")
    database_query_count: Optional[int] = Field(None, ge=0, description="Database query count")
    database_query_time_ms: Optional[float] = Field(None, ge=0, description="Database query time")
    cache_hits: int = Field(0, ge=0, description="Cache hits count")
    cache_misses: int = Field(0, ge=0, description="Cache misses count")
    errors: Optional[list[dict[str, Any]]] = Field(None, description="Error details")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class PerformanceMetricCreate(PerformanceMetricBase):
    """Schema for creating performance metrics."""

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metric timestamp")


class PerformanceMetricResponse(PerformanceMetricBase):
    """Schema for performance metric responses."""

    id: UUID = Field(..., description="Metric ID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    timestamp: datetime = Field(..., description="Metric timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


# === MONITORING ALERT SCHEMAS ===


class MonitoringAlertBase(BaseModel):
    """Base monitoring alert schema."""

    alert_type: str = Field(..., min_length=1, max_length=50, description="Alert type")
    severity: AlertSeverity = Field(..., description="Alert severity")
    title: str = Field(..., min_length=1, max_length=200, description="Alert title")
    description: Optional[str] = Field(None, description="Alert description")
    condition: str = Field(..., min_length=1, max_length=500, description="Alert condition")
    threshold: Optional[float] = Field(None, description="Alert threshold")
    current_value: Optional[float] = Field(None, description="Current metric value")
    is_active: bool = Field(True, description="Active alert flag")
    notification_channels: Optional[list[str]] = Field(None, description="Notification channels")
    escalation_policy: Optional[dict[str, Any]] = Field(None, description="Escalation policy")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class MonitoringAlertCreate(MonitoringAlertBase):
    """Schema for creating monitoring alerts."""

    component_id: UUID = Field(..., description="Component ID")


class MonitoringAlertUpdate(BaseModel):
    """Schema for updating monitoring alerts."""

    alert_type: Optional[str] = Field(None, min_length=1, max_length=50)
    severity: Optional[AlertSeverity] = None
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    condition: Optional[str] = Field(None, min_length=1, max_length=500)
    threshold: Optional[float] = None
    current_value: Optional[float] = None
    is_active: Optional[bool] = None
    is_resolved: Optional[bool] = None
    resolution_notes: Optional[str] = None
    notification_channels: Optional[list[str]] = None
    escalation_policy: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None


class MonitoringAlertResponse(MonitoringAlertBase):
    """Schema for monitoring alert responses."""

    id: UUID = Field(..., description="Alert ID")
    component_id: UUID = Field(..., description="Component ID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    is_resolved: bool = Field(..., description="Resolved flag")
    triggered_at: datetime = Field(..., description="Triggered timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Resolved timestamp")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# === DASHBOARD SCHEMAS ===


class MonitoringDashboardBase(BaseModel):
    """Base monitoring dashboard schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Dashboard name")
    description: Optional[str] = Field(None, description="Dashboard description")
    dashboard_type: str = Field(..., min_length=1, max_length=50, description="Dashboard type")
    layout_config: Optional[dict[str, Any]] = Field(None, description="Layout configuration")
    widget_config: Optional[dict[str, Any]] = Field(None, description="Widget configuration")
    refresh_interval: int = Field(60, ge=10, le=3600, description="Refresh interval in seconds")
    is_public: bool = Field(False, description="Public dashboard flag")
    is_default: bool = Field(False, description="Default dashboard flag")
    access_permissions: Optional[list[str]] = Field(None, description="Access permissions")
    filters: Optional[dict[str, Any]] = Field(None, description="Dashboard filters")


class MonitoringDashboardCreate(MonitoringDashboardBase):
    """Schema for creating monitoring dashboards."""

    pass


class MonitoringDashboardUpdate(BaseModel):
    """Schema for updating monitoring dashboards."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    dashboard_type: Optional[str] = Field(None, min_length=1, max_length=50)
    layout_config: Optional[dict[str, Any]] = None
    widget_config: Optional[dict[str, Any]] = None
    refresh_interval: Optional[int] = Field(None, ge=10, le=3600)
    is_public: Optional[bool] = None
    is_default: Optional[bool] = None
    access_permissions: Optional[list[str]] = None
    filters: Optional[dict[str, Any]] = None


class MonitoringDashboardResponse(MonitoringDashboardBase):
    """Schema for monitoring dashboard responses."""

    id: UUID = Field(..., description="Dashboard ID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# === METRIC THRESHOLD SCHEMAS ===


class MetricThresholdBase(BaseModel):
    """Base metric threshold schema."""

    metric_name: str = Field(..., min_length=1, max_length=100, description="Metric name")
    threshold_type: str = Field(..., min_length=1, max_length=50, description="Threshold type")
    warning_threshold: Optional[float] = Field(None, description="Warning threshold")
    critical_threshold: Optional[float] = Field(None, description="Critical threshold")
    comparison_operator: str = Field(..., pattern=r"^(gt|gte|lt|lte|eq|ne)$", description="Comparison operator")
    evaluation_period: int = Field(300, ge=60, le=3600, description="Evaluation period in seconds")
    is_active: bool = Field(True, description="Active threshold flag")
    notification_config: Optional[dict[str, Any]] = Field(None, description="Notification configuration")
    escalation_config: Optional[dict[str, Any]] = Field(None, description="Escalation configuration")


class MetricThresholdCreate(MetricThresholdBase):
    """Schema for creating metric thresholds."""

    component_id: Optional[UUID] = Field(None, description="Component ID")


class MetricThresholdUpdate(BaseModel):
    """Schema for updating metric thresholds."""

    metric_name: Optional[str] = Field(None, min_length=1, max_length=100)
    threshold_type: Optional[str] = Field(None, min_length=1, max_length=50)
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    comparison_operator: Optional[str] = Field(None, pattern=r"^(gt|gte|lt|lte|eq|ne)$")
    evaluation_period: Optional[int] = Field(None, ge=60, le=3600)
    is_active: Optional[bool] = None
    notification_config: Optional[dict[str, Any]] = None
    escalation_config: Optional[dict[str, Any]] = None


class MetricThresholdResponse(MetricThresholdBase):
    """Schema for metric threshold responses."""

    id: UUID = Field(..., description="Threshold ID")
    component_id: Optional[UUID] = Field(None, description="Component ID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# === MONITORING OVERVIEW SCHEMAS ===


class MonitoringOverviewResponse(BaseModel):
    """Schema for monitoring overview response."""

    total_components: int = Field(..., ge=0, description="Total monitored components")
    healthy_components: int = Field(..., ge=0, description="Healthy components count")
    degraded_components: int = Field(..., ge=0, description="Degraded components count")
    unhealthy_components: int = Field(..., ge=0, description="Unhealthy components count")
    active_alerts: int = Field(..., ge=0, description="Active alerts count")
    critical_alerts: int = Field(..., ge=0, description="Critical alerts count")
    system_uptime: float = Field(..., ge=0, le=100, description="Overall system uptime percentage")
    average_response_time: float = Field(..., ge=0, description="Average response time in ms")
    recent_events: list[dict[str, Any]] = Field(..., description="Recent monitoring events")
    component_status: dict[str, Any] = Field(..., description="Component status breakdown")
    performance_metrics: dict[str, float] = Field(..., description="Key performance metrics")


class SystemHealthResponse(BaseModel):
    """Schema for system health response."""

    overall_status: HealthCheckStatus = Field(..., description="Overall system health")
    timestamp: datetime = Field(..., description="Health check timestamp")
    uptime_seconds: int = Field(..., ge=0, description="System uptime in seconds")
    component_checks: list[dict[str, Any]] = Field(..., description="Individual component checks")
    failed_checks: list[dict[str, Any]] = Field(..., description="Failed health checks")
    performance_summary: dict[str, float] = Field(..., description="Performance summary")
    resource_usage: dict[str, float] = Field(..., description="Resource usage metrics")


class AlertSummaryResponse(BaseModel):
    """Schema for alert summary response."""

    total_alerts: int = Field(..., ge=0, description="Total alerts")
    active_alerts: int = Field(..., ge=0, description="Active alerts")
    resolved_alerts: int = Field(..., ge=0, description="Resolved alerts")
    alerts_by_severity: dict[str, int] = Field(..., description="Alerts grouped by severity")
    alerts_by_component: dict[str, int] = Field(..., description="Alerts grouped by component")
    recent_alerts: list[dict[str, Any]] = Field(..., description="Recent alert activity")
    alert_trends: dict[str, Any] = Field(..., description="Alert trend data")


class PerformanceReportResponse(BaseModel):
    """Schema for performance report response."""

    report_period_start: datetime = Field(..., description="Report period start")
    report_period_end: datetime = Field(..., description="Report period end")
    total_requests: int = Field(..., ge=0, description="Total requests processed")
    average_response_time: float = Field(..., ge=0, description="Average response time")
    p95_response_time: float = Field(..., ge=0, description="95th percentile response time")
    p99_response_time: float = Field(..., ge=0, description="99th percentile response time")
    error_rate: float = Field(..., ge=0, le=100, description="Error rate percentage")
    throughput_rps: float = Field(..., ge=0, description="Throughput in requests per second")
    endpoint_metrics: list[dict[str, Any]] = Field(..., description="Per-endpoint metrics")
    database_metrics: dict[str, float] = Field(..., description="Database performance metrics")
    cache_metrics: dict[str, float] = Field(..., description="Cache performance metrics")


# === REQUEST SCHEMAS ===


class HealthCheckRequest(BaseModel):
    """Schema for health check requests."""

    component_ids: Optional[list[UUID]] = Field(None, description="Specific component IDs to check")
    include_details: bool = Field(True, description="Include detailed check information")
    force_check: bool = Field(False, description="Force immediate check bypass cache")


class AlertActionRequest(BaseModel):
    """Schema for alert action requests."""

    action: str = Field(..., pattern=r"^(acknowledge|resolve|escalate|snooze)$", description="Action to perform")
    notes: Optional[str] = Field(None, description="Action notes")
    snooze_duration_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Snooze duration")


class MetricQueryRequest(BaseModel):
    """Schema for metric query requests."""

    metric_names: list[str] = Field(..., min_length=1, description="Metric names to query")
    time_range_start: datetime = Field(..., description="Query time range start")
    time_range_end: datetime = Field(..., description="Query time range end")
    aggregation: Optional[str] = Field("avg", pattern=r"^(avg|sum|min|max|count)$", description="Aggregation function")
    group_by: Optional[list[str]] = Field(None, description="Group by dimensions")
    filters: Optional[dict[str, Any]] = Field(None, description="Query filters")


class MetricQueryResponse(BaseModel):
    """Schema for metric query responses."""

    query_id: str = Field(..., description="Query ID")
    metric_data: dict[str, list[dict[str, Any]]] = Field(..., description="Metric data by name")
    query_metadata: dict[str, Any] = Field(..., description="Query execution metadata")
    total_data_points: int = Field(..., ge=0, description="Total data points returned")


# === MAIN MONITORING SCHEMAS ===


class MonitoringCreate(ServiceComponentCreate):
    """Main schema for creating monitoring resources."""

    pass


class MonitoringUpdate(ServiceComponentUpdate):
    """Main schema for updating monitoring resources."""

    pass


class MonitoringResponse(ServiceComponentResponse):
    """Main schema for monitoring responses."""

    pass
