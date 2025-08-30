"""
Core event models and data structures.

Pydantic v2 compatible models for event streaming, metadata, and configuration.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

logger = structlog.get_logger(__name__)


# Exceptions
class EventBusError(Exception):
    """Base exception for Event Bus operations."""

    pass


class PublishError(EventBusError):
    """Exception raised when event publishing fails."""

    pass


class SubscriptionError(EventBusError):
    """Exception raised when subscription operations fail."""

    pass


class ValidationError(EventBusError):
    """Exception raised when event validation fails."""

    pass


# Core Models
class EventMetadata(BaseModel):
    """
    Event metadata for tracing, correlation, and routing.

    Supports distributed tracing, multi-tenancy, and event correlation.
    """

    model_config = ConfigDict(
        extra="allow", str_strip_whitespace=True, validate_assignment=True
    )

    # Tracing and correlation
    event_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique event identifier"
    )
    correlation_id: Optional[str] = Field(
        default=None, description="Correlation ID for request tracing"
    )
    causation_id: Optional[str] = Field(
        default=None, description="ID of event that caused this event"
    )
    trace_id: Optional[str] = Field(default=None, description="Distributed trace ID")
    span_id: Optional[str] = Field(default=None, description="Trace span ID")

    # Context
    source: Optional[str] = Field(default=None, description="Source service/system")
    user_id: Optional[str] = Field(
        default=None, description="User who triggered the event"
    )
    tenant_id: Optional[str] = Field(
        default=None, description="Tenant identifier for multi-tenancy"
    )
    session_id: Optional[str] = Field(default=None, description="Session identifier")

    # Routing
    partition_key: Optional[str] = Field(
        default=None, description="Partition key for event routing"
    )
    routing_key: Optional[str] = Field(
        default=None, description="Routing key for message routing"
    )

    # Timing
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Event creation timestamp"
    )
    expires_at: Optional[datetime] = Field(
        default=None, description="Event expiration timestamp"
    )

    # Custom headers
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Additional headers"
    )

    @field_validator(
        "event_id", "correlation_id", "causation_id", "trace_id", "span_id"
    )
    @classmethod
    def validate_ids(cls, v):
        """Validate ID formats."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("IDs cannot be empty strings")
        return v

    @field_validator("tenant_id", "user_id", "session_id")
    @classmethod
    def validate_context_ids(cls, v):
        """Validate context ID formats."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Context IDs cannot be empty strings")
        return v


class EventRecord(BaseModel):
    """
    Core event record model.

    Represents a single event with its data, metadata, and routing information.
    """

    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, str_strip_whitespace=True
    )

    # Core event data
    event_type: str = Field(
        ..., min_length=1, max_length=100, description="Event type identifier"
    )
    data: Dict[str, Any] = Field(..., description="Event payload data")

    # Metadata
    metadata: EventMetadata = Field(
        default_factory=EventMetadata, description="Event metadata"
    )

    # Routing and partitioning
    partition_key: Optional[str] = Field(
        default=None, description="Partition key override"
    )
    topic: Optional[str] = Field(default=None, description="Target topic/stream")

    # Timestamps (set by adapters)
    timestamp: Optional[datetime] = Field(
        default=None, description="Event timestamp from broker"
    )

    # Adapter-specific fields (set by consumers)
    offset: Optional[str] = Field(
        default=None, description="Event offset in stream/topic"
    )
    partition: Optional[int] = Field(default=None, description="Partition number")

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v):
        """Validate event type format."""
        if not v or not v.strip():
            raise ValueError("Event type cannot be empty")

        # Event type should follow domain.entity.action pattern (recommended)
        parts = v.split(".")
        if len(parts) < 2:
            logger.warning(
                "Event type should follow 'domain.entity.action' pattern", event_type=v
            )

        return v.strip()

    @field_validator("data")
    @classmethod
    def validate_data(cls, v):
        """Validate event data."""
        if not isinstance(v, dict):
            raise ValueError("Event data must be a dictionary")
        return v

    @property
    def event_id(self) -> str:
        """Get event ID from metadata."""
        return self.metadata.event_id

    @property
    def tenant_id(self) -> Optional[str]:
        """Get tenant ID from metadata."""
        return self.metadata.tenant_id


class PublishResult(BaseModel):
    """
    Result of publishing an event to the event bus.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(..., description="Published event ID")
    topic: Optional[str] = Field(
        default=None, description="Topic where event was published"
    )
    partition: Optional[int] = Field(default=None, description="Partition number")
    offset: Optional[str] = Field(default=None, description="Event offset in topic")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Publish timestamp"
    )
    success: bool = Field(default=True, description="Whether publish was successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ConsumerRecord(BaseModel):
    """
    Event record as received by a consumer.

    Includes additional consumer-specific metadata.
    """

    model_config = ConfigDict(extra="forbid")

    event: EventRecord = Field(..., description="The consumed event")
    consumer_group: str = Field(..., description="Consumer group name")
    consumer_id: str = Field(..., description="Consumer identifier")
    topic: str = Field(..., description="Topic name")
    partition: int = Field(..., description="Partition number")
    offset: str = Field(..., description="Message offset")
    timestamp: datetime = Field(..., description="Consumption timestamp")
    lag: Optional[int] = Field(default=None, description="Consumer lag")


class AdapterConfig(BaseModel):
    """
    Base configuration for event adapters.
    """

    model_config = ConfigDict(extra="allow")

    # Connection
    connection_string: str = Field(..., description="Connection string for the adapter")
    timeout_seconds: int = Field(
        default=30, ge=1, le=300, description="Connection timeout"
    )

    # Retry configuration
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts"
    )
    retry_backoff_seconds: float = Field(
        default=1.0, ge=0.1, le=60.0, description="Retry backoff"
    )

    # Performance
    batch_size: int = Field(
        default=100, ge=1, le=1000, description="Batch size for operations"
    )
    buffer_size: int = Field(default=1000, ge=100, le=10000, description="Buffer size")

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable adapter metrics")
    metrics_prefix: str = Field(default="dotmac_events", description="Metrics prefix")

    @field_validator("connection_string")
    @classmethod
    def validate_connection_string(cls, v):
        """Validate connection string is not empty."""
        if not v or not v.strip():
            raise ValueError("Connection string cannot be empty")
        return v.strip()


