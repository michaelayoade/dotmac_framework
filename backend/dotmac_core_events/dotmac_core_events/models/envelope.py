"""
Standard event envelope schema for all topics.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class EventEnvelope(BaseModel):
    """
    Standard envelope for all events across the platform.

    Format: {domain}.{entity}.{event}.v{version}
    Examples:
    - svc.activation.requested.v1
    - prov.cpe.provisioned.v1
    - ops.workflow.started.v1
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event identifier (UUID)"
    )

    type: str = Field(
        ...,
        description="Event type in format: {domain}.{entity}.{event}.v{version}",
        regex=r"^[a-z]+\.[a-z_]+\.[a-z_]+\.v\d+$"
    )

    schema_version: str = Field(
        default="1",
        description="Schema version for this envelope format"
    )

    tenant_id: str = Field(
        ...,
        description="Tenant identifier (UUID)"
    )

    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the event occurred (RFC3339)"
    )

    trace_id: Optional[str] = Field(
        default=None,
        description="Distributed tracing identifier"
    )

    data: Dict[str, Any] = Field(
        ...,
        description="Event-specific payload data"
    )

    # Optional metadata fields
    source: Optional[str] = Field(
        default=None,
        description="Event source service/component"
    )

    correlation_id: Optional[str] = Field(
        default=None,
        description="Correlation ID for request tracking"
    )

    causation_id: Optional[str] = Field(
        default=None,
        description="ID of the event that caused this event"
    )

    version: Optional[str] = Field(
        default=None,
        description="Event data version (separate from envelope schema_version)"
    )

    @validator("tenant_id")
    def validate_tenant_id(cls, v):
        """Validate tenant_id is a valid UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("tenant_id must be a valid UUID")

    @validator("id")
    def validate_id(cls, v):
        """Validate id is a valid UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("id must be a valid UUID")

    @validator("data")
    def validate_data_has_partition_key(cls, v, values):
        """Validate data contains required partition key for ordering."""
        # Check for common partition keys
        partition_keys = ["service_id", "device_id", "customer_id", "site_id"]

        # Allow explicit partition_key field
        if "partition_key" in v:
            return v

        # Check for standard partition keys
        if any(key in v for key in partition_keys):
            return v

        # For some event types, partition key might not be required
        event_type = values.get("type", "")
        if any(pattern in event_type for pattern in ["system.", "admin.", "health."]):
            return v

        raise ValueError(
            f"Data must contain a partition key (one of: {partition_keys}) "
            f"or explicit 'partition_key' field for ordered events"
        )

    def get_partition_key(self) -> Optional[str]:
        """Extract partition key from data for message ordering."""
        # Explicit partition key
        if "partition_key" in self.data:
            return str(self.data["partition_key"])

        # Standard partition keys in priority order
        for key in ["service_id", "device_id", "customer_id", "site_id"]:
            if key in self.data:
                return str(self.data[key])

        # Fallback to tenant_id for global ordering
        return self.tenant_id

    def get_topic_name(self) -> str:
        """Get topic name from event type."""
        # Remove version suffix for topic name
        return self.type.rsplit(".v", 1)[0]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.dict(by_alias=True)

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "svc.activation.requested.v1",
                "schema_version": "1",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                "occurred_at": "2023-12-07T10:30:00Z",
                "trace_id": "abc123def456",
                "data": {
                    "service_id": "svc_789",
                    "customer_id": "cust_456",
                    "activation_type": "immediate",
                    "parameters": {
                        "bandwidth": "100Mbps",
                        "vlan": 100
                    }
                },
                "source": "service-management-api",
                "correlation_id": "req_12345"
            }
        }


class EventMetadata(BaseModel):
    """Additional metadata for event processing."""

    published_at: Optional[datetime] = Field(
        default=None,
        description="When the event was published to the bus"
    )

    received_at: Optional[datetime] = Field(
        default=None,
        description="When the event was received by consumer"
    )

    retry_count: int = Field(
        default=0,
        description="Number of processing retries"
    )

    consumer_group: Optional[str] = Field(
        default=None,
        description="Consumer group processing this event"
    )

    processing_duration_ms: Optional[int] = Field(
        default=None,
        description="Time taken to process event in milliseconds"
    )


# Common event types for the platform
class EventTypes:
    """Standard event type constants."""

    # Service events
    SERVICE_ACTIVATION_REQUESTED = "svc.activation.requested.v1"
    SERVICE_ACTIVATION_COMPLETED = "svc.activation.completed.v1"
    SERVICE_ACTIVATION_FAILED = "svc.activation.failed.v1"
    SERVICE_SUSPENDED = "svc.lifecycle.suspended.v1"
    SERVICE_RESUMED = "svc.lifecycle.resumed.v1"
    SERVICE_TERMINATED = "svc.lifecycle.terminated.v1"

    # Provisioning events
    CPE_PROVISIONING_STARTED = "prov.cpe.started.v1"
    CPE_PROVISIONED = "prov.cpe.provisioned.v1"
    CPE_PROVISIONING_FAILED = "prov.cpe.failed.v1"

    # Workflow events
    WORKFLOW_STARTED = "ops.workflow.started.v1"
    WORKFLOW_COMPLETED = "ops.workflow.completed.v1"
    WORKFLOW_FAILED = "ops.workflow.failed.v1"
    WORKFLOW_STEP_STARTED = "ops.workflow.step_started.v1"
    WORKFLOW_STEP_COMPLETED = "ops.workflow.step_completed.v1"
    WORKFLOW_STEP_FAILED = "ops.workflow.step_failed.v1"

    # Billing events
    BILLING_CYCLE_STARTED = "billing.cycle.started.v1"
    BILLING_INVOICE_GENERATED = "billing.invoice.generated.v1"
    BILLING_PAYMENT_RECEIVED = "billing.payment.received.v1"

    # Customer events
    CUSTOMER_CREATED = "customer.lifecycle.created.v1"
    CUSTOMER_UPDATED = "customer.lifecycle.updated.v1"
    CUSTOMER_SUSPENDED = "customer.lifecycle.suspended.v1"

    # System events
    SYSTEM_HEALTH_CHECK = "system.health.check.v1"
    SYSTEM_ALERT_TRIGGERED = "system.alert.triggered.v1"
    SYSTEM_MAINTENANCE_STARTED = "system.maintenance.started.v1"


def create_event_envelope(
    event_type: str,
    tenant_id: str,
    data: Dict[str, Any],
    trace_id: Optional[str] = None,
    source: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> EventEnvelope:
    """
    Convenience function to create a standard event envelope.

    Args:
        event_type: Event type (e.g., "svc.activation.requested.v1")
        tenant_id: Tenant identifier
        data: Event payload data
        trace_id: Optional trace ID for distributed tracing
        source: Optional source service/component
        correlation_id: Optional correlation ID

    Returns:
        EventEnvelope instance
    """
    return EventEnvelope(
        type=event_type,
        tenant_id=tenant_id,
        data=data,
        trace_id=trace_id,
        source=source,
        correlation_id=correlation_id
    )
