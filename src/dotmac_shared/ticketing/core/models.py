"""
Core ticketing models for universal ticket management.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class TicketStatus(str, Enum):
    """Ticket status enumeration."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    WAITING_FOR_VENDOR = "waiting_for_vendor"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TicketPriority(str, Enum):
    """Ticket priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TicketCategory(str, Enum):
    """Ticket categories."""

    TECHNICAL_SUPPORT = "technical_support"
    BILLING_INQUIRY = "billing_inquiry"
    SERVICE_REQUEST = "service_request"
    NETWORK_ISSUE = "network_issue"
    ACCOUNT_MANAGEMENT = "account_management"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    COMPLIANCE = "compliance"
    SECURITY_INCIDENT = "security_incident"
    OTHER = "other"


class TicketSource(str, Enum):
    """How the ticket was created."""

    CUSTOMER_PORTAL = "customer_portal"
    ADMIN_PORTAL = "admin_portal"
    EMAIL = "email"
    PHONE = "phone"
    CHAT = "chat"
    API = "api"
    AUTOMATION = "automation"
    ESCALATION = "escalation"


class Ticket(Base):
    """Core ticket model."""

    __tablename__ = "tickets"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    ticket_number = Column(String, unique=True, nullable=False, index=True)

    # Basic ticket information
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default=TicketStatus.OPEN, nullable=False, index=True)
    priority = Column(String, default=TicketPriority.NORMAL, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    source = Column(String, default=TicketSource.CUSTOMER_PORTAL, nullable=False)

    # Customer information
    customer_id = Column(String, nullable=True, index=True)
    customer_email = Column(String, nullable=True, index=True)
    customer_name = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)

    # Assignment information
    assigned_to_id = Column(String, nullable=True, index=True)
    assigned_to_name = Column(String, nullable=True)
    assigned_team = Column(String, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)

    # Service Level Agreement
    sla_breach_time = Column(DateTime, nullable=True)
    response_time_minutes = Column(Integer, nullable=True)
    resolution_time_minutes = Column(Integer, nullable=True)

    # Metadata
    tags = Column(JSON, default=list)
    extra_data = Column(
        JSON, default=dict
    )  # Renamed from metadata to avoid SQLAlchemy conflict
    external_references = Column(JSON, default=dict)  # Links to other systems

    # Relationships
    comments = relationship(
        "TicketComment", back_populates="ticket", cascade="all, delete-orphan"
    )
    attachments = relationship(
        "TicketAttachment", back_populates="ticket", cascade="all, delete-orphan"
    )
    escalations = relationship(
        "TicketEscalation", back_populates="ticket", cascade="all, delete-orphan"
    )


class TicketComment(Base):
    """Ticket comment/note model."""

    __tablename__ = "ticket_comments"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Comment content
    content = Column(Text, nullable=False)
    is_internal = Column(
        Boolean, default=False, nullable=False
    )  # Internal notes vs customer-visible
    is_solution = Column(Boolean, default=False, nullable=False)  # Mark as solution

    # Author information
    author_id = Column(String, nullable=True, index=True)
    author_name = Column(String, nullable=False)
    author_email = Column(String, nullable=True)
    author_type = Column(String, default="staff")  # staff, customer, system

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Additional data
    extra_data = Column(
        JSON, default=dict
    )  # Renamed from metadata to avoid SQLAlchemy conflict

    # Relationships
    ticket = relationship("Ticket", back_populates="comments")


class TicketAttachment(Base):
    """Ticket attachment model."""

    __tablename__ = "ticket_attachments"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # File information
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)  # Storage path
    file_url = Column(String, nullable=True)  # Download URL

    # Upload information
    uploaded_by_id = Column(String, nullable=True, index=True)
    uploaded_by_name = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Additional data
    extra_data = Column(
        JSON, default=dict
    )  # Renamed from metadata to avoid SQLAlchemy conflict

    # Relationships
    ticket = relationship("Ticket", back_populates="attachments")


class TicketEscalation(Base):
    """Ticket escalation tracking."""

    __tablename__ = "ticket_escalations"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Escalation details
    escalation_level = Column(Integer, default=1, nullable=False)  # 1, 2, 3, etc.
    escalation_reason = Column(String, nullable=False)
    escalated_from = Column(String, nullable=True)  # Previous assignee
    escalated_to = Column(String, nullable=False)  # New assignee
    escalated_to_team = Column(String, nullable=True)

    # Timing
    escalated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    escalated_by = Column(String, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Metadata
    escalation_rules = Column(JSON, default=dict)  # Rules that triggered escalation
    extra_data = Column(
        JSON, default=dict
    )  # Renamed from metadata to avoid SQLAlchemy conflict

    # Relationships
    ticket = relationship("Ticket", back_populates="escalations")


# Pydantic models for API
class TicketCreate(BaseModel):
    """Create ticket request."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    category: TicketCategory
    priority: TicketPriority = TicketPriority.NORMAL
    source: TicketSource = TicketSource.CUSTOMER_PORTAL
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")


class TicketUpdate(BaseModel):
    """Update ticket request."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1)
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None
    assigned_to_id: Optional[str] = None
    assigned_team: Optional[str] = None
    tags: Optional[List[str]] = None
    extra_data: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    due_date: Optional[datetime] = None


class TicketResponse(BaseModel):
    """Ticket API response."""

    id: str
    tenant_id: str
    ticket_number: str
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    source: TicketSource
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_team: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")
    comment_count: Optional[int] = None
    attachment_count: Optional[int] = None

    class Config:
        """Config implementation."""

        from_attributes = True
        populate_by_name = True


class CommentCreate(BaseModel):
    """Create comment request."""

    content: str = Field(..., min_length=1)
    is_internal: bool = False
    is_solution: bool = False


class CommentResponse(BaseModel):
    """Comment API response."""

    id: str
    ticket_id: str
    content: str
    is_internal: bool
    is_solution: bool
    author_name: str
    author_email: Optional[str] = None
    author_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Config implementation."""

        from_attributes = True
        populate_by_name = True
