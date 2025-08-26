"""Analytics schemas for API requests and responses."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from dotmac_isp.shared.schemas import TenantModelSchema


class MetricDataPoint(BaseModel):
    """Schema for metric data points used in analytics and reporting."""

    timestamp: datetime = Field(..., description="Data point timestamp")
    value: float = Field(..., description="Metric value")
    metric_name: str = Field(..., description="Name of the metric")
    dimensions: Optional[Dict[str, Any]] = Field(
        None, description="Additional dimensions/tags"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

class MetricType(str, Enum):
    """Available metric types for analytics."""

    BANDWIDTH = "bandwidth"
    REVENUE = "revenue"
    CUSTOMER_COUNT = "customer_count"
    SERVICE_UPTIME = "service_uptime"
    SUPPORT_TICKETS = "support_tickets"
    NETWORK_LATENCY = "network_latency"
    DATA_USAGE = "data_usage"


class ReportType(str, Enum):
    """Available report types."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricBase(BaseModel):
    """Base metric schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Metric name")
    display_name: str = Field(
        ..., min_length=1, max_length=255, description="Display name"
    )
    description: Optional[str] = Field(None, description="Metric description")
    metric_type: MetricType = Field(..., description="Metric type")
    unit: Optional[str] = Field(None, max_length=50, description="Unit of measurement")
    calculation_config: Optional[Dict[str, Any]] = Field(
        None, description="Calculation configuration"
    )
    dimensions: Optional[List[str]] = Field(None, description="Metric dimensions")
    tags: Optional[Dict[str, Any]] = Field(None, description="Metric tags")


class ServiceAnalyticsResponse(BaseModel):
    """Response schema for service analytics data."""

    service_id: str = Field(..., description="Service identifier")
    service_name: str = Field(..., description="Service name")
    metrics: Dict[str, Any] = Field(..., description="Service metrics data")
    period: str = Field(..., description="Time period for metrics")
    period_start: datetime = Field(..., description="Period start time")
    period_end: datetime = Field(..., description="Period end time")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(), description="Response generation time"
    )
    total_customers: Optional[int] = Field(
        None, description="Total customers using service"
    )
    revenue: Optional[float] = Field(None, description="Revenue for the period")
    uptime_percentage: Optional[float] = Field(
        None, description="Service uptime percentage"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

class ServiceMetricsRequest(BaseModel):
    """Request schema for service metrics."""

    service_id: str = Field(..., description="Service identifier")
    start_date: Optional[datetime] = Field(None, description="Start date for metrics")
    end_date: Optional[datetime] = Field(None, description="End date for metrics")
    metric_types: Optional[List[MetricType]] = Field(
        None, description="Specific metrics to include"
    )
    granularity: Optional[str] = Field(
        "daily", description="Data granularity (hourly, daily, weekly)"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

class CustomReportRequest(BaseModel):
    """Request schema for custom reports."""

    report_name: str = Field(..., description="Name of the report")
    report_type: ReportType = Field(..., description="Type of report")
    start_date: datetime = Field(..., description="Start date for report data")
    end_date: datetime = Field(..., description="End date for report data")
    metric_types: List[MetricType] = Field(
        ..., description="Metrics to include in report"
    )
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")
    format: str = Field("json", description="Output format (json, csv, pdf)")
    include_charts: bool = Field(True, description="Include charts in report")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

class CustomReportResponse(BaseModel):
    """Response schema for custom reports."""

    report_id: str = Field(..., description="Generated report ID")
    report_name: str = Field(..., description="Name of the report")
    status: str = Field(..., description="Report generation status")
    data: Dict[str, Any] = Field(..., description="Report data")
    generated_at: datetime = Field(..., description="Generation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Report expiration")
    download_url: Optional[str] = Field(None, description="Download URL for report")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

class RealTimeMetricsResponse(BaseModel):
    """Response schema for real-time metrics."""

    timestamp: datetime = Field(..., description="Metrics timestamp")
    metrics: Dict[str, Any] = Field(..., description="Current metrics data")
    health_status: str = Field(..., description="Overall system health")
    active_connections: int = Field(..., description="Active connections count")
    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(None, description="Memory usage percentage")
    network_throughput: Optional[Dict[str, float]] = Field(
        None, description="Network throughput stats"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

class MetricCreate(MetricBase):
    """Schema for creating metrics."""

    pass


class MetricUpdate(BaseModel):
    """Schema for updating metrics."""

    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    unit: Optional[str] = Field(None, max_length=50)
    calculation_config: Optional[Dict[str, Any]] = None
    dimensions: Optional[List[str]] = None
    tags: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    refresh_interval: Optional[int] = Field(None, ge=1)
    retention_days: Optional[int] = Field(None, ge=1, le=365)


class MetricResponse(MetricBase):
    """Schema for metric responses."""

    id: str = Field(..., description="Metric ID")
    tenant_id: str = Field(..., description="Tenant ID")
    latest_value: Optional[float] = Field(None, description="Latest metric value")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class MetricValueBase(BaseModel):
    """Base metric value schema."""

    value: float = Field(..., description="Metric value")
    timestamp: datetime = Field(..., description="Value timestamp")
    dimensions: Optional[Dict[str, Any]] = Field(None, description="Value dimensions")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class MetricValueCreate(MetricValueBase):
    """Schema for creating metric values."""

    metric_id: str = Field(..., description="Metric ID")


class MetricValueResponse(MetricValueBase):
    """Schema for metric value responses."""

    id: str = Field(..., description="Value ID")
    metric_id: str = Field(..., description="Metric ID")
    tenant_id: str = Field(..., description="Tenant ID")

    model_config = ConfigDict(from_attributes=True)


class ReportBase(BaseModel):
    """Base report schema."""

    title: str = Field(..., min_length=1, max_length=200, description="Report title")
    description: Optional[str] = Field(None, description="Report description")
    report_type: ReportType = Field(..., description="Report type")
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    filters: Optional[Dict[str, Any]] = Field(None, description="Report filters")
    format_config: Optional[Dict[str, Any]] = Field(
        None, description="Format configuration"
    )
    is_scheduled: bool = Field(False, description="Scheduled report flag")
    schedule_config: Optional[Dict[str, Any]] = Field(
        None, description="Schedule configuration"
    )
    is_public: bool = Field(False, description="Public access flag")


class ReportCreate(ReportBase):
    """Schema for creating reports."""

    pass


class ReportUpdate(BaseModel):
    """Schema for updating reports."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    format_config: Optional[Dict[str, Any]] = None
    is_scheduled: Optional[bool] = None
    schedule_config: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None