class TopicConfig(BaseModel):
    """
    Configuration for event topics/streams.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100, description="Topic name")
    partitions: int = Field(default=1, ge=1, le=100, description="Number of partitions")
    replication_factor: int = Field(
        default=1, ge=1, le=10, description="Replication factor"
    )
    retention_ms: Optional[int] = Field(
        default=None, ge=3600000, description="Retention in milliseconds"
    )
    max_message_bytes: int = Field(
        default=1048576, ge=1024, le=10485760, description="Max message size"
    )

    @field_validator("name")
    @classmethod
    def validate_topic_name(cls, v):
        """Validate topic name format."""
        if not v or not v.strip():
            raise ValueError("Topic name cannot be empty")

        # Topic names should be alphanumeric with hyphens/underscores
        import re

        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError(
                "Topic name can only contain alphanumeric characters, dots, hyphens, and underscores"
            )

        return v.strip()


class ConsumerConfig(BaseModel):
    """
    Configuration for event consumers.
    """

    model_config = ConfigDict(extra="forbid")

    consumer_group: str = Field(..., min_length=1, description="Consumer group name")
    consumer_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Consumer instance ID"
    )
    topics: List[str] = Field(..., min_length=1, description="Topics to consume")
    auto_offset_reset: str = Field(
        default="latest",
        pattern="^(earliest|latest)$",
        description="Offset reset policy",
    )
    max_poll_records: int = Field(
        default=500, ge=1, le=10000, description="Max records per poll"
    )
    session_timeout_ms: int = Field(
        default=30000, ge=1000, le=300000, description="Session timeout"
    )
    enable_auto_commit: bool = Field(default=False, description="Enable auto commit")

    @field_validator("consumer_group")
    @classmethod
    def validate_consumer_group(cls, v):
        """Validate consumer group name."""
        if not v or not v.strip():
            raise ValueError("Consumer group cannot be empty")
        return v.strip()

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v):
        """Validate topic list."""
        if not v:
            raise ValueError("Must specify at least one topic")

        cleaned = [topic.strip() for topic in v if topic.strip()]
        if not cleaned:
            raise ValueError("All topics cannot be empty strings")

        return cleaned
