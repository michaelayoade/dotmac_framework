"""Support module schemas for API requests and responses."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr

from .models import (
    TicketPriority,
    TicketStatus,
    TicketCategory,
    TicketSource,
    SLAStatus,
)


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = {"from_attributes": True}


# Ticket schemas
class TicketBase(BaseSchema):
    """Base ticket schema."""

    title: str = Field(..., min_length=1, max_length=500, description="Ticket title")
    description: str = Field(..., min_length=1, description="Ticket description")
    category: TicketCategory = Field(
        default=TicketCategory.GENERAL, description="Ticket category"
    )
    priority: TicketPriority = Field(
        default=TicketPriority.NORMAL, description="Ticket priority"
    )
    source: TicketSource = Field(
        default=TicketSource.WEB_PORTAL, description="Ticket source"
    )


class TicketCreate(TicketBase):
    """Schema for creating tickets."""

    # Customer information
    customer_id: Optional[str] = Field(None, description="Customer ID")
    contact_name: Optional[str] = Field(
        None, max_length=255, description="Contact name"
    )
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(
        None, max_length=20, description="Contact phone"
    )

    # Service reference
    service_instance_id: Optional[str] = Field(
        None, description="Related service instance ID"
    )

    # Assignment
    assigned_to: Optional[str] = Field(None, description="Assigned user ID")
    assigned_team: Optional[str] = Field(
        None, max_length=100, description="Assigned team"
    )

    # Additional metadata
    tags: Optional[List[str]] = Field(None, description="Ticket tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")


class TicketUpdate(BaseSchema):
    """Schema for updating tickets."""

    title: Optional[str] = Field(
        None, min_length=1, max_length=500, description="Ticket title"
    )
    description: Optional[str] = Field(
        None, min_length=1, description="Ticket description"
    )
    category: Optional[TicketCategory] = Field(None, description="Ticket category")
    priority: Optional[TicketPriority] = Field(None, description="Ticket priority")
    status: Optional[TicketStatus] = Field(None, description="Ticket status")
    assigned_to: Optional[str] = Field(None, description="Assigned user ID")
    assigned_team: Optional[str] = Field(None, description="Assigned team")
    tags: Optional[List[str]] = Field(None, description="Ticket tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")


class TicketResponse(TicketBase):
    """Schema for ticket responses."""

    id: str = Field(..., description="Ticket ID")
    tenant_id: str = Field(..., description="Tenant ID")
    ticket_number: str = Field(..., description="Ticket number")
    status: TicketStatus = Field(..., description="Ticket status")

    # Customer information
    customer_id: Optional[str] = Field(None, description="Customer ID")
    contact_name: Optional[str] = Field(None, description="Contact name")
    contact_email: Optional[str] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone")

    # Assignment
    created_by: Optional[str] = Field(None, description="Creator user ID")
    assigned_to: Optional[str] = Field(None, description="Assigned user ID")
    assigned_team: Optional[str] = Field(None, description="Assigned team")

    # Timing
    opened_at: datetime = Field(..., description="Ticket creation timestamp")
    first_response_at: Optional[datetime] = Field(
        None, description="First response timestamp"
    )
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    closed_at: Optional[datetime] = Field(None, description="Closure timestamp")

    # SLA tracking
    sla_due_date: Optional[datetime] = Field(None, description="SLA due date")
    sla_status: SLAStatus = Field(..., description="SLA status")
    is_overdue: bool = Field(..., description="Is ticket overdue")

    # Service reference
    service_instance_id: Optional[str] = Field(
        None, description="Related service instance ID"
    )

    # Counts
    comment_count: int = Field(0, ge=0, description="Number of comments")
    attachment_count: int = Field(0, ge=0, description="Number of attachments")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Ticket Comment schemas
class TicketCommentBase(BaseSchema):
    """Base ticket comment schema."""

    content: str = Field(..., min_length=1, description="Comment content")
    is_internal: bool = Field(default=False, description="Is internal note")


class TicketCommentCreate(TicketCommentBase):
    """Schema for creating ticket comments."""

    ticket_id: str = Field(..., description="Ticket ID")
    author_name: Optional[str] = Field(
        None, description="Author name (for external comments)"
    )
    author_email: Optional[EmailStr] = Field(
        None, description="Author email (for external comments)"
    )
    comment_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional comment data"
    )


class TicketCommentUpdate(BaseSchema):
    """Schema for updating ticket comments."""

    content: Optional[str] = Field(None, min_length=1, description="Comment content")
    is_internal: Optional[bool] = Field(None, description="Is internal note")


class TicketCommentResponse(TicketCommentBase):
    """Schema for ticket comment responses."""

    id: str = Field(..., description="Comment ID")
    tenant_id: str = Field(..., description="Tenant ID")
    ticket_id: str = Field(..., description="Ticket ID")
    is_system_generated: bool = Field(..., description="Is system generated")

    # Author information
    author_id: Optional[str] = Field(None, description="Author user ID")
    author_name: Optional[str] = Field(None, description="Author name")
    author_email: Optional[str] = Field(None, description="Author email")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Ticket Attachment schemas
class TicketAttachmentResponse(BaseSchema):
    """Schema for ticket attachment responses."""

    id: str = Field(..., description="Attachment ID")
    tenant_id: str = Field(..., description="Tenant ID")
    ticket_id: str = Field(..., description="Ticket ID")
    filename: str = Field(..., description="File name")
    original_filename: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="Content type")
    uploaded_by: Optional[str] = Field(None, description="Uploader user ID")
    upload_date: datetime = Field(..., description="Upload timestamp")


# Knowledge Base schemas
class KnowledgeBaseCategoryBase(BaseSchema):
    """Base knowledge base category schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    slug: str = Field(..., max_length=255, description="Category slug")


