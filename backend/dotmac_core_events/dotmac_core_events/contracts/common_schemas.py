"""
Common schemas and data models for dotmac_core_events.

Provides shared Pydantic models for:
- Event metadata and messages
- Validation and compatibility results
- Health and metrics data
- Configuration models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class CompatibilityLevel(str, Enum):
    """Schema compatibility levels."""
    NONE = "NONE"
    BACKWARD = "BACKWARD"
    FORWARD = "FORWARD"
    FULL = "FULL"


class HealthStatus(str, Enum):
    """Health status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class EventMetadata(BaseModel):
    """Event metadata model."""

    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    causation_id: Optional[str] = Field(None, description="Causation ID for event chains")
    user_id: Optional[str] = Field(None, description="User ID who triggered the event")
    source: Optional[str] = Field(None, description="Event source system")
    version: Optional[str] = Field(None, description="Event schema version")
    tags: Optional[Dict[str, str]] = Field(None, description="Custom tags")

    class Config:
        extra = "allow"


class EventMessage(BaseModel):
    """Complete event message model."""

    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event type identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    data: Dict[str, Any] = Field(..., description="Event payload data")
    event_metadata: Optional[EventMetadata] = Field(None, description="Event metadata")
    partition_key: Optional[str] = Field(None, description="Partition key")
    timestamp: datetime = Field(..., description="Event timestamp")
    version: str = Field("1.0", description="Message format version")

    @validator("timestamp", pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class PublishResult(BaseModel):
    """Event publish result model."""

    event_id: str = Field(..., description="Published event ID")
    partition: Optional[int] = Field(None, description="Assigned partition")
    offset: Optional[int] = Field(None, description="Message offset")
    timestamp: datetime = Field(..., description="Publish timestamp")
    topic: Optional[str] = Field(None, description="Target topic")

    @validator("timestamp", pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class SubscriptionConfig(BaseModel):
    """Event subscription configuration."""

    event_types: List[str] = Field(..., description="Event types to subscribe to")
    consumer_group: str = Field(..., description="Consumer group identifier")
    auto_commit: bool = Field(True, description="Auto-commit offsets")
    max_poll_records: int = Field(100, ge=1, le=1000, description="Max records per poll")
    session_timeout_ms: int = Field(30000, ge=1000, description="Session timeout in ms")
    heartbeat_interval_ms: int = Field(3000, ge=100, description="Heartbeat interval in ms")

    @validator("max_poll_records")
    def validate_max_poll_records(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("max_poll_records must be between 1 and 1000")
        return v


class ValidationResult(BaseModel):
    """Schema validation result model."""

    valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    schema_version: Optional[str] = Field(None, description="Schema version used")

    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.valid and len(self.errors) == 0


class ComponentHealth(BaseModel):
    """Individual component health status."""

    name: str = Field(..., description="Component name")
    status: HealthStatus = Field(..., description="Health status")
    message: Optional[str] = Field(None, description="Status message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    last_check: datetime = Field(..., description="Last health check time")

    @validator("last_check", pre=True)
    def parse_last_check(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class MetricsData(BaseModel):
    """Metrics data model."""

    name: str = Field(..., description="Metric name")
    value: Union[int, float] = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Metric unit")
    tags: Optional[Dict[str, str]] = Field(None, description="Metric tags")
    timestamp: datetime = Field(..., description="Metric timestamp")

    @validator("timestamp", pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class SchemaInfo(BaseModel):
    """Schema information model."""

    event_type: str = Field(..., description="Event type identifier")
    version: str = Field(..., description="Schema version")
    schema: Dict[str, Any] = Field(..., description="JSON schema definition")
    compatibility_level: CompatibilityLevel = Field(..., description="Compatibility level")
    created_at: datetime = Field(..., description="Schema creation time")
    created_by: Optional[str] = Field(None, description="Schema creator")

    @validator("created_at", pre=True)
    def parse_created_at(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class ConsumerGroupState(BaseModel):
    """Consumer group state model."""

    group_id: str = Field(..., description="Consumer group ID")
    state: str = Field(..., description="Group state")
    protocol_type: Optional[str] = Field(None, description="Protocol type")
    protocol: Optional[str] = Field(None, description="Protocol name")
    members: List[Dict[str, Any]] = Field(default_factory=list, description="Group members")
    coordinator: Optional[str] = Field(None, description="Group coordinator")


class TopicMetrics(BaseModel):
    """Topic metrics model."""

    topic: str = Field(..., description="Topic name")
    partition_count: int = Field(..., description="Number of partitions")
    message_count: int = Field(0, description="Total message count")
    size_bytes: int = Field(0, description="Topic size in bytes")
    retention_ms: Optional[int] = Field(None, description="Retention time in ms")
    cleanup_policy: Optional[str] = Field(None, description="Cleanup policy")


class ErrorInfo(BaseModel):
    """Error information model."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(..., description="Error timestamp")

    @validator("timestamp", pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class PaginationInfo(BaseModel):
    """Pagination information model."""

    page: int = Field(1, ge=1, description="Current page number")
    per_page: int = Field(100, ge=1, le=1000, description="Items per page")
    total: int = Field(0, ge=0, description="Total number of items")
    pages: int = Field(0, ge=0, description="Total number of pages")
    has_next: bool = Field(False, description="Whether there is a next page")
    has_prev: bool = Field(False, description="Whether there is a previous page")


class BatchResult(BaseModel):
    """Batch operation result model."""

    total: int = Field(..., description="Total items processed")
    successful: int = Field(..., description="Successfully processed items")
    failed: int = Field(..., description="Failed items")
    errors: List[ErrorInfo] = Field(default_factory=list, description="Error details")

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total == 0:
            return 0.0
        return self.successful / self.total
