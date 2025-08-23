"""Production-ready omnichannel models for modular monolith."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
    Table,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel, StatusMixin, AuditMixin


# ===== ENUMS =====


class ContactType(str, Enum):
    """Contact type classification."""

    PRIMARY = "primary"
    BILLING = "billing"
    TECHNICAL = "technical"
    EMERGENCY = "emergency"
    SALES = "sales"
    SUPPORT = "support"
    EXECUTIVE = "executive"


class InteractionType(str, Enum):
    """Interaction type classification."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"
    SYSTEM = "system"


class InteractionStatus(str, Enum):
    """Interaction status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """Agent availability status."""

    AVAILABLE = "available"
    BUSY = "busy"
    AWAY = "away"
    OFFLINE = "offline"
    IN_TRAINING = "in_training"
    ON_BREAK = "on_break"


class RoutingStrategy(str, Enum):
    """Routing strategy for interactions."""

    ROUND_ROBIN = "round_robin"
    LEAST_BUSY = "least_busy"
    SKILL_BASED = "skill_based"
    PRIORITY_BASED = "priority_based"
    GEOGRAPHIC = "geographic"
    CUSTOMER_HISTORY = "customer_history"


class EscalationTrigger(str, Enum):
    """Escalation trigger conditions."""

    TIME_BASED = "time_based"
    PRIORITY_BASED = "priority_based"
    KEYWORD_BASED = "keyword_based"
    SENTIMENT_BASED = "sentiment_based"
    CUSTOMER_TIER = "customer_tier"
    AGENT_REQUEST = "agent_request"


# ===== CHANNEL PLUGIN MODELS =====


class RegisteredChannel(TenantModel, AuditMixin):
    """Registry of available communication channels (plugin-based)."""

    __tablename__ = "omnichannel_registered_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(
        String(50), nullable=False
    )  # Plugin identifier (email, sms, whatsapp)
    channel_name = Column(String(100), nullable=False)  # Human readable name
    plugin_class = Column(String(200), nullable=False)  # Fully qualified class name
    capabilities = Column(JSONB, default=list)  # List of supported capabilities
    is_active = Column(Boolean, default=True)
    configuration_schema = Column(JSONB, default=dict)  # Required config fields

    # Relationships
    channel_configs = relationship(
        "ChannelConfiguration", back_populates="channel", cascade="all, delete-orphan"
    )
    contact_channels = relationship(
        "ContactCommunicationChannel", back_populates="registered_channel"
    )
    routing_rules = relationship("RoutingRule", back_populates="channel")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "channel_id", name="uq_registered_channel_tenant_channel"
        ),
        Index("ix_registered_channel_tenant", "tenant_id"),
        Index("ix_registered_channel_active", "is_active"),
    )


class ChannelConfiguration(TenantModel, AuditMixin):
    """Channel configuration per tenant (encrypted sensitive data)."""

    __tablename__ = "omnichannel_channel_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_registered_channels.id"),
        nullable=False,
    )
    configuration = Column(JSONB, default=dict)  # Encrypted configuration data
    is_enabled = Column(Boolean, default=False)
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(20), default="unknown")  # healthy, unhealthy, unknown
    error_message = Column(Text, nullable=True)

    # Performance metrics
    total_messages_sent = Column(Integer, default=0)
    total_messages_failed = Column(Integer, default=0)
    average_response_time = Column(Float, default=0.0)
    last_message_sent = Column(DateTime, nullable=True)

    # Relationships
    channel = relationship("RegisteredChannel", back_populates="channel_configs")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "channel_id", name="uq_channel_config_tenant_channel"
        ),
        Index("ix_channel_config_tenant", "tenant_id"),
        Index("ix_channel_config_enabled", "is_enabled"),
        Index("ix_channel_config_health", "health_status"),
    )


# ===== CUSTOMER & CONTACT MODELS =====


class CustomerContact(TenantModel, AuditMixin):
    """Customer contacts with dynamic channel support."""

    __tablename__ = "omnichannel_customer_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(
        UUID(as_uuid=True), nullable=False
    )  # Reference to identity.customers
    contact_type = Column(SQLEnum(ContactType), nullable=False)

    # Contact information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=True)  # Override full name if needed
    email_primary = Column(String(255), nullable=True)
    phone_primary = Column(String(50), nullable=True)

    # Status and preferences
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    preferred_language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")

    # Communication preferences
    allow_marketing = Column(Boolean, default=False)
    allow_notifications = Column(Boolean, default=True)
    quiet_hours_start = Column(String(8), nullable=True)  # HH:MM:SS
    quiet_hours_end = Column(String(8), nullable=True)

    # Relationships
    communication_channels = relationship(
        "ContactCommunicationChannel",
        back_populates="contact",
        cascade="all, delete-orphan",
    )
    interactions = relationship("CommunicationInteraction", back_populates="contact")
    conversation_threads = relationship("ConversationThread", back_populates="contact")

    @hybrid_property
    def full_name(self):
        return self.display_name or f"{self.first_name} {self.last_name}"

    __table_args__ = (
        Index("ix_customer_contact_customer", "customer_id"),
        Index("ix_customer_contact_tenant", "tenant_id"),
        Index("ix_customer_contact_primary", "is_primary"),
        Index("ix_customer_contact_active", "is_active"),
    )


class ContactCommunicationChannel(TenantModel, AuditMixin):
    """Contact's communication channels (plugin-based)."""

    __tablename__ = "omnichannel_contact_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_customer_contacts.id"),
        nullable=False,
    )
    registered_channel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_registered_channels.id"),
        nullable=False,
    )

    # Channel-specific contact information
    channel_address = Column(
        String(500), nullable=False
    )  # Email, phone, username, etc.
    channel_display_name = Column(
        String(200), nullable=True
    )  # Display name for this channel
    is_verified = Column(Boolean, default=False)
    is_preferred = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Channel metadata (plugin-specific data)
    channel_metadata = Column(JSONB, default=dict)

    # Communication preferences per channel
    opt_in_marketing = Column(Boolean, default=False)
    opt_in_notifications = Column(Boolean, default=True)

    # Relationships
    contact = relationship("CustomerContact", back_populates="communication_channels")
    registered_channel = relationship(
        "RegisteredChannel", back_populates="contact_channels"
    )
    interactions = relationship(
        "CommunicationInteraction", back_populates="channel_info"
    )

    __table_args__ = (
        UniqueConstraint(
            "contact_id",
            "registered_channel_id",
            "channel_address",
            name="uq_contact_channel_address",
        ),
        Index("ix_contact_channel_contact", "contact_id"),
        Index("ix_contact_channel_registered", "registered_channel_id"),
        Index("ix_contact_channel_verified", "is_verified"),
        Index("ix_contact_channel_active", "is_active"),
        Index("ix_contact_channel_preferred", "is_preferred"),
    )


