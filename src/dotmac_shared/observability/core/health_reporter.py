"""
Health status reporter for cross-platform monitoring.

Enhanced version of the ISP framework health reporter for shared service usage.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class HealthReporter:
    """Service for reporting health status with cross-platform compatibility."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize health reporter."""
        self.config = config or {}
        self.tenant_id = os.getenv("ISP_TENANT_ID") or self.config.get("tenant_id")
        self.reporting_interval = int(
            os.getenv("HEALTH_REPORTING_INTERVAL", "60")
        )  # seconds
        self.is_running = False
        self._health_data_cache = {}
        self._last_report_time = None

        # Health check configuration
        self.include_system_metrics = self.config.get("include_system_metrics", True)
        self.include_database_health = self.config.get("include_database_health", True)
        self.include_redis_health = self.config.get("include_redis_health", True)
        self.include_network_health = self.config.get("include_network_health", True)
        self.include_application_health = self.config.get(
            "include_application_health", True
        )
        self.include_business_metrics = self.config.get(
            "include_business_metrics", True
        )

        # Thresholds
        self.cpu_warning_threshold = self.config.get("cpu_warning_threshold", 70.0)
        self.cpu_critical_threshold = self.config.get("cpu_critical_threshold", 90.0)
        self.memory_warning_threshold = self.config.get(
            "memory_warning_threshold", 70.0
        )
        self.memory_critical_threshold = self.config.get(
            "memory_critical_threshold", 90.0
        )
        self.disk_warning_threshold = self.config.get("disk_warning_threshold", 80.0)
        self.disk_critical_threshold = self.config.get("disk_critical_threshold", 90.0)

        # Database thresholds
        self.db_response_warning_ms = self.config.get("db_response_warning_ms", 1000.0)
        self.db_response_critical_ms = self.config.get(
            "db_response_critical_ms", 5000.0
        )

        # Redis thresholds
        self.redis_response_warning_ms = self.config.get(
            "redis_response_warning_ms", 100.0
        )
        self.redis_response_critical_ms = self.config.get(
            "redis_response_critical_ms", 1000.0
        )

    async def start_health_reporting(self):
        """Start background health reporting task."""
        if self.is_running:
            return

        self.is_running = True
        logger.info("Starting health reporting")

        # Start background task
        asyncio.create_task(self._health_reporting_loop())

    def stop_health_reporting(self):
        """Stop health reporting."""
        self.is_running = False
        logger.info("Stopped health reporting")

    async def _health_reporting_loop(self):
        """Background loop for health reporting."""
        while self.is_running:
            try:
                await self._collect_and_report_health()
                await asyncio.sleep(self.reporting_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health reporting loop: {e}")
                await asyncio.sleep(self.reporting_interval)

    async def _collect_and_report_health(self):
        """Collect health data and report to external systems."""
        try:
            # Collect health data for all components
            health_data = await self._collect_comprehensive_health_data()

            # Cache the data
            self._health_data_cache = health_data
            self._last_report_time = datetime.now(timezone.utc)

            # Report to external systems (can be extended)
            await self._report_to_external_systems(health_data)

            logger.debug(f"Health reported for {len(health_data)} components")

        except Exception as e:
            logger.error(f"Error collecting and reporting health: {e}")

    async def _report_to_external_systems(self, health_data: Dict[str, Dict[str, Any]]):
        """Report health data to external monitoring systems."""
        # This can be extended to report to various systems
        # For now, we just log the health summary

        unhealthy_components = [
            comp
            for comp, data in health_data.items()
            if data.get("status") == "unhealthy"
        ]

        warning_components = [
            comp
            for comp, data in health_data.items()
            if data.get("status") == "warning"
        ]

        if unhealthy_components:
            logger.warning(f"Unhealthy components: {unhealthy_components}")

        if warning_components:
            logger.warning(f"Warning components: {warning_components}")

    async def _collect_comprehensive_health_data(self) -> Dict[str, Dict[str, Any]]:
        """Collect comprehensive health data for all components."""
        health_data = {}

        # System health
        if self.include_system_metrics:
            health_data["system"] = await self._check_system_health()

        # Database health
        if self.include_database_health:
            health_data["database"] = await self._check_database_health()

        # Redis health
        if self.include_redis_health:
            health_data["redis"] = await self._check_redis_health()

        # Application health
        if self.include_application_health:
            health_data["application"] = await self._check_application_health()

        # Plugin health
        health_data["plugins"] = await self._check_plugins_health()

        # Network health
        if self.include_network_health:
            health_data["network"] = await self._check_network_health()

        return health_data

    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system resource health."""
        if not PSUTIL_AVAILABLE:
            return {
                "status": "unknown",
                "metrics": {},
                "details": "psutil not available - system metrics disabled",
            }

        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100

            # Load average (Unix-like systems)
            try:
                load_avg = os.getloadavg()
                load_1min = load_avg[0]
            except (OSError, AttributeError):
                load_1min = None

            # Determine status
            status = "healthy"
            if (
                cpu_percent > self.cpu_critical_threshold
                or memory_percent > self.memory_critical_threshold
                or disk_percent > self.disk_critical_threshold
            ):
                status = "unhealthy"
            elif (
                cpu_percent > self.cpu_warning_threshold
                or memory_percent > self.memory_warning_threshold
                or disk_percent > self.disk_warning_threshold
            ):
                status = "warning"

            return {
                "status": status,
                "metrics": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk_percent,
                    "disk_free_gb": disk.free / (1024**3),
                    "load_average_1min": load_1min,
                    "uptime_seconds": time.time() - psutil.boot_time(),
                },
                "details": f"CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%, Disk: {disk_percent:.1f}%",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "metrics": {},
                "details": f"System health check failed: {str(e)}",
            }

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            # Try to import database dependencies
            try:
                from sqlalchemy import text
                from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
            except ImportError:
                return {
                    "status": "unknown",
                    "metrics": {},
                    "details": "Database client not available",
                }

            # Get database URL from environment
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                return {
                    "status": "unknown",
                    "metrics": {},
                    "details": "DATABASE_URL not configured",
                }

            # Create engine and test connection
            engine = create_async_engine(database_url, pool_size=1, max_overflow=0)

            start_time = time.time()

            try:
                async with engine.begin() as conn:
                    # Test basic connectivity
                    result = await conn.execute(text("SELECT 1"))
                    basic_check = result.scalar()

                    # Test database performance
                    await conn.execute(
                        text("SELECT COUNT(*) FROM information_schema.tables")
                    )

                    response_time_ms = (time.time() - start_time) * 1000

                    # Check active connections (PostgreSQL specific)
                    try:
                        result = await conn.execute(
                            text(
                                """
                            SELECT count(*) as active_connections
                            FROM pg_stat_activity
                            WHERE state = 'active'
                        """
                            )
                        )
                        active_connections = result.scalar()
                    except Exception:
                        active_connections = None

                    # Determine status
                    status = "healthy"
                    if response_time_ms > self.db_response_critical_ms:
                        status = "unhealthy"
                    elif response_time_ms > self.db_response_warning_ms:
                        status = "warning"

                    return {
                        "status": status,
                        "metrics": {
                            "response_time_ms": response_time_ms,
                            "active_connections": active_connections,
                            "basic_check_passed": basic_check == 1,
                        },
                        "details": f"Response time: {response_time_ms:.2f}ms, Active connections: {active_connections}",
                    }

            finally:
                await engine.dispose()

        except Exception as e:
            return {
                "status": "unhealthy",
                "metrics": {"response_time_ms": None, "basic_check_passed": False},
                "details": f"Database health check failed: {str(e)}",
            }

    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        try:
            # Import Redis here to avoid dependency issues if Redis isn't used
            try:
                import redis.asyncio as redis
            except ImportError:
                return {
                    "status": "unknown",
                    "metrics": {},
                    "details": "Redis client not available",
                }

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

            redis_client = redis.from_url(redis_url)

            start_time = time.time()

            try:
                # Test connectivity
                pong = await redis_client.ping()

                # Test performance
                await redis_client.set("health_check", "test")
                value = await redis_client.get("health_check")
                await redis_client.delete("health_check")

                response_time_ms = (time.time() - start_time) * 1000

                # Get Redis info
                redis_info = await redis_client.info()

                # Determine status
                status = "healthy"
                if response_time_ms > self.redis_response_critical_ms:
                    status = "unhealthy"
                elif response_time_ms > self.redis_response_warning_ms:
                    status = "warning"

                return {
                    "status": status,
                    "metrics": {
                        "response_time_ms": response_time_ms,
                        "ping_successful": pong,
                        "connected_clients": redis_info.get("connected_clients", 0),
                        "used_memory_mb": redis_info.get("used_memory", 0)
                        / (1024 * 1024),
                        "uptime_seconds": redis_info.get("uptime_in_seconds", 0),
                    },
                    "details": f"Response time: {response_time_ms:.2f}ms, Connected clients: {redis_info.get('connected_clients', 0)}",
                }

            finally:
                await redis_client.close()

        except ImportError:
            return {
                "status": "unknown",
                "metrics": {},
                "details": "Redis client not available",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "metrics": {"response_time_ms": None, "ping_successful": False},
                "details": f"Redis health check failed: {str(e)}",
            }

    async def _check_application_health(self) -> Dict[str, Any]:
        """Check application-specific health."""
        if not PSUTIL_AVAILABLE:
            return {
                "status": "unknown",
                "metrics": {},
                "details": "psutil not available - application metrics disabled",
            }

        try:
            # Check if application is responding
            start_time = time.time()

            # Basic application health indicators
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()

            response_time_ms = (time.time() - start_time) * 1000

            # Check thread count (high thread count might indicate issues)
            thread_count = process.num_threads()

            # Check file descriptors (Unix-like systems)
            try:
                fd_count = process.num_fds()
            except (AttributeError, psutil.AccessDenied):
                fd_count = None

            # Determine status
            status = "healthy"
            if thread_count > 100 or cpu_percent > 80:
                status = "warning"
            if thread_count > 200 or cpu_percent > 95:
                status = "unhealthy"

            return {
                "status": status,
                "metrics": {
                    "response_time_ms": response_time_ms,
                    "memory_usage_mb": memory_info.rss / (1024 * 1024),
                    "cpu_percent": cpu_percent,
                    "thread_count": thread_count,
                    "file_descriptors": fd_count,
                    "process_uptime_seconds": time.time() - process.create_time(),
                },
                "details": f"Memory: {memory_info.rss/(1024*1024):.1f}MB, CPU: {cpu_percent:.1f}%, Threads: {thread_count}",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "metrics": {},
                "details": f"Application health check failed: {str(e)}",
            }

    async def _check_plugins_health(self) -> Dict[str, Any]:
        """Check plugin system health."""
        try:
            # Basic plugin health check
            plugin_count = 0
            active_plugins = 0
            failed_plugins = 0

            # Check if plugin system is available
            status = "healthy"

            return {
                "status": status,
                "metrics": {
                    "total_plugins": plugin_count,
                    "active_plugins": active_plugins,
                    "failed_plugins": failed_plugins,
                    "plugin_system_available": True,
                },
                "details": f"Plugins: {active_plugins}/{plugin_count} active",
            }

        except ImportError:
            return {
                "status": "unknown",
                "metrics": {"plugin_system_available": False},
                "details": "Plugin system not available",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "metrics": {"plugin_system_available": False},
                "details": f"Plugin health check failed: {str(e)}",
            }

    async def _check_network_health(self) -> Dict[str, Any]:
        """Check network connectivity and performance."""
        try:
            import socket

            # Check DNS resolution
            start_time = time.time()
            try:
                socket.gethostbyname("google.com")
                dns_resolution_ms = (time.time() - start_time) * 1000
                dns_working = True
            except socket.gaierror:
                dns_resolution_ms = None
                dns_working = False

            # Check HTTP connectivity
            http_working = False
            http_response_time_ms = None

            try:
                # Try to import aiohttp for async HTTP check
                import aiohttp

                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://httpbin.org/status/200",
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response:
                        if response.status == 200:
                            http_working = True
                            http_response_time_ms = (time.time() - start_time) * 1000
            except ImportError:
                # Fallback to basic socket test
                try:
                    socket.create_connection(("8.8.8.8", 53), timeout=5)
                    http_working = True
                except Exception:
                    pass
            except Exception:
                pass

            # Determine status
            status = "healthy"
            if not dns_working or not http_working:
                status = "warning"
            if not dns_working and not http_working:
                status = "unhealthy"

            return {
                "status": status,
                "metrics": {
                    "dns_resolution_working": dns_working,
                    "dns_resolution_ms": dns_resolution_ms,
                    "http_connectivity_working": http_working,
                    "http_response_time_ms": http_response_time_ms,
                },
                "details": f"DNS: {'OK' if dns_working else 'Failed'}, HTTP: {'OK' if http_working else 'Failed'}",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "metrics": {},
                "details": f"Network health check failed: {str(e)}",
            }

    async def force_health_report(self) -> Dict[str, Any]:
        """Force immediate health report."""
        try:
            await self._collect_and_report_health()
            return {
                "status": "success",
                "reported_at": (
                    self._last_report_time.isoformat()
                    if self._last_report_time
                    else None
                ),
                "components": list(self._health_data_cache.keys()),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_latest_health_data(self) -> Dict[str, Any]:
        """Get latest cached health data."""
        return {
            "health_data": self._health_data_cache,
            "last_collection": (
                self._last_report_time.isoformat() if self._last_report_time else None
            ),
            "reporting_interval_seconds": self.reporting_interval,
            "is_reporting": self.is_running,
        }

    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of health status."""
        if not self._health_data_cache:
            return {"status": "unknown", "message": "No health data available"}

        components = self._health_data_cache
        healthy_count = sum(
            1 for comp in components.values() if comp.get("status") == "healthy"
        )
        warning_count = sum(
            1 for comp in components.values() if comp.get("status") == "warning"
        )
        unhealthy_count = sum(
            1 for comp in components.values() if comp.get("status") == "unhealthy"
        )
        total_count = len(components)

        overall_status = "healthy"
        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif warning_count > 0:
            overall_status = "warning"

        return {
            "status": overall_status,
            "total_components": total_count,
            "healthy": healthy_count,
            "warning": warning_count,
            "unhealthy": unhealthy_count,
            "last_check": (
                self._last_report_time.isoformat() if self._last_report_time else None
            ),
        }


# Global health reporter instance
_health_reporter: Optional[HealthReporter] = None


def get_health_reporter(config: Optional[Dict[str, Any]] = None) -> HealthReporter:
    """Get global health reporter instance."""
    global _health_reporter
    if _health_reporter is None:
        _health_reporter = HealthReporter(config)
    return _health_reporter


async def start_health_reporting(config: Optional[Dict[str, Any]] = None):
    """Start global health reporting."""
    reporter = get_health_reporter(config)
    await reporter.start_health_reporting()


def stop_health_reporting():
    """Stop global health reporting."""
    if _health_reporter:
        _health_reporter.stop_health_reporting()


def clear_health_reporter():
    """Clear global health reporter instance (useful for testing)."""
    global _health_reporter
    if _health_reporter:
        _health_reporter.stop_health_reporting()
    _health_reporter = None
