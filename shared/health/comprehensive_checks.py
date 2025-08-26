"""
Comprehensive health check system for all platform components.

Provides standardized health checks with severity levels, dependencies,
and automated recovery suggestions.
"""

import asyncio
import logging
import os
import platform
import psutil
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
from pathlib import Path


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """Types of system components."""
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    EXTERNAL_SERVICE = "external_service"
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    SECURITY = "security"
    OBSERVABILITY = "observability"
    APPLICATION = "application"


@dataclass
class HealthMetric:
    """Represents a health metric with thresholds."""
    name: str
    value: float
    unit: str
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    higher_is_better: bool = True
    
    @property
    def status(self) -> HealthStatus:
        """Determine status based on thresholds."""
        if self.critical_threshold is not None:
            if self.higher_is_better:
                if self.value < self.critical_threshold:
                    return HealthStatus.UNHEALTHY
            else:
                if self.value > self.critical_threshold:
                    return HealthStatus.UNHEALTHY
        
        if self.warning_threshold is not None:
            if self.higher_is_better:
                if self.value < self.warning_threshold:
                    return HealthStatus.DEGRADED
            else:
                if self.value > self.warning_threshold:
                    return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    component_name: str
    component_type: ComponentType
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: List[HealthMetric] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None
    duration_ms: float = 0.0
    recovery_suggestions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "component_name": self.component_name,
            "component_type": self.component_type.value,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "status": m.status.value,
                    "warning_threshold": m.warning_threshold,
                    "critical_threshold": m.critical_threshold
                }
                for m in self.metrics
            ],
            "details": self.details,
            "error": str(self.error) if self.error else None,
            "recovery_suggestions": self.recovery_suggestions,
            "dependencies": self.dependencies
        }


class HealthCheck(ABC):
    """Abstract base class for health checks."""
    
    def __init__(
        self,
        name: str,
        component_type: ComponentType,
        timeout_seconds: float = 10.0,
        dependencies: List[str] = None
    ):
        self.name = name
        self.component_type = component_type
        self.timeout_seconds = timeout_seconds
        self.dependencies = dependencies or []
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """Perform the health check. Must be implemented by subclasses."""
        pass
    
    async def run_check(self) -> HealthCheckResult:
        """Run the health check with timeout and error handling."""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                self.check_health(),
                timeout=self.timeout_seconds
            )
            result.duration_ms = (time.time() - start_time) * 1000
            return result
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component_name=self.name,
                component_type=self.component_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout_seconds}s",
                duration_ms=duration_ms,
                recovery_suggestions=[
                    "Check if the component is responding",
                    "Investigate potential network issues",
                    "Consider increasing timeout threshold"
                ]
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component_name=self.name,
                component_type=self.component_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                error=e,
                duration_ms=duration_ms,
                details={"traceback": traceback.format_exc()},
                recovery_suggestions=[
                    "Check component configuration",
                    "Verify component is running",
                    "Review error logs for more details"
                ]
            )


class DatabaseHealthCheck(HealthCheck):
    """Health check for database connections."""
    
    def __init__(self, db_session_factory: Callable, **kwargs):
        super().__init__("Database", ComponentType.DATABASE, **kwargs)
        self.db_session_factory = db_session_factory
        
    async def check_health(self) -> HealthCheckResult:
        """Check database health."""
        try:
            async with self.db_session_factory() as session:
                # Simple query to test connection
                result = await session.execute(text("SELECT 1"))
                await session.commit()
                
                return HealthCheckResult(
                    component_name=self.name,
                    component_type=self.component_type,
                    status=HealthStatus.HEALTHY,
                    message="Database connection is healthy",
                    details={"query_result": result.scalar()}
                )
                
        except Exception as e:
            return HealthCheckResult(
                component_name=self.name,
                component_type=self.component_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                error=e,
                recovery_suggestions=[
                    "Check database server status",
                    "Verify connection string",
                    "Check network connectivity",
                    "Review database logs"
                ]
            )


