"""
FastAPI application factory for the DotMac Management Platform with complete observability integration.

The Management Platform is the core SaaS service that provides:
- Multi-tenant ISP Framework deployment and management
- Partner and reseller portal management
- Infrastructure monitoring and billing
- Automated tenant provisioning and scaling
- Real-time deployment status and analytics

Features:
- Tenant identity resolution from host headers
- Edge JWT validation for sensitive routes
- Service-to-service authentication via signed tokens
- OpenTelemetry instrumentation with tenant-scoped metrics
- Unified metrics schema and dashboard generation
"""

import logging
import os
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import shared systems
from dotmac_shared.application import create_management_platform_app
from dotmac_shared.application.config import ObservabilityConfig

# Import new observability and auth systems
from dotmac_shared.tenant.identity import TenantIdentityResolver
from dotmac_shared.tenant.middleware import TenantMiddleware
from dotmac_shared.auth.edge_validation import EdgeJWTValidator, EdgeAuthMiddleware
from dotmac_shared.auth.service_tokens import configure_service_auth, ServiceAuthMiddleware
from dotmac_shared.observability import (
    initialize_otel, 
    create_default_config, 
    initialize_metrics_registry,
    initialize_tenant_metrics,
    get_metrics_registry
)

logger = logging.getLogger(__name__)


async def create_app() -> FastAPI:
    """
    Create Management Platform application with complete observability integration.

    This creates a management platform instance with:
    - Tenant identity resolution from host headers
    - Edge JWT validation for sensitive routes  
    - Service-to-service authentication
    - OpenTelemetry instrumentation
    - Unified metrics and tenant-scoped dashboards
    - Multi-tenant orchestration
    - Kubernetes integration
    """
    logger.info("Creating Management Platform application with full observability integration...")

    # Production baseline guard (opt-in strict mode)
    if os.getenv("ENVIRONMENT", "development") == "production" and os.getenv("STRICT_PROD_BASELINE", "false").lower() == "true":
        allow_insecure = os.getenv("ALLOW_INSECURE_PROD", "false").lower() == "true"
        missing = []
        if not os.getenv("OPENBAO_URL"):
            missing.append("OPENBAO_URL")
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url or db_url.startswith("sqlite"):
            missing.append("DATABASE_URL (non-sqlite)")
        if not os.getenv("REDIS_URL"):
            missing.append("REDIS_URL")
        if not os.getenv("APPLY_RLS_AFTER_MIGRATION"):
            missing.append("APPLY_RLS_AFTER_MIGRATION")
        if missing:
            msg = f"Production baseline unmet: {', '.join(missing)}"
            if allow_insecure:
                logger.warning("%s (ALLOW_INSECURE_PROD=true)", msg)
            else:
                logger.error(msg)
                raise SystemExit(msg)
    
    # Get configuration from environment
    environment = os.getenv("ENVIRONMENT", "production")
    service_name = "dotmac-management"
    service_version = os.getenv("APP_VERSION", "1.0.0")
    
    # 1. Initialize OpenTelemetry first
    logger.info("Initializing OpenTelemetry...")
    otel_config = create_default_config(
        service_name=service_name,
        environment=environment,
        service_version=service_version,
        # Environment-specific exporter configuration
        tracing_exporters=["otlp", "prometheus"] if environment == "production" else ["console"],
        metrics_exporters=["otlp", "prometheus"] if environment == "production" else ["console"]
    )
    otel_bootstrap = initialize_otel(otel_config)
    
    # 2. Initialize unified metrics registry
    logger.info("Initializing metrics registry...")
    metrics_registry = initialize_metrics_registry(service_name, enable_prometheus=True)
    
    # Set OTEL meter for metrics integration
    if otel_bootstrap and otel_bootstrap.get_meter():
        metrics_registry.set_otel_meter(otel_bootstrap.get_meter())
    
    # 3. Initialize tenant metrics system
    logger.info("Initializing tenant metrics...")
    tenant_metrics = initialize_tenant_metrics(
        service_name=service_name,
        metrics_registry=metrics_registry,
        enable_dashboards=True,
        enable_slo_monitoring=True
    )
    
    # 4. Configure service-to-service authentication
    logger.info("Configuring service authentication...")
    service_signing_secret = os.getenv("SERVICE_SIGNING_SECRET", "dev-secret-key-change-in-production")
    service_token_manager = configure_service_auth(service_signing_secret)
    
    # Register this service and allowed communication patterns
    service_token_manager.register_service(
        service_name=service_name,
        service_info={
            "version": service_version,
            "environment": environment,
            "capabilities": ["tenant_management", "partner_management", "billing"]
        },
        allowed_targets=[
            "dotmac-shared", "dotmac-logging", "dotmac-metrics",
            "isp-customer", "isp-billing", "isp-network"
        ]
    )
    
    # 5. Initialize tenant identity resolver
    logger.info("Initializing tenant identity resolver...")
    tenant_resolver = TenantIdentityResolver()
    
    # Configure subdomain patterns for management platform
    tenant_resolver.configure_patterns({
        "management": r"^admin\.(?P<tenant_id>\w+)\..*",
        "partner": r"^partner\.(?P<tenant_id>\w+)\..*", 
        "reseller": r"^(?P<tenant_id>\w+)\.reseller\..*"
    })
    
    # 6. Initialize JWT validator for edge authentication
    logger.info("Initializing edge JWT validator...")
    jwt_secret = os.getenv("JWT_SECRET", "dev-jwt-secret-change-in-production")
    edge_validator = EdgeJWTValidator(
        jwt_secret=jwt_secret,
        tenant_resolver=tenant_resolver
    )
    
    # Configure route sensitivity patterns for management platform
    edge_validator.configure_sensitivity_patterns({
        # Admin routes require highest security
        (r"/admin/.*", ".*"): "admin",
        (r"/api/admin/.*", ".*"): "admin",
        
        # Tenant management routes
        (r"/api/tenants/.*", "GET"): "authenticated", 
        (r"/api/tenants/.*", "POST|PUT|DELETE"): "sensitive",
        
        # Partner routes
        (r"/api/partners/.*", "GET"): "authenticated",
        (r"/api/partners/.*", "POST|PUT|DELETE"): "sensitive",
        
        # Billing routes are highly sensitive
        (r"/api/billing/.*", ".*"): "sensitive",
        
        # Service-to-service internal routes
        (r"/internal/.*", ".*"): "internal",
        
        # Public routes
        (r"/health", ".*"): "public",
        (r"/metrics", ".*"): "public",
        (r"/docs", ".*"): "public"
    })

    # 7. Create the base FastAPI application
    logger.info("Creating base FastAPI application...")
    app = await create_management_platform_app()
    
    # 8. Add middleware in correct order (LIFO - Last In, First Out)
    # Service auth middleware (innermost - applied last)
    app.add_middleware(
        ServiceAuthMiddleware,
        token_manager=service_token_manager,
        service_name=service_name,
        required_operations=[]  # Configured per route if needed
    )
    
    # Edge JWT validation middleware
    app.add_middleware(
        EdgeAuthMiddleware,
        validator=edge_validator,
        service_name=service_name
    )
    
    # Tenant middleware (outermost - applied first)  
    app.add_middleware(
        TenantMiddleware,
        resolver=tenant_resolver,
        service_name=service_name
    )
    
    # Store components in app state for access in routes
    app.state.otel_bootstrap = otel_bootstrap
    app.state.metrics_registry = metrics_registry
    app.state.tenant_metrics = tenant_metrics
    app.state.service_token_manager = service_token_manager
    app.state.tenant_resolver = tenant_resolver
    app.state.edge_validator = edge_validator

    logger.info("✅ Management Platform application created with full observability integration")
    
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