class ReportResponse(ReportBase):
    """Schema for report responses."""

    id: str = Field(..., description="Report ID")
    tenant_id: str = Field(..., description="Tenant ID")
    generated_at: datetime = Field(..., description="Generation timestamp")
    data: Dict[str, Any] = Field(..., description="Report data")
    duration_days: int = Field(..., description="Report duration in days")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class DashboardBase(BaseModel):
    """Base dashboard schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Dashboard name")
    description: Optional[str] = Field(None, description="Dashboard description")
    layout: Optional[Dict[str, Any]] = Field(None, description="Dashboard layout")
    is_public: bool = Field(False, description="Public access flag")
    refresh_rate: int = Field(30, ge=1, description="Refresh rate in seconds")
    theme_config: Optional[Dict[str, Any]] = Field(
        None, description="Theme configuration"
    )
    access_permissions: Optional[List[str]] = Field(
        None, description="Access permissions"
    )


class DashboardCreate(DashboardBase):
    """Schema for creating dashboards."""

    pass


class DashboardUpdate(BaseModel):
    """Schema for updating dashboards."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    layout: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    refresh_rate: Optional[int] = Field(None, ge=1)
    theme_config: Optional[Dict[str, Any]] = None
    access_permissions: Optional[List[str]] = None


class DashboardResponse(DashboardBase):
    """Schema for dashboard responses."""

    id: str = Field(..., description="Dashboard ID")
    tenant_id: str = Field(..., description="Tenant ID")
    widget_count: int = Field(..., description="Widget count")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class WidgetBase(BaseModel):
    """Base widget schema."""

    widget_type: str = Field(
        ..., min_length=1, max_length=50, description="Widget type"
    )
    title: str = Field(..., min_length=1, max_length=100, description="Widget title")
    position: int = Field(..., ge=0, description="Widget position")
    config: Optional[Dict[str, Any]] = Field(None, description="Widget configuration")
    data_source: Optional[Dict[str, Any]] = Field(
        None, description="Data source configuration"
    )
    style_config: Optional[Dict[str, Any]] = Field(
        None, description="Style configuration"
    )
    is_visible: bool = Field(True, description="Visibility flag")
    refresh_interval: int = Field(60, ge=1, description="Refresh interval in seconds")


