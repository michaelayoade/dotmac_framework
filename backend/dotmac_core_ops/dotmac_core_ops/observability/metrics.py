"""
Golden metrics collection for workflow operations with Prometheus integration.
"""

import asyncio
import time
from typing import Dict, List, Optional, Union
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class MetricType(str, Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricSample:
    """A single metric sample."""

    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Counter:
    """Counter metric implementation."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.values: Dict[str, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def inc(self, labels: Optional[Dict[str, str]] = None, value: float = 1.0):
        """Increment counter."""
        label_key = self._labels_to_key(labels or {})
        async with self._lock:
            self.values[label_key] += value

    async def get_samples(self) -> List[MetricSample]:
        """Get metric samples."""
        samples = []
        async with self._lock:
            for label_key, value in self.values.items():
                labels = self._key_to_labels(label_key)
                samples.append(MetricSample(
                    name=self.name,
                    value=value,
                    labels=labels
                ))
        return samples

    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to string key."""
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def _key_to_labels(self, key: str) -> Dict[str, str]:
        """Convert string key back to labels dict."""
        if not key:
            return {}
        return dict(pair.split("=", 1) for pair in key.split("|"))


class Gauge:
    """Gauge metric implementation."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.values: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge value."""
        label_key = self._labels_to_key(labels or {})
        async with self._lock:
            self.values[label_key] = value

    async def inc(self, labels: Optional[Dict[str, str]] = None, value: float = 1.0):
        """Increment gauge."""
        label_key = self._labels_to_key(labels or {})
        async with self._lock:
            self.values[label_key] = self.values.get(label_key, 0) + value

    async def dec(self, labels: Optional[Dict[str, str]] = None, value: float = 1.0):
        """Decrement gauge."""
        await self.inc(labels, -value)

    async def get_samples(self) -> List[MetricSample]:
        """Get metric samples."""
        samples = []
        async with self._lock:
            for label_key, value in self.values.items():
                labels = self._key_to_labels(label_key)
                samples.append(MetricSample(
                    name=self.name,
                    value=value,
                    labels=labels
                ))
        return samples

    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to string key."""
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def _key_to_labels(self, key: str) -> Dict[str, str]:
        """Convert string key back to labels dict."""
        if not key:
            return {}
        return dict(pair.split("=", 1) for pair in key.split("|"))


class Histogram:
    """Histogram metric implementation."""

    def __init__(self, name: str, description: str = "", buckets: Optional[List[float]] = None):
        self.name = name
        self.description = description
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.bucket_counts: Dict[str, Dict[float, int]] = defaultdict(lambda: defaultdict(int))
        self.sums: Dict[str, float] = defaultdict(float)
        self.counts: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a value."""
        label_key = self._labels_to_key(labels or {})
        async with self._lock:
            self.sums[label_key] += value
            self.counts[label_key] += 1

            # Update bucket counts
            for bucket in self.buckets:
                if value <= bucket:
                    self.bucket_counts[label_key][bucket] += 1

    async def get_samples(self) -> List[MetricSample]:
        """Get metric samples."""
        samples = []
        async with self._lock:
            for label_key in self.counts:
                labels = self._key_to_labels(label_key)

                # Add bucket samples
                for bucket in self.buckets:
                    bucket_labels = labels.copy()
                    bucket_labels["le"] = str(bucket)
                    samples.append(MetricSample(
                        name=f"{self.name}_bucket",
                        value=self.bucket_counts[label_key][bucket],
                        labels=bucket_labels
                    ))

                # Add +Inf bucket
                inf_labels = labels.copy()
                inf_labels["le"] = "+Inf"
                samples.append(MetricSample(
                    name=f"{self.name}_bucket",
                    value=self.counts[label_key],
                    labels=inf_labels
                ))

                # Add sum and count
                samples.append(MetricSample(
                    name=f"{self.name}_sum",
                    value=self.sums[label_key],
                    labels=labels
                ))
                samples.append(MetricSample(
                    name=f"{self.name}_count",
                    value=self.counts[label_key],
                    labels=labels
                ))

        return samples

    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to string key."""
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def _key_to_labels(self, key: str) -> Dict[str, str]:
        """Convert string key back to labels dict."""
        if not key:
            return {}
        return dict(pair.split("=", 1) for pair in key.split("|"))


class MetricsRegistry:
    """Registry for managing metrics."""

    def __init__(self):
        self.metrics: Dict[str, Union[Counter, Gauge, Histogram]] = {}
        self._lock = asyncio.Lock()

    async def register_counter(self, name: str, description: str = "") -> Counter:
        """Register a counter metric."""
        async with self._lock:
            if name in self.metrics:
                metric = self.metrics[name]
                if not isinstance(metric, Counter):
                    raise ValueError(f"Metric {name} already exists with different type")
                return metric

            counter = Counter(name, description)
            self.metrics[name] = counter
            return counter

    async def register_gauge(self, name: str, description: str = "") -> Gauge:
        """Register a gauge metric."""
        async with self._lock:
            if name in self.metrics:
                metric = self.metrics[name]
                if not isinstance(metric, Gauge):
                    raise ValueError(f"Metric {name} already exists with different type")
                return metric

            gauge = Gauge(name, description)
            self.metrics[name] = gauge
            return gauge

    async def register_histogram(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None
    ) -> Histogram:
        """Register a histogram metric."""
        async with self._lock:
            if name in self.metrics:
                metric = self.metrics[name]
                if not isinstance(metric, Histogram):
                    raise ValueError(f"Metric {name} already exists with different type")
                return metric

            histogram = Histogram(name, description, buckets)
            self.metrics[name] = histogram
            return histogram

    async def get_all_samples(self) -> List[MetricSample]:
        """Get all metric samples."""
        all_samples = []
        async with self._lock:
            for metric in self.metrics.values():
                samples = await metric.get_samples()
                all_samples.extend(samples)
        return all_samples

    def get_metric(self, name: str) -> Optional[Union[Counter, Gauge, Histogram]]:
        """Get metric by name."""
        return self.metrics.get(name)


class WorkflowMetrics:
    """Golden metrics for workflow operations."""

    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
        self._initialized = False
        self._metrics: Dict[str, Union[Counter, Gauge, Histogram]] = {}

    async def initialize(self):
        """Initialize all workflow metrics."""
        if self._initialized:
            return

        # Workflow run metrics
        self._metrics["workflow_runs_total"] = await self.registry.register_counter(
            "workflow_runs_total",
            "Total number of workflow runs"
        )

        self._metrics["workflow_runs_active"] = await self.registry.register_gauge(
            "workflow_runs_active",
            "Number of currently active workflow runs"
        )

        self._metrics["workflow_run_duration_seconds"] = await self.registry.register_histogram(
            "workflow_run_duration_seconds",
            "Duration of workflow runs in seconds",
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0]
        )

        # Step metrics
        self._metrics["step_executions_total"] = await self.registry.register_counter(
            "step_executions_total",
            "Total number of step executions"
        )

        self._metrics["step_retries_total"] = await self.registry.register_counter(
            "step_retries_total",
            "Total number of step retries"
        )

        self._metrics["step_duration_seconds"] = await self.registry.register_histogram(
            "step_duration_seconds",
            "Duration of step executions in seconds",
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
        )

        # Queue metrics
        self._metrics["queue_lag_seconds"] = await self.registry.register_gauge(
            "queue_lag_seconds",
            "Queue lag in seconds"
        )

        self._metrics["queue_size"] = await self.registry.register_gauge(
            "queue_size",
            "Number of jobs in queue"
        )

        self._metrics["queue_processing_duration_seconds"] = await self.registry.register_histogram(
            "queue_processing_duration_seconds",
            "Time spent processing queue jobs in seconds"
        )

        # Scheduler metrics
        self._metrics["scheduler_drift_seconds"] = await self.registry.register_histogram(
            "scheduler_drift_seconds",
            "Scheduler drift in seconds",
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
        )

        self._metrics["scheduled_jobs_total"] = await self.registry.register_counter(
            "scheduled_jobs_total",
            "Total number of scheduled jobs"
        )

        # Error metrics
        self._metrics["errors_total"] = await self.registry.register_counter(
            "errors_total",
            "Total number of errors"
        )

        # DLQ metrics
        self._metrics["dlq_messages_total"] = await self.registry.register_counter(
            "dlq_messages_total",
            "Total number of messages sent to DLQ"
        )

        self._metrics["dlq_size"] = await self.registry.register_gauge(
            "dlq_size",
            "Number of messages in DLQ"
        )

        # Rate limiting metrics
        self._metrics["rate_limit_hits_total"] = await self.registry.register_counter(
            "rate_limit_hits_total",
            "Total number of rate limit hits"
        )

        self._initialized = True
        logger.info("Workflow metrics initialized")

    async def record_workflow_started(self, tenant_id: str, workflow_id: str):
        """Record workflow start."""
        await self._ensure_initialized()

        labels = {"tenant_id": tenant_id, "workflow_id": workflow_id, "status": "started"}
        await self._metrics["workflow_runs_total"].inc(labels)
        await self._metrics["workflow_runs_active"].inc({"tenant_id": tenant_id})

    async def record_workflow_completed(
        self,
        tenant_id: str,
        workflow_id: str,
        duration_seconds: float,
        status: str = "completed"
    ):
        """Record workflow completion."""
        await self._ensure_initialized()

        labels = {"tenant_id": tenant_id, "workflow_id": workflow_id, "status": status}
        await self._metrics["workflow_runs_total"].inc(labels)
        await self._metrics["workflow_runs_active"].dec({"tenant_id": tenant_id})
        await self._metrics["workflow_run_duration_seconds"].observe(duration_seconds, labels)

    async def record_step_execution(
        self,
        tenant_id: str,
        workflow_id: str,
        step_id: str,
        duration_seconds: float,
        status: str = "completed",
        attempt: int = 1
    ):
        """Record step execution."""
        await self._ensure_initialized()

        labels = {
            "tenant_id": tenant_id,
            "workflow_id": workflow_id,
            "step_id": step_id,
            "status": status
        }

        await self._metrics["step_executions_total"].inc(labels)
        await self._metrics["step_duration_seconds"].observe(duration_seconds, labels)

        if attempt > 1:
            retry_labels = labels.copy()
            retry_labels["attempt"] = str(attempt)
            await self._metrics["step_retries_total"].inc(retry_labels)

    async def record_queue_metrics(
        self,
        tenant_id: str,
        queue_name: str,
        lag_seconds: float,
        queue_size: int,
        processing_duration: Optional[float] = None
    ):
        """Record queue metrics."""
        await self._ensure_initialized()

        labels = {"tenant_id": tenant_id, "queue_name": queue_name}

        await self._metrics["queue_lag_seconds"].set(lag_seconds, labels)
        await self._metrics["queue_size"].set(queue_size, labels)

        if processing_duration is not None:
            await self._metrics["queue_processing_duration_seconds"].observe(
                processing_duration, labels
            )

    async def record_scheduler_drift(
        self,
        tenant_id: str,
        schedule_id: str,
        drift_seconds: float
    ):
        """Record scheduler drift."""
        await self._ensure_initialized()

        labels = {"tenant_id": tenant_id, "schedule_id": schedule_id}
        await self._metrics["scheduler_drift_seconds"].observe(drift_seconds, labels)

    async def record_scheduled_job(self, tenant_id: str, schedule_id: str, status: str = "executed"):
        """Record scheduled job execution."""
        await self._ensure_initialized()

        labels = {"tenant_id": tenant_id, "schedule_id": schedule_id, "status": status}
        await self._metrics["scheduled_jobs_total"].inc(labels)

    async def record_error(
        self,
        tenant_id: str,
        error_type: str,
        component: str,
        resource_id: Optional[str] = None
    ):
        """Record error occurrence."""
        await self._ensure_initialized()

        labels = {
            "tenant_id": tenant_id,
            "error_type": error_type,
            "component": component
        }

        if resource_id:
            labels["resource_id"] = resource_id

        await self._metrics["errors_total"].inc(labels)

    async def record_dlq_message(self, tenant_id: str, queue_name: str, reason: str):
        """Record DLQ message."""
        await self._ensure_initialized()

        labels = {"tenant_id": tenant_id, "queue_name": queue_name, "reason": reason}
        await self._metrics["dlq_messages_total"].inc(labels)

    async def update_dlq_size(self, tenant_id: str, queue_name: str, size: int):
        """Update DLQ size."""
        await self._ensure_initialized()

        labels = {"tenant_id": tenant_id, "queue_name": queue_name}
        await self._metrics["dlq_size"].set(size, labels)

    async def record_rate_limit_hit(self, tenant_id: str, operation: str, limit_type: str):
        """Record rate limit hit."""
        await self._ensure_initialized()

        labels = {"tenant_id": tenant_id, "operation": operation, "limit_type": limit_type}
        await self._metrics["rate_limit_hits_total"].inc(labels)

    async def _ensure_initialized(self):
        """Ensure metrics are initialized."""
        if not self._initialized:
            await self.initialize()


class MetricsCollector:
    """Collector for gathering metrics from various components."""

    def __init__(self, workflow_metrics: WorkflowMetrics):
        self.workflow_metrics = workflow_metrics
        self.collection_interval = 30  # seconds
        self.running = False
        self._collection_task: Optional[asyncio.Task] = None

    async def start_collection(self):
        """Start metrics collection."""
        if self.running:
            return

        self.running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Metrics collection started")

    async def stop_collection(self):
        """Stop metrics collection."""
        self.running = False

        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

        logger.info("Metrics collection stopped")

    async def _collection_loop(self):
        """Main collection loop."""
        while self.running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error("Metrics collection error", error=str(e))
                await asyncio.sleep(self.collection_interval)

    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        # This would integrate with actual system monitoring
        # For now, we'll just log that collection is happening
        logger.debug("Collecting system metrics")


class PrometheusExporter:
    """Prometheus metrics exporter."""

    def __init__(self, registry: MetricsRegistry, port: int = 8000):
        self.registry = registry
        self.port = port
        self.app = None

    async def start_server(self):
        """Start Prometheus metrics server."""
        try:
            from aiohttp import web

            self.app = web.Application()
            self.app.router.add_get("/metrics", self._metrics_handler)

            runner = web.AppRunner(self.app)
            await runner.setup()

            site = web.TCPSite(runner, "127.0.0.1", self.port)
            await site.start()

            logger.info("Prometheus metrics server started", port=self.port)

        except ImportError:
            logger.warning("aiohttp not available, Prometheus server not started")

    async def _metrics_handler(self, request):
        """Handle metrics request."""
        try:
            from aiohttp import web

            samples = await self.registry.get_all_samples()
            output = self._format_prometheus_output(samples)

            return web.Response(
                text=output,
                content_type="text/plain; version=0.0.4; charset=utf-8"
            )

        except Exception as e:
            logger.error("Error generating metrics", error=str(e))
            return web.Response(text="Error generating metrics", status=500)

    def _format_prometheus_output(self, samples: List[MetricSample]) -> str:
        """Format samples as Prometheus exposition format."""
        output_lines = []

        # Group samples by metric name
        metrics_by_name = defaultdict(list)
        for sample in samples:
            metrics_by_name[sample.name].append(sample)

        for metric_name, metric_samples in metrics_by_name.items():
            # Add metric samples
            for sample in metric_samples:
                labels_str = ""
                if sample.labels:
                    label_pairs = [f'{k}="{v}"' for k, v in sample.labels.items()]
                    labels_str = "{" + ",".join(label_pairs) + "}"

                output_lines.append(f"{sample.name}{labels_str} {sample.value}")

        return "\n".join(output_lines) + "\n"


# Global metrics registry and workflow metrics
_global_registry = MetricsRegistry()
_global_workflow_metrics = WorkflowMetrics(_global_registry)


async def get_workflow_metrics() -> WorkflowMetrics:
    """Get global workflow metrics instance."""
    await _global_workflow_metrics.initialize()
    return _global_workflow_metrics


async def get_metrics_registry() -> MetricsRegistry:
    """Get global metrics registry."""
    return _global_registry
