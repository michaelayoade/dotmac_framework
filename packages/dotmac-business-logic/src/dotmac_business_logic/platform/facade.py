"""
Platform integration facade for business logic.

Provides unified interface for platform services with graceful fallbacks
when optional platform dependencies are not available.
"""

import logging
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


class IntegrationManagerProtocol(Protocol):
    """Protocol for platform integration manager."""

    def record_metric(self, name: str, value: float, tags: dict[str, Any]) -> None:
        """Record a metric with tags."""
        ...

    def send_notification(self, event: str, data: dict[str, Any]) -> None:
        """Send notification for an event."""
        ...


class BenchmarkManagerProtocol(Protocol):
    """Protocol for benchmark manager."""

    def start_benchmark(self, name: str) -> str:
        """Start a benchmark and return benchmark ID."""
        ...

    def end_benchmark(self, benchmark_id: str, metadata: dict[str, Any] = None) -> None:
        """End a benchmark with optional metadata."""
        ...


class PlatformFacade:
    """
    Unified facade for platform integrations.

    Provides graceful fallbacks when platform components are not available,
    ensuring business logic can operate independently.
    """

    def __init__(self) -> None:
        """Initialize platform facade with graceful component discovery."""
        self._integration_manager: Optional[IntegrationManagerProtocol] = None
        self._benchmark_manager: Optional[BenchmarkManagerProtocol] = None
        self._initialize_integrations()

    def _initialize_integrations(self) -> None:
        """Initialize platform integrations with graceful fallback."""
        # Try to initialize integration manager
        try:
            from dotmac.platform.monitoring.integrations import IntegrationManager

            self._integration_manager = IntegrationManager()
            logger.debug("Platform integration manager initialized")
        except ImportError:
            logger.debug("Platform integration manager not available")

        # Try to initialize benchmark manager
        try:
            from dotmac.platform.monitoring.benchmarks import BenchmarkManager

            self._benchmark_manager = BenchmarkManager()
            logger.debug("Platform benchmark manager initialized")
        except ImportError:
            logger.debug("Platform benchmark manager not available")

    def record_metric(
        self, name: str, value: float, tags: dict[str, Any] = None
    ) -> None:
        """Record metric with fallback to logging."""
        if self._integration_manager:
            self._integration_manager.record_metric(name, value, tags or {})
        else:
            logger.info(f"Metric: {name}={value} tags={tags or {}}")

    def send_notification(self, event: str, data: dict[str, Any]) -> None:
        """Send notification with fallback to logging."""
        if self._integration_manager:
            self._integration_manager.send_notification(event, data)
        else:
            logger.info(f"Event: {event} data={data}")

    def start_benchmark(self, name: str) -> str:
        """Start benchmark with fallback to no-op."""
        if self._benchmark_manager:
            return self._benchmark_manager.start_benchmark(name)
        else:
            logger.debug(f"Benchmark started: {name} (no-op)")
            return f"noop-{name}"

    def end_benchmark(self, benchmark_id: str, metadata: dict[str, Any] = None) -> None:
        """End benchmark with fallback to no-op."""
        if self._benchmark_manager:
            self._benchmark_manager.end_benchmark(benchmark_id, metadata)
        else:
            logger.debug(f"Benchmark ended: {benchmark_id} metadata={metadata} (no-op)")

    @property
    def has_integration_manager(self) -> bool:
        """Check if integration manager is available."""
        return self._integration_manager is not None

    @property
    def has_benchmark_manager(self) -> bool:
        """Check if benchmark manager is available."""
        return self._benchmark_manager is not None


# Global instance for package-wide use
_platform_facade: Optional[PlatformFacade] = None


def get_platform_facade() -> PlatformFacade:
    """Get or create global platform facade instance."""
    global _platform_facade
    if _platform_facade is None:
        _platform_facade = PlatformFacade()
    return _platform_facade
