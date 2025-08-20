"""
AsyncAPI contracts for workflow events and operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

from .common_schemas import OperationMetadata


class WorkflowEventType(str, Enum):
    """Workflow event types for AsyncAPI topics."""

    # Workflow lifecycle events
    WORKFLOW_STARTED = "ops.workflow.started"
    WORKFLOW_COMPLETED = "ops.workflow.completed"
    WORKFLOW_FAILED = "ops.workflow.failed"
    WORKFLOW_CANCELLED = "ops.workflow.cancelled"

    # Step lifecycle events
    STEP_STARTED = "ops.workflow.step.started"
    STEP_COMPLETED = "ops.workflow.step.completed"
    STEP_FAILED = "ops.workflow.step.failed"
    STEP_RETRYING = "ops.workflow.step.retrying"
    STEP_SKIPPED = "ops.workflow.step.skipped"

    # Saga events
    SAGA_COMPENSATING = "ops.workflow.saga.compensating"
    SAGA_COMPENSATED = "ops.workflow.saga.compensated"
    SAGA_COMPENSATION_FAILED = "ops.workflow.saga.compensation_failed"


class WorkflowEventPayload(BaseModel):
    """Base payload for workflow events."""

    tenant_id: str = Field(..., description="Tenant identifier")
    workflow_id: str = Field(..., description="Workflow definition ID")
    execution_id: str = Field(..., description="Workflow execution ID")
    business_key: Optional[str] = Field(None, description="Business key for idempotency")
    correlation_id: str = Field(..., description="Correlation ID for tracing")
    timestamp: datetime = Field(..., description="Event timestamp")
    metadata: OperationMetadata = Field(..., description="Operation metadata")


class WorkflowStartedEvent(WorkflowEventPayload):
    """Event published when a workflow execution starts."""

    event_type: str = Field(WorkflowEventType.WORKFLOW_STARTED, const=True)
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Workflow input data")
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled execution time")


class WorkflowCompletedEvent(WorkflowEventPayload):
    """Event published when a workflow execution completes successfully."""

    event_type: str = Field(WorkflowEventType.WORKFLOW_COMPLETED, const=True)
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Workflow output data")
    duration_seconds: float = Field(..., description="Execution duration in seconds")
    steps_executed: int = Field(..., description="Number of steps executed")


class WorkflowFailedEvent(WorkflowEventPayload):
    """Event published when a workflow execution fails."""

    event_type: str = Field(WorkflowEventType.WORKFLOW_FAILED, const=True)
    error_message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    failed_step_id: Optional[str] = Field(None, description="ID of the step that failed")
    retry_count: int = Field(0, description="Number of retries attempted")
    is_retryable: bool = Field(True, description="Whether the failure is retryable")


class WorkflowCancelledEvent(WorkflowEventPayload):
    """Event published when a workflow execution is cancelled."""

    event_type: str = Field(WorkflowEventType.WORKFLOW_CANCELLED, const=True)
    cancelled_by: str = Field(..., description="User or system that cancelled the workflow")
    reason: Optional[str] = Field(None, description="Cancellation reason")
    steps_completed: int = Field(..., description="Number of steps completed before cancellation")


class StepEventPayload(WorkflowEventPayload):
    """Base payload for step events."""

    step_id: str = Field(..., description="Step identifier")
    step_name: str = Field(..., description="Step name")
    step_type: str = Field(..., description="Step type (action, condition, etc.)")
    attempt: int = Field(1, description="Attempt number (1-based)")


class StepStartedEvent(StepEventPayload):
    """Event published when a step starts execution."""

    event_type: str = Field(WorkflowEventType.STEP_STARTED, const=True)
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Step input data")
    dependencies_completed: List[str] = Field(default_factory=list, description="Completed dependency step IDs")


class StepCompletedEvent(StepEventPayload):
    """Event published when a step completes successfully."""

    event_type: str = Field(WorkflowEventType.STEP_COMPLETED, const=True)
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Step output data")
    duration_seconds: float = Field(..., description="Step execution duration in seconds")


class StepFailedEvent(StepEventPayload):
    """Event published when a step fails."""

    event_type: str = Field(WorkflowEventType.STEP_FAILED, const=True)
    error_message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    is_retryable: bool = Field(True, description="Whether the step failure is retryable")
    next_retry_at: Optional[datetime] = Field(None, description="Next retry timestamp")


class StepRetryingEvent(StepEventPayload):
    """Event published when a step is being retried."""

    event_type: str = Field(WorkflowEventType.STEP_RETRYING, const=True)
    previous_error: str = Field(..., description="Previous error message")
    retry_delay_seconds: float = Field(..., description="Delay before retry in seconds")
    max_retries: int = Field(..., description="Maximum number of retries")


class StepSkippedEvent(StepEventPayload):
    """Event published when a step is skipped."""

    event_type: str = Field(WorkflowEventType.STEP_SKIPPED, const=True)
    skip_reason: str = Field(..., description="Reason for skipping the step")
    condition_result: Optional[Dict[str, Any]] = Field(None, description="Condition evaluation result")


class SagaCompensatingEvent(WorkflowEventPayload):
    """Event published when saga compensation starts."""

    event_type: str = Field(WorkflowEventType.SAGA_COMPENSATING, const=True)
    failed_step_id: str = Field(..., description="ID of the step that triggered compensation")
    compensation_steps: List[str] = Field(..., description="List of steps to compensate")
    compensation_reason: str = Field(..., description="Reason for compensation")


class SagaCompensatedEvent(WorkflowEventPayload):
    """Event published when saga compensation completes successfully."""

    event_type: str = Field(WorkflowEventType.SAGA_COMPENSATED, const=True)
    compensated_steps: List[str] = Field(..., description="List of successfully compensated steps")
    compensation_duration_seconds: float = Field(..., description="Compensation duration in seconds")


class SagaCompensationFailedEvent(WorkflowEventPayload):
    """Event published when saga compensation fails."""

    event_type: str = Field(WorkflowEventType.SAGA_COMPENSATION_FAILED, const=True)
    failed_compensation_step: str = Field(..., description="Step that failed during compensation")
    error_message: str = Field(..., description="Compensation error message")
    partial_compensation: List[str] = Field(default_factory=list, description="Steps that were successfully compensated")


# Event type mapping for serialization/deserialization
EVENT_TYPE_MAPPING = {
    WorkflowEventType.WORKFLOW_STARTED: WorkflowStartedEvent,
    WorkflowEventType.WORKFLOW_COMPLETED: WorkflowCompletedEvent,
    WorkflowEventType.WORKFLOW_FAILED: WorkflowFailedEvent,
    WorkflowEventType.WORKFLOW_CANCELLED: WorkflowCancelledEvent,
    WorkflowEventType.STEP_STARTED: StepStartedEvent,
    WorkflowEventType.STEP_COMPLETED: StepCompletedEvent,
    WorkflowEventType.STEP_FAILED: StepFailedEvent,
    WorkflowEventType.STEP_RETRYING: StepRetryingEvent,
    WorkflowEventType.STEP_SKIPPED: StepSkippedEvent,
    WorkflowEventType.SAGA_COMPENSATING: SagaCompensatingEvent,
    WorkflowEventType.SAGA_COMPENSATED: SagaCompensatedEvent,
    WorkflowEventType.SAGA_COMPENSATION_FAILED: SagaCompensationFailedEvent,
}


class WorkflowEventEnvelope(BaseModel):
    """Event envelope for workflow events with metadata."""

    event_id: str = Field(..., description="Unique event identifier")
    event_type: WorkflowEventType = Field(..., description="Event type")
    event_version: str = Field("1.0", description="Event schema version")
    source: str = Field("dotmac-core-ops", description="Event source")
    subject: str = Field(..., description="Event subject (workflow/execution ID)")
    time: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event payload")

    # CloudEvents compatibility
    specversion: str = Field("1.0", description="CloudEvents spec version")
    datacontenttype: str = Field("application/json", description="Data content type")

    class Config:
        extra = "allow"  # Allow additional CloudEvents attributes


def create_workflow_event(
    event_type: WorkflowEventType,
    payload: WorkflowEventPayload,
    event_id: Optional[str] = None,
    subject: Optional[str] = None
) -> WorkflowEventEnvelope:
    """
    Create a workflow event envelope.

    Args:
        event_type: Type of the event
        payload: Event payload
        event_id: Optional event ID (generated if not provided)
        subject: Optional subject (defaults to execution_id)

    Returns:
        Event envelope ready for publishing
    """
    import uuid

    if event_id is None:
        event_id = str(uuid.uuid4())

    if subject is None:
        subject = payload.execution_id

    return WorkflowEventEnvelope(
        event_id=event_id,
        event_type=event_type,
        subject=subject,
        time=payload.timestamp,
        data=payload.dict()
    )