class WidgetCreate(WidgetBase):
    """Schema for creating widgets."""

    dashboard_id: str = Field(..., description="Dashboard ID")


class WidgetUpdate(BaseModel):
    """Schema for updating widgets."""

    widget_type: Optional[str] = Field(None, min_length=1, max_length=50)
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    position: Optional[int] = Field(None, ge=0)
    config: Optional[Dict[str, Any]] = None
    data_source: Optional[Dict[str, Any]] = None
    style_config: Optional[Dict[str, Any]] = None
    is_visible: Optional[bool] = None
    refresh_interval: Optional[int] = Field(None, ge=1)


class WidgetResponse(WidgetBase):
    """Schema for widget responses."""

    id: str = Field(..., description="Widget ID")
    dashboard_id: str = Field(..., description="Dashboard ID")
    tenant_id: str = Field(..., description="Tenant ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class AlertBase(BaseModel):
    """Base alert schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Alert name")
    condition: str = Field(
        ..., pattern=r"^(greater_than|less_than|equals)$", description="Alert condition"
    )
    threshold: float = Field(..., description="Alert threshold")
    severity: AlertSeverity = Field(..., description="Alert severity")
    notification_channels: Optional[List[str]] = Field(
        None, description="Notification channels"
    )
    condition_config: Optional[Dict[str, Any]] = Field(
        None, description="Condition configuration"
    )
    is_active: bool = Field(True, description="Active status")


class AlertCreate(AlertBase):
    """Schema for creating alerts."""

    metric_id: str = Field(..., description="Metric ID")


class AlertUpdate(BaseModel):
    """Schema for updating alerts."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    condition: Optional[str] = Field(None, pattern=r"^(greater_than|less_than|equals)$")
    threshold: Optional[float] = None
    severity: Optional[AlertSeverity] = None
    notification_channels: Optional[List[str]] = None
    condition_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AlertResponse(AlertBase):
    """Schema for alert responses."""

    id: str = Field(..., description="Alert ID")
    metric_id: str = Field(..., description="Metric ID")
    tenant_id: str = Field(..., description="Tenant ID")
    last_triggered: Optional[datetime] = Field(
        None, description="Last trigger timestamp"
    )
    trigger_count: int = Field(..., description="Trigger count")
    priority_score: int = Field(..., description="Priority score")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class DataSourceBase(BaseModel):
    """Base data source schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Data source name")
    source_type: str = Field(
        ..., min_length=1, max_length=50, description="Source type"
    )
    connection_config: Optional[Dict[str, Any]] = Field(
        None, description="Connection configuration"
    )
    query_config: Optional[Dict[str, Any]] = Field(
        None, description="Query configuration"
    )
    refresh_schedule: Optional[str] = Field(None, description="Refresh schedule (cron)")
    data_mapping: Optional[Dict[str, Any]] = Field(None, description="Data mapping")
    is_active: bool = Field(True, description="Active status")


class DataSourceCreate(DataSourceBase):
    """Schema for creating data sources."""

    pass


class DataSourceUpdate(BaseModel):
    """Schema for updating data sources."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    connection_config: Optional[Dict[str, Any]] = None
    query_config: Optional[Dict[str, Any]] = None
    refresh_schedule: Optional[str] = None
    data_mapping: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class DataSourceResponse(DataSourceBase):
    """Schema for data source responses."""

    id: str = Field(..., description="Data source ID")
    tenant_id: str = Field(..., description="Tenant ID")
    last_sync: Optional[datetime] = Field(None, description="Last sync timestamp")
    sync_status: str = Field(..., description="Sync status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class AnalyticsOverviewResponse(BaseModel):
    """Schema for analytics overview."""

    metrics_count: int = Field(..., ge=0, description="Total metrics count")
    reports_count: int = Field(..., ge=0, description="Total reports count")
    dashboards_count: int = Field(..., ge=0, description="Total dashboards count")
    active_alerts_count: int = Field(..., ge=0, description="Active alerts count")
    key_metrics: Dict[str, Any] = Field(..., description="Key performance metrics")
    recent_activity: List[Dict[str, Any]] = Field(..., description="Recent activity")


class MetricAggregationRequest(BaseModel):
    """Schema for metric aggregation requests."""

    metric_id: str = Field(..., description="Metric ID")
    aggregation_type: str = Field(
        ..., pattern=r"^(avg|sum|min|max|count)$", description="Aggregation type"
    )
    period: str = Field(
        ..., pattern=r"^(hour|day|week|month)$", description="Aggregation period"
    )
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    group_by: Optional[List[str]] = Field(None, description="Group by dimensions")


class MetricAggregationResponse(BaseModel):
    """Schema for metric aggregation responses."""

    metric_id: str = Field(..., description="Metric ID")
    aggregation_type: str = Field(..., description="Aggregation type")
    period: str = Field(..., description="Aggregation period")
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    data_points: List[Dict[str, Any]] = Field(..., description="Aggregated data points")
    summary: Dict[str, float] = Field(..., description="Summary statistics")


class ReportExportRequest(BaseModel):
    """Schema for report export requests."""

    report_id: str = Field(..., description="Report ID")
    format_type: str = Field(
        ..., pattern=r"^(json|csv|pdf|excel)$", description="Export format"
    )
    include_raw_data: bool = Field(False, description="Include raw data")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")


class ReportExportResponse(BaseModel):
    """Schema for report export responses."""

    export_id: str = Field(..., description="Export ID")
    report_id: str = Field(..., description="Report ID")
    format_type: str = Field(..., description="Export format")
    status: str = Field(..., description="Export status")
    download_url: Optional[str] = Field(None, description="Download URL")
    expires_at: Optional[datetime] = Field(None, description="Download expiration")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")


class DashboardMetricsResponse(BaseModel):
    """Schema for dashboard metrics."""

    total_views: int = Field(..., ge=0, description="Total dashboard views")
    unique_users: int = Field(..., ge=0, description="Unique users")
    avg_session_duration: float = Field(
        ..., ge=0, description="Average session duration"
    )
    bounce_rate: float = Field(..., ge=0, le=100, description="Bounce rate percentage")
    most_viewed_widgets: List[Dict[str, Any]] = Field(
        ..., description="Most viewed widgets"
    )
    performance_metrics: Dict[str, float] = Field(
        ..., description="Performance metrics"
    )


class AlertTestRequest(BaseModel):
    """Schema for testing alert conditions."""

    alert_id: str = Field(..., description="Alert ID")
    test_value: float = Field(..., description="Test value")
    simulate_trigger: bool = Field(False, description="Simulate trigger action")


class AlertTestResponse(BaseModel):
    """Schema for alert test responses."""

    alert_id: str = Field(..., description="Alert ID")
    test_value: float = Field(..., description="Test value")
    would_trigger: bool = Field(..., description="Would alert trigger")
    threshold: float = Field(..., description="Alert threshold")
    condition: str = Field(..., description="Alert condition")
    severity: AlertSeverity = Field(..., description="Alert severity")
    notification_channels: List[str] = Field(..., description="Notification channels")


class DashboardOverviewResponse(BaseModel):
    """Schema for dashboard overview response."""

    total_customers: int = Field(..., ge=0, description="Total customer count")
    total_revenue: float = Field(..., ge=0, description="Total revenue")
    active_services: int = Field(..., ge=0, description="Active services count")
    support_tickets: int = Field(..., ge=0, description="Open support tickets")
    network_uptime: float = Field(
        ..., ge=0, le=100, description="Network uptime percentage"
    )
    bandwidth_usage: float = Field(..., ge=0, description="Bandwidth usage in GB")
    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")
    trends: Dict[str, Any] = Field(..., description="Trend data")
    alerts: List[Dict[str, Any]] = Field(..., description="Recent alerts")


class ExecutiveReportResponse(BaseModel):
    """Schema for executive report response."""

    report_id: str = Field(..., description="Report ID")
    generated_at: datetime = Field(..., description="Generation timestamp")
    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")
    executive_summary: Dict[str, Any] = Field(..., description="Executive summary")
    financial_metrics: Dict[str, Any] = Field(..., description="Financial metrics")
    operational_metrics: Dict[str, Any] = Field(..., description="Operational metrics")
    customer_metrics: Dict[str, Any] = Field(..., description="Customer metrics")
    network_metrics: Dict[str, Any] = Field(..., description="Network metrics")
    recommendations: List[Dict[str, Any]] = Field(
        ..., description="Strategic recommendations"
    )


class CustomerAnalyticsResponse(BaseModel):
    """Schema for customer analytics response."""

    customer_id: str = Field(..., description="Customer ID")
    total_revenue: float = Field(..., ge=0, description="Total revenue from customer")
    monthly_recurring_revenue: float = Field(
        ..., ge=0, description="Monthly recurring revenue"
    )
    lifetime_value: float = Field(..., ge=0, description="Customer lifetime value")
    service_count: int = Field(..., ge=0, description="Number of active services")
    support_tickets: int = Field(..., ge=0, description="Number of support tickets")
    payment_history: Dict[str, Any] = Field(..., description="Payment history summary")
    usage_metrics: Dict[str, Any] = Field(..., description="Usage metrics")
    churn_risk_score: float = Field(..., ge=0, le=100, description="Churn risk score")
    satisfaction_score: Optional[float] = Field(
        None, ge=0, le=10, description="Customer satisfaction score"
    )
    acquisition_date: datetime = Field(..., description="Customer acquisition date")
    last_activity: Optional[datetime] = Field(
        None, description="Last activity timestamp"
    )


class RevenueAnalyticsResponse(BaseModel):
    """Schema for revenue analytics response."""

    period_start: datetime = Field(..., description="Analysis period start")
    period_end: datetime = Field(..., description="Analysis period end")
    total_revenue: float = Field(..., ge=0, description="Total revenue for period")
    recurring_revenue: float = Field(..., ge=0, description="Monthly recurring revenue")
    one_time_revenue: float = Field(..., ge=0, description="One-time revenue")
    growth_rate: float = Field(..., description="Revenue growth rate percentage")
    average_revenue_per_user: float = Field(..., ge=0, description="ARPU")
    revenue_by_service: Dict[str, float] = Field(
        ..., description="Revenue breakdown by service type"
    )
    revenue_by_region: Dict[str, float] = Field(
        ..., description="Revenue breakdown by region"
    )
    top_customers: List[Dict[str, Any]] = Field(
        ..., description="Top revenue generating customers"
    )
    churn_impact: float = Field(..., description="Revenue impact from churn")
    forecasted_revenue: Optional[float] = Field(
        None, ge=0, description="Forecasted revenue for next period"
    )
