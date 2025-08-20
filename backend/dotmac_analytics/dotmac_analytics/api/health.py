"""
Health check API endpoints for analytics service.
"""

from datetime import datetime
from dotmac_analytics.core.datetime_utils import utc_now, utc_now_iso

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.config import get_config
from ..core.database import check_connection, get_session

health_router = APIRouter(prefix="/health", tags=["health"])


@health_router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "dotmac-analytics",
        "timestamp": utc_now(),
        "version": "1.0.0"
    }


@health_router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_session)):
    """Detailed health check with component status."""
    try:
        config = get_config()

        # Check database connection
        db_healthy = check_connection()

        # Check configuration
        config_errors = config.validate()
        config_healthy = len(config_errors) == 0

        # Overall health status
        overall_healthy = db_healthy and config_healthy

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "service": "dotmac-analytics",
            "timestamp": utc_now(),
            "version": "1.0.0",
            "components": {
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "details": "Connection successful" if db_healthy else "Connection failed"
                },
                "configuration": {
                    "status": "healthy" if config_healthy else "unhealthy",
                    "errors": config_errors if not config_healthy else []
                }
            },
            "environment": config.environment,
            "debug_mode": config.debug
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@health_router.get("/ready")
async def readiness_check(db: Session = Depends(get_session)):
    """Readiness check for Kubernetes deployments."""
    try:
        # Check if service is ready to handle requests
        db_healthy = check_connection()

        if not db_healthy:
            raise HTTPException(status_code=503, detail="Service not ready")

        return {
            "status": "ready",
            "timestamp": utc_now()
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


@health_router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes deployments."""
    return {
        "status": "alive",
        "timestamp": utc_now()
    }