# ===== CONVERSATION & INTERACTION MODELS =====


class ConversationThread(TenantModel, AuditMixin):
    """Conversation threading for related interactions."""

    __tablename__ = "omnichannel_conversation_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_customer_contacts.id"),
        nullable=False,
    )
    registered_channel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_registered_channels.id"),
        nullable=False,
    )

    # Thread information
    thread_subject = Column(String(500), nullable=True)
    thread_reference = Column(
        String(100), unique=True, nullable=False
    )  # External thread ID
    first_interaction_at = Column(DateTime, default=datetime.utcnow)
    last_interaction_at = Column(DateTime, default=datetime.utcnow)

    # Thread status
    is_active = Column(Boolean, default=True)
    is_resolved = Column(Boolean, default=False)
    priority_level = Column(Integer, default=3)  # 1=highest, 5=lowest

    # Thread metadata
    tags = Column(JSONB, default=list)
    context_summary = Column(Text, nullable=True)  # Brief summary of conversation

    # Relationships
    contact = relationship("CustomerContact", back_populates="conversation_threads")
    registered_channel = relationship("RegisteredChannel")
    interactions = relationship(
        "CommunicationInteraction", back_populates="conversation_thread"
    )

    @hybrid_property
    def interaction_count(self):
        return len(self.interactions)

    __table_args__ = (
        Index("ix_conversation_contact", "contact_id"),
        Index("ix_conversation_channel", "registered_channel_id"),
        Index("ix_conversation_active", "is_active"),
        Index("ix_conversation_resolved", "is_resolved"),
        Index("ix_conversation_last_interaction", "last_interaction_at"),
    )


