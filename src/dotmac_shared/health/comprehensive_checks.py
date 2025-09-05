"""
Comprehensive Health Check System for DotMac Framework
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Optional

import asyncpg
import httpx

import redis

logger = logging.getLogger(__name__)


class HealthChecker:
    """Main health checker for all system components."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}

    async def check_all(self) -> dict[str, Any]:
        """Check health of all system components."""
        results = {"timestamp": datetime.now().isoformat(), "overall_status": "unknown"}

        # Run all health checks concurrently
        checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_external_services(),
            return_exceptions=True,
        )

        # Process results
        results["database"] = (
            checks[0]
            if not isinstance(checks[0], Exception)
            else {"status": "error", "error": str(checks[0])}
        )
        results["redis"] = (
            checks[1]
            if not isinstance(checks[1], Exception)
            else {"status": "error", "error": str(checks[1])}
        )
        results["external_services"] = (
            checks[2] if not isinstance(checks[2], Exception) else []
        )

        # Determine overall status
        results["overall_status"] = self._determine_overall_status(results)

        return results

    async def check_database(self) -> dict[str, Any]:
        """Check database health."""
        start_time = time.time()

        try:
            pool = await self._get_db_pool()

            async with pool.acquire() as conn:
                # Simple health check query
                result = await conn.fetchval("SELECT 1")

                if result == 1:
                    response_time = time.time() - start_time
                    return {
                        "status": "healthy",
                        "response_time": round(response_time, 3),
                    }
                else:
                    return {"status": "unhealthy", "error": "Unexpected query result"}

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - start_time,
            }

    async def check_redis(self) -> dict[str, Any]:
        """Check Redis health."""
        start_time = time.time()

        try:
            redis_client = await self._get_redis_client()

            # Test Redis connection
            result = await redis_client.ping()

            if result:
                response_time = time.time() - start_time
                return {"status": "healthy", "response_time": round(response_time, 3)}
            else:
                return {"status": "unhealthy", "error": "Redis ping failed"}

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - start_time,
            }

    async def check_external_services(self) -> list[dict[str, Any]]:
        """Check external service health."""
        external_services = self.config.get("external_services", [])
        if not external_services:
            return []

        tasks = [
            self.check_external_service(service["url"]) for service in external_services
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        service_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_results.append(
                    {
                        "name": external_services[i].get("name", f"service_{i}"),
                        "status": "unhealthy",
                        "error": str(result),
                    }
                )
            else:
                result["name"] = external_services[i].get("name", f"service_{i}")
                service_results.append(result)

        return service_results

    async def check_external_service(self, url: str) -> dict[str, Any]:
        """Check a single external service."""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)

                response_time = time.time() - start_time

                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "status_code": response.status_code,
                        "response_time": round(response_time, 3),
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "status_code": response.status_code,
                        "response_time": round(response_time, 3),
                    }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - start_time,
            }

    async def _get_db_pool(self):
        """Get database connection pool."""
        if hasattr(self, "_db_pool"):
            return self._db_pool

        db_url = self.config.get("database_url", "postgresql://localhost/test")
        return await asyncpg.create_pool(db_url, min_size=1, max_size=5)

    async def _get_redis_client(self):
        """Get Redis client."""
        if hasattr(self, "_redis_client"):
            return self._redis_client

        redis_url = self.config.get("redis_url", "redis://localhost:6379/1")
        return redis.from_url(redis_url)

    def _determine_overall_status(self, results: dict[str, Any]) -> str:
        """Determine overall system status."""
        critical_services = ["database", "redis"]

        # Check critical services
        for service in critical_services:
            if results.get(service, {}).get("status") == "unhealthy":
                return "unhealthy"

        # Check external services
        external_services = results.get("external_services", [])
        unhealthy_external = sum(
            1 for svc in external_services if svc.get("status") == "unhealthy"
        )

        if unhealthy_external > len(external_services) / 2:  # More than half unhealthy
            return "degraded"
        elif unhealthy_external > 0:
            return "degraded"

        return "healthy"


