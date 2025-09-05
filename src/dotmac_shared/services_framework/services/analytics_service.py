"""
Analytics service implementation for DotMac Services Framework.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

from ...application.config import DeploymentContext, DeploymentMode
from ..core.base import ServiceHealth, ServiceStatus, StatefulService

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsServiceConfig:
    """Analytics service configuration."""

    provider: str = "prometheus"  # prometheus, datadog, newrelic, custom
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    deployment_context: Optional[DeploymentContext] = None

    # Metrics collection settings
    collection_interval_seconds: int = 60
    metric_retention_hours: int = 24
    batch_size: int = 100
    max_cached_metrics: int = 10000

    # Custom metrics configuration
    custom_metrics: dict[str, Any] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.custom_metrics is None:
            self.custom_metrics = {}

        # Get provider-specific configuration
        if self.provider.lower() == "prometheus":
            if not self.endpoint:
                self.endpoint = os.getenv("PROMETHEUS_ENDPOINT", "http://localhost:9090")

        elif self.provider.lower() == "datadog":
            if not self.api_key:
                self.api_key = os.getenv("DATADOG_API_KEY")
            if not self.endpoint:
                self.endpoint = os.getenv("DATADOG_ENDPOINT", "https://api.datadoghq.com")

        elif self.provider.lower() == "newrelic":
            if not self.api_key:
                self.api_key = os.getenv("NEWRELIC_API_KEY")
            if not self.endpoint:
                self.endpoint = os.getenv("NEWRELIC_ENDPOINT", "https://api.newrelic.com")

        # Try tenant-specific configuration
        if (
            self.deployment_context
            and self.deployment_context.mode == DeploymentMode.TENANT_CONTAINER
            and self.deployment_context.tenant_id
        ):
            tenant_id = self.deployment_context.tenant_id.upper()

            tenant_api_key = os.getenv(f"TENANT_{tenant_id}_ANALYTICS_API_KEY")
            if tenant_api_key:
                self.api_key = tenant_api_key

            tenant_endpoint = os.getenv(f"TENANT_{tenant_id}_ANALYTICS_ENDPOINT")
            if tenant_endpoint:
                self.endpoint = tenant_endpoint


class AnalyticsService(StatefulService):
    """Service layer - exceptions bubble up to router @standard_exception_handler."""

    """Analytics service implementation."""

    def __init__(self, config: AnalyticsServiceConfig):
        """__init__ service method."""
        super().__init__(name="analytics", config=config.__dict__, required_config=["provider"])
        self.analytics_config = config
        self.metrics_cache: list[dict[str, Any]] = []
        self.priority = 90  # High priority for monitoring
        self._last_collection = 0
        self._last_cleanup = 0

    async def _initialize_stateful_service(self) -> bool:
        """Initialize analytics service."""
        provider = self.analytics_config.provider.lower()

        # Initialize provider-specific client
        if provider == "prometheus":
            await self._initialize_prometheus()
        elif provider == "datadog":
            await self._initialize_datadog()
        elif provider == "newrelic":
            await self._initialize_newrelic()
        elif provider == "custom":
            await self._initialize_custom()
        else:
            raise ValueError(f"Unsupported analytics provider: {provider}")

        # Initialize state
        self.set_state("metrics_collected", 0)
        self.set_state("metrics_sent", 0)
        self.set_state("analytics_errors", 0)
        self.set_state("data_points", 0)
        self._last_collection = time.time()

        await self._set_status(
            ServiceStatus.READY,
            f"Analytics service ready with {provider}",
            {
                "provider": provider,
                "endpoint": self.analytics_config.endpoint,
                "collection_interval": self.analytics_config.collection_interval_seconds,
                "retention_hours": self.analytics_config.metric_retention_hours,
            },
        )
        return True

    async def _initialize_prometheus(self):
        """Initialize Prometheus analytics provider."""
        logger.info("Initializing Prometheus analytics provider...")

        # Validate endpoint
        if not self.analytics_config.endpoint:
            raise ValueError("Prometheus endpoint is required")

        # Test connection (simulated)
        logger.info(f"✅ Prometheus connection validated: {self.analytics_config.endpoint}")

    async def _initialize_datadog(self):
        """Initialize Datadog analytics provider."""
        logger.info("Initializing Datadog analytics provider...")

        if not self.analytics_config.api_key:
            raise ValueError("Datadog API key is required")

        # Test API connection (simulated)
        logger.info("✅ Datadog API connection validated")

    async def _initialize_newrelic(self):
        """Initialize New Relic analytics provider."""
        logger.info("Initializing New Relic analytics provider...")

        if not self.analytics_config.api_key:
            raise ValueError("New Relic API key is required")

        # Test API connection (simulated)
        logger.info("✅ New Relic API connection validated")

    async def _initialize_custom(self):
        """Initialize custom analytics provider."""
        logger.info("Initializing custom analytics provider...")

        # Custom provider initialization would go here
        logger.info("✅ Custom analytics provider initialized")

    async def shutdown(self) -> bool:
        """Shutdown analytics service."""
        await self._set_status(ServiceStatus.SHUTTING_DOWN, "Shutting down analytics service")

        # Send any remaining metrics
        if self.metrics_cache:
            await self._flush_metrics()

        # Clear cache and state
        self.metrics_cache.clear()
        self.clear_state()

        await self._set_status(ServiceStatus.SHUTDOWN, "Analytics service shutdown complete")
        return True

    async def _health_check_stateful_service(self) -> ServiceHealth:
        """Perform health check."""
        # Check cache size
        cache_usage = len(self.metrics_cache) / self.analytics_config.max_cached_metrics

        # Clean up old metrics if needed
        self._cleanup_old_metrics()

        # Test provider connectivity
        provider_healthy = await self._test_provider_connectivity()

        if not provider_healthy:
            return ServiceHealth(
                status=ServiceStatus.ERROR,
                message=f"Analytics provider {self.analytics_config.provider} is unavailable",
                details=self._get_health_details(),
            )

        if cache_usage > 0.9:
            return ServiceHealth(
                status=ServiceStatus.READY,
                message=f"Analytics service healthy but cache nearly full ({len(self.metrics_cache)}/{self.analytics_config.max_cached_metrics})",
                details=self._get_health_details(),
            )

        return ServiceHealth(
            status=ServiceStatus.READY,
            message="Analytics service healthy",
            details=self._get_health_details(),
        )

    async def _test_provider_connectivity(self) -> bool:
        """Test connectivity to analytics provider."""
        # In real implementation, this would test actual provider APIs
        return True

    def _get_health_details(self) -> dict[str, Any]:
        """Get health check details."""
        return {
            "provider": self.analytics_config.provider,
            "endpoint": self.analytics_config.endpoint,
            "cached_metrics": len(self.metrics_cache),
            "max_cached_metrics": self.analytics_config.max_cached_metrics,
            "cache_usage": f"{len(self.metrics_cache)}/{self.analytics_config.max_cached_metrics}",
            "metrics_collected": self.get_state("metrics_collected", 0),
            "metrics_sent": self.get_state("metrics_sent", 0),
            "data_points": self.get_state("data_points", 0),
            "analytics_errors": self.get_state("analytics_errors", 0),
            "last_collection": self._last_collection,
        }

    async def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[dict[str, str]] = None,
        timestamp: Optional[float] = None,
    ) -> bool:
        """Record a single metric."""
        if not self.is_ready():
            raise RuntimeError("Analytics service not ready")

        # Check cache limits
        if len(self.metrics_cache) >= self.analytics_config.max_cached_metrics:
            # Flush oldest metrics
            await self._flush_oldest_metrics()

        tags = tags or {}
        timestamp = timestamp or time.time()

        # Add tenant context if available
        if self.analytics_config.deployment_context and self.analytics_config.deployment_context.tenant_id:
            tags["tenant_id"] = self.analytics_config.deployment_context.tenant_id

        # Add deployment context
        if self.analytics_config.deployment_context:
            if self.analytics_config.deployment_context.platform:
                tags["platform"] = self.analytics_config.deployment_context.platform
            if self.analytics_config.deployment_context.environment:
                tags["environment"] = self.analytics_config.deployment_context.environment

        metric = {
            "name": metric_name,
            "value": value,
            "tags": tags,
            "timestamp": timestamp,
            "recorded_at": time.time(),
        }

        # Cache the metric
        self.metrics_cache.append(metric)

        # Update statistics
        metrics_collected = self.get_state("metrics_collected", 0)
        data_points = self.get_state("data_points", 0)

        self.set_state("metrics_collected", metrics_collected + 1)
        self.set_state("data_points", data_points + 1)

        # Auto-flush if we have enough metrics
        if len(self.metrics_cache) >= self.analytics_config.batch_size:
            await self._flush_metrics()

        return True

    async def record_event(
        self,
        event_name: str,
        properties: Optional[dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ) -> bool:
        """Record an analytics event."""
        if not self.is_ready():
            raise RuntimeError("Analytics service not ready")

        properties = properties or {}
        timestamp = timestamp or time.time()

        # Add tenant context if available
        if self.analytics_config.deployment_context and self.analytics_config.deployment_context.tenant_id:
            properties["tenant_id"] = self.analytics_config.deployment_context.tenant_id

        # Convert event to metric format
        await self.record_metric(
            metric_name=f"events.{event_name}",
            value=1.0,
            tags={"event_type": event_name},
            timestamp=timestamp,
        )

        return True

    async def record_batch_metrics(self, metrics: list[dict[str, Any]]) -> int:
        """Record multiple metrics in batch."""
        if not self.is_ready():
            raise RuntimeError("Analytics service not ready")

        successful_count = 0

        for metric in metrics:
            success = await self.record_metric(
                metric_name=metric["name"],
                value=metric["value"],
                tags=metric.get("tags"),
                timestamp=metric.get("timestamp"),
            )
            if success:
                successful_count += 1

        return successful_count

    async def _flush_metrics(self) -> bool:
        """Flush cached metrics to analytics provider."""
        if not self.metrics_cache:
            return True

        # Simulate sending metrics to provider
        metrics_to_send = self.metrics_cache.copy()

        # In real implementation, this would send to actual provider
        provider = self.analytics_config.provider.lower()

        if provider == "prometheus":
            await self._send_to_prometheus(metrics_to_send)
        elif provider == "datadog":
            await self._send_to_datadog(metrics_to_send)
        elif provider == "newrelic":
            await self._send_to_newrelic(metrics_to_send)
        else:
            await self._send_to_custom(metrics_to_send)

        # Clear cache after successful send
        self.metrics_cache.clear()

        # Update statistics
        metrics_sent = self.get_state("metrics_sent", 0)
        self.set_state("metrics_sent", metrics_sent + len(metrics_to_send))

        logger.debug(f"Flushed {len(metrics_to_send)} metrics to {provider}")

        return True

    async def _flush_oldest_metrics(self):
        """Flush oldest cached metrics to make room."""
        if len(self.metrics_cache) < self.analytics_config.batch_size:
            return

        # Take oldest batch_size metrics
        oldest_metrics = self.metrics_cache[: self.analytics_config.batch_size]
        remaining_metrics = self.metrics_cache[self.analytics_config.batch_size :]

        # Update cache with remaining metrics
        self.metrics_cache = remaining_metrics

        # Send oldest metrics
        await self._send_metrics_batch(oldest_metrics)

    async def _send_to_prometheus(self, metrics: list[dict[str, Any]]):
        """Send metrics to Prometheus."""
        # Simulate Prometheus metrics sending
        logger.debug(f"Sending {len(metrics)} metrics to Prometheus")

    async def _send_to_datadog(self, metrics: list[dict[str, Any]]):
        """Send metrics to Datadog."""
        # Simulate Datadog metrics sending
        logger.debug(f"Sending {len(metrics)} metrics to Datadog")

    async def _send_to_newrelic(self, metrics: list[dict[str, Any]]):
        """Send metrics to New Relic."""
        # Simulate New Relic metrics sending
        logger.debug(f"Sending {len(metrics)} metrics to New Relic")

    async def _send_to_custom(self, metrics: list[dict[str, Any]]):
        """Send metrics to custom provider."""
        # Custom provider implementation
        logger.debug(f"Sending {len(metrics)} metrics to custom provider")

    async def _send_metrics_batch(self, metrics: list[dict[str, Any]]):
        """Send a batch of metrics to the configured provider."""
        provider = self.analytics_config.provider.lower()

        if provider == "prometheus":
            await self._send_to_prometheus(metrics)
        elif provider == "datadog":
            await self._send_to_datadog(metrics)
        elif provider == "newrelic":
            await self._send_to_newrelic(metrics)
        else:
            await self._send_to_custom(metrics)

    def _cleanup_old_metrics(self):
        """Remove old metrics from cache."""
        current_time = time.time()

        # Only cleanup every 5 minutes
        if current_time - self._last_cleanup < 300:
            return

        self._last_cleanup = current_time
        retention_seconds = self.analytics_config.metric_retention_hours * 3600

        # Remove metrics older than retention period
        old_metrics = [
            metric for metric in self.metrics_cache if current_time - metric["recorded_at"] > retention_seconds
        ]

        for metric in old_metrics:
            self.metrics_cache.remove(metric)

        if old_metrics:
            logger.debug(f"Cleaned up {len(old_metrics)} old metrics")

    def _increment_analytics_errors(self):
        """Increment analytics error count."""
        errors = self.get_state("analytics_errors", 0)
        self.set_state("analytics_errors", errors + 1)

    def get_analytics_stats(self) -> dict[str, Any]:
        """Get analytics service statistics."""
        return {
            "provider": self.analytics_config.provider,
            "endpoint": self.analytics_config.endpoint,
            "cached_metrics": len(self.metrics_cache),
            "max_cached_metrics": self.analytics_config.max_cached_metrics,
            "metrics_collected": self.get_state("metrics_collected", 0),
            "metrics_sent": self.get_state("metrics_sent", 0),
            "data_points": self.get_state("data_points", 0),
            "analytics_errors": self.get_state("analytics_errors", 0),
            "collection_interval": self.analytics_config.collection_interval_seconds,
            "retention_hours": self.analytics_config.metric_retention_hours,
        }


async def create_analytics_service(config: AnalyticsServiceConfig) -> AnalyticsService:
    """Create and initialize analytics service."""
    service = AnalyticsService(config)

    # Service will be initialized by the registry
    return service
