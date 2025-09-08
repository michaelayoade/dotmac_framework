"""API router registration for DotMac ISP Framework."""

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def register_routers(app: FastAPI) -> None:
    """Register all API routers with the FastAPI application.

    This function dynamically imports and registers available routers
    to avoid import errors for modules that don't exist yet.
    """
    logger.info("Registering API routers...")

    # Core health endpoint is already in app.py

    # Try to register module routers (gracefully handle missing modules)
    _register_module_routers(app)

    # Try to register portal routers (gracefully handle missing modules)
    _register_portal_routers(app)

    # Register security management endpoints
    _register_security_routers(app)

    # Register WebSocket and file handling endpoints
    _register_integration_routers(app)

    # Register performance monitoring endpoints
    _register_performance_routers(app)

    logger.info("API router registration complete")


def _register_module_routers(app: FastAPI) -> None:
    """Register module routers if they exist."""
    module_routers = [
        ("dotmac_isp.modules.identity.router", "router", "/api/v1/identity"),
        ("dotmac_isp.modules.billing.router", "billing_router", "/api/v1/billing"),
        ("dotmac_isp.modules.services.router", "services_router", "/api/v1/services"),
        # Support router replaced with dotmac_shared.ticketing package
        (
            "dotmac_isp.modules.customers.router",
            "customers_router",
            "/api/v1/customers",
        ),
        (
            "dotmac_isp.modules.network_integration.router",
            "router",
            "/api/v1/networking",
        ),
        (
            "dotmac_isp.modules.network_monitoring.router",
            "router",
            "/api/v1/network-monitoring",
        ),
        ("dotmac_isp.modules.gis.router", "router", "/api/v1/gis"),
        (
            "dotmac_isp.modules.analytics.router",
            "analytics_router",
            "/api/v1/analytics",
        ),
        # Sales module moved to management platform for multi-tenant orchestration
        # Inventory router moved to dotmac_shared.inventory_management package
        # Compliance module moved to management platform for multi-tenant orchestration
        # Field ops module moved to management platform for multi-tenant orchestration
        # Licensing module moved to management platform for multi-tenant orchestration
        # Notifications handled by shared dotmac_shared.notifications service
        (
            "dotmac_isp.modules.portal_management.router",
            "router",
            "/api/v1/portal-management",
        ),
        (
            "dotmac_isp.modules.captive_portal.router",
            "router",
            "/api/v1/captive-portal",
        ),
        (
            "dotmac_isp.modules.network_visualization.router",
            "router",
            "/api/v1/network-visualization",
        ),
        # Resellers module - using shared reseller service for DRY compliance
        (
            "dotmac_isp.modules.resellers.router",
            "router",
            "/api/v1/resellers",
        ),
    ]

    for module_path, router_name, prefix in module_routers:
        try:
            # Security: Validate module path is from trusted namespace
            if not module_path.startswith("dotmac_isp."):
                logger.warning(f"Security: Blocked router import from untrusted module: {module_path}")
                continue

            # Use importlib for safer importing
            import importlib

            module = importlib.import_module(module_path)
            router = getattr(module, router_name, None)

            if router:
                app.include_router(router, prefix=prefix, tags=[prefix.split("/")[-1]])
                logger.info(f"Registered router: {module_path} at {prefix}")
            else:
                logger.warning(f"Router {router_name} not found in {module_path}")

        except ImportError:
            logger.debug(f"Module {module_path} not available yet")
        except Exception as e:
            logger.error(f"Error registering router {module_path}: {e}")


def _register_portal_routers(app: FastAPI) -> None:
    """Register portal routers if they exist."""
    # First register the comprehensive portal integration APIs
    try:
        from dotmac_isp.api.portal_integrations import (
            admin_router,
            customer_router,
            reseller_router,
            technician_router,
        )

        app.include_router(customer_router, tags=["customer-portal"])
        app.include_router(admin_router, tags=["admin-portal"])
        app.include_router(technician_router, tags=["technician-portal"])
        app.include_router(reseller_router, tags=["reseller-portal"])
        logger.info("Registered portal integration APIs")

    except ImportError as e:
        logger.warning(f"Portal integration APIs not available: {e}")
    except Exception as e:
        logger.error(f"Error registering portal integration APIs: {e}")

    # Legacy portal routers (if they exist)
    portal_routers = [
        ("dotmac_isp.portals.admin.router", "admin_router", "/api/v1/admin"),
        ("dotmac_isp.portals.customer.router", "customer_router", "/api/v1/customer"),
        ("dotmac_isp.portals.reseller.router", "reseller_router", "/api/v1/reseller"),
        (
            "dotmac_isp.portals.technician.router",
            "technician_router",
            "/api/v1/technician",
        ),
    ]

    for module_path, router_name, prefix in portal_routers:
        try:
            # Security: Validate module path is from trusted namespace
            if not module_path.startswith("dotmac_isp."):
                logger.warning(f"Security: Blocked portal router import from untrusted module: {module_path}")
                continue

            # Use importlib for safer importing
            import importlib

            module = importlib.import_module(module_path)
            router = getattr(module, router_name, None)

            if router:
                app.include_router(router, prefix=prefix, tags=[prefix.split("/")[-1]])
                logger.info(f"Registered portal router: {module_path} at {prefix}")
            else:
                logger.warning(f"Portal router {router_name} not found in {module_path}")
        except ImportError:
            logger.debug(f"Portal module {module_path} not available yet")
        except Exception as e:
            logger.error(f"Error registering portal router {module_path}: {e}")


