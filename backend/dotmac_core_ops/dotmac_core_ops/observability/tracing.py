"""
Distributed tracing implementation for workflow operations.
"""

import asyncio
import uuid
import time
from typing import Any, Dict, List, Optional, AsyncContextManager
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class SpanKind(str, Enum):
    """Types of spans."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(str, Enum):
    """Span status codes."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """Span context for distributed tracing."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = self._generate_trace_id()
        if not self.span_id:
            self.span_id = self._generate_span_id()

    @staticmethod
    def _generate_trace_id() -> str:
        """Generate a new trace ID."""
        return uuid.uuid4().hex

    @staticmethod
    def _generate_span_id() -> str:
        """Generate a new span ID."""
        return uuid.uuid4().hex[:16]

    def create_child_context(self) -> "SpanContext":
        """Create a child span context."""
        return SpanContext(
            trace_id=self.trace_id,
            span_id=self._generate_span_id(),
            parent_span_id=self.span_id,
            baggage=self.baggage.copy()
        )


@dataclass
class Span:
    """Distributed tracing span."""

    context: SpanContext
    operation_name: str
    kind: SpanKind = SpanKind.INTERNAL
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def set_tag(self, key: str, value: Any):
        """Set a span tag."""
        self.tags[key] = value

    def set_tags(self, tags: Dict[str, Any]):
        """Set multiple span tags."""
        self.tags.update(tags)

    def log(self, message: str, **kwargs):
        """Add a log entry to the span."""
        log_entry = {
            "timestamp": time.time(),
            "message": message,
            **kwargs
        }
        self.logs.append(log_entry)

    def set_status(self, status: SpanStatus, description: Optional[str] = None):
        """Set span status."""
        self.status = status
        if description:
            self.set_tag("status.description", description)

    def finish(self):
        """Finish the span."""
        if self.end_time is None:
            self.end_time = time.time()

    @property
    def duration(self) -> Optional[float]:
        """Get span duration in seconds."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_span_id": self.context.parent_span_id,
            "operation_name": self.operation_name,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "status": self.status.value,
            "tags": self.tags,
            "logs": self.logs
        }


class TracingBackend:
    """Base class for tracing backends."""

    async def report_span(self, span: Span):
        """Report a completed span."""
        raise NotImplementedError

    async def flush(self):
        """Flush any pending spans."""
        pass


class InMemoryTracingBackend(TracingBackend):
    """In-memory tracing backend for testing."""

    def __init__(self, max_spans: int = 10000):
        self.spans: List[Span] = []
        self.max_spans = max_spans
        self._lock = asyncio.Lock()

    async def report_span(self, span: Span):
        """Report a completed span."""
        async with self._lock:
            self.spans.append(span)

            # Keep only recent spans
            if len(self.spans) > self.max_spans:
                self.spans = self.spans[-self.max_spans//2:]

    async def get_spans(
        self,
        trace_id: Optional[str] = None,
        operation_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Span]:
        """Get spans with optional filtering."""
        async with self._lock:
            filtered_spans = self.spans

            if trace_id:
                filtered_spans = [s for s in filtered_spans if s.context.trace_id == trace_id]

            if operation_name:
                filtered_spans = [s for s in filtered_spans if s.operation_name == operation_name]

            return filtered_spans[-limit:]

    async def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace."""
        return await self.get_spans(trace_id=trace_id, limit=1000)


class JaegerTracingBackend(TracingBackend):
    """Jaeger tracing backend."""

    def __init__(self, jaeger_endpoint: str, service_name: str = "dotmac-core-ops"):
        self.jaeger_endpoint = jaeger_endpoint
        self.service_name = service_name
        self.pending_spans: List[Span] = []
        self.batch_size = 100
        self._lock = asyncio.Lock()

    async def report_span(self, span: Span):
        """Report a completed span."""
        async with self._lock:
            self.pending_spans.append(span)

            if len(self.pending_spans) >= self.batch_size:
                await self._flush_spans()

    async def flush(self):
        """Flush any pending spans."""
        async with self._lock:
            if self.pending_spans:
                await self._flush_spans()

    async def _flush_spans(self):
        """Flush pending spans to Jaeger."""
        if not self.pending_spans:
            return

        try:
            # Convert spans to Jaeger format
            jaeger_spans = []
            for span in self.pending_spans:
                jaeger_span = self._convert_to_jaeger_format(span)
                jaeger_spans.append(jaeger_span)

            # Send to Jaeger (would use actual HTTP client in production)
            logger.debug(
                "Sending spans to Jaeger",
                endpoint=self.jaeger_endpoint,
                span_count=len(jaeger_spans)
            )

            self.pending_spans.clear()

        except Exception as e:
            logger.error("Failed to send spans to Jaeger", error=str(e))

    def _convert_to_jaeger_format(self, span: Span) -> Dict[str, Any]:
        """Convert span to Jaeger format."""
        return {
            "traceID": span.context.trace_id,
            "spanID": span.context.span_id,
            "parentSpanID": span.context.parent_span_id,
            "operationName": span.operation_name,
            "startTime": int(span.start_time * 1_000_000),  # microseconds
            "duration": int((span.duration or 0) * 1_000_000),  # microseconds
            "tags": [{"key": k, "value": v} for k, v in span.tags.items()],
            "logs": [
                {
                    "timestamp": int(log["timestamp"] * 1_000_000),
                    "fields": [{"key": k, "value": v} for k, v in log.items() if k != "timestamp"]
                }
                for log in span.logs
            ],
            "process": {
                "serviceName": self.service_name,
                "tags": []
            }
        }


