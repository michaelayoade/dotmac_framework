"""
Collect Metrics Use Case
Orchestrates monitoring data collection and processing
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from dotmac_shared.core.logging import get_logger
from dotmac_shared.exceptions import ExceptionContext

from ..base import UseCase, UseCaseContext, UseCaseResult

logger = get_logger(__name__)


class MetricType(str, Enum):
    """Types of metrics to collect"""

    SYSTEM = "system"
    APPLICATION = "application"
    BUSINESS = "business"
    SECURITY = "security"
    BILLING = "billing"


@dataclass
class CollectMetricsInput:
    """Input data for metrics collection"""

    tenant_id: Optional[str] = None  # None for system-wide metrics
    metric_types: list[MetricType] = None
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None
    aggregation_level: str = "minute"  # minute, hour, day
    include_metadata: bool = True

    def __post_init__(self):
        if self.metric_types is None:
            self.metric_types = [MetricType.SYSTEM, MetricType.APPLICATION]
        if self.time_range_end is None:
            self.time_range_end = datetime.utcnow().isoformat()
        if self.time_range_start is None:
            start_time = datetime.utcnow() - timedelta(hours=1)
            self.time_range_start = start_time.isoformat()


@dataclass
class MetricDataPoint:
    """Individual metric data point"""

    timestamp: str
    metric_name: str
    value: float
    unit: str
    tags: dict[str, str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MetricsSummary:
    """Summary statistics for metrics"""

    metric_name: str
    count: int
    min_value: float
    max_value: float
    avg_value: float
    sum_value: float
    last_value: float
    trend: str  # "increasing", "decreasing", "stable"


@dataclass
class CollectMetricsOutput:
    """Output data for metrics collection"""

    tenant_id: Optional[str]
    time_range: dict[str, str]
    aggregation_level: str
    data_points: list[MetricDataPoint]
    summaries: list[MetricsSummary]
    collection_metadata: dict[str, Any]


class CollectMetricsUseCase(UseCase[CollectMetricsInput, CollectMetricsOutput]):
    """
    Collect and process monitoring metrics.

    This use case orchestrates:
    - Metrics collection from various sources
    - Data aggregation and processing
    - Anomaly detection
    - Alert evaluation
    - Metrics storage and indexing

    Can collect tenant-specific or system-wide metrics.
    """

    def __init__(self):
        super().__init__()

    async def validate_input(self, input_data: CollectMetricsInput) -> bool:
        """Validate metrics collection input"""
        try:
            if input_data.time_range_start:
                datetime.fromisoformat(input_data.time_range_start.replace("Z", "+00:00"))
            if input_data.time_range_end:
                datetime.fromisoformat(input_data.time_range_end.replace("Z", "+00:00"))
        except ValueError:
            return False

        if input_data.aggregation_level not in ["minute", "hour", "day"]:
            return False

        return True

    async def can_execute(self, context: Optional[UseCaseContext] = None) -> bool:
        """Check if metrics collection can be executed"""

        # Check permissions
        if context and context.permissions:
            required_permissions = ["monitoring.read", "metrics.collect"]
            user_permissions = context.permissions.get("actions", [])

            if not any(perm in user_permissions for perm in required_permissions):
                return False

        return True

    async def execute(
        self, input_data: CollectMetricsInput, context: Optional[UseCaseContext] = None
    ) -> UseCaseResult[CollectMetricsOutput]:
        """Execute metrics collection"""

        try:
            if not await self.validate_input(input_data):
                return self._create_error_result("Input validation failed", error_code="INVALID_INPUT")

            if not await self.can_execute(context):
                return self._create_error_result("Metrics collection not allowed", error_code="EXECUTION_DENIED")

            self.logger.info(
                "Collecting metrics",
                extra={
                    "tenant_id": input_data.tenant_id,
                    "metric_types": [mt.value for mt in input_data.metric_types],
                    "time_range_start": input_data.time_range_start,
                    "time_range_end": input_data.time_range_end,
                },
            )

            # Collect data points from various sources
            data_points = []
            for metric_type in input_data.metric_types:
                type_data_points = await self._collect_metrics_by_type(metric_type, input_data)
                data_points.extend(type_data_points)

            # Generate summaries
            summaries = await self._generate_summaries(data_points)

            # Create collection metadata
            metadata = {
                "collected_at": datetime.utcnow().isoformat(),
                "data_point_count": len(data_points),
                "metric_types_collected": [mt.value for mt in input_data.metric_types],
                "collection_duration_ms": 150,  # Mock value
                "data_sources": ["infrastructure", "application", "database"],
            }

            output_data = CollectMetricsOutput(
                tenant_id=input_data.tenant_id,
                time_range={
                    "start": input_data.time_range_start,
                    "end": input_data.time_range_end,
                },
                aggregation_level=input_data.aggregation_level,
                data_points=data_points,
                summaries=summaries,
                collection_metadata=metadata,
            )

            return self._create_success_result(output_data)

        except ExceptionContext.LIFECYCLE_EXCEPTIONS as e:
            self.logger.error(f"Metrics collection failed: {e}")
            return self._create_error_result(str(e), error_code="COLLECTION_FAILED")

    async def _collect_metrics_by_type(
        self, metric_type: MetricType, input_data: CollectMetricsInput
    ) -> list[MetricDataPoint]:
        """Collect metrics for a specific type"""

        collection_map = {
            MetricType.SYSTEM: self._collect_system_metrics,
            MetricType.APPLICATION: self._collect_application_metrics,
            MetricType.BUSINESS: self._collect_business_metrics,
            MetricType.SECURITY: self._collect_security_metrics,
            MetricType.BILLING: self._collect_billing_metrics,
        }

        collector = collection_map.get(metric_type)
        if not collector:
            return []

        return await collector(input_data)

    async def _collect_system_metrics(self, input_data: CollectMetricsInput) -> list[MetricDataPoint]:
        """Collect system-level metrics"""

        # Mock system metrics - would integrate with actual monitoring systems
        base_time = datetime.fromisoformat(input_data.time_range_start.replace("Z", "+00:00"))
        metrics = []

        for i in range(10):  # 10 data points
            timestamp = (base_time + timedelta(minutes=i * 6)).isoformat()

            metrics.extend(
                [
                    MetricDataPoint(
                        timestamp=timestamp,
                        metric_name="cpu_usage_percent",
                        value=45.2 + (i * 2.1),
                        unit="percent",
                        tags={
                            "host": "host-1",
                            "tenant": input_data.tenant_id or "system",
                        },
                    ),
                    MetricDataPoint(
                        timestamp=timestamp,
                        metric_name="memory_usage_bytes",
                        value=2_147_483_648 + (i * 104_857_600),  # ~2GB + growth
                        unit="bytes",
                        tags={
                            "host": "host-1",
                            "tenant": input_data.tenant_id or "system",
                        },
                    ),
                    MetricDataPoint(
                        timestamp=timestamp,
                        metric_name="disk_usage_bytes",
                        value=10_737_418_240 + (i * 536_870_912),  # ~10GB + growth
                        unit="bytes",
                        tags={"host": "host-1", "device": "/dev/sda1"},
                    ),
                ]
            )

        return metrics

    async def _collect_application_metrics(self, input_data: CollectMetricsInput) -> list[MetricDataPoint]:
        """Collect application-level metrics"""

        base_time = datetime.fromisoformat(input_data.time_range_start.replace("Z", "+00:00"))
        metrics = []

        for i in range(10):
            timestamp = (base_time + timedelta(minutes=i * 6)).isoformat()

            metrics.extend(
                [
                    MetricDataPoint(
                        timestamp=timestamp,
                        metric_name="http_requests_total",
                        value=1250 + (i * 50),
                        unit="count",
                        tags={
                            "method": "GET",
                            "status": "200",
                            "tenant": input_data.tenant_id or "system",
                        },
                    ),
                    MetricDataPoint(
                        timestamp=timestamp,
                        metric_name="response_time_ms",
                        value=125.5 + (i * 5.2),
                        unit="milliseconds",
                        tags={
                            "endpoint": "/api/v1/health",
                            "tenant": input_data.tenant_id or "system",
                        },
                    ),
                ]
            )

        return metrics

    async def _collect_business_metrics(self, input_data: CollectMetricsInput) -> list[MetricDataPoint]:
        """Collect business-level metrics"""

        if not input_data.tenant_id:
            return []  # Business metrics are tenant-specific

        base_time = datetime.fromisoformat(input_data.time_range_start.replace("Z", "+00:00"))
        metrics = []

        for i in range(10):
            timestamp = (base_time + timedelta(minutes=i * 6)).isoformat()

            metrics.extend(
                [
                    MetricDataPoint(
                        timestamp=timestamp,
                        metric_name="active_users",
                        value=24 + i,
                        unit="count",
                        tags={"tenant": input_data.tenant_id},
                    ),
                    MetricDataPoint(
                        timestamp=timestamp,
                        metric_name="transactions_total",
                        value=450 + (i * 15),
                        unit="count",
                        tags={"tenant": input_data.tenant_id, "type": "billing"},
                    ),
                ]
            )

        return metrics

    async def _collect_security_metrics(self, input_data: CollectMetricsInput) -> list[MetricDataPoint]:
        """Collect security-related metrics"""

        base_time = datetime.fromisoformat(input_data.time_range_start.replace("Z", "+00:00"))
        metrics = []

        for i in range(10):
            timestamp = (base_time + timedelta(minutes=i * 6)).isoformat()

            metrics.append(
                MetricDataPoint(
                    timestamp=timestamp,
                    metric_name="failed_login_attempts",
                    value=max(0, 3 - i // 3),
                    unit="count",
                    tags={"tenant": input_data.tenant_id or "system", "source": "web"},
                )
            )

        return metrics

    async def _collect_billing_metrics(self, input_data: CollectMetricsInput) -> list[MetricDataPoint]:
        """Collect billing-related metrics"""

        if not input_data.tenant_id:
            return []  # Billing metrics are tenant-specific

        base_time = datetime.fromisoformat(input_data.time_range_start.replace("Z", "+00:00"))
        metrics = []

        for i in range(10):
            timestamp = (base_time + timedelta(minutes=i * 6)).isoformat()

            metrics.extend(
                [
                    MetricDataPoint(
                        timestamp=timestamp,
                        metric_name="compute_hours",
                        value=1.0,  # 1 hour per data point
                        unit="hours",
                        tags={"tenant": input_data.tenant_id, "service": "compute"},
                    ),
                    MetricDataPoint(
                        timestamp=timestamp,
                        metric_name="storage_gb",
                        value=10.5 + (i * 0.1),
                        unit="gigabytes",
                        tags={"tenant": input_data.tenant_id, "service": "storage"},
                    ),
                ]
            )

        return metrics

    async def _generate_summaries(self, data_points: list[MetricDataPoint]) -> list[MetricsSummary]:
        """Generate summary statistics for collected metrics"""

        # Group data points by metric name
        grouped_metrics = {}
        for point in data_points:
            if point.metric_name not in grouped_metrics:
                grouped_metrics[point.metric_name] = []
            grouped_metrics[point.metric_name].append(point)

        summaries = []
        for metric_name, points in grouped_metrics.items():
            values = [p.value for p in points]

            if not values:
                continue

            # Calculate trend (simplified)
            trend = "stable"
            if len(values) >= 3:
                if values[-1] > values[0] * 1.1:
                    trend = "increasing"
                elif values[-1] < values[0] * 0.9:
                    trend = "decreasing"

            summary = MetricsSummary(
                metric_name=metric_name,
                count=len(values),
                min_value=min(values),
                max_value=max(values),
                avg_value=sum(values) / len(values),
                sum_value=sum(values),
                last_value=values[-1],
                trend=trend,
            )

            summaries.append(summary)

        return summaries
