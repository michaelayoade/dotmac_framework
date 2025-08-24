"""Health status reporter for cross-platform monitoring."""

import asyncio
import logging
import os
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from dotmac_isp.core.database import get_async_session
from dotmac_isp.core.management_platform_client import get_management_client


logger = logging.getLogger(__name__)


class HealthReporter:
    """Service for reporting health status to Management Platform."""

    def __init__(self):
        """  Init   operation."""
        self.tenant_id = os.getenv("ISP_TENANT_ID")
        self.reporting_interval = int(
            os.getenv("HEALTH_REPORTING_INTERVAL", "60")
        )  # seconds
        self.is_running = False
        self._health_data_cache = {}
        self._last_report_time = None

    async def start_health_reporting(self):
        """Start background health reporting task."""
        if self.is_running:
            return

        self.is_running = True
        logger.info("Starting health reporting to Management Platform")

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
        """Collect health data and report to Management Platform."""
        try:
            if not self.tenant_id:
                logger.warning("No tenant ID configured - skipping health reporting")
                return

            # Collect health data for all components
            health_data = await self._collect_comprehensive_health_data()

            # Cache the data
            self._health_data_cache = health_data
            self._last_report_time = datetime.utcnow()

            # Report each component to Management Platform
            management_client = await get_management_client()

            for component_name, component_data in health_data.items():
                try:
                    await management_client.report_health_status(
                        component=component_name,
                        status=component_data["status"],
                        metrics=component_data["metrics"],
                        details=component_data.get("details"),
                    )
                except Exception as e:
                    logger.warning(f"Failed to report health for {component_name}: {e}")

            logger.debug(f"Health reported for {len(health_data)} components")

        except Exception as e:
            logger.error(f"Error collecting and reporting health: {e}")

    async def _collect_comprehensive_health_data(self) -> Dict[str, Dict[str, Any]]:
        """Collect comprehensive health data for all components."""
        health_data = {}

        # System health
        health_data["system"] = await self._check_system_health()

        # Database health
        health_data["database"] = await self._check_database_health()

        # Redis health
        health_data["redis"] = await self._check_redis_health()

        # Application health
        health_data["application"] = await self._check_application_health()

        # Plugin health
        health_data["plugins"] = await self._check_plugins_health()

        # Network health
        health_data["network"] = await self._check_network_health()

        return health_data

    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system resource health."""
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
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                status = "unhealthy"
            elif cpu_percent > 70 or memory_percent > 70 or disk_percent > 80:
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
            async with get_async_session() as session:
                start_time = time.time()

                # Test basic connectivity
                result = await session.execute(text("SELECT 1"))
                basic_check = result.scalar()

                # Test database performance
                await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables")
                )

                response_time_ms = (time.time() - start_time) * 1000

                # Check active connections
                result = await session.execute(
                    text(
                        """
                    SELECT count(*) as active_connections 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """
                    )
                )
                active_connections = result.scalar()

                # Determine status
                status = "healthy"
                if response_time_ms > 5000:  # 5 seconds
                    status = "unhealthy"
                elif response_time_ms > 1000:  # 1 second
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
            import redis.asyncio as redis

            redis_url = os.getenv("REDIS_URL", "redis://:dotmac_redis_password@redis-shared:6379/0")

            redis_client = redis.from_url(redis_url)

            start_time = time.time()

            # Test connectivity
            pong = await redis_client.ping()

            # Test performance
            await redis_client.set("health_check", "test")
            value = await redis_client.get("health_check")
            await redis_client.delete("health_check")

            response_time_ms = (time.time() - start_time) * 1000

            # Get Redis info
            redis_info = await redis_client.info()

            await redis_client.close()

            # Determine status
            status = "healthy"
            if response_time_ms > 1000:  # 1 second
                status = "unhealthy"
            elif response_time_ms > 100:  # 100ms
                status = "warning"

            return {
                "status": status,
                "metrics": {
                    "response_time_ms": response_time_ms,
                    "ping_successful": pong,
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "used_memory_mb": redis_info.get("used_memory", 0) / (1024 * 1024),
                    "uptime_seconds": redis_info.get("uptime_in_seconds", 0),
                },
                "details": f"Response time: {response_time_ms:.2f}ms, Connected clients: {redis_info.get('connected_clients', 0)}",
            }

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
            # Import plugin manager
            from dotmac_isp.plugins.core.manager import PluginManager

            # This would typically use a global plugin manager instance
            # For now, we'll create a basic health check

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
            import aiohttp

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
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://httpbin.org/status/200",
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response:
                        if response.status == 200:
                            http_working = True
                            http_response_time_ms = (time.time() - start_time) * 1000
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


# Global health reporter instance
_health_reporter: Optional[HealthReporter] = None


def get_health_reporter() -> HealthReporter:
    """Get global health reporter instance."""
    global _health_reporter
    if _health_reporter is None:
        _health_reporter = HealthReporter()
    return _health_reporter


async def start_health_reporting():
    """Start global health reporting."""
    reporter = get_health_reporter()
    await reporter.start_health_reporting()


def stop_health_reporting():
    """Stop global health reporting."""
    reporter = get_health_reporter()
    reporter.stop_health_reporting()
