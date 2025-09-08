"""Health check system for task processing."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = aioredis = None


class HealthStatus(Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Individual health check result."""

    name: str
    status: HealthStatus
    message: str
    details: dict[str, Any] | None = None
    timestamp: str | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class HealthChecker:
    """Comprehensive health checker for task processing system."""

    def __init__(
        self,
        redis_queue=None,
        task_runner=None,
        redis_client=None,
        thresholds: dict[str, Any] | None = None
    ):
        self.redis_queue = redis_queue
        self.task_runner = task_runner
        self.redis_client = redis_client

        # Default thresholds
        default_thresholds = {
            "queue_depth_warning": 1000,
            "queue_depth_critical": 10000,
            "utilization_warning": 0.8,
            "utilization_critical": 0.95,
            "redis_response_time_warning": 100,  # ms
            "redis_response_time_critical": 1000,  # ms
        }
        self.thresholds = {**default_thresholds, **(thresholds or {})}

    async def check_redis_connectivity(self) -> HealthCheck:
        """Check Redis server connectivity and response time."""
        if not REDIS_AVAILABLE:
            return HealthCheck(
                "redis_connectivity",
                HealthStatus.UNHEALTHY,
                "Redis library not available"
            )

        if not (self.redis_client or self.redis_queue):
            return HealthCheck(
                "redis_connectivity",
                HealthStatus.UNHEALTHY,
                "No Redis client or queue configured"
            )

        try:
            # Get Redis client
            if self.redis_client:
                client = self.redis_client
            else:
                client = await self.redis_queue._get_redis()

            # Measure response time
            start_time = asyncio.get_event_loop().time()
            await client.ping()
            response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Determine status based on response time
            if response_time_ms > self.thresholds["redis_response_time_critical"]:
                status = HealthStatus.UNHEALTHY
                message = f"Redis response time critical: {response_time_ms:.1f}ms"
            elif response_time_ms > self.thresholds["redis_response_time_warning"]:
                status = HealthStatus.DEGRADED
                message = f"Redis response time high: {response_time_ms:.1f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = f"Redis responding normally: {response_time_ms:.1f}ms"

            return HealthCheck(
                "redis_connectivity",
                status,
                message,
                {"response_time_ms": response_time_ms}
            )

        except Exception as e:
            return HealthCheck(
                "redis_connectivity",
                HealthStatus.UNHEALTHY,
                f"Redis connection failed: {e!s}"
            )

    async def check_queue_depth(self) -> HealthCheck:
        """Check task queue depth."""
        if not self.redis_queue:
            return HealthCheck(
                "queue_depth",
                HealthStatus.HEALTHY,
                "No queue configured"
            )

        try:
            depth = self.redis_queue.get_queue_size()

            if depth > self.thresholds["queue_depth_critical"]:
                status = HealthStatus.UNHEALTHY
                message = f"Queue depth critical: {depth} tasks"
            elif depth > self.thresholds["queue_depth_warning"]:
                status = HealthStatus.DEGRADED
                message = f"Queue depth high: {depth} tasks"
            else:
                status = HealthStatus.HEALTHY
                message = f"Queue depth normal: {depth} tasks"

            return HealthCheck(
                "queue_depth",
                status,
                message,
                {"depth": depth, "warning_threshold": self.thresholds["queue_depth_warning"]}
            )

        except Exception as e:
            return HealthCheck(
                "queue_depth",
                HealthStatus.UNHEALTHY,
                f"Cannot check queue depth: {e!s}"
            )

    def check_task_runner_capacity(self) -> HealthCheck:
        """Check task runner capacity utilization."""
        if not self.task_runner:
            return HealthCheck(
                "task_runner_capacity",
                HealthStatus.HEALTHY,
                "No task runner configured"
            )

        try:
            active_tasks = len(self.task_runner._running_tasks)
            max_concurrent = self.task_runner.max_concurrent
            utilization = active_tasks / max_concurrent if max_concurrent > 0 else 0

            if utilization > self.thresholds["utilization_critical"]:
                status = HealthStatus.UNHEALTHY
                message = f"Task runner utilization critical: {utilization:.1%}"
            elif utilization > self.thresholds["utilization_warning"]:
                status = HealthStatus.DEGRADED
                message = f"Task runner utilization high: {utilization:.1%}"
            else:
                status = HealthStatus.HEALTHY
                message = f"Task runner utilization normal: {utilization:.1%}"

            return HealthCheck(
                "task_runner_capacity",
                status,
                message,
                {
                    "active_tasks": active_tasks,
                    "max_concurrent": max_concurrent,
                    "utilization": utilization
                }
            )

        except Exception as e:
            return HealthCheck(
                "task_runner_capacity",
                HealthStatus.UNHEALTHY,
                f"Cannot check task runner: {e!s}"
            )

    async def check_storage_backends(self) -> list[HealthCheck]:
        """Check all configured storage backends."""
        checks = []

        # Check Redis storage if available
        if REDIS_AVAILABLE and (self.redis_client or self.redis_queue):
            redis_check = await self.check_redis_connectivity()
            checks.append(redis_check)

        return checks

    async def get_overall_health(self) -> dict[str, Any]:
        """Get comprehensive health status."""
        checks = []

        # Collect all health checks
        checks.append(await self.check_redis_connectivity())
        checks.append(await self.check_queue_depth())
        checks.append(self.check_task_runner_capacity())

        # Determine overall status
        statuses = [check.status for check in checks]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": [asdict(check) for check in checks],
            "summary": {
                "total_checks": len(checks),
                "healthy": sum(1 for c in checks if c.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for c in checks if c.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for c in checks if c.status == HealthStatus.UNHEALTHY),
            }
        }

    async def is_healthy(self) -> bool:
        """Simple boolean health check."""
        health = await self.get_overall_health()
        return health["status"] == HealthStatus.HEALTHY.value

    def set_thresholds(self, thresholds: dict[str, Any]) -> None:
        """Update health check thresholds."""
        self.thresholds.update(thresholds)
