"""
Monitoring and observability schemas for validation and serialization.
"""

from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from .common import BaseSchema, PaginatedResponse


class MetricBase(BaseModel):
    """MetricBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    service_name: str = Field(..., description="Service name")
    metric_name: str = Field(..., description="Metric name")
    metric_type: str = Field(..., description="Metric type (gauge, counter, histogram)")
    value: float = Field(..., description="Metric value")
    timestamp: datetime = Field(..., description="Metric timestamp")
    labels: dict[str, str] = Field(default_factory=dict, description="Metric labels")
    unit: Optional[str] = Field(None, description="Metric unit")


class MetricCreate(MetricBase):
    """MetricCreate implementation."""

    pass


class Metric(MetricBase, BaseSchema):
    """Metric implementation."""

    pass


class AlertRuleBase(BaseModel):
    """AlertRuleBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., description="Alert rule name")
    description: Optional[str] = Field(None, description="Alert rule description")
    query: str = Field(..., description="Metric query for alert condition")
    condition: str = Field(..., description="Alert condition (>, <, ==, etc.)")
    threshold: float = Field(..., description="Alert threshold value")
    severity: str = Field(..., description="Alert severity (critical, warning, info)")
    enabled: bool = Field(default=True, description="Whether alert rule is enabled")
    evaluation_interval: int = Field(default=60, description="Evaluation interval in seconds")
    for_duration: int = Field(default=300, description="Duration before firing in seconds")
    labels: dict[str, str] = Field(default_factory=dict, description="Alert labels")
    annotations: dict[str, str] = Field(default_factory=dict, description="Alert annotations")


class AlertRuleCreate(AlertRuleBase):
    """AlertRuleCreate implementation."""

    pass


class AlertRuleUpdate(BaseModel):
    """AlertRuleUpdate implementation."""

    name: Optional[str] = None
    description: Optional[str] = None
    query: Optional[str] = None
    condition: Optional[str] = None
    threshold: Optional[float] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None
    evaluation_interval: Optional[int] = None
    for_duration: Optional[int] = None
    labels: Optional[dict[str, str]] = None
    annotations: Optional[dict[str, str]] = None


class AlertRule(AlertRuleBase, BaseSchema):
    """AlertRule implementation."""

    pass


class AlertBase(BaseModel):
    """AlertBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    rule_id: UUID = Field(..., description="Alert rule ID")
    status: str = Field(..., description="Alert status (firing, resolved)")
    severity: str = Field(..., description="Alert severity")
    message: str = Field(..., description="Alert message")
    started_at: datetime = Field(..., description="Alert start time")
    resolved_at: Optional[datetime] = Field(None, description="Alert resolution time")
    labels: dict[str, str] = Field(default_factory=dict, description="Alert labels")
    annotations: dict[str, str] = Field(default_factory=dict, description="Alert annotations")
    fingerprint: str = Field(..., description="Unique alert fingerprint")


class AlertCreate(AlertBase):
    """AlertCreate implementation."""

    pass


class AlertUpdate(BaseModel):
    """AlertUpdate implementation."""

    status: Optional[str] = None
    resolved_at: Optional[datetime] = None
    annotations: Optional[dict[str, str]] = None


class Alert(AlertBase, BaseSchema):
    """Alert implementation."""

    rule: Optional[AlertRule] = None


class NotificationChannelBase(BaseModel):
    """NotificationChannelBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., description="Channel name")
    type: str = Field(..., description="Channel type (email, slack, webhook, etc.)")
    configuration: dict[str, Any] = Field(..., description="Channel configuration")
    enabled: bool = Field(default=True, description="Whether channel is enabled")
    filters: dict[str, Any] = Field(default_factory=dict, description="Notification filters")


class NotificationChannelCreate(NotificationChannelBase):
    """NotificationChannelCreate implementation."""

    pass


