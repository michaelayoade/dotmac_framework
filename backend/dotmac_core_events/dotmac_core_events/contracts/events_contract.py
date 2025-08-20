"""
Event API contract definitions.

Provides Pydantic models for event API requests and responses:
- Event publishing contracts
- Subscription management contracts
- Event history and replay contracts
- Topic information contracts
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from .common_schemas import EventMessage, EventMetadata, PaginationInfo, PublishResult


class PublishEventRequest(BaseModel):
    """Request model for publishing an event."""

    event_type: str = Field(..., description="Event type identifier")
    data: Dict[str, Any] = Field(..., description="Event payload data")
    partition_key: Optional[str] = Field(None, description="Partition key for routing")
    event_metadata: Optional[EventMetadata] = Field(None, description="Event metadata")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key")

    @validator("event_type")
    def validate_event_type(cls, v):
        if not v or not v.strip():
            raise ValueError("event_type cannot be empty")
        return v.strip()


class PublishEventResponse(BaseModel):
    """Response model for event publishing."""

    success: bool = Field(..., description="Whether publish was successful")
    result: Optional[PublishResult] = Field(None, description="Publish result details")
    error: Optional[str] = Field(None, description="Error message if failed")


class SubscribeRequest(BaseModel):
    """Request model for event subscription."""

    event_types: List[str] = Field(..., description="Event types to subscribe to")
    consumer_group: str = Field(..., description="Consumer group identifier")
    auto_commit: bool = Field(True, description="Auto-commit offsets")
    max_poll_records: int = Field(100, ge=1, le=1000, description="Max records per poll")
    session_timeout_ms: int = Field(30000, ge=1000, description="Session timeout in ms")
    heartbeat_interval_ms: int = Field(3000, ge=100, description="Heartbeat interval in ms")

    @validator("event_types")
    def validate_event_types(cls, v):
        if not v:
            raise ValueError("event_types cannot be empty")
        return [event_type.strip() for event_type in v if event_type.strip()]

    @validator("consumer_group")
    def validate_consumer_group(cls, v):
        if not v or not v.strip():
            raise ValueError("consumer_group cannot be empty")
        return v.strip()


class SubscribeResponse(BaseModel):
    """Response model for event subscription."""

    subscription_id: str = Field(..., description="Unique subscription identifier")
    consumer_group: str = Field(..., description="Consumer group identifier")
    event_types: List[str] = Field(..., description="Subscribed event types")
    created_at: datetime = Field(..., description="Subscription creation time")

    @validator("created_at", pre=True)
    def parse_created_at(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class UnsubscribeRequest(BaseModel):
    """Request model for unsubscribing from events."""

    subscription_id: str = Field(..., description="Subscription ID to cancel")

    @validator("subscription_id")
    def validate_subscription_id(cls, v):
        if not v or not v.strip():
            raise ValueError("subscription_id cannot be empty")
        return v.strip()


class EventHistoryRequest(BaseModel):
    """Request model for event history retrieval."""

    event_type: str = Field(..., description="Event type to retrieve")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of events")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    start_time: Optional[datetime] = Field(None, description="Start time filter")
    end_time: Optional[datetime] = Field(None, description="End time filter")

    @validator("event_type")
    def validate_event_type(cls, v):
        if not v or not v.strip():
            raise ValueError("event_type cannot be empty")
        return v.strip()

    @validator("start_time", "end_time", pre=True)
    def parse_datetime(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    @validator("end_time")
    def validate_time_range(cls, v, values):
        if v and "start_time" in values and values["start_time"]:
            if v <= values["start_time"]:
                raise ValueError("end_time must be after start_time")
        return v


class EventHistoryResponse(BaseModel):
    """Response model for event history."""

    events: List[EventMessage] = Field(..., description="Retrieved events")
    pagination: PaginationInfo = Field(..., description="Pagination information")
    total_count: int = Field(..., description="Total number of matching events")


class ReplayRequest(BaseModel):
    """Request model for event replay."""

    event_type: str = Field(..., description="Event type to replay")
    start_time: datetime = Field(..., description="Replay start time")
    end_time: datetime = Field(..., description="Replay end time")
    target_topic: Optional[str] = Field(None, description="Target topic for replayed events")
    speed_multiplier: float = Field(1.0, ge=0.1, le=100.0, description="Replay speed multiplier")

    @validator("event_type")
    def validate_event_type(cls, v):
        if not v or not v.strip():
            raise ValueError("event_type cannot be empty")
        return v.strip()

    @validator("start_time", "end_time", pre=True)
    def parse_datetime(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    @validator("end_time")
    def validate_time_range(cls, v, values):
        if "start_time" in values and values["start_time"]:
            if v <= values["start_time"]:
                raise ValueError("end_time must be after start_time")
        return v


class ReplayResponse(BaseModel):
    """Response model for event replay."""

    replay_id: str = Field(..., description="Unique replay job identifier")
    event_type: str = Field(..., description="Event type being replayed")
    start_time: datetime = Field(..., description="Replay start time")
    end_time: datetime = Field(..., description="Replay end time")
    target_topic: Optional[str] = Field(None, description="Target topic")
    speed_multiplier: float = Field(..., description="Replay speed multiplier")
    status: str = Field(..., description="Replay job status")
    created_at: datetime = Field(..., description="Replay job creation time")

    @validator("created_at", pre=True)
    def parse_created_at(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class TopicInfoResponse(BaseModel):
    """Response model for topic information."""

    topic: str = Field(..., description="Topic name")
    event_type: str = Field(..., description="Event type")
    partitions: int = Field(..., description="Number of partitions")
    replication_factor: Optional[int] = Field(None, description="Replication factor")
    retention_hours: Optional[int] = Field(None, description="Retention in hours")
    message_count: Optional[int] = Field(None, description="Total message count")
    size_bytes: Optional[int] = Field(None, description="Topic size in bytes")
    cleanup_policy: Optional[str] = Field(None, description="Cleanup policy")
    created_at: Optional[datetime] = Field(None, description="Topic creation time")

    @validator("created_at", pre=True)
    def parse_created_at(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class BatchPublishRequest(BaseModel):
    """Request model for batch event publishing."""

    events: List[PublishEventRequest] = Field(..., description="Events to publish")

    @validator("events")
    def validate_events(cls, v):
        if not v:
            raise ValueError("events cannot be empty")
        if len(v) > 100:
            raise ValueError("Cannot publish more than 100 events in a single batch")
        return v


class BatchPublishResponse(BaseModel):
    """Response model for batch event publishing."""

    total: int = Field(..., description="Total events processed")
    successful: int = Field(..., description="Successfully published events")
    failed: int = Field(..., description="Failed events")
    results: List[PublishEventResponse] = Field(..., description="Individual publish results")

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total == 0:
            return 0.0
        return self.successful / self.total


class EventStreamMessage(BaseModel):
    """Model for streaming event messages."""

    message_type: str = Field(..., description="Message type (event, heartbeat, error)")
    event: Optional[EventMessage] = Field(None, description="Event data if message_type is 'event'")
    heartbeat: Optional[Dict[str, Any]] = Field(None, description="Heartbeat data")
    error: Optional[str] = Field(None, description="Error message if message_type is 'error'")
    timestamp: datetime = Field(..., description="Message timestamp")

    @validator("timestamp", pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v
