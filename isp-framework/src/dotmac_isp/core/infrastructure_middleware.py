"""Infrastructure middleware integration for caching, tracing, and monitoring."""

import time
import logging
from typing import Callable, Dict, Any
from datetime import datetime

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from dotmac_isp.core.caching_middleware import ResponseCacheMiddleware
from dotmac_isp.core.rate_limiting import RateLimitMiddleware
from dotmac_isp.core.tracing import TracingMiddleware, trace_context
from dotmac_isp.core.monitoring import app_monitor, metrics_collector

logger = logging.getLogger(__name__)


class InfrastructureMiddleware(BaseHTTPMiddleware):
    """Combined infrastructure middleware for monitoring and metrics."""

    def __init__(self, app, service_name: str = "dotmac-isp"):
        """  Init   operation."""
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with infrastructure monitoring."""
        start_time = time.time()

        # Extract request info
        method = request.method
        path = str(request.url.path)
        user_agent = request.headers.get("User-Agent", "")

        # Record request start
        metrics_collector.counter(
            "http.requests.started", 1, {"method": method, "endpoint": path}
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Record successful request metrics
            app_monitor.record_request_metrics(
                method=method,
                endpoint=path,
                status_code=response.status_code,
                duration=duration,
            )

            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

            # Log request completion
            logger.info(f"{method} {path} {response.status_code} {duration:.3f}s")

            return response

        except Exception as e:
            # Calculate duration for failed request
            duration = time.time() - start_time

            # Record error metrics
            if isinstance(e, HTTPException):
                status_code = e.status_code
            else:
                status_code = 500

            app_monitor.record_request_metrics(
                method=method, endpoint=path, status_code=status_code, duration=duration
            )

            # Record error details
            metrics_collector.counter(
                "http.requests.exceptions",
                1,
                {
                    "method": method,
                    "endpoint": path,
                    "exception_type": type(e).__name__,
                },
            )

            # Log error
            logger.error(f"{method} {path} ERROR {duration:.3f}s: {e}")

            # Re-raise exception
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware."""

    def __init__(self, app):
        """  Init   operation."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        )

        # HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


def add_infrastructure_middleware(app, settings):
    """Add all infrastructure middleware to FastAPI app."""

    # Security headers (first - applied to all responses)
    app.add_middleware(SecurityHeadersMiddleware)

    # Infrastructure monitoring and metrics
    app.add_middleware(InfrastructureMiddleware, service_name=settings.app_name)

    # Distributed tracing
    app.add_middleware(TracingMiddleware, service_name=settings.app_name)

    # Rate limiting
    rate_limit_rules = {
        "/auth/": "10/minute",
        "/upload": "5/minute",
        "/payment": "20/minute",
        "/api/v1/analytics": "50/minute",
    }

    app.add_middleware(
        RateLimitMiddleware,
        default_rate_limit="100/minute",
        per_ip_limit="60/minute",
        per_user_limit="1000/minute",
        rate_limit_rules=rate_limit_rules,
        exempt_paths=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
    )

    # Response caching (last - caches final response)
    cache_patterns = ["/api/v1/"]
    exclude_patterns = [
        "/auth/",
        "/logout",
        "/upload",
        "/payment",
        "/health",
        "/metrics",
    ]

    app.add_middleware(
        ResponseCacheMiddleware,
        default_ttl=300,  # 5 minutes
        cache_patterns=cache_patterns,
        exclude_patterns=exclude_patterns,
    )

    logger.info("✅ Infrastructure middleware configured")


# Monitoring endpoints
def create_monitoring_endpoints(app):
    """Add monitoring and health check endpoints."""

    from fastapi import APIRouter
    from dotmac_isp.core.monitoring import (
        health_checker,
        metrics_collector,
        system_monitor,
        app_monitor,
        alert_manager,
    )

    monitoring_router = APIRouter(prefix="/monitoring", tags=["monitoring"])

    @monitoring_router.get("/health")
    async def health_check():
        """Comprehensive health check endpoint."""
        return health_checker.run_health_checks()

    @monitoring_router.get("/metrics")
    async def get_metrics():
        """Get current system metrics."""
        # Collect fresh metrics
        system_monitor.collect_system_metrics()
        app_monitor.collect_application_metrics()

        # Return key metrics
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": metrics_collector.get_metric("system.cpu.percent"),
                "memory_percent": metrics_collector.get_metric("system.memory.percent"),
                "disk_percent": metrics_collector.get_metric("system.disk.percent"),
            },
            "application": {
                "redis_hit_ratio": metrics_collector.get_metric("redis.hit_ratio"),
                "redis_used_memory_mb": metrics_collector.get_metric(
                    "redis.used_memory_mb"
                ),
                "redis_connected_clients": metrics_collector.get_metric(
                    "redis.connected_clients"
                ),
            },
            "http": {
                "requests_total": metrics_collector.get_metric("http.requests.total"),
                "requests_errors": metrics_collector.get_metric("http.requests.errors"),
            },
        }

    @monitoring_router.get("/alerts")
    async def get_alerts():
        """Get active alerts."""
        return {
            "alerts": alert_manager.get_active_alerts(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    @monitoring_router.post("/alerts/{alert_id}/resolve")
    async def resolve_alert(alert_id: str):
        """Resolve an alert."""
        alert_manager.resolve_alert(alert_id)
        return {"message": f"Alert {alert_id} resolved"}

    @monitoring_router.get("/metrics/{metric_name}/history")
    async def get_metric_history(metric_name: str, hours: int = 24):
        """Get metric history."""
        history = metrics_collector.get_metric_history(metric_name, hours)
        return {
            "metric_name": metric_name,
            "hours": hours,
            "data_points": len(history),
            "history": history,
        }

    @monitoring_router.get("/traces/{trace_id}")
    async def get_trace(trace_id: str):
        """Get trace information."""
        from dotmac_isp.core.tracing import tracing_service

        trace_data = tracing_service.get_trace(trace_id)
        if not trace_data:
            raise HTTPException(status_code=404, detail="Trace not found")

        return {"trace_id": trace_id, "spans": trace_data}

    @monitoring_router.get("/performance")
    async def get_performance_metrics():
        """Get performance analytics."""
        from dotmac_isp.core.tracing import tracing_service

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "operations": tracing_service.get_performance_metrics(),
        }

    # Add router to app
    app.include_router(monitoring_router)

    # Simple health endpoint (without prefix for load balancers)
    @app.get("/health")
    async def simple_health():
        """Simple health check for load balancers."""
        try:
            # Quick Redis check
            metrics_collector.cache_manager.redis_client.ping()
            return {"status": "healthy"}
        except:
            raise HTTPException(status_code=503, detail="Service unhealthy")

    @app.get("/ready")
    async def readiness_check():
        """Kubernetes readiness check."""
        health_result = health_checker.run_health_checks()

        if health_result["status"] in ["healthy", "degraded"]:
            return health_result
        else:
            raise HTTPException(status_code=503, detail="Service not ready")

    logger.info("✅ Monitoring endpoints configured")


# Startup/shutdown handlers
async def startup_infrastructure():
    """Initialize infrastructure on startup."""
    from dotmac_isp.core.monitoring import (
        system_monitor,
        app_monitor,
        alert_manager,
        setup_default_alerts,
        setup_default_health_checks,
    )
    from dotmac_isp.core.tasks import schedule_metrics_collection

    logger.info("🚀 Initializing infrastructure...")

    # Collect initial metrics
    system_monitor.collect_system_metrics()
    app_monitor.collect_application_metrics()

    # Check alerts
    alert_manager.check_alerts()

    # Schedule periodic metrics collection
    schedule_metrics_collection()

    logger.info("✅ Infrastructure initialized")


async def shutdown_infrastructure():
    """Clean up infrastructure on shutdown."""
    logger.info("🛑 Shutting down infrastructure...")

    # Clear trace context
    trace_context.clear()

    logger.info("✅ Infrastructure shutdown complete")
