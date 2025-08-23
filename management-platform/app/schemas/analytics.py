"""
Analytics and reporting schemas for validation and serialization.
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, validator

from .common import BaseSchema


class AnalyticsTimeframe(str, Enum):
    """Analytics timeframe options."""
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    LAST_6_MONTHS = "last_6_months"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


class MetricType(str, Enum):
    """Metric types for analytics."""
    REVENUE = "revenue"
    USAGE = "usage"
    USER_ACTIVITY = "user_activity"
    PERFORMANCE = "performance"
    INFRASTRUCTURE = "infrastructure"
    NOTIFICATIONS = "notifications"


class ReportFormat(str, Enum):
    """Report output formats."""
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class ChartType(str, Enum):
    """Chart types for visualization."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"


class AnalyticsFilter(BaseModel):
    """Analytics filter schema."""
    field: str = Field(..., description="Field to filter on")
    operator: str = Field(..., description="Filter operator (eq, ne, gt, gte, lt, lte, in, not_in, like)")
    value: Union[str, int, float, List[Any]] = Field(..., description="Filter value")
    
    @validator('operator')
    def validate_operator(cls, v):
        valid_operators = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'not_in', 'like']
        if v not in valid_operators:
            raise ValueError(f"Operator must be one of: {', '.join(valid_operators)}")
        return v


class AnalyticsQuery(BaseModel):
    """Analytics query schema."""
    name: str = Field(..., description="Query name")
    metric_type: MetricType = Field(..., description="Type of metric to analyze")
    start_date: datetime = Field(..., description="Start date for analysis")
    end_date: datetime = Field(..., description="End date for analysis")
    tenant_id: Optional[UUID] = Field(None, description="Optional tenant filter")
    filters: Optional[List[AnalyticsFilter]] = Field(None, description="Additional filters")
    group_by: Optional[List[str]] = Field(None, description="Fields to group by")
    aggregation: Optional[str] = Field("sum", description="Aggregation method")
    format: ReportFormat = Field(default=ReportFormat.JSON, description="Output format")
    save_report: bool = Field(default=False, description="Whether to save the report")
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError("End date must be after start date")
        return v


class TimeSeriesDataPoint(BaseModel):
    """Time series data point schema."""
    timestamp: datetime = Field(..., description="Data point timestamp")
    value: float = Field(..., description="Data point value")
    label: Optional[str] = Field(None, description="Data point label")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MetricSummary(BaseModel):
    """Metric summary schema."""
    current_value: float = Field(..., description="Current metric value")
    previous_value: Optional[float] = Field(None, description="Previous period value")
    change_percentage: Optional[float] = Field(None, description="Percentage change")
    change_absolute: Optional[float] = Field(None, description="Absolute change")
    trend: Optional[str] = Field(None, description="Trend direction (up, down, stable)")


class KPI(BaseModel):
    """Key Performance Indicator schema."""
    name: str = Field(..., description="KPI name")
    display_name: str = Field(..., description="Human-readable KPI name")
    value: float = Field(..., description="Current KPI value")
    target: Optional[float] = Field(None, description="Target value")
    unit: str = Field(..., description="Unit of measurement")
    format: str = Field(default="number", description="Display format")
    summary: MetricSummary = Field(..., description="Metric summary")
    chart_data: Optional[List[TimeSeriesDataPoint]] = Field(None, description="Chart data")


class TenantAnalytics(BaseModel):
    """Tenant analytics schema."""
    tenant_id: Optional[UUID] = Field(None, description="Tenant identifier")
    period: Dict[str, str] = Field(..., description="Analysis period")
    total_tenants: int = Field(..., description="Total number of tenants")
    active_tenants: int = Field(..., description="Number of active tenants")
    new_tenants: int = Field(..., description="New tenants in period")
    churn_rate: float = Field(..., description="Tenant churn rate")
    growth_metrics: List[TimeSeriesDataPoint] = Field(..., description="Growth over time")
    top_tenants: List[Dict[str, Any]] = Field(..., description="Top performing tenants")


