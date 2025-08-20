"""
Enums for DotMac Analytics models.
"""

from enum import Enum


class EventType(str, Enum):
    """Analytics event types."""
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    BUSINESS_EVENT = "business_event"
    PERFORMANCE_METRIC = "performance_metric"
    NETWORK_EVENT = "network_event"
    BILLING_EVENT = "billing_event"
    CUSTOMER_EVENT = "customer_event"
    SERVICE_EVENT = "service_event"


class MetricType(str, Enum):
    """Metric data types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    RATE = "rate"
    PERCENTAGE = "percentage"
    DURATION = "duration"
    SIZE = "size"


class MetricAggregation(str, Enum):
    """Metric aggregation methods."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    DISTINCT_COUNT = "distinct_count"
    MEDIAN = "median"
    PERCENTILE_95 = "p95"
    PERCENTILE_99 = "p99"
    STDDEV = "stddev"


class DataSourceType(str, Enum):
    """Data source types."""
    DATABASE = "database"
    API = "api"
    FILE = "file"
    STREAM = "stream"
    WEBHOOK = "webhook"
    LOG = "log"
    METRIC = "metric"
    EVENT = "event"


class WidgetType(str, Enum):
    """Dashboard widget types."""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    AREA_CHART = "area_chart"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"
    TABLE = "table"
    METRIC_CARD = "metric_card"
    GAUGE = "gauge"
    MAP = "map"
    FUNNEL = "funnel"
    COHORT = "cohort"


class ReportType(str, Enum):
    """Report types."""
    EXECUTIVE_SUMMARY = "executive_summary"
    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    CUSTOMER_ANALYTICS = "customer_analytics"
    NETWORK_PERFORMANCE = "network_performance"
    SERVICE_QUALITY = "service_quality"
    REVENUE_ANALYSIS = "revenue_analysis"
    CHURN_ANALYSIS = "churn_analysis"
    USAGE_ANALYSIS = "usage_analysis"
    CUSTOM = "custom"


class ReportFrequency(str, Enum):
    """Report generation frequency."""
    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ON_DEMAND = "on_demand"


class SegmentOperator(str, Enum):
    """Segment rule operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    REGEX = "regex"


class TimeGranularity(str, Enum):
    """Time granularity for analytics."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