class NotificationChannelUpdate(BaseModel):
    """NotificationChannelUpdate implementation."""

    name: Optional[str] = None
    configuration: Optional[dict[str, Any]] = None
    enabled: Optional[bool] = None
    filters: Optional[dict[str, Any]] = None


class NotificationChannel(NotificationChannelBase, BaseSchema):
    """NotificationChannel implementation."""

    pass


class NotificationBase(BaseModel):
    """NotificationBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    alert_id: UUID = Field(..., description="Alert ID")
    channel_id: UUID = Field(..., description="Notification channel ID")
    status: str = Field(..., description="Notification status")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")
    delivered_at: Optional[datetime] = Field(None, description="Delivery timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Retry count")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class NotificationCreate(NotificationBase):
    """NotificationCreate implementation."""

    pass


class NotificationUpdate(BaseModel):
    """NotificationUpdate implementation."""

    status: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None


class Notification(NotificationBase, BaseSchema):
    """Notification implementation."""

    alert: Optional[Alert] = None
    channel: Optional[NotificationChannel] = None


class DashboardBase(BaseModel):
    """DashboardBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., description="Dashboard name")
    description: Optional[str] = Field(None, description="Dashboard description")
    layout: dict[str, Any] = Field(..., description="Dashboard layout configuration")
    widgets: list[dict[str, Any]] = Field(default_factory=list, description="Dashboard widgets")
    variables: dict[str, Any] = Field(default_factory=dict, description="Dashboard variables")
    time_range: dict[str, Any] = Field(default_factory=dict, description="Default time range")
    refresh_interval: Optional[int] = Field(None, description="Auto-refresh interval in seconds")
    is_public: bool = Field(default=False, description="Whether dashboard is public")
    tags: list[str] = Field(default_factory=list, description="Dashboard tags")


class DashboardCreate(DashboardBase):
    """DashboardCreate implementation."""

    pass


class DashboardUpdate(BaseModel):
    """DashboardUpdate implementation."""

    name: Optional[str] = None
    description: Optional[str] = None
    layout: Optional[dict[str, Any]] = None
    widgets: Optional[list[dict[str, Any]]] = None
    variables: Optional[dict[str, Any]] = None
    time_range: Optional[dict[str, Any]] = None
    refresh_interval: Optional[int] = None
    is_public: Optional[bool] = None
    tags: Optional[list[str]] = None


class Dashboard(DashboardBase, BaseSchema):
    """Dashboard implementation."""

    pass