class Tracer:
    """Distributed tracer."""

    def __init__(self, backend: TracingBackend, service_name: str = "dotmac-core-ops"):
        self.backend = backend
        self.service_name = service_name
        self.active_spans: Dict[str, Span] = {}
        self._context_var = None

        try:
            import contextvars
            self._context_var = contextvars.ContextVar('tracing_context', default=None)
        except ImportError:
            logger.warning("contextvars not available, using thread-local storage")

    def get_current_context(self) -> Optional[SpanContext]:
        """Get current tracing context."""
        if self._context_var:
            return self._context_var.get()
        return None

    def set_current_context(self, context: Optional[SpanContext]):
        """Set current tracing context."""
        if self._context_var:
            self._context_var.set(context)

    def start_span(
        self,
        operation_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_context: Optional[SpanContext] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> Span:
        """Start a new span."""
        # Determine parent context
        if parent_context is None:
            parent_context = self.get_current_context()

        # Create span context
        if parent_context:
            span_context = parent_context.create_child_context()
        else:
            span_context = SpanContext(
                trace_id=SpanContext._generate_trace_id(),
                span_id=SpanContext._generate_span_id()
            )

        # Create span
        span = Span(
            context=span_context,
            operation_name=operation_name,
            kind=kind
        )

        # Set default tags
        span.set_tag("service.name", self.service_name)
        span.set_tag("span.kind", kind.value)

        if tags:
            span.set_tags(tags)

        # Store active span
        self.active_spans[span.context.span_id] = span

        return span

    async def finish_span(self, span: Span):
        """Finish a span."""
        span.finish()

        # Remove from active spans
        self.active_spans.pop(span.context.span_id, None)

        # Report to backend
        await self.backend.report_span(span)

    @asynccontextmanager
    async def span(
        self,
        operation_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_context: Optional[SpanContext] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> AsyncContextManager[Span]:
        """Context manager for spans."""
        span = self.start_span(operation_name, kind, parent_context, tags)

        # Set as current context
        old_context = self.get_current_context()
        self.set_current_context(span.context)

        try:
            yield span
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            span.set_tag("error", True)
            span.set_tag("error.message", str(e))
            span.set_tag("error.type", type(e).__name__)
            raise
        finally:
            # Restore old context
            self.set_current_context(old_context)
            await self.finish_span(span)

    async def flush(self):
        """Flush all pending spans."""
        await self.backend.flush()


class WorkflowTracer:
    """Specialized tracer for workflow operations."""

    def __init__(self, tracer: Tracer):
        self.tracer = tracer

    @asynccontextmanager
    async def trace_workflow_run(
        self,
        tenant_id: str,
        workflow_id: str,
        run_id: str,
        business_key: Optional[str] = None
    ) -> AsyncContextManager[Span]:
        """Trace a workflow run."""
        tags = {
            "tenant.id": tenant_id,
            "workflow.id": workflow_id,
            "workflow.run.id": run_id,
            "component": "workflow_engine"
        }

        if business_key:
            tags["workflow.business_key"] = business_key

        async with self.tracer.span(
            f"workflow.run.{workflow_id}",
            kind=SpanKind.SERVER,
            tags=tags
        ) as span:
            yield span

    @asynccontextmanager
    async def trace_step_execution(
        self,
        tenant_id: str,
        workflow_id: str,
        run_id: str,
        step_id: str,
        attempt: int = 1
    ) -> AsyncContextManager[Span]:
        """Trace a step execution."""
        tags = {
            "tenant.id": tenant_id,
            "workflow.id": workflow_id,
            "workflow.run.id": run_id,
            "workflow.step.id": step_id,
            "workflow.step.attempt": attempt,
            "component": "step_executor"
        }

        async with self.tracer.span(
            f"workflow.step.{step_id}",
            kind=SpanKind.INTERNAL,
            tags=tags
        ) as span:
            yield span

    @asynccontextmanager
    async def trace_event_publish(
        self,
        tenant_id: str,
        event_type: str,
        topic: str
    ) -> AsyncContextManager[Span]:
        """Trace event publishing."""
        tags = {
            "tenant.id": tenant_id,
            "event.type": event_type,
            "messaging.destination": topic,
            "component": "event_publisher"
        }

        async with self.tracer.span(
            f"event.publish.{event_type}",
            kind=SpanKind.PRODUCER,
            tags=tags
        ) as span:
            yield span

    @asynccontextmanager
    async def trace_event_consume(
        self,
        tenant_id: str,
        event_type: str,
        topic: str,
        consumer_group: str
    ) -> AsyncContextManager[Span]:
        """Trace event consumption."""
        tags = {
            "tenant.id": tenant_id,
            "event.type": event_type,
            "messaging.destination": topic,
            "messaging.consumer_group": consumer_group,
            "component": "event_consumer"
        }

        async with self.tracer.span(
            f"event.consume.{event_type}",
            kind=SpanKind.CONSUMER,
            tags=tags
        ) as span:
            yield span

    @asynccontextmanager
    async def trace_queue_job(
        self,
        tenant_id: str,
        queue_name: str,
        job_id: str,
        job_type: str
    ) -> AsyncContextManager[Span]:
        """Trace queue job processing."""
        tags = {
            "tenant.id": tenant_id,
            "queue.name": queue_name,
            "job.id": job_id,
            "job.type": job_type,
            "component": "job_processor"
        }

        async with self.tracer.span(
            f"queue.job.{job_type}",
            kind=SpanKind.CONSUMER,
            tags=tags
        ) as span:
            yield span

    @asynccontextmanager
    async def trace_scheduler_execution(
        self,
        tenant_id: str,
        schedule_id: str,
        job_type: str
    ) -> AsyncContextManager[Span]:
        """Trace scheduled job execution."""
        tags = {
            "tenant.id": tenant_id,
            "schedule.id": schedule_id,
            "job.type": job_type,
            "component": "scheduler"
        }

        async with self.tracer.span(
            f"scheduler.job.{job_type}",
            kind=SpanKind.INTERNAL,
            tags=tags
        ) as span:
            yield span


class TracingMiddleware:
    """Middleware for automatic tracing of HTTP requests."""

    def __init__(self, tracer: Tracer):
        self.tracer = tracer

    async def __call__(self, request, handler):
        """Process request with tracing."""
        # Extract trace context from headers
        trace_id = request.headers.get("X-Trace-Id")
        span_id = request.headers.get("X-Span-Id")
        parent_span_id = request.headers.get("X-Parent-Span-Id")

        parent_context = None
        if trace_id and span_id:
            parent_context = SpanContext(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id
            )

        # Start span for request
        tags = {
            "http.method": request.method,
            "http.url": str(request.url),
            "http.scheme": request.url.scheme,
            "http.host": request.url.host,
            "http.target": request.url.path,
            "component": "http_server"
        }

        async with self.tracer.span(
            f"{request.method} {request.url.path}",
            kind=SpanKind.SERVER,
            parent_context=parent_context,
            tags=tags
        ) as span:
            try:
                response = await handler(request)

                span.set_tag("http.status_code", response.status)
                if response.status >= 400:
                    span.set_status(SpanStatus.ERROR, f"HTTP {response.status}")
                else:
                    span.set_status(SpanStatus.OK)

                # Add trace headers to response
                response.headers["X-Trace-Id"] = span.context.trace_id
                response.headers["X-Span-Id"] = span.context.span_id

                return response

            except Exception as e:
                span.set_tag("http.status_code", 500)
                span.set_status(SpanStatus.ERROR, str(e))
                raise


class StructlogTracingProcessor:
    """Structlog processor to add tracing context to logs."""

    def __init__(self, tracer: Tracer):
        self.tracer = tracer

    def __call__(self, logger, method_name, event_dict):
        """Add tracing context to log event."""
        context = self.tracer.get_current_context()
        if context:
            event_dict["trace_id"] = context.trace_id
            event_dict["span_id"] = context.span_id
            if context.parent_span_id:
                event_dict["parent_span_id"] = context.parent_span_id

        return event_dict


# Global tracer instances
_global_backend = InMemoryTracingBackend()
_global_tracer = Tracer(_global_backend)
_global_workflow_tracer = WorkflowTracer(_global_tracer)


def get_tracer() -> Tracer:
    """Get global tracer instance."""
    return _global_tracer


def get_workflow_tracer() -> WorkflowTracer:
    """Get global workflow tracer instance."""
    return _global_workflow_tracer


def configure_tracing(
    backend_type: str = "memory",
    jaeger_endpoint: Optional[str] = None,
    service_name: str = "dotmac-core-ops"
):
    """Configure global tracing."""
    global _global_backend, _global_tracer, _global_workflow_tracer

    if backend_type == "jaeger" and jaeger_endpoint:
        _global_backend = JaegerTracingBackend(jaeger_endpoint, service_name)
    else:
        _global_backend = InMemoryTracingBackend()

    _global_tracer = Tracer(_global_backend, service_name)
    _global_workflow_tracer = WorkflowTracer(_global_tracer)

    # Configure structlog processor
    tracing_processor = StructlogTracingProcessor(_global_tracer)

    # Add to structlog configuration (would need to be integrated with existing config)
    logger.info("Tracing configured", backend_type=backend_type, service_name=service_name)
