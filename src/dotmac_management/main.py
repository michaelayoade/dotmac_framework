"""
FastAPI application factory for the DotMac Management Platform using shared factory.

The Management Platform is the core SaaS service that provides:
- Multi-tenant ISP Framework deployment and management
- Partner and reseller portal management
- Infrastructure monitoring and billing
- Automated tenant provisioning and scaling
- Real-time deployment status and analytics
"""

import logging
from typing import Any, Dict

from dotmac_shared.application import create_management_platform_app
from dotmac_shared.application.config import ObservabilityConfig

logger = logging.getLogger(__name__)


async def create_app() -> "FastAPI":
    """
    Create Management Platform application using shared factory.

    This creates a management platform instance optimized for:
    - Multi-tenant orchestration
    - Kubernetes integration
    - Enhanced observability
    - Tenant container provisioning
    - Real-time monitoring
    """
    logger.info("Creating Management Platform application using shared factory...")

    app = await create_management_platform_app()

    logger.info(
        "✅ Management Platform application created successfully using shared factory"
    )

    return app


# For compatibility with synchronous imports, we need to handle async creation
import asyncio


def _create_app_sync():
    """Synchronous wrapper for app creation."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(create_app())


# Create the application instance using shared factory
app = _create_app_sync()


# Add Management Platform specific endpoints that aren't covered by StandardEndpoints
@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus-style metrics endpoint with Management Platform specific metrics."""
    import os

    from fastapi.responses import PlainTextResponse

    # Get configuration values
    app_version = getattr(app.state, "version", os.getenv("APP_VERSION", "1.0.0"))
    environment = os.getenv("ENVIRONMENT", "development")

    # Get WebSocket connection stats if available
    ws_stats = {}
    if hasattr(app.state, "websocket_manager"):
        ws_stats = app.state.websocket_manager.get_connection_stats()

    # Get request metrics from app state if available
    request_stats = getattr(
        app.state,
        "request_metrics",
        {
            "total_requests": 0,
            "bucket_01": 0,
            "bucket_05": 0,
            "bucket_10": 0,
            "total_duration": 0.0,
        },
    )

    # Management Platform specific metrics using configuration
    metrics_text = f"""# HELP management_platform_info Management Platform information
# TYPE management_platform_info gauge
management_platform_info{{version="{app_version}",environment="{environment}"}} 1

# HELP management_platform_websocket_connections WebSocket connections by type
# TYPE management_platform_websocket_connections gauge
management_platform_websocket_connections{{type="admin"}} {ws_stats.get('admin_connections', 0)}
management_platform_websocket_connections{{type="tenant"}} {ws_stats.get('tenant_connections', 0)}
management_platform_websocket_connections{{type="partner"}} {ws_stats.get('partner_connections', 0)}

# HELP management_platform_active_tenants Number of active tenant connections
# TYPE management_platform_active_tenants gauge
management_platform_active_tenants {ws_stats.get('active_tenants', 0)}

# HELP management_platform_active_partners Number of active partner connections
# TYPE management_platform_active_partners gauge
management_platform_active_partners {ws_stats.get('active_partners', 0)}

# HELP management_platform_requests_total Total number of requests
# TYPE management_platform_requests_total counter
management_platform_requests_total {request_stats['total_requests']}

# HELP management_platform_request_duration_seconds Request duration in seconds
# TYPE management_platform_request_duration_seconds histogram
management_platform_request_duration_seconds_bucket{{le="0.1"}} {request_stats['bucket_01']}
management_platform_request_duration_seconds_bucket{{le="0.5"}} {request_stats['bucket_05']}
management_platform_request_duration_seconds_bucket{{le="1.0"}} {request_stats['bucket_10']}
management_platform_request_duration_seconds_bucket{{le="+Inf"}} {request_stats['total_requests']}
management_platform_request_duration_seconds_sum {request_stats['total_duration']}
management_platform_request_duration_seconds_count {request_stats['total_requests']}
"""

    return PlainTextResponse(
        content=metrics_text, media_type="text/plain; charset=utf-8"
    )


if __name__ == "__main__":
    import uvicorn

    # Get settings for runtime configuration using config management
    try:
        from config import settings

        host = settings.host
        port = settings.port
        reload = getattr(settings, "reload", False) and getattr(
            settings, "is_development", False
        )
        log_level = getattr(settings, "log_level", "INFO").lower()
    except ImportError:
        # Use environment variables as fallback
        import os

        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8001"))
        reload = (
            os.getenv("RELOAD", "false").lower() == "true"
            and os.getenv("ENVIRONMENT", "production") == "development"
        )
        log_level = os.getenv("LOG_LEVEL", "info").lower()

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )
