"""
Enhanced workflow analytics with DRY patterns for DotMac Framework.
Consolidates workflow tracking and analytics across all platforms.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from dotmac.application import standard_exception_handler
from dotmac.communications.events import EventBus
from dotmac.core import create_cache_service
from dotmac.core.schemas.base_schemas import TenantBaseModel
from dotmac_shared.application.config import DeploymentContext
from dotmac_shared.services_framework.core.base import (
    ServiceHealth,
    ServiceStatus,
    StatefulService,
)

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class WorkflowType(str, Enum):
    """Types of workflows."""

    CUSTOMER_ONBOARDING = "customer_onboarding"
    SERVICE_PROVISIONING = "service_provisioning"
    BILLING_PROCESS = "billing_process"
    SUPPORT_TICKET = "support_ticket"
    COMPLIANCE_CHECK = "compliance_check"
    TENANT_SETUP = "tenant_setup"
    USER_MANAGEMENT = "user_management"
    REPORTING = "reporting"
    MAINTENANCE = "maintenance"
    CUSTOM = "custom"


class WorkflowEvent(TenantBaseModel):
    """Workflow event tracking."""

    event_id: UUID = field(default_factory=uuid4)
    workflow_id: UUID = field(..., description="Workflow identifier")
    workflow_type: WorkflowType = field(..., description="Type of workflow")
    event_type: str = field(..., description="Event type")
    step_name: Optional[str] = field(None, description="Workflow step name")
    status: WorkflowStatus = field(..., description="Current status")

    # Context information
    user_id: Optional[UUID] = field(None, description="User who triggered")
    session_id: Optional[str] = field(None, description="Session identifier")

    # Performance metrics
    duration_ms: Optional[float] = field(None, description="Event duration in milliseconds")
    resource_usage: dict[str, Any] = field(default_factory=dict, description="Resource usage")

    # Data and metadata
    input_data: dict[str, Any] = field(default_factory=dict, description="Input data")
    output_data: dict[str, Any] = field(default_factory=dict, description="Output data")
    error_details: Optional[dict[str, Any]] = field(None, description="Error information")
    metadata: dict[str, Any] = field(default_factory=dict, description="Additional metadata")

    # Timestamps
    started_at: Optional[datetime] = field(None, description="Event start time")
    completed_at: Optional[datetime] = field(None, description="Event completion time")
    timestamp: datetime = field(default_factory=datetime.utcnow, description="Event timestamp")


class WorkflowMetrics(TenantBaseModel):
    """Workflow analytics metrics."""

    workflow_type: WorkflowType
    period_start: datetime
    period_end: datetime

    # Volume metrics
    total_workflows: int
    completed_workflows: int
    failed_workflows: int
    cancelled_workflows: int

    # Performance metrics
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    percentile_95_ms: float

    # Success metrics
    success_rate: float
    failure_rate: float
    retry_rate: float

    # Throughput metrics
    workflows_per_hour: float
    peak_concurrent: int

    # Error analysis
    top_errors: list[dict[str, Any]]
    error_categories: dict[str, int]

    # Step analysis
    bottleneck_steps: list[dict[str, Any]]
    step_success_rates: dict[str, float]

    calculated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkflowAnalyticsConfig:
    """Configuration for workflow analytics."""

    enabled_workflow_types: list[WorkflowType]
    deployment_context: Optional[DeploymentContext] = None

    # Analytics settings
    real_time_analytics: bool = True
    batch_processing: bool = True
    retention_days: int = 90

    # Performance settings
    max_events_per_batch: int = 1000
    analytics_interval_minutes: int = 5
    cache_ttl_seconds: int = 1800  # 30 minutes

    # Alerting
    performance_alerts: bool = True
    failure_rate_threshold: float = 0.1  # 10%
    duration_threshold_multiplier: float = 2.0  # 2x average

    def __post_init__(self):
        if not self.enabled_workflow_types:
            self.enabled_workflow_types = list(WorkflowType)


class WorkflowAnalyticsService(StatefulService):
    """
    Enhanced workflow analytics service with DRY patterns.
    Provides centralized workflow tracking and analytics.
    """

    def __init__(self, config: WorkflowAnalyticsConfig):
        """Initialize workflow analytics service."""
        super().__init__(
            name="workflow_analytics",
            config=config.__dict__,
            required_config=["enabled_workflow_types"],
        )

        self.analytics_config = config
        self.priority = 85  # High priority for analytics

        # Service dependencies
        self.event_bus: Optional[EventBus] = None
        self.cache_service = None

        # Analytics storage (in production, this would be a database)
        self._workflow_events: list[WorkflowEvent] = []
        self._workflow_metrics: dict[str, WorkflowMetrics] = {}

        # Service state
        self._events_processed = 0
        self._metrics_calculated = 0
        self._alerts_generated = 0

    async def _initialize_stateful_service(self) -> bool:
        """Initialize workflow analytics service."""
        try:
            # Initialize dependencies
            self.cache_service = create_cache_service()
            if self.cache_service:
                await self.cache_service.initialize()

            # Initialize state
            self.set_state("events_processed", 0)
            self.set_state("metrics_calculated", 0)
            self.set_state("alerts_generated", 0)
            self.set_state("last_analytics_run", datetime.now(timezone.utc).isoformat())

            await self._set_status(
                ServiceStatus.READY,
                f"Workflow analytics ready for {len(self.analytics_config.enabled_workflow_types)} workflow types",
                {
                    "workflow_types": [wt.value for wt in self.analytics_config.enabled_workflow_types],
                    "real_time": self.analytics_config.real_time_analytics,
                    "batch_processing": self.analytics_config.batch_processing,
                },
            )

            return True

        except Exception as e:
            logger.error(f"Failed to initialize workflow analytics service: {e}")
            await self._set_status(ServiceStatus.ERROR, f"Initialization failed: {e}")
            return False

    async def shutdown(self) -> bool:
        """Shutdown workflow analytics service."""
        await self._set_status(ServiceStatus.SHUTTING_DOWN, "Shutting down workflow analytics")

        # Process remaining events
        if self.analytics_config.batch_processing and self._workflow_events:
            await self._process_batch_analytics()

        # Clear state
        self.clear_state()

        await self._set_status(ServiceStatus.SHUTDOWN, "Workflow analytics shutdown complete")
        return True

    async def _health_check_stateful_service(self) -> ServiceHealth:
        """Perform health check on workflow analytics service."""
        try:
            details = {
                "workflow_types": [wt.value for wt in self.analytics_config.enabled_workflow_types],
                "events_in_buffer": len(self._workflow_events),
                "events_processed": self.get_state("events_processed", 0),
                "metrics_calculated": self.get_state("metrics_calculated", 0),
                "alerts_generated": self.get_state("alerts_generated", 0),
                "cache_available": self.cache_service is not None,
                "last_analytics_run": self.get_state("last_analytics_run"),
            }

            # Check buffer size
            if len(self._workflow_events) > self.analytics_config.max_events_per_batch * 2:
                return ServiceHealth(
                    status=ServiceStatus.READY,
                    message=f"High event buffer: {len(self._workflow_events)} events",
                    details=details,
                )

            return ServiceHealth(
                status=ServiceStatus.READY,
                message="Workflow analytics service healthy",
                details=details,
            )

        except Exception as e:
            return ServiceHealth(
                status=ServiceStatus.ERROR,
                message=f"Health check failed: {e}",
                details={"error": str(e)},
            )

    @standard_exception_handler
    async def track_workflow_event(
        self,
        workflow_id: UUID,
        workflow_type: WorkflowType,
        event_type: str,
        status: WorkflowStatus,
        step_name: Optional[str] = None,
        user_id: Optional[UUID] = None,
        duration_ms: Optional[float] = None,
        input_data: Optional[dict[str, Any]] = None,
        output_data: Optional[dict[str, Any]] = None,
        error_details: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Track a workflow event."""
        if not self.is_ready():
            raise RuntimeError("Workflow analytics service not ready")

        # Get tenant context
        tenant_id = None
        if self.analytics_config.deployment_context and hasattr(self.analytics_config.deployment_context, "tenant_id"):
            tenant_id = self.analytics_config.deployment_context.tenant_id

        # Create workflow event
        event = WorkflowEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            event_type=event_type,
            step_name=step_name,
            status=status,
            user_id=user_id,
            duration_ms=duration_ms,
            input_data=input_data or {},
            output_data=output_data or {},
            error_details=error_details,
            metadata=metadata or {},
            tenant_id=tenant_id,
        )

        # Set timing information
        if status == WorkflowStatus.RUNNING:
            event.started_at = datetime.now(timezone.utc)
        elif status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        ]:
            event.completed_at = datetime.now(timezone.utc)

        # Store event
        self._workflow_events.append(event)

        # Update statistics
        events_processed = self.get_state("events_processed", 0)
        self.set_state("events_processed", events_processed + 1)
        self._events_processed += 1

        # Process real-time analytics if enabled
        if self.analytics_config.real_time_analytics:
            await self._process_real_time_analytics(event)

        # Process batch if we've reached the threshold
        if (
            self.analytics_config.batch_processing
            and len(self._workflow_events) >= self.analytics_config.max_events_per_batch
        ):
            await self._process_batch_analytics()

        # Cache the event
        if self.cache_service:
            cache_key = f"workflow_event:{tenant_id}:{event.event_id}"
            await self.cache_service.set(
                cache_key,
                event.model_dump(),
                tenant_id=tenant_id,
                expire=self.analytics_config.cache_ttl_seconds,
            )

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                "workflow.event_tracked",
                {
                    "event_id": str(event.event_id),
                    "workflow_id": str(event.workflow_id),
                    "workflow_type": event.workflow_type.value,
                    "event_type": event.event_type,
                    "status": event.status.value,
                    "tenant_id": tenant_id,
                },
            )

        return True

    @standard_exception_handler
    async def get_workflow_metrics(
        self,
        workflow_type: WorkflowType,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        tenant_id: Optional[str] = None,
    ) -> WorkflowMetrics:
        """Get workflow metrics for a specific type and period."""
        if not self.is_ready():
            raise RuntimeError("Workflow analytics service not ready")

        if not period_start:
            period_start = datetime.now(timezone.utc) - timedelta(days=7)
        if not period_end:
            period_end = datetime.now(timezone.utc)

        # Filter events for the period and workflow type
        filtered_events = [
            event
            for event in self._workflow_events
            if (
                event.workflow_type == workflow_type
                and event.timestamp >= period_start
                and event.timestamp <= period_end
                and (not tenant_id or event.tenant_id == tenant_id)
            )
        ]

        return await self._calculate_workflow_metrics(workflow_type, filtered_events, period_start, period_end)

    @standard_exception_handler
    async def get_workflow_analytics_dashboard(
        self,
        period_days: int = 7,
        tenant_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get comprehensive workflow analytics dashboard."""
        if not self.is_ready():
            raise RuntimeError("Workflow analytics service not ready")

        period_start = datetime.now(timezone.utc) - timedelta(days=period_days)
        period_end = datetime.now(timezone.utc)

        dashboard = {
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
                "days": period_days,
            },
            "overview": {
                "total_workflows": 0,
                "active_workflows": 0,
                "completed_workflows": 0,
                "failed_workflows": 0,
                "overall_success_rate": 0.0,
                "avg_duration_minutes": 0.0,
            },
            "by_type": {},
            "trends": {},
            "alerts": [],
        }

        # Calculate metrics for each workflow type
        for workflow_type in self.analytics_config.enabled_workflow_types:
            metrics = await self.get_workflow_metrics(workflow_type, period_start, period_end, tenant_id)

            dashboard["by_type"][workflow_type.value] = {
                "total": metrics.total_workflows,
                "completed": metrics.completed_workflows,
                "failed": metrics.failed_workflows,
                "success_rate": metrics.success_rate,
                "avg_duration_ms": metrics.avg_duration_ms,
                "throughput": metrics.workflows_per_hour,
            }

            # Aggregate overview metrics
            dashboard["overview"]["total_workflows"] += metrics.total_workflows
            dashboard["overview"]["completed_workflows"] += metrics.completed_workflows
            dashboard["overview"]["failed_workflows"] += metrics.failed_workflows

        # Calculate overall metrics
        total = dashboard["overview"]["total_workflows"]
        if total > 0:
            dashboard["overview"]["overall_success_rate"] = dashboard["overview"]["completed_workflows"] / total

        # Add trend data (simplified)
        dashboard["trends"] = await self._calculate_workflow_trends(period_start, period_end, tenant_id)

        return dashboard

    async def _process_real_time_analytics(self, event: WorkflowEvent):
        """Process real-time analytics for a workflow event."""

        # Check for performance alerts
        if event.duration_ms and self.analytics_config.performance_alerts:
            await self._check_performance_alerts(event)

        # Check for failure alerts
        if event.status == WorkflowStatus.FAILED and self.analytics_config.performance_alerts:
            await self._check_failure_alerts(event)

    async def _process_batch_analytics(self):
        """Process batch analytics for accumulated events."""

        if not self._workflow_events:
            return

        # Group events by workflow type
        events_by_type = {}
        for event in self._workflow_events:
            workflow_type = event.workflow_type
            if workflow_type not in events_by_type:
                events_by_type[workflow_type] = []
            events_by_type[workflow_type].append(event)

        # Calculate metrics for each type
        for workflow_type, events in events_by_type.items():
            period_start = min(e.timestamp for e in events)
            period_end = max(e.timestamp for e in events)

            metrics = await self._calculate_workflow_metrics(workflow_type, events, period_start, period_end)

            # Cache metrics
            metrics_key = f"{workflow_type.value}_{period_start.date()}_{period_end.date()}"
            self._workflow_metrics[metrics_key] = metrics

            if self.cache_service:
                cache_key = f"workflow_metrics:{metrics_key}"
                await self.cache_service.set(
                    cache_key,
                    metrics.model_dump(),
                    expire=self.analytics_config.cache_ttl_seconds * 2,
                )

        # Update statistics
        metrics_calculated = self.get_state("metrics_calculated", 0)
        self.set_state("metrics_calculated", metrics_calculated + len(events_by_type))
        self.set_state("last_analytics_run", datetime.now(timezone.utc).isoformat())

        # Clear processed events (in production, these would be archived)
        self._workflow_events.clear()

        logger.info(f"Processed batch analytics for {len(events_by_type)} workflow types")

    async def _calculate_workflow_metrics(
        self,
        workflow_type: WorkflowType,
        events: list[WorkflowEvent],
        period_start: datetime,
        period_end: datetime,
    ) -> WorkflowMetrics:
        """Calculate workflow metrics from events."""

        if not events:
            return WorkflowMetrics(
                workflow_type=workflow_type,
                period_start=period_start,
                period_end=period_end,
                total_workflows=0,
                completed_workflows=0,
                failed_workflows=0,
                cancelled_workflows=0,
                avg_duration_ms=0.0,
                min_duration_ms=0.0,
                max_duration_ms=0.0,
                percentile_95_ms=0.0,
                success_rate=0.0,
                failure_rate=0.0,
                retry_rate=0.0,
                workflows_per_hour=0.0,
                peak_concurrent=0,
                top_errors=[],
                error_categories={},
                bottleneck_steps=[],
                step_success_rates={},
                tenant_id=getattr(self.analytics_config.deployment_context, "tenant_id", None),
            )

        # Group events by workflow ID to get complete workflows
        workflows = {}
        for event in events:
            workflow_id = event.workflow_id
            if workflow_id not in workflows:
                workflows[workflow_id] = []
            workflows[workflow_id].append(event)

        # Calculate basic counts
        total_workflows = len(workflows)
        completed_workflows = 0
        failed_workflows = 0
        cancelled_workflows = 0

        # Duration metrics
        durations = []

        for workflow_events in workflows.values():
            # Sort events by timestamp
            workflow_events.sort(key=lambda e: e.timestamp)

            # Determine final status
            final_event = workflow_events[-1]
            if final_event.status == WorkflowStatus.COMPLETED:
                completed_workflows += 1
            elif final_event.status == WorkflowStatus.FAILED:
                failed_workflows += 1
            elif final_event.status == WorkflowStatus.CANCELLED:
                cancelled_workflows += 1

            # Calculate duration if we have start and end events
            start_event = next((e for e in workflow_events if e.started_at), None)
            end_event = next((e for e in reversed(workflow_events) if e.completed_at), None)

            if start_event and end_event and start_event.started_at and end_event.completed_at:
                duration = (end_event.completed_at - start_event.started_at).total_seconds() * 1000
                durations.append(duration)

        # Calculate duration statistics
        avg_duration_ms = sum(durations) / len(durations) if durations else 0.0
        min_duration_ms = min(durations) if durations else 0.0
        max_duration_ms = max(durations) if durations else 0.0

        # Calculate 95th percentile
        if durations:
            sorted_durations = sorted(durations)
            percentile_95_index = int(0.95 * len(sorted_durations))
            percentile_95_ms = (
                sorted_durations[percentile_95_index]
                if percentile_95_index < len(sorted_durations)
                else max_duration_ms
            )
        else:
            percentile_95_ms = 0.0

        # Calculate rates
        success_rate = completed_workflows / total_workflows if total_workflows > 0 else 0.0
        failure_rate = failed_workflows / total_workflows if total_workflows > 0 else 0.0

        # Calculate throughput
        period_hours = (period_end - period_start).total_seconds() / 3600
        workflows_per_hour = total_workflows / period_hours if period_hours > 0 else 0.0

        # Error analysis
        top_errors = []
        error_categories = {}
        failed_events = [e for e in events if e.status == WorkflowStatus.FAILED and e.error_details]

        for event in failed_events:
            if event.error_details:
                error_type = event.error_details.get("type", "unknown")
                error_categories[error_type] = error_categories.get(error_type, 0) + 1

        # Convert to top errors list
        for error_type, count in sorted(error_categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            top_errors.append(
                {
                    "error_type": error_type,
                    "count": count,
                    "percentage": count / failed_workflows * 100 if failed_workflows > 0 else 0,
                }
            )

        # Step analysis (simplified)
        step_events = [e for e in events if e.step_name]
        step_success_rates = {}
        bottleneck_steps = []

        if step_events:
            # Group by step name
            steps = {}
            for event in step_events:
                step_name = event.step_name
                if step_name not in steps:
                    steps[step_name] = {"total": 0, "successful": 0, "durations": []}

                steps[step_name]["total"] += 1
                if event.status == WorkflowStatus.COMPLETED:
                    steps[step_name]["successful"] += 1

                if event.duration_ms:
                    steps[step_name]["durations"].append(event.duration_ms)

            # Calculate step metrics
            for step_name, step_data in steps.items():
                success_rate = step_data["successful"] / step_data["total"] if step_data["total"] > 0 else 0.0
                step_success_rates[step_name] = success_rate

                if step_data["durations"]:
                    avg_duration = sum(step_data["durations"]) / len(step_data["durations"])
                    bottleneck_steps.append(
                        {
                            "step_name": step_name,
                            "avg_duration_ms": avg_duration,
                            "total_executions": step_data["total"],
                            "success_rate": success_rate,
                        }
                    )

            # Sort bottlenecks by duration
            bottleneck_steps.sort(key=lambda x: x["avg_duration_ms"], reverse=True)
            bottleneck_steps = bottleneck_steps[:5]  # Top 5 bottlenecks

        return WorkflowMetrics(
            workflow_type=workflow_type,
            period_start=period_start,
            period_end=period_end,
            total_workflows=total_workflows,
            completed_workflows=completed_workflows,
            failed_workflows=failed_workflows,
            cancelled_workflows=cancelled_workflows,
            avg_duration_ms=avg_duration_ms,
            min_duration_ms=min_duration_ms,
            max_duration_ms=max_duration_ms,
            percentile_95_ms=percentile_95_ms,
            success_rate=success_rate,
            failure_rate=failure_rate,
            retry_rate=0.0,  # Would need retry tracking
            workflows_per_hour=workflows_per_hour,
            peak_concurrent=0,  # Would need concurrent tracking
            top_errors=top_errors,
            error_categories=error_categories,
            bottleneck_steps=bottleneck_steps,
            step_success_rates=step_success_rates,
            tenant_id=getattr(self.analytics_config.deployment_context, "tenant_id", None),
        )

    async def _calculate_workflow_trends(
        self,
        period_start: datetime,
        period_end: datetime,
        tenant_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Calculate workflow trends over time."""

        # Simplified trend calculation - would be more sophisticated in production
        trends = {
            "volume_trend": "increasing",
            "performance_trend": "stable",
            "success_rate_trend": "improving",
            "daily_volumes": [],
        }

        # Generate daily volume data (simplified)
        current_date = period_start.date()
        end_date = period_end.date()

        while current_date <= end_date:
            # Count workflows for this date
            day_events = [
                e
                for e in self._workflow_events
                if (e.timestamp.date() == current_date and (not tenant_id or e.tenant_id == tenant_id))
            ]

            workflows_count = len({e.workflow_id for e in day_events})

            trends["daily_volumes"].append(
                {
                    "date": current_date.isoformat(),
                    "count": workflows_count,
                }
            )

            current_date += timedelta(days=1)

        return trends

    async def _check_performance_alerts(self, event: WorkflowEvent):
        """Check for performance-related alerts."""

        if not event.duration_ms:
            return

        # Get average duration for this workflow type (simplified)
        # In production, this would use historical data
        baseline_duration = 5000  # 5 seconds baseline

        threshold = baseline_duration * self.analytics_config.duration_threshold_multiplier

        if event.duration_ms > threshold:
            await self._generate_alert(
                "performance",
                f"Slow workflow execution: {event.workflow_type.value}",
                {
                    "workflow_id": str(event.workflow_id),
                    "workflow_type": event.workflow_type.value,
                    "duration_ms": event.duration_ms,
                    "threshold_ms": threshold,
                    "step_name": event.step_name,
                },
            )

    async def _check_failure_alerts(self, event: WorkflowEvent):
        """Check for failure-related alerts."""

        await self._generate_alert(
            "failure",
            f"Workflow failed: {event.workflow_type.value}",
            {
                "workflow_id": str(event.workflow_id),
                "workflow_type": event.workflow_type.value,
                "step_name": event.step_name,
                "error_details": event.error_details,
            },
        )

    async def _generate_alert(self, alert_type: str, message: str, context: dict[str, Any]):
        """Generate an analytics alert."""

        alert = {
            "alert_id": str(uuid4()),
            "type": alert_type,
            "message": message,
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "workflow_analytics",
        }

        # Update alert count
        alerts_generated = self.get_state("alerts_generated", 0)
        self.set_state("alerts_generated", alerts_generated + 1)
        self._alerts_generated += 1

        # Publish alert
        if self.event_bus:
            await self.event_bus.publish("workflow_analytics.alert_generated", alert)

        logger.warning(f"Workflow analytics alert: {message}")


# Factory function
async def create_workflow_analytics_service(
    config: WorkflowAnalyticsConfig,
) -> WorkflowAnalyticsService:
    """Create and initialize workflow analytics service."""
    service = WorkflowAnalyticsService(config)

    # Service will be initialized by the registry
    return service