class UserAnalytics(BaseModel):
    """User analytics schema."""
    period: Dict[str, str] = Field(..., description="Analysis period")
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    new_users: int = Field(..., description="New users in period")
    user_growth: List[TimeSeriesDataPoint] = Field(..., description="User growth over time")
    activity_patterns: Dict[str, Any] = Field(..., description="User activity patterns")
    retention_metrics: Dict[str, float] = Field(..., description="User retention metrics")


class RevenueAnalytics(BaseModel):
    """Revenue analytics schema."""
    period: Dict[str, str] = Field(..., description="Analysis period")
    total_revenue: float = Field(..., description="Total revenue")
    mrr: float = Field(..., description="Monthly recurring revenue")
    arr: float = Field(..., description="Annual recurring revenue")
    growth_rate: float = Field(..., description="Revenue growth rate")
    revenue_by_period: List[TimeSeriesDataPoint] = Field(..., description="Revenue over time")
    revenue_by_plan: Dict[str, float] = Field(..., description="Revenue by billing plan")
    churn_analysis: Dict[str, Any] = Field(..., description="Revenue churn analysis")
    cohort_analysis: Dict[str, Any] = Field(..., description="Revenue cohort analysis")


class UsageAnalytics(BaseModel):
    """Usage analytics schema."""
    period: Dict[str, str] = Field(..., description="Analysis period")
    infrastructure_usage: Dict[str, Any] = Field(..., description="Infrastructure usage metrics")
    api_usage: Dict[str, Any] = Field(..., description="API usage metrics")
    notification_usage: Dict[str, Any] = Field(..., description="Notification usage metrics")
    storage_usage: Dict[str, Any] = Field(..., description="Storage usage metrics")
    peak_usage: Dict[str, Any] = Field(..., description="Peak usage analysis")
    usage_trends: List[TimeSeriesDataPoint] = Field(..., description="Usage trends over time")


class PerformanceMetrics(BaseModel):
    """Performance metrics schema."""
    period: Dict[str, str] = Field(..., description="Analysis period")
    response_times: Dict[str, float] = Field(..., description="Response time metrics")
    error_rates: Dict[str, float] = Field(..., description="Error rate metrics")
    throughput: Dict[str, float] = Field(..., description="Throughput metrics")
    uptime: float = Field(..., description="System uptime percentage")
    resource_utilization: Dict[str, float] = Field(..., description="Resource utilization")
    external_services: Dict[str, Dict[str, float]] = Field(..., description="External service metrics")


class CustomReport(BaseModel):
    """Custom report schema."""
    report_id: UUID = Field(..., description="Report identifier")
    name: str = Field(..., description="Report name")
    description: Optional[str] = Field(None, description="Report description")
    query: AnalyticsQuery = Field(..., description="Report query configuration")
    data: Dict[str, Any] = Field(..., description="Report data")
    visualization: Optional[Dict[str, Any]] = Field(None, description="Visualization configuration")
    created_by: UUID = Field(..., description="User who created the report")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_run: Optional[datetime] = Field(None, description="Last execution timestamp")
    is_scheduled: bool = Field(default=False, description="Whether report is scheduled")
    schedule: Optional[str] = Field(None, description="Schedule configuration")


class ReportSchedule(BaseModel):
    """Report schedule schema."""
    schedule_id: UUID = Field(..., description="Schedule identifier")
    report_id: UUID = Field(..., description="Report identifier")
    frequency: str = Field(..., description="Schedule frequency (daily, weekly, monthly)")
    time: str = Field(..., description="Execution time (HH:MM format)")
    timezone: str = Field(default="UTC", description="Timezone for schedule")
    recipients: List[str] = Field(..., description="Email recipients")
    is_active: bool = Field(default=True, description="Whether schedule is active")
    next_run: datetime = Field(..., description="Next scheduled run")
    last_run: Optional[datetime] = Field(None, description="Last execution timestamp")