class CommunicationInteraction(TenantModel, AuditMixin):
    """Unified communication interaction with plugin-based channels."""

    __tablename__ = "omnichannel_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interaction_reference = Column(String(100), unique=True, nullable=False)

    # Relationships
    contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_customer_contacts.id"),
        nullable=False,
    )
    channel_info_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_contact_channels.id"),
        nullable=False,
    )
    conversation_thread_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_conversation_threads.id"),
        nullable=True,
    )

    # Interaction details
    interaction_type = Column(SQLEnum(InteractionType), nullable=False)
    status = Column(SQLEnum(InteractionStatus), default=InteractionStatus.PENDING)
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text")  # text, html, markdown

    # Plugin-specific data
    channel_message_id = Column(
        String(200), nullable=True
    )  # External message ID from channel
    channel_metadata = Column(JSONB, default=dict)  # Channel-specific metadata

    # Routing and assignment
    assigned_agent_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agents.id"), nullable=True
    )
    assigned_team_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agent_teams.id"), nullable=True
    )
    priority_level = Column(Integer, default=3)  # 1=highest, 5=lowest

    # Timing and SLA
    interaction_start = Column(DateTime, default=datetime.utcnow)
    first_response_time = Column(DateTime, nullable=True)
    resolution_time = Column(DateTime, nullable=True)
    sla_due_time = Column(DateTime, nullable=True)
    is_sla_breached = Column(Boolean, default=False)

    # Analytics and tracking
    sentiment_score = Column(Float, nullable=True)  # -1 to 1 range
    satisfaction_rating = Column(Integer, nullable=True)  # 1-5 scale
    tags = Column(JSONB, default=list)
    internal_notes = Column(Text, nullable=True)

    # Relationships
    contact = relationship("CustomerContact", back_populates="interactions")
    channel_info = relationship(
        "ContactCommunicationChannel", back_populates="interactions"
    )
    conversation_thread = relationship(
        "ConversationThread", back_populates="interactions"
    )
    assigned_agent = relationship(
        "OmnichannelAgent", back_populates="assigned_interactions"
    )
    assigned_team = relationship("AgentTeam", back_populates="team_interactions")
    responses = relationship(
        "InteractionResponse",
        back_populates="interaction",
        cascade="all, delete-orphan",
    )
    escalations = relationship(
        "InteractionEscalation",
        back_populates="interaction",
        cascade="all, delete-orphan",
    )

    @hybrid_property
    def response_time_minutes(self):
        """Calculate response time in minutes."""
        if self.first_response_time and self.interaction_start:
            delta = self.first_response_time - self.interaction_start
            return delta.total_seconds() / 60
        return None

    @hybrid_property
    def is_overdue(self):
        """Check if interaction is overdue."""
        if self.sla_due_time and not self.resolution_time:
            return datetime.utcnow() > self.sla_due_time
        return False

    __table_args__ = (
        Index("ix_interaction_contact", "contact_id"),
        Index("ix_interaction_channel", "channel_info_id"),
        Index("ix_interaction_thread", "conversation_thread_id"),
        Index("ix_interaction_agent", "assigned_agent_id"),
        Index("ix_interaction_team", "assigned_team_id"),
        Index("ix_interaction_status", "status"),
        Index("ix_interaction_priority", "priority_level"),
        Index("ix_interaction_tenant_status", "tenant_id", "status"),
        Index("ix_interaction_sla_due", "sla_due_time"),
        Index("ix_interaction_created", "created_at"),
    )


