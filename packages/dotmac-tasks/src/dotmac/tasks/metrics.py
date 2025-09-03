"""
Metrics hooks for observability integration.

Provides no-op hooks by default that can be wired to observability
systems like dotmac.observability or external metrics collectors.
"""

import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class MetricsHooks:
    """
    Metrics hooks for recording background operations events.
    
    By default, these are no-op functions. Applications can replace
    these with actual metrics collection implementations.
    """

    def __init__(self) -> None:
        """Initialize metrics hooks."""
        self.record_operation_enqueued: Callable[[str, str, Dict[str, Any]], None] = self._noop_hook
        self.record_operation_completed: Callable[[str, str, bool, Optional[str]], None] = self._noop_hook
        self.record_operation_duration: Callable[[str, str, float], None] = self._noop_hook
        self.record_saga_created: Callable[[str, str, int], None] = self._noop_hook
        self.record_saga_status_change: Callable[[str, str, str], None] = self._noop_hook
        self.record_saga_step_executed: Callable[[str, str, str, bool, int], None] = self._noop_hook
        self.record_idempotency_hit: Callable[[str, str], None] = self._noop_hook
        self.record_idempotency_miss: Callable[[str, str], None] = self._noop_hook
        self.record_storage_operation: Callable[[str, str, float], None] = self._noop_hook
        self.record_lock_acquired: Callable[[str, float], None] = self._noop_hook
        self.record_lock_failed: Callable[[str], None] = self._noop_hook
        
    def _noop_hook(self, *args, **kwargs) -> None:
        """No-op hook that does nothing."""
        pass

    def enable_logging_metrics(self, log_level: int = logging.INFO) -> None:
        """
        Enable simple logging-based metrics.
        
        Args:
            log_level: Logging level for metrics
        """
        def log_operation_enqueued(tenant_id: str, operation_type: str, metadata: Dict[str, Any]) -> None:
            logger.log(log_level, f"Operation enqueued: {operation_type} for tenant {tenant_id}")

        def log_operation_completed(tenant_id: str, operation_type: str, success: bool, error: Optional[str]) -> None:
            status = "success" if success else f"failed ({error})"
            logger.log(log_level, f"Operation completed: {operation_type} for tenant {tenant_id} - {status}")

        def log_operation_duration(tenant_id: str, operation_type: str, duration_seconds: float) -> None:
            logger.log(log_level, f"Operation duration: {operation_type} for tenant {tenant_id} took {duration_seconds:.3f}s")

        def log_saga_created(tenant_id: str, workflow_type: str, step_count: int) -> None:
            logger.log(log_level, f"Saga created: {workflow_type} for tenant {tenant_id} with {step_count} steps")

        def log_saga_status_change(tenant_id: str, saga_id: str, new_status: str) -> None:
            logger.log(log_level, f"Saga status change: {saga_id} for tenant {tenant_id} -> {new_status}")

        def log_saga_step_executed(tenant_id: str, saga_id: str, step_name: str, success: bool, retry_count: int) -> None:
            status = "success" if success else "failed"
            retry_info = f" (retry {retry_count})" if retry_count > 0 else ""
            logger.log(log_level, f"Saga step: {step_name} in {saga_id} for tenant {tenant_id} - {status}{retry_info}")

        def log_idempotency_hit(tenant_id: str, operation_type: str) -> None:
            logger.log(log_level, f"Idempotency hit: {operation_type} for tenant {tenant_id}")

        def log_idempotency_miss(tenant_id: str, operation_type: str) -> None:
            logger.log(log_level, f"Idempotency miss: {operation_type} for tenant {tenant_id}")

        def log_storage_operation(operation: str, backend: str, duration_seconds: float) -> None:
            logger.log(log_level, f"Storage {operation} on {backend} took {duration_seconds:.3f}s")

        def log_lock_acquired(lock_key: str, duration_seconds: float) -> None:
            logger.log(log_level, f"Lock acquired: {lock_key} (took {duration_seconds:.3f}s)")

        def log_lock_failed(lock_key: str) -> None:
            logger.log(log_level, f"Lock acquisition failed: {lock_key}")

        # Replace hooks
        self.record_operation_enqueued = log_operation_enqueued
        self.record_operation_completed = log_operation_completed
        self.record_operation_duration = log_operation_duration
        self.record_saga_created = log_saga_created
        self.record_saga_status_change = log_saga_status_change
        self.record_saga_step_executed = log_saga_step_executed
        self.record_idempotency_hit = log_idempotency_hit
        self.record_idempotency_miss = log_idempotency_miss
        self.record_storage_operation = log_storage_operation
        self.record_lock_acquired = log_lock_acquired
        self.record_lock_failed = log_lock_failed

        logger.info("Enabled logging-based metrics")


# Global metrics instance
_metrics_hooks = MetricsHooks()


def get_metrics_hooks() -> MetricsHooks:
    """Get the global metrics hooks instance."""
    return _metrics_hooks


def configure_metrics_hooks(hooks: MetricsHooks) -> None:
    """
    Configure custom metrics hooks.
    
    Args:
        hooks: MetricsHooks instance with configured callbacks
    """
    global _metrics_hooks
    _metrics_hooks = hooks
    logger.info("Configured custom metrics hooks")


# Convenience functions for recording metrics

