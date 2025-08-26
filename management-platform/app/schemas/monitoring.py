"""
Monitoring and observability schemas for validation and serialization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

from schemas.common import BaseSchema, PaginatedResponse


class MetricBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    service_name: str = Field(..., description="Service name")
    metric_name: str = Field(..., description="Metric name")
    metric_type: str = Field(..., description="Metric type (gauge, counter, histogram)")
    value: float = Field(..., description="Metric value")
    timestamp: datetime = Field(..., description="Metric timestamp")
    labels: Dict[str, str] = Field(default_factory=dict, description="Metric labels")
    unit: Optional[str] = Field(None, description="Metric unit")


class MetricCreate(MetricBase):
    pass


class Metric(MetricBase, BaseSchema):
    pass


class AlertRuleBase(BaseModel):
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
    labels: Dict[str, str] = Field(default_factory=dict, description="Alert labels")
    annotations: Dict[str, str] = Field(default_factory=dict, description="Alert annotations")


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    query: Optional[str] = None
    condition: Optional[str] = None
    threshold: Optional[float] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None
    evaluation_interval: Optional[int] = None
    for_duration: Optional[int] = None
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None


class AlertRule(AlertRuleBase, BaseSchema):
    pass


class AlertBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    rule_id: UUID = Field(..., description="Alert rule ID")
    status: str = Field(..., description="Alert status (firing, resolved)")
    severity: str = Field(..., description="Alert severity")
    message: str = Field(..., description="Alert message")
    started_at: datetime = Field(..., description="Alert start time")
    resolved_at: Optional[datetime] = Field(None, description="Alert resolution time")
    labels: Dict[str, str] = Field(default_factory=dict, description="Alert labels")
    annotations: Dict[str, str] = Field(default_factory=dict, description="Alert annotations")
    fingerprint: str = Field(..., description="Unique alert fingerprint")


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: Optional[str] = None
    resolved_at: Optional[datetime] = None
    annotations: Optional[Dict[str, str]] = None


class Alert(AlertBase, BaseSchema):
    rule: Optional[AlertRule] = None


class NotificationChannelBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., description="Channel name")
    type: str = Field(..., description="Channel type (email, slack, webhook, etc.)")
    configuration: Dict[str, Any] = Field(..., description="Channel configuration")
    enabled: bool = Field(default=True, description="Whether channel is enabled")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Notification filters")


class NotificationChannelCreate(NotificationChannelBase):
    pass


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    filters: Optional[Dict[str, Any]] = None


class NotificationChannel(NotificationChannelBase, BaseSchema):
    pass


class NotificationBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    alert_id: UUID = Field(..., description="Alert ID")
    channel_id: UUID = Field(..., description="Notification channel ID")
    status: str = Field(..., description="Notification status")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")
    delivered_at: Optional[datetime] = Field(None, description="Delivery timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Retry count")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    status: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class Notification(NotificationBase, BaseSchema):
    alert: Optional[Alert] = None
    channel: Optional[NotificationChannel] = None


class DashboardBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., description="Dashboard name")
    description: Optional[str] = Field(None, description="Dashboard description")
    layout: Dict[str, Any] = Field(..., description="Dashboard layout configuration")
    widgets: List[Dict[str, Any]] = Field(default_factory=list, description="Dashboard widgets")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Dashboard variables")
    time_range: Dict[str, Any] = Field(default_factory=dict, description="Default time range")
    refresh_interval: Optional[int] = Field(None, description="Auto-refresh interval in seconds")
    is_public: bool = Field(default=False, description="Whether dashboard is public")
    tags: List[str] = Field(default_factory=list, description="Dashboard tags")


class DashboardCreate(DashboardBase):
    pass


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    layout: Optional[Dict[str, Any]] = None
    widgets: Optional[List[Dict[str, Any]]] = None
    variables: Optional[Dict[str, Any]] = None
    time_range: Optional[Dict[str, Any]] = None
    refresh_interval: Optional[int] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None


class Dashboard(DashboardBase, BaseSchema):
    pass


class LogEntryBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    service_name: str = Field(..., description="Service name")
    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    timestamp: datetime = Field(..., description="Log timestamp")
    source: Optional[str] = Field(None, description="Log source")
    trace_id: Optional[str] = Field(None, description="Trace ID")
    span_id: Optional[str] = Field(None, description="Span ID")
    labels: Dict[str, str] = Field(default_factory=dict, description="Log labels")
    structured_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Structured log data")


class LogEntryCreate(LogEntryBase):
    pass


class LogEntry(LogEntryBase, BaseSchema):
    pass


# Response schemas
class MetricListResponse(PaginatedResponse):
    items: List[Metric]


class AlertRuleListResponse(PaginatedResponse):
    items: List[AlertRule]


class AlertListResponse(PaginatedResponse):
    items: List[Alert]


class NotificationChannelListResponse(PaginatedResponse):
    items: List[NotificationChannel]


class NotificationListResponse(PaginatedResponse):
    items: List[Notification]


class DashboardListResponse(PaginatedResponse):
    items: List[Dashboard]


class LogEntryListResponse(PaginatedResponse):
    items: List[LogEntry]


# Complex query schemas
class MetricQuery(BaseModel):
    query: str = Field(..., description="Metric query")
    start_time: datetime = Field(..., description="Query start time")
    end_time: datetime = Field(..., description="Query end time")
    step: Optional[int] = Field(None, description="Query step in seconds")
    labels: Optional[Dict[str, str]] = Field(default_factory=dict, description="Additional labels")


class MetricQueryResult(BaseModel):
    metric: Dict[str, str] = Field(..., description="Metric labels")
    values: List[List[Union[float, str]]] = Field(..., description="Time series values")


class MetricQueryResponse(BaseModel):
    status: str = Field(..., description="Query status")
    data: Dict[str, Any] = Field(..., description="Query result data")
    query: str = Field(..., description="Original query")
    execution_time: float = Field(..., description="Query execution time")


class LogQuery(BaseModel):
    query: str = Field(..., description="Log query")
    start_time: datetime = Field(..., description="Query start time")
    end_time: datetime = Field(..., description="Query end time")
    limit: int = Field(default=1000, description="Maximum number of log entries")
    labels: Optional[Dict[str, str]] = Field(default_factory=dict, description="Label filters")


class ServiceHealthStatus(BaseModel):
    service_name: str
    status: str
    uptime_percentage: float
    error_rate: float
    response_time_p95: float
    last_deployment: Optional[datetime]
    active_alerts: int
    resource_usage: Dict[str, float]


class TenantMonitoringOverview(BaseModel):
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
    service_health: List[ServiceHealthStatus]
    recent_alerts: List[Alert]


# Synthetic monitoring schemas
class SyntheticCheckBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., description="Check name")
    type: str = Field(..., description="Check type (http, tcp, dns, etc.)")
    target: str = Field(..., description="Check target (URL, hostname, etc.)")
    configuration: Dict[str, Any] = Field(..., description="Check configuration")
    interval: int = Field(default=300, description="Check interval in seconds")
    timeout: int = Field(default=30, description="Check timeout in seconds")
    enabled: bool = Field(default=True, description="Whether check is enabled")
    locations: List[str] = Field(default_factory=list, description="Check locations")


class SyntheticCheckCreate(SyntheticCheckBase):
    pass


class SyntheticCheckUpdate(BaseModel):
    name: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    interval: Optional[int] = None
    timeout: Optional[int] = None
    enabled: Optional[bool] = None
    locations: Optional[List[str]] = None


class SyntheticCheck(SyntheticCheckBase, BaseSchema):
    pass


class SyntheticCheckResultBase(BaseModel):
    check_id: UUID = Field(..., description="Synthetic check ID")
    status: str = Field(..., description="Check status")
    response_time: float = Field(..., description="Response time in milliseconds")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    location: str = Field(..., description="Check location")
    timestamp: datetime = Field(..., description="Check timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class SyntheticCheckResultCreate(SyntheticCheckResultBase):
    pass


class SyntheticCheckResult(SyntheticCheckResultBase, BaseSchema):
    check: Optional[SyntheticCheck] = None