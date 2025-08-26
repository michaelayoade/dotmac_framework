"""
Distributed Tracing Enhancements for DotMac Platform.

This module provides advanced distributed tracing capabilities with OpenTelemetry integration,
correlation ID management, and cross-service trace propagation.
"""

import logging
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

logger = logging.getLogger(__name__)


@dataclass
class TraceContext:
    """Enhanced trace context with correlation and causation tracking."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    operation_name: str = ""
    service_name: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: float | None = None
    status: str = "OK"
    tags: dict[str, Any] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    baggage: dict[str, str] = field(default_factory=dict)

    # DotMac-specific fields
    tenant_id: str | None = None
    user_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None  # For event causation tracking

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "service_name": self.service_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "logs": self.logs,
            "baggage": self.baggage,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
        }


class TraceHeaders:
    """Standard trace header names for HTTP propagation."""

    TRACE_ID = "X-Trace-Id"
    SPAN_ID = "X-Span-Id"
    PARENT_SPAN_ID = "X-Parent-Span-Id"
    CORRELATION_ID = "X-Correlation-Id"
    CAUSATION_ID = "X-Causation-Id"
    TENANT_ID = "X-Tenant-Id"
    USER_ID = "X-User-Id"
    REQUEST_ID = "X-Request-Id"
    BAGGAGE = "X-Trace-Baggage"


class TracePropagator:
    """Handles trace context propagation across services."""

    @staticmethod
    def inject_headers(context: TraceContext) -> dict[str, str]:
        """Inject trace context into HTTP headers."""
        headers = {
            TraceHeaders.TRACE_ID: context.trace_id,
            TraceHeaders.SPAN_ID: context.span_id,
        }

        if context.parent_span_id:
            headers[TraceHeaders.PARENT_SPAN_ID] = context.parent_span_id
        if context.correlation_id:
            headers[TraceHeaders.CORRELATION_ID] = context.correlation_id
        if context.causation_id:
            headers[TraceHeaders.CAUSATION_ID] = context.causation_id
        if context.tenant_id:
            headers[TraceHeaders.TENANT_ID] = context.tenant_id
        if context.user_id:
            headers[TraceHeaders.USER_ID] = context.user_id
        if context.request_id:
            headers[TraceHeaders.REQUEST_ID] = context.request_id
        if context.baggage:
            # Serialize baggage as comma-separated key=value pairs
            baggage_str = ",".join(f"{k}={v}" for k, v in context.baggage.items()
            headers[TraceHeaders.BAGGAGE] = baggage_str

        return headers

    @staticmethod
    def extract_context(headers: dict[str, str]) -> TraceContext | None:
        """Extract trace context from HTTP headers."""
        trace_id = headers.get(TraceHeaders.TRACE_ID)
        span_id = headers.get(TraceHeaders.SPAN_ID)

        if not trace_id or not span_id:
            return None

        # Parse baggage
        baggage = {}
        baggage_str = headers.get(TraceHeaders.BAGGAGE, "")
        if baggage_str:
            for item in baggage_str.split(","):
                if "=" in item:
                    key, value = item.split("=", 1)
                    baggage[key.strip()] = value.strip()

        return TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=headers.get(TraceHeaders.PARENT_SPAN_ID),
            correlation_id=headers.get(TraceHeaders.CORRELATION_ID),
            causation_id=headers.get(TraceHeaders.CAUSATION_ID),
            tenant_id=headers.get(TraceHeaders.TENANT_ID),
            user_id=headers.get(TraceHeaders.USER_ID),
            request_id=headers.get(TraceHeaders.REQUEST_ID),
            baggage=baggage,
        )


class DistributedTracer:
    """Enhanced distributed tracer with advanced features."""

    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        self.active_spans: dict[str, TraceContext] = {}
        self.completed_spans: list[TraceContext] = []
        self.span_processors: list[Callable[[TraceContext], None]] = []

        # Sampling configuration
        self.sampling_rate = 1.0  # Sample 100% by default
        self.max_spans_per_trace = 1000

    def add_span_processor(self, processor: Callable[[TraceContext], None]):
        """Add a span processor for custom span handling."""
        self.span_processors.append(processor)

    def start_span(
        self,
        operation_name: str,
        parent_context: TraceContext | None = None,
        tags: dict[str, Any] | None = None,
        start_time: datetime | None = None,
    ) -> TraceContext:
        """Start a new span."""
        # Generate IDs
        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        else:
            trace_id = str(uuid.uuid4()
            parent_span_id = None

        span_id = str(uuid.uuid4()

        # Create span context
        context = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=start_time or datetime.now(UTC),
            tags=tags or {},
        )

        # Inherit context from parent
        if parent_context:
            context.tenant_id = parent_context.tenant_id
            context.user_id = parent_context.user_id
            context.request_id = parent_context.request_id
            context.correlation_id = parent_context.correlation_id
            context.baggage = parent_context.baggage.model_copy()

        # Add service tags
        context.tags.update(
            {
                "service.name": self.service_name,
                "service.version": self.version,
                "span.kind": "internal",
            }
        )

        self.active_spans[span_id] = context
        return context

    def finish_span(
        self,
        context: TraceContext,
        status: str = "OK",
        end_time: datetime | None = None,
    ) -> TraceContext:
        """Finish a span."""
        context.end_time = end_time or datetime.now(UTC)
        context.status = status

        if context.start_time and context.end_time:
            duration = context.end_time - context.start_time
            context.duration_ms = duration.total_seconds() * 1000

        # Remove from active spans
        if context.span_id in self.active_spans:
            del self.active_spans[context.span_id]

        # Add to completed spans
        self.completed_spans.append(context)

        # Process span through processors
        for processor in self.span_processors:
            try:
                processor(context)
            except Exception as e:
                logger.warning(f"Span processor error: {e}")

        return context

    def add_span_log(
        self,
        context: TraceContext,
        level: str,
        message: str,
        fields: dict[str, Any] | None = None,
    ):
        """Add a log entry to a span."""
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "message": message,
            "fields": fields or {},
        }
        context.logs.append(log_entry)

    def set_span_tag(self, context: TraceContext, key: str, value: Any):
        """Set a tag on a span."""
        context.tags[key] = value

    def set_baggage(self, context: TraceContext, key: str, value: str):
        """Set baggage item that propagates to child spans."""
        context.baggage[key] = value

    @asynccontextmanager
    async def span(
        self,
        operation_name: str,
        parent_context: TraceContext | None = None,
        tags: dict[str, Any] | None = None,
    ):
        """Context manager for automatic span lifecycle management."""
        span_context = self.start_span(operation_name, parent_context, tags)

        try:
            yield span_context
            self.finish_span(span_context, "OK")
        except Exception as e:
            self.set_span_tag(span_context, "error", True)
            self.set_span_tag(span_context, "error.message", str(e)
            self.add_span_log(
                span_context, "ERROR", str(e), {"exception": type(e).__name__}
            )
            self.finish_span(span_context, "ERROR")
            raise

    def create_child_context(
        self, parent: TraceContext, operation_name: str
    ) -> TraceContext:
        """Create a child span context."""
        return self.start_span(operation_name, parent)

    def get_active_spans(self) -> dict[str, TraceContext]:
        """Get all currently active spans."""
        return self.active_spans.model_copy()

    def get_completed_spans(self, trace_id: str | None = None) -> list[TraceContext]:
        """Get completed spans, optionally filtered by trace ID."""
        if trace_id:
            return [span for span in self.completed_spans if span.trace_id == trace_id]
        return self.completed_spans.model_copy()


class TraceAnalyzer:
    """Analyzes trace data for performance insights."""

    def __init__(self):
        self.traces: dict[str, list[TraceContext]] = {}

    def add_spans(self, spans: list[TraceContext]):
        """Add spans to analyzer."""
        for span in spans:
            if span.trace_id not in self.traces:
                self.traces[span.trace_id] = []
            self.traces[span.trace_id].append(span)

    def analyze_trace_performance(self, trace_id: str) -> dict[str, Any]:
        """Analyze performance characteristics of a trace."""
        spans = self.traces.get(trace_id, [])
        if not spans:
            return {"error": "Trace not found"}

        # Sort spans by start time
        spans.sort(key=lambda s: s.start_time or datetime.min)

        # Calculate trace duration
        trace_start = min(s.start_time for s in spans if s.start_time)
        trace_end = max(s.end_time for s in spans if s.end_time)
        trace_duration = (
            (trace_end - trace_start).total_seconds() * 1000
            if trace_end and trace_start
            else 0
        )

        # Calculate critical path
        critical_path = self._calculate_critical_path(spans)

        # Service breakdown
        service_breakdown = {}
        for span in spans:
            service = span.service_name
            if service not in service_breakdown:
                service_breakdown[service] = {"count": 0, "total_duration": 0}
            service_breakdown[service]["count"] += 1
            service_breakdown[service]["total_duration"] += span.duration_ms or 0

        # Error analysis
        error_spans = [s for s in spans if s.status == "ERROR"]

        return {
            "trace_id": trace_id,
            "total_spans": len(spans),
            "trace_duration_ms": trace_duration,
            "critical_path_duration_ms": critical_path,
            "service_breakdown": service_breakdown,
            "error_count": len(error_spans),
            "error_rate": len(error_spans) / len(spans) * 100 if spans else 0,
            "services_involved": list(service_breakdown.keys(),
            "deepest_nesting": self._calculate_max_depth(spans),
        }

    def _calculate_critical_path(self, spans: list[TraceContext]) -> float:
        """Calculate the critical path duration."""
        # Simplified critical path calculation
        # In a real implementation, this would build a dependency graph
        max_duration = 0
        for span in spans:
            if span.duration_ms and span.duration_ms > max_duration:
                max_duration = span.duration_ms
        return max_duration

    def _calculate_max_depth(self, spans: list[TraceContext]) -> int:
        """Calculate maximum nesting depth of spans."""
        span_map = {s.span_id: s for s in spans}
        max_depth = 0

        for span in spans:
            depth = self._get_span_depth(span, span_map, set()
            max_depth = max(max_depth, depth)

        return max_depth

    def _get_span_depth(
        self, span: TraceContext, span_map: dict[str, TraceContext], visited: set
    ) -> int:
        """Recursively calculate span depth."""
        if span.span_id in visited:
            return 0

        visited.add(span.span_id)

        if not span.parent_span_id or span.parent_span_id not in span_map:
            return 1

        parent = span_map[span.parent_span_id]
        return 1 + self._get_span_depth(parent, span_map, visited)


class CorrelationManager:
    """Manages correlation and causation relationships between operations."""

    def __init__(self):
        self.correlations: dict[str, list[str]] = {}  # correlation_id -> [trace_ids]
        self.causations: dict[str, str] = {}  # causation_id -> causing_trace_id

    def correlate_traces(self, correlation_id: str, trace_id: str):
        """Associate a trace with a correlation ID."""
        if correlation_id not in self.correlations:
            self.correlations[correlation_id] = []
        self.correlations[correlation_id].append(trace_id)

    def set_causation(self, effect_trace_id: str, cause_trace_id: str):
        """Record causation relationship between traces."""
        self.causations[effect_trace_id] = cause_trace_id

    def get_correlated_traces(self, correlation_id: str) -> list[str]:
        """Get all trace IDs associated with a correlation ID."""
        return self.correlations.get(correlation_id, [])

    def get_causation_chain(self, trace_id: str) -> list[str]:
        """Get the causation chain for a trace."""
        chain = [trace_id]
        current = trace_id

        # Walk backwards through causation chain
        while current in self.causations:
            current = self.causations[current]
            if current in chain:  # Prevent infinite loops
                break
            chain.append(current)

        return list(reversed(chain)


# Global instances for convenience
default_tracer = DistributedTracer("dotmac-platform")
trace_analyzer = TraceAnalyzer()
correlation_manager = CorrelationManager()


# Convenience functions
def start_trace(operation_name: str, **kwargs) -> TraceContext:
    """Start a new trace."""
    return default_tracer.start_span(operation_name, **kwargs)


def trace_async(operation_name: str = None):
    """Decorator for automatic async function tracing."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            async with default_tracer.span(op_name) as span_context:
                default_tracer.set_span_tag(
                    span_context, "function.name", func.__name__
                )
                default_tracer.set_span_tag(
                    span_context, "function.module", func.__module__
                )
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def trace_sync(operation_name: str = None):
    """Decorator for automatic sync function tracing."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            span_context = default_tracer.start_span(op_name)
            default_tracer.set_span_tag(span_context, "function.name", func.__name__)
            default_tracer.set_span_tag(
                span_context, "function.module", func.__module__
            )

            try:
                result = func(*args, **kwargs)
                default_tracer.finish_span(span_context, "OK")
                return result
            except Exception as e:
                default_tracer.set_span_tag(span_context, "error", True)
                default_tracer.set_span_tag(span_context, "error.message", str(e)
                default_tracer.finish_span(span_context, "ERROR")
                raise

        return wrapper

    return decorator
