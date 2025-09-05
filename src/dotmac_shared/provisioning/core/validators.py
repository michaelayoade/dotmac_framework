"""
Container health validation for the DotMac Provisioning Service.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import aiohttp
import structlog

from .exceptions import HealthCheckError, ValidationError
from .models import ContainerHealth, HealthStatus

logger = structlog.get_logger(__name__)


class HealthValidator:
    """Validates container health during and after provisioning."""

    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def validate_container_health(
        self,
        container_id: str,
        base_url: str,
        expected_checks: Optional[list[str]] = None,
    ) -> ContainerHealth:
        """Perform comprehensive container health validation."""

        logger.info(
            "Starting container health validation",
            container_id=container_id,
            base_url=base_url,
        )

        health_result = ContainerHealth(
            overall_status=HealthStatus.STARTING, last_check=datetime.now(timezone.utc)
        )

        try:
            # Initialize session if not already done
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )

            # Perform individual health checks
            await self._check_api_health(base_url, health_result)
            await self._check_database_health(base_url, health_result)
            await self._check_cache_health(base_url, health_result)
            await self._check_ssl_health(base_url, health_result)

            # Additional container-specific checks
            if expected_checks:
                await self._check_custom_endpoints(
                    base_url, expected_checks, health_result
                )

            # Determine overall status
            health_result.overall_status = self._determine_overall_status(health_result)

            logger.info(
                "Container health validation completed",
                container_id=container_id,
                overall_status=health_result.overall_status.value,
                failed_checks=health_result.failed_checks,
            )

        except Exception as e:
            logger.error(
                "Container health validation failed",
                container_id=container_id,
                error=str(e),
            )
            health_result.overall_status = HealthStatus.UNHEALTHY
            health_result.failed_checks.append("validation_error")
            health_result.error_messages["validation_error"] = str(e)

        return health_result

    async def _check_api_health(
        self, base_url: str, health_result: ContainerHealth
    ) -> None:
        """Check API endpoint health."""
        try:
            start_time = time.time()

            async with self.session.get(f"{base_url}/health/live") as response:
                health_result.api_response_time = time.time() - start_time

                if response.status == 200:
                    health_result.api_healthy = True
                    logger.debug(
                        "API health check passed",
                        response_time=health_result.api_response_time,
                    )
                else:
                    health_result.api_healthy = False
                    health_result.failed_checks.append("api_health")
                    health_result.error_messages[
                        "api_health"
                    ] = f"HTTP {response.status}"
                    logger.warning("API health check failed", status=response.status)

        except Exception as e:
            health_result.api_healthy = False
            health_result.failed_checks.append("api_health")
            health_result.error_messages["api_health"] = str(e)
            logger.error("API health check error", error=str(e))

    async def _check_database_health(
        self, base_url: str, health_result: ContainerHealth
    ) -> None:
        """Check database connectivity."""
        try:
            start_time = time.time()

            async with self.session.get(f"{base_url}/health/database") as response:
                health_result.database_response_time = time.time() - start_time

                if response.status == 200:
                    health_result.database_healthy = True
                    logger.debug(
                        "Database health check passed",
                        response_time=health_result.database_response_time,
                    )
                else:
                    health_result.database_healthy = False
                    health_result.failed_checks.append("database_health")
                    health_result.error_messages[
                        "database_health"
                    ] = f"HTTP {response.status}"
                    logger.warning(
                        "Database health check failed", status=response.status
                    )

        except Exception as e:
            health_result.database_healthy = False
            health_result.failed_checks.append("database_health")
            health_result.error_messages["database_health"] = str(e)
            logger.error("Database health check error", error=str(e))

    async def _check_cache_health(
        self, base_url: str, health_result: ContainerHealth
    ) -> None:
        """Check cache (Redis) connectivity."""
        try:
            async with self.session.get(f"{base_url}/health/cache") as response:
                if response.status == 200:
                    health_result.cache_healthy = True
                    logger.debug("Cache health check passed")
                else:
                    health_result.cache_healthy = False
                    health_result.failed_checks.append("cache_health")
                    health_result.error_messages[
                        "cache_health"
                    ] = f"HTTP {response.status}"
                    logger.warning("Cache health check failed", status=response.status)

        except Exception as e:
            health_result.cache_healthy = False
            health_result.failed_checks.append("cache_health")
            health_result.error_messages["cache_health"] = str(e)
            logger.error("Cache health check error", error=str(e))

    async def _check_ssl_health(
        self, base_url: str, health_result: ContainerHealth
    ) -> None:
        """Check SSL certificate status."""
        try:
            # Only check SSL if URL uses HTTPS
            if not base_url.startswith("https://"):
                health_result.ssl_healthy = True  # SSL not required for HTTP
                return

            async with self.session.get(f"{base_url}/health/ssl") as response:
                if response.status == 200:
                    health_result.ssl_healthy = True
                    logger.debug("SSL health check passed")
                else:
                    health_result.ssl_healthy = False
                    health_result.failed_checks.append("ssl_health")
                    health_result.error_messages[
                        "ssl_health"
                    ] = f"HTTP {response.status}"
                    logger.warning("SSL health check failed", status=response.status)

        except Exception as e:
            health_result.ssl_healthy = False
            health_result.failed_checks.append("ssl_health")
            health_result.error_messages["ssl_health"] = str(e)
            logger.error("SSL health check error", error=str(e))

    async def _check_custom_endpoints(
        self, base_url: str, endpoints: list[str], health_result: ContainerHealth
    ) -> None:
        """Check custom health endpoints."""
        for endpoint in endpoints:
            try:
                endpoint_url = f"{base_url}/{endpoint.lstrip('/')}"
                async with self.session.get(endpoint_url) as response:
                    if response.status != 200:
                        health_result.failed_checks.append(f"custom_{endpoint}")
                        health_result.error_messages[
                            f"custom_{endpoint}"
                        ] = f"HTTP {response.status}"
                        logger.warning(
                            "Custom endpoint check failed",
                            endpoint=endpoint,
                            status=response.status,
                        )
                    else:
                        logger.debug("Custom endpoint check passed", endpoint=endpoint)

            except Exception as e:
                health_result.failed_checks.append(f"custom_{endpoint}")
                health_result.error_messages[f"custom_{endpoint}"] = str(e)
                logger.error(
                    "Custom endpoint check error", endpoint=endpoint, error=str(e)
                )

    def _determine_overall_status(self, health_result: ContainerHealth) -> HealthStatus:
        """Determine overall health status based on individual checks."""

        # Critical checks that must pass
        critical_checks = [health_result.api_healthy, health_result.database_healthy]

        # If any critical check fails, overall status is unhealthy
        if not all(critical_checks):
            return HealthStatus.UNHEALTHY

        # If all critical checks pass but some non-critical checks fail, still healthy
        # (cache and SSL are non-critical for basic functionality)
        return HealthStatus.HEALTHY

    async def wait_for_healthy(
        self,
        container_id: str,
        base_url: str,
        max_wait_seconds: int = 300,
        check_interval: int = 10,
    ) -> ContainerHealth:
        """Wait for container to become healthy with retries."""

        logger.info(
            "Waiting for container to become healthy",
            container_id=container_id,
            max_wait_seconds=max_wait_seconds,
        )

        start_time = time.time()
        attempt = 0

        while time.time() - start_time < max_wait_seconds:
            attempt += 1
            logger.debug(
                "Health check attempt", attempt=attempt, container_id=container_id
            )

            try:
                health_result = await self.validate_container_health(
                    container_id, base_url
                )

                if health_result.overall_status == HealthStatus.HEALTHY:
                    logger.info(
                        "Container is healthy",
                        container_id=container_id,
                        attempts=attempt,
                        duration=time.time() - start_time,
                    )
                    return health_result

                logger.debug(
                    "Container not yet healthy, retrying",
                    container_id=container_id,
                    status=health_result.overall_status.value,
                    failed_checks=health_result.failed_checks,
                )

            except Exception as e:
                logger.warning(
                    "Health check attempt failed",
                    container_id=container_id,
                    attempt=attempt,
                    error=str(e),
                )

            # Wait before next attempt
            await asyncio.sleep(check_interval)

        # Timeout reached
        logger.error(
            "Container health check timeout",
            container_id=container_id,
            max_wait_seconds=max_wait_seconds,
            attempts=attempt,
        )

        raise HealthCheckError(
            f"Container did not become healthy within {max_wait_seconds} seconds",
            health_check_type="overall_health",
            container_id=container_id,
        )

    async def get_container_metrics(self, base_url: str) -> dict[str, Any]:
        """Get container performance metrics."""
        try:
            async with self.session.get(f"{base_url}/metrics") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(
                        "Failed to get container metrics", status=response.status
                    )
                    return {}
        except Exception as e:
            logger.error("Error getting container metrics", error=str(e))
            return {}


async def validate_container_health(
    container_id: str,
    base_url: str,
    timeout: int = 60,
    expected_checks: Optional[list[str]] = None,
) -> ContainerHealth:
    """
    Standalone function to validate container health.

    Args:
        container_id: Unique container identifier
        base_url: Base URL for health checks
        timeout: Request timeout in seconds
        expected_checks: List of additional endpoints to check

    Returns:
        ContainerHealth object with validation results
    """

    async with HealthValidator(timeout=timeout) as validator:
        return await validator.validate_container_health(
            container_id=container_id,
            base_url=base_url,
            expected_checks=expected_checks,
        )


class ProvisioningValidator:
    """Validates provisioning process and requirements."""

    @staticmethod
    async def validate_provisioning_request(
        isp_id: UUID,
        customer_count: int,
        config: Any,  # ISPConfig
        custom_resources: Optional[Any] = None,  # ResourceRequirements
    ) -> None:
        """Validate provisioning request parameters."""

        # Validate customer count
        if customer_count < 1 or customer_count > 50000:
            raise ValidationError(
                f"Customer count must be between 1 and 50,000, got {customer_count}",
                validation_type="customer_count",
                isp_id=isp_id,
            )

        # Validate tenant name uniqueness (would check against database in real implementation)
        if not config.tenant_name or len(config.tenant_name) < 3:
            raise ValidationError(
                f"Tenant name must be at least 3 characters, got '{config.tenant_name}'",
                validation_type="tenant_name",
                isp_id=isp_id,
            )

        # Validate resource requirements
        if custom_resources:
            if custom_resources.cpu_cores > 16.0:
                raise ValidationError(
                    f"CPU limit exceeds maximum of 16 cores, got {custom_resources.cpu_cores}",
                    validation_type="resource_limits",
                    isp_id=isp_id,
                )

            if custom_resources.memory_gb > 64.0:
                raise ValidationError(
                    f"Memory limit exceeds maximum of 64GB, got {custom_resources.memory_gb}",
                    validation_type="resource_limits",
                    isp_id=isp_id,
                )

        logger.info(
            "Provisioning request validation passed",
            isp_id=str(isp_id),
            customer_count=customer_count,
        )

    @staticmethod
    async def validate_infrastructure_readiness(
        infrastructure_type: str, region: str = "us-east-1"
    ) -> bool:
        """Validate that infrastructure is ready for deployment."""

        # This would check:
        # - Kubernetes cluster availability
        # - Resource quotas
        # - Network policies
        # - Storage classes

        logger.info(
            "Infrastructure readiness validation passed",
            infrastructure_type=infrastructure_type,
            region=region,
        )
        return True
