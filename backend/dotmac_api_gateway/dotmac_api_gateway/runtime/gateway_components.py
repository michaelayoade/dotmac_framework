"""
Refactored API Gateway components with single responsibilities.
Extracted from monolithic APIGatewayApp class.
"""

import logging
import time
import uuid
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response
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


class SDKManager:
    """Manages SDK lifecycle and provides access to SDK instances."""

    def __init__(self, config: GatewayConfig):
        self.config = config
        self._sdks: Dict[str, Any] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize all SDK instances."""
        if self._initialized:
            return

        tenant_id = self.config.tenant_id or "default"

        self._sdks = {
            "gateway": GatewaySDK(tenant_id=tenant_id),
            "auth": AuthenticationProxySDK(tenant_id=tenant_id),
            "rate_limit": RateLimitingSDK(tenant_id=tenant_id),
            "versioning": APIVersioningSDK(tenant_id=tenant_id),
            "analytics": GatewayAnalyticsSDK(tenant_id=tenant_id),
            "documentation": APIDocumentationSDK(tenant_id=tenant_id),
        }

        self._initialized = True
        logger.info(f"Initialized SDKs for tenant: {tenant_id}")

    async def cleanup(self):
        """Cleanup SDK resources."""
        self._sdks.clear()
        self._initialized = False
        logger.info("SDK cleanup complete")

    def get_sdk(self, name: str) -> Optional[Any]:
        """Get SDK instance by name."""
        return self._sdks.get(name)

    @property
    def is_initialized(self) -> bool:
        """Check if SDKs are initialized."""
        return self._initialized


class GatewayMiddleware:
    """Handles core gateway middleware functionality."""

    def __init__(self, config: GatewayConfig):
        self.config = config

    async def process_request(self, request: Request, call_next: Callable) -> Response:
        """Core gateway middleware for request processing."""
        # Add request ID
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


class AnalyticsMiddleware:
    """Handles analytics and metrics collection."""

    def __init__(self, sdk_manager: SDKManager):
        self.sdk_manager = sdk_manager

    async def process_request(self, request: Request, call_next: Callable) -> Response:
        """Analytics middleware for request tracking."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Record metrics
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        try:
            analytics_sdk = self.sdk_manager.get_sdk("analytics")
            if analytics_sdk:
                await analytics_sdk.record_request_metric(
                    gateway_id="default",
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    response_time_ms=response_time,
                    request_size_bytes=self._get_request_size(request),
                    response_size_bytes=self._get_response_size(response),
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
        except Exception as e:
            logger.warning(f"Failed to record analytics: {e}")

        return response

    def _get_request_size(self, request: Request) -> int:
        """Get request body size safely."""
        try:
            return len(request.body()) if hasattr(request, "body") else 0
        except Exception:
            return 0

    def _get_response_size(self, response: Response) -> int:
        """Get response body size safely."""
        try:
            return len(response.body) if hasattr(response, "body") else 0
        except Exception:
            return 0


class RateLimitMiddleware:
    """Handles rate limiting functionality."""

    def __init__(self, sdk_manager: SDKManager):
        self.sdk_manager = sdk_manager
        self.excluded_paths = {"/health", "/docs", "/redoc", "/openapi.json"}

    async def process_request(self, request: Request, call_next: Callable) -> Response:
        """Rate limiting middleware."""
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        try:
            # Get rate limit policy (in a real implementation, this would be route-specific)
            rate_limit_sdk = self.sdk_manager.get_sdk("rate_limit")
            if rate_limit_sdk and hasattr(request.state, "rate_limit_policy"):
                identifier = request.client.host if request.client else "unknown"

                await rate_limit_sdk.check_rate_limit(
                    policy_id=request.state.rate_limit_policy,
                    identifier=identifier
                )
        except RateLimitError as e:
            return self._create_rate_limit_error_response(request, e)
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")

        return await call_next(request)

    def _create_rate_limit_error_response(self, request: Request, error: RateLimitError) -> JSONResponse:
        """Create rate limit error response."""
        return JSONResponse(
            status_code=429,
            content={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": str(error),
                "request_id": getattr(request.state, "request_id", None)
            }
        )


class AuthenticationMiddleware:
    """Handles authentication functionality."""

    def __init__(self, sdk_manager: SDKManager):
        self.sdk_manager = sdk_manager
        self.public_paths = {"/health", "/docs", "/redoc", "/openapi.json"}

    async def process_request(self, request: Request, call_next: Callable) -> Response:
        """Authentication middleware."""
        # Skip auth for public endpoints
        if request.url.path in self.public_paths:
            return await call_next(request)

        try:
            # Get auth policy (in a real implementation, this would be route-specific)
            auth_sdk = self.sdk_manager.get_sdk("auth")
            if auth_sdk and hasattr(request.state, "auth_policy"):
                auth_result = await auth_sdk.authenticate_request(
                    headers=dict(request.headers),
                    query_params=dict(request.query_params),
                    policy_id=request.state.auth_policy
                )

                # Add auth context to request
                request.state.auth_user = auth_result
        except (AuthenticationError, AuthorizationError) as e:
            return self._create_auth_error_response(request, e)
        except Exception as e:
            logger.warning(f"Authentication check failed: {e}")

        return await call_next(request)

    def _create_auth_error_response(self, request: Request, error: Exception) -> JSONResponse:
        """Create authentication error response."""
        return JSONResponse(
            status_code=401,
            content={
                "error": "AUTHENTICATION_FAILED",
                "message": str(error),
                "request_id": getattr(request.state, "request_id", None)
            }
        )


class ExceptionHandlerRegistry:
    """Manages registration of exception handlers."""

    def register_handlers(self, app: FastAPI):
        """Register all exception handlers with the app."""
        self._register_gateway_error_handler(app)
        self._register_auth_error_handlers(app)
        self._register_rate_limit_error_handler(app)
        self._register_routing_error_handler(app)
        self._register_config_error_handler(app)

    def _register_gateway_error_handler(self, app: FastAPI):
        """Register gateway error handler."""
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

    def _register_auth_error_handlers(self, app: FastAPI):
        """Register authentication and authorization error handlers."""
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

    def _register_rate_limit_error_handler(self, app: FastAPI):
        """Register rate limit error handler."""
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

    def _register_routing_error_handler(self, app: FastAPI):
        """Register routing error handler."""
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

    def _register_config_error_handler(self, app: FastAPI):
        """Register configuration error handler."""
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


class RouteRegistry:
    """Manages registration of API routes."""

    def __init__(self, config: GatewayConfig, sdk_manager: SDKManager):
        self.config = config
        self.sdk_manager = sdk_manager

    def register_routes(self, app: FastAPI):
        """Register all routes with the app."""
        self._register_health_routes(app)
        self._register_gateway_routes(app)
        self._register_auth_routes(app)
        self._register_rate_limit_routes(app)

    def _register_health_routes(self, app: FastAPI):
        """Register health and monitoring routes."""
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
            analytics_sdk = self.sdk_manager.get_sdk("analytics")
            if not analytics_sdk:
                raise HTTPException(status_code=503, detail="Analytics service unavailable")

            metrics = await analytics_sdk.get_request_metrics(
                gateway_id="default",
                time_range="1h"
            )

            return metrics

    def _register_gateway_routes(self, app: FastAPI):
        """Register gateway management routes."""
        @app.post("/gateway/routes")
        async def create_route(request: Request):
            """Create gateway route."""
            gateway_sdk = self.sdk_manager.get_sdk("gateway")
            if not gateway_sdk:
                raise HTTPException(status_code=503, detail="Gateway service unavailable")

            data = await request.json()
            route = await gateway_sdk.create_route(**data)
            return route

        @app.get("/gateway/routes")
        async def list_routes():
            """List gateway routes."""
            gateway_sdk = self.sdk_manager.get_sdk("gateway")
            if not gateway_sdk:
                raise HTTPException(status_code=503, detail="Gateway service unavailable")

            routes = await gateway_sdk.list_routes(gateway_id="default")
            return routes

    def _register_auth_routes(self, app: FastAPI):
        """Register authentication management routes."""
        @app.post("/auth/policies")
        async def create_auth_policy(request: Request):
            """Create authentication policy."""
            auth_sdk = self.sdk_manager.get_sdk("auth")
            if not auth_sdk:
                raise HTTPException(status_code=503, detail="Auth service unavailable")

            data = await request.json()
            policy = await auth_sdk.create_auth_policy(**data)
            return policy

    def _register_rate_limit_routes(self, app: FastAPI):
        """Register rate limit management routes."""
        @app.post("/rate-limit/policies")
        async def create_rate_limit_policy(request: Request):
            """Create rate limit policy."""
            rate_limit_sdk = self.sdk_manager.get_sdk("rate_limit")
            if not rate_limit_sdk:
                raise HTTPException(status_code=503, detail="Rate limit service unavailable")

            data = await request.json()
            policy = await rate_limit_sdk.create_rate_limit_policy(**data)
            return policy


class MiddlewareRegistry:
    """Manages registration of middleware."""

    def __init__(self, config: GatewayConfig, sdk_manager: SDKManager):
        self.config = config
        self.sdk_manager = sdk_manager

    def register_middleware(self, app: FastAPI):
        """Register all middleware with the app."""
        self._register_security_middleware(app)
        self._register_cors_middleware(app)
        self._register_custom_middleware(app)

    def _register_security_middleware(self, app: FastAPI):
        """Register security middleware."""
        # Trusted Host Middleware
        if self.config.security.allowed_hosts:
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=self.config.security.allowed_hosts
            )

    def _register_cors_middleware(self, app: FastAPI):
        """Register CORS middleware."""
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.security.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _register_custom_middleware(self, app: FastAPI):
        """Register custom middleware in proper order."""
        # Create middleware instances
        gateway_middleware = GatewayMiddleware(self.config)
        analytics_middleware = AnalyticsMiddleware(self.sdk_manager)
        rate_limit_middleware = RateLimitMiddleware(self.sdk_manager)
        auth_middleware = AuthenticationMiddleware(self.sdk_manager)

        # Register middleware (order matters - last registered runs first)
        app.middleware("http")(auth_middleware.process_request)
        app.middleware("http")(rate_limit_middleware.process_request)
        app.middleware("http")(analytics_middleware.process_request)
        app.middleware("http")(gateway_middleware.process_request)
