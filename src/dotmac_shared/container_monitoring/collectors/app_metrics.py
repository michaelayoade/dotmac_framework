"""
Application Metrics Collector

Collects application-specific metrics from ISP framework containers including:
- HTTP request/response metrics
- API endpoint performance
- Error rates and types
- Custom business metrics
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Union

import docker
from docker.models.containers import Container

try:
    import httpx

    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False


@dataclass
class EndpointMetrics:
    """Metrics for a specific API endpoint"""

    path: str
    method: str = "GET"
    request_count: int = 0
    response_time_avg: float = 0.0
    response_time_min: float = 0.0
    response_time_max: float = 0.0
    response_time_p50: float = 0.0
    response_time_p95: float = 0.0
    response_time_p99: float = 0.0
    error_count: int = 0
    error_rate: float = 0.0
    status_codes: dict[int, int] = field(default_factory=dict)
    last_error: Optional[str] = None
    last_request_time: Optional[datetime] = None


@dataclass
class ApplicationMetricsSnapshot:
    """Comprehensive application metrics snapshot"""

    # Overall application metrics
    total_requests: int = 0
    requests_per_second: float = 0.0
    avg_response_time: float = 0.0
    error_rate: float = 0.0
    total_errors: int = 0

    # Connection metrics
    active_connections: int = 0
    max_connections: int = 0
    connection_pool_usage: float = 0.0
    websocket_connections: int = 0

    # Resource usage
    thread_count: int = 0
    memory_heap_used: int = 0
    memory_heap_max: int = 0
    garbage_collection_count: int = 0
    garbage_collection_time: float = 0.0

    # Business metrics (ISP-specific)
    active_tenants: int = 0
    active_customers: int = 0
    billing_operations_per_min: float = 0.0
    auth_operations_per_min: float = 0.0

    # Endpoint-specific metrics
    endpoints: dict[str, EndpointMetrics] = field(default_factory=dict)

    # Error details
    recent_errors: list[str] = field(default_factory=list)
    error_types: dict[str, int] = field(default_factory=dict)

    # Custom metrics
    custom_metrics: dict[str, Union[int, float, str]] = field(default_factory=dict)

    # Health indicators
    health_status: str = "unknown"
    health_checks: dict[str, bool] = field(default_factory=dict)

    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "application": {
                "total_requests": self.total_requests,
                "requests_per_second": self.requests_per_second,
                "avg_response_time": self.avg_response_time,
                "error_rate": self.error_rate,
                "total_errors": self.total_errors,
            },
            "connections": {
                "active": self.active_connections,
                "max": self.max_connections,
                "pool_usage": self.connection_pool_usage,
                "websockets": self.websocket_connections,
            },
            "resources": {
                "thread_count": self.thread_count,
                "heap_used": self.memory_heap_used,
                "heap_max": self.memory_heap_max,
                "gc_count": self.garbage_collection_count,
                "gc_time": self.garbage_collection_time,
            },
            "business": {
                "active_tenants": self.active_tenants,
                "active_customers": self.active_customers,
                "billing_ops_per_min": self.billing_operations_per_min,
                "auth_ops_per_min": self.auth_operations_per_min,
            },
            "endpoints": {
                path: {
                    "method": endpoint.method,
                    "request_count": endpoint.request_count,
                    "response_time_avg": endpoint.response_time_avg,
                    "response_time_p95": endpoint.response_time_p95,
                    "error_count": endpoint.error_count,
                    "error_rate": endpoint.error_rate,
                    "status_codes": endpoint.status_codes,
                }
                for path, endpoint in self.endpoints.items()
            },
            "errors": {"recent": self.recent_errors, "by_type": self.error_types},
            "health": {"status": self.health_status, "checks": self.health_checks},
            "custom": self.custom_metrics,
            "timestamp": self.timestamp.isoformat(),
        }


class AppMetricsCollector:
    """
    Application metrics collector for ISP framework containers

    Collects comprehensive application-level metrics including:
    - HTTP/API request and response metrics
    - Application resource usage
    - Business-specific metrics (tenants, customers, billing)
    - Health check results
    - Custom application metrics
    """

    def __init__(
        self,
        collection_timeout: int = 10,
        enable_endpoint_metrics: bool = True,
        enable_business_metrics: bool = True,
        custom_metrics_endpoints: Optional[list[str]] = None,
        prometheus_enabled: bool = False,
    ):
        self.collection_timeout = collection_timeout
        self.enable_endpoint_metrics = enable_endpoint_metrics
        self.enable_business_metrics = enable_business_metrics
        self.custom_metrics_endpoints = custom_metrics_endpoints or []
        # Force-disable legacy Prometheus scraping
        if prometheus_enabled:
            self.logger.info("Prometheus scraping is deprecated and disabled; using SigNoz/OTLP only")
        self.prometheus_enabled = False

        self.docker_client = docker.from_env()
        self.logger = logging.getLogger(__name__)

        # Cache for rate calculations
        self._previous_snapshots: dict[str, ApplicationMetricsSnapshot] = {}
        self._collection_timestamps: dict[str, float] = {}

    async def collect_application_metrics(self, container_id: str) -> ApplicationMetricsSnapshot:
        """
        Collect comprehensive application metrics for a container

        Args:
            container_id: Docker container ID or name

        Returns:
            ApplicationMetricsSnapshot with detailed application metrics
        """
        snapshot = ApplicationMetricsSnapshot()
        current_time = time.time()

        try:
            container = self.docker_client.containers.get(container_id)

            # Get container network information
            container_ip = self._get_container_ip(container)
            ports = self._get_port_mappings(container)

            if not ports:
                self.logger.warning(f"No accessible ports found for container {container_id}")
                return snapshot

            # Collect metrics from various sources
            collection_tasks = []

            # Prometheus scraping disabled

            collection_tasks.extend(
                [
                    self._collect_health_metrics(container_ip, ports, snapshot),
                    self._collect_api_metrics(container_ip, ports, snapshot),
                ]
            )

            if self.enable_business_metrics:
                collection_tasks.append(self._collect_business_metrics(container_ip, ports, snapshot))

            if self.custom_metrics_endpoints:
                collection_tasks.append(self._collect_custom_metrics(container_ip, ports, snapshot))

            # Execute all collection tasks
            await asyncio.gather(*collection_tasks, return_exceptions=True)

            # Calculate rates based on previous snapshot
            if container_id in self._previous_snapshots:
                self._calculate_rates(container_id, snapshot, current_time)

            # Update cache
            self._previous_snapshots[container_id] = snapshot
            self._collection_timestamps[container_id] = current_time

        except docker.errors.NotFound:
            self.logger.error(f"Container {container_id} not found")
        except Exception as e:
            self.logger.error(f"Application metrics collection failed for {container_id}: {e}")

        return snapshot

    async def _collect_prometheus_metrics(
        self, container_ip: str, ports: list[int], snapshot: ApplicationMetricsSnapshot
    ) -> None:
        """Collect Prometheus metrics"""
        try:
            prometheus_data = await self._fetch_prometheus_data(container_ip, ports)
            if not prometheus_data:
                return

            # Parse common Prometheus metrics
            for line in prometheus_data.split("\n"):
                line = line.strip()
                if line.startswith("#") or not line:
                    continue

                try:
                    metric_name, metric_value = line.split(" ", 1)
                    value = float(metric_value)

                    # Map common metrics
                    if "http_requests_total" in metric_name:
                        snapshot.total_requests += int(value)
                    elif "http_request_duration_seconds_sum" in metric_name:
                        if snapshot.total_requests > 0:
                            snapshot.avg_response_time = value / snapshot.total_requests
                    elif "http_request_duration_seconds_count" in metric_name:
                        pass  # Already counted in total_requests
                    elif "process_open_fds" in metric_name:
                        snapshot.active_connections = int(value)
                    elif "go_threads" in metric_name or "python_threads" in metric_name:
                        snapshot.thread_count = int(value)
                    elif "go_memstats_heap_inuse_bytes" in metric_name:
                        snapshot.memory_heap_used = int(value)
                    elif "go_memstats_heap_sys_bytes" in metric_name:
                        snapshot.memory_heap_max = int(value)
                    elif "go_gc_duration_seconds_count" in metric_name:
                        snapshot.garbage_collection_count = int(value)
                    else:
                        # Store as custom metric
                        snapshot.custom_metrics[metric_name] = value

                except ValueError:
                    continue

        except Exception as e:
            self.logger.error(f"Failed to collect Prometheus metrics: {e}")

    async def _collect_health_metrics(
        self, container_ip: str, ports: list[int], snapshot: ApplicationMetricsSnapshot
    ) -> None:
        """Collect application health metrics"""
        if not HTTP_CLIENT_AVAILABLE:
            snapshot.health_status = "unknown"
            return

        health_endpoints = [
            "/health",
            "/api/health",
            "/api/v1/health",
            "/healthcheck",
            "/status",
        ]

        async with httpx.AsyncClient(timeout=self.collection_timeout) as client:
            for port in ports:
                for endpoint in health_endpoints:
                    try:
                        url = f"http://{container_ip}:{port}{endpoint}"
                        response = await client.get(url)

                        if response.status_code == 200:
                            snapshot.health_status = "healthy"

                            # Parse health response
                            try:
                                health_data = await response.json()
                                if isinstance(health_data, dict):
                                    # Extract health checks
                                    for key, value in health_data.items():
                                        if isinstance(value, bool):
                                            snapshot.health_checks[key] = value
                                        elif isinstance(value, str) and value.lower() in ["ok", "healthy", "up"]:
                                            snapshot.health_checks[key] = True
                                        elif isinstance(value, str) and value.lower() in [
                                            "error",
                                            "unhealthy",
                                            "down",
                                        ]:
                                            snapshot.health_checks[key] = False
                            except json.JSONDecodeError as e:
                                logger.debug(f"Failed to parse health check response as JSON: {e}")
                                pass

                            return  # Found working health endpoint

                    except httpx.RequestError:
                        continue

            # If no health endpoint responded, mark as unknown
            if not snapshot.health_checks:
                snapshot.health_status = "unknown"

    async def _collect_api_metrics(
        self, container_ip: str, ports: list[int], snapshot: ApplicationMetricsSnapshot
    ) -> None:
        """Collect API-specific metrics"""
        if not self.enable_endpoint_metrics or not HTTP_CLIENT_AVAILABLE:
            return

        # Try to get OpenAPI/FastAPI metrics
        api_endpoints = [
            "/metrics",
            "/api/metrics",
            "/docs",  # FastAPI docs might have some info
            "/openapi.json",  # OpenAPI spec
        ]

        async with httpx.AsyncClient(timeout=self.collection_timeout) as client:
            for port in ports:
                # Try to get API specification for endpoint discovery
                try:
                    openapi_url = f"http://{container_ip}:{port}/openapi.json"
                    response = await client.get(openapi_url)

                    if response.status_code == 200:
                        api_spec = await response.json()
                        await self._extract_endpoints_from_openapi(api_spec, snapshot)

                except httpx.RequestError:
                    pass

                # Try direct metrics endpoints
                for endpoint in api_endpoints:
                    try:
                        url = f"http://{container_ip}:{port}{endpoint}"
                        response = await client.get(url)

                        if response.status_code == 200:
                            await self._parse_api_metrics_response(response, snapshot)

                    except httpx.RequestError:
                        continue

    async def _collect_business_metrics(
        self, container_ip: str, ports: list[int], snapshot: ApplicationMetricsSnapshot
    ) -> None:
        """Collect ISP business-specific metrics"""
        if not HTTP_CLIENT_AVAILABLE:
            return

        business_endpoints = [
            "/api/v1/admin/stats",
            "/api/v1/metrics/business",
            "/api/admin/dashboard/stats",
            "/api/stats",
        ]

        async with httpx.AsyncClient(timeout=self.collection_timeout) as client:
            for port in ports:
                for endpoint in business_endpoints:
                    try:
                        url = f"http://{container_ip}:{port}{endpoint}"
                        response = await client.get(url)

                        if response.status_code == 200:
                            business_data = await response.json()

                            # Extract business metrics
                            if isinstance(business_data, dict):
                                # Tenant metrics
                                if "active_tenants" in business_data:
                                    snapshot.active_tenants = int(business_data["active_tenants"])
                                elif "tenants" in business_data:
                                    snapshot.active_tenants = int(business_data["tenants"])

                                # Customer metrics
                                if "active_customers" in business_data:
                                    snapshot.active_customers = int(business_data["active_customers"])
                                elif "customers" in business_data:
                                    snapshot.active_customers = int(business_data["customers"])

                                # Operation rates
                                if "billing_operations" in business_data:
                                    snapshot.billing_operations_per_min = float(business_data["billing_operations"])
                                if "auth_operations" in business_data:
                                    snapshot.auth_operations_per_min = float(business_data["auth_operations"])

                                # Store other metrics as custom
                                for key, value in business_data.items():
                                    if key not in [
                                        "active_tenants",
                                        "active_customers",
                                        "billing_operations",
                                        "auth_operations",
                                    ]:
                                        if isinstance(value, (int, float, str)):
                                            snapshot.custom_metrics[f"business_{key}"] = value

                            return  # Found working business metrics endpoint

                    except (httpx.RequestError, json.JSONDecodeError):
                        continue

    async def _collect_custom_metrics(
        self, container_ip: str, ports: list[int], snapshot: ApplicationMetricsSnapshot
    ) -> None:
        """Collect custom application metrics"""
        if not HTTP_CLIENT_AVAILABLE:
            return

        async with httpx.AsyncClient(timeout=self.collection_timeout) as client:
            for port in ports:
                for endpoint in self.custom_metrics_endpoints:
                    try:
                        url = f"http://{container_ip}:{port}{endpoint}"
                        response = await client.get(url)

                        if response.status_code == 200:
                            custom_data = await response.json()

                            if isinstance(custom_data, dict):
                                # Store all numeric values as custom metrics
                                for key, value in custom_data.items():
                                    if isinstance(value, (int, float)):
                                        snapshot.custom_metrics[f"custom_{key}"] = value
                                    elif isinstance(value, str) and value.replace(".", "").isdigit():
                                        snapshot.custom_metrics[f"custom_{key}"] = float(value)

                    except (httpx.RequestError, json.JSONDecodeError):
                        continue

    async def _fetch_prometheus_data(self, container_ip: str, ports: list[int]) -> Optional[str]:
        """Fetch Prometheus metrics data"""
        if not HTTP_CLIENT_AVAILABLE:
            return None

        prometheus_paths = ["/metrics", "/api/metrics", "/prometheus"]

        async with httpx.AsyncClient(timeout=self.collection_timeout) as client:
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

    async def _extract_endpoints_from_openapi(self, api_spec: dict, snapshot: ApplicationMetricsSnapshot) -> None:
        """Extract endpoint information from OpenAPI specification"""
        try:
            paths = api_spec.get("paths", {})

            for path, methods in paths.items():
                for method, _spec in methods.items():
                    if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                        endpoint = EndpointMetrics(path=path, method=method.upper())
                        snapshot.endpoints[f"{method.upper()} {path}"] = endpoint

        except Exception as e:
            self.logger.error(f"Failed to extract endpoints from OpenAPI spec: {e}")

    async def _parse_api_metrics_response(self, response: httpx.Response, snapshot: ApplicationMetricsSnapshot) -> None:
        """Parse API metrics response"""
        try:
            if "application/json" in response.headers.get("content-type", ""):
                data = await response.json()

                if isinstance(data, dict):
                    # Look for common metrics patterns
                    for key, value in data.items():
                        if isinstance(value, (int, float)):
                            if "request" in key.lower() and "count" in key.lower():
                                snapshot.total_requests += int(value)
                            elif "error" in key.lower() and "count" in key.lower():
                                snapshot.total_errors += int(value)
                            elif "response_time" in key.lower() or "latency" in key.lower():
                                snapshot.avg_response_time = max(snapshot.avg_response_time, float(value))

        except json.JSONDecodeError:
            pass

    def _calculate_rates(
        self,
        container_id: str,
        current_snapshot: ApplicationMetricsSnapshot,
        current_time: float,
    ) -> None:
        """Calculate rate-based metrics"""
        try:
            previous_snapshot = self._previous_snapshots[container_id]
            previous_time = self._collection_timestamps[container_id]

            time_delta = current_time - previous_time
            if time_delta <= 0:
                return

            # Calculate requests per second
            request_delta = current_snapshot.total_requests - previous_snapshot.total_requests
            current_snapshot.requests_per_second = max(0, request_delta / time_delta)

            # Calculate error rate
            if current_snapshot.total_requests > 0:
                current_snapshot.error_rate = current_snapshot.total_errors / current_snapshot.total_requests * 100

            # Calculate business operation rates (convert to per minute)
            billing_delta = current_snapshot.billing_operations_per_min - previous_snapshot.billing_operations_per_min
            current_snapshot.billing_operations_per_min = max(0, billing_delta / time_delta * 60)

            auth_delta = current_snapshot.auth_operations_per_min - previous_snapshot.auth_operations_per_min
            current_snapshot.auth_operations_per_min = max(0, auth_delta / time_delta * 60)

        except Exception as e:
            self.logger.error(f"Failed to calculate rates: {e}")

    def _get_container_ip(self, container: Container) -> str:
        """Get container IP address"""
        try:
            networks = container.attrs["NetworkSettings"]["Networks"]
            for network in networks.values():
                ip = network.get("IPAddress")
                if ip:
                    return ip
        except KeyError:
            pass
        return "localhost"

    def _get_port_mappings(self, container: Container) -> list[int]:
        """Get accessible port mappings"""
        try:
            ports = container.attrs["NetworkSettings"]["Ports"]
            accessible_ports = []

            for port, bindings in ports.items():
                if bindings:
                    # Port is mapped to host
                    for binding in bindings:
                        host_port = binding.get("HostPort")
                        if host_port:
                            accessible_ports.append(int(host_port))
                else:
                    # Internal port, use directly if we have container IP
                    internal_port = int(port.split("/")[0])
                    accessible_ports.append(internal_port)

            # Fallback to common ports
            if not accessible_ports:
                accessible_ports = [8000, 8080, 3000, 5000]

            return accessible_ports

        except (KeyError, ValueError):
            return [8000]  # Default fallback

    def clear_cache(self, container_id: Optional[str] = None) -> None:
        """Clear cached data for rate calculations"""
        if container_id:
            self._previous_snapshots.pop(container_id, None)
            self._collection_timestamps.pop(container_id, None)
        else:
            self._previous_snapshots.clear()
            self._collection_timestamps.clear()
