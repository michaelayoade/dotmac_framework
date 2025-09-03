"""
Observability hooks and monitoring for plugin system.

Provides extensible hooks for monitoring plugin lifecycle events,
errors, and performance metrics for integration with observability systems.
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Protocol

try:
    from opentelemetry import trace, metrics
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    metrics = None

from .interfaces import IPlugin


class ObservabilityCollector(Protocol):
    """Protocol for observability data collection."""
    
    def record_event(self, event_type: str, plugin_name: str, data: Dict[str, Any]) -> None:
        """Record plugin event."""
        ...
    
    def record_metric(self, metric_name: str, value: float, labels: Dict[str, str]) -> None:
        """Record plugin metric."""
        ...
    
    def record_error(self, plugin_name: str, error: Exception, context: Dict[str, Any]) -> None:
        """Record plugin error."""
        ...


class PluginObservabilityHooks:
    """
    Comprehensive observability hooks for plugin system.
    
    Provides extensible event hooks that can be connected to monitoring
    systems, logging frameworks, and observability platforms.
    """
    
    def __init__(
        self,
        collector: Optional[ObservabilityCollector] = None,
        enable_metrics: bool = True,
        enable_tracing: bool = True,
        enable_logging: bool = True
    ):
        """
        Initialize observability hooks.
        
        Args:
            collector: Optional external observability collector
            enable_metrics: Whether to collect metrics
            enable_tracing: Whether to enable tracing
            enable_logging: Whether to enable logging
        """
        self.collector = collector
        self.enable_metrics = enable_metrics
        self.enable_tracing = enable_tracing and OTEL_AVAILABLE
        self.enable_logging = enable_logging
        
        self._logger = logging.getLogger(__name__)
        self._event_callbacks: Dict[str, List[Callable]] = {}
        
        # OpenTelemetry setup
        if self.enable_tracing and OTEL_AVAILABLE:
            self._tracer = trace.get_tracer(__name__)
            self._meter = metrics.get_meter(__name__)
            
            # Create metrics
            self._plugin_counter = self._meter.create_counter(
                "dotmac_plugins_total",
                description="Total number of plugin operations"
            )
            
            self._plugin_duration = self._meter.create_histogram(
                "dotmac_plugin_operation_duration_seconds", 
                description="Plugin operation duration in seconds"
            )
            
            self._plugin_errors = self._meter.create_counter(
                "dotmac_plugin_errors_total",
                description="Total number of plugin errors"
            )
        else:
            self._tracer = None
            self._meter = None
            self._plugin_counter = None
            self._plugin_duration = None
            self._plugin_errors = None
    
    def add_callback(self, event_type: str, callback: Callable[[IPlugin, Dict[str, Any]], None]) -> None:
        """
        Add callback for specific event type.
        
        Args:
            event_type: Event type to listen for
            callback: Function to call on event
        """
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []
        self._event_callbacks[event_type].append(callback)
    
    def remove_callback(self, event_type: str, callback: Callable) -> None:
        """
        Remove callback for event type.
        
        Args:
            event_type: Event type
            callback: Callback function to remove
        """
        if event_type in self._event_callbacks:
            try:
                self._event_callbacks[event_type].remove(callback)
            except ValueError:
                pass
    
    def _trigger_callbacks(self, event_type: str, plugin: IPlugin, data: Dict[str, Any]) -> None:
        """Trigger registered callbacks for event."""
        for callback in self._event_callbacks.get(event_type, []):
            try:
                callback(plugin, data)
            except Exception as e:
                self._logger.error(f"Error in observability callback for {event_type}: {e}")
    
    def _record_event(self, event_type: str, plugin: IPlugin, data: Dict[str, Any] = None) -> None:
        """Record event with all enabled systems."""
        if data is None:
            data = {}
        
        plugin_data = {
            "plugin_name": plugin.name,
            "plugin_version": plugin.version,
            "plugin_kind": plugin.kind.value,
            "plugin_status": plugin.status.name,
            **data
        }
        
        # Log event
        if self.enable_logging:
            self._logger.info(f"Plugin {event_type}: {plugin.name} ({plugin.kind.value})")
        
        # Record with external collector
        if self.collector:
            try:
                self.collector.record_event(event_type, plugin.name, plugin_data)
            except Exception as e:
                self._logger.error(f"Error recording event with collector: {e}")
        
        # Record metrics
        if self.enable_metrics and self._plugin_counter:
            labels = {
                "plugin_name": plugin.name,
                "plugin_kind": plugin.kind.value,
                "event_type": event_type
            }
            self._plugin_counter.add(1, labels)
        
        # Trigger callbacks
        self._trigger_callbacks(event_type, plugin, plugin_data)
    
    def on_register(self, plugin: IPlugin) -> None:
        """Called when plugin is registered."""
        self._record_event("register", plugin, {
            "metadata": plugin.metadata.to_dict() if hasattr(plugin.metadata, 'to_dict') else {}
        })
    
    def on_init(self, plugin: IPlugin) -> None:
        """Called when plugin initialization succeeds."""
        self._record_event("init", plugin)
    
    def on_start(self, plugin: IPlugin) -> None:
        """Called when plugin startup succeeds."""
        self._record_event("start", plugin)
    
    def on_stop(self, plugin: IPlugin) -> None:
        """Called when plugin is stopped."""
        self._record_event("stop", plugin)
    
    def on_error(self, plugin: IPlugin, error: Exception, context: Dict[str, Any] = None) -> None:
        """Called when plugin encounters an error."""
        if context is None:
            context = {}
        
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            **context
        }
        
        # Log error
        if self.enable_logging:
            self._logger.error(
                f"Plugin error in {plugin.name}: {error}",
                exc_info=error,
                extra={"plugin_name": plugin.name, "plugin_kind": plugin.kind.value}
            )
        
        # Record with external collector
        if self.collector:
            try:
                self.collector.record_error(plugin.name, error, {
                    "plugin_kind": plugin.kind.value,
                    "plugin_status": plugin.status.name,
                    **context
                })
            except Exception as e:
                self._logger.error(f"Error recording error with collector: {e}")
        
        # Record error metrics
        if self.enable_metrics and self._plugin_errors:
            labels = {
                "plugin_name": plugin.name,
                "plugin_kind": plugin.kind.value,
                "error_type": type(error).__name__
            }
            self._plugin_errors.add(1, labels)
        
        # Trigger callbacks
        self._trigger_callbacks("error", plugin, error_data)
    
    def time_operation(self, operation_name: str, plugin: IPlugin):
        """
        Context manager for timing plugin operations.
        
        Args:
            operation_name: Name of operation being timed
            plugin: Plugin instance
            
        Returns:
            Context manager for timing
        """
        return PluginOperationTimer(
            operation_name, plugin, self._plugin_duration, 
            self._tracer, self.enable_logging
        )


class PluginOperationTimer:
    """Context manager for timing plugin operations."""
    
    def __init__(
        self, 
        operation_name: str, 
        plugin: IPlugin,
        duration_metric=None,
        tracer=None,
        enable_logging: bool = True
    ):
        self.operation_name = operation_name
        self.plugin = plugin
        self.duration_metric = duration_metric
        self.tracer = tracer
        self.enable_logging = enable_logging
        self.start_time = None
        self.span = None
        self._logger = logging.getLogger(__name__)
    
    def __enter__(self):
        """Enter timing context."""
        self.start_time = time.time()
        
        # Start tracing span
        if self.tracer:
            self.span = self.tracer.start_span(
                f"plugin.{self.operation_name}",
                attributes={
                    "plugin.name": self.plugin.name,
                    "plugin.kind": self.plugin.kind.value,
                    "plugin.version": self.plugin.version,
                    "operation.name": self.operation_name
                }
            )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit timing context."""
        duration = time.time() - self.start_time
        
        # Record duration metric
        if self.duration_metric:
            labels = {
                "plugin_name": self.plugin.name,
                "plugin_kind": self.plugin.kind.value,
                "operation": self.operation_name
            }
            self.duration_metric.record(duration, labels)
        
        # Log duration
        if self.enable_logging:
            self._logger.debug(
                f"Plugin {self.operation_name} for {self.plugin.name} took {duration:.3f}s"
            )
        
        # Finish tracing span
        if self.span:
            if exc_type is not None:
                self.span.set_status(
                    Status(StatusCode.ERROR, f"{exc_type.__name__}: {exc_val}")
                )
            else:
                self.span.set_status(Status(StatusCode.OK))
            
            self.span.set_attribute("operation.duration_seconds", duration)
            self.span.end()


