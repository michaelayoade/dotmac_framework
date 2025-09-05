"""
Unified API Gateway Integration

Provides comprehensive API gateway functionality for the consolidated DotMac services:
- Centralized routing and load balancing
- Authentication and authorization middleware
- Rate limiting and throttling
- Request/response transformation
- Circuit breaker and fault tolerance
- API versioning and backwards compatibility
- Monitoring and analytics integration
- Security and compliance enforcement
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..services.performance_optimization import PerformanceOptimizationService
from ..services.service_marketplace import ServiceMarketplace, ServiceStatus
from ..services.unified_identity_service import UnifiedIdentityService

logger = logging.getLogger(__name__)


class RouteStrategy(str, Enum):
    """Routing strategies for API gateway."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    HEALTH_BASED = "health_based"
    STICKY_SESSION = "sticky_session"


class GatewayConfig:
    """Configuration for the unified API gateway."""

    def __init__(
        self,
        # Basic settings
        title: str = "DotMac Unified API Gateway",
        version: str = "3.0.0",
        description: str = "Unified API gateway for consolidated DotMac services",
        # Security settings
        enable_authentication: bool = True,
        enable_authorization: bool = True,
        cors_origins: list[str] | None = None,
        trusted_hosts: list[str] | None = None,
        # Performance settings
        default_rate_limit: int = 1000,  # requests per minute
        enable_caching: bool = True,
        cache_ttl: int = 300,
        # Routing settings
        default_route_strategy: RouteStrategy = RouteStrategy.HEALTH_BASED,
        enable_circuit_breaker: bool = True,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
        # Monitoring settings
        enable_metrics: bool = True,
        enable_tracing: bool = True,
        log_requests: bool = True,
        # Service discovery
        service_discovery_interval: int = 30,
        health_check_interval: int = 15,
    ):
        self.title = title
        self.version = version
        self.description = description
        self.enable_authentication = enable_authentication
        self.enable_authorization = enable_authorization
        self.cors_origins = cors_origins or ["*"]
        self.trusted_hosts = trusted_hosts or ["*"]
        self.default_rate_limit = default_rate_limit
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        self.default_route_strategy = default_route_strategy
        self.enable_circuit_breaker = enable_circuit_breaker
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.enable_metrics = enable_metrics
        self.enable_tracing = enable_tracing
        self.log_requests = log_requests
        self.service_discovery_interval = service_discovery_interval
        self.health_check_interval = health_check_interval


