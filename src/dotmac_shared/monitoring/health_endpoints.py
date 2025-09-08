"""
FastAPI health check endpoints with production-ready monitoring.
Provides standardized health endpoints for all DotMac services.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .health_service import HealthMonitoringService, HealthStatus


def create_health_router(
    health_service: HealthMonitoringService,
    include_detailed: bool = True,
    include_liveness: bool = True,
    include_readiness: bool = True
) -> APIRouter:
    """
    Create FastAPI health check router.
    
    Args:
        health_service: Configured health monitoring service
        include_detailed: Include detailed health endpoint
        include_liveness: Include liveness probe endpoint  
        include_readiness: Include readiness probe endpoint
    """
    router = APIRouter(prefix="/health", tags=["Health"])
    
    @router.get("/", response_model=Dict[str, Any])
    async def health_check() -> Dict[str, Any]:
        """
        Basic health check endpoint.
        Returns overall system health status.
        """
        health_data = await health_service.get_system_health()
        
        # Set appropriate HTTP status code
        if health_data["status"] == HealthStatus.UNHEALTHY.value:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health_data["status"] == HealthStatus.DEGRADED.value:
            status_code = status.HTTP_200_OK  # Still operational
        else:
            status_code = status.HTTP_200_OK
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": health_data["status"],
                "timestamp": health_data["timestamp"],
                "version": "1.0.0",  # Could be injected from environment
                "service": "dotmac-framework"
            }
        )
    
    if include_detailed:
        @router.get("/detailed", response_model=Dict[str, Any])
        async def detailed_health_check() -> Dict[str, Any]:
            """
            Detailed health check endpoint.
            Returns comprehensive system health with all check results.
            """
            health_data = await health_service.get_system_health()
            
            # Set appropriate HTTP status code
            if health_data["status"] == HealthStatus.UNHEALTHY.value:
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            elif health_data["status"] == HealthStatus.DEGRADED.value:
                status_code = status.HTTP_200_OK
            else:
                status_code = status.HTTP_200_OK
            
            return JSONResponse(
                status_code=status_code,
                content=health_data
            )
    
    if include_liveness:
        @router.get("/live", response_model=Dict[str, Any])
        async def liveness_probe() -> Dict[str, Any]:
            """
            Kubernetes liveness probe endpoint.
            Returns 200 if the application is running and can serve requests.
            """
            # Run only critical checks for liveness
            results = await health_service.run_all_checks()
            
            critical_checks = [
                result for name, result in results.items()
                if health_service.checks[name].critical
            ]
            
            # If any critical check is unhealthy, the service is not live
            unhealthy_critical = [
                result for result in critical_checks
                if result.status == HealthStatus.UNHEALTHY
            ]
            
            if unhealthy_critical:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "status": "unhealthy",
                        "failed_checks": [check.name for check in unhealthy_critical]
                    }
                )
            
            return {
                "status": "alive",
                "timestamp": int(time.time())
            }
    
    if include_readiness:
        @router.get("/ready", response_model=Dict[str, Any])
        async def readiness_probe() -> Dict[str, Any]:
            """
            Kubernetes readiness probe endpoint.
            Returns 200 if the application is ready to serve requests.
            """
            health_data = await health_service.get_system_health()
            
            # Service is ready if it's healthy or degraded (but not unhealthy)
            if health_data["status"] == HealthStatus.UNHEALTHY.value:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "status": "not_ready",
                        "reason": "Critical health checks failing"
                    }
                )
            
            return {
                "status": "ready",
                "timestamp": int(time.time())
            }
    
    @router.get("/metrics", response_model=Dict[str, Any])
    async def health_metrics() -> Dict[str, Any]:
        """
        Health metrics endpoint for monitoring systems.
        Returns metrics data for SigNoz integration.
        """
        health_data = await health_service.get_system_health()
        
        metrics = {
            "health_check_total": health_data["summary"]["total"],
            "health_check_healthy": health_data["summary"]["healthy"], 
            "health_check_unhealthy": health_data["summary"]["unhealthy"],
            "health_check_success_rate": health_data["summary"]["success_rate"],
            "health_status": {
                "healthy": 1 if health_data["status"] == "healthy" else 0,
                "degraded": 1 if health_data["status"] == "degraded" else 0,
                "unhealthy": 1 if health_data["status"] == "unhealthy" else 0
            },
            "check_latencies": {
                name: check_data.get("latency_ms", 0)
                for name, check_data in health_data["checks"].items()
                if check_data.get("latency_ms") is not None
            }
        }
        
        return {
            "metrics": metrics,
            "timestamp": health_data["timestamp"]
        }
    
    return router


def create_simple_health_router() -> APIRouter:
    """
    Create a simple health router for services that don't need comprehensive monitoring.
    """
    router = APIRouter(prefix="/health", tags=["Health"])
    
    @router.get("/")
    async def simple_health_check() -> Dict[str, Any]:
        """Simple health check that just returns OK."""
        return {
            "status": "healthy",
            "timestamp": int(time.time()),
            "service": "dotmac-service"
        }
    
    @router.get("/live")
    async def simple_liveness() -> Dict[str, Any]:
        """Simple liveness probe."""
        return {
            "status": "alive",
            "timestamp": int(time.time())
        }
    
    @router.get("/ready")  
    async def simple_readiness() -> Dict[str, Any]:
        """Simple readiness probe."""
        return {
            "status": "ready",
            "timestamp": int(time.time())
        }
    
    return router


# Middleware for request metrics
class HealthMetricsMiddleware:
    """Middleware to collect basic request metrics for health monitoring."""
    
    def __init__(self, app):
        self.app = app
        self.request_count = 0
        self.error_count = 0
        self.start_time = time.time()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            self.request_count += 1
            
            # Intercept response to count errors
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    status_code = message.get("status", 200)
                    if status_code >= 500:
                        self.error_count += 1
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        uptime = time.time() - self.start_time
        return {
            "requests_total": self.request_count,
            "errors_total": self.error_count,
            "uptime_seconds": uptime,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0
        }


# Export main components
__all__ = [
    'create_health_router',
    'create_simple_health_router', 
    'HealthMetricsMiddleware'
]
