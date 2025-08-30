"""
Standardized error handling for application startup sequences.

Provides consistent error handling, retry logic, and failure recovery
across all platform services.
"""

import asyncio
import logging
import os
import sys
import traceback
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class StartupPhase(Enum):
    """Startup phases for error categorization."""

    INITIALIZATION = "initialization"
    DATABASE = "database"
    CACHE = "cache"
    OBSERVABILITY = "observability"
    SECURITY = "security"
    ROUTING = "routing"
    MIDDLEWARE = "middleware"
    BACKGROUND_TASKS = "background_tasks"
    CLEANUP = "cleanup"


class StartupErrorSeverity(Enum):
    """Error severity levels for startup failures."""

    CRITICAL = "critical"  # Cannot continue, immediate shutdown
    HIGH = "high"  # Major feature unavailable, continue with degraded mode
    MEDIUM = "medium"  # Non-critical feature unavailable, log and continue
    LOW = "low"  # Minor issue, log warning and continue


@dataclass
class StartupError:
    """Represents a startup error with context."""

    phase: StartupPhase
    severity: StartupErrorSeverity
    error: Exception
    message: str
    component: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "phase": self.phase.value,
            "severity": self.severity.value,
            "error_type": type(self.error).__name__,
            "message": self.message,
            "component": self.component,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "traceback": traceback.format_exception(
                type(self.error), self.error, self.error.__traceback__
            ),
        }


