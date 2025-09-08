"""Health monitoring for dotmac-observability."""

import asyncio
import inspect
import time
from datetime import datetime
from typing import Any, Optional

from .types import (
    HealthCheckFunction,
    HealthCheckResult,
    HealthStatus,
)


class HealthMonitor:
    """
    Health monitoring system with configurable checks.

    Supports both sync and async health checks with timeout and error handling.
    """

    def __init__(self) -> None:
        """Initialize the health monitor."""
        self._checks: dict[str, dict[str, Any]] = {}
        self._last_results: Optional[dict[str, Any]] = None

    def add_check(
        self,
        name: str,
        check: HealthCheckFunction,
        *,
        required: bool = True,
        timeout: float = 5.0,
        description: str = "",
    ) -> None:
        """
        Add a health check.

        Args:
            name: Unique name for the check
            check: Function that returns True if healthy
            required: Whether this check is required for overall health
            timeout: Timeout in seconds
            description: Human-readable description
        """
        self._checks[name] = {
            "check": check,
            "required": required,
            "timeout": timeout,
            "description": description,
        }

    async def run_checks(self) -> dict[str, Any]:
        """
        Run all health checks and return results.

        Returns:
            Dictionary with overall status and individual check results
        """
        check_results: list[HealthCheckResult] = []
        start_time = time.perf_counter()

        # Run all checks
        for name, config in self._checks.items():
            result = await self._run_single_check(name, config)
            check_results.append(result)

        total_duration = (time.perf_counter() - start_time) * 1000

        # Determine overall status
        required_checks = [r for r in check_results if r.required]
        overall_status = self._determine_overall_status(required_checks)

        # Build response
        results = {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": total_duration,
            "checks": {r.name: self._result_to_dict(r) for r in check_results},
            "summary": {
                "total": len(check_results),
                "healthy": sum(1 for r in check_results if r.is_healthy()),
                "required": len(required_checks),
                "required_healthy": sum(1 for r in required_checks if r.is_healthy()),
            },
        }

        self._last_results = results
        return results

    def get_last_results(self) -> Optional[dict[str, Any]]:
        """
        Get results from the last check run.

        Returns:
            Last results or None if no checks have been run
        """
        return self._last_results

    async def _run_single_check(self, name: str, config: dict[str, Any]) -> HealthCheckResult:
        """Run a single health check with timeout and error handling."""
        check_func = config["check"]
        timeout = config["timeout"]
        required = config["required"]

        start_time = time.perf_counter()

        try:
            # Determine if check is async
            if inspect.iscoroutinefunction(check_func):
                # Async check
                result = await asyncio.wait_for(check_func(), timeout=timeout)
            else:
                # Sync check - run in thread pool to avoid blocking
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, check_func), timeout=timeout
                )

            duration_ms = (time.perf_counter() - start_time) * 1000

            if result is True:
                return HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    duration_ms=duration_ms,
                    required=required,
                    timestamp=datetime.utcnow(),
                )
            else:
                return HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    duration_ms=duration_ms,
                    error="Check returned False",
                    required=required,
                    timestamp=datetime.utcnow(),
                )

        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return HealthCheckResult(
                name=name,
                status=HealthStatus.TIMEOUT,
                duration_ms=duration_ms,
                error=f"Check timed out after {timeout}s",
                required=required,
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                duration_ms=duration_ms,
                error=str(e),
                required=required,
                timestamp=datetime.utcnow(),
            )

    def _determine_overall_status(self, required_checks: list[HealthCheckResult]) -> HealthStatus:
        """Determine overall health status based on required checks."""
        if not required_checks:
            return HealthStatus.UNKNOWN

        unhealthy_count = sum(1 for check in required_checks if not check.is_healthy())

        if unhealthy_count == 0:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNHEALTHY

    def _result_to_dict(self, result: HealthCheckResult) -> dict[str, Any]:
        """Convert a HealthCheckResult to a dictionary."""
        data = {
            "status": result.status.value,
            "duration_ms": result.duration_ms,
            "required": result.required,
        }

        if result.error:
            data["error"] = result.error
        if result.message:
            data["message"] = result.message
        if result.timestamp:
            data["timestamp"] = result.timestamp.isoformat()

        return data

    def remove_check(self, name: str) -> bool:
        """
        Remove a health check.

        Args:
            name: Name of the check to remove

        Returns:
            True if check was removed, False if not found
        """
        if name in self._checks:
            del self._checks[name]
            return True
        return False

    def list_checks(self) -> list[dict[str, Any]]:
        """
        List all configured health checks.

        Returns:
            List of check configurations
        """
        checks = []
        for name, config in self._checks.items():
            checks.append(
                {
                    "name": name,
                    "required": config["required"],
                    "timeout": config["timeout"],
                    "description": config["description"],
                }
            )
        return checks
