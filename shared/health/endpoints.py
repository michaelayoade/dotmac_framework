"""
Health check endpoints for FastAPI applications.

Provides standardized health check endpoints with comprehensive
status reporting and dependency checking.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .comprehensive_checks import HealthChecker, HealthStatus


logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Health check response model."""
    service_name: str
    overall_status: str
    message: str
    timestamp: str
    total_checks: int
    healthy_count: int
    degraded_count: int
    unhealthy_count: int
    unknown_count: int
    checks: Dict[str, Any]


class ReadinessResponse(BaseModel):
    """Readiness check response model."""
    ready: bool
    message: str
    timestamp: str
    checks: Dict[str, Any]


class LivenessResponse(BaseModel):
    """Liveness check response model."""
    alive: bool
    message: str
    timestamp: str
    uptime_seconds: float


def get_health_checker(request: Request) -> HealthChecker:
    """Get health checker from app state."""
    health_checker = getattr(request.app.state, 'health_checker', None)
    if not health_checker:
        raise HTTPException(status_code=503, detail="Health checker not initialized")
    return health_checker


def add_health_endpoints(app: FastAPI) -> None:
    """Add comprehensive health check endpoints to FastAPI app."""
    
    # Store startup time for uptime calculation
    if not hasattr(app.state, 'startup_time'):
        app.state.startup_time = datetime.now(timezone.utc)
    
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Comprehensive health check",
        description="Get overall system health status with detailed component checks"
    )
    async def health_check(
        check_name: Optional[str] = Query(None, description="Run specific health check only"),
        parallel: bool = Query(True, description="Run checks in parallel for faster response"),
        health_checker: HealthChecker = Depends(get_health_checker)
    ) -> HealthResponse:
        """
        Comprehensive health check endpoint.
        
        Returns overall system health status and individual component health checks.
        Can run all checks or a specific named check.
        """
        try:
            if check_name:
                # Run specific check
                result = await health_checker.run_check(check_name)
                overall_status = health_checker.get_overall_status({check_name: result})
            else:
                # Run all checks
                results = await health_checker.run_all_checks(parallel=parallel)
                overall_status = health_checker.get_overall_status(results)
            
            return HealthResponse(**overall_status)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")
    
    @app.get(
        "/health/ready",
        response_model=ReadinessResponse,
        tags=["Health"],
        summary="Readiness check",
        description="Check if the service is ready to handle requests"
    )
    async def readiness_check(
        health_checker: HealthChecker = Depends(get_health_checker)
    ) -> Dict[str, Any]:
        """
        Kubernetes-style readiness check.
        
        Returns whether the service is ready to handle requests.
        A service is ready if no components are unhealthy.
        """
        try:
            results = await health_checker.run_all_checks(parallel=True)
            overall_status = health_checker.get_overall_status(results)
            
            # Service is ready if no unhealthy components
            ready = overall_status.get("unhealthy_count", 0) == 0
            
            # If not ready, return 503 status
            status_code = 200 if ready else 503
            
            response_data = ReadinessResponse(
                ready=ready,
                message=overall_status.get("message", "Unknown status"),
                timestamp=datetime.now(timezone.utc).isoformat(),
                checks={
                    name: {
                        "status": result.status.value,
                        "message": result.message
                    }
                    for name, result in results.items()
                }
            )
            
            return JSONResponse(
                status_code=status_code,
                content=response_data.model_dump()
            )
            
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return JSONResponse(
                status_code=503,
                content=ReadinessResponse(
                    ready=False,
                    message=f"Readiness check failed: {str(e)}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    checks={}
                ).model_dump()
            )
    
    @app.get(
        "/health/live",
        response_model=LivenessResponse,
        tags=["Health"],
        summary="Liveness check",
        description="Check if the service is alive and responding"
    )
    async def liveness_check() -> Dict[str, Any]:
        """
        Kubernetes-style liveness check.
        
        Returns whether the service is alive. This is a minimal check
        that should only fail if the service needs to be restarted.
        """
        try:
            uptime = (datetime.now(timezone.utc) - app.state.startup_time).total_seconds()
            
            return LivenessResponse(
                alive=True,
                message="Service is alive and responding",
                timestamp=datetime.now(timezone.utc).isoformat(),
                uptime_seconds=uptime
            )
            
        except Exception as e:
            logger.error(f"Liveness check failed: {e}")
            return JSONResponse(
                status_code=503,
                content=LivenessResponse(
                    alive=False,
                    message=f"Liveness check failed: {str(e)}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    uptime_seconds=0.0
                ).model_dump()
            )
    
    @app.get(
        "/health/metrics",
        tags=["Health"],
        summary="Health metrics",
        description="Get detailed health metrics for monitoring"
    )
    async def health_metrics(
        check_name: Optional[str] = Query(None, description="Get metrics for specific check"),
        health_checker: HealthChecker = Depends(get_health_checker)
    ) -> Dict[str, Any]:
        """
        Health metrics endpoint for monitoring systems.
        
        Returns detailed metrics from health checks in a format
        suitable for monitoring systems like Prometheus.
        """
        try:
            if check_name:
                result = await health_checker.run_check(check_name)
                results = {check_name: result}
            else:
                results = await health_checker.run_all_checks(parallel=True)
            
            metrics = {}
            
            for name, result in results.items():
                check_metrics = {
                    "status": result.status.value,
                    "duration_ms": result.duration_ms,
                    "timestamp": result.timestamp.isoformat(),
                }
                
                # Add component-specific metrics
                for metric in result.metrics:
                    metrics[f"{name}_{metric.name}"] = {
                        "value": metric.value,
                        "unit": metric.unit,
                        "status": metric.status.value,
                        "warning_threshold": metric.warning_threshold,
                        "critical_threshold": metric.critical_threshold
                    }
                
                metrics[name] = check_metrics
            
            return metrics
            
        except Exception as e:
            logger.error(f"Health metrics failed: {e}")
            raise HTTPException(status_code=503, detail=f"Health metrics failed: {str(e)}")
    
    @app.get(
        "/health/trends/{check_name}",
        tags=["Health"],
        summary="Health trends",
        description="Get health trends for a specific check over time"
    )
    async def health_trends(
        check_name: str,
        hours: int = Query(24, description="Number of hours to look back"),
        health_checker: HealthChecker = Depends(get_health_checker)
    ) -> Dict[str, Any]:
        """
        Health trends endpoint for analyzing health patterns over time.
        
        Returns health status trends for a specific component over the
        specified time period.
        """
        try:
            trends = health_checker.get_health_trends(check_name, hours)
            return trends
            
        except Exception as e:
            logger.error(f"Health trends failed: {e}")
            raise HTTPException(status_code=500, detail=f"Health trends failed: {str(e)}")
    
    @app.post(
        "/health/run/{check_name}",
        tags=["Health"],
        summary="Run specific health check",
        description="Manually trigger a specific health check"
    )
    async def run_health_check(
        check_name: str,
        health_checker: HealthChecker = Depends(get_health_checker)
    ) -> Dict[str, Any]:
        """
        Manually trigger a specific health check.
        
        Useful for testing and debugging health check implementations.
        """
        try:
            result = await health_checker.run_check(check_name)
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Manual health check failed: {e}")
            raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
    
    logger.info("✅ Health check endpoints added to FastAPI application")


def add_startup_status_endpoint(app: FastAPI) -> None:
    """Add startup status endpoint to show startup process results."""
    
    @app.get(
        "/health/startup",
        tags=["Health"],
        summary="Startup status",
        description="Get information about the service startup process"
    )
    async def startup_status() -> Dict[str, Any]:
        """
        Startup status endpoint.
        
        Returns information about how the service started up,
        including any errors or warnings from the startup process.
        """
        startup_manager = getattr(app.state, 'startup_manager', None)
        
        if not startup_manager:
            return {
                "status": "unknown",
                "message": "No startup information available"
            }
        
        return {
            "service_name": startup_manager.service_name,
            "environment": startup_manager.environment,
            "startup_errors": [error.to_dict() for error in startup_manager.startup_errors],
            "startup_warnings": startup_manager.startup_warnings,
            "startup_metadata": startup_manager.startup_metadata,
            "should_continue": startup_manager.should_continue_startup(),
            "has_critical_errors": any(
                error.severity.value == "critical"
                for error in startup_manager.startup_errors
            )
        }
    
    logger.info("✅ Startup status endpoint added to FastAPI application")