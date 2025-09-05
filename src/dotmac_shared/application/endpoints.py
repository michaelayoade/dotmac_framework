"""
Standard endpoints for all DotMac applications.
"""

import logging

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .config import DeploymentMode, PlatformConfig

logger = logging.getLogger(__name__)


class StandardEndpoints:
    """Standard endpoints that all DotMac applications should have."""

    def __init__(self, platform_config: PlatformConfig):
        self.platform_config = platform_config
        self.added_endpoints: list[str] = []

    def add_to_app(self, app: FastAPI) -> list[str]:
        """Add standard endpoints to FastAPI application."""
        logger.info(
            f"Adding standard endpoints for {self.platform_config.platform_name}"
        )

        # Add core endpoints
        self._add_root_endpoint(app)
        self._add_favicon_endpoint(app)

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
            if hasattr(app.state, "health_checker"):
                try:
                    health_status = await app.state.health_checker.get_health_summary()
                    info["health"] = health_status["status"]
                except Exception:
                    info["health"] = "unknown"

            # Add observability tier if available
            if hasattr(app.state, "observability_tier"):
                info["observability_tier"] = app.state.observability_tier

            return JSONResponse(content=info)

        self.added_endpoints.append("GET /")

    def _add_favicon_endpoint(self, app: FastAPI):
        """Add favicon endpoint."""

        @app.get("/favicon.ico", include_in_schema=False)
        async def favicon():
            """Favicon endpoint - returns 204 No Content."""
            return Response(status_code=204)

        self.added_endpoints.append("GET /favicon.ico")

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

        @app.get("/tenant/ssl-status", tags=["Tenant"])
        async def ssl_status():
            """SSL certificate status for tenant."""
            try:
                from dotmac_isp.core.ssl_manager import get_ssl_manager

                ssl_manager = get_ssl_manager()
                status = await ssl_manager.get_status()
                return JSONResponse(status)
            except ImportError:
                return JSONResponse({"status": "ssl_manager_not_available"})
            except Exception as e:
                return JSONResponse({"status": "error", "message": str(e)})

        @app.get("/tenant/celery-status", tags=["Tenant"])
        async def celery_status():
            """Celery task queue status for tenant."""
            try:
                from dotmac_isp.core.celery_app import celery_app

                # Test Celery connection
                stats = celery_app.control.inspect().stats()
                active_tasks = celery_app.control.inspect().active()

                return JSONResponse(
                    {
                        "status": "operational" if stats else "disconnected",
                        "workers": len(stats) if stats else 0,
                        "active_tasks": (
                            sum(len(tasks) for tasks in active_tasks.values())
                            if active_tasks
                            else 0
                        ),
                    }
                )
            except ImportError:
                return JSONResponse({"status": "celery_not_available"})
            except Exception as e:
                return JSONResponse({"status": "error", "message": str(e)})

        self.added_endpoints.extend(
            ["GET /tenant/info", "GET /tenant/ssl-status", "GET /tenant/celery-status"]
        )

    def _add_management_endpoints(self, app: FastAPI):
        """Add management platform specific endpoints."""

        @app.get("/management/stats", tags=["Management"])
        async def management_stats():
            """Management platform statistics."""
            stats = {
                "platform": "management",
                "active_tenants": 0,
                "total_containers": 0,
                "system_status": "operational",
            }

            # Try to get real stats if available
            try:
                if hasattr(app.state, "websocket_manager"):
                    stats[
                        "websocket_connections"
                    ] = app.state.websocket_manager.connection_count
            except Exception:
                pass

            return JSONResponse(stats)

        @app.get("/management/tenants", tags=["Management"])
        async def list_tenants():
            """List managed tenants."""
            # This would integrate with tenant management service
            return JSONResponse(
                {
                    "tenants": [],
                    "total": 0,
                    "message": "Tenant management integration pending",
                }
            )

        @app.get("/management/websocket-status", tags=["Management"])
        async def websocket_status():
            """WebSocket manager status."""
            try:
                if hasattr(app.state, "websocket_manager"):
                    status = await app.state.websocket_manager.get_status()
                    return JSONResponse(status)
                else:
                    return JSONResponse({"status": "websocket_manager_not_initialized"})
            except Exception as e:
                return JSONResponse({"status": "error", "message": str(e)})

        self.added_endpoints.extend(
            [
                "GET /management/stats",
                "GET /management/tenants",
                "GET /management/websocket-status",
            ]
        )

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
                            "methods": list(route.methods),
                            "name": getattr(route, "name", None),
                        }
                    )

            return JSONResponse({"total_routes": len(routes), "routes": routes})

        @app.get("/dev/startup-report", tags=["Development"])
        async def startup_report(request: Request):
            """Development startup report."""
            report = {
                "platform": self.platform_config.platform_name,
                "startup_complete": True,
                "registration_stats": getattr(app.state, "registration_stats", {}),
                "observability_status": "unknown",
                "health_checks": "unknown",
            }

            # Add observability status
            if hasattr(app.state, "observability_instance"):
                try:
                    obs_status = (
                        await app.state.observability_instance.get_system_status()
                    )
                    report["observability_status"] = obs_status
                except Exception:
                    pass

            # Add health check status
            if hasattr(app.state, "health_checker"):
                try:
                    health_summary = await app.state.health_checker.get_health_summary()
                    report["health_checks"] = health_summary
                except Exception:
                    pass

            return JSONResponse(report)

        self.added_endpoints.extend(
            ["GET /dev/config", "GET /dev/routes", "GET /dev/startup-report"]
        )
