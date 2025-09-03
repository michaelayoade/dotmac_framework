"""
Observability hooks for secrets management
Provides metrics, logging, and monitoring integration
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from .interfaces import ObservabilityHook
from .types import SecretKind

logger = logging.getLogger(__name__)

# Try to import OpenTelemetry for optional metrics support
try:
    from opentelemetry import metrics
    from opentelemetry.metrics import Counter, Histogram, get_meter
    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False
    metrics = None


class LoggingObservabilityHook:
    """
    Simple observability hook that logs metrics and events
    Useful for development and debugging
    """
    
    def __init__(self, log_level: int = logging.INFO) -> None:
        """
        Initialize logging hook
        
        Args:
            log_level: Logging level for metrics
        """
        self.log_level = log_level
        self.logger = logging.getLogger(f"{__name__}.metrics")
        self.stats = {
            "secret_fetches": {"success": 0, "failure": 0},
            "validation_failures": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "provider_errors": 0,
        }
    
    def record_secret_fetch(
        self,
        kind: SecretKind,
        source: str,
        success: bool,
        latency_ms: float,
        path: str = ""
    ) -> None:
        """Record secret fetch metrics"""
        status = "success" if success else "failure"
        self.stats["secret_fetches"][status] += 1
        
        self.logger.log(
            self.log_level,
            f"Secret fetch: {kind.value} from {source} - {status} "
            f"({latency_ms:.2f}ms) path={path}"
        )
    
    def record_validation_failure(
        self,
        kind: SecretKind,
        reason: str,
        path: str = ""
    ) -> None:
        """Record validation failure"""
        self.stats["validation_failures"] += 1
        
        self.logger.warning(
            f"Secret validation failed: {kind.value} - {reason} path={path}"
        )
    
    def record_cache_hit(self, path: str) -> None:
        """Record cache hit"""
        self.stats["cache_hits"] += 1
        
        self.logger.log(
            self.log_level,
            f"Cache hit: {path}"
        )
    
    def record_cache_miss(self, path: str) -> None:
        """Record cache miss"""
        self.stats["cache_misses"] += 1
        
        self.logger.log(
            self.log_level,
            f"Cache miss: {path}"
        )
    
    def record_provider_error(
        self,
        provider_type: str,
        error_type: str,
        path: str = ""
    ) -> None:
        """Record provider error"""
        self.stats["provider_errors"] += 1
        
        self.logger.error(
            f"Provider error: {provider_type} - {error_type} path={path}"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get accumulated statistics"""
        return self.stats.copy()


class OpenTelemetryObservabilityHook:
    """
    OpenTelemetry-based observability hook
    Provides structured metrics for monitoring systems
    """
    
    def __init__(self, meter_name: str = "dotmac.secrets") -> None:
        """
        Initialize OpenTelemetry hook
        
        Args:
            meter_name: Name for the OpenTelemetry meter
        """
        if not HAS_OTEL:
            raise ImportError("OpenTelemetry not available. Install with: pip install opentelemetry-api")
        
        self.meter = get_meter(meter_name)
        
        # Create metrics instruments
        self.secret_fetch_counter = self.meter.create_counter(
            name="secrets_fetched_total",
            description="Total number of secret fetches",
            unit="1"
        )
        
        self.secret_fetch_duration = self.meter.create_histogram(
            name="secret_fetch_duration_ms",
            description="Duration of secret fetch operations",
            unit="ms"
        )
        
        self.validation_failure_counter = self.meter.create_counter(
            name="secret_validation_failures_total",
            description="Total number of secret validation failures",
            unit="1"
        )
        
        self.cache_hit_counter = self.meter.create_counter(
            name="secret_cache_hits_total",
            description="Total number of cache hits",
            unit="1"
        )
        
        self.cache_miss_counter = self.meter.create_counter(
            name="secret_cache_misses_total",
            description="Total number of cache misses",
            unit="1"
        )
        
        self.provider_error_counter = self.meter.create_counter(
            name="secret_provider_errors_total",
            description="Total number of provider errors",
            unit="1"
        )
    
    def record_secret_fetch(
        self,
        kind: SecretKind,
        source: str,
        success: bool,
        latency_ms: float,
        path: str = ""
    ) -> None:
        """Record secret fetch metrics"""
        attributes = {
            "secret_kind": kind.value,
            "source": source,
            "success": str(success).lower(),
        }
        
        # Add path as attribute (but be careful about cardinality)
        if path:
            # Extract path prefix to reduce cardinality
            path_parts = path.split('/')
            if len(path_parts) >= 2:
                attributes["path_prefix"] = f"{path_parts[0]}/{path_parts[1]}"
        
        self.secret_fetch_counter.add(1, attributes)
        self.secret_fetch_duration.record(latency_ms, attributes)
    
    def record_validation_failure(
        self,
        kind: SecretKind,
        reason: str,
        path: str = ""
    ) -> None:
        """Record validation failure"""
        attributes = {
            "secret_kind": kind.value,
            "reason": reason[:100],  # Truncate to avoid high cardinality
        }
        
        self.validation_failure_counter.add(1, attributes)
    
    def record_cache_hit(self, path: str) -> None:
        """Record cache hit"""
        attributes = {}
        
        # Add path prefix to reduce cardinality
        if path:
            path_parts = path.split('/')
            if len(path_parts) >= 2:
                attributes["path_prefix"] = f"{path_parts[0]}/{path_parts[1]}"
        
        self.cache_hit_counter.add(1, attributes)
    
    def record_cache_miss(self, path: str) -> None:
        """Record cache miss"""
        attributes = {}
        
        # Add path prefix to reduce cardinality
        if path:
            path_parts = path.split('/')
            if len(path_parts) >= 2:
                attributes["path_prefix"] = f"{path_parts[0]}/{path_parts[1]}"
        
        self.cache_miss_counter.add(1, attributes)
    
    def record_provider_error(
        self,
        provider_type: str,
        error_type: str,
        path: str = ""
    ) -> None:
        """Record provider error"""
        attributes = {
            "provider_type": provider_type,
            "error_type": error_type,
        }
        
        self.provider_error_counter.add(1, attributes)


