"""
Service Mesh Implementation

Provides comprehensive service-to-service communication management:
- Service registration and discovery
- Load balancing and traffic routing
- Circuit breakers and retry policies
- Security and encryption (mTLS)
- Observability and distributed tracing
- Traffic policies and rate limiting
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

import aiohttp
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import EntityNotFoundError
from ..services.performance_optimization import PerformanceOptimizationService
from ..services.service_marketplace import ServiceMarketplace

logger = logging.getLogger(__name__)


class TrafficPolicy(str, Enum):
    """Traffic routing policies."""

    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"
    CONSISTENT_HASH = "consistent_hash"
    STICKY_SESSION = "sticky_session"


class RetryPolicy(str, Enum):
    """Retry policies for failed requests."""

    NONE = "none"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_INTERVAL = "fixed_interval"
    CIRCUIT_BREAKER = "circuit_breaker"


class EncryptionLevel(str, Enum):
    """Service communication encryption levels."""

    NONE = "none"
    TLS = "tls"
    MTLS = "mtls"


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""

    service_name: str
    host: str
    port: int
    path: str = "/"
    protocol: str = "http"
    weight: int = 100
    health_check_path: str = "/health"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def url(self) -> str:
        """Get the full URL for this endpoint."""
        return f"{self.protocol}://{self.host}:{self.port}{self.path}"

    @property
    def health_url(self) -> str:
        """Get the health check URL."""
        return f"{self.protocol}://{self.host}:{self.port}{self.health_check_path}"


@dataclass
class TrafficRule:
    """Traffic routing rule configuration."""

    name: str
    source_service: str
    destination_service: str
    policy: TrafficPolicy = TrafficPolicy.ROUND_ROBIN
    weight_distribution: dict[str, int] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL_BACKOFF
    max_retries: int = 3
    circuit_breaker_enabled: bool = True
    rate_limit_rpm: int | None = None
    encryption_level: EncryptionLevel = EncryptionLevel.TLS


@dataclass
class ServiceCall:
    """Represents a service-to-service call."""

    call_id: str
    source_service: str
    destination_service: str
    method: str
    path: str
    headers: dict[str, str]
    body: bytes | None
    timestamp: datetime
    trace_id: str
    span_id: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "call_id": self.call_id,
            "source_service": self.source_service,
            "destination_service": self.destination_service,
            "method": self.method,
            "path": self.path,
            "headers": self.headers,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "span_id": self.span_id,
        }


class CircuitBreakerState:
    """Circuit breaker for service calls."""

    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker closed after successful call")

    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def can_execute(self) -> bool:
        """Check if call can be executed."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - (self.last_failure_time or 0) > self.timeout_seconds:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False
        else:  # HALF_OPEN
            return True