class CacheHealthCheck(HealthCheck):
    """Health check for cache (Redis) connections."""
    
    def __init__(self, cache_client, **kwargs):
        super().__init__("Cache", ComponentType.CACHE, **kwargs)
        self.cache_client = cache_client
        
    async def check_health(self) -> HealthCheckResult:
        """Check cache health."""
        try:
            # Test cache with ping and set/get
            await self.cache_client.ping()
            
            test_key = f"health_check_{int(time.time())}"
            test_value = "health_check_value"
            
            await self.cache_client.set(test_key, test_value, ex=10)  # 10 second expiry
            retrieved_value = await self.cache_client.get(test_key)
            await self.cache_client.delete(test_key)
            
            if retrieved_value != test_value:
                raise ValueError("Cache set/get test failed")
            
            # Get cache info for metrics
            info = await self.cache_client.info()
            connected_clients = info.get("connected_clients", 0)
            used_memory = info.get("used_memory", 0)
            used_memory_mb = used_memory / (1024 * 1024)
            
            metrics = [
                HealthMetric("connected_clients", connected_clients, "count"),
                HealthMetric("used_memory_mb", used_memory_mb, "MB", critical_threshold=1000, higher_is_better=False)
            ]
            
            return HealthCheckResult(
                component_name=self.name,
                component_type=self.component_type,
                status=HealthStatus.HEALTHY,
                message="Cache connection is healthy",
                metrics=metrics,
                details={
                    "redis_version": info.get("redis_version", "unknown"),
                    "uptime_in_seconds": info.get("uptime_in_seconds", 0)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name=self.name,
                component_type=self.component_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Cache connection failed: {str(e)}",
                error=e,
                recovery_suggestions=[
                    "Check Redis server status",
                    "Verify Redis configuration",
                    "Check network connectivity",
                    "Review Redis logs"
                ]
            )


class SystemResourcesHealthCheck(HealthCheck):
    """Health check for system resources (CPU, memory, disk)."""
    
    def __init__(self, **kwargs):
        super().__init__("System Resources", ComponentType.APPLICATION, **kwargs)
        
    async def check_health(self) -> HealthCheckResult:
        """Check system resource health."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024 ** 3)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 ** 3)
            
            # Process info
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024 * 1024)
            process_cpu_percent = process.cpu_percent()
            
            metrics = [
                HealthMetric("cpu_percent", cpu_percent, "%", warning_threshold=80, critical_threshold=95, higher_is_better=False),
                HealthMetric("memory_percent", memory_percent, "%", warning_threshold=80, critical_threshold=90, higher_is_better=False),
                HealthMetric("memory_available_gb", memory_available_gb, "GB", warning_threshold=1.0, critical_threshold=0.5),
                HealthMetric("disk_percent", disk_percent, "%", warning_threshold=80, critical_threshold=90, higher_is_better=False),
                HealthMetric("disk_free_gb", disk_free_gb, "GB", warning_threshold=5.0, critical_threshold=1.0),
                HealthMetric("process_memory_mb", process_memory_mb, "MB", critical_threshold=2048, higher_is_better=False),
                HealthMetric("process_cpu_percent", process_cpu_percent, "%", warning_threshold=50, critical_threshold=80, higher_is_better=False)
            ]
            
            # Determine overall status based on metrics
            statuses = [metric.status for metric in metrics]
            if HealthStatus.UNHEALTHY in statuses:
                overall_status = HealthStatus.UNHEALTHY
                message = "System resources are unhealthy"
            elif HealthStatus.DEGRADED in statuses:
                overall_status = HealthStatus.DEGRADED
                message = "System resources are degraded"
            else:
                overall_status = HealthStatus.HEALTHY
                message = "System resources are healthy"
            
            return HealthCheckResult(
                component_name=self.name,
                component_type=self.component_type,
                status=overall_status,
                message=message,
                metrics=metrics,
                details={
                    "platform": platform.platform(),
                    "python_version": platform.python_version(),
                    "cpu_count": psutil.cpu_count(),
                    "total_memory_gb": memory.total / (1024 ** 3),
                    "total_disk_gb": disk.total / (1024 ** 3)
                },
                recovery_suggestions=[
                    "Monitor resource usage trends",
                    "Consider scaling up if consistently high",
                    "Check for memory leaks if process memory is high",
                    "Review logs for high resource usage patterns"
                ] if overall_status != HealthStatus.HEALTHY else []
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name=self.name,
                component_type=self.component_type,
                status=HealthStatus.UNHEALTHY,
                message=f"System resources check failed: {str(e)}",
                error=e,
                recovery_suggestions=[
                    "Check system monitoring tools",
                    "Verify psutil library installation"
                ]
            )


class FilesystemHealthCheck(HealthCheck):
    """Health check for filesystem access and permissions."""
    
    def __init__(self, paths_to_check: List[str] = None, **kwargs):
        super().__init__("Filesystem", ComponentType.FILESYSTEM, **kwargs)
        self.paths_to_check = paths_to_check or ["/tmp", ".", "logs"]
        
    async def check_health(self) -> HealthCheckResult:
        """Check filesystem health."""
        try:
            issues = []
            details = {}
            
            for path_str in self.paths_to_check:
                path = Path(path_str)
                path_details = {}
                
                # Check if path exists
                if not path.exists():
                    issues.append(f"Path {path} does not exist")
                    continue
                    
                # Check read access
                if not os.access(path, os.R_OK):
                    issues.append(f"No read access to {path}")
                    
                # Check write access
                if not os.access(path, os.W_OK):
                    issues.append(f"No write access to {path}")
                    
                # Test actual write operation
                if path.is_dir():
                    test_file = path / f"health_check_{int(time.time())}"
                    try:
                        test_file.write_text("health check")
                        test_file.unlink()  # Clean up
                        path_details["write_test"] = "success"
                    except Exception as e:
                        issues.append(f"Write test failed for {path}: {e}")
                        path_details["write_test"] = f"failed: {e}"
                
                # Get path stats
                if path.exists():
                    stat = path.stat()
                    path_details.update({
                        "size_bytes": stat.st_size if path.is_file() else "N/A",
                        "permissions": oct(stat.st_mode)[-3:],
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                
                details[str(path)] = path_details
            
            status = HealthStatus.UNHEALTHY if issues else HealthStatus.HEALTHY
            message = f"Filesystem issues: {'; '.join(issues)}" if issues else "Filesystem access is healthy"
            
            return HealthCheckResult(
                component_name=self.name,
                component_type=self.component_type,
                status=status,
                message=message,
                details=details,
                recovery_suggestions=[
                    "Check file permissions",
                    "Verify disk space availability",
                    "Check directory ownership"
                ] if issues else []
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name=self.name,
                component_type=self.component_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Filesystem check failed: {str(e)}",
                error=e,
                recovery_suggestions=[
                    "Check filesystem mounting",
                    "Verify path configurations"
                ]
            )


class HealthChecker:
    """Comprehensive health checker that manages multiple health checks."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.health_checks: Dict[str, HealthCheck] = {}
        self.last_check_results: Dict[str, HealthCheckResult] = {}
        self.check_history: List[Dict[str, HealthCheckResult]] = []
        self.max_history_size = 100
        
    def register_check(self, health_check: HealthCheck) -> None:
        """Register a health check."""
        self.health_checks[health_check.name] = health_check
        logger.info(f"Registered health check: {health_check.name}")
        
    def unregister_check(self, check_name: str) -> None:
        """Unregister a health check."""
        if check_name in self.health_checks:
            del self.health_checks[check_name]
            logger.info(f"Unregistered health check: {check_name}")
            
    async def run_check(self, check_name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if check_name not in self.health_checks:
            return HealthCheckResult(
                component_name=check_name,
                component_type=ComponentType.APPLICATION,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{check_name}' not found"
            )
        
        health_check = self.health_checks[check_name]
        result = await health_check.run_check()
        self.last_check_results[check_name] = result
        
        return result
    
    async def run_all_checks(self, parallel: bool = True) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        if not self.health_checks:
            return {}
        
        if parallel:
            tasks = {
                name: self.run_check(name)
                for name in self.health_checks.keys()
            }
            
            results = {}
            for name, task in tasks.items():
                try:
                    results[name] = await task
                except Exception as e:
                    logger.error(f"Health check {name} failed with exception: {e}")
                    results[name] = HealthCheckResult(
                        component_name=name,
                        component_type=ComponentType.APPLICATION,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Health check exception: {str(e)}",
                        error=e
                    )
        else:
            results = {}
            for name in self.health_checks.keys():
                results[name] = await self.run_check(name)
        
        # Store in history
        self.check_history.append(results.model_copy())
        if len(self.check_history) > self.max_history_size:
            self.check_history.pop(0)
            
        return results
    
    def get_overall_status(self, results: Dict[str, HealthCheckResult] = None) -> Dict[str, Any]:
        """Get overall system health status."""
        if results is None:
            results = self.last_check_results
        
        if not results:
            return {
                "overall_status": HealthStatus.UNKNOWN.value,
                "message": "No health checks available"
            }
        
        statuses = [result.status for result in results.values()]
        
        # Determine overall status
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
            unhealthy_components = [
                name for name, result in results.items()
                if result.status == HealthStatus.UNHEALTHY
            ]
            message = f"System unhealthy: {', '.join(unhealthy_components)}"
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
            degraded_components = [
                name for name, result in results.items()
                if result.status == HealthStatus.DEGRADED
            ]
            message = f"System degraded: {', '.join(degraded_components)}"
        elif HealthStatus.UNKNOWN in statuses:
            overall_status = HealthStatus.UNKNOWN
            unknown_components = [
                name for name, result in results.items()
                if result.status == HealthStatus.UNKNOWN
            ]
            message = f"System status unknown: {', '.join(unknown_components)}"
        else:
            overall_status = HealthStatus.HEALTHY
            message = "All system components are healthy"
        
        return {
            "service_name": self.service_name,
            "overall_status": overall_status.value,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_checks": len(results),
            "healthy_count": sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY),
            "degraded_count": sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED),
            "unhealthy_count": sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY),
            "unknown_count": sum(1 for r in results.values() if r.status == HealthStatus.UNKNOWN),
            "checks": {name: result.to_dict() for name, result in results.items()}
        }
    
    def get_health_trends(self, check_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get health trends for a specific check over time."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        relevant_results = []
        for check_batch in self.check_history:
            if check_name in check_batch:
                result = check_batch[check_name]
                if result.timestamp >= cutoff_time:
                    relevant_results.append(result)
        
        if not relevant_results:
            return {"error": f"No data found for {check_name} in the last {hours} hours"}
        
        status_counts = {}
        for result in relevant_results:
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "check_name": check_name,
            "time_period_hours": hours,
            "total_checks": len(relevant_results),
            "status_distribution": status_counts,
            "latest_status": relevant_results[-1].status.value,
            "latest_message": relevant_results[-1].message
        }