# Add Management Platform specific endpoints with unified metrics
@app.get("/metrics")
async def unified_metrics_endpoint():
    """
    Unified Prometheus-style metrics endpoint using the shared metrics registry.
    
    This endpoint exposes:
    - Standard application metrics (requests, duration, errors)
    - Management Platform specific metrics (tenants, partners, deployments)  
    - Tenant-scoped business metrics
    - System and infrastructure metrics
    """
    from fastapi.responses import PlainTextResponse
    from prometheus_client import generate_latest
    
    try:
        # Get the unified metrics registry from app state
        metrics_registry = getattr(app.state, "metrics_registry", None)
        if not metrics_registry:
            # Fallback to basic metrics if registry not available
            return PlainTextResponse("# Metrics registry not initialized\n", media_type="text/plain")
        
        # Get Prometheus registry and generate metrics
        prometheus_registry = metrics_registry.get_prometheus_registry()
        if prometheus_registry:
            metrics_output = generate_latest(prometheus_registry).decode('utf-8')
        else:
            metrics_output = "# Prometheus registry not available\n"
        
        # Add Management Platform specific metrics
        app_version = os.getenv("APP_VERSION", "1.0.0")
        environment = os.getenv("ENVIRONMENT", "production")
        
        # Get WebSocket stats if available
        ws_stats = {}
        if hasattr(app.state, "websocket_manager"):
            ws_stats = app.state.websocket_manager.get_connection_stats()
        
        # Management Platform business metrics
        platform_metrics = f"""
# HELP dotmac_management_info Management Platform service information
# TYPE dotmac_management_info gauge
dotmac_management_info{{version="{app_version}",environment="{environment}"}} 1

# HELP dotmac_management_websocket_connections Active WebSocket connections by type
# TYPE dotmac_management_websocket_connections gauge
dotmac_management_websocket_connections{{type="admin"}} {ws_stats.get('admin_connections', 0)}
dotmac_management_websocket_connections{{type="tenant"}} {ws_stats.get('tenant_connections', 0)}
dotmac_management_websocket_connections{{type="partner"}} {ws_stats.get('partner_connections', 0)}

# HELP dotmac_management_active_tenants Currently active tenant instances
# TYPE dotmac_management_active_tenants gauge
dotmac_management_active_tenants {ws_stats.get('active_tenants', 0)}

# HELP dotmac_management_active_partners Currently active partner connections  
# TYPE dotmac_management_active_partners gauge
dotmac_management_active_partners {ws_stats.get('active_partners', 0)}
"""
        
        # Combine unified metrics with platform-specific metrics
        combined_metrics = metrics_output + platform_metrics
        
        return PlainTextResponse(
            content=combined_metrics, 
            media_type="text/plain; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        error_response = f"# Error generating metrics: {str(e)}\n"
        return PlainTextResponse(
            content=error_response,
            media_type="text/plain; charset=utf-8"
        )


# Example routes demonstrating tenant-aware functionality
@app.get("/api/tenants/dashboard")
async def get_tenant_dashboard(request):
    """
    Example endpoint showing how to use tenant context and metrics.
    
    This demonstrates:
    - Accessing tenant context from middleware
    - Recording tenant-scoped metrics
    - Using business metrics for dashboard data
    """
    from fastapi import Request
    from dotmac_shared.tenant.identity import get_current_tenant_context
    
    try:
        # Get tenant context set by middleware
        tenant_context = get_current_tenant_context()
        if not tenant_context:
            return {"error": "No tenant context available", "tenant_id": None}
        
        # Record a business metric for dashboard access
        if hasattr(app.state, "tenant_metrics"):
            await app.state.tenant_metrics.record_business_metric(
                metric_name="dashboard_views",
                value=1,
                tenant_context=tenant_context,
                metadata={"endpoint": "/api/tenants/dashboard"}
            )
        
        # Generate tenant-specific dashboard configuration
        dashboard_config = None
        if hasattr(app.state, "tenant_metrics"):
            dashboard_config = app.state.tenant_metrics.generate_tenant_dashboard_config(tenant_context)
        
        return {
            "tenant_id": tenant_context.tenant_id,
            "tenant_type": "management" if tenant_context.is_management else "customer", 
            "subdomain": tenant_context.subdomain,
            "dashboard_config": dashboard_config,
            "message": "Tenant dashboard data retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error in tenant dashboard endpoint: {e}")
        return {"error": str(e)}


@app.get("/api/tenants/{tenant_id}/metrics")
async def get_tenant_metrics(tenant_id: str, request: Request):
    """
    Example endpoint for retrieving tenant-specific metrics and SLO status.
    
    This demonstrates:
    - Tenant-specific metric queries
    - SLO evaluation
    - Business metric aggregation
    """
    from dotmac_shared.tenant.identity import get_current_tenant_context
    
    try:
        # Validate tenant access
        tenant_context = get_current_tenant_context()
        if not tenant_context or tenant_context.tenant_id != tenant_id:
            return {"error": "Access denied to tenant metrics", "tenant_id": tenant_id}
        
        metrics_data = {}
        slo_status = {}
        
        # Get tenant metrics collector
        if hasattr(app.state, "tenant_metrics"):
            tenant_metrics = app.state.tenant_metrics
            
            # Evaluate SLOs for this tenant
            slo_status = tenant_metrics.evaluate_slos(tenant_context)
            
            # Get business metric summary
            metrics_data = {
                "tenant_id": tenant_id,
                "collection_time": "2024-01-01T00:00:00Z",  # Would be current time
                "business_metrics": {
                    "active_users": 150,
                    "total_requests": 10000,
                    "error_rate": 0.01,
                    "avg_response_time": 0.25
                }
            }
        
        return {
            "tenant_id": tenant_id,
            "metrics": metrics_data,
            "slo_status": slo_status,
            "dashboard_url": f"/dashboards/tenant/{tenant_id}"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving tenant metrics: {e}")
        return {"error": str(e)}


@app.post("/internal/service-token")
async def issue_service_token(request: Request):
    """
    Example internal endpoint for issuing service-to-service tokens.
    
    This demonstrates:
    - Service token generation
    - Internal route protection
    - Service authentication workflow
    """
    try:
        # This would typically validate the requesting service
        # For demo purposes, we'll create a token for ISP service communication
        
        if not hasattr(app.state, "service_token_manager"):
            return {"error": "Service token manager not available"}
        
        service_identity = app.state.service_token_manager.create_service_identity(
            service_name="dotmac-management",
            version="1.0.0",
            environment=os.getenv("ENVIRONMENT", "production")
        )
        
        # Issue token for communication with ISP services
        token = await app.state.service_token_manager.issue_service_token(
            service_identity=service_identity,
            target_service="isp-customer",
            allowed_operations=["read_customer", "update_billing"],
            tenant_context="example-tenant-123"
        )
        
        return {
            "token": token,
            "service": "dotmac-management",
            "target": "isp-customer",
            "expires_in": 3600,
            "message": "Service token issued successfully"
        }
        
    except Exception as e:
        logger.error(f"Error issuing service token: {e}")
        return {"error": str(e)}


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