class KnowledgeBaseCategoryCreate(KnowledgeBaseCategoryBase):
    """Schema for creating knowledge base categories."""

    parent_id: Optional[str] = Field(None, description="Parent category ID")
    sort_order: int = Field(default=0, description="Sort order")
    is_public: bool = Field(default=True, description="Is publicly visible")
    is_active: bool = Field(default=True, description="Is active")


class KnowledgeBaseCategoryUpdate(BaseSchema):
    """Schema for updating knowledge base categories."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Category name"
    )
    description: Optional[str] = Field(None, description="Category description")
    sort_order: Optional[int] = Field(None, description="Sort order")
    is_public: Optional[bool] = Field(None, description="Is publicly visible")
    is_active: Optional[bool] = Field(None, description="Is active")


class KnowledgeBaseCategoryResponse(KnowledgeBaseCategoryBase):
    """Schema for knowledge base category responses."""

    id: str = Field(..., description="Category ID")
    tenant_id: str = Field(..., description="Tenant ID")
    parent_id: Optional[str] = Field(None, description="Parent category ID")
    sort_order: int = Field(..., description="Sort order")
    is_public: bool = Field(..., description="Is publicly visible")
    is_active: bool = Field(..., description="Is active")
    article_count: int = Field(0, ge=0, description="Number of articles")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class KnowledgeBaseArticleBase(BaseSchema):
    """Base knowledge base article schema."""

    title: str = Field(..., min_length=1, max_length=500, description="Article title")
    slug: str = Field(..., max_length=500, description="Article slug")
    content: str = Field(..., min_length=1, description="Article content")
    summary: Optional[str] = Field(None, description="Article summary")


class KnowledgeBaseArticleCreate(KnowledgeBaseArticleBase):
    """Schema for creating knowledge base articles."""

    category_id: str = Field(..., description="Category ID")
    tags: Optional[List[str]] = Field(None, description="Article tags")
    is_published: bool = Field(default=False, description="Is published")
    is_featured: bool = Field(default=False, description="Is featured")
    meta_description: Optional[str] = Field(
        None, description="Meta description for SEO"
    )
    meta_keywords: Optional[str] = Field(None, description="Meta keywords for SEO")


class KnowledgeBaseArticleUpdate(BaseSchema):
    """Schema for updating knowledge base articles."""

    title: Optional[str] = Field(
        None, min_length=1, max_length=500, description="Article title"
    )
    content: Optional[str] = Field(None, min_length=1, description="Article content")
    summary: Optional[str] = Field(None, description="Article summary")
    category_id: Optional[str] = Field(None, description="Category ID")
    tags: Optional[List[str]] = Field(None, description="Article tags")
    is_published: Optional[bool] = Field(None, description="Is published")
    is_featured: Optional[bool] = Field(None, description="Is featured")
    meta_description: Optional[str] = Field(None, description="Meta description")
    meta_keywords: Optional[str] = Field(None, description="Meta keywords")


class KnowledgeBaseArticleResponse(KnowledgeBaseArticleBase):
    """Schema for knowledge base article responses."""

    id: str = Field(..., description="Article ID")
    tenant_id: str = Field(..., description="Tenant ID")
    category_id: str = Field(..., description="Category ID")
    tags: Optional[List[str]] = Field(None, description="Article tags")

    # Authorship
    author_id: str = Field(..., description="Author user ID")
    last_updated_by: Optional[str] = Field(None, description="Last editor user ID")

    # Publishing
    is_published: bool = Field(..., description="Is published")
    is_featured: bool = Field(..., description="Is featured")
    published_at: Optional[datetime] = Field(None, description="Publication timestamp")

    # Statistics
    view_count: int = Field(..., description="View count")
    helpful_votes: int = Field(..., description="Helpful votes")
    unhelpful_votes: int = Field(..., description="Unhelpful votes")

    # SEO
    meta_description: Optional[str] = Field(None, description="Meta description")
    meta_keywords: Optional[str] = Field(None, description="Meta keywords")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# SLA Policy schemas
class SLAPolicyBase(BaseSchema):
    """Base SLA policy schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Policy name")
    description: Optional[str] = Field(None, description="Policy description")
    first_response_time: int = Field(
        ..., gt=0, description="First response time in minutes"
    )
    resolution_time: int = Field(..., gt=0, description="Resolution time in minutes")


