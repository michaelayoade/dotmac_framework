"""
Workflow analytics service layer using DRY patterns.
Consolidates analytics business logic with built-in operations.
"""
from __future__ import annotations

from datetime import datetime, timedelta

# Define enums locally to avoid import dependencies
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import ValidationError
from ..services import BaseService


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowType(str, Enum):
    """Types of workflows that can be tracked."""

    CUSTOMER_ONBOARDING = "customer_onboarding"
    SERVICE_PROVISIONING = "service_provisioning"
    BILLING_PROCESS = "billing_process"
    SUPPORT_TICKET = "support_ticket"
    DEPLOYMENT = "deployment"
    MIGRATION = "migration"
    MAINTENANCE = "maintenance"


# Define metrics model locally
class WorkflowMetrics:
    """Workflow metrics data."""

    def __init__(
        self,
        workflow_type: WorkflowType,
        total_executions: int = 0,
        successful_executions: int = 0,
        failed_executions: int = 0,
        average_duration_ms: float = 0.0,
        bottleneck_steps: list[dict[str, Any]] | None = None,
    ):
        self.workflow_type = workflow_type
        self.total_executions = total_executions
        self.successful_executions = successful_executions
        self.failed_executions = failed_executions
        self.average_duration_ms = average_duration_ms
        self.bottleneck_steps = bottleneck_steps or []

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions


# Define schema types for service
class TrackWorkflowRequest:
    """Request schema for tracking workflow events."""

    def __init__(
        self,
        workflow_id: UUID,
        workflow_type: WorkflowType,
        event_type: str,
        status: WorkflowStatus,
        step_name: str | None = None,
        duration_ms: float | None = None,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        error_details: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.workflow_id = workflow_id
        self.workflow_type = workflow_type
        self.event_type = event_type
        self.status = status
        self.step_name = step_name
        self.duration_ms = duration_ms
        self.input_data = input_data or {}
        self.output_data = output_data or {}
        self.error_details = error_details
        self.metadata = metadata or {}


class WorkflowEvent:
    """Workflow event model."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class WorkflowAnalyticsService(
    BaseService[WorkflowEvent, TrackWorkflowRequest, TrackWorkflowRequest, dict]
):
    """Workflow analytics service with DRY patterns and business logic."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        super().__init__(
            db,
            tenant_id,
            create_schema=TrackWorkflowRequest,
            update_schema=TrackWorkflowRequest,
            response_schema=dict,
        )
        # Initialize in-memory storage for demo purposes (production would use database)
        self._events_cache: list[dict[str, Any]] = []

    async def _apply_create_business_rules(
        self, data: TrackWorkflowRequest
    ) -> TrackWorkflowRequest:
        """Apply business rules for workflow event tracking."""
        # Validate workflow ID
        if not data.workflow_id:
            raise ValidationError("Workflow ID is required")

        # Ensure metadata contains required fields
        if "tenant_id" not in data.metadata:
            data.metadata["tenant_id"] = self.tenant_id

        # Add timestamp if not present
        if "timestamp" not in data.metadata:
            data.metadata["timestamp"] = datetime.utcnow().isoformat()

        # Validate duration for completed events
        if data.status == WorkflowStatus.COMPLETED and not data.duration_ms:
            raise ValidationError("Duration is required for completed workflow steps")

        return data

    async def track_workflow_event(
        self,
        workflow_id: UUID,
        workflow_type: WorkflowType,
        event_type: str,
        status: WorkflowStatus,
        step_name: str | None = None,
        user_id: str | None = None,
        duration_ms: float | None = None,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        error_details: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Track a workflow event with validation and business rules."""

        # Create request object
        request = TrackWorkflowRequest(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            event_type=event_type,
            status=status,
            step_name=step_name,
            duration_ms=duration_ms,
            input_data=input_data,
            output_data=output_data,
            error_details=error_details,
            metadata=metadata,
        )

        # Apply business rules
        validated_request = await self._apply_create_business_rules(request)

        try:
            # Store event (in production this would go to database)
            event_data = {
                "workflow_id": str(validated_request.workflow_id),
                "workflow_type": validated_request.workflow_type.value,
                "event_type": validated_request.event_type,
                "status": validated_request.status.value,
                "step_name": validated_request.step_name,
                "user_id": user_id,
                "duration_ms": validated_request.duration_ms,
                "input_data": validated_request.input_data,
                "output_data": validated_request.output_data,
                "error_details": validated_request.error_details,
                "metadata": validated_request.metadata,
                "timestamp": datetime.utcnow().isoformat(),
                "tenant_id": self.tenant_id,
            }
            self._events_cache.append(event_data)

            return {
                "message": "Workflow event tracked successfully",
                "workflow_id": str(validated_request.workflow_id),
                "event_type": validated_request.event_type,
            }

        except Exception as e:
            raise ValidationError(f"Failed to track workflow event: {str(e)}") from e

    async def get_workflow_metrics(
        self,
        workflow_type: WorkflowType,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> WorkflowMetrics:
        """Get workflow metrics with business validation."""
        try:
            # Filter events by workflow type and date range
            filtered_events = [
                event
                for event in self._events_cache
                if event["workflow_type"] == workflow_type.value
                and event["tenant_id"] == self.tenant_id
            ]

            if not filtered_events:
                return WorkflowMetrics(workflow_type=workflow_type)

            # Calculate metrics
            total = len(filtered_events)
            successful = len([e for e in filtered_events if e["status"] == "completed"])
            failed = len([e for e in filtered_events if e["status"] == "failed"])

            # Calculate average duration
            durations = [e["duration_ms"] for e in filtered_events if e["duration_ms"]]
            avg_duration = sum(durations) / len(durations) if durations else 0.0

            return WorkflowMetrics(
                workflow_type=workflow_type,
                total_executions=total,
                successful_executions=successful,
                failed_executions=failed,
                average_duration_ms=avg_duration,
            )
        except Exception as e:
            raise ValidationError(f"Failed to get workflow metrics: {str(e)}") from e

    async def get_workflow_status_distribution(
        self,
        workflow_type: WorkflowType,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, int]:
        """Get workflow status distribution with validation."""
        try:
            # Filter events by workflow type
            filtered_events = [
                event
                for event in self._events_cache
                if event["workflow_type"] == workflow_type.value
                and event["tenant_id"] == self.tenant_id
            ]

            # Count by status
            distribution = {}
            for event in filtered_events:
                status = event["status"]
                distribution[status] = distribution.get(status, 0) + 1

            return distribution
        except Exception as e:
            raise ValidationError(f"Failed to get status distribution: {str(e)}") from e

    async def get_performance_bottlenecks(
        self,
        workflow_type: WorkflowType | None = None,
        user_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get performance bottlenecks with business logic."""
        try:
            # Analyze events for bottlenecks
            filtered_events = self._events_cache
            if workflow_type:
                filtered_events = [
                    event
                    for event in filtered_events
                    if event["workflow_type"] == workflow_type.value
                ]

            # Group by step_name and calculate metrics
            step_metrics = {}
            for event in filtered_events:
                if not event.get("step_name") or not event.get("duration_ms"):
                    continue

                step_name = event["step_name"]
                if step_name not in step_metrics:
                    step_metrics[step_name] = {
                        "step_name": step_name,
                        "workflow_type": event["workflow_type"],
                        "durations": [],
                        "successes": 0,
                        "total": 0,
                    }

                metrics = step_metrics[step_name]
                metrics["durations"].append(event["duration_ms"])
                metrics["total"] += 1
                if event["status"] == "completed":
                    metrics["successes"] += 1

            # Calculate bottlenecks
            bottlenecks = []
            for step_name, metrics in step_metrics.items():
                if metrics["total"] == 0:
                    continue

                avg_duration = sum(metrics["durations"]) / len(metrics["durations"])
                success_rate = metrics["successes"] / metrics["total"]
                # Impact score based on duration and frequency
                impact_score = (
                    (avg_duration / 1000) * metrics["total"] * (2 - success_rate)
                )

                bottlenecks.append(
                    {
                        "step_name": step_name,
                        "workflow_type": metrics["workflow_type"],
                        "avg_duration_ms": avg_duration,
                        "total_executions": metrics["total"],
                        "success_rate": success_rate,
                        "impact_score": int(impact_score),
                    }
                )

            # Sort by impact score and return top results
            bottlenecks.sort(key=lambda x: x["impact_score"], reverse=True)
            return bottlenecks[:limit]

        except Exception as e:
            raise ValidationError(
                f"Failed to get performance bottlenecks: {str(e)}"
            ) from e

    async def get_workflow_trends(
        self, workflow_type: WorkflowType, user_id: str, days: int = 30
    ) -> dict[str, Any]:
        """Get workflow trends over time."""
        try:
            # Filter events for the specified time period
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            filtered_events = [
                event
                for event in self._events_cache
                if event["workflow_type"] == workflow_type.value
                and event["tenant_id"] == self.tenant_id
                and datetime.fromisoformat(event["timestamp"]) >= cutoff_date
            ]

            # Group by day
            daily_metrics = {}
            for event in filtered_events:
                day = datetime.fromisoformat(event["timestamp"]).date().isoformat()
                if day not in daily_metrics:
                    daily_metrics[day] = {"total": 0, "successful": 0, "failed": 0}

                daily_metrics[day]["total"] += 1
                if event["status"] == "completed":
                    daily_metrics[day]["successful"] += 1
                elif event["status"] == "failed":
                    daily_metrics[day]["failed"] += 1

            return {
                "workflow_type": workflow_type.value,
                "period_days": days,
                "daily_trends": daily_metrics,
                "total_events": len(filtered_events),
                "summary": {
                    "avg_daily_volume": len(filtered_events) / days if days > 0 else 0,
                    "peak_day": max(daily_metrics.items(), key=lambda x: x[1]["total"])[
                        0
                    ]
                    if daily_metrics
                    else None,
                },
            }

        except Exception as e:
            raise ValidationError(f"Failed to get workflow trends: {str(e)}") from e