class AnalyticsDashboard(BaseModel):
    """Analytics dashboard schema."""
    dashboard_id: UUID = Field(..., description="Dashboard identifier")
    name: str = Field(..., description="Dashboard name")
    description: Optional[str] = Field(None, description="Dashboard description")
    widgets: List[Dict[str, Any]] = Field(..., description="Dashboard widgets")
    layout: Dict[str, Any] = Field(..., description="Dashboard layout configuration")
    filters: Optional[List[AnalyticsFilter]] = Field(None, description="Global dashboard filters")
    refresh_interval: Optional[int] = Field(None, description="Auto-refresh interval in seconds")
    is_public: bool = Field(default=False, description="Whether dashboard is publicly accessible")
    created_by: UUID = Field(..., description="User who created the dashboard")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class DashboardWidget(BaseModel):
    """Dashboard widget schema."""
    widget_id: UUID = Field(..., description="Widget identifier")
    dashboard_id: UUID = Field(..., description="Parent dashboard identifier")
    name: str = Field(..., description="Widget name")
    type: str = Field(..., description="Widget type (chart, metric, table)")
    query: AnalyticsQuery = Field(..., description="Widget data query")
    visualization: Dict[str, Any] = Field(..., description="Visualization configuration")
    position: Dict[str, int] = Field(..., description="Widget position and size")
    refresh_interval: Optional[int] = Field(None, description="Widget refresh interval")
    is_active: bool = Field(default=True, description="Whether widget is active")


class ExportRequest(BaseModel):
    """Data export request schema."""
    export_type: str = Field(..., description="Type of data to export")
    format: ReportFormat = Field(..., description="Export format")
    filters: Optional[List[AnalyticsFilter]] = Field(None, description="Export filters")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    include_metadata: bool = Field(default=True, description="Include metadata in export")
    compression: bool = Field(default=False, description="Compress export file")


class ExportJob(BaseModel):
    """Data export job schema."""
    job_id: UUID = Field(..., description="Export job identifier")
    export_request: ExportRequest = Field(..., description="Export request configuration")
    status: str = Field(..., description="Job status (pending, running, completed, failed)")
    progress: float = Field(default=0.0, description="Job progress percentage")
    file_url: Optional[str] = Field(None, description="Download URL for completed export")
    file_size: Optional[int] = Field(None, description="Export file size in bytes")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    created_by: UUID = Field(..., description="User who requested the export")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    expires_at: Optional[datetime] = Field(None, description="Download link expiration")


class AnalyticsAlert(BaseModel):
    """Analytics alert schema."""
    alert_id: UUID = Field(..., description="Alert identifier")
    name: str = Field(..., description="Alert name")
    description: Optional[str] = Field(None, description="Alert description")
    metric_query: AnalyticsQuery = Field(..., description="Metric query for alert")
    threshold: float = Field(..., description="Alert threshold value")
    operator: str = Field(..., description="Comparison operator (gt, gte, lt, lte, eq, ne)")
    severity: str = Field(..., description="Alert severity (low, medium, high, critical)")
    notification_channels: List[str] = Field(..., description="Notification channels")
    is_active: bool = Field(default=True, description="Whether alert is active")
    created_by: UUID = Field(..., description="User who created the alert")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_triggered: Optional[datetime] = Field(None, description="Last trigger timestamp")
    trigger_count: int = Field(default=0, description="Number of times alert has triggered")


class AlertTrigger(BaseModel):
    """Alert trigger event schema."""
    trigger_id: UUID = Field(..., description="Trigger identifier")
    alert_id: UUID = Field(..., description="Alert identifier")
    metric_value: float = Field(..., description="Metric value that triggered alert")
    threshold_value: float = Field(..., description="Alert threshold value")
    severity: str = Field(..., description="Alert severity")
    message: str = Field(..., description="Alert message")
    triggered_at: datetime = Field(..., description="Trigger timestamp")
    acknowledged_at: Optional[datetime] = Field(None, description="Acknowledgment timestamp")
    acknowledged_by: Optional[UUID] = Field(None, description="User who acknowledged alert")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    status: str = Field(default="active", description="Trigger status (active, acknowledged, resolved)")


