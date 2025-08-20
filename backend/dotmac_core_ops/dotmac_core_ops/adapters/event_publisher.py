"""
Event publisher for workflow events with schema validation and DLQ support.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import structlog
from pydantic import ValidationError

from ..contracts.workflow_events import (
    WorkflowEventType,
    WorkflowEventPayload,
    create_workflow_event,
    EVENT_TYPE_MAPPING
)
from .schema_validator import SchemaValidator

logger = structlog.get_logger(__name__)


class EventPublishError(Exception):
    """Exception raised when event publishing fails."""
    pass


class EventPublisher:
    """
    Event publisher for workflow events with schema validation and DLQ support.

    Integrates with dotmac_core_events for reliable event publishing.
    """

    def __init__(
        self,
        event_bus_sdk,  # From dotmac_core_events
        schema_validator: Optional[SchemaValidator] = None,
        enable_dlq: bool = True,
        max_retries: int = 3
    ):
        self.event_bus = event_bus_sdk
        self.schema_validator = schema_validator
        self.enable_dlq = enable_dlq
        self.max_retries = max_retries
        self._dlq_events: List[Dict[str, Any]] = []

    async def publish_workflow_event(  # noqa: C901
        self,
        event_type: WorkflowEventType,
        payload: Union[WorkflowEventPayload, Dict[str, Any]],
        tenant_id: str,
        correlation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> bool:
        """
        Publish a workflow event with schema validation.

        Args:
            event_type: Type of workflow event
            payload: Event payload (Pydantic model or dict)
            tenant_id: Tenant ID for isolation
            correlation_id: Optional correlation ID for tracing
            idempotency_key: Optional idempotency key

        Returns:
            True if published successfully, False otherwise
        """
        try:
            # Convert dict payload to proper event model
            if isinstance(payload, dict):
                event_class = EVENT_TYPE_MAPPING.get(event_type)
                if not event_class:
                    raise EventPublishError(f"Unknown event type: {event_type}")

                # Ensure required fields are present
                if 'tenant_id' not in payload:
                    payload['tenant_id'] = tenant_id
                if 'timestamp' not in payload:
                    payload['timestamp'] = datetime.now(timezone.utc)
                if 'correlation_id' not in payload and correlation_id:
                    payload['correlation_id'] = correlation_id

                payload = event_class(**payload)

            # Validate schema if validator is available
            if self.schema_validator:
                await self.schema_validator.validate_event(event_type, payload.dict())

            # Create event envelope
            event_envelope = create_workflow_event(
                event_type=event_type,
                payload=payload,
                event_id=str(uuid.uuid4()),
                subject=payload.execution_id
            )

            # Determine topic based on event type
            topic = self._get_topic_for_event_type(event_type)

            # Publish via event bus
            result = await self.event_bus.publish(
                event_type=event_type.value,
                data=event_envelope.dict(),
                partition_key=payload.execution_id,
                metadata={
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id or payload.correlation_id,
                    "source": "dotmac-core-ops",
                    "subject": payload.execution_id
                },
                idempotency_key=idempotency_key
            )

            if result.success:
                logger.info(
                    "Published workflow event",
                    event_type=event_type.value,
                    execution_id=payload.execution_id,
                    tenant_id=tenant_id,
                    event_id=event_envelope.event_id
                )
                return True
            else:
                logger.error(
                    "Failed to publish workflow event",
                    event_type=event_type.value,
                    execution_id=payload.execution_id,
                    error=result.error
                )

                # Send to DLQ if enabled
                if self.enable_dlq:
                    await self._send_to_dlq(event_envelope, result.error)

                return False

        except ValidationError as e:
            logger.error(
                "Event validation failed",
                event_type=event_type.value,
                validation_errors=e.errors(),
                payload=payload.dict() if hasattr(payload, 'dict') else payload
            )

            # Send to DLQ for manual inspection
            if self.enable_dlq:
                await self._send_to_dlq(
                    {"event_type": event_type.value, "payload": payload},
                    f"Validation error: {str(e)}"
                )

            return False

        except Exception as e:
            logger.error(
                "Unexpected error publishing event",
                event_type=event_type.value,
                error=str(e),
                exc_info=e
            )

            if self.enable_dlq:
                await self._send_to_dlq(
                    {"event_type": event_type.value, "payload": payload},
                    f"Publish error: {str(e)}"
                )

            return False

    def _get_topic_for_event_type(self, event_type: WorkflowEventType) -> str:
        """Get the appropriate topic for an event type."""
        if event_type in [
            WorkflowEventType.WORKFLOW_STARTED,
            WorkflowEventType.WORKFLOW_COMPLETED,
            WorkflowEventType.WORKFLOW_FAILED,
            WorkflowEventType.WORKFLOW_CANCELLED
        ]:
            return "ops.workflow.lifecycle"
        elif event_type in [
            WorkflowEventType.STEP_STARTED,
            WorkflowEventType.STEP_COMPLETED,
            WorkflowEventType.STEP_FAILED,
            WorkflowEventType.STEP_RETRYING,
            WorkflowEventType.STEP_SKIPPED
        ]:
            return "ops.workflow.steps"
        elif event_type in [
            WorkflowEventType.SAGA_COMPENSATING,
            WorkflowEventType.SAGA_COMPENSATED,
            WorkflowEventType.SAGA_COMPENSATION_FAILED
        ]:
            return "ops.workflow.saga"
        else:
            return "ops.workflow.events"

    async def _send_to_dlq(self, event_data: Any, error_reason: str):
        """Send failed event to dead letter queue."""
        dlq_entry = {
            "event_id": str(uuid.uuid4()),
            "original_event": event_data,
            "error_reason": error_reason,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0
        }

        try:
            # Try to publish to DLQ topic
            await self.event_bus.publish(
                event_type="ops.workflow.dlq",
                data=dlq_entry,
                partition_key="dlq"
            )

            logger.info("Sent event to DLQ", event_id=dlq_entry["event_id"])

        except Exception as e:
            # If DLQ publishing fails, store locally for later retry
            logger.error("Failed to send to DLQ, storing locally", error=str(e))
            self._dlq_events.append(dlq_entry)

    async def replay_dlq_event(self, dlq_event_id: str) -> bool:
        """
        Replay an event from the dead letter queue.

        Args:
            dlq_event_id: ID of the DLQ event to replay

        Returns:
            True if replay was successful
        """
        try:
            # In a real implementation, this would fetch from DLQ storage
            # For now, check local DLQ events
            dlq_event = None
            for event in self._dlq_events:
                if event["event_id"] == dlq_event_id:
                    dlq_event = event
                    break

            if not dlq_event:
                logger.error("DLQ event not found", dlq_event_id=dlq_event_id)
                return False

            original_event = dlq_event["original_event"]

            # Extract event type and payload
            if isinstance(original_event, dict) and "event_type" in original_event:
                event_type = WorkflowEventType(original_event["event_type"])
                payload = original_event["payload"]

                # Retry publishing
                success = await self.publish_workflow_event(
                    event_type=event_type,
                    payload=payload,
                    tenant_id=payload.get("tenant_id", "unknown")
                )

                if success:
                    # Remove from local DLQ
                    self._dlq_events = [e for e in self._dlq_events if e["event_id"] != dlq_event_id]
                    logger.info("Successfully replayed DLQ event", dlq_event_id=dlq_event_id)
                    return True
                else:
                    # Increment retry count
                    dlq_event["retry_count"] += 1
                    logger.warning("DLQ replay failed", dlq_event_id=dlq_event_id)
                    return False

        except Exception as e:
            logger.error("Error replaying DLQ event", dlq_event_id=dlq_event_id, error=str(e))
            return False

        return False

    async def get_dlq_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from the dead letter queue."""
        # In a real implementation, this would query DLQ storage
        return self._dlq_events[:limit]

    async def publish_workflow_started(
        self,
        tenant_id: str,
        workflow_id: str,
        execution_id: str,
        input_data: Dict[str, Any],
        business_key: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Convenience method to publish workflow started event."""
        from ..contracts.workflow_events import WorkflowStartedEvent
        from ..contracts.common_schemas import OperationMetadata

        payload = WorkflowStartedEvent(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            business_key=business_key,
            correlation_id=correlation_id or str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            metadata=OperationMetadata(
                tenant_id=tenant_id,
                created_by="system",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            input_data=input_data
        )

        return await self.publish_workflow_event(
            event_type=WorkflowEventType.WORKFLOW_STARTED,
            payload=payload,
            tenant_id=tenant_id,
            correlation_id=correlation_id
        )

    async def publish_workflow_completed(
        self,
        tenant_id: str,
        workflow_id: str,
        execution_id: str,
        output_data: Dict[str, Any],
        duration_seconds: float,
        steps_executed: int,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Convenience method to publish workflow completed event."""
        from ..contracts.workflow_events import WorkflowCompletedEvent
        from ..contracts.common_schemas import OperationMetadata

        payload = WorkflowCompletedEvent(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            metadata=OperationMetadata(
                tenant_id=tenant_id,
                created_by="system",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            output_data=output_data,
            duration_seconds=duration_seconds,
            steps_executed=steps_executed
        )

        return await self.publish_workflow_event(
            event_type=WorkflowEventType.WORKFLOW_COMPLETED,
            payload=payload,
            tenant_id=tenant_id,
            correlation_id=correlation_id
        )

    async def publish_step_started(  # noqa: PLR0913
        self,
        tenant_id: str,
        workflow_id: str,
        execution_id: str,
        step_id: str,
        step_name: str,
        step_type: str,
        input_data: Dict[str, Any],
        attempt: int = 1,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Convenience method to publish step started event."""
        from ..contracts.workflow_events import StepStartedEvent
        from ..contracts.common_schemas import OperationMetadata

        payload = StepStartedEvent(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            metadata=OperationMetadata(
                tenant_id=tenant_id,
                created_by="system",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            step_id=step_id,
            step_name=step_name,
            step_type=step_type,
            attempt=attempt,
            input_data=input_data
        )

        return await self.publish_workflow_event(
            event_type=WorkflowEventType.STEP_STARTED,
            payload=payload,
            tenant_id=tenant_id,
            correlation_id=correlation_id
        )

    async def publish_step_completed(  # noqa: PLR0913
        self,
        tenant_id: str,
        workflow_id: str,
        execution_id: str,
        step_id: str,
        step_name: str,
        step_type: str,
        output_data: Dict[str, Any],
        duration_seconds: float,
        attempt: int = 1,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Convenience method to publish step completed event."""
        from ..contracts.workflow_events import StepCompletedEvent
        from ..contracts.common_schemas import OperationMetadata

        payload = StepCompletedEvent(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            metadata=OperationMetadata(
                tenant_id=tenant_id,
                created_by="system",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            step_id=step_id,
            step_name=step_name,
            step_type=step_type,
            attempt=attempt,
            output_data=output_data,
            duration_seconds=duration_seconds
        )

        return await self.publish_workflow_event(
            event_type=WorkflowEventType.STEP_COMPLETED,
            payload=payload,
            tenant_id=tenant_id,
            correlation_id=correlation_id
        )
