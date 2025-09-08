"""
Production-ready health monitoring service with comprehensive checks.
Provides standardized health check patterns for all DotMac services.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import httpx
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    latency_ms: Optional[int] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class HealthCheckConfig:
    """Configuration for a health check."""
    name: str
    check_function: Callable
    timeout_seconds: int = 5
    critical: bool = True
    interval_seconds: int = 30
    retry_count: int = 3


class HealthMonitoringService:
    """
    Comprehensive health monitoring service.
    
    Provides:
    - Database connectivity checks
    - Redis connectivity checks
    - External service checks
    - Custom health checks
    - Metrics collection
    - Alerting integration
    """
    
    def __init__(self):
        self.checks: Dict[str, HealthCheckConfig] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def register_check(self, config: HealthCheckConfig) -> None:
        """Register a new health check."""
        self.checks[config.name] = config
        self.logger.info(f"Registered health check: {config.name}")
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found"
            )
        
        config = self.checks[name]
        start_time = time.time()
        
        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                config.check_function(),
                timeout=config.timeout_seconds
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if isinstance(result, HealthCheckResult):
                result.latency_ms = latency_ms
                return result
            elif isinstance(result, bool):
                return HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    message="OK" if result else "Check failed",
                    latency_ms=latency_ms
                )
            else:
                return HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message=str(result),
                    latency_ms=latency_ms
                )
                
        except asyncio.TimeoutError:
            latency_ms = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {config.timeout_seconds}s",
                latency_ms=latency_ms
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self.logger.error(f"Health check '{name}' failed: {e}")
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                latency_ms=latency_ms
            )
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}
        
        # Run checks concurrently
        tasks = []
        for name in self.checks:
            task = asyncio.create_task(self.run_check(name))
            tasks.append((name, task))
        
        # Collect results
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
                self.last_results[name] = result
            except Exception as e:
                self.logger.error(f"Failed to run health check '{name}': {e}")
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Failed to run check: {str(e)}"
                )
        
        return results
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        results = await self.run_all_checks()
        
        # Calculate overall health
        critical_checks = [
            result for name, result in results.items()
            if self.checks[name].critical
        ]
        
        unhealthy_critical = [
            result for result in critical_checks
            if result.status == HealthStatus.UNHEALTHY
        ]
        
        degraded_critical = [
            result for result in critical_checks
            if result.status == HealthStatus.DEGRADED
        ]
        
        if unhealthy_critical:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_critical:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Calculate metrics
        total_checks = len(results)
        healthy_checks = len([r for r in results.values() if r.status == HealthStatus.HEALTHY])
        unhealthy_checks = len([r for r in results.values() if r.status == HealthStatus.UNHEALTHY])
        
        return {
            "status": overall_status.value,
            "timestamp": int(time.time()),
            "checks": {name: {
                "status": result.status.value,
                "message": result.message,
                "latency_ms": result.latency_ms,
                "details": result.details
            } for name, result in results.items()},
            "summary": {
                "total": total_checks,
                "healthy": healthy_checks,
                "unhealthy": unhealthy_checks,
                "success_rate": healthy_checks / total_checks if total_checks > 0 else 0
            }
        }
    
    def create_database_check(self, session_factory: Callable) -> HealthCheckConfig:
        """Create a database health check."""
        async def check_database():
            async with session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                if result.scalar():
                    return HealthCheckResult(
                        name="database",
                        status=HealthStatus.HEALTHY,
                        message="Database connection OK"
                    )
                else:
                    return HealthCheckResult(
                        name="database",
                        status=HealthStatus.UNHEALTHY,
                        message="Database query failed"
                    )
        
        return HealthCheckConfig(
            name="database",
            check_function=check_database,
            timeout_seconds=5,
            critical=True
        )
    
    def create_redis_check(self, redis_url: str) -> HealthCheckConfig:
        """Create a Redis health check."""
        async def check_redis():
            try:
                redis_client = aioredis.from_url(redis_url)
                await redis_client.ping()
                await redis_client.close()
                
                return HealthCheckResult(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis connection OK"
                )
            except Exception as e:
                return HealthCheckResult(
                    name="redis",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Redis connection failed: {str(e)}"
                )
        
        return HealthCheckConfig(
            name="redis",
            check_function=check_redis,
            timeout_seconds=3,
            critical=True
        )
    
    def create_external_service_check(
        self, 
        name: str, 
        url: str, 
        expected_status: int = 200
    ) -> HealthCheckConfig:
        """Create an external service health check."""
        async def check_external_service():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=5.0)
                    
                    if response.status_code == expected_status:
                        return HealthCheckResult(
                            name=name,
                            status=HealthStatus.HEALTHY,
                            message=f"Service responded with {response.status_code}",
                            details={"status_code": response.status_code}
                        )
                    else:
                        return HealthCheckResult(
                            name=name,
                            status=HealthStatus.UNHEALTHY,
                            message=f"Service responded with {response.status_code}, expected {expected_status}",
                            details={"status_code": response.status_code}
                        )
                        
            except httpx.TimeoutException:
                return HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message="Service timeout"
                )
            except Exception as e:
                return HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Service check failed: {str(e)}"
                )
        
        return HealthCheckConfig(
            name=name,
            check_function=check_external_service,
            timeout_seconds=10,
            critical=False
        )
    
    def create_disk_space_check(self, path: str = "/", threshold: int = 85) -> HealthCheckConfig:
        """Create a disk space health check."""
        async def check_disk_space():
            import shutil
            
            try:
                total, used, free = shutil.disk_usage(path)
                used_percent = (used / total) * 100
                
                if used_percent < threshold:
                    return HealthCheckResult(
                        name="disk_space",
                        status=HealthStatus.HEALTHY,
                        message=f"Disk usage: {used_percent:.1f}%",
                        details={
                            "path": path,
                            "used_percent": used_percent,
                            "free_gb": free / (1024**3)
                        }
                    )
                elif used_percent < 95:
                    return HealthCheckResult(
                        name="disk_space",
                        status=HealthStatus.DEGRADED,
                        message=f"Disk usage high: {used_percent:.1f}%",
                        details={
                            "path": path,
                            "used_percent": used_percent,
                            "free_gb": free / (1024**3)
                        }
                    )
                else:
                    return HealthCheckResult(
                        name="disk_space",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Disk usage critical: {used_percent:.1f}%",
                        details={
                            "path": path,
                            "used_percent": used_percent,
                            "free_gb": free / (1024**3)
                        }
                    )
                    
            except Exception as e:
                return HealthCheckResult(
                    name="disk_space",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Disk check failed: {str(e)}"
                )
        
        return HealthCheckConfig(
            name="disk_space",
            check_function=check_disk_space,
            timeout_seconds=5,
            critical=True
        )
    
    def create_memory_check(self, threshold: int = 85) -> HealthCheckConfig:
        """Create a memory usage health check."""
        async def check_memory():
            import psutil
            
            try:
                memory = psutil.virtual_memory()
                used_percent = memory.percent
                
                if used_percent < threshold:
                    return HealthCheckResult(
                        name="memory",
                        status=HealthStatus.HEALTHY,
                        message=f"Memory usage: {used_percent:.1f}%",
                        details={
                            "used_percent": used_percent,
                            "available_gb": memory.available / (1024**3)
                        }
                    )
                elif used_percent < 95:
                    return HealthCheckResult(
                        name="memory",
                        status=HealthStatus.DEGRADED,
                        message=f"Memory usage high: {used_percent:.1f}%",
                        details={
                            "used_percent": used_percent,
                            "available_gb": memory.available / (1024**3)
                        }
                    )
                else:
                    return HealthCheckResult(
                        name="memory",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Memory usage critical: {used_percent:.1f}%",
                        details={
                            "used_percent": used_percent,
                            "available_gb": memory.available / (1024**3)
                        }
                    )
                    
            except Exception as e:
                return HealthCheckResult(
                    name="memory",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Memory check failed: {str(e)}"
                )
        
        return HealthCheckConfig(
            name="memory",
            check_function=check_memory,
            timeout_seconds=5,
            critical=True
        )


# Factory function to create a configured health service
def create_health_service(
    database_session_factory: Callable = None,
    redis_url: str = None,
    external_services: Dict[str, str] = None
) -> HealthMonitoringService:
    """Create a health monitoring service with standard checks."""
    service = HealthMonitoringService()
    
    # Add database check
    if database_session_factory:
        db_check = service.create_database_check(database_session_factory)
        service.register_check(db_check)
    
    # Add Redis check
    if redis_url:
        redis_check = service.create_redis_check(redis_url)
        service.register_check(redis_check)
    
    # Add external service checks
    if external_services:
        for name, url in external_services.items():
            ext_check = service.create_external_service_check(name, url)
            service.register_check(ext_check)
    
    # Add system resource checks
    disk_check = service.create_disk_space_check()
    service.register_check(disk_check)
    
    memory_check = service.create_memory_check()
    service.register_check(memory_check)
    
    return service


# Export main classes
__all__ = [
    'HealthMonitoringService',
    'HealthCheckConfig',
    'HealthCheckResult', 
    'HealthStatus',
    'create_health_service'
]