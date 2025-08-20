"""
Events observability with golden metrics and SLO targets.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = structlog.get_logger(__name__)


class SLOStatus(str, Enum):
    """SLO status indicators."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class SLOTarget:
    """SLO target definition."""

    name: str
    description: str
    target_percentage: float  # e.g., 99.9 for 99.9%
    time_window_minutes: int  # e.g., 5 for 5-minute window
    threshold_value: Optional[float] = None  # For latency/error rate thresholds
    comparison: str = "less_than"  # less_than, greater_than, equals

    def evaluate(self, current_value: float, success_rate: float) -> SLOStatus:
        """Evaluate current performance against SLO target."""

        if success_rate < self.target_percentage:
            if success_rate < self.target_percentage - 5:  # 5% buffer
                return SLOStatus.CRITICAL
            else:
                return SLOStatus.WARNING

        if self.threshold_value is not None:
            if self.comparison == "less_than" and current_value > self.threshold_value or self.comparison == "greater_than" and current_value < self.threshold_value:
                return SLOStatus.WARNING

        return SLOStatus.HEALTHY


@dataclass
class MetricSnapshot:
    """Point-in-time metric snapshot."""

    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class EventsMetricsCollector:
    """Collector for events golden metrics."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()

        # Golden Metrics - Events
        self.events_published_total = Counter(
            "events_published_total",
            "Total number of events published",
            ["tenant_id", "event_type", "topic", "status"],
            registry=self.registry
        )

        self.events_consumed_total = Counter(
            "events_consumed_total",
            "Total number of events consumed",
            ["tenant_id", "consumer_group", "topic", "status"],
            registry=self.registry
        )

        self.event_publish_duration_seconds = Histogram(
            "event_publish_duration_seconds",
            "Time taken to publish events",
            ["tenant_id", "event_type", "topic"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )

        self.event_processing_duration_seconds = Histogram(
            "event_processing_duration_seconds",
            "Time taken to process events",
            ["tenant_id", "consumer_group", "event_type"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
            registry=self.registry
        )

        self.consumer_lag_messages = Gauge(
            "consumer_lag_messages",
            "Number of messages behind in consumer lag",
            ["tenant_id", "consumer_group", "topic", "partition"],
            registry=self.registry
        )

        self.topic_partition_count = Gauge(
            "topic_partition_count",
            "Number of partitions per topic",
            ["tenant_id", "topic"],
            registry=self.registry
        )

        self.topic_message_count = Gauge(
            "topic_message_count",
            "Total messages in topic",
            ["tenant_id", "topic"],
            registry=self.registry
        )

        # Error Metrics
        self.event_publish_errors_total = Counter(
            "event_publish_errors_total",
            "Total number of event publish errors",
            ["tenant_id", "event_type", "topic", "error_type"],
            registry=self.registry
        )

        self.event_processing_errors_total = Counter(
            "event_processing_errors_total",
            "Total number of event processing errors",
            ["tenant_id", "consumer_group", "event_type", "error_type"],
            registry=self.registry
        )

        # Outbox Metrics
        self.outbox_entries_total = Counter(
            "outbox_entries_total",
            "Total number of outbox entries",
            ["tenant_id", "status"],
            registry=self.registry
        )

        self.outbox_processing_duration_seconds = Histogram(
            "outbox_processing_duration_seconds",
            "Time from outbox creation to publish",
            ["tenant_id"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 300.0],
            registry=self.registry
        )

        # Circuit Breaker Metrics
        self.circuit_breaker_state = Gauge(
            "circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half_open)",
            ["tenant_id", "circuit_name"],
            registry=self.registry
        )

        self.circuit_breaker_failures_total = Counter(
            "circuit_breaker_failures_total",
            "Total circuit breaker failures",
            ["tenant_id", "circuit_name"],
            registry=self.registry
        )

        # Deduplication Metrics
        self.deduplication_hits_total = Counter(
            "deduplication_hits_total",
            "Total deduplication hits (duplicates found)",
            ["tenant_id", "consumer_group"],
            registry=self.registry
        )

        self.deduplication_store_size = Gauge(
            "deduplication_store_size",
            "Number of entries in deduplication store",
            ["tenant_id"],
            registry=self.registry
        )

        # Partition Ordering Metrics
        self.partition_queue_size = Gauge(
            "partition_queue_size",
            "Number of events queued per partition",
            ["tenant_id", "topic", "partition"],
            registry=self.registry
        )

        self.partition_processing_lag_seconds = Gauge(
            "partition_processing_lag_seconds",
            "Processing lag per partition in seconds",
            ["tenant_id", "topic", "partition"],
            registry=self.registry
        )

    def record_event_published(
        self,
        tenant_id: str,
        event_type: str,
        topic: str,
        status: str = "success",
        duration_seconds: Optional[float] = None
    ):
        """Record event publication."""
        self.events_published_total.labels(
            tenant_id=tenant_id,
            event_type=event_type,
            topic=topic,
            status=status
        ).inc()

        if duration_seconds is not None:
            self.event_publish_duration_seconds.labels(
                tenant_id=tenant_id,
                event_type=event_type,
                topic=topic
            ).observe(duration_seconds)

    def record_event_consumed(
        self,
        tenant_id: str,
        consumer_group: str,
        topic: str,
        event_type: str,
        status: str = "success",
        processing_duration_seconds: Optional[float] = None
    ):
        """Record event consumption."""
        self.events_consumed_total.labels(
            tenant_id=tenant_id,
            consumer_group=consumer_group,
            topic=topic,
            status=status
        ).inc()

        if processing_duration_seconds is not None:
            self.event_processing_duration_seconds.labels(
                tenant_id=tenant_id,
                consumer_group=consumer_group,
                event_type=event_type
            ).observe(processing_duration_seconds)

    def record_publish_error(
        self,
        tenant_id: str,
        event_type: str,
        topic: str,
        error_type: str
    ):
        """Record publish error."""
        self.event_publish_errors_total.labels(
            tenant_id=tenant_id,
            event_type=event_type,
            topic=topic,
            error_type=error_type
        ).inc()

    def record_processing_error(
        self,
        tenant_id: str,
        consumer_group: str,
        event_type: str,
        error_type: str
    ):
        """Record processing error."""
        self.event_processing_errors_total.labels(
            tenant_id=tenant_id,
            consumer_group=consumer_group,
            event_type=event_type,
            error_type=error_type
        ).inc()

    def update_consumer_lag(
        self,
        tenant_id: str,
        consumer_group: str,
        topic: str,
        partition: str,
        lag_messages: int
    ):
        """Update consumer lag."""
        self.consumer_lag_messages.labels(
            tenant_id=tenant_id,
            consumer_group=consumer_group,
            topic=topic,
            partition=partition
        ).set(lag_messages)

    def update_topic_stats(
        self,
        tenant_id: str,
        topic: str,
        partition_count: int,
        message_count: int
    ):
        """Update topic statistics."""
        self.topic_partition_count.labels(
            tenant_id=tenant_id,
            topic=topic
        ).set(partition_count)

        self.topic_message_count.labels(
            tenant_id=tenant_id,
            topic=topic
        ).set(message_count)

    def record_outbox_entry(
        self,
        tenant_id: str,
        status: str,
        processing_duration_seconds: Optional[float] = None
    ):
        """Record outbox entry."""
        self.outbox_entries_total.labels(
            tenant_id=tenant_id,
            status=status
        ).inc()

        if processing_duration_seconds is not None:
            self.outbox_processing_duration_seconds.labels(
                tenant_id=tenant_id
            ).observe(processing_duration_seconds)

    def update_circuit_breaker_state(
        self,
        tenant_id: str,
        circuit_name: str,
        state: int
    ):
        """Update circuit breaker state."""
        self.circuit_breaker_state.labels(
            tenant_id=tenant_id,
            circuit_name=circuit_name
        ).set(state)

    def record_circuit_breaker_failure(
        self,
        tenant_id: str,
        circuit_name: str
    ):
        """Record circuit breaker failure."""
        self.circuit_breaker_failures_total.labels(
            tenant_id=tenant_id,
            circuit_name=circuit_name
        ).inc()

    def record_deduplication_hit(
        self,
        tenant_id: str,
        consumer_group: str
    ):
        """Record deduplication hit."""
        self.deduplication_hits_total.labels(
            tenant_id=tenant_id,
            consumer_group=consumer_group
        ).inc()

    def update_deduplication_store_size(
        self,
        tenant_id: str,
        size: int
    ):
        """Update deduplication store size."""
        self.deduplication_store_size.labels(
            tenant_id=tenant_id
        ).set(size)

    def update_partition_queue_size(
        self,
        tenant_id: str,
        topic: str,
        partition: str,
        size: int
    ):
        """Update partition queue size."""
        self.partition_queue_size.labels(
            tenant_id=tenant_id,
            topic=topic,
            partition=partition
        ).set(size)

    def update_partition_processing_lag(
        self,
        tenant_id: str,
        topic: str,
        partition: str,
        lag_seconds: float
    ):
        """Update partition processing lag."""
        self.partition_processing_lag_seconds.labels(
            tenant_id=tenant_id,
            topic=topic,
            partition=partition
        ).set(lag_seconds)

    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format."""
        return generate_latest(self.registry).decode("utf-8")


