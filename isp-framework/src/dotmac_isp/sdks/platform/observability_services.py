"""
Refactored observability services with separation of concerns.
Each class has a single, well-defined responsibility.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from dotmac_isp.sdks.contracts.observability import (
    LogEntry,
    LogLevel,
    LogsQuery,
    LogsQueryResponse,
    Metric,
    MetricsQuery,
    MetricsQueryResponse,
    MetricType,
    TraceSpan,
    TracesQuery,
    TracesQueryResponse,
    TraceStatus,
)
from dotmac_isp.sdks.contracts.transport import RequestContext
from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

logger = logging.getLogger(__name__)


class MetricStorage:
    """Handles storage and retrieval of metrics."""

    def __init__(self, database_sdk=None, cache_sdk=None):
        self.database_sdk = database_sdk
        self.cache_sdk = cache_sdk
        self._memory_metrics: dict[str, list[Metric]] = {}

    async def store_metric(self, metric: Metric) -> bool:
        """Store a metric."""
        try:
            # Store in memory for development/testing
            tenant_key = str(metric.tenant_id)
            if tenant_key not in self._memory_metrics:
                self._memory_metrics[tenant_key] = []
            self._memory_metrics[tenant_key].append(metric)

            # Store in database if available
            if self.database_sdk:
                await self.database_sdk.store_metric(metric)

            return True
        except Exception as e:
            logger.error(f"Failed to store metric: {e}")
            return False

    async def query_metrics(self, query: MetricsQuery) -> MetricsQueryResponse:
        """Query metrics based on criteria."""
        try:
            # Simple in-memory query for testing
            tenant_key = str(query.tenant_id)
            metrics = self._memory_metrics.get(tenant_key, [])

            # Filter by metric names if specified
            if query.metric_names:
                metrics = [m for m in metrics if m.name in query.metric_names]

            # Filter by time range
            if query.start_time and query.end_time:
                metrics = [
                    m
                    for m in metrics
                    if query.start_time <= m.timestamp <= query.end_time
                ]

            return MetricsQueryResponse(
                metrics=[
                    m.model_dump()
                    for m in (
                        metrics[: getattr(query, "limit", None)]
                        if getattr(query, "limit", None)
                        else metrics
                    )
                ],
                query=query,
                execution_time_ms=1.0,
            )
        except Exception as e:
            logger.error(f"Failed to query metrics: {e}")
            return MetricsQueryResponse(metrics=[], query=query, execution_time_ms=0.0)


class LogStorage:
    """Handles storage and retrieval of logs."""

    def __init__(self, database_sdk=None, cache_sdk=None):
        self.database_sdk = database_sdk
        self.cache_sdk = cache_sdk
        self._memory_logs: dict[str, list[LogEntry]] = {}

    async def store_log(self, log_entry: LogEntry) -> bool:
        """Store a log entry."""
        try:
            # Store in memory for development/testing
            tenant_key = str(log_entry.tenant_id)
            if tenant_key not in self._memory_logs:
                self._memory_logs[tenant_key] = []
            self._memory_logs[tenant_key].append(log_entry)

            # Store in database if available
            if self.database_sdk:
                await self.database_sdk.store_log(log_entry)

            return True
        except Exception as e:
            logger.error(f"Failed to store log: {e}")
            return False

    async def query_logs(self, query: LogsQuery) -> LogsQueryResponse:
        """Query logs based on criteria."""
        try:
            # Simple in-memory query for testing
            tenant_key = str(query.tenant_id)
            logs = self._memory_logs.get(tenant_key, [])

            # Filter by levels if specified
            if query.levels:
                logs = [log for log in logs if log.level in query.levels]

            # Filter by services if specified
            if query.services:
                logs = [log for log in logs if log.service in query.services]

            # Filter by time range
            if query.start_time and query.end_time:
                logs = [
                    log
                    for log in logs
                    if query.start_time <= log.timestamp <= query.end_time
                ]

            return LogsQueryResponse(
                logs=(
                    logs[: getattr(query, "limit", None)]
                    if getattr(query, "limit", None)
                    else logs
                ),
                total_count=len(logs),
                query=query,
                execution_time_ms=1.0,
            )
        except Exception as e:
            logger.error(f"Failed to query logs: {e}")
            return LogsQueryResponse(
                logs=[], total_count=0, query=query, execution_time_ms=0.0
            )


class TraceStorage:
    """Handles storage and retrieval of traces."""

    def __init__(self, database_sdk=None, cache_sdk=None):
        self.database_sdk = database_sdk
        self.cache_sdk = cache_sdk
        self._memory_traces: dict[str, dict[str, TraceSpan]] = {}

    async def store_trace_span(self, span: TraceSpan) -> bool:
        """Store a trace span."""
        try:
            # Store in memory for development/testing
            tenant_key = str(span.tenant_id)
            if tenant_key not in self._memory_traces:
                self._memory_traces[tenant_key] = {}
            self._memory_traces[tenant_key][span.span_id] = span

            # Store in database if available
            if self.database_sdk:
                await self.database_sdk.store_trace_span(span)

            return True
        except Exception as e:
            logger.error(f"Failed to store trace span: {e}")
            return False

    async def get_trace_span(self, tenant_id: UUID, span_id: str) -> TraceSpan | None:
        """Get a specific trace span."""
        tenant_key = str(tenant_id)
        return self._memory_traces.get(tenant_key, {}).get(span_id)

    async def query_traces(self, query: TracesQuery) -> TracesQueryResponse:
        """Query traces based on criteria."""
        try:
            # Simple in-memory query for testing
            tenant_key = str(query.tenant_id)
            all_spans = self._memory_traces.get(tenant_key, {}).values()

            # Filter by service if specified
            if query.service_name:
                all_spans = [
                    s for s in all_spans if s.service_name == query.service_name
                ]

            # Convert to list and apply limit
            spans = list(all_spans)
            if query.limit:
                spans = spans[: query.limit]

            return TracesQueryResponse(spans=spans, total_count=len(spans))
        except Exception as e:
            logger.error(f"Failed to query traces: {e}")
            return TracesQueryResponse(spans=[], total_count=0)


class ObservabilityQueueManager:
    """Manages async processing queues for observability data."""

    def __init__(self, max_queue_size: int = 50000, batch_size: int = 1000):
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.metrics_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.logs_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._processing_tasks: list[asyncio.Task] = []

    async def queue_metric(self, metric: Metric) -> bool:
        """Queue a metric for async processing."""
        try:
            await self.metrics_queue.put(metric)
            return True
        except asyncio.QueueFull:
            logger.warning("Metrics queue is full, dropping metric")
            return False

    async def queue_log(self, log_entry: LogEntry) -> bool:
        """Queue a log entry for async processing."""
        try:
            await self.logs_queue.put(log_entry)
            return True
        except asyncio.QueueFull:
            logger.warning("Logs queue is full, dropping log entry")
            return False

    def start_background_processing(
        self, metric_storage: MetricStorage, log_storage: LogStorage
    ):
        """Start background processing tasks."""
        # Start metrics processing task
        metrics_task = asyncio.create_task(self._process_metrics_queue(metric_storage))
        self._processing_tasks.append(metrics_task)

        # Start logs processing task
        logs_task = asyncio.create_task(self._process_logs_queue(log_storage))
        self._processing_tasks.append(logs_task)

    async def stop_background_processing(self):
        """Stop all background processing tasks."""
        for task in self._processing_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._processing_tasks, return_exceptions=True)
        self._processing_tasks.clear()

    async def _process_metrics_queue(self, metric_storage: MetricStorage):
        """Process metrics from queue in batches."""
        while True:
            try:
                metrics_batch = []

                # Collect batch of metrics
                for _ in range(self.batch_size):
                    try:
                        metric = await asyncio.wait_for(
                            self.metrics_queue.get(), timeout=1.0
                        )
                        metrics_batch.append(metric)
                    except TimeoutError:
                        break

                # Process batch if we have metrics
                if metrics_batch:
                    for metric in metrics_batch:
                        await metric_storage.store_metric(metric)

                await asyncio.sleep(0.1)  # Small delay to prevent tight loop

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing metrics queue: {e}")

    async def _process_logs_queue(self, log_storage: LogStorage):
        """Process logs from queue in batches."""
        while True:
            try:
                logs_batch = []

                # Collect batch of logs
                for _ in range(self.batch_size):
                    try:
                        log_entry = await asyncio.wait_for(
                            self.logs_queue.get(), timeout=1.0
                        )
                        logs_batch.append(log_entry)
                    except TimeoutError:
                        break

                # Process batch if we have logs
                if logs_batch:
                    for log_entry in logs_batch:
                        await log_storage.store_log(log_entry)

                await asyncio.sleep(0.1)  # Small delay to prevent tight loop

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing logs queue: {e}")


class MetricsService:
    """Service for recording and querying metrics."""

    def __init__(
        self,
        storage: MetricStorage,
        queue_manager: ObservabilityQueueManager | None = None,
        enable_async: bool = True,
    ):
        self.storage = storage
        self.queue_manager = queue_manager
        self.enable_async = enable_async and queue_manager is not None

    async def record_metric(
        self,
        tenant_id: UUID,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: dict[str, str] | None = None,
        context: RequestContext | None = None,
    ) -> bool:
        """Record a metric data point."""
        try:
            metric = Metric(
                name=name,
                type=metric_type,
                value=value,
                timestamp=datetime.now(UTC),
                labels=labels or {},
                tenant_id=tenant_id,
            )

            if self.enable_async and self.queue_manager:
                return await self.queue_manager.queue_metric(metric)
            else:
                return await self.storage.store_metric(metric)

        except Exception as e:
            logger.error(f"Failed to record metric: {e}")
            return False

    async def query_metrics(
        self, query: MetricsQuery, context: RequestContext | None = None
    ) -> MetricsQueryResponse:
        """Query metrics data."""
        return await self.storage.query_metrics(query)


class LoggingService:
    """Service for structured logging."""

    def __init__(
        self,
        storage: LogStorage,
        queue_manager: ObservabilityQueueManager | None = None,
        enable_async: bool = True,
    ):
        self.storage = storage
        self.queue_manager = queue_manager
        self.enable_async = enable_async and queue_manager is not None

    async def log(
        self,
        tenant_id: UUID,
        level: LogLevel,
        message: str,
        service: str | None = None,
        component: str | None = None,
        fields: dict[str, Any] | None = None,
        context: RequestContext | None = None,
    ) -> bool:
        """Log a structured message."""
        try:
            log_entry = LogEntry(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                level=level,
                message=message,
                tenant_id=tenant_id,
                service=service,
                component=component,
                fields=fields or {},
            )

            if context:
                log_entry.request_id = context.headers.x_request_id
                log_entry.correlation_id = context.headers.x_correlation_id
                log_entry.user_id = context.headers.x_user_id

            if self.enable_async and self.queue_manager:
                return await self.queue_manager.queue_log(log_entry)
            else:
                return await self.storage.store_log(log_entry)

        except Exception as e:
            logger.error(f"Failed to log message: {e}")
            return False

    async def query_logs(
        self, query: LogsQuery, context: RequestContext | None = None
    ) -> LogsQueryResponse:
        """Query logs data."""
        return await self.storage.query_logs(query)


class TracingService:
    """Service for distributed tracing."""

    def __init__(self, storage: TraceStorage):
        self.storage = storage

    async def start_trace(
        self,
        tenant_id: UUID,
        operation_name: str,
        service_name: str,
        parent_span_id: str | None = None,
        context: RequestContext | None = None,
    ) -> TraceSpan:
        """Start a new trace span."""
        trace_id = str(uuid4())
        span_id = str(uuid4())

        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=service_name,
            start_time=datetime.now(UTC),
            tenant_id=tenant_id,
        )

        await self.storage.store_trace_span(span)
        return span

    async def finish_trace(
        self,
        span: TraceSpan,
        status: TraceStatus = TraceStatus.OK,
    ) -> bool:
        """Finish a trace span."""
        try:
            span.end_time = datetime.now(UTC)
            span.status = status

            if span.start_time and span.end_time:
                span.duration_ms = (
                    span.end_time - span.start_time
                ).total_seconds() * 1000

            await self.storage.store_trace_span(span)
            return True
        except Exception as e:
            logger.error(f"Failed to finish trace: {e}")
            return False

    async def query_traces(
        self, query: TracesQuery, context: RequestContext | None = None
    ) -> TracesQueryResponse:
        """Query traces data."""
        return await self.storage.query_traces(query)
