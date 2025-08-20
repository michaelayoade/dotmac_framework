"""
Metrics service for analytics data aggregation and KPI management.
"""

import logging
from datetime import datetime, timedelta
from dotmac_analytics.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..core.exceptions import AnalyticsError, NotFoundError
from ..models.enums import AggregationMethod, AlertSeverity, MetricType, TimeGranularity
from ..models.metrics import (
    Metric,
    MetricAggregate,
    MetricAlert,
    MetricAnnotation,
    MetricValue,
)

logger = logging.getLogger(__name__)


class MetricService:
    """Service for managing analytics metrics and KPIs."""

    def __init__(self, db: Session):
        self.db = db

    async def create_metric(  # noqa: PLR0913
        self,
        tenant_id: str,
        name: str,
        display_name: str,
        metric_type: MetricType,
        description: Optional[str] = None,
        unit: Optional[str] = None,
        calculation_config: Optional[Dict[str, Any]] = None,
        dimensions: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Metric:
        """Create a new metric definition."""
        try:
            metric = Metric(
                tenant_id=tenant_id,
                name=name,
                display_name=display_name,
                description=description,
                metric_type=metric_type.value,
                unit=unit,
                calculation_config=calculation_config or {},
                dimensions=dimensions or [],
                tags=tags or {}
            )

            self.db.add(metric)
            self.db.commit()
            self.db.refresh(metric)

            logger.info(f"Created metric: {name} for tenant {tenant_id}")
            return metric

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create metric: {e}")
            raise AnalyticsError(f"Metric creation failed: {str(e)}")

    async def record_metric_value(
        self,
        tenant_id: str,
        metric_id: str,
        value: Union[int, float],
        timestamp: Optional[datetime] = None,
        dimensions: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> MetricValue:
        """Record a metric value."""
        try:
            # Verify metric exists
            metric = await self.get_metric(tenant_id, metric_id)
            if not metric:
                raise NotFoundError(f"Metric {metric_id} not found")

            metric_value = MetricValue(
                tenant_id=tenant_id,
                metric_id=metric_id,
                value=float(value),
                timestamp=timestamp or utc_now(),
                dimensions=dimensions or {},
                context=context or {}
            )

            self.db.add(metric_value)
            self.db.commit()
            self.db.refresh(metric_value)

            # Check for alerts
            await self._check_metric_alerts(metric, metric_value)

            logger.debug(f"Recorded metric value: {value} for metric {metric_id}")
            return metric_value

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record metric value: {e}")
            raise AnalyticsError(f"Metric value recording failed: {str(e)}")

    async def get_metric(self, tenant_id: str, metric_id: str) -> Optional[Metric]:
        """Get metric by ID."""
        try:
            return self.db.query(Metric).filter(
                and_(
                    Metric.tenant_id == tenant_id,
                    Metric.id == metric_id,
                    Metric.is_active == True
                )
            ).first()
        except Exception as e:
            logger.error(f"Failed to get metric: {e}")
            raise AnalyticsError(f"Metric retrieval failed: {str(e)}")

    async def get_metrics(
        self,
        tenant_id: str,
        metric_type: Optional[MetricType] = None,
        tags: Optional[Dict[str, str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Metric]:
        """Get metrics with filtering."""
        try:
            query = self.db.query(Metric).filter(
                and_(
                    Metric.tenant_id == tenant_id,
                    Metric.is_active == True
                )
            )

            if metric_type:
                query = query.filter(Metric.metric_type == metric_type.value)

            if tags:
                for key, value in tags.items():
                    query = query.filter(Metric.tags[key].astext == value)

            return query.offset(offset).limit(limit).all()

        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            raise AnalyticsError(f"Metrics retrieval failed: {str(e)}")

    async def get_metric_values(
        self,
        tenant_id: str,
        metric_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        dimensions: Optional[Dict[str, str]] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[MetricValue]:
        """Get metric values with filtering."""
        try:
            query = self.db.query(MetricValue).filter(
                and_(
                    MetricValue.tenant_id == tenant_id,
                    MetricValue.metric_id == metric_id
                )
            )

            if start_time:
                query = query.filter(MetricValue.timestamp >= start_time)

            if end_time:
                query = query.filter(MetricValue.timestamp <= end_time)

            if dimensions:
                for key, value in dimensions.items():
                    query = query.filter(MetricValue.dimensions[key].astext == value)

            return query.order_by(MetricValue.timestamp.desc()).offset(offset).limit(limit).all()

        except Exception as e:
            logger.error(f"Failed to get metric values: {e}")
            raise AnalyticsError(f"Metric values retrieval failed: {str(e)}")

    async def aggregate_metric(
        self,
        tenant_id: str,
        metric_id: str,
        aggregation_method: AggregationMethod,
        granularity: TimeGranularity,
        start_time: datetime,
        end_time: datetime,
        dimensions: Optional[List[str]] = None
    ) -> List[MetricAggregate]:
        """Aggregate metric values by time and dimensions."""
        try:
            # Check if aggregates already exist
            existing_aggregates = self.db.query(MetricAggregate).filter(
                and_(
                    MetricAggregate.tenant_id == tenant_id,
                    MetricAggregate.metric_id == metric_id,
                    MetricAggregate.aggregation_method == aggregation_method.value,
                    MetricAggregate.granularity == granularity.value,
                    MetricAggregate.time_bucket >= start_time,
                    MetricAggregate.time_bucket <= end_time
                )
            ).all()

            if existing_aggregates:
                return existing_aggregates

            # Generate aggregates
            time_buckets = self._generate_time_buckets(start_time, end_time, granularity)
            aggregates = []

            for time_bucket in time_buckets:
                bucket_end = self._get_bucket_end(time_bucket, granularity)

                # Query metric values in this time bucket
                query = self.db.query(MetricValue).filter(
                    and_(
                        MetricValue.tenant_id == tenant_id,
                        MetricValue.metric_id == metric_id,
                        MetricValue.timestamp >= time_bucket,
                        MetricValue.timestamp < bucket_end
                    )
                )

                values = query.all()

                if values:
                    # Calculate aggregate value
                    numeric_values = [v.value for v in values]

                    if aggregation_method == AggregationMethod.SUM:
                        aggregate_value = sum(numeric_values)
                    elif aggregation_method == AggregationMethod.AVG:
                        aggregate_value = sum(numeric_values) / len(numeric_values)
                    elif aggregation_method == AggregationMethod.MIN:
                        aggregate_value = min(numeric_values)
                    elif aggregation_method == AggregationMethod.MAX:
                        aggregate_value = max(numeric_values)
                    elif aggregation_method == AggregationMethod.COUNT:
                        aggregate_value = len(numeric_values)
                    else:
                        aggregate_value = sum(numeric_values)  # Default to sum

                    aggregate = MetricAggregate(
                        tenant_id=tenant_id,
                        metric_id=metric_id,
                        time_bucket=time_bucket,
                        granularity=granularity.value,
                        aggregation_method=aggregation_method.value,
                        value=aggregate_value,
                        sample_count=len(values),
                        dimensions=self._aggregate_dimensions(values, dimensions or [])
                    )

                    self.db.add(aggregate)
                    aggregates.append(aggregate)

            self.db.commit()
            return aggregates

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to aggregate metric: {e}")
            raise AnalyticsError(f"Metric aggregation failed: {str(e)}")

    async def create_metric_alert(
        self,
        tenant_id: str,
        metric_id: str,
        name: str,
        condition_config: Dict[str, Any],
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        notification_channels: Optional[List[str]] = None
    ) -> MetricAlert:
        """Create a metric alert."""
        try:
            alert = MetricAlert(
                tenant_id=tenant_id,
                metric_id=metric_id,
                name=name,
                condition_config=condition_config,
                severity=severity.value,
                notification_channels=notification_channels or []
            )

            self.db.add(alert)
            self.db.commit()
            self.db.refresh(alert)

            logger.info(f"Created metric alert: {name} for metric {metric_id}")
            return alert

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create metric alert: {e}")
            raise AnalyticsError(f"Metric alert creation failed: {str(e)}")

    async def create_metric_annotation(
        self,
        tenant_id: str,
        metric_id: str,
        timestamp: datetime,
        title: str,
        description: Optional[str] = None,
        annotation_type: str = "event",
        metadata: Optional[Dict[str, Any]] = None
    ) -> MetricAnnotation:
        """Create a metric annotation."""
        try:
            annotation = MetricAnnotation(
                tenant_id=tenant_id,
                metric_id=metric_id,
                timestamp=timestamp,
                title=title,
                description=description,
                annotation_type=annotation_type,
                metadata=metadata or {}
            )

            self.db.add(annotation)
            self.db.commit()
            self.db.refresh(annotation)

            logger.info(f"Created metric annotation: {title} for metric {metric_id}")
            return annotation

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create metric annotation: {e}")
            raise AnalyticsError(f"Metric annotation creation failed: {str(e)}")

    async def calculate_metric_trend(
        self,
        tenant_id: str,
        metric_id: str,
        current_period_start: datetime,
        current_period_end: datetime,
        comparison_period_start: datetime,
        comparison_period_end: datetime
    ) -> Dict[str, Any]:
        """Calculate metric trend between two periods."""
        try:
            # Get current period values
            current_values = await self.get_metric_values(
                tenant_id, metric_id, current_period_start, current_period_end
            )

            # Get comparison period values
            comparison_values = await self.get_metric_values(
                tenant_id, metric_id, comparison_period_start, comparison_period_end
            )

            # Calculate statistics
            current_avg = sum(v.value for v in current_values) / len(current_values) if current_values else 0
            comparison_avg = sum(v.value for v in comparison_values) / len(comparison_values) if comparison_values else 0

            # Calculate trend
            if comparison_avg > 0:
                change_percent = ((current_avg - comparison_avg) / comparison_avg) * 100
            else:
                change_percent = 0 if current_avg == 0 else 100

            return {
                "current_period": {
                    "start": current_period_start,
                    "end": current_period_end,
                    "average": current_avg,
                    "count": len(current_values),
                    "total": sum(v.value for v in current_values)
                },
                "comparison_period": {
                    "start": comparison_period_start,
                    "end": comparison_period_end,
                    "average": comparison_avg,
                    "count": len(comparison_values),
                    "total": sum(v.value for v in comparison_values)
                },
                "trend": {
                    "change_percent": change_percent,
                    "direction": "up" if change_percent > 0 else "down" if change_percent < 0 else "flat",
                    "absolute_change": current_avg - comparison_avg
                }
            }

        except Exception as e:
            logger.error(f"Failed to calculate metric trend: {e}")
            raise AnalyticsError(f"Metric trend calculation failed: {str(e)}")

    async def _check_metric_alerts(self, metric: Metric, metric_value: MetricValue):
        """Check if metric value triggers any alerts."""
        try:
            alerts = self.db.query(MetricAlert).filter(
                and_(
                    MetricAlert.tenant_id == metric.tenant_id,
                    MetricAlert.metric_id == metric.id,
                    MetricAlert.is_active == True
                )
            ).all()

            for alert in alerts:
                if self._evaluate_alert_condition(alert, metric_value):
                    # Trigger alert
                    alert.last_triggered = utc_now()
                    alert.trigger_count += 1
                    self.db.commit()

                    # Send notifications (would integrate with notification service)
                    logger.warning(f"Metric alert triggered: {alert.name}")

        except Exception as e:
            logger.error(f"Failed to check metric alerts: {e}")

    def _evaluate_alert_condition(self, alert: MetricAlert, metric_value: MetricValue) -> bool:
        """Evaluate if alert condition is met."""
        condition = alert.condition_config
        threshold = condition.get("threshold")
        operator = condition.get("operator", "gt")

        if threshold is None:
            return False

        if operator == "gt":
            return metric_value.value > threshold
        elif operator == "lt":
            return metric_value.value < threshold
        elif operator == "eq":
            return metric_value.value == threshold
        elif operator == "gte":
            return metric_value.value >= threshold
        elif operator == "lte":
            return metric_value.value <= threshold

        return False

    def _generate_time_buckets(
        self,
        start_time: datetime,
        end_time: datetime,
        granularity: TimeGranularity
    ) -> List[datetime]:
        """Generate time buckets for aggregation."""
        buckets = []
        current = start_time

        if granularity == TimeGranularity.HOUR:
            delta = timedelta(hours=1)
        elif granularity == TimeGranularity.DAY:
            delta = timedelta(days=1)
        elif granularity == TimeGranularity.WEEK:
            delta = timedelta(weeks=1)
        elif granularity == TimeGranularity.MONTH:
            delta = timedelta(days=30)  # Approximate
        else:
            delta = timedelta(minutes=1)

        while current < end_time:
            buckets.append(current)
            current += delta

        return buckets

    def _get_bucket_end(self, bucket_start: datetime, granularity: TimeGranularity) -> datetime:
        """Get the end time for a time bucket."""
        if granularity == TimeGranularity.HOUR:
            return bucket_start + timedelta(hours=1)
        elif granularity == TimeGranularity.DAY:
            return bucket_start + timedelta(days=1)
        elif granularity == TimeGranularity.WEEK:
            return bucket_start + timedelta(weeks=1)
        elif granularity == TimeGranularity.MONTH:
            return bucket_start + timedelta(days=30)
        else:
            return bucket_start + timedelta(minutes=1)

    def _aggregate_dimensions(self, values: List[MetricValue], dimensions: List[str]) -> Dict[str, Any]:
        """Aggregate dimensions from metric values."""
        if not dimensions:
            return {}

        result = {}
        for dim in dimensions:
            dim_values = [v.dimensions.get(dim) for v in values if v.dimensions.get(dim)]
            if dim_values:
                # For now, just take the most common value
                result[dim] = max(set(dim_values), key=dim_values.count)

        return result