def _register_security_routers(app: FastAPI) -> None:
    """Register security management routers."""
    try:
        from dotmac_isp.api.security_endpoints import router as security_router

        app.include_router(security_router, prefix="/api/v1", tags=["security"])
        logger.info("Registered security management endpoints at /api/v1/security")
    except ImportError as e:
        logger.warning(f"Security endpoints not available: {e}")
    except Exception as e:
        logger.error(f"Error registering security endpoints: {e}")


def _register_integration_routers(app: FastAPI) -> None:
    """Register WebSocket and file handling routers."""
    # Register WebSocket endpoints
    try:
        from dotmac_isp.api.websocket_router import router as websocket_router

        app.include_router(websocket_router, prefix="/api", tags=["websocket"])
        logger.info("Registered WebSocket endpoints at /api/ws")
    except ImportError as e:
        logger.warning(f"WebSocket endpoints not available: {e}")
    except Exception as e:
        logger.error(f"Error registering WebSocket endpoints: {e}")

    # Register file handling endpoints
    try:
        from dotmac_isp.api.file_router import router as file_router

        app.include_router(file_router, prefix="/api", tags=["files"])
        logger.info("Registered file handling endpoints at /api/files, /api/upload, /api/export")
    except ImportError as e:
        logger.warning(f"File handling endpoints not available: {e}")
    except Exception as e:
        logger.error(f"Error registering file handling endpoints: {e}")

    # Register plugin management endpoints
    try:
        from dotmac_isp.api.plugins_endpoints import router as plugins_router

        app.include_router(plugins_router, tags=["plugin-management"])
        logger.info("Registered plugin management endpoints at /api/admin/plugins")
    except ImportError as e:
        logger.warning(f"Plugin management endpoints not available: {e}")
    except Exception as e:
        logger.error(f"Error registering plugin management endpoints: {e}")

    # Register unified authentication endpoints
    try:
        from dotmac_isp.api.unified_auth import auth_router

        app.include_router(auth_router, tags=["unified-authentication"])
        logger.info("Registered unified authentication endpoints at /api/auth")
    except ImportError as e:
        logger.warning(f"Unified authentication endpoints not available: {e}")
    except Exception as e:
        logger.error(f"Error registering unified authentication endpoints: {e}")

    # Register tenant provisioning auth endpoints
    try:
        from dotmac_isp.api.auth_router import router as tenant_auth_router

        app.include_router(tenant_auth_router, prefix="/api/v1", tags=["tenant-auth", "provisioning"])
        logger.info("Registered tenant authentication endpoints at /api/v1/auth")
    except ImportError as e:
        logger.warning(f"Tenant auth endpoints not available: {e}")
    except Exception as e:
        logger.error(f"Error registering tenant auth endpoints: {e}")

    # Register domain management endpoints
    try:
        from dotmac_isp.api.domain_router import router as domain_router

        app.include_router(domain_router, prefix="/api/v1/domains", tags=["domain-management"])
        logger.info("Registered domain management endpoints at /api/v1/domains")
    except ImportError as e:
        logger.warning(f"Domain management endpoints not available: {e}")
    except Exception as e:
        logger.error(f"Error registering domain management endpoints: {e}")


def _register_performance_routers(app: FastAPI) -> None:
    """Register clean performance monitoring API."""
    try:
        from dotmac_isp.api.performance_api import performance_api

        app.include_router(performance_api, tags=["performance", "monitoring"])
        logger.info("Registered optimal performance API at /api/v1/performance")

    except ImportError as e:
        logger.warning(f"Performance API not available: {e}")
    except Exception as e:
        logger.error(f"Error registering performance API: {e}")
