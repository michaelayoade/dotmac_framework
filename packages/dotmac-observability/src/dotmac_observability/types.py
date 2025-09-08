"""Type definitions for dotmac-observability."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Protocol, runtime_checkable


class MetricType(str, Enum):
    """Types of metrics that can be collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: HealthStatus
    duration_ms: float
    error: Optional[str] = None
    message: Optional[str] = None
    required: bool = True
    timestamp: Optional[datetime] = None

    def is_healthy(self) -> bool:
        """Check if this result represents a healthy state."""
        return self.status == HealthStatus.HEALTHY


@dataclass
class MetricEntry:
    """A single metric entry."""

    name: str
    type: MetricType
    value: float
    tags: Optional[dict[str, str]] = None
    timestamp: Optional[datetime] = None


@runtime_checkable
class HealthCheck(Protocol):
    """Protocol for health check functions."""

    def __call__(self) -> bool:
        """Execute the health check and return True if healthy."""
        ...


@runtime_checkable
class AsyncHealthCheck(Protocol):
    """Protocol for async health check functions."""

    async def __call__(self) -> bool:
        """Execute the health check and return True if healthy."""
        ...


# Type aliases for common use cases
Tags = Optional[dict[str, str]]
HealthCheckFunction = Callable[[], bool]
AsyncHealthCheckFunction = Callable[[], Any]  # Awaitable[bool]
