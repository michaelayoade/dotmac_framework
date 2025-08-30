"""
Adapter to replace ISP analytics module with shared analytics service.
This provides backward compatibility while using the shared service.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.cache import create_cache_service
from dotmac_shared.events import EventBus
from dotmac_shared.services_framework.services.analytics_service import (
    AnalyticsService,
    AnalyticsServiceConfig,
)

from . import schemas

logger = logging.getLogger(__name__)


class ISPAnalyticsAdapter:
    """
    Adapter that provides ISP analytics interface using shared analytics service.
    Maintains backward compatibility with existing ISP analytics API.
    """

    def __init__(
        self,
        tenant_id: str,
        analytics_service: Optional[AnalyticsService] = None,
        event_bus: Optional[EventBus] = None,
        cache_service=None,
    ):
        self.tenant_id = tenant_id

        # Initialize shared services
        if analytics_service:
            self.analytics_service = analytics_service
        else:
            config = AnalyticsServiceConfig(
                provider="prometheus",
                deployment_context=None,  # Will be set by application factory
            )
            self.analytics_service = AnalyticsService(config)

        self.event_bus = event_bus
        self.cache_service = cache_service or create_cache_service()

    async def initialize(self) -> bool:
        """Initialize the adapter and underlying services."""
        try:
            await self.analytics_service.initialize()
            if self.cache_service:
                await self.cache_service.initialize()
            logger.info(
                f"✅ ISP Analytics Adapter initialized for tenant {self.tenant_id}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize ISP Analytics Adapter: {e}")
            return False

    # Backward compatibility methods for existing ISP analytics API

    async def track_event(
        self, event_type: str, entity_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Track an event using shared analytics service."""
        try:
            await self.analytics_service.track_event(
                event_type=event_type,
                entity_id=entity_id,
                metadata={
                    **(metadata or {}),
                    "tenant_id": self.tenant_id,
                    "source": "isp_analytics_adapter",
                },
            )
            # Publish event for other services if event bus available
            if self.event_bus:
                await self.event_bus.publish(
                    "analytics.event_tracked",
                    {
                        "event_type": event_type,
                        "entity_id": entity_id,
                        "tenant_id": self.tenant_id,
                        "metadata": metadata,
                    },
                )
            return True

        except Exception as e:
            logger.error(f"Failed to track event {event_type} for {entity_id}: {e}")
            return False

    async def get_metrics(
        self,
        metric_names: List[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get metrics data using shared analytics service."""
        try:
            # Use shared analytics service to get metrics
            metrics_data = await self.analytics_service.get_metrics(
                metric_names=metric_names,
                tenant_id=self.tenant_id,
                start_time=start_time,
                end_time=end_time,
            )
            return metrics_data

        except Exception as e:
            logger.error(f"Failed to get metrics {metric_names}: {e}")
            return {}

    async def create_metric(
        self, metric_data: schemas.MetricCreate
    ) -> Optional[schemas.MetricResponse]:
        """Create a metric configuration (mapped to shared analytics)."""
        try:
            # Convert ISP metric schema to shared analytics format
            await self.analytics_service.configure_custom_metric(
                metric_name=metric_data.name,
                metric_type=(
                    metric_data.metric_type.value
                    if hasattr(metric_data, "metric_type")
                    else "counter"
                ),
                tenant_id=self.tenant_id,
                metadata=metric_data.dict() if hasattr(metric_data, "dict") else {},
            )
            # Return response in expected format
            return schemas.MetricResponse(
                id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
                name=metric_data.name,
                tenant_id=self.tenant_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Failed to create metric {metric_data.name}: {e}")
            return None

    async def create_report(
        self, report_data: schemas.ReportCreate
    ) -> Optional[schemas.ReportResponse]:
        """Create a report using cached analytics data."""
        try:
            # Generate report using shared analytics
            report_data_result = await self.analytics_service.generate_report(
                report_type=(
                    report_data.report_type.value
                    if hasattr(report_data, "report_type")
                    else "summary"
                ),
                tenant_id=self.tenant_id,
                parameters=report_data.dict() if hasattr(report_data, "dict") else {},
            )
            # Cache the report if cache service available
            if self.cache_service and report_data_result:
                cache_key = f"report:{self.tenant_id}:{report_data.name}"
                await self.cache_service.set(
                    cache_key,
                    report_data_result,
                    tenant_id=self.tenant_id,
                    expire=3600,  # 1 hour
                )
            return schemas.ReportResponse(
                id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
                name=report_data.name,
                tenant_id=self.tenant_id,
                data=report_data_result,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Failed to create report {report_data.name}: {e}")
            return None

    async def get_dashboard_data(self, dashboard_id: UUID) -> Optional[Dict[str, Any]]:
        """Get dashboard data using shared analytics."""
        try:
            # Check cache first
            if self.cache_service:
                cache_key = f"dashboard:{self.tenant_id}:{dashboard_id}"
                cached_data = await self.cache_service.get(
                    cache_key, tenant_id=self.tenant_id
                )
                if cached_data:
                    return cached_data

            # Generate dashboard data using shared analytics
            dashboard_data = await self.analytics_service.get_dashboard_metrics(
                dashboard_id=str(dashboard_id), tenant_id=self.tenant_id
            )
            # Cache the result
            if self.cache_service and dashboard_data:
                cache_key = f"dashboard:{self.tenant_id}:{dashboard_id}"
                await self.cache_service.set(
                    cache_key,
                    dashboard_data,
                    tenant_id=self.tenant_id,
                    expire=300,  # 5 minutes
                )
            return dashboard_data

        except Exception as e:
            logger.error(f"Failed to get dashboard data {dashboard_id}: {e}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the adapter."""
        try:
            analytics_health = await self.analytics_service.health_check()

            return {
                "adapter": "healthy",
                "tenant_id": self.tenant_id,
                "shared_analytics": analytics_health.get("status", "unknown"),
                "cache_service": "available" if self.cache_service else "unavailable",
                "event_bus": "available" if self.event_bus else "unavailable",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "adapter": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


# Factory function for easy adapter creation
async def create_isp_analytics_adapter(
    tenant_id: str,
    analytics_service: Optional[AnalyticsService] = None,
    event_bus: Optional[EventBus] = None,
    cache_service=None,
) -> ISPAnalyticsAdapter:
    """Create and initialize ISP analytics adapter."""

    adapter = ISPAnalyticsAdapter(
        tenant_id=tenant_id,
        analytics_service=analytics_service,
        event_bus=event_bus,
        cache_service=cache_service,
    )
    await adapter.initialize()
    return adapter