class MetricDefinition(BaseModel):
    """Metric definition schema."""
    metric_id: UUID = Field(..., description="Metric identifier")
    name: str = Field(..., description="Metric name")
    display_name: str = Field(..., description="Human-readable metric name")
    description: str = Field(..., description="Metric description")
    unit: str = Field(..., description="Unit of measurement")
    data_type: str = Field(..., description="Data type (number, percentage, currency)")
    category: str = Field(..., description="Metric category")
    aggregation_method: str = Field(..., description="Default aggregation method")
    calculation_logic: str = Field(..., description="Calculation logic description")
    is_custom: bool = Field(default=False, description="Whether this is a custom metric")
    created_by: Optional[UUID] = Field(None, description="User who created the metric")
    created_at: datetime = Field(..., description="Creation timestamp")


class DataSource(BaseModel):
    """Data source schema for analytics."""
    source_id: UUID = Field(..., description="Data source identifier")
    name: str = Field(..., description="Data source name")
    type: str = Field(..., description="Data source type (database, api, file)")
    connection_config: Dict[str, Any] = Field(..., description="Connection configuration")
    schema_mapping: Dict[str, str] = Field(..., description="Schema field mapping")
    refresh_schedule: Optional[str] = Field(None, description="Data refresh schedule")
    last_refresh: Optional[datetime] = Field(None, description="Last refresh timestamp")
    is_active: bool = Field(default=True, description="Whether data source is active")
    created_by: UUID = Field(..., description="User who created the data source")
    created_at: datetime = Field(..., description="Creation timestamp")


class AnalyticsConfig(BaseModel):
    """Analytics configuration schema."""
    config_id: UUID = Field(..., description="Configuration identifier")
    tenant_id: Optional[UUID] = Field(None, description="Tenant identifier (global if None)")
    retention_days: int = Field(default=90, description="Data retention period in days")
    sampling_rate: float = Field(default=1.0, description="Data sampling rate (0.0-1.0)")
    aggregation_intervals: List[str] = Field(default=["hour", "day", "week"], description="Aggregation intervals")
    custom_dimensions: List[str] = Field(default_factory=list, description="Custom dimension fields")
    privacy_settings: Dict[str, bool] = Field(default_factory=dict, description="Privacy settings")
    export_limits: Dict[str, int] = Field(default_factory=dict, description="Export size limits")
    created_by: UUID = Field(..., description="User who created the configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class AnalyticsInsight(BaseModel):
    """Analytics insight schema."""
    insight_id: UUID = Field(..., description="Insight identifier")
    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Insight description")
    insight_type: str = Field(..., description="Type of insight (anomaly, trend, recommendation)")
    severity: str = Field(..., description="Insight severity (low, medium, high)")
    metric_affected: str = Field(..., description="Affected metric")
    confidence_score: float = Field(..., description="Confidence score (0.0-1.0)")
    data_points: List[TimeSeriesDataPoint] = Field(..., description="Supporting data points")
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions")
    generated_at: datetime = Field(..., description="Generation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Insight expiration")
    is_acknowledged: bool = Field(default=False, description="Whether insight is acknowledged")
    acknowledged_by: Optional[UUID] = Field(None, description="User who acknowledged insight")


class AnalyticsSummary(BaseModel):
    """Analytics summary schema."""
    period: Dict[str, str] = Field(..., description="Summary period")
    tenant_id: Optional[UUID] = Field(None, description="Tenant identifier")
    kpis: List[KPI] = Field(..., description="Key performance indicators")
    insights: List[AnalyticsInsight] = Field(..., description="Generated insights")
    alerts: List[AlertTrigger] = Field(..., description="Active alerts")
    trends: Dict[str, str] = Field(..., description="Key trends summary")
    generated_at: datetime = Field(..., description="Summary generation timestamp")