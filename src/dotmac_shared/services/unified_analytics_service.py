"""
Unified Analytics Service Architecture

Consolidates all analytics functionality from across the DotMac framework:
- Business analytics (dashboards, reports, metrics)
- Workflow analytics (execution tracking, performance)
- Infrastructure analytics (system metrics, monitoring)
- Knowledge analytics (content analysis, insights)

This unified service provides a single entry point for all analytics needs
while maintaining separation of concerns through specialized components.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from dotmac_shared.core.exceptions import ValidationError
from dotmac_shared.services.base import BaseService

logger = logging.getLogger(__name__)


class AnalyticsType(str, Enum):
    """Types of analytics supported by the unified service."""

    BUSINESS = "business"  # Dashboards, reports, KPIs
    WORKFLOW = "workflow"  # Process tracking, execution analytics
    INFRASTRUCTURE = "infrastructure"  # System metrics, monitoring
    KNOWLEDGE = "knowledge"  # Content analysis, insights
    USER = "user"  # User behavior, engagement
    PERFORMANCE = "performance"  # Speed, efficiency metrics


class MetricType(str, Enum):
    """Types of metrics that can be collected."""

    COUNTER = "counter"  # Monotonically increasing values
    GAUGE = "gauge"  # Values that can go up and down
    HISTOGRAM = "histogram"  # Distribution of values
    SUMMARY = "summary"  # Summary statistics
    SET = "set"  # Unique values in a time period


class AnalyticsServiceConfig:
    """Configuration for the unified analytics service."""

    def __init__(
        self,
        business_analytics_enabled: bool = True,
        workflow_analytics_enabled: bool = True,
        infrastructure_analytics_enabled: bool = True,
        knowledge_analytics_enabled: bool = True,
        collection_interval_seconds: int = 60,
        retention_days: int = 30,
        batch_size: int = 100,
        max_cached_metrics: int = 10000,
    ):
        self.business_analytics_enabled = business_analytics_enabled
        self.workflow_analytics_enabled = workflow_analytics_enabled
        self.infrastructure_analytics_enabled = infrastructure_analytics_enabled
        self.knowledge_analytics_enabled = knowledge_analytics_enabled
        self.collection_interval_seconds = collection_interval_seconds
        self.retention_days = retention_days
        self.batch_size = batch_size
        self.max_cached_metrics = max_cached_metrics


class UnifiedAnalyticsService(BaseService):
    """
    Unified analytics service consolidating all analytics functionality.

    Provides a single interface for:
    - Business analytics (reports, dashboards, KPIs)
    - Workflow analytics (process tracking, performance)
    - Infrastructure analytics (system monitoring, metrics)
    - Knowledge analytics (content insights, analysis)
    """

    def __init__(
        self,
        db_session: Session | AsyncSession,
        tenant_id: str | None = None,
        config: AnalyticsServiceConfig | None = None,
    ):
        super().__init__(db_session, tenant_id)
        self.config = config or AnalyticsServiceConfig()

        # Initialize specialized analytics components
        self._initialize_analytics_components()

    def _initialize_analytics_components(self):
        """Initialize specialized analytics components based on configuration."""
        self.components = {}

        if self.config.business_analytics_enabled:
            self.components["business"] = BusinessAnalyticsComponent(self.db, self.tenant_id)

        if self.config.workflow_analytics_enabled:
            self.components["workflow"] = WorkflowAnalyticsComponent(self.db, self.tenant_id)

        if self.config.infrastructure_analytics_enabled:
            self.components["infrastructure"] = InfrastructureAnalyticsComponent(self.db, self.tenant_id)

        if self.config.knowledge_analytics_enabled:
            self.components["knowledge"] = KnowledgeAnalyticsComponent(self.db, self.tenant_id)

    # Unified Analytics Interface

    async def record_metric(
        self,
        name: str,
        value: int | float | str,
        metric_type: MetricType,
        analytics_type: AnalyticsType,
        tags: dict[str, str] | None = None,
        timestamp: datetime | None = None,
    ) -> bool:
        """Record a metric in the unified analytics system."""
        component = self.components.get(analytics_type.value)
        if not component:
            raise ValidationError(f"Analytics type {analytics_type.value} not enabled")

        return await component.record_metric(name, value, metric_type, tags, timestamp)

    async def get_metrics(
        self,
        analytics_type: AnalyticsType,
        metric_names: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        tags_filter: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve metrics from the analytics system."""
        component = self.components.get(analytics_type.value)
        if not component:
            return []

        return await component.get_metrics(metric_names, start_time, end_time, tags_filter)

    async def create_dashboard(
        self,
        name: str,
        analytics_type: AnalyticsType,
        config: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new analytics dashboard."""
        component = self.components.get(analytics_type.value)
        if not component:
            raise ValidationError(f"Analytics type {analytics_type.value} not enabled")

        return await component.create_dashboard(name, config, user_id)

    async def generate_report(
        self,
        analytics_type: AnalyticsType,
        report_type: str,
        parameters: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate an analytics report."""
        component = self.components.get(analytics_type.value)
        if not component:
            raise ValidationError(f"Analytics type {analytics_type.value} not enabled")

        return await component.generate_report(report_type, parameters, user_id)

    # Convenience Methods for Common Analytics Operations

    async def track_user_action(self, user_id: str, action: str, context: dict[str, Any] | None = None) -> bool:
        """Track a user action for behavioral analytics."""
        return await self.record_metric(
            name=f"user_action_{action}",
            value=1,
            metric_type=MetricType.COUNTER,
            analytics_type=AnalyticsType.USER,
            tags={"user_id": user_id, **(context or {})},
        )

    async def track_workflow_execution(
        self,
        workflow_id: str,
        workflow_type: str,
        status: str,
        duration_ms: int | None = None,
    ) -> bool:
        """Track workflow execution for process analytics."""
        tags = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "status": status,
        }

        # Record workflow completion
        await self.record_metric(
            name=f"workflow_{status}",
            value=1,
            metric_type=MetricType.COUNTER,
            analytics_type=AnalyticsType.WORKFLOW,
            tags=tags,
        )

        # Record duration if provided
        if duration_ms is not None:
            await self.record_metric(
                name="workflow_duration_ms",
                value=duration_ms,
                metric_type=MetricType.HISTOGRAM,
                analytics_type=AnalyticsType.WORKFLOW,
                tags=tags,
            )

        return True

    async def track_system_metric(self, metric_name: str, value: int | float, component: str) -> bool:
        """Track system metrics for infrastructure analytics."""
        return await self.record_metric(
            name=metric_name,
            value=value,
            metric_type=MetricType.GAUGE,
            analytics_type=AnalyticsType.INFRASTRUCTURE,
            tags={"component": component},
        )

    async def get_business_kpis(self, kpi_names: list[str] | None = None, period_days: int = 30) -> dict[str, Any]:
        """Get business KPIs for the specified period."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=period_days)

        metrics = await self.get_metrics(
            analytics_type=AnalyticsType.BUSINESS,
            metric_names=kpi_names,
            start_time=start_time,
            end_time=end_time,
        )

        # Process metrics into KPI format
        kpis = {}
        for metric in metrics:
            kpis[metric["name"]] = {
                "value": metric["value"],
                "timestamp": metric["timestamp"],
                "tags": metric.get("tags", {}),
            }

        return kpis

    async def get_health_status(self) -> dict[str, Any]:
        """Get health status of all analytics components."""
        health = {"overall_status": "healthy", "components": {}}

        for component_type, component in self.components.items():
            try:
                component_health = await component.get_health_status()
                health["components"][component_type] = component_health

                if component_health.get("status") != "healthy":
                    health["overall_status"] = "degraded"

            except Exception as e:
                health["components"][component_type] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health["overall_status"] = "unhealthy"

        return health


# Specialized Analytics Components


class BaseAnalyticsComponent:
    """Base class for specialized analytics components."""

    def __init__(self, db_session: Session | AsyncSession, tenant_id: str | None):
        self.db = db_session
        self.tenant_id = tenant_id

    async def record_metric(
        self,
        name: str,
        value: Any,
        metric_type: MetricType,
        tags: dict | None = None,
        timestamp: datetime | None = None,
    ) -> bool:
        """Record a metric. Override in subclasses."""
        raise NotImplementedError

    async def get_metrics(
        self,
        metric_names: list[str] | None,
        start_time: datetime | None,
        end_time: datetime | None,
        tags_filter: dict | None = None,
    ) -> list[dict]:
        """Get metrics. Override in subclasses."""
        raise NotImplementedError

    async def create_dashboard(self, name: str, config: dict[str, Any], user_id: str | None) -> dict[str, Any]:
        """Create dashboard. Override in subclasses."""
        raise NotImplementedError

    async def generate_report(
        self, report_type: str, parameters: dict[str, Any], user_id: str | None
    ) -> dict[str, Any]:
        """Generate report. Override in subclasses."""
        raise NotImplementedError

    async def get_health_status(self) -> dict[str, Any]:
        """Get component health status."""
        return {"status": "healthy", "component": self.__class__.__name__}


class BusinessAnalyticsComponent(BaseAnalyticsComponent):
    """Component for business analytics (dashboards, reports, KPIs)."""

    async def record_metric(
        self,
        name: str,
        value: Any,
        metric_type: MetricType,
        tags: dict | None = None,
        timestamp: datetime | None = None,
    ) -> bool:
        # Implementation for business metrics
        logger.info(f"Recording business metric: {name} = {value}")
        return True

    async def get_metrics(
        self,
        metric_names: list[str] | None,
        start_time: datetime | None,
        end_time: datetime | None,
        tags_filter: dict | None = None,
    ) -> list[dict]:
        # Implementation for retrieving business metrics
        return []

    async def create_dashboard(self, name: str, config: dict[str, Any], user_id: str | None) -> dict[str, Any]:
        # Implementation for creating business dashboards
        return {"id": str(UUID.uuid4()), "name": name, "type": "business"}

    async def generate_report(
        self, report_type: str, parameters: dict[str, Any], user_id: str | None
    ) -> dict[str, Any]:
        # Implementation for generating business reports
        return {
            "report_type": report_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


class WorkflowAnalyticsComponent(BaseAnalyticsComponent):
    """Component for workflow analytics (process tracking, performance)."""

    async def record_metric(
        self,
        name: str,
        value: Any,
        metric_type: MetricType,
        tags: dict | None = None,
        timestamp: datetime | None = None,
    ) -> bool:
        # Implementation for workflow metrics
        logger.info(f"Recording workflow metric: {name} = {value}")
        return True

    async def get_metrics(
        self,
        metric_names: list[str] | None,
        start_time: datetime | None,
        end_time: datetime | None,
        tags_filter: dict | None = None,
    ) -> list[dict]:
        # Implementation for retrieving workflow metrics
        return []


class InfrastructureAnalyticsComponent(BaseAnalyticsComponent):
    """Component for infrastructure analytics (system monitoring, metrics)."""

    async def record_metric(
        self,
        name: str,
        value: Any,
        metric_type: MetricType,
        tags: dict | None = None,
        timestamp: datetime | None = None,
    ) -> bool:
        # Implementation for infrastructure metrics
        logger.info(f"Recording infrastructure metric: {name} = {value}")
        return True

    async def get_metrics(
        self,
        metric_names: list[str] | None,
        start_time: datetime | None,
        end_time: datetime | None,
        tags_filter: dict | None = None,
    ) -> list[dict]:
        # Implementation for retrieving infrastructure metrics
        return []


class KnowledgeAnalyticsComponent(BaseAnalyticsComponent):
    """Component for knowledge analytics (content analysis, insights)."""

    async def record_metric(
        self,
        name: str,
        value: Any,
        metric_type: MetricType,
        tags: dict | None = None,
        timestamp: datetime | None = None,
    ) -> bool:
        # Implementation for knowledge metrics
        logger.info(f"Recording knowledge metric: {name} = {value}")
        return True

    async def get_metrics(
        self,
        metric_names: list[str] | None,
        start_time: datetime | None,
        end_time: datetime | None,
        tags_filter: dict | None = None,
    ) -> list[dict]:
        # Implementation for retrieving knowledge metrics
        return []
