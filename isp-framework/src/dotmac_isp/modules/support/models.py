"""Support models - Tickets, knowledge base, SLA, and customer support."""

# ARCHITECTURE IMPROVEMENT: Explicit imports replace wildcard import
import enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID as PythonUUID
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.enums import Priority, TicketStatus


class TicketCategory(enum.Enum):
    """Ticket category enumeration."""

    TECHNICAL = "technical"
    BILLING = "billing"
    SALES = "sales"
    GENERAL = "general"
    COMPLAINT = "complaint"
    FEATURE_REQUEST = "feature_request"


class TicketSource(enum.Enum):
    """Ticket source enumeration."""

    PHONE = "phone"
    EMAIL = "email"
    WEB_PORTAL = "web_portal"
    CHAT = "chat"
    SOCIAL_MEDIA = "social_media"
    WALK_IN = "walk_in"
    SYSTEM = "system"


class SLAStatus(enum.Enum):
    """SLA status enumeration."""

    WITHIN_SLA = "within_sla"
    AT_RISK = "at_risk"
    BREACHED = "breached"


class Ticket(TenantModel):
    """Support ticket model."""

    __tablename__ = "tickets"

    # Ticket identification
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)

    # Ticket details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(
        Enum(TicketCategory), default=TicketCategory.GENERAL, nullable=False
    )
    priority = Column(
        Enum(Priority), default=Priority.MEDIUM, nullable=False
    )
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    source = Column(Enum(TicketSource), default=TicketSource.WEB_PORTAL, nullable=False)

    # Customer information
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)

    # Assignment
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_team = Column(String(100), nullable=True)

    # Timing
    opened_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # SLA tracking
    sla_due_date = Column(DateTime(timezone=True), nullable=True)
    sla_status = Column(Enum(SLAStatus), default=SLAStatus.WITHIN_SLA, nullable=False)

    # Service reference
    service_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("service_instances.id"), nullable=True
    )

    # Additional metadata
    tags = Column(JSONB, nullable=True)  # List of tags
    custom_fields = Column(JSONB, nullable=True)  # Custom fields

    # Relationships
    customer = relationship("Customer", back_populates="tickets")
    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])
    service_instance = relationship("ServiceInstance")
    comments = relationship(
        "TicketComment", back_populates="ticket", cascade="all, delete-orphan"
    )
    attachments = relationship(
        "TicketAttachment", back_populates="ticket", cascade="all, delete-orphan"
    )

    @property
    def is_overdue(self) -> bool:
        """Check if ticket is overdue based on SLA."""
        if self.sla_due_date and self.status not in [
            TicketStatus.RESOLVED,
            TicketStatus.CLOSED,
        ]:
            return datetime.utcnow() > self.sla_due_date
        return False


class TicketComment(TenantModel):
    """Ticket comment model for conversation tracking."""

    __tablename__ = "ticket_comments"

    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)

    # Comment details
    content = Column(Text, nullable=False)
    is_internal = Column(
        Boolean, default=False, nullable=False
    )  # Internal notes vs customer-facing
    is_system_generated = Column(Boolean, default=False, nullable=False)

    # Author information
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    author_name = Column(String(255), nullable=True)  # For external/anonymous comments
    author_email = Column(String(255), nullable=True)

    # Additional metadata
    comment_data = Column(JSONB, nullable=True)  # Additional structured data

    # Relationships
    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User")


class TicketAttachment(TenantModel):
    """Ticket attachment model for file uploads."""

    __tablename__ = "ticket_attachments"

    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)

    # File details
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    content_type = Column(String(100), nullable=False)
    file_path = Column(String(1000), nullable=False)  # Storage path

    # Upload metadata
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    upload_date = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Relationships
    ticket = relationship("Ticket", back_populates="attachments")
    uploader = relationship("User")


class KnowledgeBaseCategory(TenantModel):
    """Knowledge base category model."""

    __tablename__ = "kb_categories"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)

    # Hierarchy
    parent_id = Column(
        UUID(as_uuid=True), ForeignKey("kb_categories.id"), nullable=True
    )
    sort_order = Column(Integer, default=0, nullable=False)

    # Visibility
    is_public = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    parent = relationship(
        "KnowledgeBaseCategory", remote_side="KnowledgeBaseCategory.id"
    )
    children = relationship("KnowledgeBaseCategory", overlaps="parent")
    articles = relationship("KnowledgeBaseArticle", back_populates="category")


class KnowledgeBaseArticle(TenantModel):
    """Knowledge base article model."""

    __tablename__ = "kb_articles"

    # Article details
    title = Column(String(500), nullable=False)
    slug = Column(String(500), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)

    # Categorization
    category_id = Column(
        UUID(as_uuid=True), ForeignKey("kb_categories.id"), nullable=False
    )
    tags = Column(JSONB, nullable=True)  # List of tags

    # Metadata
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    last_updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Publishing
    is_published = Column(Boolean, default=False, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Statistics
    view_count = Column(Integer, default=0, nullable=False)
    helpful_votes = Column(Integer, default=0, nullable=False)
    unhelpful_votes = Column(Integer, default=0, nullable=False)

    # SEO
    meta_description = Column(Text, nullable=True)
    meta_keywords = Column(Text, nullable=True)

    # Relationships
    category = relationship("KnowledgeBaseCategory", back_populates="articles")
    author = relationship("User", foreign_keys=[author_id])
    last_editor = relationship("User", foreign_keys=[last_updated_by])


class SLAPolicy(TenantModel):
    """SLA policy model for service level agreements."""

    __tablename__ = "sla_policies"

    # Policy details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Response time targets (in minutes)
    first_response_time = Column(Integer, nullable=False)  # Minutes to first response
    resolution_time = Column(Integer, nullable=False)  # Minutes to resolution

    # Business hours
    business_hours_start = Column(
        String(5), default="09:00", nullable=False
    )  # HH:MM format
    business_hours_end = Column(
        String(5), default="17:00", nullable=False
    )  # HH:MM format
    business_days = Column(String(20), default="monday-friday", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)

    # Escalation rules
    escalation_enabled = Column(Boolean, default=True, nullable=False)
    escalation_time = Column(Integer, nullable=True)  # Minutes before escalation
    escalation_target = Column(String(255), nullable=True)  # Email or team

    # Applicability rules (stored as JSON)
    conditions = Column(JSONB, nullable=True)  # Rules for when this SLA applies


class EscalationRule(TenantModel):
    """Escalation rule model for automatic ticket escalation."""

    __tablename__ = "escalation_rules"

    # Rule details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Trigger conditions
    trigger_conditions = Column(JSONB, nullable=False)  # JSON conditions
    trigger_delay_minutes = Column(Integer, nullable=False)

    # Actions to take
    escalation_actions = Column(JSONB, nullable=False)  # JSON actions

    # Assignment changes
    new_assignee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    new_team = Column(String(100), nullable=True)
    new_priority = Column(Enum(Priority), nullable=True)

    # Notifications
    notify_emails = Column(JSONB, nullable=True)  # List of email addresses
    notification_template = Column(String(255), nullable=True)

    # Relationships
    new_assignee = relationship("User")
