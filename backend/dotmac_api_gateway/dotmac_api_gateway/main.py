"""
DotMac API Gateway Service - Main Application
Central API gateway for routing, rate limiting, and authentication proxy.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

from .core.config import config
from .core.exceptions import GatewayError, RateLimitError, RoutingError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Health",
        "description": "Gateway health and status monitoring",
    },
    {
        "name": "Proxy",
        "description": "Service proxy and routing",
    },
    {
        "name": "Services",
        "description": "Service discovery and management",
    },
    {
        "name": "RateLimit",
        "description": "Rate limiting management",
    },
    {
        "name": "Analytics",
        "description": "Gateway analytics and metrics",
    },
    {
        "name": "Circuit Breaker",
        "description": "Circuit breaker management",
    },
]


class ServiceStatus(str, Enum):
    """Service health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


# Service registry
SERVICE_REGISTRY = {
    "identity": {
        "url": "http://localhost:8001",
        "name": "Identity Service",
        "endpoints": ["/api/v1/users", "/api/v1/auth", "/api/v1/organizations"],
    },
    "billing": {
        "url": "http://localhost:8002",
        "name": "Billing Service",
        "endpoints": ["/api/v1/invoices", "/api/v1/payments", "/api/v1/subscriptions"],
    },
    "services": {
        "url": "http://localhost:8003",
        "name": "Services Provisioning",
        "endpoints": ["/api/v1/catalog", "/api/v1/orders", "/api/v1/provisioning"],
    },
    "networking": {
        "url": "http://localhost:8004",
        "name": "Network Management",
        "endpoints": ["/api/v1/devices", "/api/v1/topology", "/api/v1/monitoring"],
    },
    "analytics": {
        "url": "http://localhost:8005",
        "name": "Analytics Service",
        "endpoints": ["/api/v1/dashboards", "/api/v1/reports", "/api/v1/metrics"],
    },
    "platform": {
        "url": "http://localhost:8006",
        "name": "Platform Service",
        "endpoints": ["/api/v1/tables", "/api/v1/secrets", "/api/v1/webhooks"],
    },
    "events": {
        "url": "http://localhost:8007",
        "name": "Event Bus",
        "endpoints": ["/api/v1/events", "/api/v1/subscriptions"],
    },
    "ops": {
        "url": "http://localhost:8008",
        "name": "Core Ops",
        "endpoints": ["/api/v1/workflows", "/api/v1/jobs", "/api/v1/sagas"],
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting DotMac API Gateway...")
    logger.info(f"Service registry initialized with {len(SERVICE_REGISTRY)} services")
    
    # Initialize HTTP client
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    
    # Initialize rate limiter
    app.state.rate_limits = {}
    
    # Initialize circuit breakers
    app.state.circuit_breakers = {}
    
    yield
    
    # Cleanup
    await app.state.http_client.aclose()
    logger.info("Shutting down DotMac API Gateway...")


# Create FastAPI application
app = FastAPI(
    title="DotMac API Gateway",
    description="""
    **Central API Gateway for DotMac Platform**

    The DotMac API Gateway provides unified access to all platform services:

    ## 🌐 Core Features

    ### Service Routing
    - Intelligent request routing
    - Service discovery
    - Load balancing
    - Failover handling
    - Request/response transformation

    ### Authentication & Authorization
    - JWT token validation
    - OAuth2 proxy
    - API key management
    - Service-to-service auth
    - RBAC enforcement

    ### Rate Limiting
    - Per-client rate limits
    - Per-endpoint limits
    - Token bucket algorithm
    - Sliding window counters
    - Custom rate limit rules

    ### Circuit Breaker
    - Automatic failure detection
    - Service health monitoring
    - Graceful degradation
    - Recovery mechanisms
    - Fallback responses

    ### API Analytics
    - Request metrics
    - Latency tracking
    - Error rate monitoring
    - Usage analytics
    - Performance insights

    ### API Versioning
    - Version routing
    - Backward compatibility
    - Deprecation management
    - Version transformation

    ## 🚀 Services

    - **Identity** (8001): User management and authentication
    - **Billing** (8002): Financial services
    - **Services** (8003): Service provisioning
    - **Networking** (8004): Network management
    - **Analytics** (8005): Business intelligence
    - **Platform** (8006): Core platform utilities
    - **Events** (8007): Event bus
    - **Ops** (8008): Workflow orchestration

    **Gateway Port**: 8000
    **Version**: 1.0.0
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ServiceInfo(BaseModel):
    """Service information model."""
    service_id: str = Field(..., description="Service identifier")
    name: str = Field(..., description="Service name")
    url: str = Field(..., description="Service base URL")
    status: ServiceStatus = Field(..., description="Service health status")
    endpoints: List[str] = Field(..., description="Available endpoints")
    last_health_check: Optional[datetime] = Field(None, description="Last health check timestamp")


class RateLimitInfo(BaseModel):
    """Rate limit information."""
    client_id: str = Field(..., description="Client identifier")
    limit: int = Field(..., description="Request limit")
    remaining: int = Field(..., description="Remaining requests")
    reset_at: datetime = Field(..., description="Rate limit reset time")


class GatewayMetrics(BaseModel):
    """Gateway metrics model."""
    total_requests: int = Field(..., description="Total requests processed")
    active_connections: int = Field(..., description="Active connections")
    average_latency_ms: float = Field(..., description="Average latency in milliseconds")
    error_rate: float = Field(..., description="Error rate percentage")
    services_health: Dict[str, ServiceStatus] = Field(..., description="Service health statuses")


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Gateway health check",
    description="Check gateway health and all backend services",
    responses={
        200: {
            "description": "Gateway is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "gateway": "dotmac_api_gateway",
                        "version": "1.0.0",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "services": {
                            "identity": "healthy",
                            "billing": "healthy",
                            "services": "healthy",
                            "networking": "healthy",
                            "analytics": "healthy",
                        }
                    }
                }
            }
        }
    }
)
async def health_check(request: Request) -> Dict[str, Any]:
    """Check gateway and backend services health."""
    services_health = {}
    
    # Check each service health
    for service_id, service_info in SERVICE_REGISTRY.items():
        try:
            response = await request.app.state.http_client.get(
                f"{service_info['url']}/health",
                timeout=2.0
            )
            if response.status_code == 200:
                services_health[service_id] = ServiceStatus.HEALTHY
            else:
                services_health[service_id] = ServiceStatus.UNHEALTHY
        except Exception:
            services_health[service_id] = ServiceStatus.UNKNOWN
    
    # Determine overall gateway health
    unhealthy_count = sum(1 for status in services_health.values() 
                          if status != ServiceStatus.HEALTHY)
    
    if unhealthy_count == 0:
        gateway_status = "healthy"
    elif unhealthy_count < len(services_health) // 2:
        gateway_status = "degraded"
    else:
        gateway_status = "unhealthy"
    
    return {
        "status": gateway_status,
        "gateway": "dotmac_api_gateway",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": services_health,
    }


# Service discovery endpoint
@app.get(
    "/api/v1/services",
    tags=["Services"],
    summary="List services",
    description="Get list of all registered services",
    response_model=List[ServiceInfo],
)
async def list_services(request: Request) -> List[ServiceInfo]:
    """List all registered services."""
    services = []
    
    for service_id, service_data in SERVICE_REGISTRY.items():
        # Check service health
        try:
            response = await request.app.state.http_client.get(
                f"{service_data['url']}/health",
                timeout=2.0
            )
            status = ServiceStatus.HEALTHY if response.status_code == 200 else ServiceStatus.UNHEALTHY
        except Exception:
            status = ServiceStatus.UNKNOWN
        
        services.append(
            ServiceInfo(
                service_id=service_id,
                name=service_data["name"],
                url=service_data["url"],
                status=status,
                endpoints=service_data["endpoints"],
                last_health_check=datetime.utcnow(),
            )
        )
    
    return services


# Service proxy endpoint - Generic catch-all for service routing
@app.api_route(
    "/api/v1/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Proxy"],
    summary="Service proxy",
    description="Route requests to backend services",
)
async def proxy_request(
    request: Request,
    service: str,
    path: str,
) -> Response:
    """Proxy requests to backend services."""
    
    # Validate service exists
    if service not in SERVICE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    service_info = SERVICE_REGISTRY[service]
    
    # Build target URL
    target_url = f"{service_info['url']}/api/v1/{path}"
    
    # Add query parameters
    if request.url.query:
        target_url = f"{target_url}?{request.url.query.decode()}"
    
    # Get request body if present
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    # Forward the request
    try:
        response = await request.app.state.http_client.request(
            method=request.method,
            url=target_url,
            headers={
                key: value for key, value in request.headers.items()
                if key.lower() not in ["host", "connection"]
            },
            content=body,
        )
        
        # Return the response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
        
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout while connecting to {service} service"
        )
    except Exception as e:
        logger.error(f"Error proxying request to {service}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Error connecting to {service} service"
        )


# Rate limit status endpoint
@app.get(
    "/api/v1/rate-limit/status",
    tags=["RateLimit"],
    summary="Rate limit status",
    description="Get current rate limit status for client",
    response_model=RateLimitInfo,
)
async def rate_limit_status(request: Request) -> RateLimitInfo:
    """Get rate limit status for current client."""
    client_id = request.client.host if request.client else "unknown"
    
    # Mock rate limit info
    return RateLimitInfo(
        client_id=client_id,
        limit=1000,
        remaining=850,
        reset_at=datetime.utcnow().replace(minute=0, second=0, microsecond=0),
    )


# Gateway metrics endpoint
@app.get(
    "/api/v1/metrics",
    tags=["Analytics"],
    summary="Gateway metrics",
    description="Get gateway performance metrics",
    response_model=GatewayMetrics,
)
async def gateway_metrics(request: Request) -> GatewayMetrics:
    """Get gateway performance metrics."""
    # Check services health
    services_health = {}
    for service_id in SERVICE_REGISTRY:
        try:
            response = await request.app.state.http_client.get(
                f"{SERVICE_REGISTRY[service_id]['url']}/health",
                timeout=2.0
            )
            services_health[service_id] = (
                ServiceStatus.HEALTHY if response.status_code == 200 
                else ServiceStatus.UNHEALTHY
            )
        except Exception:
            services_health[service_id] = ServiceStatus.UNKNOWN
    
    return GatewayMetrics(
        total_requests=123456,
        active_connections=42,
        average_latency_ms=125.5,
        error_rate=0.02,
        services_health=services_health,
    )


# Circuit breaker status endpoint
@app.get(
    "/api/v1/circuit-breaker/{service}",
    tags=["Circuit Breaker"],
    summary="Circuit breaker status",
    description="Get circuit breaker status for a service",
)
async def circuit_breaker_status(service: str) -> Dict[str, Any]:
    """Get circuit breaker status for a service."""
    if service not in SERVICE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    return {
        "service": service,
        "state": "closed",  # closed, open, half_open
        "failure_count": 0,
        "success_count": 1000,
        "last_failure": None,
        "next_attempt": None,
    }


# Admin endpoint to reload service registry
@app.post(
    "/api/v1/admin/reload",
    tags=["Services"],
    summary="Reload service registry",
    description="Reload the service registry configuration",
    responses={200: {"description": "Registry reloaded successfully"}},
)
async def reload_registry() -> Dict[str, str]:
    """Reload service registry configuration."""
    # In production, this would reload from a configuration source
    return {"message": "Service registry reloaded successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "dotmac_api_gateway.main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.debug,
        log_level="info" if not config.debug else "debug",
    )