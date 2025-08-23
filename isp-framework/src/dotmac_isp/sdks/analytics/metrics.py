"""
Metrics SDK for analytics KPI management and tracking.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from ..core.exceptions import AnalyticsError
from ..models.enums import AggregationMethod, AlertSeverity, MetricType, TimeGranularity
from ..services.metrics import MetricService

logger = logging.getLogger(__name__)


class MetricsSDK:
    """SDK for analytics metrics operations."""

    def __init__(self, tenant_id: str, db: Session):
        self.tenant_id = tenant_id
        self.db = db
        self.service = MetricService(db)

    async def create_metric(
        self,
        name: str,
        display_name: str,
        metric_type: MetricType,
        description: Optional[str] = None,
        unit: Optional[str] = None,
        calculation_config: Optional[Dict[str, Any]] = None,
        dimensions: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new metric definition.

        Args:
            name: Unique metric name
            display_name: Human-readable metric name
            metric_type: Type of metric (counter, gauge, histogram)
            description: Metric description
            unit: Unit of measurement
            calculation_config: Calculation configuration
            dimensions: List of dimension names
            tags: Metric tags for categorization

        Returns:
            Dict with metric creation result
        """
        try:
            metric = await self.service.create_metric(
                tenant_id=self.tenant_id,
                name=name,
                display_name=display_name,
                metric_type=metric_type,
                description=description,
                unit=unit,
                calculation_config=calculation_config,
                dimensions=dimensions,
                tags=tags,
            )

            return {
                "metric_id": str(metric.id),
                "name": metric.name,
                "display_name": metric.display_name,
                "metric_type": metric.metric_type,
                "created_at": metric.created_at,
            }

        except Exception as e:
            logger.error(f"Failed to create metric: {e}")
            raise AnalyticsError(f"Metric creation failed: {str(e)}")

    async def record_value(
        self,
        metric_id: str,
        value: Union[int, float],
        timestamp: Optional[datetime] = None,
        dimensions: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record a metric value.

        Args:
            metric_id: Metric identifier
            value: Metric value to record
            timestamp: Value timestamp (defaults to now)
            dimensions: Dimension values
            context: Additional context

        Returns:
            Dict with value recording result
        """
        try:
            metric_value = await self.service.record_metric_value(
                tenant_id=self.tenant_id,
                metric_id=metric_id,
                value=value,
                timestamp=timestamp,
                dimensions=dimensions,
                context=context,
            )

            return {
                "value_id": str(metric_value.id),
                "metric_id": metric_id,
                "value": metric_value.value,
                "timestamp": metric_value.timestamp,
                "recorded_at": metric_value.created_at,
            }

        except Exception as e:
            logger.error(f"Failed to record metric value: {e}")
            raise AnalyticsError(f"Metric value recording failed: {str(e)}")

    async def get_metric(self, metric_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metric by ID.

        Args:
            metric_id: Metric identifier

        Returns:
            Dict with metric details or None if not found
        """
        try:
            metric = await self.service.get_metric(self.tenant_id, metric_id)
            if not metric:
                return None

            return {
                "id": str(metric.id),
                "name": metric.name,
                "display_name": metric.display_name,
                "metric_type": metric.metric_type,
                "description": metric.description,
                "unit": metric.unit,
                "calculation_config": metric.calculation_config,
                "dimensions": metric.dimensions,
                "tags": metric.tags,
                "created_at": metric.created_at,
                "updated_at": metric.updated_at,
            }

        except Exception as e:
            logger.error(f"Failed to get metric: {e}")
            raise AnalyticsError(f"Metric retrieval failed: {str(e)}")

    async def get_metrics(
        self,
        metric_type: Optional[MetricType] = None,
        tags: Optional[Dict[str, str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get metrics with filtering.

        Args:
            metric_type: Filter by metric type
            tags: Filter by tags
            limit: Maximum number of results
            offset: Result offset for pagination

        Returns:
            List of metric dictionaries
        """
        try:
            metrics = await self.service.get_metrics(
                tenant_id=self.tenant_id,
                metric_type=metric_type,
                tags=tags,
                limit=limit,
                offset=offset,
            )

            return [
                {
                    "id": str(metric.id),
                    "name": metric.name,
                    "display_name": metric.display_name,
                    "metric_type": metric.metric_type,
                    "description": metric.description,
                    "unit": metric.unit,
                    "dimensions": metric.dimensions,
                    "tags": metric.tags,
                    "created_at": metric.created_at,
                }
                for metric in metrics
            ]

        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            raise AnalyticsError(f"Metrics retrieval failed: {str(e)}")

    async def get_values(
        self,
        metric_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        dimensions: Optional[Dict[str, str]] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get metric values with filtering.

        Args:
            metric_id: Metric identifier
            start_time: Filter by start time
            end_time: Filter by end time
            dimensions: Filter by dimensions
            limit: Maximum number of results
            offset: Result offset for pagination

        Returns:
            List of metric value dictionaries
        """
        try:
            values = await self.service.get_metric_values(
                tenant_id=self.tenant_id,
                metric_id=metric_id,
                start_time=start_time,
                end_time=end_time,
                dimensions=dimensions,
                limit=limit,
                offset=offset,
            )

            return [
                {
                    "id": str(value.id),
                    "value": value.value,
                    "timestamp": value.timestamp,
                    "dimensions": value.dimensions,
                    "context": value.context,
                }
                for value in values
            ]

        except Exception as e:
            logger.error(f"Failed to get metric values: {e}")
            raise AnalyticsError(f"Metric values retrieval failed: {str(e)}")

    async def aggregate(
        self,
        metric_id: str,
        aggregation_method: AggregationMethod,
        granularity: TimeGranularity,
        start_time: datetime,
        end_time: datetime,
        dimensions: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate metric values by time and dimensions.

        Args:
            metric_id: Metric identifier
            aggregation_method: Aggregation method (sum, avg, min, max, count)
            granularity: Time granularity
            start_time: Aggregation start time
            end_time: Aggregation end time
            dimensions: Dimensions to group by

        Returns:
            List of aggregated metric data
        """
        try:
            aggregates = await self.service.aggregate_metric(
                tenant_id=self.tenant_id,
                metric_id=metric_id,
                aggregation_method=aggregation_method,
                granularity=granularity,
                start_time=start_time,
                end_time=end_time,
                dimensions=dimensions,
            )

            return [
                {
                    "time_bucket": aggregate.time_bucket,
                    "value": aggregate.value,
                    "sample_count": aggregate.sample_count,
                    "dimensions": aggregate.dimensions,
                }
                for aggregate in aggregates
            ]

        except Exception as e:
            logger.error(f"Failed to aggregate metric: {e}")
            raise AnalyticsError(f"Metric aggregation failed: {str(e)}")

    async def calculate_trend(
        self,
        metric_id: str,
        current_period_start: datetime,
        current_period_end: datetime,
        comparison_period_start: datetime,
        comparison_period_end: datetime,
    ) -> Dict[str, Any]:
        """
        Calculate metric trend between two periods.

        Args:
            metric_id: Metric identifier
            current_period_start: Current period start time
            current_period_end: Current period end time
            comparison_period_start: Comparison period start time
            comparison_period_end: Comparison period end time

        Returns:
            Dict with trend analysis results
        """
        try:
            trend_data = await self.service.calculate_metric_trend(
                tenant_id=self.tenant_id,
                metric_id=metric_id,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
                comparison_period_start=comparison_period_start,
                comparison_period_end=comparison_period_end,
            )

            return trend_data

        except Exception as e:
            logger.error(f"Failed to calculate metric trend: {e}")
            raise AnalyticsError(f"Metric trend calculation failed: {str(e)}")

    async def create_alert(
        self,
        metric_id: str,
        name: str,
        condition_config: Dict[str, Any],
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        notification_channels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a metric alert.

        Args:
            metric_id: Metric identifier
            name: Alert name
            condition_config: Alert condition configuration
            severity: Alert severity level
            notification_channels: List of notification channels

        Returns:
            Dict with alert creation result
        """
        try:
            alert = await self.service.create_metric_alert(
                tenant_id=self.tenant_id,
                metric_id=metric_id,
                name=name,
                condition_config=condition_config,
                severity=severity,
                notification_channels=notification_channels,
            )

            return {
                "alert_id": str(alert.id),
                "metric_id": metric_id,
                "name": alert.name,
                "severity": alert.severity,
                "created_at": alert.created_at,
            }

        except Exception as e:
            logger.error(f"Failed to create metric alert: {e}")
            raise AnalyticsError(f"Metric alert creation failed: {str(e)}")

    async def create_annotation(
        self,
        metric_id: str,
        timestamp: datetime,
        title: str,
        description: Optional[str] = None,
        annotation_type: str = "event",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a metric annotation.

        Args:
            metric_id: Metric identifier
            timestamp: Annotation timestamp
            title: Annotation title
            description: Annotation description
            annotation_type: Type of annotation
            metadata: Additional metadata

        Returns:
            Dict with annotation creation result
        """
        try:
            annotation = await self.service.create_metric_annotation(
                tenant_id=self.tenant_id,
                metric_id=metric_id,
                timestamp=timestamp,
                title=title,
                description=description,
                annotation_type=annotation_type,
                metadata=metadata,
            )

            return {
                "annotation_id": str(annotation.id),
                "metric_id": metric_id,
                "title": annotation.title,
                "timestamp": annotation.timestamp,
                "created_at": annotation.created_at,
            }

        except Exception as e:
            logger.error(f"Failed to create metric annotation: {e}")
            raise AnalyticsError(f"Metric annotation creation failed: {str(e)}")

    # Convenience methods for common metric operations
    async def increment(
        self,
        metric_name: str,
        value: Union[int, float] = 1,
        dimensions: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Increment a counter metric."""
        return await self.record_value(
            metric_id=metric_name, value=value, dimensions=dimensions
        )

    async def set_gauge(
        self,
        metric_name: str,
        value: Union[int, float],
        dimensions: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Set a gauge metric value."""
        return await self.record_value(
            metric_id=metric_name, value=value, dimensions=dimensions
        )

    async def record_timing(
        self,
        metric_name: str,
        duration_ms: float,
        dimensions: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Record a timing metric."""
        return await self.record_value(
            metric_id=metric_name, value=duration_ms, dimensions=dimensions
        )
