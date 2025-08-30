"""
Connection Validator - Validates database connectivity and health.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import asyncpg
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from .database_creator import DatabaseInstance

logger = structlog.get_logger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    status: HealthStatus
    response_time_ms: Optional[float]
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class ConnectionMetrics:
    """Database connection metrics."""

    active_connections: int
    idle_connections: int
    total_connections: int
    max_connections: int
    connection_utilization: float
    avg_response_time_ms: float


class ConnectionValidator:
    """Validates database connectivity and monitors health."""

    def __init__(self, db_instance: DatabaseInstance):
        self.db_instance = db_instance
        self.logger = logger.bind(
            component="connection_validator", database=db_instance.database_name
        )
        self._connection_pool = None

    async def _get_connection_pool(self):
        """Get or create connection pool."""
        if self._connection_pool is None:
            self._connection_pool = await asyncpg.create_pool(
                **self.db_instance.get_connection_params(),
                min_size=2,
                max_size=10,
                command_timeout=10,
            )
        return self._connection_pool

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def validate_database_health(self) -> HealthCheckResult:
        """
        Comprehensive database health validation.

        Returns:
            HealthCheckResult with overall health status
        """
        self.logger.info("Starting database health validation")

        start_time = time.time()

        try:
            # Run all health checks
            checks = await asyncio.gather(
                self._check_basic_connectivity(),
                self._check_schema_integrity(),
                self._check_performance_metrics(),
                self._check_disk_space(),
                return_exceptions=True,
            )

            # Evaluate overall health
            overall_status = self._evaluate_overall_health(checks)

            response_time_ms = (time.time() - start_time) * 1000

            # Compile details
            details = {
                "connectivity": (
                    checks[0]
                    if not isinstance(checks[0], Exception)
                    else {"error": str(checks[0])}
                ),
                "schema": (
                    checks[1]
                    if not isinstance(checks[1], Exception)
                    else {"error": str(checks[1])}
                ),
                "performance": (
                    checks[2]
                    if not isinstance(checks[2], Exception)
                    else {"error": str(checks[2])}
                ),
                "disk_space": (
                    checks[3]
                    if not isinstance(checks[3], Exception)
                    else {"error": str(checks[3])}
                ),
                "validation_time_ms": response_time_ms,
            }

            result = HealthCheckResult(
                status=overall_status,
                response_time_ms=response_time_ms,
                details=details,
            )

            self.logger.info(
                "Database health validation completed",
                status=overall_status.value,
                response_time_ms=response_time_ms,
            )

            return result

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000

            self.logger.error(
                "Database health validation failed",
                error=str(e),
                response_time_ms=response_time_ms,
                exc_info=True,
            )

            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                error=str(e),
            )

    async def _check_basic_connectivity(self) -> Dict[str, Any]:
        """Check basic database connectivity."""
        start_time = time.time()

        try:
            pool = await self._get_connection_pool()

            async with pool.acquire() as conn:
                # Test basic query
                result = await conn.fetchval("SELECT 1")

                if result != 1:
                    raise RuntimeError("Basic connectivity test failed")

                # Get database version
                version = await conn.fetchval("SELECT version()")

                response_time = (time.time() - start_time) * 1000

                return {
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "database_version": version,
                }

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": response_time,
            }

    async def _check_schema_integrity(self) -> Dict[str, Any]:
        """Check database schema integrity."""
        try:
            pool = await self._get_connection_pool()

            async with pool.acquire() as conn:
                # Check for essential tables
                table_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    """
                )

                # Check for alembic version table
                alembic_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'alembic_version'
                    )
                    """
                )

                # Get current migration version
                current_version = None
                if alembic_exists:
                    current_version = await conn.fetchval(
                        "SELECT version_num FROM alembic_version LIMIT 1"
                    )

                # Check for constraints and indexes
                constraint_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM information_schema.table_constraints
                    WHERE table_schema = 'public'
                    """
                )

                index_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM pg_indexes
                    WHERE schemaname = 'public'
                    """
                )

                status = "healthy" if table_count > 0 else "degraded"

                return {
                    "status": status,
                    "table_count": table_count,
                    "alembic_version": current_version,
                    "constraint_count": constraint_count,
                    "index_count": index_count,
                }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def _check_performance_metrics(self) -> Dict[str, Any]:
        """Check database performance metrics."""
        try:
            pool = await self._get_connection_pool()

            async with pool.acquire() as conn:
                # Check connection stats
                connection_stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_connections,
                        COUNT(*) FILTER (WHERE state = 'active') as active_connections,
                        COUNT(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity
                    WHERE datname = $1
                    """,
                    self.db_instance.database_name,
                )

                # Check database size
                db_size = await conn.fetchval(
                    "SELECT pg_size_pretty(pg_database_size($1))",
                    self.db_instance.database_name,
                )

                # Check query performance (top slow queries)
                slow_queries = await conn.fetch(
                    """
                    SELECT query, calls, mean_exec_time, total_exec_time
                    FROM pg_stat_statements
                    WHERE dbid = (SELECT oid FROM pg_database WHERE datname = $1)
                    ORDER BY mean_exec_time DESC
                    LIMIT 5
                    """,
                    self.db_instance.database_name,
                )

                # Calculate connection utilization
                max_connections = await conn.fetchval("SHOW max_connections")
                utilization = (
                    connection_stats["total_connections"] / int(max_connections)
                ) * 100

                # Determine performance status
                status = "healthy"
                if utilization > 80:
                    status = "degraded"
                elif utilization > 95:
                    status = "unhealthy"

                return {
                    "status": status,
                    "connections": {
                        "total": connection_stats["total_connections"],
                        "active": connection_stats["active_connections"],
                        "idle": connection_stats["idle_connections"],
                        "utilization_percent": round(utilization, 2),
                    },
                    "database_size": db_size,
                    "slow_queries": (
                        [dict(q) for q in slow_queries] if slow_queries else []
                    ),
                }

        except Exception as e:
            return {"status": "unknown", "error": str(e)}

    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check database disk space."""
        try:
            pool = await self._get_connection_pool()

            async with pool.acquire() as conn:
                # Get tablespace usage
                tablespace_usage = await conn.fetch(
                    """
                    SELECT
                        spcname as tablespace_name,
                        pg_size_pretty(pg_tablespace_size(spcname)) as size
                    FROM pg_tablespace
                    """
                )

                # Get database size details
                db_size_bytes = await conn.fetchval(
                    "SELECT pg_database_size($1)", self.db_instance.database_name
                )

                db_size_pretty = await conn.fetchval(
                    "SELECT pg_size_pretty($1)", db_size_bytes
                )

                # Check table sizes
                table_sizes = await conn.fetch(
                    """
                    SELECT
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 10
                    """
                )

                return {
                    "status": "healthy",  # We don't have disk space limits to check against
                    "database_size": {"bytes": db_size_bytes, "pretty": db_size_pretty},
                    "tablespaces": [dict(ts) for ts in tablespace_usage],
                    "largest_tables": [dict(table) for table in table_sizes],
                }

        except Exception as e:
            return {"status": "unknown", "error": str(e)}

    def _evaluate_overall_health(self, checks: List) -> HealthStatus:
        """Evaluate overall health based on individual checks."""
        statuses = []

        for check in checks:
            if isinstance(check, Exception):
                statuses.append(HealthStatus.UNHEALTHY)
            elif isinstance(check, dict) and "status" in check:
                status_str = check["status"]
                if status_str == "healthy":
                    statuses.append(HealthStatus.HEALTHY)
                elif status_str == "degraded":
                    statuses.append(HealthStatus.DEGRADED)
                elif status_str == "unhealthy":
                    statuses.append(HealthStatus.UNHEALTHY)
                else:
                    statuses.append(HealthStatus.UNKNOWN)
            else:
                statuses.append(HealthStatus.UNKNOWN)

        # Determine overall status
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    async def get_connection_metrics(self) -> ConnectionMetrics:
        """Get detailed connection metrics."""
        try:
            pool = await self._get_connection_pool()

            async with pool.acquire() as conn:
                # Get connection statistics
                stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_connections,
                        COUNT(*) FILTER (WHERE state = 'active') as active_connections,
                        COUNT(*) FILTER (WHERE state = 'idle') as idle_connections,
                        AVG(EXTRACT(EPOCH FROM (now() - query_start)) * 1000)
                            FILTER (WHERE state = 'active') as avg_query_time_ms
                    FROM pg_stat_activity
                    WHERE datname = $1
                    """,
                    self.db_instance.database_name,
                )

                max_connections = await conn.fetchval("SHOW max_connections")

                return ConnectionMetrics(
                    active_connections=stats["active_connections"] or 0,
                    idle_connections=stats["idle_connections"] or 0,
                    total_connections=stats["total_connections"] or 0,
                    max_connections=int(max_connections),
                    connection_utilization=(stats["total_connections"] or 0)
                    / int(max_connections),
                    avg_response_time_ms=stats["avg_query_time_ms"] or 0.0,
                )

        except Exception as e:
            self.logger.error("Failed to get connection metrics", error=str(e))
            raise

    async def test_query_performance(
        self, test_queries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Test query performance with sample queries."""
        if test_queries is None:
            test_queries = [
                "SELECT 1",
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'",
                "SELECT version()",
                "SELECT current_timestamp",
            ]

        results = {}
        pool = await self._get_connection_pool()

        for i, query in enumerate(test_queries):
            try:
                start_time = time.time()

                async with pool.acquire() as conn:
                    result = await conn.fetchval(query)

                execution_time_ms = (time.time() - start_time) * 1000

                results[f"query_{i+1}"] = {
                    "query": query,
                    "execution_time_ms": execution_time_ms,
                    "result": str(result) if result is not None else None,
                    "status": "success",
                }

            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000

                results[f"query_{i+1}"] = {
                    "query": query,
                    "execution_time_ms": execution_time_ms,
                    "error": str(e),
                    "status": "failed",
                }

        # Calculate average execution time
        successful_queries = [r for r in results.values() if r["status"] == "success"]
        avg_execution_time = 0
        if successful_queries:
            avg_execution_time = sum(
                q["execution_time_ms"] for q in successful_queries
            ) / len(successful_queries)

        return {
            "average_execution_time_ms": avg_execution_time,
            "total_queries": len(test_queries),
            "successful_queries": len(successful_queries),
            "failed_queries": len(test_queries) - len(successful_queries),
            "query_results": results,
        }

    async def cleanup(self):
        """Clean up resources."""
        if self._connection_pool:
            await self._connection_pool.close()
            self._connection_pool = None