# ===== AGENT MODELS =====


class OmnichannelAgent(TenantModel, AuditMixin):
    """Agent information with dynamic channel skills."""

    __tablename__ = "omnichannel_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to identity.users
    employee_id = Column(String(50), nullable=True)

    # Agent details
    display_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Status and availability
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.OFFLINE)
    max_concurrent_interactions = Column(Integer, default=5)
    current_workload = Column(Integer, default=0)

    # Skills and capabilities
    channel_skills = Column(JSONB, default=dict)  # {channel_id: skill_level}
    language_skills = Column(JSONB, default=list)  # ['en', 'es', 'fr']
    department_skills = Column(JSONB, default=list)  # ['billing', 'technical', 'sales']

    # Performance metrics (cached for quick access)
    total_interactions = Column(Integer, default=0)
    total_interactions_resolved = Column(Integer, default=0)
    average_response_time = Column(Float, default=0.0)  # in minutes
    average_resolution_time = Column(Float, default=0.0)  # in minutes
    customer_satisfaction = Column(Float, default=0.0)  # average rating

    # Availability schedule
    work_schedule = Column(JSONB, default=dict)  # Working hours per day
    timezone = Column(String(50), default="UTC")

    # Relationships
    team_memberships = relationship("AgentTeamMembership", back_populates="agent")
    assigned_interactions = relationship(
        "CommunicationInteraction", back_populates="assigned_agent"
    )
    interaction_responses = relationship("InteractionResponse", back_populates="agent")
    performance_metrics = relationship("AgentPerformanceMetric", back_populates="agent")

    @hybrid_property
    def is_available(self):
        return (
            self.status == AgentStatus.AVAILABLE
            and self.current_workload < self.max_concurrent_interactions
        )

    @hybrid_property
    def utilization_percentage(self):
        if self.max_concurrent_interactions > 0:
            return (self.current_workload / self.max_concurrent_interactions) * 100
        return 0

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_agent_tenant_user"),
        Index("ix_agent_user", "user_id"),
        Index("ix_agent_status", "status"),
        Index("ix_agent_workload", "current_workload"),
        Index("ix_agent_tenant", "tenant_id"),
    )


class AgentTeam(TenantModel, AuditMixin):
    """Agent teams for workload distribution and specialization."""

    __tablename__ = "omnichannel_agent_teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Team capabilities
    supported_channels = Column(JSONB, default=list)  # List of channel_ids
    supported_languages = Column(JSONB, default=list)
    supported_departments = Column(JSONB, default=list)

    # Team settings
    max_queue_size = Column(Integer, default=100)
    routing_strategy = Column(
        SQLEnum(RoutingStrategy), default=RoutingStrategy.ROUND_ROBIN
    )

    # Team schedule and SLA
    operating_hours = Column(JSONB, default=dict)  # Operating hours per day
    sla_response_minutes = Column(Integer, default=15)  # Response SLA in minutes
    sla_resolution_minutes = Column(Integer, default=240)  # Resolution SLA in minutes

    # Relationships
    team_memberships = relationship("AgentTeamMembership", back_populates="team")
    team_interactions = relationship(
        "CommunicationInteraction", back_populates="assigned_team"
    )
    routing_rules = relationship("RoutingRule", back_populates="target_team")

    @hybrid_property
    def member_count(self):
        return len([m for m in self.team_memberships if m.is_active])

    @hybrid_property
    def available_agents_count(self):
        return len(
            [m for m in self.team_memberships if m.is_active and m.agent.is_available]
        )

    __table_args__ = (
        Index("ix_agent_team_active", "is_active"),
        Index("ix_agent_team_tenant", "tenant_id"),
    )


