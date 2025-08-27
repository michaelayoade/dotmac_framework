"""
FastAPI application entry point.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Add shared components to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

from startup.error_handling import (
    create_startup_manager,
    StartupPhase,
    StartupErrorSeverity,
    managed_startup,
    initialize_database_with_retry
)
from health.comprehensive_checks import setup_health_checker
from health.endpoints import add_health_endpoints, add_startup_status_endpoint
from security.api_security_integration import setup_complete_api_security

from api.portals import portals_router
from api.v1 import api_router
from config import settings
from core.exceptions import add_exception_handlers
from core.logging import configure_logging, get_logger
from core.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
    TenantIsolationMiddleware,
)
from core.observability import init_observability, get_observability
from core.security_validator import startup_security_check
from core.csrf_middleware import add_csrf_protection
from core.tenant_security import init_management_tenant_security, add_management_tenant_security_middleware
from database import close_database, init_database

# Configure comprehensive logging
configure_logging(
    log_level=settings.log_level,
    log_format=settings.log_format,
    enable_console=True,
    enable_file=True,
    log_file="logs/dotmac_management.log",
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with standardized error handling."""
    
    async with managed_startup(
        service_name="DotMac Management Platform",
        fail_on_critical=True,
        fail_on_high_severity=False
    ) as startup_manager:
        
        logger.info("Starting DotMac Management Platform...")
        
        # Security validation first
        try:
            security_result = startup_security_check()
            logger.info("✅ Security validation completed")
        except Exception as e:
            logger.error(f"❌ Security validation failed: {e}")
            raise
        
        # Initialize database with retry
        db_result = await initialize_database_with_retry(
            init_database, startup_manager, max_retries=5
        )
        
        if db_result.success:
            logger.info("✅ Database initialized")
        
        # Initialize observability (SignOz integration) with retry
        observability_result = await startup_manager.execute_with_retry(
            operation=init_observability,
            phase=StartupPhase.OBSERVABILITY,
            component="SignOz Observability",
            severity=StartupErrorSeverity.MEDIUM,
            max_retries=2
        )
        
        if observability_result.success:
            logger.info("✅ SignOz observability initialized")
            app.state.observability = observability_result.metadata.get("result")
        
        # Initialize cache manager with retry
        async def init_cache():
            from core.cache import get_cache_manager
            return await get_cache_manager()
            
        cache_result = await startup_manager.execute_with_retry(
            operation=init_cache,
            phase=StartupPhase.CACHE,
            component="Cache Manager",
            severity=StartupErrorSeverity.HIGH,
            max_retries=3
        )
        
        if cache_result.success:
            logger.info("✅ Cache manager initialized")
            app.state.cache_manager = cache_result.metadata.get("result")
        
        # Initialize plugins with error handling
        async def init_plugins():
            from core.plugins.registry import plugin_registry
            from plugins.deployment import AWSDeploymentPlugin, SSHDeploymentPlugin
            from plugins.notifications import EmailPlugin, SlackPlugin, WebhookPlugin
            from plugins.monitoring import PrometheusPlugin
            
            # Create plugin instances
            plugins_to_register = [
                AWSDeploymentPlugin(),
                SSHDeploymentPlugin(),
                EmailPlugin(),
                SlackPlugin(),
                WebhookPlugin(),
                PrometheusPlugin()
            ]
            
            registered_count = 0
            for plugin in plugins_to_register:
                try:
                    if await plugin_registry.register_plugin(plugin):
                        registered_count += 1
                        logger.info(f"Registered plugin: {plugin.meta.name}")
                except Exception as e:
                    logger.warning(f"Plugin registration error for {plugin.meta.name}: {e}")
                    
            return {"registered_count": registered_count, "total_plugins": len(plugins_to_register)}
        
        plugin_result = await startup_manager.execute_with_retry(
            operation=init_plugins,
            phase=StartupPhase.INITIALIZATION,
            component="Plugin System",
            severity=StartupErrorSeverity.MEDIUM,
            max_retries=1
        )
        
        if plugin_result.success:
            metadata = plugin_result.metadata.get("result", {})
            logger.info(f"✅ Plugin system initialized: {metadata.get('registered_count', 0)} plugins registered")
        
        # Initialize Management Platform tenant security
        async def init_mgmt_tenant_sec():
            from database import engine, get_session
            async with get_session() as session:
                return await init_management_tenant_security(engine, session)
        
        mgmt_tenant_security_result = await startup_manager.execute_with_retry(
            operation=init_mgmt_tenant_sec,
            phase=StartupPhase.SECURITY,
            component="Management Tenant Security",
            severity=StartupErrorSeverity.MEDIUM,
            max_retries=1
        )
        
        if mgmt_tenant_security_result.success:
            logger.info("🔒 Management Platform tenant security initialized")
        
        # Initialize comprehensive API security
        async def init_api_security():
            return await setup_complete_api_security(
                app=app,
                environment=settings.environment,
                jwt_secret_key=settings.secret_key,
                redis_url=settings.redis_url,
                api_type="admin",  # Management platform is admin API
                tenant_domains=settings.cors_origins,
                validate_implementation=True
            )
        
        api_security_result = await startup_manager.execute_with_retry(
            operation=init_api_security,
            phase=StartupPhase.SECURITY,
            component="API Security Suite",
            severity=StartupErrorSeverity.HIGH,
            max_retries=1
        )
        
        if api_security_result.success:
            security_data = api_security_result.metadata.get("result", {})
            app.state.api_security_suite = security_data.get("security_suite")
            validation_result = security_data.get("validation_result", {})
            logger.info(f"🛡️ API Security Suite initialized - Status: {validation_result.get('overall_status', 'UNKNOWN')} - Score: {validation_result.get('security_score', 0):.1f}%")
        else:
            logger.warning("⚠️ API Security Suite initialization failed - using fallback security")
        
        # Set up comprehensive health checks
        health_checker = setup_health_checker(
            service_name="DotMac Management Platform",
            cache_client=getattr(app.state, 'cache_manager', None),
            additional_filesystem_paths=["logs", "uploads"]
        )
        app.state.health_checker = health_checker
        startup_manager.add_metadata("health_checks_registered", len(health_checker.health_checks))
        
        # Store startup manager for shutdown and health endpoints
        app.state.startup_manager = startup_manager
        
        logger.info("🚀 DotMac Management Platform startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DotMac Management Platform...")
    
    # Shutdown observability
    try:
        observability = get_observability()
        observability.shutdown()
        logger.info("Observability shutdown")
    except Exception as e:
        logger.warning("Error shutting down observability", error=str(e))
    
    # Close cache connections
    try:
        from core.cache import get_cache_manager
        cache_manager = await get_cache_manager()
        await cache_manager.close()
        logger.info("Cache connections closed")
    except Exception as e:
        logger.warning("Error closing cache connections", error=str(e))
    
    # Close database connections
    await close_database()
    logger.info("Database connections closed")
    
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-tenant SaaS platform for managing DotMac ISP Framework instances",
    docs_url=settings.docs_url if not settings.is_production else None,
    redoc_url=settings.redoc_url if not settings.is_production else None,
    openapi_url=settings.openapi_url if not settings.is_production else None,
    lifespan=lifespan,
)

