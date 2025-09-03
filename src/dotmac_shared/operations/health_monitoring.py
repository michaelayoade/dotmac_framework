"""
Network Health Monitoring Automation

Comprehensive network and service health monitoring with automated remediation.
Uses DRY patterns and standard exception handling.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.container_monitoring.core.health_monitor import (
    ContainerHealthMonitor,
    HealthReport,
    HealthStatus,
)
from dotmac_shared.core.exceptions import ExternalServiceError, ServiceError
from dotmac_shared.monitoring.config import MonitoringConfig

logger = logging.getLogger(__name__)


class NetworkHealthStatus(str, Enum):
    """Network health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class NetworkEndpoint:
    """Network endpoint configuration"""

    id: UUID
    name: str
    host: str
    port: int
    service_type: str
    tenant_id: Optional[UUID] = None
    check_interval: int = 30
    timeout: int = 5
    retry_count: int = 3
    expected_response_time: float = 1.0


@dataclass
class HealthCheckResult:
    """Health check result"""

    endpoint_id: UUID
    status: NetworkHealthStatus
    response_time: float
    message: str
    timestamp: datetime
    details: Dict[str, Any]


class NetworkHealthMonitor:
    """
    Comprehensive network health monitoring automation.
    
    Monitors network endpoints, services, and infrastructure health
    with automated alerting and remediation capabilities.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        monitoring_config: Optional[MonitoringConfig] = None,
    ):
        self.db = db_session
        self.monitoring_config = monitoring_config or MonitoringConfig(
            service_name="network_health_monitor"
        )
        self.container_monitor = ContainerHealthMonitor()
        self.active_endpoints: Dict[UUID, NetworkEndpoint] = {}
        self.health_history: Dict[UUID, List[HealthCheckResult]] = {}

    @standard_exception_handler
    async def register_endpoint(self, endpoint: NetworkEndpoint) -> None:
        """Register network endpoint for monitoring."""
        self.active_endpoints[endpoint.id] = endpoint
        logger.info(f"Registered endpoint for monitoring: {endpoint.name}")

    @standard_exception_handler
    async def unregister_endpoint(self, endpoint_id: UUID) -> None:
        """Unregister network endpoint from monitoring."""
        if endpoint_id in self.active_endpoints:
            endpoint_name = self.active_endpoints[endpoint_id].name
            del self.active_endpoints[endpoint_id]
            if endpoint_id in self.health_history:
                del self.health_history[endpoint_id]
            logger.info(f"Unregistered endpoint: {endpoint_name}")

    @standard_exception_handler
    async def check_endpoint_health(self, endpoint: NetworkEndpoint) -> HealthCheckResult:
        """Perform health check on a single endpoint."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Import here to avoid circular imports
            import asyncio
            import socket

            # Create socket connection with timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(endpoint.timeout)
            
            try:
                result = sock.connect_ex((endpoint.host, endpoint.port))
                response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                if result == 0:
                    if response_time <= endpoint.expected_response_time:
                        status = NetworkHealthStatus.HEALTHY
                        message = f"Endpoint {endpoint.name} is healthy"
                    else:
                        status = NetworkHealthStatus.DEGRADED
                        message = f"Endpoint {endpoint.name} responding slowly ({response_time:.2f}s)"
                else:
                    status = NetworkHealthStatus.CRITICAL
                    message = f"Endpoint {endpoint.name} connection failed (code: {result})"
                    
            finally:
                sock.close()
                
        except socket.timeout:
            response_time = endpoint.timeout
            status = NetworkHealthStatus.CRITICAL
            message = f"Endpoint {endpoint.name} connection timed out"
            
        except Exception as e:
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            status = NetworkHealthStatus.OFFLINE
            message = f"Endpoint {endpoint.name} check failed: {str(e)}"

        return HealthCheckResult(
            endpoint_id=endpoint.id,
            status=status,
            response_time=response_time,
            message=message,
            timestamp=start_time,
            details={
                "host": endpoint.host,
                "port": endpoint.port,
                "service_type": endpoint.service_type,
                "expected_response_time": endpoint.expected_response_time,
            }
        )

    @standard_exception_handler
    async def check_all_endpoints(self) -> List[HealthCheckResult]:
        """Check health of all registered endpoints."""
        if not self.active_endpoints:
            logger.warning("No endpoints registered for monitoring")
            return []

        # Run all health checks concurrently
        tasks = [
            self.check_endpoint_health(endpoint)
            for endpoint in self.active_endpoints.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
            else:
                valid_results.append(result)
                
        # Store results in history
        for result in valid_results:
            if result.endpoint_id not in self.health_history:
                self.health_history[result.endpoint_id] = []
            
            # Keep only last 100 results per endpoint
            self.health_history[result.endpoint_id].append(result)
            if len(self.health_history[result.endpoint_id]) > 100:
                self.health_history[result.endpoint_id].pop(0)

        return valid_results

    @standard_exception_handler
    async def get_network_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive network health summary."""
        results = await self.check_all_endpoints()
        
        if not results:
            return {
                "overall_status": NetworkHealthStatus.OFFLINE,
                "total_endpoints": 0,
                "healthy_count": 0,
                "degraded_count": 0,
                "critical_count": 0,
                "offline_count": 0,
                "average_response_time": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Calculate statistics
        status_counts = {
            NetworkHealthStatus.HEALTHY: 0,
            NetworkHealthStatus.DEGRADED: 0,
            NetworkHealthStatus.CRITICAL: 0,
            NetworkHealthStatus.OFFLINE: 0,
        }
        
        total_response_time = 0
        for result in results:
            status_counts[result.status] += 1
            total_response_time += result.response_time

        # Determine overall status
        if status_counts[NetworkHealthStatus.OFFLINE] > 0:
            overall_status = NetworkHealthStatus.OFFLINE
        elif status_counts[NetworkHealthStatus.CRITICAL] > 0:
            overall_status = NetworkHealthStatus.CRITICAL
        elif status_counts[NetworkHealthStatus.DEGRADED] > 0:
            overall_status = NetworkHealthStatus.DEGRADED
        else:
            overall_status = NetworkHealthStatus.HEALTHY

        return {
            "overall_status": overall_status,
            "total_endpoints": len(results),
            "healthy_count": status_counts[NetworkHealthStatus.HEALTHY],
            "degraded_count": status_counts[NetworkHealthStatus.DEGRADED],
            "critical_count": status_counts[NetworkHealthStatus.CRITICAL],
            "offline_count": status_counts[NetworkHealthStatus.OFFLINE],
            "average_response_time": total_response_time / len(results) if results else 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": [
                {
                    "endpoint_id": str(result.endpoint_id),
                    "endpoint_name": self.active_endpoints.get(result.endpoint_id, {}).name,
                    "status": result.status,
                    "response_time": result.response_time,
                    "message": result.message,
                }
                for result in results
            ],
        }

    @standard_exception_handler
    async def get_endpoint_trends(
        self, endpoint_id: UUID, hours: int = 24
    ) -> Dict[str, Any]:
        """Get health trends for a specific endpoint."""
        if endpoint_id not in self.health_history:
            raise ServiceError(f"No health history found for endpoint {endpoint_id}")

        # Filter results from last N hours
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_results = [
            result for result in self.health_history[endpoint_id]
            if result.timestamp >= cutoff_time
        ]

        if not recent_results:
            return {
                "endpoint_id": str(endpoint_id),
                "period_hours": hours,
                "total_checks": 0,
                "availability_percentage": 0.0,
                "average_response_time": 0.0,
                "status_distribution": {},
            }

        # Calculate trends
        healthy_count = sum(
            1 for r in recent_results 
            if r.status == NetworkHealthStatus.HEALTHY
        )
        
        total_response_time = sum(r.response_time for r in recent_results)
        
        status_distribution = {}
        for status in NetworkHealthStatus:
            count = sum(1 for r in recent_results if r.status == status)
            status_distribution[status] = {
                "count": count,
                "percentage": (count / len(recent_results)) * 100
            }

        return {
            "endpoint_id": str(endpoint_id),
            "endpoint_name": self.active_endpoints.get(endpoint_id, {}).name,
            "period_hours": hours,
            "total_checks": len(recent_results),
            "availability_percentage": (healthy_count / len(recent_results)) * 100,
            "average_response_time": total_response_time / len(recent_results),
            "status_distribution": status_distribution,
            "recent_issues": [
                {
                    "timestamp": result.timestamp.isoformat(),
                    "status": result.status,
                    "message": result.message,
                    "response_time": result.response_time,
                }
                for result in recent_results[-10:]  # Last 10 results
                if result.status != NetworkHealthStatus.HEALTHY
            ],
        }

    @standard_exception_handler
    async def start_continuous_monitoring(self, check_interval: int = 30) -> None:
        """Start continuous monitoring of all endpoints."""
        logger.info(f"Starting continuous network monitoring (interval: {check_interval}s)")
        
        while True:
            try:
                results = await self.check_all_endpoints()
                
                # Log summary
                critical_count = sum(
                    1 for r in results 
                    if r.status in [NetworkHealthStatus.CRITICAL, NetworkHealthStatus.OFFLINE]
                )
                
                if critical_count > 0:
                    logger.warning(f"Network health check: {critical_count} endpoints in critical state")
                else:
                    logger.info(f"Network health check completed: {len(results)} endpoints checked")
                
                # Wait for next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(check_interval)


class ServiceHealthChecker:
    """
    Service-specific health checking with deep integration monitoring.
    
    Extends basic network monitoring with application-specific health checks.
    """

    def __init__(self, monitoring_config: Optional[MonitoringConfig] = None):
        self.monitoring_config = monitoring_config or MonitoringConfig(
            service_name="service_health_checker"
        )
        self.container_monitor = ContainerHealthMonitor()

    @standard_exception_handler
    async def check_database_health(
        self, connection_string: str, timeout: int = 5
    ) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Import database client
            from sqlalchemy import create_engine, text
            from sqlalchemy.exc import SQLAlchemyError
            
            # Create engine with timeout
            engine = create_engine(
                connection_string,
                pool_timeout=timeout,
                pool_recycle=3600,
            )
            
            # Test connection and basic query
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                return {
                    "status": NetworkHealthStatus.HEALTHY,
                    "response_time": response_time,
                    "message": "Database connection healthy",
                    "details": {
                        "connection_successful": True,
                        "query_successful": True,
                        "timestamp": start_time.isoformat(),
                    }
                }
                
        except SQLAlchemyError as e:
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            return {
                "status": NetworkHealthStatus.CRITICAL,
                "response_time": response_time,
                "message": f"Database connection failed: {str(e)}",
                "details": {
                    "connection_successful": False,
                    "error": str(e),
                    "timestamp": start_time.isoformat(),
                }
            }
        except Exception as e:
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            return {
                "status": NetworkHealthStatus.OFFLINE,
                "response_time": response_time,
                "message": f"Database health check failed: {str(e)}",
                "details": {
                    "error": str(e),
                    "timestamp": start_time.isoformat(),
                }
            }

    @standard_exception_handler
    async def check_redis_health(
        self, redis_url: str, timeout: int = 5
    ) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        start_time = datetime.now(timezone.utc)
        
        try:
            import redis.asyncio as redis
            
            # Create Redis client
            client = redis.from_url(redis_url, socket_timeout=timeout)
            
            # Test ping
            await client.ping()
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Get basic info
            info = await client.info()
            
            await client.close()
            
            return {
                "status": NetworkHealthStatus.HEALTHY,
                "response_time": response_time,
                "message": "Redis connection healthy",
                "details": {
                    "ping_successful": True,
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "Unknown"),
                    "timestamp": start_time.isoformat(),
                }
            }
            
        except Exception as e:
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            return {
                "status": NetworkHealthStatus.CRITICAL,
                "response_time": response_time,
                "message": f"Redis health check failed: {str(e)}",
                "details": {
                    "error": str(e),
                    "timestamp": start_time.isoformat(),
                }
            }

    @standard_exception_handler
    async def check_container_health(self, container_id: str) -> Dict[str, Any]:
        """Check container health using existing container monitor."""
        try:
            health_report = await self.container_monitor.monitor_container_health(container_id)
            
            # Convert to standardized format
            status_mapping = {
                HealthStatus.HEALTHY: NetworkHealthStatus.HEALTHY,
                HealthStatus.DEGRADED: NetworkHealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY: NetworkHealthStatus.CRITICAL,
                HealthStatus.CRITICAL: NetworkHealthStatus.OFFLINE,
            }
            
            return {
                "status": status_mapping.get(health_report.overall_status, NetworkHealthStatus.OFFLINE),
                "message": f"Container {container_id} health: {health_report.overall_status}",
                "details": {
                    "container_id": container_id,
                    "uptime": str(health_report.uptime) if health_report.uptime else None,
                    "check_count": len(health_report.checks),
                    "timestamp": health_report.timestamp.isoformat(),
                    "checks": [
                        {
                            "name": check.name,
                            "status": check.status,
                            "message": check.message,
                            "response_time": check.response_time,
                        }
                        for check in health_report.checks
                    ]
                }
            }
            
        except Exception as e:
            return {
                "status": NetworkHealthStatus.OFFLINE,
                "message": f"Container health check failed: {str(e)}",
                "details": {
                    "container_id": container_id,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            }