# Association table for agent-team many-to-many relationship
class AgentTeamMembership(TenantModel, AuditMixin):
    """Agent team membership with roles and specializations."""

    __tablename__ = "omnichannel_agent_team_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agents.id"), nullable=False
    )
    team_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agent_teams.id"), nullable=False
    )

    # Membership details
    is_team_lead = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    specializations = Column(JSONB, default=list)  # Special roles within team

    # Relationships
    agent = relationship("OmnichannelAgent", back_populates="team_memberships")
    team = relationship("AgentTeam", back_populates="team_memberships")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "agent_id", "team_id", name="uq_agent_team_membership"
        ),
        Index("ix_agent_team_membership_agent", "agent_id"),
        Index("ix_agent_team_membership_team", "team_id"),
        Index("ix_agent_team_membership_active", "is_active"),
    )


# ===== ROUTING MODELS =====


class RoutingRule(TenantModel, AuditMixin):
    """Routing rules for intelligent interaction assignment."""

    __tablename__ = "omnichannel_routing_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=5)  # 1=highest, 10=lowest

    # Rule conditions
    channel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_registered_channels.id"),
        nullable=True,
    )
    priority_condition = Column(Integer, nullable=True)
    customer_tier_condition = Column(String(50), nullable=True)
    time_condition = Column(JSONB, nullable=True)  # Business hours, days of week
    keyword_conditions = Column(JSONB, default=list)
    language_condition = Column(String(10), nullable=True)

    # Rule actions
    target_team_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agent_teams.id"), nullable=True
    )
    target_agent_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agents.id"), nullable=True
    )
    priority_override = Column(Integer, nullable=True)
    sla_override_minutes = Column(Integer, nullable=True)

    # Relationships
    channel = relationship("RegisteredChannel", back_populates="routing_rules")
    target_team = relationship("AgentTeam", back_populates="routing_rules")
    target_agent = relationship("OmnichannelAgent")

    __table_args__ = (
        Index("ix_routing_rule_active", "is_active"),
        Index("ix_routing_rule_priority", "priority"),
        Index("ix_routing_rule_channel", "channel_id"),
        Index("ix_routing_rule_tenant", "tenant_id"),
    )


# ===== RESPONSE & ESCALATION MODELS =====


class InteractionResponse(TenantModel, AuditMixin):
    """Responses to customer interactions."""

    __tablename__ = "omnichannel_interaction_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interaction_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_interactions.id"), nullable=False
    )
    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agents.id"), nullable=False
    )

    # Response content
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text")  # text, html, template
    is_internal = Column(Boolean, default=False)  # Internal note vs customer response

    # Response delivery
    channel_message_id = Column(String(200), nullable=True)  # External message ID
    delivery_status = Column(
        String(50), default="pending"
    )  # pending, sent, delivered, failed
    delivery_timestamp = Column(DateTime, nullable=True)
    delivery_metadata = Column(JSONB, default=dict)

    # Response metadata
    response_time_seconds = Column(Integer, nullable=True)
    attachments = Column(JSONB, default=list)
    template_used = Column(String(100), nullable=True)

    # Relationships
    interaction = relationship("CommunicationInteraction", back_populates="responses")
    agent = relationship("OmnichannelAgent", back_populates="interaction_responses")

    __table_args__ = (
        Index("ix_response_interaction", "interaction_id"),
        Index("ix_response_agent", "agent_id"),
        Index("ix_response_delivery_status", "delivery_status"),
        Index("ix_response_created", "created_at"),
        Index("ix_response_tenant", "tenant_id"),
    )


