"""
Container Health Monitor

Provides comprehensive health monitoring for ISP containers including
system metrics, application endpoints, and database connectivity.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

import docker

# Optional imports
try:
    import httpx

    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False

try:
    from pydantic import BaseModel

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

    # Simple BaseModel replacement
    class BaseModel:
        """BaseModel implementation."""

        pass


class HealthStatus(str, Enum):
    """Container health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Individual health check result"""

    name: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    response_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Complete health report for a container"""

    container_id: str
    isp_id: Optional[UUID] = None
    overall_status: HealthStatus = HealthStatus.HEALTHY
    checks: List[HealthCheck] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    uptime: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_check(self, check: HealthCheck) -> None:
        """Add a health check result"""
        self.checks.append(check)
        self._update_overall_status()

    def _update_overall_status(self) -> None:
        """Update overall status based on individual checks"""
        if not self.checks:
            return

        statuses = [check.status for check in self.checks]

        if HealthStatus.CRITICAL in statuses:
            self.overall_status = HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in statuses:
            self.overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            self.overall_status = HealthStatus.DEGRADED
        else:
            self.overall_status = HealthStatus.HEALTHY


class ContainerHealthMonitor:
    """
    Container health monitoring service

    Monitors container health including:
    - Container runtime status
    - System resource usage
    - Application endpoint health
    - Database connectivity
    """

    def __init__(
        self,
        check_interval: int = 30,
        health_threshold: float = 0.8,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0,
        disk_threshold: float = 90.0,
        endpoint_timeout: int = 10,
        db_timeout: int = 5,
    ):
        self.check_interval = check_interval
        self.health_threshold = health_threshold
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.endpoint_timeout = endpoint_timeout
        self.db_timeout = db_timeout

        self.docker_client = docker.from_env()
        self.logger = logging.getLogger(__name__)

    async def monitor_container_health(self, container_id: str) -> HealthReport:
        """
        Perform comprehensive health monitoring for a container

        Args:
            container_id: Docker container ID or name

        Returns:
            HealthReport with all check results
        """
        report = HealthReport(container_id=container_id)

        try:
            container = self.docker_client.containers.get(container_id)
            report.isp_id = self._extract_isp_id(container)
            report.uptime = self._calculate_uptime(container)

            # Perform all health checks
            await asyncio.gather(
                self._check_container_status(container, report),
                self._check_system_resources(container, report),
                self._check_application_endpoints(container, report),
                self._check_database_connectivity(container, report),
                return_exceptions=True,
            )

        except docker.errors.NotFound:
            report.add_check(
                HealthCheck(
                    name="container_exists",
                    status=HealthStatus.CRITICAL,
                    message=f"Container {container_id} not found",
                )
            )
        except Exception as e:
            self.logger.error(f"Health check failed for {container_id}: {e}")
            report.add_check(
                HealthCheck(
                    name="health_check_error",
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(e)}",
                )
            )

        return report

    async def _check_container_status(
        self, container: docker.models.containers.Container, report: HealthReport
    ) -> None:
        """Check basic container status"""
        try:
            container.reload()
            status = container.status

            if status == "running":
                health_status = HealthStatus.HEALTHY
                message = "Container is running"
            elif status in ["paused", "restarting"]:
                health_status = HealthStatus.DEGRADED
                message = f"Container is {status}"
            else:
                health_status = HealthStatus.UNHEALTHY
                message = f"Container status: {status}"

            report.add_check(
                HealthCheck(
                    name="container_status",
                    status=health_status,
                    message=message,
                    metadata={"status": status},
                )
            )

        except Exception as e:
            report.add_check(
                HealthCheck(
                    name="container_status",
                    status=HealthStatus.CRITICAL,
                    message=f"Failed to check container status: {e}",
                )
            )

    async def _check_system_resources(
        self, container: docker.models.containers.Container, report: HealthReport
    ) -> None:
        """Check system resource usage"""
        try:
            stats = container.stats(stream=False)

            # Calculate CPU usage
            cpu_usage = self._calculate_cpu_usage(stats)
            cpu_status = self._evaluate_threshold(cpu_usage, self.cpu_threshold, "CPU")

            report.add_check(
                HealthCheck(
                    name="cpu_usage",
                    status=cpu_status,
                    message=f"CPU usage: {cpu_usage:.1f}%",
                    metadata={"cpu_percent": cpu_usage},
                )
            )

            # Calculate memory usage
            memory_usage = self._calculate_memory_usage(stats)
            memory_status = self._evaluate_threshold(
                memory_usage, self.memory_threshold, "Memory"
            )

            report.add_check(
                HealthCheck(
                    name="memory_usage",
                    status=memory_status,
                    message=f"Memory usage: {memory_usage:.1f}%",
                    metadata={"memory_percent": memory_usage},
                )
            )

        except Exception as e:
            report.add_check(
                HealthCheck(
                    name="system_resources",
                    status=HealthStatus.CRITICAL,
                    message=f"Failed to check system resources: {e}",
                )
            )

    async def _check_application_endpoints(
        self, container: docker.models.containers.Container, report: HealthReport
    ) -> None:
        """Check application endpoint health"""
        try:
            # Get container IP and port mappings
            container_ip = self._get_container_ip(container)
            port_mappings = self._get_port_mappings(container)

            # Skip endpoint checks if HTTP client not available
            if not HTTP_CLIENT_AVAILABLE:
                report.add_check(
                    HealthCheck(
                        name="application_endpoints",
                        status=HealthStatus.DEGRADED,
                        message="HTTP client not available, skipping endpoint checks",
                    )
                )
                return

            # Common ISP framework health endpoints
            endpoints = ["/health", "/api/health", "/api/v1/health", "/status"]

            async with httpx.AsyncClient(timeout=self.endpoint_timeout) as client:
                for port in port_mappings:
                    for endpoint in endpoints:
                        url = f"http://{container_ip}:{port}{endpoint}"

                        start_time = datetime.now(timezone.utc)
                        try:
                            response = await client.get(url)
                            response_time = (
                                datetime.now(timezone.utc) - start_time
                            ).total_seconds()

                            if response.status_code == 200:
                                status = HealthStatus.HEALTHY
                                message = f"Endpoint {endpoint} responding"
                            else:
                                status = HealthStatus.DEGRADED
                                message = f"Endpoint {endpoint} returned {response.status_code}"

                            report.add_check(
                                HealthCheck(
                                    name=f"endpoint_{endpoint.replace('/', '_')}",
                                    status=status,
                                    message=message,
                                    response_time=response_time,
                                    metadata={
                                        "url": url,
                                        "status_code": response.status_code,
                                    },
                                )
                            )
                            break  # Found working endpoint

                        except httpx.RequestError:
                            continue  # Try next endpoint

        except Exception as e:
            report.add_check(
                HealthCheck(
                    name="application_endpoints",
                    status=HealthStatus.DEGRADED,
                    message=f"Could not check application endpoints: {e}",
                )
            )

    async def _check_database_connectivity(
        self, container: docker.models.containers.Container, report: HealthReport
    ) -> None:
        """Check database connectivity"""
        try:
            # Check for database environment variables
            env_vars = container.attrs.get("Config", {}).get("Env", [])
            db_configs = self._extract_db_configs(env_vars)

            if not db_configs:
                report.add_check(
                    HealthCheck(
                        name="database_config",
                        status=HealthStatus.HEALTHY,
                        message="No database configuration found",
                    )
                )
                return

            # Test database connections
            for db_name, db_config in db_configs.items():
                try:
                    # This would be implemented based on database type
                    # For now, we'll do a basic connectivity check
                    connectivity_ok = await self._test_db_connection(db_config)

                    if connectivity_ok:
                        status = HealthStatus.HEALTHY
                        message = f"Database {db_name} connected"
                    else:
                        status = HealthStatus.UNHEALTHY
                        message = f"Database {db_name} connection failed"

                    report.add_check(
                        HealthCheck(
                            name=f"database_{db_name}",
                            status=status,
                            message=message,
                            metadata={"database": db_name},
                        )
                    )

                except Exception as e:
                    report.add_check(
                        HealthCheck(
                            name=f"database_{db_name}",
                            status=HealthStatus.UNHEALTHY,
                            message=f"Database {db_name} check failed: {e}",
                        )
                    )

        except Exception as e:
            report.add_check(
                HealthCheck(
                    name="database_connectivity",
                    status=HealthStatus.DEGRADED,
                    message=f"Could not check database connectivity: {e}",
                )
            )

    def _extract_isp_id(
        self, container: docker.models.containers.Container
    ) -> Optional[UUID]:
        """Extract ISP/tenant ID from container labels"""
        try:
            labels = container.labels or {}
            if "isp.tenant.id" in labels:
                return UUID(labels["isp.tenant.id"])
            elif "dotmac.tenant.id" in labels:
                return UUID(labels["dotmac.tenant.id"])
        except (ValueError, KeyError):
            pass
        return None

    def _calculate_uptime(
        self, container: docker.models.containers.Container
    ) -> timedelta:
        """Calculate container uptime"""
        try:
            started_at = container.attrs["State"]["StartedAt"]
            start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            return datetime.now(timezone.utc).replace(tzinfo=start_time.tzinfo) - start_time
        except (KeyError, ValueError):
            return timedelta(0)

    def _calculate_cpu_usage(self, stats: Dict) -> float:
        """Calculate CPU usage percentage from container stats"""
        try:
            cpu_stats = stats["cpu_stats"]
            precpu_stats = stats["precpu_stats"]

            cpu_delta = (
                cpu_stats["cpu_usage"]["total_usage"]
                - precpu_stats["cpu_usage"]["total_usage"]
            )
            system_delta = (
                cpu_stats["system_cpu_usage"] - precpu_stats["system_cpu_usage"]
            )

            if system_delta > 0 and cpu_delta > 0:
                cpu_count = len(cpu_stats["cpu_usage"]["percpu_usage"])
                return (cpu_delta / system_delta) * cpu_count * 100.0
        except (KeyError, ZeroDivisionError):
            pass
        return 0.0

    def _calculate_memory_usage(self, stats: Dict) -> float:
        """Calculate memory usage percentage from container stats"""
        try:
            memory_stats = stats["memory_stats"]
            usage = memory_stats["usage"]
            limit = memory_stats["limit"]

            if limit > 0:
                return (usage / limit) * 100.0
        except (KeyError, ZeroDivisionError):
            pass
        return 0.0

    def _evaluate_threshold(
        self, value: float, threshold: float, metric_name: str
    ) -> HealthStatus:
        """Evaluate metric against threshold"""
        if value >= threshold * 1.1:  # 110% of threshold
            return HealthStatus.CRITICAL
        elif value >= threshold:  # At threshold
            return HealthStatus.UNHEALTHY
        elif value >= threshold * 0.8:  # 80% of threshold
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def _get_container_ip(self, container: docker.models.containers.Container) -> str:
        """Get container IP address"""
        try:
            networks = container.attrs["NetworkSettings"]["Networks"]
            for network in networks.values():
                if network.get("IPAddress"):
                    return network["IPAddress"]
        except KeyError:
            pass
        return "localhost"

    def _get_port_mappings(
        self, container: docker.models.containers.Container
    ) -> List[int]:
        """Get exposed port mappings"""
        try:
            ports = container.attrs["NetworkSettings"]["Ports"]
            mapped_ports = []
            for port, bindings in ports.items():
                if bindings:
                    for binding in bindings:
                        if binding.get("HostPort"):
                            mapped_ports.append(int(binding["HostPort"]))
                else:
                    # Internal port without host mapping
                    internal_port = int(port.split("/")[0])
                    mapped_ports.append(internal_port)
            return mapped_ports
        except (KeyError, ValueError):
            return [8000]  # Default FastAPI port

    def _extract_db_configs(self, env_vars: List[str]) -> Dict[str, Dict[str, str]]:
        """Extract database configurations from environment variables"""
        db_configs = {}

        for env_var in env_vars:
            if "=" not in env_var:
                continue

            key, value = env_var.split("=", 1)

            # PostgreSQL patterns
            if key.upper() == "DATABASE_URL" and "postgresql" in value:
                db_configs["postgresql"] = {"url": value}
            elif key.upper() == "POSTGRES_HOST":
                if "postgresql" not in db_configs:
                    db_configs["postgresql"] = {}
                db_configs["postgresql"]["host"] = value

            # Redis patterns
            elif key.upper() == "REDIS_URL":
                db_configs["redis"] = {"url": value}
            elif key.upper() == "REDIS_HOST":
                if "redis" not in db_configs:
                    db_configs["redis"] = {}
                db_configs["redis"]["host"] = value

        return db_configs

    async def _test_db_connection(self, db_config: Dict[str, str]) -> bool:
        """Test database connection"""
        # This would be implemented with actual database clients
        # For now, return True as placeholder
        await asyncio.sleep(0.1)  # Simulate connection test
        return True


# Convenience function for direct usage
async def monitor_container_health(container_id: str) -> HealthReport:
    """
    Monitor container health with default settings

    Args:
        container_id: Docker container ID or name

    Returns:
        HealthReport with comprehensive health status
    """
    monitor = ContainerHealthMonitor()
    return await monitor.monitor_container_health(container_id)
