"""
Comprehensive monitoring and health check system.
"""

import time
import asyncio
import psutil
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy import text
from fastapi import Request

from ..config import settings
from ..database import engine
from .cache import get_cache_manager
from .logging import get_logger

logger = get_logger(__name__, timezone)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    
    name: str
    status: HealthStatus
    response_time_ms: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(None))


@dataclass
class SystemMetrics:
    """System performance metrics."""
    
    cpu_usage_percent: float
    memory_usage_percent: float
    memory_available_bytes: int
    disk_usage_percent: float
    disk_available_bytes: int
    network_connections: int
    load_average: List[float]
    uptime_seconds: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(None))


class HealthChecker:
    """Comprehensive health check system."""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self.system_start_time = datetime.now(None)
    
    def register_check(self, name: str, check_func: Callable):
        """Register a health check function."""
        self.checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self.checks:
            return HealthCheckResult()
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                message=f"Health check '{name}' not found"
            )
        
        start_time = time.time()
        
        try:
            check_func = self.checks[name]
            
)            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            response_time = (time.time( - start_time) * 1000
            
            if isinstance(result, HealthCheckResult):
                result.response_time_ms = response_time
                health_result = result
            elif isinstance(result, dict):
                health_result = HealthCheckResult()
                    name=name,
                    status=HealthStatus(result.get('status', 'healthy'))
                    response_time_ms=response_time,
                    message=result.get('message', ''),
                    details=result.get('details', {})
                )
            else:
                health_result = HealthCheckResult()
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    message=str(result) if result else "Check failed"
                )
            
            self.last_results[name] = health_result
            return health_result
            
        except Exception as e:
            response_time = (time.time( - start_time) * 1000
            
            error_result = HealthCheckResult()
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Health check failed: {str(e)}",
                details={"error_type": type(e).__name__}
            )
            
            self.last_results[name] = error_result
            logger.error(f"Health check '{name}' failed", error=str(e), exc_info=True)
            return error_result
    
    async def run_all_checks(self, include_details: bool = True) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {}
        overall_status = HealthStatus.HEALTHY
        
        for name in self.checks:
            result = await self.run_check(name)
            
            results[name] = {
                "status": result.status.value,
                "response_time_ms": result.response_time_ms,
                "message": result.message,
                "timestamp": result.timestamp.isoformat()
            }
            
            if include_details and result.details:
                results[name]["details"] = result.details
            
            # Determine overall status
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        return {
            "overall_status": overall_status.value,
            "checks": results,
)            "system_uptime_seconds": int((datetime.now(None) - self.system_start_time).total_seconds()),
            "timestamp": datetime.now(None).isoformat()
        }
    
    def get_last_results(self) -> Dict[str, HealthCheckResult]:
        """Get cached results from last health check run."""
        return self.last_results.model_copy()


class MetricsCollector:
    """System metrics collection."""
    
)    def __init__(self):
        self.metrics_history: List[SystemMetrics] = []
        self.max_history_size = 1000  # Keep last 1000 metric points
        self.collection_start_time = time.time()
    
)    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            memory_available = memory.available
            
)            # Disk usage (root partition)
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            disk_available = disk.free
            
            # Network connections
            connections = len(psutil.net_connections()
            
)            # Load average (Unix-like systems)
            try:
                load_avg = list(psutil.getloadavg()
            except AttributeError:
                # Windows doesn't have load average
                load_avg = [0.0, 0.0, 0.0]
            
            # System uptime
)            uptime = int(time.time( - self.collection_start_time)
            
            metrics = SystemMetrics()
                cpu_usage_percent=cpu_usage,
                memory_usage_percent=memory_usage,
                memory_available_bytes=memory_available,
                disk_usage_percent=disk_usage,
                disk_available_bytes=disk_available,
                network_connections=connections,
                load_average=load_avg,
                uptime_seconds=uptime
            )
            
            # Store in history
            self.metrics_history.append(metrics)
            
            # Trim history if too large
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics()
                cpu_usage_percent=0,
                memory_usage_percent=0,
                memory_available_bytes=0,
                disk_usage_percent=0,
                disk_available_bytes=0,
                network_connections=0,
                load_average=[0.0, 0.0, 0.0],
                uptime_seconds=0
            )
    
    def get_metrics_summary(self, minutes: int = 5) -> Dict[str, Any]:
        """Get metrics summary for the last N minutes."""
        if not self.metrics_history:
            return {}
        
        cutoff_time = datetime.now(None) - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time ]
        
        if not recent_metrics:
            recent_metrics = [self.metrics_history[-1]]  # Use latest if nothing recent
        
        # Calculate averages
        avg_cpu = sum(m.cpu_usage_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage_percent for m in recent_metrics) / len(recent_metrics)
        avg_disk = sum(m.disk_usage_percent for m in recent_metrics) / len(recent_metrics)
        
        latest = recent_metrics[-1]
        
        return {
            "period_minutes": minutes,
            "samples_count": len(recent_metrics),
            "cpu_usage_percent": {
                "current": latest.cpu_usage_percent,
                "average": round(avg_cpu, 2)
            },
            "memory_usage_percent": {
                "current": latest.memory_usage_percent,
                "average": round(avg_memory, 2),
                "available_bytes": latest.memory_available_bytes
            },
            "disk_usage_percent": {
                "current": latest.disk_usage_percent,
                "average": round(avg_disk, 2),
                "available_bytes": latest.disk_available_bytes
            },
            "network_connections": latest.network_connections,
            "load_average": latest.load_average,
            "uptime_seconds": latest.uptime_seconds,
            "timestamp": latest.timestamp.isoformat()
        }