class SLAPolicyCreate(SLAPolicyBase):
    """Schema for creating SLA policies."""

    is_default: bool = Field(default=False, description="Is default policy")
    business_hours_start: str = Field(
        default="09:00",
        pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="Business hours start (HH:MM)",
    )
    business_hours_end: str = Field(
        default="17:00",
        pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="Business hours end (HH:MM)",
    )
    business_days: str = Field(default="monday-friday", description="Business days")
    timezone: str = Field(default="UTC", description="Timezone")
    escalation_enabled: bool = Field(default=True, description="Escalation enabled")
    escalation_time: Optional[int] = Field(
        None, gt=0, description="Escalation time in minutes"
    )
    escalation_target: Optional[str] = Field(None, description="Escalation target")
    conditions: Optional[Dict[str, Any]] = Field(
        None, description="Applicability conditions"
    )


class SLAPolicyUpdate(BaseSchema):
    """Schema for updating SLA policies."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Policy name"
    )
    description: Optional[str] = Field(None, description="Policy description")
    first_response_time: Optional[int] = Field(
        None, gt=0, description="First response time in minutes"
    )
    resolution_time: Optional[int] = Field(
        None, gt=0, description="Resolution time in minutes"
    )
    is_default: Optional[bool] = Field(None, description="Is default policy")
    escalation_enabled: Optional[bool] = Field(None, description="Escalation enabled")
    escalation_time: Optional[int] = Field(
        None, gt=0, description="Escalation time in minutes"
    )
    escalation_target: Optional[str] = Field(None, description="Escalation target")


class SLAPolicyResponse(SLAPolicyBase):
    """Schema for SLA policy responses."""

    id: str = Field(..., description="Policy ID")
    tenant_id: str = Field(..., description="Tenant ID")
    is_active: bool = Field(..., description="Is active")
    is_default: bool = Field(..., description="Is default policy")
    business_hours_start: str = Field(..., description="Business hours start")
    business_hours_end: str = Field(..., description="Business hours end")
    business_days: str = Field(..., description="Business days")
    timezone: str = Field(..., description="Timezone")
    escalation_enabled: bool = Field(..., description="Escalation enabled")
    escalation_time: Optional[int] = Field(
        None, description="Escalation time in minutes"
    )
    escalation_target: Optional[str] = Field(None, description="Escalation target")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Dashboard and Analytics schemas
class SupportDashboard(BaseSchema):
    """Support dashboard metrics."""

    total_tickets: int = Field(..., ge=0, description="Total tickets")
    open_tickets: int = Field(..., ge=0, description="Open tickets")
    in_progress_tickets: int = Field(..., ge=0, description="In progress tickets")
    resolved_tickets: int = Field(..., ge=0, description="Resolved tickets")
    overdue_tickets: int = Field(..., ge=0, description="Overdue tickets")
    critical_tickets: int = Field(..., ge=0, description="Critical priority tickets")
    avg_response_time_hours: float = Field(
        ..., ge=0, description="Average response time in hours"
    )
    avg_resolution_time_hours: float = Field(
        ..., ge=0, description="Average resolution time in hours"
    )
    sla_compliance_rate: float = Field(
        ..., ge=0, le=100, description="SLA compliance rate percentage"
    )
    customer_satisfaction_score: Optional[float] = Field(
        None, ge=0, le=10, description="Customer satisfaction score"
    )
    total_kb_articles: int = Field(
        ..., ge=0, description="Total knowledge base articles"
    )
    published_kb_articles: int = Field(
        ..., ge=0, description="Published knowledge base articles"
    )


class TicketMetrics(BaseSchema):
    """Ticket metrics for analytics."""

    ticket_id: str = Field(..., description="Ticket ID")
    ticket_number: str = Field(..., description="Ticket number")
    title: str = Field(..., description="Ticket title")
    status: TicketStatus = Field(..., description="Ticket status")
    priority: TicketPriority = Field(..., description="Ticket priority")
    category: TicketCategory = Field(..., description="Ticket category")
    sla_status: SLAStatus = Field(..., description="SLA status")
    response_time_hours: Optional[float] = Field(
        None, description="Response time in hours"
    )
    resolution_time_hours: Optional[float] = Field(
        None, description="Resolution time in hours"
    )
    is_overdue: bool = Field(..., description="Is overdue")
    assigned_team: Optional[str] = Field(None, description="Assigned team")
    created_at: datetime = Field(..., description="Creation timestamp")


class BulkTicketOperation(BaseSchema):
    """Bulk ticket operation schema."""

    ticket_ids: List[str] = Field(..., min_items=1, description="Ticket IDs")
    operation: str = Field(
        ...,
        pattern="^(assign|close|escalate|change_priority|change_status)$",
        description="Operation to perform",
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Operation parameters"
    )


class BulkOperationResponse(BaseSchema):
    """Bulk operation response."""

    operation_id: str = Field(..., description="Operation ID")
    total_tickets: int = Field(..., ge=0, description="Total tickets")
    successful: int = Field(..., ge=0, description="Successful operations")
    failed: int = Field(..., ge=0, description="Failed operations")
    results: List[Dict[str, Any]] = Field(..., description="Operation results")


# Re-export commonly used schemas
__all__ = [
    # Base
    "BaseSchema",
    # Ticket schemas
    "TicketBase",
    "TicketCreate",
    "TicketUpdate",
    "TicketResponse",
    # Comment schemas
    "TicketCommentBase",
    "TicketCommentCreate",
    "TicketCommentUpdate",
    "TicketCommentResponse",
    # Attachment schemas
    "TicketAttachmentResponse",
    # Knowledge Base schemas
    "KnowledgeBaseCategoryBase",
    "KnowledgeBaseCategoryCreate",
    "KnowledgeBaseCategoryUpdate",
    "KnowledgeBaseCategoryResponse",
    "KnowledgeBaseArticleBase",
    "KnowledgeBaseArticleCreate",
    "KnowledgeBaseArticleUpdate",
    "KnowledgeBaseArticleResponse",
    # SLA schemas
    "SLAPolicyBase",
    "SLAPolicyCreate",
    "SLAPolicyUpdate",
    "SLAPolicyResponse",
    # Dashboard schemas
    "SupportDashboard",
    "TicketMetrics",
    # Bulk operations
    "BulkTicketOperation",
    "BulkOperationResponse",
    # Enums
    "TicketPriority",
    "TicketStatus",
    "TicketCategory",
    "TicketSource",
    "SLAStatus",
]