class CompositeObservabilityHook:
    """
    Composite hook that delegates to multiple observability hooks
    Allows combining logging, metrics, and other observability systems
    """
    
    def __init__(self, hooks: list[ObservabilityHook]) -> None:
        """
        Initialize composite hook
        
        Args:
            hooks: List of observability hooks to delegate to
        """
        self.hooks = hooks
    
    def record_secret_fetch(
        self,
        kind: SecretKind,
        source: str,
        success: bool,
        latency_ms: float,
        path: str = ""
    ) -> None:
        """Record secret fetch metrics in all hooks"""
        for hook in self.hooks:
            try:
                hook.record_secret_fetch(kind, source, success, latency_ms, path)
            except Exception as e:
                logger.warning(f"Observability hook failed: {e}")
    
    def record_validation_failure(
        self,
        kind: SecretKind,
        reason: str,
        path: str = ""
    ) -> None:
        """Record validation failure in all hooks"""
        for hook in self.hooks:
            try:
                hook.record_validation_failure(kind, reason, path)
            except Exception as e:
                logger.warning(f"Observability hook failed: {e}")
    
    def record_cache_hit(self, path: str) -> None:
        """Record cache hit in all hooks"""
        for hook in self.hooks:
            try:
                hook.record_cache_hit(path)
            except Exception as e:
                logger.warning(f"Observability hook failed: {e}")
    
    def record_cache_miss(self, path: str) -> None:
        """Record cache miss in all hooks"""
        for hook in self.hooks:
            try:
                hook.record_cache_miss(path)
            except Exception as e:
                logger.warning(f"Observability hook failed: {e}")
    
    def record_provider_error(
        self,
        provider_type: str,
        error_type: str,
        path: str = ""
    ) -> None:
        """Record provider error in all hooks"""
        for hook in self.hooks:
            try:
                hook.record_provider_error(provider_type, error_type, path)
            except Exception as e:
                logger.warning(f"Observability hook failed: {e}")


class NullObservabilityHook:
    """
    Null observability hook that does nothing
    Useful for disabling observability in certain environments
    """
    
    def record_secret_fetch(
        self,
        kind: SecretKind,
        source: str,
        success: bool,
        latency_ms: float,
        path: str = ""
    ) -> None:
        """No-op"""
        pass
    
    def record_validation_failure(
        self,
        kind: SecretKind,
        reason: str,
        path: str = ""
    ) -> None:
        """No-op"""
        pass
    
    def record_cache_hit(self, path: str) -> None:
        """No-op"""
        pass
    
    def record_cache_miss(self, path: str) -> None:
        """No-op"""
        pass
    
    def record_provider_error(
        self,
        provider_type: str,
        error_type: str,
        path: str = ""
    ) -> None:
        """No-op"""
        pass


def create_observability_hook(
    hook_type: str = "logging",
    **config: Any
) -> ObservabilityHook:
    """
    Factory function to create observability hooks
    
    Args:
        hook_type: Type of hook ("logging", "otel", "null", "composite")
        **config: Configuration parameters for the hook
        
    Returns:
        Observability hook instance
        
    Raises:
        ValueError: If hook type is not supported
    """
    if hook_type == "logging":
        log_level = config.get("log_level", logging.INFO)
        return LoggingObservabilityHook(log_level)
    
    elif hook_type == "otel":
        meter_name = config.get("meter_name", "dotmac.secrets")
        return OpenTelemetryObservabilityHook(meter_name)
    
    elif hook_type == "null":
        return NullObservabilityHook()
    
    elif hook_type == "composite":
        hooks = config.get("hooks", [])
        return CompositeObservabilityHook(hooks)
    
    else:
        raise ValueError(f"Unsupported observability hook type: {hook_type}")


# Register hook classes with ObservabilityHook protocol
ObservabilityHook.register(LoggingObservabilityHook)
if HAS_OTEL:
    ObservabilityHook.register(OpenTelemetryObservabilityHook)
ObservabilityHook.register(CompositeObservabilityHook)
ObservabilityHook.register(NullObservabilityHook)