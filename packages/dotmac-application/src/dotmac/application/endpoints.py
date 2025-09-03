"""
Standard endpoints for all DotMac applications.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .config import DeploymentMode, PlatformConfig

logger = logging.getLogger(__name__)


class StandardEndpoints:
    """Standard endpoints that all DotMac applications should have."""

    def __init__(self, platform_config: PlatformConfig):
        self.platform_config = platform_config
        self.added_endpoints: List[str] = []

    def add_to_app(self, app: FastAPI) -> List[str]:
        """Add standard endpoints to FastAPI application."""
        logger.info(
            f"Adding standard endpoints for {self.platform_config.platform_name}"
        )

        # Add core endpoints
        self._add_root_endpoint(app)
        self._add_favicon_endpoint(app)

        # Add health endpoints (basic stubs)
        self._add_health_endpoints(app)

        # Add deployment-specific endpoints
        if self.platform_config.deployment_context:
            mode = self.platform_config.deployment_context.mode

            if mode == DeploymentMode.TENANT_CONTAINER:
                self._add_tenant_endpoints(app)
            elif mode == DeploymentMode.MANAGEMENT_PLATFORM:
                self._add_management_endpoints(app)
            elif mode == DeploymentMode.DEVELOPMENT:
                self._add_development_endpoints(app)

        logger.info(f"Added endpoints: {self.added_endpoints}")
        return self.added_endpoints

    def _add_root_endpoint(self, app: FastAPI):
        """Add root endpoint with platform information."""

        @app.get("/", tags=["System"])
        async def root(request: Request):
            """Root endpoint with platform information and status."""

            # Get basic platform info
            info = {
                "platform": self.platform_config.platform_name,
                "title": self.platform_config.title,
                "version": self.platform_config.version,
                "status": "operational",
            }

            # Add deployment context if available
            if self.platform_config.deployment_context:
                context = self.platform_config.deployment_context
                info["deployment"] = {
                    "mode": context.mode,
                    "isolation_level": context.isolation_level,
                }

                if context.tenant_id:
                    info["tenant_id"] = context.tenant_id

            # Add health status if available
            if hasattr(app.state, "health_config"):
                info["health"] = {
                    "enabled_checks": app.state.health_config.get("enabled_checks", []),
                    "status": "ready"
                }

            return JSONResponse(content=info)

        self.added_endpoints.append("GET /")

    def _add_favicon_endpoint(self, app: FastAPI):
        """Add favicon endpoint."""

        @app.get("/favicon.ico", include_in_schema=False)
        async def favicon():
            """Favicon endpoint - returns 204 No Content."""
            return Response(status_code=204)

        self.added_endpoints.append("GET /favicon.ico")

    def _add_health_endpoints(self, app: FastAPI):
        """Add basic health check endpoints."""

        @app.get("/health", tags=["Health"])
        async def health():
            """Basic health check endpoint."""
            return JSONResponse({
                "status": "healthy",
                "platform": self.platform_config.platform_name,
                "version": self.platform_config.version,
                "timestamp": getattr(app.state, "startup_time", "unknown")
            })

        @app.get("/health/live", tags=["Health"])
        async def health_live():
            """Liveness probe endpoint for Kubernetes."""
            return JSONResponse({"status": "alive"})

        @app.get("/health/ready", tags=["Health"])
        async def health_ready():
            """Readiness probe endpoint for Kubernetes."""
            # Basic readiness check
            ready = True
            checks = []

            # Check if basic configuration is valid
            if hasattr(app.state, "config_validated"):
                checks.append({
                    "name": "configuration",
                    "status": "healthy" if app.state.config_validated else "unhealthy"
                })
                if not app.state.config_validated:
                    ready = False
            else:
                checks.append({"name": "configuration", "status": "unknown"})

            return JSONResponse({
                "status": "ready" if ready else "not_ready",
                "checks": checks
            })

        @app.get("/health/startup", tags=["Health"])
        async def health_startup():
            """Startup probe endpoint for Kubernetes."""
            return JSONResponse({
                "status": "started",
                "platform": self.platform_config.platform_name
            })

        self.added_endpoints.extend([
            "GET /health", 
            "GET /health/live", 
            "GET /health/ready", 
            "GET /health/startup"
        ])

    def _add_tenant_endpoints(self, app: FastAPI):
        """Add tenant container specific endpoints."""
        context = self.platform_config.deployment_context

        @app.get("/tenant/info", tags=["Tenant"])
        async def tenant_info():
            """Tenant container information."""
            return JSONResponse(
                {
                    "tenant_id": context.tenant_id,
                    "isolation_level": context.isolation_level,
                    "resource_limits": (
                        context.resource_limits.__dict__
                        if context.resource_limits
                        else None
                    ),
                    "kubernetes_namespace": context.kubernetes_namespace,
                    "container_name": context.container_name,
                }
            )

        self.added_endpoints.append("GET /tenant/info")

    def _add_management_endpoints(self, app: FastAPI):
        """Add management platform specific endpoints."""

        @app.get("/management/stats", tags=["Management"])
        async def management_stats():
            """Management platform statistics."""
            stats = {
                "platform": "management",
                "status": "operational",
                "features": self.platform_config.feature_config.enabled_features,
            }

            # Add basic app state info if available
            if hasattr(app.state, "applied_middleware"):
                stats["middleware_count"] = len(app.state.applied_middleware)

            if hasattr(app.state, "registration_stats"):
                stats["routers"] = app.state.registration_stats

            return JSONResponse(stats)

        self.added_endpoints.append("GET /management/stats")

    def _add_development_endpoints(self, app: FastAPI):
        """Add development-specific endpoints."""

        @app.get("/dev/config", tags=["Development"])
        async def development_config():
            """Show current platform configuration (development only)."""
            return JSONResponse(
                {
                    "platform_config": {
                        "platform_name": self.platform_config.platform_name,
                        "title": self.platform_config.title,
                        "routers": [
                            {
                                "module_path": r.module_path,
                                "prefix": r.prefix,
                                "auto_discover": r.auto_discover,
                            }
                            for r in self.platform_config.routers
                        ],
                        "observability_tier": self.platform_config.observability_config.tier,
                        "security_enabled": self.platform_config.security_config.api_security_suite,
                    }
                }
            )

        @app.get("/dev/routes", tags=["Development"])
        async def list_routes():
            """List all registered routes (development only)."""
            routes = []
            for route in app.routes:
                if hasattr(route, "methods") and hasattr(route, "path"):
                    routes.append(
                        {
                            "path": route.path,
                            "methods": list(route.methods) if hasattr(route.methods, '__iter__') else [],
                            "name": getattr(route, "name", None),
                        }
                    )

            return JSONResponse({"total_routes": len(routes), "routes": routes})

        @app.get("/dev/app-state", tags=["Development"])
        async def app_state():
            """Show current app state (development only)."""
            state_info = {}
            
            # Safely extract app state information
            for attr_name in dir(app.state):
                if not attr_name.startswith('_'):
                    try:
                        value = getattr(app.state, attr_name)
                        # Only include simple types for JSON serialization
                        if isinstance(value, (str, int, float, bool, list, dict)):
                            state_info[attr_name] = value
                        else:
                            state_info[attr_name] = str(type(value))
                    except Exception:
                        state_info[attr_name] = "unavailable"

            return JSONResponse({
                "app_state": state_info,
                "state_keys": list(state_info.keys())
            })

        self.added_endpoints.extend(
            ["GET /dev/config", "GET /dev/routes", "GET /dev/app-state"]
        )


# Convenience functions
def add_standard_endpoints(app: FastAPI, config: PlatformConfig) -> List[str]:
    """Add standard endpoints to an app."""
    endpoints = StandardEndpoints(config)
    return endpoints.add_to_app(app)


def create_endpoints_manager(config: PlatformConfig) -> StandardEndpoints:
    """Create a standard endpoints manager."""
    return StandardEndpoints(config)