class LogEntryBase(BaseModel):
    """LogEntryBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    service_name: str = Field(..., description="Service name")
    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    timestamp: datetime = Field(..., description="Log timestamp")
    source: Optional[str] = Field(None, description="Log source")
    trace_id: Optional[str] = Field(None, description="Trace ID")
    span_id: Optional[str] = Field(None, description="Span ID")
    labels: dict[str, str] = Field(default_factory=dict, description="Log labels")
    structured_data: Optional[dict[str, Any]] = Field(default_factory=dict, description="Structured log data")


class LogEntryCreate(LogEntryBase):
    """LogEntryCreate implementation."""

    pass


class LogEntry(LogEntryBase, BaseSchema):
    """LogEntry implementation."""

    pass


# Response schemas
class MetricListResponse(PaginatedResponse):
    """MetricListResponse implementation."""

    items: list[Metric]


class AlertRuleListResponse(PaginatedResponse):
    """AlertRuleListResponse implementation."""

    items: list[AlertRule]


class AlertListResponse(PaginatedResponse):
    """AlertListResponse implementation."""

    items: list[Alert]


class NotificationChannelListResponse(PaginatedResponse):
    """NotificationChannelListResponse implementation."""

    items: list[NotificationChannel]


class NotificationListResponse(PaginatedResponse):
    """NotificationListResponse implementation."""

    items: list[Notification]


class DashboardListResponse(PaginatedResponse):
    """DashboardListResponse implementation."""

    items: list[Dashboard]


class LogEntryListResponse(PaginatedResponse):
    """LogEntryListResponse implementation."""

    items: list[LogEntry]


# Complex query schemas
class MetricQuery(BaseModel):
    """MetricQuery implementation."""

    query: str = Field(..., description="Metric query")
    start_time: datetime = Field(..., description="Query start time")
    end_time: datetime = Field(..., description="Query end time")
    step: Optional[int] = Field(None, description="Query step in seconds")
    labels: Optional[dict[str, str]] = Field(default_factory=dict, description="Additional labels")


class MetricQueryResult(BaseModel):
    """MetricQueryResult implementation."""

    metric: dict[str, str] = Field(..., description="Metric labels")
    values: list[list[Union[float, str]]] = Field(..., description="Time series values")


class MetricQueryResponse(BaseModel):
    """MetricQueryResponse implementation."""

    status: str = Field(..., description="Query status")
    data: dict[str, Any] = Field(..., description="Query result data")
    query: str = Field(..., description="Original query")
    execution_time: float = Field(..., description="Query execution time")


class LogQuery(BaseModel):
    """LogQuery implementation."""

    query: str = Field(..., description="Log query")
    start_time: datetime = Field(..., description="Query start time")
    end_time: datetime = Field(..., description="Query end time")
    limit: int = Field(default=1000, description="Maximum number of log entries")
    labels: Optional[dict[str, str]] = Field(default_factory=dict, description="Label filters")


class ServiceHealthStatus(BaseModel):
    """ServiceHealthStatus implementation."""

    service_name: str
    status: str
    uptime_percentage: float
    error_rate: float
    response_time_p95: float
    last_deployment: Optional[datetime]
    active_alerts: int
    resource_usage: dict[str, float]


class TenantMonitoringOverview(BaseModel):
    """TenantMonitoringOverview implementation."""

    tenant_id: UUID
    services_monitored: int
    active_alerts: int
    critical_alerts: int
    avg_response_time: float
    uptime_percentage: float
    error_rate: float
    total_metrics_stored: int
    total_logs_stored: int
    monitoring_cost: Optional[float]
    service_health: list[ServiceHealthStatus]
    recent_alerts: list[Alert]


# Synthetic monitoring schemas
class SyntheticCheckBase(BaseModel):
    """SyntheticCheckBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., description="Check name")
    type: str = Field(..., description="Check type (http, tcp, dns, etc.)")
    target: str = Field(..., description="Check target (URL, hostname, etc.)")
    configuration: dict[str, Any] = Field(..., description="Check configuration")
    interval: int = Field(default=300, description="Check interval in seconds")
    timeout: int = Field(default=30, description="Check timeout in seconds")
    enabled: bool = Field(default=True, description="Whether check is enabled")
    locations: list[str] = Field(default_factory=list, description="Check locations")


class SyntheticCheckCreate(SyntheticCheckBase):
    """SyntheticCheckCreate implementation."""

    pass


class SyntheticCheckUpdate(BaseModel):
    """SyntheticCheckUpdate implementation."""

    name: Optional[str] = None
    configuration: Optional[dict[str, Any]] = None
    interval: Optional[int] = None
    timeout: Optional[int] = None
    enabled: Optional[bool] = None
    locations: Optional[list[str]] = None


class SyntheticCheck(SyntheticCheckBase, BaseSchema):
    """SyntheticCheck implementation."""

    pass


class SyntheticCheckResultBase(BaseModel):
    """SyntheticCheckResultBase implementation."""

    check_id: UUID = Field(..., description="Synthetic check ID")
    status: str = Field(..., description="Check status")
    response_time: float = Field(..., description="Response time in milliseconds")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    location: str = Field(..., description="Check location")
    timestamp: datetime = Field(..., description="Check timestamp")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class SyntheticCheckResultCreate(SyntheticCheckResultBase):
    """SyntheticCheckResultCreate implementation."""

    pass


class SyntheticCheckResult(SyntheticCheckResultBase, BaseSchema):
    """SyntheticCheckResult implementation."""

    check: Optional[SyntheticCheck] = None
