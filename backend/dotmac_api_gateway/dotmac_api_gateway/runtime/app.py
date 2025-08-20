"""
API Gateway Runtime Application Factory - FastAPI application with middleware integration.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from ..core.config import GatewayConfig
from ..core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    GatewayError,
    RateLimitError,
    RoutingError,
)
from ..sdks.api_documentation import APIDocumentationSDK
from ..sdks.api_versioning import APIVersioningSDK
from ..sdks.authentication_proxy import AuthenticationProxySDK
from ..sdks.gateway import GatewaySDK
from ..sdks.gateway_analytics import GatewayAnalyticsSDK
from ..sdks.rate_limiting import RateLimitingSDK

logger = logging.getLogger(__name__)


class APIGatewayApp:
    """API Gateway application factory."""

    def __init__(self, config: GatewayConfig):
        self.config = config
        self.app: Optional[FastAPI] = None
        self._sdks: Dict[str, Any] = {}

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Application lifespan manager."""
        # Startup
        await self._initialize_sdks()
        logger.info("API Gateway started successfully")

        yield

        # Shutdown
        await self._cleanup_sdks()
        logger.info("API Gateway shutdown complete")

    async def _initialize_sdks(self):
        """Initialize SDK instances."""
        tenant_id = self.config.tenant_id or "default"

        self._sdks = {
            "gateway": GatewaySDK(tenant_id=tenant_id),
            "auth": AuthenticationProxySDK(tenant_id=tenant_id),
            "rate_limit": RateLimitingSDK(tenant_id=tenant_id),
            "versioning": APIVersioningSDK(tenant_id=tenant_id),
            "analytics": GatewayAnalyticsSDK(tenant_id=tenant_id),
            "documentation": APIDocumentationSDK(tenant_id=tenant_id),
        }

        logger.info(f"Initialized SDKs for tenant: {tenant_id}")

    async def _cleanup_sdks(self):
        """Cleanup SDK resources."""
        self._sdks.clear()

    def create_app(self) -> FastAPI:
        """Create FastAPI application with middleware and routes."""
        app = FastAPI(
            title="DotMac API Gateway",
            description="ISP Operations API Gateway",
            version="1.0.0",
            debug=self.config.debug,
            lifespan=self.lifespan,
            docs_url="/docs" if self.config.debug else None,
            redoc_url="/redoc" if self.config.debug else None,
            openapi_url="/openapi.json" if self.config.debug else None,
        )

        # Add middleware
        self._add_middleware(app)

        # Add exception handlers
        self._add_exception_handlers(app)

        # Add routes
        self._add_routes(app)

        self.app = app
        return app

    def _add_middleware(self, app: FastAPI):
        """Add middleware to the application."""

        # Trusted Host Middleware
        if self.config.security.allowed_hosts:
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=self.config.security.allowed_hosts
            )

        # CORS Middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.security.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Custom middleware
        app.middleware("http")(self._gateway_middleware)
        app.middleware("http")(self._analytics_middleware)
        app.middleware("http")(self._rate_limit_middleware)
        app.middleware("http")(self._auth_middleware)

    async def _gateway_middleware(self, request: Request, call_next):
        """Core gateway middleware for request processing."""
        # Add request ID
        import uuid
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Add tenant context
        request.state.tenant_id = self.config.tenant_id

        # Process request
        response = await call_next(request)

        # Add gateway headers
        response.headers["X-Gateway-Request-ID"] = request_id
        response.headers["X-Gateway-Version"] = "1.0.0"

        return response

    async def _analytics_middleware(self, request: Request, call_next):
        """Analytics middleware for request tracking."""
        import time

        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Record metrics
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        try:
            analytics_sdk = self._sdks.get("analytics")
            if analytics_sdk:
                await analytics_sdk.record_request_metric(
                    gateway_id="default",
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    response_time_ms=response_time,
                    request_size_bytes=len(await request.body()) if hasattr(request, "body") else 0,
                    response_size_bytes=len(response.body) if hasattr(response, "body") else 0,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
        except Exception as e:
            logger.warning(f"Failed to record analytics: {e}")

        return response

    async def _rate_limit_middleware(self, request: Request, call_next):
        """Rate limiting middleware."""
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        try:
            # Get rate limit policy (in a real implementation, this would be route-specific)
            rate_limit_sdk = self._sdks.get("rate_limit")
            if rate_limit_sdk and hasattr(request.state, "rate_limit_policy"):
                identifier = request.client.host if request.client else "unknown"

                await rate_limit_sdk.check_rate_limit(
                    policy_id=request.state.rate_limit_policy,
                    identifier=identifier
                )
        except RateLimitError as e:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": str(e),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")

        return await call_next(request)

    async def _auth_middleware(self, request: Request, call_next):
        """Authentication middleware."""
        # Skip auth for public endpoints
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        try:
            # Get auth policy (in a real implementation, this would be route-specific)
            auth_sdk = self._sdks.get("auth")
            if auth_sdk and hasattr(request.state, "auth_policy"):
                auth_result = await auth_sdk.authenticate_request(
                    headers=dict(request.headers),
                    query_params=dict(request.query_params),
                    policy_id=request.state.auth_policy
                )

                # Add auth context to request
                request.state.auth_user = auth_result
        except (AuthenticationError, AuthorizationError) as e:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "AUTHENTICATION_FAILED",
                    "message": str(e),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
        except Exception as e:
            logger.warning(f"Authentication check failed: {e}")

        return await call_next(request)

    def _add_exception_handlers(self, app: FastAPI):
        """Add custom exception handlers."""

        @app.exception_handler(GatewayError)
        async def gateway_error_handler(request: Request, exc: GatewayError):
            return JSONResponse(
                status_code=500,
                content={
                    "error": "GATEWAY_ERROR",
                    "message": str(exc),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )

        @app.exception_handler(AuthenticationError)
        async def auth_error_handler(request: Request, exc: AuthenticationError):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "AUTHENTICATION_ERROR",
                    "message": str(exc),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )

        @app.exception_handler(AuthorizationError)
        async def authz_error_handler(request: Request, exc: AuthorizationError):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "AUTHORIZATION_ERROR",
                    "message": str(exc),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )

        @app.exception_handler(RateLimitError)
        async def rate_limit_error_handler(request: Request, exc: RateLimitError):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_ERROR",
                    "message": str(exc),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )

        @app.exception_handler(RoutingError)
        async def routing_error_handler(request: Request, exc: RoutingError):
            return JSONResponse(
                status_code=404,
                content={
                    "error": "ROUTING_ERROR",
                    "message": str(exc),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )

        @app.exception_handler(ConfigurationError)
        async def config_error_handler(request: Request, exc: ConfigurationError):
            return JSONResponse(
                status_code=500,
                content={
                    "error": "CONFIGURATION_ERROR",
                    "message": str(exc),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )

    def _add_routes(self, app: FastAPI):  # noqa: C901
        """Add API routes."""

        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "service": "dotmac-api-gateway",
                "version": "1.0.0",
                "environment": self.config.environment
            }

        @app.get("/metrics")
        async def metrics():
            """Metrics endpoint for monitoring."""
            analytics_sdk = self._sdks.get("analytics")
            if not analytics_sdk:
                raise HTTPException(status_code=503, detail="Analytics service unavailable")

            metrics = await analytics_sdk.get_request_metrics(
                gateway_id="default",
                time_range="1h"
            )

            return metrics

        @app.post("/gateway/routes")
        async def create_route(request: Request):
            """Create gateway route."""
            gateway_sdk = self._sdks.get("gateway")
            if not gateway_sdk:
                raise HTTPException(status_code=503, detail="Gateway service unavailable")

            data = await request.json()
            route = await gateway_sdk.create_route(**data)
            return route

        @app.get("/gateway/routes")
        async def list_routes():
            """List gateway routes."""
            gateway_sdk = self._sdks.get("gateway")
            if not gateway_sdk:
                raise HTTPException(status_code=503, detail="Gateway service unavailable")

            routes = await gateway_sdk.list_routes(gateway_id="default")
            return routes

        @app.post("/auth/policies")
        async def create_auth_policy(request: Request):
            """Create authentication policy."""
            auth_sdk = self._sdks.get("auth")
            if not auth_sdk:
                raise HTTPException(status_code=503, detail="Auth service unavailable")

            data = await request.json()
            policy = await auth_sdk.create_auth_policy(**data)
            return policy

        @app.post("/rate-limit/policies")
        async def create_rate_limit_policy(request: Request):
            """Create rate limit policy."""
            rate_limit_sdk = self._sdks.get("rate_limit")
            if not rate_limit_sdk:
                raise HTTPException(status_code=503, detail="Rate limit service unavailable")

            data = await request.json()
            policy = await rate_limit_sdk.create_rate_limit_policy(**data)
            return policy

    def run(self, host: str = "127.0.0.1", port: int = 8000, **kwargs):
        """Run the API Gateway server."""
        if not self.app:
            self.create_app()

        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info" if not self.config.debug else "debug",
            **kwargs
        )


def create_gateway_app(config: GatewayConfig) -> FastAPI:
    """Factory function to create API Gateway application."""
    gateway = APIGatewayApp(config)
    return gateway.create_app()


def run_gateway(config_path: str = None, **kwargs):
    """Run API Gateway server with configuration."""
    if config_path:
        import json
        with open(config_path) as f:
            config_data = json.load(f)
        config = GatewayConfig(**config_data)
    else:
        config = GatewayConfig()

    gateway = APIGatewayApp(config)
    gateway.create_app()
    gateway.run(**kwargs)


if __name__ == "__main__":
    run_gateway()