def record_operation_enqueued(tenant_id: str, operation_type: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Record that an operation was enqueued."""
    _metrics_hooks.record_operation_enqueued(tenant_id, operation_type, metadata or {})


def record_operation_completed(tenant_id: str, operation_type: str, success: bool, error: Optional[str] = None) -> None:
    """Record that an operation was completed."""
    _metrics_hooks.record_operation_completed(tenant_id, operation_type, success, error)


def record_operation_duration(tenant_id: str, operation_type: str, duration_seconds: float) -> None:
    """Record operation execution duration."""
    _metrics_hooks.record_operation_duration(tenant_id, operation_type, duration_seconds)


def record_saga_created(tenant_id: str, workflow_type: str, step_count: int) -> None:
    """Record that a saga workflow was created."""
    _metrics_hooks.record_saga_created(tenant_id, workflow_type, step_count)


def record_saga_status_change(tenant_id: str, saga_id: str, new_status: str) -> None:
    """Record saga status change."""
    _metrics_hooks.record_saga_status_change(tenant_id, saga_id, new_status)


def record_saga_step_executed(tenant_id: str, saga_id: str, step_name: str, success: bool, retry_count: int = 0) -> None:
    """Record saga step execution."""
    _metrics_hooks.record_saga_step_executed(tenant_id, saga_id, step_name, success, retry_count)


def record_idempotency_hit(tenant_id: str, operation_type: str) -> None:
    """Record idempotency cache hit."""
    _metrics_hooks.record_idempotency_hit(tenant_id, operation_type)


def record_idempotency_miss(tenant_id: str, operation_type: str) -> None:
    """Record idempotency cache miss."""
    _metrics_hooks.record_idempotency_miss(tenant_id, operation_type)


def record_storage_operation(operation: str, backend: str, duration_seconds: float) -> None:
    """Record storage operation performance."""
    _metrics_hooks.record_storage_operation(operation, backend, duration_seconds)


def record_lock_acquired(lock_key: str, duration_seconds: float) -> None:
    """Record successful lock acquisition."""
    _metrics_hooks.record_lock_acquired(lock_key, duration_seconds)


def record_lock_failed(lock_key: str) -> None:
    """Record failed lock acquisition."""
    _metrics_hooks.record_lock_failed(lock_key)


# Integration helpers

def setup_dotmac_observability_integration() -> None:
    """
    Set up integration with dotmac.observability package.
    
    This function attempts to import and configure dotmac.observability
    metrics. If the package is not available, it falls back to no-op hooks.
    """
    try:
        # Try to import dotmac.observability
        from dotmac.observability import get_tenant_metrics, record_counter, record_histogram
        
        def observability_operation_enqueued(tenant_id: str, operation_type: str, metadata: Dict[str, Any]) -> None:
            metrics = get_tenant_metrics(tenant_id)
            metrics.record_counter("background_operations_enqueued", 1, {
                "operation_type": operation_type,
                **metadata
            })

        def observability_operation_completed(tenant_id: str, operation_type: str, success: bool, error: Optional[str]) -> None:
            metrics = get_tenant_metrics(tenant_id)
            metrics.record_counter("background_operations_completed", 1, {
                "operation_type": operation_type,
                "success": str(success).lower(),
                "error_type": error or "none"
            })

        def observability_operation_duration(tenant_id: str, operation_type: str, duration_seconds: float) -> None:
            metrics = get_tenant_metrics(tenant_id)
            metrics.record_histogram("background_operation_duration_seconds", duration_seconds, {
                "operation_type": operation_type
            })

        def observability_saga_created(tenant_id: str, workflow_type: str, step_count: int) -> None:
            metrics = get_tenant_metrics(tenant_id)
            metrics.record_counter("sagas_created", 1, {
                "workflow_type": workflow_type
            })
            metrics.record_histogram("saga_step_count", step_count, {
                "workflow_type": workflow_type
            })

        def observability_saga_status_change(tenant_id: str, saga_id: str, new_status: str) -> None:
            metrics = get_tenant_metrics(tenant_id)
            metrics.record_counter("saga_status_changes", 1, {
                "status": new_status
            })

        def observability_idempotency_hit(tenant_id: str, operation_type: str) -> None:
            metrics = get_tenant_metrics(tenant_id)
            metrics.record_counter("idempotency_cache_hits", 1, {
                "operation_type": operation_type
            })

        def observability_idempotency_miss(tenant_id: str, operation_type: str) -> None:
            metrics = get_tenant_metrics(tenant_id)
            metrics.record_counter("idempotency_cache_misses", 1, {
                "operation_type": operation_type
            })

        # Configure hooks
        hooks = MetricsHooks()
        hooks.record_operation_enqueued = observability_operation_enqueued
        hooks.record_operation_completed = observability_operation_completed
        hooks.record_operation_duration = observability_operation_duration
        hooks.record_saga_created = observability_saga_created
        hooks.record_saga_status_change = observability_saga_status_change
        hooks.record_idempotency_hit = observability_idempotency_hit
        hooks.record_idempotency_miss = observability_idempotency_miss

        configure_metrics_hooks(hooks)
        logger.info("Configured dotmac.observability metrics integration")

    except ImportError:
        logger.warning("dotmac.observability not available, using no-op metrics hooks")
        # Keep default no-op hooks


# Auto-configure on import if observability is available
try:
    setup_dotmac_observability_integration()
except Exception as e:
    logger.debug(f"Could not auto-configure observability integration: {e}")
    pass