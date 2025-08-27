"""FastAPI application factory for the DotMac ISP Framework."""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Add shared components to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from startup.error_handling import (
    create_startup_manager,
    StartupPhase,
    StartupErrorSeverity,
    managed_startup,
    initialize_database_with_retry,
    initialize_cache_with_retry,
    initialize_observability_with_retry
)
from health.comprehensive_checks import setup_health_checker
from health.endpoints import add_health_endpoints, add_startup_status_endpoint
from security.api_security_integration import setup_complete_api_security

from dotmac_isp.api.routers import register_routers
from dotmac_isp.core.audit_middleware import (
    initialize_audit_system,
    setup_audit_middleware,
)
from dotmac_isp.core.business_rules import initialize_business_rules
from dotmac_isp.core.celery_app import celery_app
from dotmac_isp.core.database import close_database, init_database
from dotmac_isp.core.exceptions import add_exception_handlers
from dotmac_isp.core.infrastructure_middleware import (
    add_infrastructure_middleware,
    create_monitoring_endpoints,
    shutdown_infrastructure,
    startup_infrastructure,
)
from dotmac_isp.core.middleware import add_middleware
from dotmac_isp.core.search_optimization import initialize_search_optimization
from dotmac_isp.core.security import initialize_rls
from dotmac_isp.core.security_middleware import setup_enhanced_security_middleware
from dotmac_isp.core.settings import get_settings
from dotmac_isp.core.ssl_manager import get_ssl_manager, initialize_ssl
from dotmac_isp.core.csrf_middleware import add_csrf_protection
from dotmac_isp.core.tenant_security import init_tenant_security, add_tenant_security_middleware
from dotmac_isp.shared.cache import get_cache_manager

# SignOz observability integration
try:
    from dotmac_isp.sdks.core.observability_signoz import init_signoz, get_signoz
    SIGNOZ_AVAILABLE = True
