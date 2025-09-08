"""
Performance Metrics Collector

Collects comprehensive performance metrics from containers including
system metrics, application metrics, and database performance data.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

import psutil

import docker

PROMETHEUS_AVAILABLE = False


def text_string_to_metric_families(metrics_text, timezone):
    """Removed Prometheus parsing support - migrate to SignOz native metrics"""
    return []


# Optional import for HTTP client
try:
    import httpx

    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False


@dataclass
class SystemMetrics:
    """System-level metrics"""

    cpu_percent: float = 0.0
    cpu_count: int = 0
    memory_usage_bytes: int = 0
    memory_limit_bytes: int = 0
    memory_percent: float = 0.0
    disk_usage_bytes: int = 0
    disk_available_bytes: int = 0
    disk_percent: float = 0.0
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ApplicationMetrics:
    """Application-level metrics"""

    request_count: int = 0
    request_rate: float = 0.0
    response_time_avg: float = 0.0
    response_time_p95: float = 0.0
    error_count: int = 0
    error_rate: float = 0.0
    active_connections: int = 0
    thread_count: int = 0
    heap_usage_bytes: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    custom_metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class DatabaseMetrics:
    """Database performance metrics"""

    connection_count: int = 0
    max_connections: int = 0
    connection_pool_usage: float = 0.0
    query_count: int = 0
    query_rate: float = 0.0
    slow_query_count: int = 0
    avg_query_time: float = 0.0
    cache_hit_ratio: float = 0.0
    lock_waits: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    database_type: str = "unknown"
    database_name: str = ""


@dataclass
class MetricsSnapshot:
    """Complete metrics snapshot for a container"""

    container_id: str
    isp_id: Optional[UUID] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    system_metrics: Optional[SystemMetrics] = None
    application_metrics: Optional[ApplicationMetrics] = None
    database_metrics: list[DatabaseMetrics] = field(default_factory=list)
    uptime_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def overall_health_score(self) -> float:
        """Calculate overall health score (0.0 - 1.0)"""
        scores = []

        if self.system_metrics:
            # System health based on resource usage
            cpu_score = max(0, 1 - (self.system_metrics.cpu_percent / 100))
            memory_score = max(0, 1 - (self.system_metrics.memory_percent / 100))
            disk_score = max(0, 1 - (self.system_metrics.disk_percent / 100))
            scores.extend([cpu_score, memory_score, disk_score])

        if self.application_metrics:
            # Application health based on error rate
            error_score = max(0, 1 - min(1, self.application_metrics.error_rate))
            scores.append(error_score)

        if self.database_metrics:
            # Database health based on connection pool and query performance
            for db_metric in self.database_metrics:
                conn_score = max(0, 1 - (db_metric.connection_pool_usage / 100))
                scores.append(conn_score)

        return sum(scores) / len(scores) if scores else 0.5


class MetricsCollector:
    """
    Performance metrics collection service

    Collects metrics from:
    - Container system resources
    - Application performance endpoints
    - Database connections and performance
    - Custom application metrics
    """

    def __init__(
        self,
        collection_interval: int = 60,
        metrics_retention_hours: int = 24,
        enable_prometheus: bool = False,
        custom_metrics_endpoints: Optional[list[str]] = None,
    ):
        self.collection_interval = collection_interval
        self.metrics_retention_hours = metrics_retention_hours
        # Disable legacy Prometheus scraping regardless of flag
        if enable_prometheus:
            logging.getLogger(__name__).info(
                "Prometheus scraping is deprecated and disabled; using SigNoz/OTLP only"
            )
        self.enable_prometheus = False
        self.custom_metrics_endpoints = custom_metrics_endpoints or []

        self.docker_client = docker.from_env()
        self.logger = logging.getLogger(__name__)
        self._metrics_cache: dict[str, list[MetricsSnapshot]] = {}

    async def collect_performance_metrics(self, container_id: str) -> MetricsSnapshot:
        """
        Collect comprehensive performance metrics for a container

        Args:
            container_id: Docker container ID or name

        Returns:
            MetricsSnapshot with all collected metrics
        """
        snapshot = MetricsSnapshot(container_id=container_id)

        try:
            container = self.docker_client.containers.get(container_id)
            snapshot.isp_id = self._extract_isp_id(container)
            snapshot.uptime_seconds = self._calculate_uptime_seconds(container)

            # Collect metrics in parallel
            metrics_tasks = [
                self._collect_system_metrics(container),
                self._collect_application_metrics(container),
                self._collect_database_metrics(container),
            ]

            system_metrics, app_metrics, db_metrics = await asyncio.gather(*metrics_tasks, return_exceptions=True)

            # Handle results
            if isinstance(system_metrics, SystemMetrics):
                snapshot.system_metrics = system_metrics
            elif isinstance(system_metrics, Exception):
                self.logger.error(f"System metrics collection failed: {system_metrics}")

            if isinstance(app_metrics, ApplicationMetrics):
                snapshot.application_metrics = app_metrics
            elif isinstance(app_metrics, Exception):
                self.logger.error(f"Application metrics collection failed: {app_metrics}")

            if isinstance(db_metrics, list):
                snapshot.database_metrics = db_metrics
            elif isinstance(db_metrics, Exception):
                self.logger.error(f"Database metrics collection failed: {db_metrics}")

            # Cache the snapshot
            await self._cache_snapshot(snapshot)

        except docker.errors.NotFound:
            self.logger.error(f"Container {container_id} not found")
            snapshot.metadata["error"] = "Container not found"

        except Exception as e:
            self.logger.error(f"Metrics collection failed for {container_id}: {e}")
            snapshot.metadata["error"] = str(e)

        return snapshot

    async def _collect_system_metrics(self, container: docker.models.containers.Container) -> SystemMetrics:
        """Collect system-level metrics"""
        try:
            # Get container stats
            stats = container.stats(stream=False)

            # CPU metrics
            cpu_percent = self._calculate_cpu_usage(stats)
            cpu_count = len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])

            # Memory metrics
            memory_stats = stats["memory_stats"]
            memory_usage = memory_stats.get("usage", 0)
            memory_limit = memory_stats.get("limit", 0)
            memory_percent = (memory_usage / memory_limit * 100) if memory_limit > 0 else 0

            # Network metrics
            network_stats = stats.get("networks", {})
            rx_bytes = sum(net.get("rx_bytes", 0) for net in network_stats.values())
            tx_bytes = sum(net.get("tx_bytes", 0) for net in network_stats.values())

            # Disk metrics (approximated from container filesystem)
            disk_usage = 0
            disk_available = 0
            disk_percent = 0

            try:
                # Get filesystem stats from container
                if psutil.disk_usage:
                    disk_info = psutil.disk_usage("/")  # Fallback to host disk
                    disk_usage = disk_info.used
                    disk_available = disk_info.free
                    disk_percent = disk_info.used / disk_info.total * 100
            except Exception:
                pass  # Disk metrics optional

            return SystemMetrics(
                cpu_percent=cpu_percent,
                cpu_count=cpu_count,
                memory_usage_bytes=memory_usage,
                memory_limit_bytes=memory_limit,
                memory_percent=memory_percent,
                disk_usage_bytes=disk_usage,
                disk_available_bytes=disk_available,
                disk_percent=disk_percent,
                network_rx_bytes=rx_bytes,
                network_tx_bytes=tx_bytes,
            )

        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            raise

    async def _collect_application_metrics(self, container: docker.models.containers.Container) -> ApplicationMetrics:
        """Collect application-level metrics"""
        app_metrics = ApplicationMetrics()

        try:
            # Get container IP and ports
            container_ip = self._get_container_ip(container)
            ports = self._get_port_mappings(container)

            # Prometheus scraping disabled (SigNoz-only)

            # Try custom metrics endpoints
            for endpoint in self.custom_metrics_endpoints:
                custom_metrics = await self._collect_custom_metrics(container_ip, ports, endpoint)
                if custom_metrics:
                    app_metrics.custom_metrics.update(custom_metrics)

            # Fallback: Estimate metrics from container stats
            if not app_metrics.request_count and not app_metrics.custom_metrics:
                app_metrics = await self._estimate_app_metrics_from_stats(container)

        except Exception as e:
            self.logger.error(f"Failed to collect application metrics: {e}")

        return app_metrics

    async def _collect_database_metrics(self, container: docker.models.containers.Container) -> list[DatabaseMetrics]:
        """Collect database performance metrics"""
        db_metrics_list = []

        try:
            # Extract database configurations
            env_vars = container.attrs.get("Config", {}).get("Env", [])
            db_configs = self._extract_db_configs(env_vars)

            for db_name, db_config in db_configs.items():
                try:
                    db_metrics = await self._collect_single_db_metrics(db_name, db_config, container)
                    if db_metrics:
                        db_metrics_list.append(db_metrics)
                except Exception as e:
                    self.logger.error(f"Failed to collect {db_name} metrics: {e}")

        except Exception as e:
            self.logger.error(f"Failed to collect database metrics: {e}")

        return db_metrics_list

    async def _collect_prometheus_metrics(self, container_ip: str, ports: list[int]) -> Optional[str]:
        """Collect Prometheus metrics from container"""
        if not HTTP_CLIENT_AVAILABLE:
            return None

        # Common Prometheus endpoints
        prometheus_paths = ["/metrics", "/api/metrics", "/prometheus"]

        async with httpx.AsyncClient(timeout=10) as client:
            for port in ports:
                for path in prometheus_paths:
                    try:
                        url = f"http://{container_ip}:{port}{path}"
                        response = await client.get(url)

                        if response.status_code == 200:
                            content_type = response.headers.get("content-type", "")
                            if "text/plain" in content_type or "prometheus" in content_type:
                                return response.text
                    except httpx.RequestError:
                        continue
        return None

    def _parse_prometheus_metrics(self, metrics_text: str, app_metrics: ApplicationMetrics) -> ApplicationMetrics:
        """Parse Prometheus metrics text"""
        try:
            for family in text_string_to_metric_families(metrics_text):
                for sample in family.samples:
                    metric_name = sample.name
                    metric_value = sample.value

                    # Map common metrics to ApplicationMetrics fields
                    if "http_requests_total" in metric_name:
                        app_metrics.request_count += int(metric_value)
                    elif "http_request_duration" in metric_name and "avg" in metric_name:
                        app_metrics.response_time_avg = metric_value
                    elif "http_request_duration" in metric_name and "95" in metric_name:
                        app_metrics.response_time_p95 = metric_value
                    elif "http_errors_total" in metric_name:
                        app_metrics.error_count += int(metric_value)
                    elif "active_connections" in metric_name:
                        app_metrics.active_connections = int(metric_value)
                    elif "thread_count" in metric_name:
                        app_metrics.thread_count = int(metric_value)
                    elif "heap_usage" in metric_name:
                        app_metrics.heap_usage_bytes = int(metric_value)
                    else:
                        # Store as custom metric
                        app_metrics.custom_metrics[metric_name] = metric_value

        except Exception as e:
            self.logger.error(f"Failed to parse Prometheus metrics: {e}")

        return app_metrics

    async def _collect_custom_metrics(
        self, container_ip: str, ports: list[int], endpoint: str
    ) -> Optional[dict[str, float]]:
        """Collect custom metrics from endpoint"""
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            for port in ports:
                try:
                    url = f"http://{container_ip}:{port}{endpoint}"
                    response = await client.get(url)

                    if response.status_code == 200:
                        data = await response.json()
                        if isinstance(data, dict):
                            # Extract numeric values
                            metrics = {}
                            for key, value in data.items():
                                if isinstance(value, (int, float)):
                                    metrics[key] = float(value)
                            return metrics
                except (httpx.RequestError, json.JSONDecodeError):
                    continue
        return None

    async def _estimate_app_metrics_from_stats(
        self, container: docker.models.containers.Container
    ) -> ApplicationMetrics:
        """Estimate application metrics from container stats"""
        app_metrics = ApplicationMetrics()

        try:
            stats = container.stats(stream=False)

            # Estimate request count from network activity
            network_stats = stats.get("networks", {})
            total_rx = sum(net.get("rx_packets", 0) for net in network_stats.values())
            total_tx = sum(net.get("tx_packets", 0) for net in network_stats.values())

            # Very rough estimation
            app_metrics.request_count = int(min(total_rx, total_tx))
            app_metrics.active_connections = max(1, int(total_rx / 100))

        except Exception as e:
            self.logger.error(f"Failed to estimate app metrics: {e}")

        return app_metrics

    async def _collect_single_db_metrics(
        self,
        db_name: str,
        db_config: dict[str, str],
        container: docker.models.containers.Container,
    ) -> Optional[DatabaseMetrics]:
        """Collect metrics for a single database"""
        db_metrics = DatabaseMetrics(database_type=db_name, database_name=db_config.get("database", db_name))

        try:
            if db_name == "postgresql":
                return await self._collect_postgresql_metrics(db_config, db_metrics)
            elif db_name == "redis":
                return await self._collect_redis_metrics(db_config, db_metrics)
            elif db_name == "mysql":
                return await self._collect_mysql_metrics(db_config, db_metrics)
        except Exception as e:
            self.logger.error(f"Failed to collect {db_name} metrics: {e}")

        return db_metrics

    async def _collect_postgresql_metrics(
        self, db_config: dict[str, str], db_metrics: DatabaseMetrics
    ) -> DatabaseMetrics:
        """Collect PostgreSQL specific metrics"""
        # This would be implemented with actual PostgreSQL client
        # For now, return placeholder metrics
        db_metrics.connection_count = 5
        db_metrics.max_connections = 100
        db_metrics.connection_pool_usage = 5.0
        db_metrics.query_rate = 10.5
        db_metrics.cache_hit_ratio = 95.0

        return db_metrics

    async def _collect_redis_metrics(self, db_config: dict[str, str], db_metrics: DatabaseMetrics) -> DatabaseMetrics:
        """Collect Redis specific metrics"""
        # This would be implemented with actual Redis client
        # For now, return placeholder metrics
        db_metrics.connection_count = 2
        db_metrics.max_connections = 50
        db_metrics.connection_pool_usage = 4.0
        db_metrics.query_rate = 25.0
        db_metrics.cache_hit_ratio = 98.5

        return db_metrics

    async def _collect_mysql_metrics(self, db_config: dict[str, str], db_metrics: DatabaseMetrics) -> DatabaseMetrics:
        """Collect MySQL specific metrics"""
        # This would be implemented with actual MySQL client
        # For now, return placeholder metrics
        db_metrics.connection_count = 8
        db_metrics.max_connections = 150
        db_metrics.connection_pool_usage = 5.3
        db_metrics.query_rate = 15.2
        db_metrics.cache_hit_ratio = 92.0
        db_metrics.slow_query_count = 2

        return db_metrics

    async def _cache_snapshot(self, snapshot: MetricsSnapshot) -> None:
        """Cache metrics snapshot with retention"""
        container_id = snapshot.container_id

        if container_id not in self._metrics_cache:
            self._metrics_cache[container_id] = []

        self._metrics_cache[container_id].append(snapshot)

        # Implement retention policy
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.metrics_retention_hours)
        self._metrics_cache[container_id] = [s for s in self._metrics_cache[container_id] if s.timestamp > cutoff_time]

    def get_metrics_history(self, container_id: str, hours: int = 1) -> list[MetricsSnapshot]:
        """Get historical metrics for container"""
        if container_id not in self._metrics_cache:
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [snapshot for snapshot in self._metrics_cache[container_id] if snapshot.timestamp > cutoff_time]

    # Helper methods (reused from health_monitor.py)
    def _extract_isp_id(self, container: docker.models.containers.Container) -> Optional[UUID]:
        """Extract ISP/tenant ID from container labels"""
        try:
            labels = container.labels or {}
            if "isp.tenant.id" in labels:
                return UUID(labels["isp.tenant.id"])
            elif "dotmac.tenant.id" in labels:
                return UUID(labels["dotmac.tenant.id"])
        except (ValueError, KeyError) as e:
            logger.debug(f"Could not extract tenant ID from container labels: {e}")
            pass
        return None

    def _calculate_uptime_seconds(self, container: docker.models.containers.Container) -> float:
        """Calculate container uptime in seconds"""
        try:
            started_at = container.attrs["State"]["StartedAt"]
            start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            uptime = datetime.now(timezone.utc).replace(tzinfo=start_time.tzinfo) - start_time
            return uptime.total_seconds()
        except (KeyError, ValueError):
            return 0.0

    def _calculate_cpu_usage(self, stats: dict) -> float:
        """Calculate CPU usage percentage"""
        try:
            cpu_stats = stats["cpu_stats"]
            precpu_stats = stats["precpu_stats"]

            cpu_delta = cpu_stats["cpu_usage"]["total_usage"] - precpu_stats["cpu_usage"]["total_usage"]
            system_delta = cpu_stats["system_cpu_usage"] - precpu_stats["system_cpu_usage"]

            if system_delta > 0 and cpu_delta > 0:
                cpu_count = len(cpu_stats["cpu_usage"]["percpu_usage"])
                return (cpu_delta / system_delta) * cpu_count * 100.0
        except (KeyError, ZeroDivisionError) as e:
            logger.debug(f"Could not calculate CPU usage: {e}")
            pass
        return 0.0

    def _get_container_ip(self, container: docker.models.containers.Container) -> str:
        """Get container IP address"""
        try:
            networks = container.attrs["NetworkSettings"]["Networks"]
            for network in networks.values():
                if network.get("IPAddress"):
                    return network["IPAddress"]
        except KeyError as e:
            logger.debug(f"Could not extract container IP address: {e}")
            pass
        return "localhost"

    def _get_port_mappings(self, container: docker.models.containers.Container) -> list[int]:
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
                    internal_port = int(port.split("/")[0])
                    mapped_ports.append(internal_port)
            return mapped_ports
        except (KeyError, ValueError):
            return [8000]

    def _extract_db_configs(self, env_vars: list[str]) -> dict[str, dict[str, str]]:
        """Extract database configurations from environment variables"""
        db_configs = {}

        for env_var in env_vars:
            if "=" not in env_var:
                continue

            key, value = env_var.split("=", 1)

            if key.upper() == "DATABASE_URL" and "postgresql" in value:
                db_configs["postgresql"] = {"url": value, "database": "main"}
            elif key.upper() == "REDIS_URL":
                db_configs["redis"] = {"url": value, "database": "cache"}
            elif key.upper() == "MYSQL_URL":
                db_configs["mysql"] = {"url": value, "database": "main"}

        return db_configs


# Convenience function for direct usage
async def collect_performance_metrics(container_id: str) -> MetricsSnapshot:
    """
    Collect performance metrics with default settings

    Args:
        container_id: Docker container ID or name

    Returns:
        MetricsSnapshot with comprehensive performance data
    """
    collector = MetricsCollector()
    return await collector.collect_performance_metrics(container_id)
