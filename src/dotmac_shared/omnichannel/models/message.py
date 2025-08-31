"""
Message and communication models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class MessageStatus(str, Enum):
    """Message delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    BOUNCED = "bounced"


class Message(BaseModel):
    """Core message model for omnichannel communication."""

    id: str = Field(default_factory=lambda: str(uuid4()))

    # Recipients
    recipient: str = Field(..., min_length=1)
    recipients: List[str] = Field(default_factory=list)  # For bulk messages

    # Content
    subject: str = Field(default="")
    content: str = Field(..., min_length=1)

    # Channel information
    channel: str = Field(..., min_length=1)  # email, sms, whatsapp, etc.

    # Sender information
    sender_id: str = Field(..., min_length=1)
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None

    # Context
    interaction_id: Optional[str] = None
    agent_id: Optional[str] = None
    customer_id: Optional[str] = None

    # Templating
    template_id: Optional[str] = None
    template_data: Dict[str, Any] = Field(default_factory=dict)

    # Priority and routing
    priority: str = "normal"  # low, normal, high, urgent

    # Attachments
    attachments: List[Dict[str, Any]] = Field(default_factory=list)

    # Timing
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Additional data
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(
        populate_by_name=True
    )


class MessageResult(BaseModel):
    """Result of message sending operation."""

    success: bool
    message_id: Optional[str] = None
    status: MessageStatus
    channel: str

    # Timing
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    # Error handling
    failure_reason: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Provider information
    provider: Optional[str] = None
    provider_message_id: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None

    # Costs and limits
    cost: Optional[float] = None
    rate_limit_reset: Optional[datetime] = None

    # Additional data
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(
        populate_by_name=True
    )


class BulkMessageRequest(BaseModel):
    """Request for sending bulk messages."""

    messages: List[Message] = Field(..., min_length=1, max_length=1000)
    channel: str = Field(..., min_length=1)

    # Batch settings
    batch_size: int = Field(default=10, ge=1, le=100)
    delay_between_batches: int = Field(default=1, ge=0)  # seconds

    # Error handling
    stop_on_first_error: bool = False
    max_failures: Optional[int] = None

    # Timing
    scheduled_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True
    )


class BulkMessageResult(BaseModel):
    """Result of bulk message operation."""

    total_messages: int
    successful_messages: int
    failed_messages: int

    # Results per message
    results: List[MessageResult] = Field(default_factory=list)

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Summary
    success_rate: float = 0.0
    average_send_time: Optional[float] = None

    # Error summary
    error_summary: Dict[str, int] = Field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_messages == 0:
            return 0.0
        return self.successful_messages / self.total_messages * 100


class MessageTemplate(BaseModel):
    """Message template for consistent messaging."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str

    # Template metadata
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    category: Optional[str] = None

    # Template content
    subject_template: str = Field(default="")
    content_template: str = Field(..., min_length=1)

    # Channel support
    supported_channels: List[str] = Field(default_factory=list)

    # Template variables
    required_variables: List[str] = Field(default_factory=list)
    optional_variables: List[str] = Field(default_factory=list)
    sample_data: Dict[str, Any] = Field(default_factory=dict)

    # Status
    active: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Additional data
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(
        populate_by_name=True
    )