except ImportError as e:
    logging.warning(f"SignOz SDK not available: {e}")
    init_signoz = None
    get_signoz = None
    SIGNOZ_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with standardized error handling."""
    settings = get_settings()
    
    async with managed_startup(
        service_name="DotMac ISP Framework",
        fail_on_critical=True,
        fail_on_high_severity=False
    ) as startup_manager:
        
        # Initialize cache with retry
        async def init_cache():
            cache_manager = get_cache_manager()
            return cache_manager
            
        cache_result = await initialize_cache_with_retry(init_cache, startup_manager)
        if cache_result.success:
            logging.info("✅ Redis cache connection established")
            app.state.cache_manager = cache_result.metadata.get("result")
        else:
            startup_manager.add_warning("Cache initialization failed - running without cache")

        # Initialize database with retry
        database_result = await initialize_database_with_retry(init_database, startup_manager)
        if database_result.success:
            logging.info("✅ Database initialized successfully")
        else:
            startup_manager.add_warning("Database initialization failed - some features may not work")

        # Initialize SignOz observability with retry
        if SIGNOZ_AVAILABLE and init_signoz:
            async def init_signoz_observability():
                return init_signoz(
                    service_name="dotmac-isp-framework",
                    service_version="1.0.0",
                    environment=settings.environment,
                    signoz_endpoint=getattr(settings, 'signoz_endpoint', 'localhost:4317'),
                    signoz_access_token=getattr(settings, 'signoz_access_token', None),
                    enable_metrics=True,
                    enable_traces=True,
                    enable_logs=True,
                    enable_profiling=getattr(settings, 'signoz_profiling', False),
                    custom_attributes={
                        "service.tier": "backend",
                        "service.component": "isp_framework", 
                        "platform": "isp_framework",
                        "deployment": "monolithic",
                        "business_model": "b2b_saas",
                        "tenant.isolation": "enabled",
                        "plugin.system": "enabled"
                    }
                )
            
            observability_result = await initialize_observability_with_retry(
                init_signoz_observability, startup_manager
            )
            
            if observability_result.success:
                app.state.signoz_telemetry = observability_result.metadata.get("result")
                logging.info("✅ SignOz observability initialized with full telemetry")
            else:
                startup_manager.add_warning("SignOz observability initialization failed")

        # Initialize infrastructure with retry
        infrastructure_result = await startup_manager.execute_with_retry(
            operation=startup_infrastructure,
            phase=StartupPhase.MIDDLEWARE,
            component="Infrastructure Middleware",
            severity=StartupErrorSeverity.HIGH,
            max_retries=2
        )
        
        if infrastructure_result.success:
            logging.info("✅ Infrastructure middleware initialized")

        # Initialize security systems with individual error handling
        security_components = [
            ("Row Level Security", initialize_rls, StartupErrorSeverity.HIGH),
            ("Business Rules", initialize_business_rules, StartupErrorSeverity.MEDIUM),
            ("Search Optimization", initialize_search_optimization, StartupErrorSeverity.MEDIUM)
        ]
        
        for component_name, init_func, severity in security_components:
            result = await startup_manager.execute_with_retry(
                operation=init_func,
                phase=StartupPhase.SECURITY,
                component=component_name,
                severity=severity,
                max_retries=1
            )
            
            if result.success:
                logging.info(f"🔒 {component_name} initialized")
            else:
                startup_manager.add_warning(f"{component_name} initialization failed")

        # Initialize tenant security (RLS + middleware)
        async def init_tenant_sec():
            from dotmac_isp.core.database import engine, get_session
            async with get_session() as session:
                return await init_tenant_security(engine, session)
        
        tenant_security_result = await startup_manager.execute_with_retry(
            operation=init_tenant_sec,
            phase=StartupPhase.SECURITY,
            component="Tenant Security (RLS)",
            severity=StartupErrorSeverity.HIGH,
            max_retries=2
        )
        
        if tenant_security_result.success:
            logging.info("🔒 Tenant Security (RLS) initialized")
        else:
            startup_manager.add_warning("Tenant Security initialization failed")

        # Initialize comprehensive API security
        async def init_api_security():
            return await setup_complete_api_security(
                app=app,
                environment=settings.environment,
                jwt_secret_key=settings.secret_key,
                redis_url=settings.redis_url,
                api_type="api",  # ISP Framework is standard API
                tenant_domains=settings.cors_origins_list,
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
            logging.info(f"🛡️ API Security Suite initialized - Status: {validation_result.get('overall_status', 'UNKNOWN')} - Score: {validation_result.get('security_score', 0):.1f}%")
        else:
            logging.warning("⚠️ API Security Suite initialization failed - using fallback security")

        # Initialize SSL certificates if enabled
        if hasattr(settings, "ssl_enabled") and settings.ssl_enabled:
            ssl_result = await startup_manager.execute_with_retry(
                operation=initialize_ssl,
                phase=StartupPhase.SECURITY,
                component="SSL Certificates",
                severity=StartupErrorSeverity.MEDIUM,
                max_retries=1
            )
            
            if ssl_result.success:
                logging.info("✅ SSL certificates initialized")
            else:
                startup_manager.add_warning("SSL certificate initialization failed")

        # Initialize Celery task queue
        async def test_celery():
            result = celery_app.send_task("dotmac_isp.core.tasks.health_check")
            return result
            
        celery_result = await startup_manager.execute_with_retry(
            operation=test_celery,
            phase=StartupPhase.BACKGROUND_TASKS,
            component="Celery Task Queue",
            severity=StartupErrorSeverity.HIGH,
            max_retries=2
        )
        
        if celery_result.success:
            logging.info("✅ Celery task queue connection established")

        # Initialize WebSocket manager for real-time updates
        async def init_websocket():
            from dotmac_isp.core.websocket_manager import websocket_manager
            from dotmac_isp.core.billing_events import register_billing_event_handlers
            
            await websocket_manager.start()
            await register_billing_event_handlers()
            return websocket_manager
            
        websocket_result = await startup_manager.execute_with_retry(
            operation=init_websocket,
            phase=StartupPhase.BACKGROUND_TASKS,
            component="WebSocket Manager",
            severity=StartupErrorSeverity.MEDIUM,
            max_retries=1
        )
        
        if websocket_result.success:
            logging.info("🔌 WebSocket manager and billing events initialized")
            app.state.websocket_manager = websocket_result.metadata.get("result")

        # Set up comprehensive health checks
        health_checker = setup_health_checker(
            service_name="DotMac ISP Framework",
            cache_client=getattr(app.state, 'cache_manager', None),
            additional_filesystem_paths=["logs", "uploads", "static"]
        )
        app.state.health_checker = health_checker
        startup_manager.add_metadata("health_checks_registered", len(health_checker.health_checks))
        
        logging.info("🚀 DotMac ISP Framework startup complete")
        
        # Store startup manager for shutdown
        app.state.startup_manager = startup_manager

    yield

    # Shutdown
    try:
        # Shutdown WebSocket manager
        try:
            from dotmac_isp.core.websocket_manager import websocket_manager
            await websocket_manager.stop()
            logging.info("🔌 WebSocket manager shutdown complete")
        except Exception as e:
            logging.error(f"⚠️  WebSocket manager shutdown failed: {e}")

        # Shutdown SignOz telemetry
        if hasattr(app.state, 'signoz_telemetry') and app.state.signoz_telemetry:
            try:
                app.state.signoz_telemetry.shutdown()
                logging.info("✅ SignOz telemetry shutdown complete")
            except Exception as e:
                logging.error(f"⚠️  SignOz shutdown failed: {e}")

        # Shutdown infrastructure
        await shutdown_infrastructure()

        # await close_database()
        logging.info("✅ DotMac ISP Framework shutdown complete")

    except Exception as e:
        logging.error(f"❌ Shutdown error: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="DotMac ISP Framework",
        description="Comprehensive ISP management system",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # Essential middleware (API Security Suite handles most security middleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)

    # Infrastructure middleware (caching, tracing, monitoring)  
    add_infrastructure_middleware(app, settings)

    # Add CSRF protection
    add_csrf_protection(app)

    # Add tenant security middleware
    add_tenant_security_middleware(app)

    # Security and audit middleware
    # setup_audit_middleware(app)  # Temporarily disabled to fix SQLAlchemy mapper conflicts

    # Custom middleware
    add_middleware(app)

    # Exception handlers
    add_exception_handlers(app)

    # Monitoring endpoints (/health, /metrics, /alerts, etc.)
    create_monitoring_endpoints(app)
    
    # Add comprehensive health check endpoints
    add_health_endpoints(app)
    add_startup_status_endpoint(app)

    # Register API routes
    register_routers(app)
    
    # Instrument FastAPI with SignOz
    if SIGNOZ_AVAILABLE and get_signoz:
        try:
            signoz_telemetry = get_signoz()
            if signoz_telemetry:
                signoz_telemetry.instrument_fastapi(app)
                logging.info("✅ FastAPI instrumented with SignOz observability")
        except Exception as e:
            logging.warning(f"⚠️  SignOz FastAPI instrumentation failed: {e}")

    return app


# Create the application instance
app = create_app()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "dotmac-isp-framework", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "DotMac ISP Framework API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/ssl-status")
async def ssl_status():
    """SSL certificate status endpoint."""
    settings = get_settings()
    if not settings.ssl_enabled:
        return {"ssl_enabled": False, "message": "SSL not enabled"}

    ssl_manager = get_ssl_manager()
    certificates = await ssl_manager.get_certificate_status()

    return {
        "ssl_enabled": True,
        "certificates": [
            {
                "domain": cert.domain,
                "expires_in_days": cert.days_until_expiry,
                "expiry_date": cert.expiry_date.isoformat(),
                "is_expiring": cert.is_expiring,
                "is_expired": cert.is_expired,
            }
            for cert in certificates
        ],
    }


@app.get("/celery-status")
async def celery_status():
    """Celery task queue status endpoint."""
    try:
        # Get active workers
        inspect = celery_app.control.inspect()

        # Check if we can connect to broker
        try:
            stats = inspect.stats()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()

            worker_count = len(stats) if stats else 0
            total_active = sum(
                len(tasks) for tasks in (active_tasks.values() if active_tasks else [])
            )
            total_scheduled = sum(
                len(tasks)
                for tasks in (scheduled_tasks.values() if scheduled_tasks else [])
            )

            return {
                "celery_enabled": True,
                "broker_url": celery_app.conf.broker_url,
                "workers_active": worker_count,
                "active_tasks": total_active,
                "scheduled_tasks": total_scheduled,
                "worker_stats": stats or {},
                "status": "healthy" if worker_count > 0 else "no_workers",
            }

        except Exception as e:
            return {
                "celery_enabled": True,
                "broker_url": celery_app.conf.broker_url,
                "status": "broker_unreachable",
                "error": str(e),
            }

    except Exception as e:
        return {
            "celery_enabled": False,
            "error": str(e),
            "message": "Celery not properly configured",
        }


@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint to prevent 404 errors."""
    from fastapi.responses import Response

    # Return empty 204 No Content response
    return Response(status_code=204)
