"""
Database health monitoring and diagnostics.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Health check result container."""

    status: HealthStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None


class DatabaseHealthChecker:
    """
    Comprehensive database health checker with configurable checks.

    Provides health monitoring for database connections, performance,
    and system metrics.
    """

    def __init__(
        self,
        connection_timeout: float = 5.0,
        query_timeout: float = 10.0,
        slow_query_threshold: float = 1.0,
    ):
        """
        Initialize health checker.

        Args:
            connection_timeout: Connection timeout in seconds
            query_timeout: Query timeout in seconds
            slow_query_threshold: Threshold for slow query warning (seconds)
        """
        self.connection_timeout = connection_timeout
        self.query_timeout = query_timeout
        self.slow_query_threshold = slow_query_threshold

    def check_health(self, session: Session) -> HealthCheckResult:
        """
        Perform comprehensive health check (synchronous).

        Args:
            session: Database session

        Returns:
            Health check result
        """
        start_time = time.time()

        try:
            # Perform basic connectivity check
            connectivity_result = self._check_connectivity(session)
            if connectivity_result.status != HealthStatus.HEALTHY:
                return connectivity_result

            # Perform performance check
            performance_result = self._check_performance(session)

            # Collect system metrics
            metrics = self._collect_metrics(session)

            # Determine overall health status
            overall_status = self._determine_overall_status(
                [
                    connectivity_result,
                    performance_result,
                ]
            )

            duration_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                status=overall_status,
                message=f"Database health check completed in {duration_ms:.2f}ms",
                details={
                    "connectivity": connectivity_result.details,
                    "performance": performance_result.details,
                    "metrics": metrics,
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Health check failed: %s", e)

            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {e!s}",
                details={"error": str(e)},
                duration_ms=duration_ms,
                error=str(e),
            )

    async def async_check_health(self, session: AsyncSession) -> HealthCheckResult:
        """
        Perform comprehensive health check (asynchronous).

        Args:
            session: Async database session

        Returns:
            Health check result
        """
        start_time = time.time()

        try:
            # Perform basic connectivity check
            connectivity_result = await self._async_check_connectivity(session)
            if connectivity_result.status != HealthStatus.HEALTHY:
                return connectivity_result

            # Perform performance check
            performance_result = await self._async_check_performance(session)

            # Collect system metrics
            metrics = await self._async_collect_metrics(session)

            # Determine overall health status
            overall_status = self._determine_overall_status(
                [
                    connectivity_result,
                    performance_result,
                ]
            )

            duration_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                status=overall_status,
                message=f"Database health check completed in {duration_ms:.2f}ms",
                details={
                    "connectivity": connectivity_result.details,
                    "performance": performance_result.details,
                    "metrics": metrics,
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Async health check failed: %s", e)

            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {e!s}",
                details={"error": str(e)},
                duration_ms=duration_ms,
                error=str(e),
            )

    def check_connectivity(self, session: Session) -> HealthCheckResult:
        """
        Check basic database connectivity.

        Args:
            session: Database session

        Returns:
            Connectivity check result
        """
        return self._check_connectivity(session)

    async def async_check_connectivity(self, session: AsyncSession) -> HealthCheckResult:
        """
        Check basic database connectivity (async).

        Args:
            session: Async database session

        Returns:
            Connectivity check result
        """
        return await self._async_check_connectivity(session)

    def _check_connectivity(self, session: Session) -> HealthCheckResult:
        """Internal connectivity check (sync)."""
        start_time = time.time()

        try:
            # Execute simple query to test connectivity
            result = session.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()

            duration_ms = (time.time() - start_time) * 1000

            if row and row[0] == 1:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful",
                    details={
                        "query_duration_ms": duration_ms,
                        "connection_active": True,
                    },
                    duration_ms=duration_ms,
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message="Database query returned unexpected result",
                    details={
                        "query_duration_ms": duration_ms,
                        "expected_result": 1,
                        "actual_result": row[0] if row else None,
                    },
                    duration_ms=duration_ms,
                )

        except SQLAlchemyError as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Database connectivity failed: {e!s}",
                details={
                    "query_duration_ms": duration_ms,
                    "error_type": type(e).__name__,
                    "connection_active": False,
                },
                duration_ms=duration_ms,
                error=str(e),
            )

    async def _async_check_connectivity(self, session: AsyncSession) -> HealthCheckResult:
        """Internal connectivity check (async)."""
        start_time = time.time()

        try:
            # Execute simple query to test connectivity
            result = await session.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()

            duration_ms = (time.time() - start_time) * 1000

            if row and row[0] == 1:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful",
                    details={
                        "query_duration_ms": duration_ms,
                        "connection_active": True,
                    },
                    duration_ms=duration_ms,
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message="Database query returned unexpected result",
                    details={
                        "query_duration_ms": duration_ms,
                        "expected_result": 1,
                        "actual_result": row[0] if row else None,
                    },
                    duration_ms=duration_ms,
                )

        except SQLAlchemyError as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Database connectivity failed: {e!s}",
                details={
                    "query_duration_ms": duration_ms,
                    "error_type": type(e).__name__,
                    "connection_active": False,
                },
                duration_ms=duration_ms,
                error=str(e),
            )

    def _check_performance(self, session: Session) -> HealthCheckResult:
        """Internal performance check (sync)."""
        start_time = time.time()

        try:
            # Test query performance
            query = text("SELECT COUNT(*) FROM information_schema.tables")
            result = session.execute(query)
            count = result.scalar()

            duration_ms = (time.time() - start_time) * 1000

            # Determine status based on query duration
            if duration_ms < self.slow_query_threshold * 1000:
                status = HealthStatus.HEALTHY
                message = f"Database performance is good ({duration_ms:.2f}ms)"
            elif duration_ms < self.slow_query_threshold * 2000:
                status = HealthStatus.DEGRADED
                message = f"Database performance is degraded ({duration_ms:.2f}ms)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Database performance is poor ({duration_ms:.2f}ms)"

            return HealthCheckResult(
                status=status,
                message=message,
                details={
                    "query_duration_ms": duration_ms,
                    "slow_query_threshold_ms": self.slow_query_threshold * 1000,
                    "table_count": count,
                },
                duration_ms=duration_ms,
            )

        except SQLAlchemyError as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Performance check failed: {e!s}",
                details={
                    "query_duration_ms": duration_ms,
                    "error_type": type(e).__name__,
                },
                duration_ms=duration_ms,
                error=str(e),
            )

    async def _async_check_performance(self, session: AsyncSession) -> HealthCheckResult:
        """Internal performance check (async)."""
        start_time = time.time()

        try:
            # Test query performance
            query = text("SELECT COUNT(*) FROM information_schema.tables")
            result = await session.execute(query)
            count = result.scalar()

            duration_ms = (time.time() - start_time) * 1000

            # Determine status based on query duration
            if duration_ms < self.slow_query_threshold * 1000:
                status = HealthStatus.HEALTHY
                message = f"Database performance is good ({duration_ms:.2f}ms)"
            elif duration_ms < self.slow_query_threshold * 2000:
                status = HealthStatus.DEGRADED
                message = f"Database performance is degraded ({duration_ms:.2f}ms)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Database performance is poor ({duration_ms:.2f}ms)"

            return HealthCheckResult(
                status=status,
                message=message,
                details={
                    "query_duration_ms": duration_ms,
                    "slow_query_threshold_ms": self.slow_query_threshold * 1000,
                    "table_count": count,
                },
                duration_ms=duration_ms,
            )

        except SQLAlchemyError as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Performance check failed: {e!s}",
                details={
                    "query_duration_ms": duration_ms,
                    "error_type": type(e).__name__,
                },
                duration_ms=duration_ms,
                error=str(e),
            )

    def _collect_metrics(self, session: Session) -> dict[str, Any]:
        """Collect database metrics (sync)."""
        metrics = {}

        try:
            # Database version
            version_result = session.execute(text("SELECT version()"))
            metrics["database_version"] = version_result.scalar()

            # Active connections (PostgreSQL specific)
            try:
                connections_result = session.execute(
                    text(
                        """
                    SELECT count(*)
                    FROM pg_stat_activity
                    WHERE state = 'active'
                """
                    )
                )
                metrics["active_connections"] = connections_result.scalar()
            except SQLAlchemyError:
                # Not PostgreSQL or insufficient permissions
                metrics["active_connections"] = "unavailable"

            # Database size (PostgreSQL specific)
            try:
                size_result = session.execute(
                    text(
                        """
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """
                    )
                )
                metrics["database_size"] = size_result.scalar()
            except SQLAlchemyError:
                metrics["database_size"] = "unavailable"

        except SQLAlchemyError as e:
            logger.warning("Failed to collect some metrics: %s", e)
            metrics["collection_error"] = str(e)

        return metrics

    async def _async_collect_metrics(self, session: AsyncSession) -> dict[str, Any]:
        """Collect database metrics (async)."""
        metrics = {}

        try:
            # Database version
            version_result = await session.execute(text("SELECT version()"))
            metrics["database_version"] = version_result.scalar()

            # Active connections (PostgreSQL specific)
            try:
                connections_result = await session.execute(
                    text(
                        """
                    SELECT count(*)
                    FROM pg_stat_activity
                    WHERE state = 'active'
                """
                    )
                )
                metrics["active_connections"] = connections_result.scalar()
            except SQLAlchemyError:
                # Not PostgreSQL or insufficient permissions
                metrics["active_connections"] = "unavailable"

            # Database size (PostgreSQL specific)
            try:
                size_result = await session.execute(
                    text(
                        """
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """
                    )
                )
                metrics["database_size"] = size_result.scalar()
            except SQLAlchemyError:
                metrics["database_size"] = "unavailable"

        except SQLAlchemyError as e:
            logger.warning("Failed to collect some metrics: %s", e)
            metrics["collection_error"] = str(e)

        return metrics

    def _determine_overall_status(self, results: list[HealthCheckResult]) -> HealthStatus:
        """Determine overall health status from individual checks."""
        if any(result.status == HealthStatus.UNHEALTHY for result in results):
            return HealthStatus.UNHEALTHY
        elif any(result.status == HealthStatus.DEGRADED for result in results):
            return HealthStatus.DEGRADED
        elif all(result.status == HealthStatus.HEALTHY for result in results):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN


