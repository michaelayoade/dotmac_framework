"""Core analytics SDK module."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class MetricType(str, Enum):
    """Metric type enumeration."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricData:
    """Metric data schema."""

    metric_name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    labels: Optional[dict[str, str]] = None


class AnalyticsCoreSDK:
    """Core analytics SDK for basic analytics operations."""

    def __init__(self, tenant_id: str):
        """Init   operation."""
        self.tenant_id = tenant_id

    async def record_metric(self, metric: MetricData) -> bool:
        """Record a metric."""
        # Mock implementation
        return True

    async def get_metrics(
        self, metric_name: str, start_time: datetime, end_time: datetime
    ) -> list[MetricData]:
        """Get metrics."""
        # Mock implementation
        return []