class DatabaseHealthCheck:
    """Detailed database health checks."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    async def check_pool_health(self) -> dict[str, Any]:
        """Check connection pool health."""
        if not hasattr(self, "_pool"):
            return {"error": "Pool not initialized"}

        return {
            "total_connections": self._pool.get_size(),
            "idle_connections": self._pool.get_idle_size(),
            "active_connections": self._pool.get_size() - self._pool.get_idle_size(),
        }

    async def check_query_performance(self) -> dict[str, Any]:
        """Check database query performance."""
        start_time = time.time()

        try:
            async with self._get_connection() as conn:
                # Test query performance
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM information_schema.tables"
                )

                query_time = time.time() - start_time
                return {"query_time": round(query_time, 3), "row_count": result}

        except Exception as e:
            return {"error": str(e), "query_time": time.time() - start_time}

    async def check_disk_space(self) -> dict[str, Any]:
        """Check database disk space usage."""
        try:
            async with self._get_connection() as conn:
                # PostgreSQL disk space query
                result = await conn.fetchrow(
                    """
                    SELECT
                        pg_database_size(current_database()) as database_size,
                        pg_size_pretty(pg_database_size(current_database())) as database_size_pretty
                """
                )

                database_size_bytes = result["database_size"]

                return {
                    "database_size_mb": round(database_size_bytes / (1024 * 1024), 2),
                    "available_space_gb": 10,  # This would be calculated from system stats
                    "usage_percentage": 10.0,  # This would be calculated
                }

        except Exception as e:
            return {"error": str(e)}

    @asynccontextmanager
    async def _get_connection(self):
        """Get database connection context manager."""

        # Mock implementation - would use actual connection
        class MockConnection:
            """MockConnection implementation."""

            async def fetchval(self, query):
                return 100

            async def fetchrow(self, query):
                return {
                    "database_size": 1073741824,  # 1GB
                    "database_size_pretty": "1024 MB",
                }

        yield MockConnection()


class RedisHealthCheck:
    """Detailed Redis health checks."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url

    async def check_memory_usage(self) -> dict[str, Any]:
        """Check Redis memory usage."""
        try:
            info = await self._redis_client.info("memory")

            used_memory = info.get("used_memory", 0)
            used_memory_peak = info.get("used_memory_peak", 0)
            maxmemory = info.get("maxmemory", 0)

            return {
                "used_memory_mb": round(used_memory / (1024 * 1024), 2),
                "peak_memory_mb": round(used_memory_peak / (1024 * 1024), 2),
                "max_memory_mb": (
                    round(maxmemory / (1024 * 1024), 2) if maxmemory else None
                ),
                "memory_usage_percentage": (
                    round((used_memory / maxmemory) * 100, 2) if maxmemory else None
                ),
            }

        except Exception as e:
            return {"error": str(e)}

    async def check_connected_clients(self) -> dict[str, Any]:
        """Check Redis connected clients."""
        try:
            info = await self._redis_client.info("clients")

            return {
                "connected_clients": info.get("connected_clients", 0),
                "longest_output_list": info.get("client_longest_output_list", 0),
                "biggest_input_buf": info.get("client_biggest_input_buf", 0),
            }

        except Exception as e:
            return {"error": str(e)}

    async def check_key_statistics(self) -> dict[str, Any]:
        """Check Redis key statistics."""
        try:
            info = await self._redis_client.info("keyspace")
            total_keys = await self._redis_client.dbsize()

            databases = {}
            for key, value in info.items():
                if key.startswith("db"):
                    # Parse db info: keys=1000,expires=50,avg_ttl=3600000
                    db_info = {}
                    for item in value.split(","):
                        k, v = item.split("=")
                        db_info[k] = int(v)
                    databases[key] = db_info

            return {"total_keys": total_keys, "databases": databases}

        except Exception as e:
            return {"error": str(e)}

    async def check_performance_metrics(self) -> dict[str, Any]:
        """Check Redis performance metrics."""
        try:
            start_time = time.time()
            await self._redis_client.ping()
            latency = (time.time() - start_time) * 1000  # Convert to milliseconds

            info = await self._redis_client.info("stats")

            return {
                "latency_ms": round(latency, 2),
                "ops_per_second": info.get("instantaneous_ops_per_sec", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
            }

        except Exception as e:
            return {"error": str(e)}

    @property
    def _redis_client(self):
        """Get Redis client."""
        if not hasattr(self, "_client"):
            self._client = redis.from_url(self.redis_url)
        return self._client


class ExternalServiceHealthCheck:
    """Health checks for external services."""

    def __init__(self, services: list[dict[str, Any]]):
        self.services = services

    async def check_all_services(self) -> list[dict[str, Any]]:
        """Check all external services."""
        tasks = [self.check_service(service) for service in self.services]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        service_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_results.append(
                    {
                        "name": self.services[i].get("name", f"service_{i}"),
                        "status": "unhealthy",
                        "error": str(result),
                    }
                )
            else:
                service_results.append(result)

        return service_results

    async def check_service(self, service_config: dict[str, Any]) -> dict[str, Any]:
        """Check a single external service."""
        name = service_config.get("name", "unknown")
        url = service_config["url"]
        timeout = service_config.get("timeout", 5.0)
        headers = service_config.get("headers", {})

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=headers)

                response_time = time.time() - start_time

                result = {
                    "name": name,
                    "url": url,
                    "status_code": response.status_code,
                    "response_time": round(response_time, 3),
                }

                if response.status_code == 200:
                    result["status"] = "healthy"
                else:
                    result["status"] = "unhealthy"

                return result

        except asyncio.TimeoutError:
            return {
                "name": name,
                "url": url,
                "status": "unhealthy",
                "error": "Request timeout",
                "response_time": time.time() - start_time,
            }
        except Exception as e:
            return {
                "name": name,
                "url": url,
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - start_time,
            }


async def perform_health_check(
    config: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Perform comprehensive health check."""
    try:
        health_checker = HealthChecker(config)
        return await health_checker.check_all()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