class AdvancedHealthChecker(DatabaseHealthChecker):
    """
    Advanced health checker with additional database-specific checks.
    """

    def __init__(
        self,
        connection_timeout: float = 5.0,
        query_timeout: float = 10.0,
        slow_query_threshold: float = 1.0,
        enable_deep_checks: bool = False,
    ):
        """
        Initialize advanced health checker.

        Args:
            connection_timeout: Connection timeout in seconds
            query_timeout: Query timeout in seconds
            slow_query_threshold: Threshold for slow query warning (seconds)
            enable_deep_checks: Enable resource-intensive deep checks
        """
        super().__init__(connection_timeout, query_timeout, slow_query_threshold)
        self.enable_deep_checks = enable_deep_checks

    def check_health(self, session: Session) -> HealthCheckResult:
        """Enhanced health check with additional database-specific checks."""
        # Run basic health checks first
        basic_result = super().check_health(session)

        if not self.enable_deep_checks or basic_result.status == HealthStatus.UNHEALTHY:
            return basic_result

        # Perform additional deep checks
        try:
            deep_checks = self._perform_deep_checks(session)

            # Merge results
            basic_result.details.update({"deep_checks": deep_checks})

            return basic_result

        except Exception as e:
            logger.warning("Deep health checks failed: %s", e)
            basic_result.details["deep_checks"] = {"error": str(e)}
            return basic_result

    def _perform_deep_checks(self, session: Session) -> dict[str, Any]:
        """Perform resource-intensive deep health checks."""
        deep_checks = {}

        try:
            # Check for long-running queries (PostgreSQL)
            long_queries = session.execute(
                text(
                    """
                SELECT count(*)
                FROM pg_stat_activity
                WHERE state = 'active'
                AND now() - query_start > interval '30 seconds'
            """
                )
            )
            deep_checks["long_running_queries"] = long_queries.scalar()

        except SQLAlchemyError:
            deep_checks["long_running_queries"] = "unavailable"

        try:
            # Check for table bloat (PostgreSQL)
            bloat_check = session.execute(
                text(
                    """
                SELECT schemaname, tablename,
                       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 5
            """
                )
            )
            large_tables = [dict(row._mapping) for row in bloat_check.fetchall()]
            deep_checks["largest_tables"] = large_tables

        except SQLAlchemyError:
            deep_checks["largest_tables"] = "unavailable"

        return deep_checks
