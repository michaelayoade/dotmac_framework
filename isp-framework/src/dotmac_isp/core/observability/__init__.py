"""
Enhanced Observability Package for DotMac Platform.

This package provides advanced observability capabilities including
distributed tracing, correlation management, and performance analysis.
"""

from .distributed_tracing import (
    CorrelationManager,
    DistributedTracer,
    TraceAnalyzer,
    TraceContext,
    TracePropagator,
    correlation_manager,
    default_tracer,
    start_trace,
    trace_analyzer,
    trace_async,
    trace_sync,
)

__all__ = [
    "DistributedTracer",
    "TraceContext",
    "TracePropagator",
    "TraceAnalyzer",
    "CorrelationManager",
    "default_tracer",
    "trace_analyzer",
    "correlation_manager",
    "start_trace",
    "trace_async",
    "trace_sync",
]