@dataclass
class StartupResult:
    """Result of a startup operation."""

    success: bool
    errors: List[StartupError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_critical_errors(self) -> bool:
        """Check if any critical errors occurred."""
        return any(
            error.severity == StartupErrorSeverity.CRITICAL for error in self.errors
        )

    @property
    def has_high_severity_errors(self) -> bool:
        """Check if any high severity errors occurred."""
        return any(
            error.severity in [StartupErrorSeverity.CRITICAL, StartupErrorSeverity.HIGH]
            for error in self.errors
        )


class StartupManager:
    """Manages standardized startup sequences with error handling."""

    def __init__(self, service_name: str, environment: str = None):
        """Initialize startup manager."""
        self.service_name = service_name
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.startup_errors: List[StartupError] = []
        self.startup_warnings: List[str] = []
        self.startup_metadata: Dict[str, Any] = {}
        self.shutdown_callbacks: List[Callable] = []
        self._logger = logging.getLogger(f"{__name__}.{service_name}")

    def register_shutdown_callback(self, callback: Callable) -> None:
        """Register callback to run during shutdown."""
        self.shutdown_callbacks.append(callback)

    def add_warning(self, message: str) -> None:
        """Add a startup warning."""
        self.startup_warnings.append(message)
        self._logger.warning(f"Startup warning: {message}")

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata about startup process."""
        self.startup_metadata[key] = value

    async def execute_with_retry(
        self,
        operation: Callable,
        phase: StartupPhase,
        component: str,
        severity: StartupErrorSeverity = StartupErrorSeverity.HIGH,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs,
    ) -> StartupResult:
        """Execute an operation with retry logic and error handling."""
        startup_error = None

        for attempt in range(max_retries + 1):
            try:
                result = (
                    await operation(**kwargs)
                    if asyncio.iscoroutinefunction(operation)
                    else operation(**kwargs)
                )

                if startup_error and attempt > 0:
                    self._logger.info(
                        f"✅ {component} recovered after {attempt} attempts"
                    )

                return StartupResult(
                    success=True, metadata={"attempts": attempt + 1, "result": result}
                )

            except Exception as e:
                startup_error = StartupError(
                    phase=phase,
                    severity=severity,
                    error=e,
                    message=f"Failed to initialize {component}: {str(e)}",
                    component=component,
                    retry_count=attempt,
                    max_retries=max_retries,
                )

                if attempt < max_retries:
                    self._logger.warning(
                        f"⚠️  {component} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                else:
                    self._logger.error(
                        f"❌ {component} failed after {max_retries + 1} attempts: {e}"
                    )

        # All attempts failed
        self.startup_errors.append(startup_error)

        return StartupResult(
            success=False,
            errors=[startup_error],
            metadata={"attempts": max_retries + 1},
        )

    def startup_step(
        self,
        phase: StartupPhase,
        component: str,
        severity: StartupErrorSeverity = StartupErrorSeverity.HIGH,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Decorator for startup steps with standardized error handling."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await self.execute_with_retry(
                    operation=func,
                    phase=phase,
                    component=component,
                    severity=severity,
                    max_retries=max_retries,
                    retry_delay=retry_delay,
                    *args,
                    **kwargs,
                )

            return wrapper

        return decorator

    def log_startup_summary(self) -> None:
        """Log comprehensive startup summary."""
        total_errors = len(self.startup_errors)
        critical_errors = sum(
            1
            for e in self.startup_errors
            if e.severity == StartupErrorSeverity.CRITICAL
        )
        high_errors = sum(
            1 for e in self.startup_errors if e.severity == StartupErrorSeverity.HIGH
        )

        self._logger.info("=" * 60)
        self._logger.info(f"🚀 {self.service_name} Startup Summary")
        self._logger.info("=" * 60)

        if total_errors == 0:
            self._logger.info("✅ All startup components initialized successfully")
        else:
            self._logger.error(f"❌ {total_errors} startup errors occurred:")
            self._logger.error(f"   - Critical: {critical_errors}")
            self._logger.error(f"   - High: {high_errors}")

            for error in self.startup_errors:
                self._logger.error(f"   • {error.component}: {error.message}")

        if self.startup_warnings:
            self._logger.warning(f"⚠️  {len(self.startup_warnings)} warnings:")
            for warning in self.startup_warnings:
                self._logger.warning(f"   • {warning}")

        if self.startup_metadata:
            self._logger.info("📊 Startup metadata:")
            for key, value in self.startup_metadata.items():
                self._logger.info(f"   • {key}: {value}")

        self._logger.info("=" * 60)

    def should_continue_startup(self) -> bool:
        """Determine if startup should continue based on errors."""
        # Critical errors always stop startup
        if any(
            e.severity == StartupErrorSeverity.CRITICAL for e in self.startup_errors
        ):
            return False

        # In production, high severity errors might stop startup
        if self.environment == "production":
            high_severity_count = sum(
                1
                for e in self.startup_errors
                if e.severity == StartupErrorSeverity.HIGH
            )
            # Allow up to 2 high severity errors in production
            return high_severity_count <= 2

        # In development, continue unless critical
        return True

    async def graceful_shutdown(self, app=None) -> None:
        """Perform graceful shutdown with cleanup."""
        self._logger.info(f"🛑 Starting graceful shutdown of {self.service_name}...")

        # Run shutdown callbacks in reverse order
        for callback in reversed(self.shutdown_callbacks):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
                self._logger.info(
                    f"✅ Shutdown callback completed: {callback.__name__}"
                )
            except Exception as e:
                self._logger.error(
                    f"❌ Shutdown callback failed: {callback.__name__}: {e}"
                )

        self._logger.info(f"✅ Graceful shutdown of {self.service_name} completed")


def create_startup_manager(
    service_name: str, environment: str = None
) -> StartupManager:
    """Factory function to create a startup manager."""
    return StartupManager(service_name, environment)


@asynccontextmanager
async def managed_startup(
    service_name: str,
    startup_manager: StartupManager = None,
    fail_on_critical: bool = True,
    fail_on_high_severity: bool = False,
):
    """Context manager for managed startup/shutdown."""
    if startup_manager is None:
        startup_manager = create_startup_manager(service_name)

    try:
        yield startup_manager

        # Check if we should continue based on startup errors
        if fail_on_critical and any(
            e.severity == StartupErrorSeverity.CRITICAL
            for e in startup_manager.startup_errors
        ):
            raise RuntimeError("Critical startup errors occurred, cannot continue")

        if fail_on_high_severity and startup_manager.has_high_severity_errors:
            raise RuntimeError("High severity startup errors occurred, cannot continue")

    except Exception as e:
        logger.error(f"Fatal error during {service_name} startup: {e}")
        raise
    finally:
        startup_manager.log_startup_summary()
        await startup_manager.graceful_shutdown()


# Convenience functions for common startup patterns


async def initialize_database_with_retry(
    init_func: Callable, startup_manager: StartupManager, max_retries: int = 5
) -> StartupResult:
    """Initialize database with retry logic."""
    return await startup_manager.execute_with_retry(
        operation=init_func,
        phase=StartupPhase.DATABASE,
        component="Database Connection",
        severity=StartupErrorSeverity.CRITICAL,
        max_retries=max_retries,
        retry_delay=2.0,
    )


async def initialize_cache_with_retry(
    init_func: Callable, startup_manager: StartupManager, max_retries: int = 3
) -> StartupResult:
    """Initialize cache with retry logic."""
    return await startup_manager.execute_with_retry(
        operation=init_func,
        phase=StartupPhase.CACHE,
        component="Cache Connection",
        severity=StartupErrorSeverity.HIGH,
        max_retries=max_retries,
        retry_delay=1.0,
    )


async def initialize_observability_with_retry(
    init_func: Callable, startup_manager: StartupManager, max_retries: int = 2
) -> StartupResult:
    """Initialize observability with retry logic."""
    return await startup_manager.execute_with_retry(
        operation=init_func,
        phase=StartupPhase.OBSERVABILITY,
        component="Observability System",
        severity=StartupErrorSeverity.MEDIUM,
        max_retries=max_retries,
        retry_delay=1.0,
    )