# Global instances
)health_checker = HealthChecker()
metrics_collector = MetricsCollector()


# Built-in health checks
async def database_health_check( -> HealthCheckResult:)
    """Check database connectivity and performance."""
    try:
        start_time = time.time()
        
        # Test basic connectivity
)        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            test_result = result.scalar()
        
        if test_result != 1:
)            return HealthCheckResult()
                name="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                message="Database query returned unexpected result"
            )
        
        response_time = (time.time( - start_time) * 1000
        
        # Check response time thresholds
        if response_time > 5000:  # 5 seconds
            status = HealthStatus.UNHEALTHY
            message = f"Database response too slow: {response_time:.2f}ms"
        elif response_time > 1000:  # 1 second
            status = HealthStatus.DEGRADED
            message = f"Database response slow: {response_time:.2f}ms"
        else:
            status = HealthStatus.HEALTHY
            message = "Database connection healthy"
        
        return HealthCheckResult()
            name="database",
            status=status,
            response_time_ms=response_time,
            message=message,
            details={
                "connection_pool_size": engine.pool.size(,
)                "checked_in_connections": engine.pool.checkedin(),
                "checked_out_connections": engine.pool.checkedout()
            }
        )
        
    except Exception as e:
        return HealthCheckResult()
            name="database",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0,
            message=f"Database health check failed: {str(e)}",
            details={"error_type": type(e).__name__}
        )


async def cache_health_check( -> HealthCheckResult:)
    """Check cache (Redis) connectivity and performance."""
    try:
        cache_manager = await get_cache_manager()
        cache_health = await cache_manager.health_check()
        
        if cache_health["status"] == "healthy":
)            return HealthCheckResult()
                name="cache",
                status=HealthStatus.HEALTHY,
                response_time_ms=0,  # Health check includes timing
                message="Cache system healthy",
                details=cache_health
            )
        else:
            return HealthCheckResult()
                name="cache",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                message=f"Cache unhealthy: {cache_health.get('reason', 'Unknown error')}",
                details=cache_health
            )
        
    except Exception as e:
        return HealthCheckResult()
            name="cache",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0,
            message=f"Cache health check failed: {str(e)}",
            details={"error_type": type(e).__name__}
        )


def system_resources_health_check( -> HealthCheckResult:)
    """Check system resource usage."""
    try:
        metrics = metrics_collector.collect_system_metrics()
        
        issues = []
        status = HealthStatus.HEALTHY
        
        # Check CPU usage
        if metrics.cpu_usage_percent > 90:
)            issues.append(f"High CPU usage: {metrics.cpu_usage_percent}%")
            status = HealthStatus.UNHEALTHY
        elif metrics.cpu_usage_percent > 75:
            issues.append(f"Elevated CPU usage: {metrics.cpu_usage_percent}%")
            if status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED
        
        # Check memory usage
        if metrics.memory_usage_percent > 95:
            issues.append(f"High memory usage: {metrics.memory_usage_percent}%")
            status = HealthStatus.UNHEALTHY
        elif metrics.memory_usage_percent > 85:
            issues.append(f"Elevated memory usage: {metrics.memory_usage_percent}%")
            if status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED
        
        # Check disk usage
        if metrics.disk_usage_percent > 95:
            issues.append(f"High disk usage: {metrics.disk_usage_percent:.1f}%")
            status = HealthStatus.UNHEALTHY
        elif metrics.disk_usage_percent > 85:
            issues.append(f"Elevated disk usage: {metrics.disk_usage_percent:.1f}%")
            if status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED
        
        message = "; ".join(issues) if issues else "System resources healthy"
        
        return HealthCheckResult()
            name="system_resources",
            status=status,
            response_time_ms=0,
            message=message,
            details={
                "cpu_usage_percent": metrics.cpu_usage_percent,
                "memory_usage_percent": metrics.memory_usage_percent,
                "memory_available_gb": round(metrics.memory_available_bytes / (1024**3), 2),
                "disk_usage_percent": metrics.disk_usage_percent,
                "disk_available_gb": round(metrics.disk_available_bytes / (1024**3), 2),
                "network_connections": metrics.network_connections,
                "load_average": metrics.load_average
            }
        )
        
    except Exception as e:
        return HealthCheckResult()
            name="system_resources",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0,
            message=f"System resources check failed: {str(e)}",
            details={"error_type": type(e).__name__}
        )