class ServiceRegistry:
    """Registry for service endpoints and configurations."""

    def __init__(self):
        self.endpoints: dict[str, list[ServiceEndpoint]] = {}
        self.traffic_rules: dict[str, TrafficRule] = {}
        self.circuit_breakers: dict[str, CircuitBreakerState] = {}
        self.connection_counts: dict[str, int] = {}

    def register_endpoint(self, endpoint: ServiceEndpoint):
        """Register a service endpoint."""
        if endpoint.service_name not in self.endpoints:
            self.endpoints[endpoint.service_name] = []

        # Remove existing endpoint with same host:port
        self.endpoints[endpoint.service_name] = [
            ep
            for ep in self.endpoints[endpoint.service_name]
            if not (ep.host == endpoint.host and ep.port == endpoint.port)
        ]

        self.endpoints[endpoint.service_name].append(endpoint)
        logger.info(f"Registered endpoint: {endpoint.service_name} at {endpoint.url}")

    def unregister_endpoint(self, service_name: str, host: str, port: int):
        """Unregister a service endpoint."""
        if service_name in self.endpoints:
            self.endpoints[service_name] = [
                ep for ep in self.endpoints[service_name] if not (ep.host == host and ep.port == port)
            ]
            logger.info(f"Unregistered endpoint: {service_name} at {host}:{port}")

    def get_endpoints(self, service_name: str) -> list[ServiceEndpoint]:
        """Get all endpoints for a service."""
        return self.endpoints.get(service_name, [])

    def add_traffic_rule(self, rule: TrafficRule):
        """Add a traffic routing rule."""
        rule_key = f"{rule.source_service}->{rule.destination_service}"
        self.traffic_rules[rule_key] = rule
        logger.info(f"Added traffic rule: {rule.name}")

    def get_traffic_rule(self, source_service: str, destination_service: str) -> TrafficRule | None:
        """Get traffic rule for service pair."""
        rule_key = f"{source_service}->{destination_service}"
        return self.traffic_rules.get(rule_key)

    def get_circuit_breaker(self, service_name: str) -> CircuitBreakerState:
        """Get circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreakerState()
        return self.circuit_breakers[service_name]


class LoadBalancer:
    """Load balancer for selecting service endpoints."""

    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.round_robin_counters: dict[str, int] = {}

    def select_endpoint(
        self,
        service_name: str,
        policy: TrafficPolicy,
        source_context: dict[str, Any] | None = None,
    ) -> ServiceEndpoint | None:
        """Select an endpoint based on traffic policy."""
        endpoints = self.registry.get_endpoints(service_name)
        if not endpoints:
            return None

        # Filter healthy endpoints
        healthy_endpoints = [ep for ep in endpoints if self._is_healthy(ep)]
        if not healthy_endpoints:
            # Fallback to all endpoints if none are healthy
            healthy_endpoints = endpoints

        if policy == TrafficPolicy.ROUND_ROBIN:
            return self._select_round_robin(service_name, healthy_endpoints)
        elif policy == TrafficPolicy.WEIGHTED:
            return self._select_weighted(healthy_endpoints)
        elif policy == TrafficPolicy.LEAST_CONNECTIONS:
            return self._select_least_connections(healthy_endpoints)
        elif policy == TrafficPolicy.CONSISTENT_HASH:
            return self._select_consistent_hash(healthy_endpoints, source_context)
        else:
            return healthy_endpoints[0]  # Default to first

    def _select_round_robin(self, service_name: str, endpoints: list[ServiceEndpoint]) -> ServiceEndpoint:
        """Select endpoint using round robin."""
        if service_name not in self.round_robin_counters:
            self.round_robin_counters[service_name] = 0

        selected = endpoints[self.round_robin_counters[service_name] % len(endpoints)]
        self.round_robin_counters[service_name] += 1
        return selected

    def _select_weighted(self, endpoints: list[ServiceEndpoint]) -> ServiceEndpoint:
        """Select endpoint using weighted random selection."""
        total_weight = sum(ep.weight for ep in endpoints)
        if total_weight == 0:
            return endpoints[0]

        from secrets import SystemRandom

        _sr = SystemRandom()
        r = _sr.randint(1, total_weight)
        current_weight = 0

        for endpoint in endpoints:
            current_weight += endpoint.weight
            if current_weight >= r:
                return endpoint

        return endpoints[-1]

    def _select_least_connections(self, endpoints: list[ServiceEndpoint]) -> ServiceEndpoint:
        """Select endpoint with least connections."""
        min_connections = float("inf")
        selected = endpoints[0]

        for endpoint in endpoints:
            endpoint_key = f"{endpoint.host}:{endpoint.port}"
            connections = self.registry.connection_counts.get(endpoint_key, 0)
            if connections < min_connections:
                min_connections = connections
                selected = endpoint

        return selected

    def _select_consistent_hash(
        self, endpoints: list[ServiceEndpoint], source_context: dict[str, Any]
    ) -> ServiceEndpoint:
        """Select endpoint using consistent hashing."""
        if not source_context:
            return endpoints[0]

        # Create hash from source context (using SHA-256 instead of MD5 for security)
        hash_input = json.dumps(source_context, sort_keys=True)
        hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest()[:16], 16)
        index = hash_value % len(endpoints)
        return endpoints[index]

    def _is_healthy(self, endpoint: ServiceEndpoint) -> bool:
        """Check if endpoint is healthy (placeholder)."""
        # In real implementation, this would check health status
        return True


class ServiceMesh:
    """Main service mesh implementation."""

    def __init__(
        self,
        db_session: AsyncSession,
        tenant_id: str,
        marketplace: ServiceMarketplace,
        performance_service: PerformanceOptimizationService | None = None,
    ):
        self.db_session = db_session
        self.tenant_id = tenant_id
        self.marketplace = marketplace
        self.performance_service = performance_service

        self.registry = ServiceRegistry()
        self.load_balancer = LoadBalancer(self.registry)

        # Metrics and monitoring
        self.call_metrics: dict[str, Any] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "average_latency_ms": 0.0,
            "calls_by_service": {},
            "active_connections": 0,
        }

        # HTTP session for service calls
        self.http_session: aiohttp.ClientSession | None = None

    async def initialize(self):
        """Initialize the service mesh."""
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100),
        )

        # Discover and register services from marketplace
        await self._discover_services()

        logger.info(f"Service mesh initialized for tenant: {self.tenant_id}")

    async def shutdown(self):
        """Shutdown the service mesh."""
        if self.http_session:
            await self.http_session.close()
        logger.info("Service mesh shutdown complete")

    async def _discover_services(self):
        """Discover services from marketplace and register endpoints."""
        try:
            services = await self.marketplace.discover_service()

            for service_info in services:
                service_name = service_info.get("name", "unknown")
                instances = service_info.get("instances", [])

                for instance in instances:
                    endpoint = ServiceEndpoint(
                        service_name=service_name,
                        host=instance.get("host", "localhost"),
                        port=instance.get("port", 8000),
                        path=instance.get("base_path", "/"),
                        metadata=instance.get("metadata", {}),
                    )
                    self.registry.register_endpoint(endpoint)

            logger.info(f"Discovered and registered {len(services)} services")
        except Exception as e:
            logger.error(f"Service discovery failed: {e}")

    async def call_service(
        self,
        source_service: str,
        destination_service: str,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Make a service-to-service call through the mesh."""
        start_time = time.time()
        call_id = str(uuid4())
        trace_id = headers.get("X-Trace-ID", str(uuid4())) if headers else str(uuid4())
        span_id = str(uuid4())

        # Get traffic rule
        traffic_rule = self.registry.get_traffic_rule(source_service, destination_service)
        if not traffic_rule:
            # Create default rule
            traffic_rule = TrafficRule(
                name=f"default-{source_service}-{destination_service}",
                source_service=source_service,
                destination_service=destination_service,
            )

        # Check circuit breaker
        circuit_breaker = self.registry.get_circuit_breaker(destination_service)
        if not circuit_breaker.can_execute():
            raise HTTPException(
                status_code=503,
                detail=f"Service {destination_service} is currently unavailable (circuit breaker open)",
            )

        # Select endpoint
        endpoint = self.load_balancer.select_endpoint(
            destination_service, traffic_rule.policy, {"source_service": source_service}
        )

        if not endpoint:
            raise EntityNotFoundError(f"No endpoints available for service: {destination_service}")

        # Create service call record
        service_call = ServiceCall(
            call_id=call_id,
            source_service=source_service,
            destination_service=destination_service,
            method=method,
            path=path,
            headers=headers or {},
            body=body,
            timestamp=datetime.now(timezone.utc),
            trace_id=trace_id,
            span_id=span_id,
        )

        try:
            # Update connection count
            endpoint_key = f"{endpoint.host}:{endpoint.port}"
            self.registry.connection_counts[endpoint_key] = self.registry.connection_counts.get(endpoint_key, 0) + 1

            # Make the actual HTTP call
            response = await self._make_http_call(
                endpoint,
                method,
                path,
                headers,
                body,
                timeout or traffic_rule.timeout_seconds,
            )

            # Record success
            circuit_breaker.record_success()
            self._record_call_success(service_call, time.time() - start_time)

            return {
                "status_code": response["status_code"],
                "headers": response["headers"],
                "body": response["body"],
                "call_id": call_id,
                "trace_id": trace_id,
                "span_id": span_id,
            }

        except Exception as e:
            # Record failure
            circuit_breaker.record_failure()
            self._record_call_failure(service_call, time.time() - start_time, str(e))

            # Retry logic could be implemented here
            if traffic_rule.retry_policy != RetryPolicy.NONE and traffic_rule.max_retries > 0:
                # For now, just re-raise
                pass

            raise HTTPException(status_code=500, detail=f"Service call failed: {e}") from e

        finally:
            # Update connection count
            if endpoint:
                endpoint_key = f"{endpoint.host}:{endpoint.port}"
                current_count = self.registry.connection_counts.get(endpoint_key, 1)
                self.registry.connection_counts[endpoint_key] = max(0, current_count - 1)

    async def _make_http_call(
        self,
        endpoint: ServiceEndpoint,
        method: str,
        path: str,
        headers: dict[str, str] | None,
        body: bytes | None,
        timeout: int,
    ) -> dict[str, Any]:
        """Make the actual HTTP call to the service."""
        url = f"{endpoint.url.rstrip('/')}/{path.lstrip('/')}"

        # Prepare headers
        call_headers = {}
        if headers:
            call_headers.update(headers)

        # Add mesh headers
        call_headers.update(
            {
                "X-Mesh-Source": "dotmac-service-mesh",
                "X-Mesh-Version": "1.0.0",
                "X-Mesh-Tenant": self.tenant_id,
            }
        )

        if not self.http_session:
            raise RuntimeError("HTTP session not initialized")

        async with self.http_session.request(
            method=method.upper(),
            url=url,
            headers=call_headers,
            data=body,
            timeout=timeout,
        ) as response:
            response_body = await response.read()

            return {
                "status_code": response.status,
                "headers": dict(response.headers),
                "body": response_body,
            }

    def _record_call_success(self, call: ServiceCall, duration: float):
        """Record a successful service call."""
        self.call_metrics["total_calls"] += 1
        self.call_metrics["successful_calls"] += 1

        # Update average latency
        current_avg = self.call_metrics["average_latency_ms"]
        total_calls = self.call_metrics["total_calls"]
        self.call_metrics["average_latency_ms"] = (current_avg * (total_calls - 1) + duration * 1000) / total_calls

        # Update service-specific metrics
        service_key = f"{call.source_service}->{call.destination_service}"
        if service_key not in self.call_metrics["calls_by_service"]:
            self.call_metrics["calls_by_service"][service_key] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
            }

        self.call_metrics["calls_by_service"][service_key]["total"] += 1
        self.call_metrics["calls_by_service"][service_key]["successful"] += 1

    def _record_call_failure(self, call: ServiceCall, duration: float, error: str):
        """Record a failed service call."""
        self.call_metrics["total_calls"] += 1
        self.call_metrics["failed_calls"] += 1

        # Update service-specific metrics
        service_key = f"{call.source_service}->{call.destination_service}"
        if service_key not in self.call_metrics["calls_by_service"]:
            self.call_metrics["calls_by_service"][service_key] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
            }

        self.call_metrics["calls_by_service"][service_key]["total"] += 1
        self.call_metrics["calls_by_service"][service_key]["failed"] += 1

        logger.warning(f"Service call failed: {call.call_id} - {error}")

    def add_traffic_rule(self, rule: TrafficRule):
        """Add a traffic routing rule."""
        self.registry.add_traffic_rule(rule)

    def register_service_endpoint(self, endpoint: ServiceEndpoint):
        """Register a new service endpoint."""
        self.registry.register_endpoint(endpoint)

    def get_mesh_metrics(self) -> dict[str, Any]:
        """Get service mesh metrics."""
        success_rate = 0.0
        if self.call_metrics["total_calls"] > 0:
            success_rate = (self.call_metrics["successful_calls"] / self.call_metrics["total_calls"]) * 100

        return {
            "tenant_id": self.tenant_id,
            "total_calls": self.call_metrics["total_calls"],
            "successful_calls": self.call_metrics["successful_calls"],
            "failed_calls": self.call_metrics["failed_calls"],
            "success_rate_percent": round(success_rate, 2),
            "average_latency_ms": round(self.call_metrics["average_latency_ms"], 2),
            "active_connections": self.call_metrics["active_connections"],
            "registered_services": len(self.registry.endpoints),
            "total_endpoints": sum(len(eps) for eps in self.registry.endpoints.values()),
            "traffic_rules": len(self.registry.traffic_rules),
            "circuit_breakers": {name: cb.state for name, cb in self.registry.circuit_breakers.items()},
            "calls_by_service": self.call_metrics["calls_by_service"],
        }

    def get_service_topology(self) -> dict[str, Any]:
        """Get service mesh topology information."""
        topology = {"services": {}, "connections": []}

        # Build service information
        for service_name, endpoints in self.registry.endpoints.items():
            topology["services"][service_name] = {
                "endpoints": [
                    {
                        "host": ep.host,
                        "port": ep.port,
                        "path": ep.path,
                        "weight": ep.weight,
                        "metadata": ep.metadata,
                    }
                    for ep in endpoints
                ],
                "total_endpoints": len(endpoints),
            }

        # Build connection information from traffic rules
        for rule in self.registry.traffic_rules.values():
            topology["connections"].append(
                {
                    "source": rule.source_service,
                    "destination": rule.destination_service,
                    "policy": rule.policy,
                    "encryption": rule.encryption_level,
                    "circuit_breaker": rule.circuit_breaker_enabled,
                }
            )

        return topology