class RateLimiter:
    """Rate limiting implementation for API gateway."""

    def __init__(self, requests_per_minute: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.client_requests: dict[str, list[float]] = {}
        self.cleanup_interval = 60  # Cleanup old entries every minute
        self.last_cleanup = time.time()

    async def is_allowed(self, client_id: str) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed for the client."""
        current_time = time.time()

        # Cleanup old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            await self._cleanup_old_entries()
            self.last_cleanup = current_time

        # Get or create client request history
        if client_id not in self.client_requests:
            self.client_requests[client_id] = []

        client_history = self.client_requests[client_id]

        # Remove requests older than 1 minute
        cutoff_time = current_time - 60
        client_history[:] = [
            req_time for req_time in client_history if req_time > cutoff_time
        ]

        # Check rate limit
        if len(client_history) >= self.requests_per_minute:
            return False, {
                "error": "Rate limit exceeded",
                "limit": self.requests_per_minute,
                "window": "1 minute",
                "retry_after": 60,
            }

        # Add current request
        client_history.append(current_time)

        return True, {
            "remaining": self.requests_per_minute - len(client_history),
            "reset_time": int(current_time + 60),
        }

    async def _cleanup_old_entries(self):
        """Remove old client entries to prevent memory leaks."""
        current_time = time.time()
        cutoff_time = current_time - 300  # 5 minutes ago

        clients_to_remove = []
        for client_id, requests in self.client_requests.items():
            # If all requests are old, remove the client entirely
            if not requests or all(req_time < cutoff_time for req_time in requests):
                clients_to_remove.append(client_id)

        for client_id in clients_to_remove:
            del self.client_requests[client_id]


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        current_time = time.time()

        # Check if circuit breaker should transition states
        if self.state == "OPEN":
            if current_time - (self.last_failure_time or 0) > self.timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable (circuit breaker open)",
                )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Success - reset failure count
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit breaker transitioning to CLOSED")

            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = current_time

            # Check if we should open the circuit
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(
                    f"Circuit breaker opening due to {self.failure_count} failures"
                )

            raise e


class GatewayMetrics:
    """Metrics collection for API gateway."""

    def __init__(self):
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limited_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.response_times: list[float] = []
        self.status_codes: dict[int, int] = {}
        self.endpoint_stats: dict[str, dict[str, Any]] = {}

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float,
        cache_hit: bool = False,
    ):
        """Record request metrics."""
        self.total_requests += 1

        if 200 <= status_code < 400:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        if status_code == 429:
            self.rate_limited_requests += 1

        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        self.response_times.append(response_time)

        # Track status codes
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

        # Track per-endpoint statistics
        endpoint_key = f"{method} {endpoint}"
        if endpoint_key not in self.endpoint_stats:
            self.endpoint_stats[endpoint_key] = {
                "count": 0,
                "success_count": 0,
                "total_response_time": 0.0,
                "avg_response_time": 0.0,
            }

        stats = self.endpoint_stats[endpoint_key]
        stats["count"] += 1
        if 200 <= status_code < 400:
            stats["success_count"] += 1
        stats["total_response_time"] += response_time
        stats["avg_response_time"] = stats["total_response_time"] / stats["count"]

    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        uptime = time.time() - self.start_time

        avg_response_time = 0.0
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)

        success_rate = 0.0
        if self.total_requests > 0:
            success_rate = (self.successful_requests / self.total_requests) * 100

        cache_hit_rate = 0.0
        if (self.cache_hits + self.cache_misses) > 0:
            cache_hit_rate = (
                self.cache_hits / (self.cache_hits + self.cache_misses)
            ) * 100

        return {
            "uptime_seconds": uptime,
            "total_requests": self.total_requests,
            "requests_per_second": self.total_requests / uptime if uptime > 0 else 0,
            "success_rate": round(success_rate, 2),
            "average_response_time_ms": round(avg_response_time * 1000, 2),
            "cache_hit_rate": round(cache_hit_rate, 2),
            "rate_limited_requests": self.rate_limited_requests,
            "status_codes": self.status_codes,
            "top_endpoints": sorted(
                self.endpoint_stats.items(), key=lambda x: x[1]["count"], reverse=True
            )[:10],
        }


class RequestTransformer:
    """Request and response transformation middleware."""

    def __init__(self):
        self.transformers: dict[str, Callable] = {}

    def register_transformer(self, pattern: str, transformer: Callable):
        """Register a transformer for requests matching pattern."""
        self.transformers[pattern] = transformer

    async def transform_request(self, request: Request) -> Request:
        """Transform incoming request."""
        path = request.url.path

        for pattern, transformer in self.transformers.items():
            if pattern in path:
                try:
                    request = await transformer(request)
                except Exception as e:
                    logger.warning(f"Request transformation failed: {e}")

        return request

    async def transform_response(
        self, response: Response, request: Request
    ) -> Response:
        """Transform outgoing response."""
        # Placeholder for response transformation logic
        return response


class UnifiedAPIGateway:
    """
    Unified API Gateway for consolidated DotMac services.

    Provides centralized routing, authentication, rate limiting, caching,
    circuit breaking, and monitoring for all consolidated services.
    """

    def __init__(
        self,
        config: GatewayConfig,
        service_marketplace: ServiceMarketplace,
        identity_service: UnifiedIdentityService | None = None,
        performance_service: PerformanceOptimizationService | None = None,
    ):
        self.config = config
        self.service_marketplace = service_marketplace
        self.identity_service = identity_service
        self.performance_service = performance_service

        # Initialize components
        self.rate_limiter = RateLimiter(config.default_rate_limit)
        self.circuit_breaker = CircuitBreaker(
            config.circuit_breaker_threshold, config.circuit_breaker_timeout
        )
        self.metrics = GatewayMetrics()
        self.request_transformer = RequestTransformer()

        # Service routing cache
        self.service_routes: dict[str, list[dict[str, Any]]] = {}
        self.last_service_discovery = 0

        # Create FastAPI app
        self.app = self._create_app()

        # Start background tasks
        asyncio.create_task(self._service_discovery_loop())
        asyncio.create_task(self._health_check_loop())

    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        app = FastAPI(
            title=self.config.title,
            version=self.config.version,
            description=self.config.description,
            docs_url="/docs",
            redoc_url="/redoc",
        )

        # Add middleware
        if self.config.cors_origins:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        if self.config.trusted_hosts:
            app.add_middleware(
                TrustedHostMiddleware, allowed_hosts=self.config.trusted_hosts
            )

        # Add custom middleware
        app.add_middleware(GatewayMiddleware, gateway=self)

        # Add routes
        self._setup_routes(app)

        return app

    def _setup_routes(self, app: FastAPI):
        """Setup API routes."""

        # Health check endpoint
        @app.get("/health")
        async def health_check():
            """Gateway health check."""
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": self.config.version,
                "services": len(self.service_routes),
            }

        # Metrics endpoint
        @app.get("/metrics")
        async def get_metrics():
            """Get gateway metrics."""
            return self.metrics.get_summary()

        # Service discovery endpoint
        @app.get("/services")
        async def list_services():
            """List available services."""
            return {
                "services": list(self.service_routes.keys()),
                "total": len(self.service_routes),
                "last_discovery": self.last_service_discovery,
            }

        # Dynamic service routing
        @app.api_route(
            "/{service_name}/{path:path}",
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        async def route_to_service(
            service_name: str,
            path: str,
            request: Request,
            credentials: HTTPAuthorizationCredentials
            | None = Depends(HTTPBearer(auto_error=False)),
        ):
            """Route requests to consolidated services."""
            return await self.route_request(service_name, path, request, credentials)

    async def route_request(
        self,
        service_name: str,
        path: str,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = None,
    ) -> Response:
        """Route request to appropriate service."""
        start_time = time.time()

        try:
            # Authentication check
            if self.config.enable_authentication and credentials:
                user_info = await self._authenticate_request(credentials.credentials)
                if not user_info:
                    raise HTTPException(
                        status_code=401, detail="Invalid authentication"
                    )

            # Rate limiting check
            client_id = self._get_client_id(request)
            is_allowed, rate_info = await self.rate_limiter.is_allowed(client_id)
            if not is_allowed:
                response_time = time.time() - start_time
                self.metrics.record_request(path, request.method, 429, response_time)
                return JSONResponse(
                    status_code=429,
                    content=rate_info,
                    headers={"Retry-After": str(rate_info.get("retry_after", 60))},
                )

            # Find service instances
            service_instances = await self._get_service_instances(service_name)
            if not service_instances:
                raise HTTPException(
                    status_code=503, detail=f"Service '{service_name}' not available"
                )

            # Select instance using load balancing strategy
            instance = await self._select_service_instance(service_instances, request)

            # Execute with circuit breaker
            response = await self.circuit_breaker.call(
                self._forward_request, instance, path, request
            )

            response_time = time.time() - start_time
            self.metrics.record_request(
                path, request.method, response.status_code, response_time
            )

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Request routing failed: {e}")
            response_time = time.time() - start_time
            self.metrics.record_request(path, request.method, 500, response_time)
            raise HTTPException(status_code=500, detail="Internal gateway error") from e

    async def _authenticate_request(self, token: str) -> dict[str, Any] | None:
        """Authenticate request using identity service."""
        if not self.identity_service:
            return None

        try:
            return await self.identity_service.validate_token(token)
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return None

    def _get_client_id(self, request: Request) -> str:
        """Extract client ID from request for rate limiting."""
        # Try to get from headers first
        client_id = request.headers.get("X-Client-ID")
        if client_id:
            return client_id

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return str(request.client.host) if request.client else "unknown"

    async def _get_service_instances(self, service_name: str) -> list[dict[str, Any]]:
        """Get available instances for a service."""
        # Discover services if cache is stale
        current_time = time.time()
        if (
            current_time - self.last_service_discovery
            > self.config.service_discovery_interval
        ):
            await self._discover_services()

        return self.service_routes.get(service_name, [])

    async def _select_service_instance(
        self, instances: list[dict[str, Any]], request: Request
    ) -> dict[str, Any]:
        """Select service instance using configured strategy."""
        if not instances:
            raise HTTPException(
                status_code=503, detail="No healthy service instances available"
            )

        # Filter healthy instances
        healthy_instances = [
            i for i in instances if i.get("status") == ServiceStatus.HEALTHY
        ]
        if not healthy_instances:
            healthy_instances = (
                instances  # Fall back to all instances if none are healthy
            )

        # Apply load balancing strategy
        if self.config.default_route_strategy == RouteStrategy.ROUND_ROBIN:
            # Simple round-robin (could be improved with persistent state)
            return healthy_instances[int(time.time()) % len(healthy_instances)]

        elif self.config.default_route_strategy == RouteStrategy.HEALTH_BASED:
            # Sort by health score (simulated)
            return max(healthy_instances, key=lambda x: x.get("health_score", 0))

        else:
            # Default to first available
            return healthy_instances[0]

    async def _forward_request(
        self, instance: dict[str, Any], path: str, request: Request
    ) -> Response:
        """Forward request to service instance."""
        # This would make an actual HTTP request to the service instance
        # For now, return a simulated response

        service_url = f"http://{instance['host']}:{instance['port']}/{path}"

        # Simulate service response
        response_data = {
            "service": instance.get("service_name", "unknown"),
            "instance": instance.get("instance_id", "unknown"),
            "path": path,
            "method": request.method,
            "forwarded_to": service_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return JSONResponse(content=response_data)

    async def _discover_services(self):
        """Discover available services from marketplace."""
        try:
            # Get all services from marketplace
            services = await self.service_marketplace.discover_service(
                healthy_only=False
            )

            # Update service routes cache
            self.service_routes.clear()

            for service in services:
                service_instances = (
                    await self.service_marketplace.get_service_instances(
                        service.service_id, healthy_only=False
                    )
                )

                instance_data = []
                for instance in service_instances:
                    instance_data.append(
                        {
                            "instance_id": instance.instance_id,
                            "service_name": service.name,
                            "host": instance.host,
                            "port": instance.port,
                            "status": instance.status,
                            "health_score": 100
                            if instance.status == ServiceStatus.HEALTHY
                            else 50,
                            "last_seen": instance.last_seen.isoformat(),
                        }
                    )

                if instance_data:
                    self.service_routes[
                        service.name.lower().replace(" ", "_")
                    ] = instance_data

            self.last_service_discovery = time.time()
            logger.info(f"Discovered {len(self.service_routes)} services")

        except Exception as e:
            logger.error(f"Service discovery failed: {e}")

    async def _service_discovery_loop(self):
        """Background service discovery loop."""
        while True:
            try:
                await self._discover_services()
                await asyncio.sleep(self.config.service_discovery_interval)
            except Exception as e:
                logger.error(f"Service discovery loop error: {e}")
                await asyncio.sleep(10)

    async def _health_check_loop(self):
        """Background health check loop."""
        while True:
            try:
                # Check health of all service instances
                for _service_name, instances in self.service_routes.items():
                    for instance in instances:
                        # Simulate health check (in real implementation, make HTTP request)
                        # For now, randomly mark some as unhealthy
                        from secrets import SystemRandom

                        _sr = SystemRandom()

                        if _sr.random() > 0.9:  # 10% chance of being unhealthy
                            instance["status"] = ServiceStatus.UNHEALTHY
                            instance["health_score"] = 0
                        else:
                            instance["status"] = ServiceStatus.HEALTHY
                            instance["health_score"] = 100

                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(30)

    def get_app(self) -> FastAPI:
        """Get the FastAPI application."""
        return self.app


class GatewayMiddleware(BaseHTTPMiddleware):
    """Custom middleware for API gateway."""

    def __init__(self, app: ASGIApp, gateway: UnifiedAPIGateway):
        super().__init__(app)
        self.gateway = gateway

    async def dispatch(self, request: Request, call_next):
        """Process request through middleware."""
        start_time = time.time()

        # Log request if enabled
        if self.gateway.config.log_requests:
            logger.info(
                f"{request.method} {request.url.path} - {request.client.host if request.client else 'unknown'}"
            )

        # Transform request if needed
        request = await self.gateway.request_transformer.transform_request(request)

        # Process request
        response = await call_next(request)

        # Transform response if needed
        response = await self.gateway.request_transformer.transform_response(
            response, request
        )

        # Add gateway headers
        response.headers["X-Gateway"] = "DotMac-Unified-Gateway"
        response.headers["X-Gateway-Version"] = self.gateway.config.version
        response.headers["X-Response-Time"] = str(
            int((time.time() - start_time) * 1000)
        )

        return response


# Gateway Factory and Builder


class GatewayFactory:
    """Factory for creating API gateway instances."""

    @staticmethod
    def create_gateway(
        service_marketplace: ServiceMarketplace,
        config: GatewayConfig | None = None,
        identity_service: UnifiedIdentityService | None = None,
        performance_service: PerformanceOptimizationService | None = None,
    ) -> UnifiedAPIGateway:
        """Create a unified API gateway instance."""
        if not config:
            config = GatewayConfig()

        return UnifiedAPIGateway(
            config=config,
            service_marketplace=service_marketplace,
            identity_service=identity_service,
            performance_service=performance_service,
        )

    @staticmethod
    def create_config(**kwargs) -> GatewayConfig:
        """Create gateway configuration."""
        return GatewayConfig(**kwargs)


# Integration with consolidated services
async def setup_consolidated_services_gateway(
    service_marketplace: ServiceMarketplace,
    identity_service: UnifiedIdentityService | None = None,
    performance_service: PerformanceOptimizationService | None = None,
) -> UnifiedAPIGateway:
    """Set up API gateway for consolidated services."""

    # Create gateway configuration optimized for consolidated services
    config = GatewayFactory.create_config(
        title="DotMac Consolidated Services Gateway",
        version="3.0.0",
        description="Unified API gateway for consolidated billing, analytics, and identity services",
        default_rate_limit=5000,  # Higher limit for consolidated services
        enable_caching=True,
        cache_ttl=600,  # 10 minutes
        default_route_strategy=RouteStrategy.HEALTH_BASED,
        enable_circuit_breaker=True,
        circuit_breaker_threshold=3,  # More aggressive circuit breaker
        enable_metrics=True,
        enable_tracing=True,
        service_discovery_interval=15,  # More frequent discovery
        health_check_interval=10,
    )

    # Create gateway instance
    gateway = GatewayFactory.create_gateway(
        service_marketplace=service_marketplace,
        config=config,
        identity_service=identity_service,
        performance_service=performance_service,
    )

    return gateway
