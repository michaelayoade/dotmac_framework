"""
Strategic Service Dependency Health Monitoring

Comprehensive health checks for all service dependencies to prevent
startup failures and runtime issues like we experienced.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthResult:
    """Health check result with detailed information."""
    service: str
    status: HealthStatus
    message: str
    response_time_ms: float
    details: Dict[str, Any]
    timestamp: float


class DependencyHealthMonitor:
    """
    Strategic health monitoring for all service dependencies.
    
    Prevents issues like:
    - PostgreSQL connection failures
    - Redis connectivity problems  
    - WebSocket manager startup failures
    - Celery broker connection issues
    """

    def __init__(self):
        """  Init   operation."""
        self.health_cache: Dict[str, HealthResult] = {}
        self.cache_ttl_seconds = 30
        
    async def check_all_dependencies(self) -> Dict[str, HealthResult]:
        """Check health of all critical service dependencies."""
        health_checks = [
            self.check_database_health(),
            self.check_redis_health(), 
            self.check_celery_broker_health(),
            self.check_file_storage_health(),
            self.check_secrets_management_health(),
        ]
        
        results = await asyncio.gather(*health_checks, return_exceptions=True)
        
        health_status = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed with exception: {result}")
                continue
            elif isinstance(result, HealthResult):
                health_status[result.service] = result
                
        return health_status

    async def check_database_health(self) -> HealthResult:
        """Strategic database health check with connection validation."""
        start_time = time.time()
        
        try:
            from dotmac_isp.core.database import get_db
            from dotmac_isp.core.settings import get_settings
            
            settings = get_settings()
            
            # Test database connection
            async for db in get_db():
                try:
                    # Test basic connectivity
                    await db.execute("SELECT 1")
                    
                    # Test database existence and permissions
                    result = await db.execute("SELECT current_database(), current_user")
                    row = result.fetchone()
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    return HealthResult(
                        service="database",
                        status=HealthStatus.HEALTHY,
                        message="Database connection successful",
                        response_time_ms=response_time,
                        details={
                            "database": row[0] if row else "unknown",
                            "user": row[1] if row else "unknown",
                            "url_host": settings.database_url.split("@")[1].split("/")[0] if "@" in settings.database_url else "unknown"
                        },
                        timestamp=time.time()
                    )
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    return HealthResult(
                        service="database", 
                        status=HealthStatus.UNHEALTHY,
                        message=f"Database query failed: {str(e)[:100]}",
                        response_time_ms=response_time,
                        details={"error": str(e)},
                        timestamp=time.time()
                    )
                finally:
                    break
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthResult(
                service="database",
                status=HealthStatus.UNHEALTHY, 
                message=f"Database connection failed: {str(e)[:100]}",
                response_time_ms=response_time,
                details={"error": str(e)},
                timestamp=time.time()
            )

    async def check_redis_health(self) -> HealthResult:
        """Strategic Redis health check preventing WebSocket manager failures."""
        start_time = time.time()
        
        try:
            import redis.asyncio as redis
            from dotmac_isp.core.settings import get_settings
            
            settings = get_settings()
            
            # Use strategic Redis URL (prevents localhost:6379 issues)
            redis_client = redis.from_url(settings.redis_url)
            
            # Test basic connectivity
            pong = await redis_client.ping()
            
            # Test read/write operations
            test_key = "health_check_test"
            await redis_client.set(test_key, "ok", ex=10)
            test_value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            # Check if read/write worked
            if test_value != b"ok":
                return HealthResult(
                    service="redis",
                    status=HealthStatus.DEGRADED,
                    message="Redis read/write test failed",
                    response_time_ms=response_time,
                    details={"ping": str(pong), "read_write": "failed"},
                    timestamp=time.time()
                )
            
            return HealthResult(
                service="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection and operations successful", 
                response_time_ms=response_time,
                details={"ping": str(pong), "read_write": "ok"},
                timestamp=time.time()
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthResult(
                service="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)[:100]}",
                response_time_ms=response_time, 
                details={"error": str(e)},
                timestamp=time.time()
            )

    async def check_celery_broker_health(self) -> HealthResult:
        """Check Celery broker connectivity.""" 
        start_time = time.time()
        
        try:
            from dotmac_isp.core.celery_app import celery_app
            from dotmac_isp.core.settings import get_settings
            
            settings = get_settings()
            
            # Try to get broker connection info
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            
            response_time = (time.time() - start_time) * 1000
            
            if stats:
                return HealthResult(
                    service="celery_broker",
                    status=HealthStatus.HEALTHY,
                    message="Celery broker connection successful",
                    response_time_ms=response_time,
                    details={"workers": len(stats) if stats else 0},
                    timestamp=time.time()
                )
            else:
                return HealthResult(
                    service="celery_broker", 
                    status=HealthStatus.DEGRADED,
                    message="Celery broker connected but no workers available",
                    response_time_ms=response_time,
                    details={"workers": 0},
                    timestamp=time.time()
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthResult(
                service="celery_broker",
                status=HealthStatus.UNHEALTHY,
                message=f"Celery broker connection failed: {str(e)[:100]}", 
                response_time_ms=response_time,
                details={"error": str(e)},
                timestamp=time.time()
            )

    async def check_file_storage_health(self) -> HealthResult:
        """Check file storage (MinIO) connectivity."""
        start_time = time.time()
        
        try:
            import httpx
            
            # Check MinIO health endpoint
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://minio:9000/minio/health/live")
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return HealthResult(
                        service="file_storage",
                        status=HealthStatus.HEALTHY,
                        message="MinIO storage accessible",
                        response_time_ms=response_time,
                        details={"status_code": response.status_code},
                        timestamp=time.time()
                    )
                else:
                    return HealthResult(
                        service="file_storage",
                        status=HealthStatus.DEGRADED, 
                        message=f"MinIO returned status {response.status_code}",
                        response_time_ms=response_time,
                        details={"status_code": response.status_code},
                        timestamp=time.time()
                    )
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthResult(
                service="file_storage",
                status=HealthStatus.UNHEALTHY,
                message=f"File storage check failed: {str(e)[:100]}",
                response_time_ms=response_time,
                details={"error": str(e)},
                timestamp=time.time()
            )

    async def check_secrets_management_health(self) -> HealthResult:
        """Check secrets management (OpenBao/Vault) connectivity."""
        start_time = time.time()
        
        try:
            from dotmac_isp.core.secret_manager import get_secret_manager
            
            secret_manager = get_secret_manager()
            
            # Test secret retrieval
            test_secret = secret_manager.get_secret("health_check", "test_value")
            
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus.HEALTHY if secret_manager.vault_client else HealthStatus.DEGRADED
            message = ("Vault connection successful" if secret_manager.vault_client 
                      else "Using environment variables (Vault not available)")
            
            return HealthResult(
                service="secrets_management",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    "vault_enabled": secret_manager.use_vault,
                    "vault_connected": secret_manager.vault_client is not None,
                    "environment": secret_manager.environment
                },
                timestamp=time.time()
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthResult(
                service="secrets_management",
                status=HealthStatus.UNHEALTHY,
                message=f"Secrets management check failed: {str(e)[:100]}",
                response_time_ms=response_time,
                details={"error": str(e)},
                timestamp=time.time()
            )

    def get_overall_health_status(self, health_results: Dict[str, HealthResult]) -> HealthStatus:
        """Determine overall system health status."""
        if not health_results:
            return HealthStatus.UNKNOWN
            
        statuses = [result.status for result in health_results.values()]
        
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    async def wait_for_dependencies(self, timeout_seconds: int = 60) -> bool:
        """
        Strategic dependency waiting to prevent startup failures.
        
        Waits for all critical dependencies to be healthy before allowing
        application startup to proceed.
        """
        logger.info("🔍 Waiting for service dependencies to be ready...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            health_results = await self.check_all_dependencies()
            overall_status = self.get_overall_health_status(health_results)
            
            # Log current status
            for service, result in health_results.items():
                status_emoji = {
                    HealthStatus.HEALTHY: "✅",
                    HealthStatus.DEGRADED: "⚠️", 
                    HealthStatus.UNHEALTHY: "❌",
                    HealthStatus.UNKNOWN: "❓"
                }.get(result.status, "❓")
                
                logger.info(f"{status_emoji} {service}: {result.message} ({result.response_time_ms:.1f}ms)")
            
            if overall_status == HealthStatus.HEALTHY:
                logger.info("✅ All dependencies are healthy - starting application")
                return True
            elif overall_status == HealthStatus.DEGRADED:
                logger.warning("⚠️ Some dependencies degraded but continuing startup")
                return True
                
            logger.info(f"⏳ Waiting for dependencies... ({int(time.time() - start_time)}s elapsed)")
            await asyncio.sleep(5)
        
        logger.error(f"❌ Dependency health check timeout after {timeout_seconds}s")
        return False


# Global instance
_health_monitor = None


def get_dependency_health_monitor() -> DependencyHealthMonitor:
    """Get global dependency health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = DependencyHealthMonitor()
    return _health_monitor