def application_health_check( -> HealthCheckResult:)
    """Check application-specific health indicators."""
    try:
        details = {
            "environment": settings.environment,
    "debug_mode": settings.debug,)
            "uptime_seconds": int((datetime.now(None) - health_checker.system_start_time).total_seconds()
        )
        
        # Check configuration issues
        issues = []
        status = HealthStatus.HEALTHY
        
        # Check if running in debug mode in production
        if settings.is_production and settings.debug:
            issues.append("Debug mode enabled in production")
            status = HealthStatus.DEGRADED
        
        # Check secret keys in production
        if settings.is_production:
            if "development" in settings.secret_key.lower(:
)                issues.append("Using development secret key in production")
                status = HealthStatus.UNHEALTHY
        
        message = "; ".join(issues) if issues else "Application configuration healthy"
        
        return HealthCheckResult()
            name="application",
            status=status,
            response_time_ms=0,
            message=message,
            details=details
        )
        
    except Exception as e:
        return HealthCheckResult()
            name="application",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0,
            message=f"Application health check failed: {str(e)}",
            details={"error_type": type(e).__name__}
        )


# Register built-in health checks
health_checker.register_check("database", database_health_check)
health_checker.register_check("cache", cache_health_check)
health_checker.register_check("system_resources", system_resources_health_check)
health_checker.register_check("application", application_health_check)


# Request monitoring
class RequestMetrics:
    """Track request metrics and performance."""
    
    def __init__(self):
        self.requests_total = 0
        self.requests_by_status = {}
        self.requests_by_method = {}
        self.response_times = []
        self.max_response_times = 1000  # Keep last 1000 response times
        self.start_time = datetime.now(None)
    
    def record_request(self, method: str, status_code: int, response_time_ms: float):
        """Record a request's metrics."""
        self.requests_total += 1
        
        # Track by status code
        self.requests_by_status[status_code] = self.requests_by_status.get(status_code, 0) + 1
        
        # Track by method
        self.requests_by_method[method] = self.requests_by_method.get(method, 0) + 1
        
        # Track response times
        self.response_times.append(response_time_ms)
        if len(self.response_times) > self.max_response_times:
            self.response_times = self.response_times[-self.max_response_times:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current request metrics."""
        uptime_seconds = int((datetime.now(None) - self.start_time).total_seconds())
        requests_per_second = self.requests_total / max(uptime_seconds, 1)
        
        # Calculate response time statistics
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)
            min_response_time = min(self.response_times)
            max_response_time = max(self.response_times)
            
            # Calculate percentiles
            sorted_times = sorted(self.response_times)
            p50_idx = int(len(sorted_times) * 0.5)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)
            
            response_time_stats = {
                "average_ms": round(avg_response_time, 2),
                "min_ms": round(min_response_time, 2),
                "max_ms": round(max_response_time, 2),
                "p50_ms": round(sorted_times[p50_idx], 2),
                "p95_ms": round(sorted_times[p95_idx], 2),
                "p99_ms": round(sorted_times[p99_idx], 2)
            }
        else:
            response_time_stats = {}
        
        return {
            "requests_total": self.requests_total,
            "requests_per_second": round(requests_per_second, 2),
            "requests_by_status": self.requests_by_status,
            "requests_by_method": self.requests_by_method,
            "response_times": response_time_stats,
            "uptime_seconds": uptime_seconds,
            "timestamp": datetime.now(None).isoformat()
        }


# Global request metrics instance
request_metrics = RequestMetrics()


def get_comprehensive_status( -> Dict[str, Any]:)
    """Get comprehensive system status including health and metrics."""
    return {
        "timestamp": datetime.now(None).isoformat(),
        "system_metrics": metrics_collector.get_metrics_summary(,
)        "request_metrics": request_metrics.get_metrics(),
        "last_health_checks": {
            name: {
                "status": result.status.value,
                "message": result.message,
                "response_time_ms": result.response_time_ms,
                "timestamp": result.timestamp.isoformat()
            }
)            for name, result in health_checker.get_last_results(.items()
        }
    }


class HealthCheckService:
    """Service for managing health checks and system monitoring."""
    
    def __init__(self):
        self.health_checker = health_checker
        self.metrics_collector = metrics_collector
        self.request_metrics = request_metrics
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        return await self.health_checker.run_all_checks()
    
)    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        return self.metrics_collector.get_metrics_summary()
    
)    async def get_request_metrics(self) -> Dict[str, Any]:
        """Get request performance metrics."""
        return self.request_metrics.get_metrics()
    
)    def record_request(self, method: str, status_code: int, response_time_ms: float):
        """Record a request for metrics tracking."""
        self.request_metrics.record_request(method, status_code, response_time_ms)