# Factory functions for common health checks

def create_standard_health_checks(
    db_session_factory: Callable = None,
    cache_client = None,
    additional_filesystem_paths: List[str] = None
) -> List[HealthCheck]:
    """Create standard health checks for most applications."""
    checks = []
    
    # Always include system resources
    checks.append(SystemResourcesHealthCheck())
    
    # Always include filesystem check
    filesystem_paths = [".", "logs", "/tmp"]
    if additional_filesystem_paths:
        filesystem_paths.extend(additional_filesystem_paths)
    checks.append(FilesystemHealthCheck(filesystem_paths))
    
    # Add database check if factory provided
    if db_session_factory:
        checks.append(DatabaseHealthCheck(db_session_factory))
    
    # Add cache check if client provided
    if cache_client:
        checks.append(CacheHealthCheck(cache_client))
    
    return checks


def setup_health_checker(
    service_name: str,
    db_session_factory: Callable = None,
    cache_client = None,
    additional_checks: List[HealthCheck] = None,
    additional_filesystem_paths: List[str] = None
) -> HealthChecker:
    """Set up a complete health checker with standard checks."""
    health_checker = HealthChecker(service_name)
    
    # Register standard checks
    standard_checks = create_standard_health_checks(
        db_session_factory=db_session_factory,
        cache_client=cache_client,
        additional_filesystem_paths=additional_filesystem_paths
    )
    
    for check in standard_checks:
        health_checker.register_check(check)
    
    # Register additional checks
    if additional_checks:
        for check in additional_checks:
            health_checker.register_check(check)
    
    return health_checker