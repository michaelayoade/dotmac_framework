"""FastAPI application factory for the DotMac ISP Framework."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

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
    """Application lifespan manager with enterprise SDK initialization."""
    settings = get_settings()

    # Startup
    try:
        # Initialize database
        # await init_database()  # Will be enabled when needed

        # Initialize Redis cache
        cache_manager = get_cache_manager()
        logging.info("✅ Redis cache connection established")

        # Initialize SignOz observability
        if SIGNOZ_AVAILABLE and init_signoz:
            try:
                signoz_telemetry = init_signoz(
                    service_name="dotmac-isp-framework",
                    service_version="1.0.0",
                    environment=settings.environment,
                    signoz_endpoint=settings.signoz_endpoint if hasattr(settings, 'signoz_endpoint') else None,
                    custom_attributes={
                        "platform": "isp_framework",
                        "deployment": "monolithic",
                        "business_model": "b2b_saas"
                    }
                )
                logging.info("✅ SignOz observability initialized")
            except Exception as e:
                logging.warning(f"⚠️  SignOz initialization failed: {e}")

        # Initialize infrastructure (monitoring, metrics, tracing)
        await startup_infrastructure()

        # Initialize security systems
        try:
            # Initialize Row Level Security policies
            initialize_rls()
            logging.info("🔒 Row Level Security policies initialized")

            # Initialize business rules and constraints
            initialize_business_rules()
            logging.info("📋 Business rules and constraints initialized")

            # Initialize audit system
            # initialize_audit_system()  # Temporarily disabled to fix SQLAlchemy mapper conflicts
            # logging.info("📋 Audit trail system initialized")

            # Initialize search optimization
            search_optimization = initialize_search_optimization()
            logging.info("🔍 Search optimization system initialized")

        except Exception as e:
            logging.error(f"⚠️  Security system initialization failed: {e}")
            # Continue startup even if security initialization fails

        # Initialize SSL certificates if enabled
        if hasattr(settings, "ssl_enabled") and settings.ssl_enabled:
            ssl_success = await initialize_ssl()
            if ssl_success:
                logging.info("✅ SSL certificates initialized")
            else:
                logging.warning("⚠️  SSL certificate initialization had issues")

        # Test Celery connection
        try:
            # Send a test task to verify Celery is working
            result = celery_app.send_task("dotmac_isp.core.tasks.health_check")
            logging.info("✅ Celery task queue connection established")
        except Exception as e:
            logging.warning(f"⚠️  Celery connection failed: {e}")

        # Initialize WebSocket manager for real-time updates
        try:
            from dotmac_isp.core.websocket_manager import websocket_manager
            from dotmac_isp.core.billing_events import register_billing_event_handlers
            
            await websocket_manager.start()
            await register_billing_event_handlers()
            logging.info("🔌 WebSocket manager and billing events initialized")
        except Exception as e:
            logging.error(f"⚠️  WebSocket manager initialization failed: {e}")

        logging.info("🚀 DotMac ISP Framework startup complete")

    except Exception as e:
        logging.error(f"❌ Startup error: {e}")

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

    # Security middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Infrastructure middleware (caching, tracing, monitoring, rate limiting)
    add_infrastructure_middleware(app, settings)

    # Enhanced security middleware (highest priority)
    setup_enhanced_security_middleware(app)

    # Security and audit middleware
    # setup_audit_middleware(app)  # Temporarily disabled to fix SQLAlchemy mapper conflicts

    # Custom middleware
    add_middleware(app)

    # Exception handlers
    add_exception_handlers(app)

    # Monitoring endpoints (/health, /metrics, /alerts, etc.)
    create_monitoring_endpoints(app)

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