class SLOMonitor:
    """Monitor SLO compliance for events."""

    def __init__(self, metrics_collector: EventsMetricsCollector):
        self.metrics_collector = metrics_collector
        self.slo_targets = self._define_slo_targets()
        self.metric_history = defaultdict(lambda: deque(maxlen=1000))

    def _define_slo_targets(self) -> List[SLOTarget]:
        """Define SLO targets for events."""
        return [
            # Availability SLOs
            SLOTarget(
                name="event_publish_success_rate",
                description="Event publish success rate",
                target_percentage=99.9,
                time_window_minutes=5
            ),
            SLOTarget(
                name="event_processing_success_rate",
                description="Event processing success rate",
                target_percentage=99.5,
                time_window_minutes=5
            ),

            # Latency SLOs
            SLOTarget(
                name="event_publish_p95_latency",
                description="95th percentile event publish latency",
                target_percentage=95.0,
                time_window_minutes=5,
                threshold_value=0.1,  # 100ms
                comparison="less_than"
            ),
            SLOTarget(
                name="event_processing_p95_latency",
                description="95th percentile event processing latency",
                target_percentage=95.0,
                time_window_minutes=5,
                threshold_value=1.0,  # 1 second
                comparison="less_than"
            ),

            # Lag SLOs
            SLOTarget(
                name="consumer_lag_p95",
                description="95th percentile consumer lag",
                target_percentage=95.0,
                time_window_minutes=5,
                threshold_value=1000,  # 1000 messages
                comparison="less_than"
            ),

            # Outbox SLOs
            SLOTarget(
                name="outbox_processing_p95_latency",
                description="95th percentile outbox processing latency",
                target_percentage=95.0,
                time_window_minutes=5,
                threshold_value=5.0,  # 5 seconds
                comparison="less_than"
            )
        ]

    def record_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Record metric value for SLO monitoring."""
        snapshot = MetricSnapshot(
            timestamp=datetime.now(timezone.utc),
            value=value,
            labels=labels or {}
        )
        self.metric_history[metric_name].append(snapshot)

    def evaluate_slos(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate all SLO targets."""
        results = {}

        for slo_target in self.slo_targets:
            try:
                status = self._evaluate_slo_target(slo_target, tenant_id)
                results[slo_target.name] = {
                    "target": slo_target,
                    "status": status,
                    "evaluated_at": datetime.now(timezone.utc)
                }
            except Exception as e:
                logger.error(f"Failed to evaluate SLO {slo_target.name}", error=str(e))
                results[slo_target.name] = {
                    "target": slo_target,
                    "status": SLOStatus.UNKNOWN,
                    "error": str(e),
                    "evaluated_at": datetime.now(timezone.utc)
                }

        return results

    def _evaluate_slo_target(self, slo_target: SLOTarget, tenant_id: Optional[str]) -> SLOStatus:
        """Evaluate a specific SLO target."""

        # Get recent metrics within time window
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=slo_target.time_window_minutes)
        recent_metrics = [
            m for m in self.metric_history[slo_target.name]
            if m.timestamp >= cutoff_time and (not tenant_id or m.labels.get("tenant_id") == tenant_id)
        ]

        if not recent_metrics:
            return SLOStatus.UNKNOWN

        # Calculate success rate and current value based on SLO type
        if "success_rate" in slo_target.name:
            success_count = len([m for m in recent_metrics if m.value == 1.0])
            total_count = len(recent_metrics)
            success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
            current_value = success_rate

        elif "latency" in slo_target.name or "lag" in slo_target.name:
            # Calculate percentile
            values = sorted([m.value for m in recent_metrics])
            if values:
                percentile_index = int((slo_target.target_percentage / 100) * len(values))
                current_value = values[min(percentile_index, len(values) - 1)]
                success_rate = slo_target.target_percentage  # Assume target met for percentile
            else:
                current_value = float("inf")
                success_rate = 0

        else:
            # Generic metric evaluation
            current_value = sum(m.value for m in recent_metrics) / len(recent_metrics)
            success_rate = slo_target.target_percentage  # Default assumption

        return slo_target.evaluate(current_value, success_rate)

    def get_slo_dashboard_data(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get SLO data for dashboard display."""
        slo_results = self.evaluate_slos(tenant_id)

        dashboard_data = {
            "overall_health": self._calculate_overall_health(slo_results),
            "slo_summary": {
                "total": len(slo_results),
                "healthy": len([r for r in slo_results.values() if r["status"] == SLOStatus.HEALTHY]),
                "warning": len([r for r in slo_results.values() if r["status"] == SLOStatus.WARNING]),
                "critical": len([r for r in slo_results.values() if r["status"] == SLOStatus.CRITICAL]),
                "unknown": len([r for r in slo_results.values() if r["status"] == SLOStatus.UNKNOWN])
            },
            "slo_details": slo_results,
            "generated_at": datetime.now(timezone.utc)
        }

        return dashboard_data

    def _calculate_overall_health(self, slo_results: Dict[str, Any]) -> SLOStatus:
        """Calculate overall system health from SLO results."""
        statuses = [result["status"] for result in slo_results.values()]

        if SLOStatus.CRITICAL in statuses:
            return SLOStatus.CRITICAL
        elif SLOStatus.WARNING in statuses:
            return SLOStatus.WARNING
        elif SLOStatus.UNKNOWN in statuses:
            return SLOStatus.UNKNOWN
        else:
            return SLOStatus.HEALTHY


class EventsObservabilityManager:
    """Manager for events observability and monitoring."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.metrics_collector = EventsMetricsCollector(registry)
        self.slo_monitor = SLOMonitor(self.metrics_collector)
        self.alert_rules = self._define_alert_rules()

    def _define_alert_rules(self) -> List[Dict[str, Any]]:
        """Define alerting rules for events."""
        return [
            {
                "name": "HighEventPublishErrorRate",
                "description": "Event publish error rate is high",
                "query": "rate(event_publish_errors_total[5m]) / rate(events_published_total[5m]) > 0.01",
                "severity": "warning",
                "threshold": 0.01
            },
            {
                "name": "HighEventProcessingErrorRate",
                "description": "Event processing error rate is high",
                "query": "rate(event_processing_errors_total[5m]) / rate(events_consumed_total[5m]) > 0.05",
                "severity": "warning",
                "threshold": 0.05
            },
            {
                "name": "HighConsumerLag",
                "description": "Consumer lag is high",
                "query": "consumer_lag_messages > 10000",
                "severity": "critical",
                "threshold": 10000
            },
            {
                "name": "SlowEventPublishing",
                "description": "Event publishing is slow",
                "query": "histogram_quantile(0.95, event_publish_duration_seconds) > 0.5",
                "severity": "warning",
                "threshold": 0.5
            },
            {
                "name": "SlowEventProcessing",
                "description": "Event processing is slow",
                "query": "histogram_quantile(0.95, event_processing_duration_seconds) > 5.0",
                "severity": "warning",
                "threshold": 5.0
            },
            {
                "name": "CircuitBreakerOpen",
                "description": "Circuit breaker is open",
                "query": "circuit_breaker_state == 1",
                "severity": "critical",
                "threshold": 1
            },
            {
                "name": "HighOutboxProcessingTime",
                "description": "Outbox processing time is high",
                "query": "histogram_quantile(0.95, outbox_processing_duration_seconds) > 30",
                "severity": "warning",
                "threshold": 30
            }
        ]

    def get_health_check(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive health check."""
        slo_data = self.slo_monitor.get_slo_dashboard_data(tenant_id)

        return {
            "status": slo_data["overall_health"].value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "slo_summary": slo_data["slo_summary"],
            "tenant_id": tenant_id
        }

    def get_metrics_summary(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics summary for tenant."""
        # This would query the actual metrics from the collector
        # For now, return a placeholder structure
        return {
            "tenant_id": tenant_id,
            "events_published_total": 0,
            "events_consumed_total": 0,
            "publish_error_rate": 0.0,
            "processing_error_rate": 0.0,
            "avg_publish_latency_ms": 0.0,
            "avg_processing_latency_ms": 0.0,
            "max_consumer_lag": 0,
            "circuit_breakers_open": 0,
            "outbox_pending_count": 0,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    def export_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        return self.metrics_collector.get_metrics_text()


# Factory functions
def create_events_observability(registry: Optional[CollectorRegistry] = None) -> EventsObservabilityManager:
    """Create events observability manager."""
    return EventsObservabilityManager(registry)


def create_metrics_middleware(observability_manager: EventsObservabilityManager):
    """Create middleware for automatic metrics collection."""

    async def middleware(envelope, handler, next_middleware):
        """Metrics collection middleware."""
        start_time = time.time()

        try:
            # Process event
            result = await next_middleware(envelope, handler)

            # Record success metrics
            duration = time.time() - start_time
            observability_manager.metrics_collector.record_event_consumed(
                tenant_id=envelope.tenant_id,
                consumer_group=getattr(handler, "consumer_group", "unknown"),
                topic=envelope.get_topic_name(),
                event_type=envelope.type,
                status="success",
                processing_duration_seconds=duration
            )

            # Record SLO metric
            observability_manager.slo_monitor.record_metric(
                "event_processing_success_rate",
                1.0,
                {"tenant_id": envelope.tenant_id}
            )

            return result

        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            observability_manager.metrics_collector.record_processing_error(
                tenant_id=envelope.tenant_id,
                consumer_group=getattr(handler, "consumer_group", "unknown"),
                event_type=envelope.type,
                error_type=type(e).__name__
            )

            # Record SLO metric
            observability_manager.slo_monitor.record_metric(
                "event_processing_success_rate",
                0.0,
                {"tenant_id": envelope.tenant_id}
            )

            raise

    return middleware