class LoggingObservabilityCollector:
    """Simple logging-based observability collector."""
    
    def __init__(self, logger_name: str = "dotmac.plugins.observability"):
        self.logger = logging.getLogger(logger_name)
    
    def record_event(self, event_type: str, plugin_name: str, data: Dict[str, Any]) -> None:
        """Record plugin event to logs."""
        self.logger.info(f"Plugin event: {event_type} - {plugin_name}", extra=data)
    
    def record_metric(self, metric_name: str, value: float, labels: Dict[str, str]) -> None:
        """Record plugin metric to logs."""
        self.logger.info(f"Plugin metric: {metric_name} = {value}", extra=labels)
    
    def record_error(self, plugin_name: str, error: Exception, context: Dict[str, Any]) -> None:
        """Record plugin error to logs."""
        self.logger.error(
            f"Plugin error in {plugin_name}: {error}", 
            exc_info=error,
            extra=context
        )


class MetricsCollector:
    """Metrics collection for plugin system."""
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._gauges: Dict[str, float] = {}
    
    def increment_counter(self, name: str, labels: Dict[str, str] = None) -> None:
        """Increment counter metric."""
        key = self._make_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + 1
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Record histogram value."""
        key = self._make_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Set gauge value."""
        key = self._make_key(name, labels)
        self._gauges[key] = value
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create metric key from name and labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_counters(self) -> Dict[str, int]:
        """Get all counter values."""
        return self._counters.copy()
    
    def get_histograms(self) -> Dict[str, List[float]]:
        """Get all histogram values."""
        return {k: v.copy() for k, v in self._histograms.items()}
    
    def get_gauges(self) -> Dict[str, float]:
        """Get all gauge values."""
        return self._gauges.copy()
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._histograms.clear()
        self._gauges.clear()