class InteractionEscalation(TenantModel, AuditMixin):
    """Escalation tracking for interactions."""

    __tablename__ = "omnichannel_interaction_escalations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interaction_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_interactions.id"), nullable=False
    )

    # Escalation details
    escalation_level = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    trigger_type = Column(SQLEnum(EscalationTrigger), nullable=False)
    trigger_reason = Column(Text, nullable=False)

    # Escalation assignment
    escalated_from_agent_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agents.id"), nullable=True
    )
    escalated_to_agent_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agents.id"), nullable=True
    )
    escalated_to_team_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agent_teams.id"), nullable=True
    )

    # Escalation timing
    escalated_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    is_resolved = Column(Boolean, default=False)

    # Escalation notes
    escalation_notes = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Relationships
    interaction = relationship("CommunicationInteraction", back_populates="escalations")
    escalated_from_agent = relationship(
        "OmnichannelAgent", foreign_keys=[escalated_from_agent_id]
    )
    escalated_to_agent = relationship(
        "OmnichannelAgent", foreign_keys=[escalated_to_agent_id]
    )
    escalated_to_team = relationship("AgentTeam")

    __table_args__ = (
        Index("ix_escalation_interaction", "interaction_id"),
        Index("ix_escalation_level", "escalation_level"),
        Index("ix_escalation_trigger", "trigger_type"),
        Index("ix_escalation_resolved", "is_resolved"),
        Index("ix_escalation_tenant", "tenant_id"),
    )


# ===== PERFORMANCE METRICS MODELS =====


class AgentPerformanceMetric(TenantModel, AuditMixin):
    """Agent performance metrics (daily aggregates)."""

    __tablename__ = "omnichannel_agent_performance_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agents.id"), nullable=False
    )
    metric_date = Column(DateTime, nullable=False)  # Date for this metric period

    # Interaction metrics
    total_interactions = Column(Integer, default=0)
    interactions_resolved = Column(Integer, default=0)
    interactions_escalated = Column(Integer, default=0)
    average_response_time_minutes = Column(Float, default=0.0)
    average_resolution_time_minutes = Column(Float, default=0.0)

    # Quality metrics
    customer_satisfaction_average = Column(Float, default=0.0)
    customer_satisfaction_count = Column(Integer, default=0)
    sla_breaches = Column(Integer, default=0)

    # Activity metrics
    online_time_minutes = Column(Integer, default=0)
    active_time_minutes = Column(
        Integer, default=0
    )  # Time actually handling interactions
    utilization_percentage = Column(Float, default=0.0)

    # Channel-specific metrics
    channel_metrics = Column(JSONB, default=dict)  # Per-channel performance data

    # Relationships
    agent = relationship("OmnichannelAgent", back_populates="performance_metrics")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "agent_id", "metric_date", name="uq_agent_metric_date"
        ),
        Index("ix_agent_metric_agent", "agent_id"),
        Index("ix_agent_metric_date", "metric_date"),
        Index("ix_agent_metric_tenant", "tenant_id"),
    )


class ChannelAnalytics(TenantModel, AuditMixin):
    """Channel performance analytics (daily aggregates)."""

    __tablename__ = "omnichannel_channel_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registered_channel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_registered_channels.id"),
        nullable=False,
    )
    metric_date = Column(DateTime, nullable=False)

    # Volume metrics
    total_interactions = Column(Integer, default=0)
    inbound_interactions = Column(Integer, default=0)
    outbound_interactions = Column(Integer, default=0)

    # Performance metrics
    average_response_time_minutes = Column(Float, default=0.0)
    average_resolution_time_minutes = Column(Float, default=0.0)
    customer_satisfaction_average = Column(Float, default=0.0)
    customer_satisfaction_count = Column(Integer, default=0)

    # Technical metrics
    plugin_uptime_percentage = Column(Float, default=0.0)
    plugin_error_count = Column(Integer, default=0)
    message_delivery_rate = Column(Float, default=0.0)

    # Relationships
    registered_channel = relationship("RegisteredChannel")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "registered_channel_id",
            "metric_date",
            name="uq_channel_analytics_date",
        ),
        Index("ix_channel_analytics_channel", "registered_channel_id"),
        Index("ix_channel_analytics_date", "metric_date"),
        Index("ix_channel_analytics_tenant", "tenant_id"),
    )
