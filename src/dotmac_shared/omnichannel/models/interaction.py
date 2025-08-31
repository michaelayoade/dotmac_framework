"""
Interaction management models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class InteractionPriority(str, Enum):
    """Interaction priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class InteractionStatus(str, Enum):
    """Interaction status states."""

    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    WAITING_VENDOR = "waiting_vendor"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class InteractionMessage(BaseModel):
    """Message within an interaction."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    interaction_id: str
    content: str = Field(..., min_length=1)
    sender_id: str
    sender_name: str
    sender_type: str = "customer"  # customer, agent, system
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    message_type: str = "text"  # text, attachment, system_note
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(
        populate_by_name=True
    )


class InteractionModel(BaseModel):
    """Core interaction model."""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    customer_id: UUID

    # Content
    channel: str = Field(..., min_length=1)
    subject: str = Field(default="")
    content: str = Field(..., min_length=1)

    # Classification
    priority: InteractionPriority = InteractionPriority.MEDIUM
    status: InteractionStatus = InteractionStatus.OPEN
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Assignment
    assigned_to_id: Optional[UUID] = None
    assigned_to_name: Optional[str] = None
    assigned_team: Optional[str] = None

    # Tracking
    source: str = "customer_portal"
    thread_id: str
    conversation_id: Optional[str] = None

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None

    sla_breach_time: Optional[datetime] = None
    response_time_minutes: Optional[int] = None
    resolution_time_minutes: Optional[int] = None

    # Communication
    messages: List[InteractionMessage] = Field(default_factory=list)

    # Escalation
    escalation_level: int = 0
    escalation_reason: Optional[str] = None
    escalated_to: Optional[str] = None

    # Resolution
    resolution_summary: Optional[str] = None
    customer_satisfied: Optional[bool] = None
    satisfaction_score: Optional[int] = None

    # Additional data - using alias to avoid SQLAlchemy conflict
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(
        populate_by_name=True
    )


class CreateInteractionRequest(BaseModel):
    """Request to create a new interaction."""

    customer_id: UUID
    channel: str = Field(..., min_length=1)
    subject: str = Field(default="")
    content: str = Field(..., min_length=1)
    priority: InteractionPriority = InteractionPriority.MEDIUM
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: str = "customer_portal"
    due_date: Optional[datetime] = None
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(
        populate_by_name=True
    )


class UpdateInteractionRequest(BaseModel):
    """Request to update an interaction."""

    subject: Optional[str] = Field(None, min_length=1)
    content: Optional[str] = Field(None, min_length=1)
    priority: Optional[InteractionPriority] = None
    status: Optional[InteractionStatus] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    assigned_to_id: Optional[UUID] = None
    assigned_team: Optional[str] = None
    due_date: Optional[datetime] = None
    resolution_summary: Optional[str] = None
    customer_satisfied: Optional[bool] = None
    satisfaction_score: Optional[int] = Field(None, ge=1, le=5)
    extra_data: Optional[Dict[str, Any]] = Field(None, alias="metadata")

    model_config = ConfigDict(
        populate_by_name=True
    )