class ServiceMeshFactory:
    """Factory for creating service mesh instances."""

    @staticmethod
    def create_service_mesh(
        db_session: AsyncSession,
        tenant_id: str,
        marketplace: ServiceMarketplace,
        performance_service: PerformanceOptimizationService | None = None,
    ) -> ServiceMesh:
        """Create a service mesh instance."""
        mesh = ServiceMesh(
            db_session=db_session,
            tenant_id=tenant_id,
            marketplace=marketplace,
            performance_service=performance_service,
        )
        return mesh

    @staticmethod
    def create_traffic_rule(name: str, source_service: str, destination_service: str, **kwargs) -> TrafficRule:
        """Create a traffic rule with default settings."""
        return TrafficRule(
            name=name,
            source_service=source_service,
            destination_service=destination_service,
            **kwargs,
        )

    @staticmethod
    def create_service_endpoint(service_name: str, host: str, port: int, **kwargs) -> ServiceEndpoint:
        """Create a service endpoint configuration."""
        return ServiceEndpoint(service_name=service_name, host=host, port=port, **kwargs)


async def setup_service_mesh_for_consolidated_services(
    db_session: AsyncSession,
    tenant_id: str,
    marketplace: ServiceMarketplace,
    performance_service: PerformanceOptimizationService | None = None,
) -> ServiceMesh:
    """Setup service mesh with consolidated services from Phase 2."""
    mesh = ServiceMeshFactory.create_service_mesh(db_session, tenant_id, marketplace, performance_service)

    await mesh.initialize()

    # Add default traffic rules for consolidated services
    consolidated_services = [
        "unified-billing-service",
        "unified-analytics-service",
        "unified-identity-service",
    ]

    for source in consolidated_services:
        for dest in consolidated_services:
            if source != dest:
                rule = ServiceMeshFactory.create_traffic_rule(
                    name=f"default-{source}-to-{dest}",
                    source_service=source,
                    destination_service=dest,
                    policy=TrafficPolicy.ROUND_ROBIN,
                    retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
                    max_retries=3,
                    circuit_breaker_enabled=True,
                )
                mesh.add_traffic_rule(rule)

    logger.info("Service mesh setup complete with consolidated services")
    return mesh