# Essential middleware (API Security Suite handles most security middleware)
trusted_hosts = (
    ["localhost", "127.0.0.1", "149.102.135.97", "testserver", "*.dotmac.app"]
    if not settings.is_production
    else ["*.dotmac.app"]
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(TenantIsolationMiddleware)  # Keep tenant isolation

# Add CSRF protection
add_csrf_protection(app)

# Add management tenant security middleware
add_management_tenant_security_middleware(app)

# Add exception handlers
add_exception_handlers(app)

# Add comprehensive health check endpoints
add_health_endpoints(app)
add_startup_status_endpoint(app)

# Include routers
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(portals_router, prefix="/portals")

# Include dashboard router (web UI)
from api.dashboard import router as dashboard_router
app.include_router(dashboard_router)

# Instrument FastAPI with observability
try:
    observability = get_observability()
    observability.instrument_fastapi(app)
    logger.info("FastAPI instrumented with SignOz observability")
except Exception as e:
    logger.warning("Failed to instrument FastAPI", error=str(e))


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "message": "DotMac Management Platform",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs_url": app.docs_url,
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus-style metrics endpoint."""
    from fastapi.responses import PlainTextResponse
    
    # Basic Prometheus-style metrics
    metrics_text = """# HELP app_info Application information
# TYPE app_info gauge
app_info{version="1.0.0",environment="development"} 1

# HELP app_requests_total Total number of requests
# TYPE app_requests_total counter
app_requests_total 100

# HELP app_request_duration_seconds Request duration in seconds
# TYPE app_request_duration_seconds histogram
app_request_duration_seconds_bucket{le="0.1"} 50
app_request_duration_seconds_bucket{le="0.5"} 80
app_request_duration_seconds_bucket{le="1.0"} 95
app_request_duration_seconds_bucket{le="+Inf"} 100
app_request_duration_seconds_sum 25.5
app_request_duration_seconds_count 100
"""
    
    return PlainTextResponse(content=metrics_text, media_type="text/plain; charset=utf-8")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.is_development,
        log_level=settings.log_level.lower(),
    )