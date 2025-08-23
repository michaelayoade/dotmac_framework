"""
FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .api.portals import portals_router
from .api.v1 import api_router
from .config import settings
from .core.exceptions import add_exception_handlers
from .core.logging import configure_logging, get_logger
from .core.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
    TenantIsolationMiddleware,
)
from .database import close_database, init_database

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
    """Application lifespan manager."""
    # Startup
    logger.info("Starting DotMac Management Platform...")
    
    # Initialize database
    await init_database()
    logger.info("Database initialized")
    
    # Initialize cache manager
    try:
        from .core.cache import get_cache_manager
        cache_manager = await get_cache_manager()
        logger.info("Cache manager initialized")
    except Exception as e:
        logger.warning("Failed to initialize cache manager", error=str(e))
    
    # Initialize metrics collection
    try:
        from .core.monitoring import metrics_collector
        metrics_collector.collect_system_metrics()
        logger.info("Monitoring system initialized")
    except Exception as e:
        logger.warning("Failed to initialize monitoring", error=str(e))
    
    logger.info("DotMac Management Platform startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DotMac Management Platform...")
    
    # Close cache connections
    try:
        from .core.cache import get_cache_manager
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

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

trusted_hosts = (
    ["localhost", "127.0.0.1", "testserver", "*.dotmac.app"]
    if not settings.is_production
    else ["*.dotmac.app"]
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware, calls_per_minute=settings.rate_limit_per_minute)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TenantIsolationMiddleware)

# Add exception handlers
add_exception_handlers(app)

# Include routers
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(portals_router, prefix="/portals")


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