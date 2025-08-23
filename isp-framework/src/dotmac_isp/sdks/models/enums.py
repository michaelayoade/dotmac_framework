"""Common enums for SDK models."""

from enum import Enum


class AggregationMethod(str, Enum):
    """Aggregation method enumeration."""

    SUM = "sum"
    AVERAGE = "average"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    PERCENTILE = "percentile"


class AlertSeverity(str, Enum):
    """Alert severity enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """Metric type enumeration."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class TimeGranularity(str, Enum):
    """Time granularity enumeration."""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class DataSourceType(str, Enum):
    """Data source type enumeration."""

    DATABASE = "database"
    API = "api"
    FILE = "file"
    STREAM = "stream"
    WEBHOOK = "webhook"


class ReportType(str, Enum):
    """Report type enumeration."""

    DASHBOARD = "dashboard"
    SCHEDULED = "scheduled"
    AD_HOC = "ad_hoc"
    EXPORT = "export"


class EventType(str, Enum):
    """Event type enumeration."""

    USER = "user"
    SYSTEM = "system"
    BUSINESS = "business"
    ERROR = "error"


class SegmentOperator(str, Enum):
    """Segment operator enumeration."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
