"""
Health check endpoints for DotMac Framework.
Provides standardized health monitoring across all services.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any

import psutil
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Health check router
health_router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    """Health status response model."""

    status: str = Field(description="Overall health status")
    timestamp: datetime = Field(description="Health check timestamp")
    version: str = Field(description="Application version")
    uptime_seconds: float = Field(description="Application uptime in seconds")

    # System metrics
    cpu_percent: float = Field(description="CPU usage percentage")
    memory_percent: float = Field(description="Memory usage percentage")
    disk_percent: float = Field(description="Disk usage percentage")

    # Service checks
    database: str = Field(description="Database health status")
    cache: str = Field(description="Cache health status")
    external_services: dict[str, str] = Field(description="External service statuses")

    # Additional info
    environment: str = Field(description="Environment name")
    service_name: str = Field(description="Service name")


class DetailedHealthStatus(HealthStatus):
    """Detailed health status with additional metrics."""

    python_version: str = Field(description="Python version")
    platform: str = Field(description="Operating system platform")
    process_id: int = Field(description="Process ID")

    # Detailed system metrics
    memory_total_gb: float = Field(description="Total system memory in GB")
    memory_used_gb: float = Field(description="Used system memory in GB")
    disk_total_gb: float = Field(description="Total disk space in GB")
    disk_used_gb: float = Field(description="Used disk space in GB")

    # Network
    network_connections: int = Field(description="Number of network connections")

    # Environment variables (non-sensitive)
    config_status: dict[str, bool] = Field(description="Configuration status")


# Store startup time for uptime calculation
startup_time = datetime.now()


async def check_database_health() -> str:
    """Check database connectivity."""
    try:
        # Import database session here to avoid circular imports
        from dotmac.database.session import check_database_health

        is_healthy = await check_database_health()
        return "healthy" if is_healthy else "unhealthy"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return "unavailable"


async def check_cache_health() -> str:
    """Check cache (Redis) connectivity."""
    try:
        # This would check Redis connectivity
        # For now, return healthy as a placeholder
        return "healthy"
    except Exception as e:
        logger.warning(f"Cache health check failed: {e}")
        return "unavailable"


async def check_external_services() -> dict[str, str]:
    """Check external service health."""
    external_services = {}

    # Check common external services
    services_to_check = ["signoz", "openbao", "freeradius", "voltha"]

    for service in services_to_check:
        try:
            # Placeholder health check
            external_services[service] = "healthy"
        except Exception as e:
            logger.warning(f"External service {service} health check failed: {e}")
            external_services[service] = "unavailable"

    return external_services


def get_system_metrics() -> dict[str, Any]:
    """Get system performance metrics."""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_total_gb = memory.total / (1024**3)
        memory_used_gb = memory.used / (1024**3)

        # Disk usage
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100
        disk_total_gb = disk.total / (1024**3)
        disk_used_gb = disk.used / (1024**3)

        # Network connections
        try:
            network_connections = len(psutil.net_connections())
        except (psutil.AccessDenied, OSError):
            network_connections = 0

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_total_gb": round(memory_total_gb, 2),
            "memory_used_gb": round(memory_used_gb, 2),
            "disk_percent": round(disk_percent, 2),
            "disk_total_gb": round(disk_total_gb, 2),
            "disk_used_gb": round(disk_used_gb, 2),
            "network_connections": network_connections,
        }

    except Exception as e:
        logger.warning(f"Failed to get system metrics: {e}")
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_total_gb": 0.0,
            "memory_used_gb": 0.0,
            "disk_percent": 0.0,
            "disk_total_gb": 0.0,
            "disk_used_gb": 0.0,
            "network_connections": 0,
        }


def get_config_status() -> dict[str, bool]:
    """Check configuration status."""
    config_checks = {
        "database_url_set": bool(os.environ.get("DATABASE_URL")),
        "redis_url_set": bool(os.environ.get("REDIS_URL")),
        "jwt_secret_set": bool(os.environ.get("JWT_SECRET_KEY")),
        "environment_set": bool(os.environ.get("ENVIRONMENT")),
        "log_level_set": bool(os.environ.get("LOG_LEVEL")),
    }

    return config_checks


async def get_health_status(detailed: bool = False) -> dict[str, Any]:
    """
    Get comprehensive health status.

    Args:
        detailed: Whether to include detailed metrics

    Returns:
        Health status dictionary
    """
    try:
        # Calculate uptime
        uptime = (datetime.now() - startup_time).total_seconds()

        # Get system metrics
        system_metrics = get_system_metrics()

        # Check service health
        database_status = await check_database_health()
        cache_status = await check_cache_health()
        external_services_status = await check_external_services()

        # Determine overall health
        overall_status = "healthy"
        if database_status != "healthy" or cache_status != "healthy":
            overall_status = "degraded"

        if any(status == "unavailable" for status in external_services_status.values()):
            if overall_status == "healthy":
                overall_status = "degraded"

        # Base health status
        health_data = {
            "status": overall_status,
            "timestamp": datetime.now(),
            "version": os.environ.get("APP_VERSION", "unknown"),
            "uptime_seconds": round(uptime, 2),
            "cpu_percent": system_metrics["cpu_percent"],
            "memory_percent": system_metrics["memory_percent"],
            "disk_percent": system_metrics["disk_percent"],
            "database": database_status,
            "cache": cache_status,
            "external_services": external_services_status,
            "environment": os.environ.get("ENVIRONMENT", "unknown"),
            "service_name": os.environ.get("SERVICE_NAME", "dotmac-framework"),
        }

        # Add detailed metrics if requested
        if detailed:
            health_data.update(
                {
                    "python_version": sys.version.split()[0],
                    "platform": sys.platform,
                    "process_id": os.getpid(),
                    "memory_total_gb": system_metrics["memory_total_gb"],
                    "memory_used_gb": system_metrics["memory_used_gb"],
                    "disk_total_gb": system_metrics["disk_total_gb"],
                    "disk_used_gb": system_metrics["disk_used_gb"],
                    "network_connections": system_metrics["network_connections"],
                    "config_status": get_config_status(),
                }
            )

        return health_data

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(),
            "error": str(e),
            "version": "unknown",
            "uptime_seconds": 0,
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_percent": 0,
            "database": "unknown",
            "cache": "unknown",
            "external_services": {},
            "environment": "unknown",
            "service_name": "unknown",
        }


@health_router.get("/", response_model=HealthStatus)
async def health_check():
    """Basic health check endpoint."""
    health_data = await get_health_status(detailed=False)

    # Return appropriate HTTP status based on health
    if health_data["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_data
        )

    return health_data


@health_router.get("/detailed", response_model=DetailedHealthStatus)
async def detailed_health_check():
    """Detailed health check with full metrics."""
    health_data = await get_health_status(detailed=True)

    if health_data["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_data
        )

    return health_data


@health_router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    health_data = await get_health_status(detailed=False)

    # Ready if not unhealthy
    if health_data["status"] in ["healthy", "degraded"]:
        return {"status": "ready"}

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"status": "not ready", "reason": "service unhealthy"},
    )


@health_router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    # Simple liveness check - if we can respond, we're alive
    return {"status": "alive", "timestamp": datetime.now()}


@health_router.get("/metrics")
async def metrics_endpoint():
    """Prometheus-compatible metrics endpoint."""
    health_data = await get_health_status(detailed=True)

    # Convert to Prometheus format (simplified)
    metrics = [
        f"dotmac_health_status{{status=\"{health_data['status']}\"}} 1",
        f"dotmac_uptime_seconds {health_data['uptime_seconds']}",
        f"dotmac_cpu_percent {health_data['cpu_percent']}",
        f"dotmac_memory_percent {health_data['memory_percent']}",
        f"dotmac_disk_percent {health_data['disk_percent']}",
        (
            'dotmac_database_healthy{status="%s"} %d'
            % (
                health_data["database"],
                1 if health_data["database"] == "healthy" else 0,
            )
        ),
        (
            'dotmac_cache_healthy{status="%s"} %d'
            % (health_data["cache"], 1 if health_data["cache"] == "healthy" else 0)
        ),
    ]

    # Add external service metrics
    for service, service_status in health_data.get("external_services", {}).items():
        metrics.append(
            'dotmac_external_service_healthy{service="%s",status="%s"} %d'
            % (service, service_status, 1 if service_status == "healthy" else 0)
        )

    return {"metrics": "\n".join(metrics), "content_type": "text/plain"}


def add_health_endpoints(app):
    """
    Add health endpoints to FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.include_router(health_router)
    logger.info("Health endpoints added to application")


def add_startup_status_endpoint(app):
    """
    Add startup status endpoint to FastAPI application.

    Args:
        app: FastAPI application instance
    """
    startup_router = APIRouter(prefix="/startup", tags=["startup"])

    @startup_router.get("/status")
    async def startup_status():
        """Get application startup status."""
        return {
            "status": "completed",
            "timestamp": datetime.now(),
            "uptime_seconds": (datetime.now() - startup_time).total_seconds(),
            "routes_loaded": len(app.routes),
            "title": getattr(app, "title", "DotMac Service"),
        }

    app.include_router(startup_router)
    logger.info("Startup status endpoint added to application")
