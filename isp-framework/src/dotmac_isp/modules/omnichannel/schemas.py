"""Omnichannel system Pydantic schemas."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator

from dotmac_isp.shared.schemas import TenantModelSchema
from .models import (
    ContactType,
    CommunicationChannel,
    InteractionType,
    InteractionStatus,
    AgentStatus,
    RoutingStrategy,
    EscalationTrigger,
)


# ===== BASE SCHEMAS =====


class OmnichannelBaseSchema(BaseModel):
    """Base schema for omnichannel objects."""

    class Config:
        """Class for Config operations."""
        use_enum_values = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


# ===== CONTACT MANAGEMENT SCHEMAS =====


class CustomerContactCreate(OmnichannelBaseSchema):
    """Schema for creating customer contacts."""

    customer_id: UUID = Field(..., description="Customer ID this contact belongs to")
    contact_type: ContactType = Field(..., description="Type of contact")
    first_name: str = Field(..., max_length=100, description="Contact first name")
    last_name: str = Field(..., max_length=100, description="Contact last name")
    display_name: Optional[str] = Field(
        None, max_length=200, description="Display name override"
    )
    title: Optional[str] = Field(None, max_length=100, description="Job title")
    department: Optional[str] = Field(None, max_length=100, description="Department")

    # Contact preferences
    primary_language: str = Field(
        "en", max_length=10, description="Primary language code"
    )
    timezone: str = Field("UTC", max_length=50, description="Contact timezone")
    preferred_contact_method: Optional[CommunicationChannel] = Field(
        None, description="Preferred communication channel"
    )

    # Permissions and status
    is_primary: bool = Field(False, description="Is this the primary contact")
    can_authorize_changes: bool = Field(
        False, description="Can authorize account changes"
    )
    can_receive_billing: bool = Field(
        False, description="Can receive billing communications"
    )
    can_receive_technical: bool = Field(
        False, description="Can receive technical communications"
    )

    # Communication preferences
    marketing_opt_in: bool = Field(
        False, description="Opted in to marketing communications"
    )
    sms_opt_in: bool = Field(False, description="Opted in to SMS communications")
    email_opt_in: bool = Field(True, description="Opted in to email communications")

    # Additional data
    notes: Optional[str] = Field(None, description="Additional notes about contact")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")
    tags: Optional[List[str]] = Field(None, description="Contact tags")


class CustomerContactUpdate(OmnichannelBaseSchema):
    """Schema for updating customer contacts."""

    contact_type: Optional[ContactType] = None
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=200)
    title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)

    primary_language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    preferred_contact_method: Optional[CommunicationChannel] = None

    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    can_authorize_changes: Optional[bool] = None
    can_receive_billing: Optional[bool] = None
    can_receive_technical: Optional[bool] = None

    marketing_opt_in: Optional[bool] = None
    sms_opt_in: Optional[bool] = None
    email_opt_in: Optional[bool] = None

    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class ContactCommunicationChannelCreate(OmnichannelBaseSchema):
    """Schema for creating communication channels."""

    contact_id: UUID = Field(..., description="Contact ID this channel belongs to")
    channel_type: CommunicationChannel = Field(
        ..., description="Type of communication channel"
    )
    channel_value: str = Field(
        ..., max_length=500, description="Channel value (email, phone, etc.)"
    )
    channel_display_name: Optional[str] = Field(
        None, max_length=200, description="Display name for channel"
    )

    is_primary: bool = Field(
        False, description="Is this the primary channel for this type"
    )
    is_verified: bool = Field(False, description="Has this channel been verified")

    # Platform-specific data for social media
    platform_user_id: Optional[str] = Field(
        None, max_length=255, description="Platform user ID"
    )
    platform_username: Optional[str] = Field(
        None, max_length=255, description="Platform username"
    )
    platform_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional platform data"
    )

    channel_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata"
    )


class ContactCommunicationChannelUpdate(OmnichannelBaseSchema):
    """Schema for updating communication channels."""

    channel_value: Optional[str] = Field(None, max_length=500)
    channel_display_name: Optional[str] = Field(None, max_length=200)
    is_primary: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None

    platform_user_id: Optional[str] = Field(None, max_length=255)
    platform_username: Optional[str] = Field(None, max_length=255)
    platform_data: Optional[Dict[str, Any]] = None
    channel_metadata: Optional[Dict[str, Any]] = None


class ContactCommunicationChannelResponse(TenantModelSchema):
    """Schema for communication channel responses."""

    contact_id: UUID
    channel_type: CommunicationChannel
    channel_value: str
    channel_display_name: Optional[str]
    is_verified: bool
    is_primary: bool
    is_active: bool
    verification_date: Optional[datetime]

    platform_user_id: Optional[str]
    platform_username: Optional[str]
    platform_data: Optional[Dict[str, Any]]

    last_used: Optional[datetime]
    usage_count: int
    success_count: int
    failure_count: int
    response_rate: Optional[float]
    avg_response_time: Optional[float]
    bounce_rate: Optional[float]

    channel_metadata: Optional[Dict[str, Any]]


class CustomerContactResponse(TenantModelSchema):
    """Schema for customer contact responses."""

    customer_id: UUID
    contact_type: ContactType
    first_name: str
    last_name: str
    display_name: Optional[str]
    title: Optional[str]
    department: Optional[str]

    primary_language: str
    timezone: str
    preferred_contact_method: Optional[CommunicationChannel]

    is_primary: bool
    is_active: bool
    can_authorize_changes: bool
    can_receive_billing: bool
    can_receive_technical: bool

    marketing_opt_in: bool
    sms_opt_in: bool
    email_opt_in: bool

    notes: Optional[str]
    custom_fields: Optional[Dict[str, Any]]
    tags: Optional[List[str]]

    # Computed properties
    full_name: str

    # Related data
    communication_channels: List[ContactCommunicationChannelResponse] = []


# ===== COMMUNICATION INTERACTION SCHEMAS =====


class CommunicationInteractionCreate(OmnichannelBaseSchema):
    """Schema for creating communication interactions."""

    customer_id: UUID = Field(..., description="Customer ID")
    contact_id: Optional[UUID] = Field(None, description="Specific contact ID if known")
    channel_id: Optional[UUID] = Field(
        None, description="Communication channel ID if known"
    )

    channel_type: CommunicationChannel = Field(
        ..., description="Communication channel type"
    )
    interaction_type: InteractionType = Field(..., description="Type of interaction")

    subject: Optional[str] = Field(
        None, max_length=500, description="Interaction subject"
    )
    content: str = Field(..., description="Interaction content")
    content_type: str = Field("text", max_length=50, description="Content type")

    # Platform-specific data
    external_id: Optional[str] = Field(
        None, max_length=255, description="External platform message ID"
    )
    external_thread_id: Optional[str] = Field(
        None, max_length=255, description="External thread ID"
    )
    platform_data: Optional[Dict[str, Any]] = Field(
        None, description="Platform-specific data"
    )

    # Classification
    category: Optional[str] = Field(
        None, max_length=100, description="Interaction category"
    )
    subcategory: Optional[str] = Field(
        None, max_length=100, description="Interaction subcategory"
    )
    priority: str = Field("normal", max_length=20, description="Interaction priority")

    # Business context
    related_ticket_id: Optional[UUID] = Field(
        None, description="Related support ticket ID"
    )
    related_order_id: Optional[str] = Field(
        None, max_length=100, description="Related order ID"
    )
    related_service_id: Optional[str] = Field(
        None, max_length=100, description="Related service ID"
    )

    # Additional data
    tags: Optional[List[str]] = Field(None, description="Interaction tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")
    attachments: Optional[List[Dict[str, Any]]] = Field(
        None, description="Attachment metadata"
    )


class InteractionResponseCreate(OmnichannelBaseSchema):
    """Schema for creating interaction responses."""

    interaction_id: UUID = Field(
        ..., description="Interaction ID this response belongs to"
    )
    content: str = Field(..., description="Response content")
    content_type: str = Field("text", max_length=50, description="Content type")
    is_internal: bool = Field(False, description="Is this an internal note")

    author_type: str = Field(..., max_length=50, description="Type of author")
    author_id: Optional[UUID] = Field(None, description="Author ID if applicable")
    author_name: Optional[str] = Field(None, max_length=255, description="Author name")

    # Platform-specific
    external_id: Optional[str] = Field(
        None, max_length=255, description="Platform response ID"
    )
    platform_data: Optional[Dict[str, Any]] = Field(
        None, description="Platform-specific data"
    )

    # Attachments and metadata
    attachments: Optional[List[Dict[str, Any]]] = Field(
        None, description="Attachment metadata"
    )
    response_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata"
    )


class InteractionResponseResponse(TenantModelSchema):
    """Schema for interaction response data."""

    interaction_id: UUID
    sequence_number: int
    content: str
    content_type: str
    is_internal: bool

    author_type: str
    author_id: Optional[UUID]
    author_name: Optional[str]

    sent_at: datetime
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]

    external_id: Optional[str]
    platform_data: Optional[Dict[str, Any]]

    sentiment: Optional[str]
    sentiment_score: Optional[float]

    attachments: Optional[List[Dict[str, Any]]]
    response_metadata: Optional[Dict[str, Any]]


class CommunicationInteractionResponse(TenantModelSchema):
    """Schema for communication interaction responses."""

    interaction_reference: str
    customer_id: UUID
    contact_id: Optional[UUID]
    channel_id: Optional[UUID]

    channel_type: CommunicationChannel
    interaction_type: InteractionType
    status: InteractionStatus

    subject: Optional[str]
    content: str
    content_type: str

    external_id: Optional[str]
    external_thread_id: Optional[str]
    platform_data: Optional[Dict[str, Any]]

    assigned_agent_id: Optional[UUID]
    assigned_team: Optional[str]
    routing_data: Optional[Dict[str, Any]]

    received_at: datetime
    first_response_at: Optional[datetime]
    last_response_at: Optional[datetime]
    resolved_at: Optional[datetime]

    category: Optional[str]
    subcategory: Optional[str]
    intent: Optional[str]
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    language: Optional[str]

    priority: str
    urgency_score: Optional[float]
    escalation_level: int

    response_count: int
    response_time_seconds: Optional[int]
    resolution_time_seconds: Optional[int]
    customer_satisfaction: Optional[float]

    tags: Optional[List[str]]
    keywords: Optional[List[str]]

    related_ticket_id: Optional[UUID]
    related_order_id: Optional[str]
    related_service_id: Optional[str]

    custom_fields: Optional[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]]

    # Computed properties
    is_resolved: bool
    response_time_minutes: Optional[float]

    # Related data
    responses: List[InteractionResponseResponse] = []


# ===== AGENT MANAGEMENT SCHEMAS =====


class OmnichannelAgentCreate(OmnichannelBaseSchema):
    """Schema for creating omnichannel agents."""

    user_id: UUID = Field(..., description="User ID for this agent")
    agent_code: str = Field(..., max_length=50, description="Unique agent code")
    display_name: str = Field(..., max_length=200, description="Agent display name")
    email: str = Field(..., max_length=255, description="Agent email")
    phone: Optional[str] = Field(None, max_length=20, description="Agent phone")

    team_id: Optional[UUID] = Field(None, description="Team this agent belongs to")
    supervisor_id: Optional[UUID] = Field(None, description="Supervisor agent ID")
    role_level: str = Field("agent", max_length=50, description="Agent role level")

    supported_channels: List[CommunicationChannel] = Field(
        ..., description="Channels agent can handle"
    )
    skill_tags: Optional[List[str]] = Field(
        None, description="Agent skills and capabilities"
    )
    max_concurrent_interactions: int = Field(
        5, ge=1, le=50, description="Max concurrent interactions"
    )

    work_schedule: Optional[Dict[str, Any]] = Field(
        None, description="Weekly work schedule"
    )
    timezone: str = Field("UTC", max_length=50, description="Agent timezone")
    is_24x7: bool = Field(False, description="Available 24/7")

    target_response_time: int = Field(
        300, ge=30, description="Target response time in seconds"
    )
    target_resolution_time: int = Field(
        3600, ge=300, description="Target resolution time in seconds"
    )
    quality_threshold: float = Field(
        4.0, ge=1.0, le=5.0, description="Quality threshold (1-5 scale)"
    )

    hire_date: Optional[datetime] = Field(None, description="Agent hire date")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")
    notes: Optional[str] = Field(None, description="Notes about agent")


class OmnichannelAgentUpdate(OmnichannelBaseSchema):
    """Schema for updating omnichannel agents."""

    display_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)

    status: Optional[AgentStatus] = None
    status_message: Optional[str] = Field(None, max_length=500)

    team_id: Optional[UUID] = None
    supervisor_id: Optional[UUID] = None
    role_level: Optional[str] = Field(None, max_length=50)

    supported_channels: Optional[List[CommunicationChannel]] = None
    skill_tags: Optional[List[str]] = None
    max_concurrent_interactions: Optional[int] = Field(None, ge=1, le=50)

    work_schedule: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = Field(None, max_length=50)
    is_24x7: Optional[bool] = None

    target_response_time: Optional[int] = Field(None, ge=30)
    target_resolution_time: Optional[int] = Field(None, ge=300)
    quality_threshold: Optional[float] = Field(None, ge=1.0, le=5.0)

    is_active: Optional[bool] = None
    custom_fields: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class AgentTeamCreate(OmnichannelBaseSchema):
    """Schema for creating agent teams."""

    team_name: str = Field(..., max_length=200, description="Team name")
    team_code: str = Field(..., max_length=50, description="Unique team code")
    description: Optional[str] = Field(None, description="Team description")

    supported_channels: List[CommunicationChannel] = Field(
        ..., description="Channels this team handles"
    )
    specializations: Optional[List[str]] = Field(
        None, description="Team specializations"
    )

    routing_strategy: RoutingStrategy = Field(
        RoutingStrategy.ROUND_ROBIN, description="Routing strategy"
    )
    max_queue_size: int = Field(50, ge=1, description="Maximum queue size")
    escalation_team_id: Optional[UUID] = Field(None, description="Escalation team ID")

    team_lead_id: Optional[UUID] = Field(None, description="Team lead agent ID")

    business_hours: Optional[Dict[str, Any]] = Field(
        None, description="Team business hours"
    )
    timezone: str = Field("UTC", max_length=50, description="Team timezone")

    target_response_time: int = Field(
        300, ge=30, description="Target response time in seconds"
    )
    target_resolution_time: int = Field(
        3600, ge=300, description="Target resolution time in seconds"
    )
    target_satisfaction: float = Field(
        4.0, ge=1.0, le=5.0, description="Target satisfaction score"
    )

    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")


class AgentTeamResponse(TenantModelSchema):
    """Schema for agent team responses."""

    team_name: str
    team_code: str
    description: Optional[str]

    supported_channels: List[CommunicationChannel]
    specializations: Optional[List[str]]

    routing_strategy: RoutingStrategy
    max_queue_size: int
    escalation_team_id: Optional[UUID]

    team_lead_id: Optional[UUID]

    business_hours: Optional[Dict[str, Any]]
    timezone: str

    target_response_time: int
    target_resolution_time: int
    target_satisfaction: float

    is_active: bool
    custom_fields: Optional[Dict[str, Any]]


class OmnichannelAgentResponse(TenantModelSchema):
    """Schema for omnichannel agent responses."""

    user_id: UUID
    agent_code: str
    display_name: str
    email: str
    phone: Optional[str]

    status: AgentStatus
    last_activity: Optional[datetime]
    status_message: Optional[str]

    team_id: Optional[UUID]
    supervisor_id: Optional[UUID]
    role_level: str

    supported_channels: List[CommunicationChannel]
    skill_tags: Optional[List[str]]
    max_concurrent_interactions: int

    work_schedule: Optional[Dict[str, Any]]
    timezone: str
    is_24x7: bool

    target_response_time: int
    target_resolution_time: int
    quality_threshold: float

    current_interactions: int
    current_load_percentage: float

    is_active: bool
    hire_date: Optional[datetime]
    last_login: Optional[datetime]

    # Performance metrics (cached)
    total_interactions: int
    avg_response_time: Optional[float]
    avg_resolution_time: Optional[float]
    customer_satisfaction: Optional[float]
    resolution_rate: Optional[float]

    custom_fields: Optional[Dict[str, Any]]
    notes: Optional[str]

    # Computed properties
    is_available: bool
    utilization_rate: float

    # Related data
    team: Optional[AgentTeamResponse] = None


# ===== ROUTING AND ESCALATION SCHEMAS =====


class RoutingRuleCreate(OmnichannelBaseSchema):
    """Schema for creating routing rules."""

    rule_name: str = Field(..., max_length=255, description="Rule name")
    rule_code: str = Field(..., max_length=100, description="Unique rule code")
    description: Optional[str] = Field(None, description="Rule description")

    priority: int = Field(0, description="Rule priority (higher = more priority)")
    is_active: bool = Field(True, description="Is rule active")

    conditions: Dict[str, Any] = Field(..., description="Rule conditions (JSON)")

    target_team_id: Optional[UUID] = Field(None, description="Target team ID")
    target_agent_id: Optional[UUID] = Field(None, description="Target agent ID")
    routing_strategy: Optional[RoutingStrategy] = Field(
        None, description="Routing strategy override"
    )

    priority_boost: int = Field(
        0, description="Priority boost for matching interactions"
    )
    urgency_multiplier: float = Field(
        1.0, ge=0.1, le=10.0, description="Urgency multiplier"
    )

    business_hours_only: bool = Field(
        False, description="Apply only during business hours"
    )
    valid_from: Optional[datetime] = Field(None, description="Rule valid from date")
    valid_to: Optional[datetime] = Field(None, description="Rule valid to date")

    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")


class InteractionEscalationCreate(OmnichannelBaseSchema):
    """Schema for creating interaction escalations."""

    interaction_id: UUID = Field(..., description="Interaction to escalate")
    escalation_level: int = Field(..., ge=1, description="Escalation level")

    trigger_type: EscalationTrigger = Field(
        ..., description="What triggered the escalation"
    )
    trigger_details: Optional[Dict[str, Any]] = Field(
        None, description="Trigger details"
    )

    from_agent_id: Optional[UUID] = Field(None, description="Escalating from agent")
    from_team_id: Optional[UUID] = Field(None, description="Escalating from team")
    to_agent_id: Optional[UUID] = Field(None, description="Escalating to agent")
    to_team_id: Optional[UUID] = Field(None, description="Escalating to team")

    reason: str = Field(..., description="Escalation reason")
    notes: Optional[str] = Field(None, description="Additional notes")


class InteractionEscalationResponse(TenantModelSchema):
    """Schema for escalation responses."""

    interaction_id: UUID
    escalation_level: int

    trigger_type: EscalationTrigger
    trigger_details: Optional[Dict[str, Any]]

    from_agent_id: Optional[UUID]
    from_team_id: Optional[UUID]
    to_agent_id: Optional[UUID]
    to_team_id: Optional[UUID]

    escalated_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]

    reason: str
    notes: Optional[str]
    status: str


# ===== ANALYTICS SCHEMAS =====


class AgentPerformanceMetricResponse(TenantModelSchema):
    """Schema for agent performance metrics."""

    agent_id: UUID
    metric_date: datetime
    metric_period: str

    # Volume metrics
    total_interactions: int
    interactions_by_channel: Optional[Dict[str, int]]

    # Response time metrics
    avg_response_time_seconds: Optional[float]
    median_response_time_seconds: Optional[float]
    first_response_sla_met_count: int
    first_response_sla_total_count: int

    # Resolution metrics
    avg_resolution_time_seconds: Optional[float]
    median_resolution_time_seconds: Optional[float]
    resolution_sla_met_count: int
    resolution_sla_total_count: int

    # Quality metrics
    customer_satisfaction_avg: Optional[float]
    customer_satisfaction_count: int
    resolution_rate: Optional[float]
    escalation_rate: Optional[float]

    # Activity metrics
    active_time_minutes: float
    idle_time_minutes: float
    break_time_minutes: float

    # Workload metrics
    max_concurrent_interactions: int
    avg_concurrent_interactions: float
    utilization_rate: float

    # Channel-specific metrics
    channel_performance: Optional[Dict[str, Any]]

    # Quality scores
    qa_score_avg: Optional[float]
    qa_score_count: int

    custom_metrics: Optional[Dict[str, Any]]

    @property
    def first_response_sla_rate(self) -> Optional[float]:
        """Calculate first response SLA rate."""
        if self.first_response_sla_total_count > 0:
            return (
                self.first_response_sla_met_count / self.first_response_sla_total_count
            ) * 100
        return None

    @property
    def resolution_sla_rate(self) -> Optional[float]:
        """Calculate resolution SLA rate."""
        if self.resolution_sla_total_count > 0:
            return (
                self.resolution_sla_met_count / self.resolution_sla_total_count
            ) * 100
        return None


class ChannelAnalyticsResponse(TenantModelSchema):
    """Schema for channel analytics."""

    channel_type: CommunicationChannel
    metric_date: datetime
    metric_period: str

    # Volume metrics
    total_interactions: int
    inbound_interactions: int
    outbound_interactions: int

    # Response metrics
    avg_response_time_seconds: Optional[float]
    median_response_time_seconds: Optional[float]
    response_rate: Optional[float]

    # Resolution metrics
    avg_resolution_time_seconds: Optional[float]
    resolution_rate: Optional[float]
    escalation_rate: Optional[float]

    # Quality metrics
    customer_satisfaction_avg: Optional[float]
    customer_satisfaction_count: int

    # Engagement metrics
    bounce_rate: Optional[float]
    click_through_rate: Optional[float]
    conversion_rate: Optional[float]

    # Sentiment analysis
    sentiment_positive: int
    sentiment_neutral: int
    sentiment_negative: int
    avg_sentiment_score: Optional[float]

    # Cost metrics
    total_cost: Optional[float]
    cost_per_interaction: Optional[float]
    cost_currency: Optional[str]

    custom_metrics: Optional[Dict[str, Any]]


class CustomerCommunicationSummaryResponse(TenantModelSchema):
    """Schema for customer communication summary."""

    customer_id: UUID
    total_interactions: int
    first_interaction_date: Optional[datetime]
    last_interaction_date: Optional[datetime]

    preferred_channels: Optional[List[str]]
    channel_usage_stats: Optional[Dict[str, int]]

    avg_response_time_minutes: Optional[float]
    typical_response_hours: Optional[List[int]]

    avg_satisfaction_score: Optional[float]
    overall_sentiment: Optional[str]
    sentiment_trend: Optional[str]

    common_categories: Optional[List[str]]
    resolution_rate: Optional[float]
    escalation_frequency: Optional[float]

    marketing_engaged: bool
    prefers_self_service: bool
    communication_frequency_preference: Optional[str]

    churn_risk_score: Optional[float]
    satisfaction_trend: Optional[str]
    last_complaint_date: Optional[datetime]

    communication_profile_tags: Optional[List[str]]
    last_calculated: datetime


# ===== SEARCH AND FILTER SCHEMAS =====


class InteractionSearchFilters(OmnichannelBaseSchema):
    """Schema for searching interactions."""

    customer_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    team: Optional[str] = None

    channel_type: Optional[CommunicationChannel] = None
    interaction_type: Optional[InteractionType] = None
    status: Optional[InteractionStatus] = None

    category: Optional[str] = None
    priority: Optional[str] = None
    sentiment: Optional[str] = None

    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    has_escalations: Optional[bool] = None
    is_resolved: Optional[bool] = None

    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None

    # Pagination
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    # Sorting
    sort_by: str = Field("received_at", description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class AgentSearchFilters(OmnichannelBaseSchema):
    """Schema for searching agents."""

    team_id: Optional[UUID] = None
    status: Optional[AgentStatus] = None
    role_level: Optional[str] = None

    supported_channels: Optional[List[CommunicationChannel]] = None
    skill_tags: Optional[List[str]] = None

    is_available: Optional[bool] = None
    is_active: Optional[bool] = None

    # Performance filters
    min_satisfaction: Optional[float] = Field(None, ge=1.0, le=5.0)
    max_response_time: Optional[int] = Field(None, ge=0)
    min_resolution_rate: Optional[float] = Field(None, ge=0, le=100)

    # Pagination
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    # Sorting
    sort_by: str = Field("display_name", description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")


# ===== BULK OPERATIONS SCHEMAS =====


class BulkContactImport(OmnichannelBaseSchema):
    """Schema for bulk contact import."""

    contacts: List[CustomerContactCreate] = Field(..., min_items=1, max_items=1000)
    update_existing: bool = Field(False, description="Update existing contacts")
    skip_validation_errors: bool = Field(
        False, description="Skip rows with validation errors"
    )


class BulkChannelUpdate(OmnichannelBaseSchema):
    """Schema for bulk channel updates."""

    channel_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    updates: ContactCommunicationChannelUpdate = Field(
        ..., description="Updates to apply"
    )


class BulkInteractionAssignment(OmnichannelBaseSchema):
    """Schema for bulk interaction assignment."""

    interaction_ids: List[UUID] = Field(..., min_items=1, max_items=50)
    agent_id: Optional[UUID] = Field(None, description="Assign to specific agent")
    team: Optional[str] = Field(None, max_length=100, description="Assign to team")
    priority: Optional[str] = Field(None, max_length=20, description="Update priority")

    notes: Optional[str] = Field(None, description="Assignment notes")


# ===== DASHBOARD SCHEMAS =====


class OmnichannelDashboardStats(OmnichannelBaseSchema):
    """Schema for omnichannel dashboard statistics."""

    # Current status
    total_active_interactions: int
    total_pending_interactions: int
    total_available_agents: int
    total_busy_agents: int

    # Performance metrics
    avg_response_time_minutes: Optional[float]
    avg_resolution_time_hours: Optional[float]
    current_satisfaction_score: Optional[float]
    sla_compliance_rate: Optional[float]

    # Channel breakdown
    interactions_by_channel: Dict[str, int]
    channel_response_times: Dict[str, float]

    # Team performance
    team_utilization_rates: Dict[str, float]
    team_queue_sizes: Dict[str, int]

    # Trends (last 24 hours)
    hourly_interaction_volume: List[int]
    hourly_response_times: List[float]

    # Alerts and issues
    breached_sla_count: int
    high_priority_queue_size: int
    escalated_interactions_count: int

    # Calculated at
    calculated_at: datetime


class AgentDashboardStats(OmnichannelBaseSchema):
    """Schema for agent-specific dashboard stats."""

    agent_id: UUID

    # Current status
    current_status: AgentStatus
    current_interactions: int
    utilization_rate: float

    # Today's performance
    today_interactions_handled: int
    today_avg_response_time_minutes: Optional[float]
    today_customer_satisfaction: Optional[float]

    # Recent performance (last 7 days)
    weekly_interactions: int
    weekly_avg_response_time: Optional[float]
    weekly_resolution_rate: Optional[float]
    weekly_satisfaction_score: Optional[float]

    # Performance ranking (within team)
    team_ranking_satisfaction: Optional[int]
    team_ranking_response_time: Optional[int]
    team_ranking_volume: Optional[int]

    # Goals and targets
    response_time_target: int
    resolution_time_target: int
    satisfaction_target: float

    # Achievement rates
    response_time_achievement_rate: Optional[float]
    resolution_time_achievement_rate: Optional[float]
    satisfaction_achievement_rate: Optional[float]

    # Calculated at
    calculated_at: datetime
