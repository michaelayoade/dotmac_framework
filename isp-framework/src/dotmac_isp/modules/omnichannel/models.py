"""Omnichannel communication system models."""

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


class CommunicationChannel(str, Enum):
    """Communication channel types."""

    EMAIL = "email"
    PHONE = "phone"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TELEGRAM = "telegram"
    LIVE_CHAT = "live_chat"
    WEB_PORTAL = "web_portal"
    MOBILE_APP = "mobile_app"
    WALK_IN = "walk_in"
    VIDEO_CALL = "video_call"
    SLACK = "slack"
    TEAMS = "teams"


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


# ===== CORE MODELS =====


class CustomerContact(TenantModel, AuditMixin):
    """Multiple contacts per customer with detailed information."""

    __tablename__ = "customer_contacts"

    # Core identification
    customer_id = Column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True
    )
    contact_type = Column(SQLEnum(ContactType), nullable=False, index=True)

    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=True)
    title = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)

    # Contact preferences
    primary_language = Column(String(10), default="en", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    preferred_contact_method = Column(SQLEnum(CommunicationChannel), nullable=True)

    # Status and permissions
    is_primary = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    can_authorize_changes = Column(Boolean, default=False, nullable=False)
    can_receive_billing = Column(Boolean, default=False, nullable=False)
    can_receive_technical = Column(Boolean, default=False, nullable=False)

    # Communication preferences
    marketing_opt_in = Column(Boolean, default=False, nullable=False)
    sms_opt_in = Column(Boolean, default=False, nullable=False)
    email_opt_in = Column(Boolean, default=True, nullable=False)

    # Additional data
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSONB, nullable=True)
    tags = Column(JSONB, nullable=True)  # Searchable tags

    # Relationships
    customer = relationship("Customer")
    communication_channels = relationship(
        "ContactCommunicationChannel",
        back_populates="contact",
        cascade="all, delete-orphan",
    )
    interactions = relationship("CommunicationInteraction", back_populates="contact")

    __table_args__ = (
        Index("ix_contacts_customer_type", "customer_id", "contact_type"),
        Index("ix_contacts_primary", "customer_id", "is_primary"),
    )

    @property
    def full_name(self) -> str:
        """Get contact's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self):
        """  Repr   operation."""
        return f"<CustomerContact(customer_id='{self.customer_id}', name='{self.full_name}', type='{self.contact_type}')>"


class ContactCommunicationChannel(TenantModel, AuditMixin):
    """Communication channels for each contact."""

    __tablename__ = "contact_communication_channels"

    # Channel identification
    contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_contacts.id"),
        nullable=False,
        index=True,
    )
    channel_type = Column(SQLEnum(CommunicationChannel), nullable=False, index=True)

    # Channel details
    channel_value = Column(
        String(500), nullable=False
    )  # Email, phone, social media handle, etc.
    channel_display_name = Column(String(200), nullable=True)  # Friendly display name

    # Verification and status
    is_verified = Column(Boolean, default=False, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    verification_date = Column(DateTime(timezone=True), nullable=True)

    # Platform-specific data
    platform_user_id = Column(String(255), nullable=True)  # Social media user ID
    platform_username = Column(String(255), nullable=True)  # Social media username
    platform_data = Column(JSONB, nullable=True)  # Additional platform-specific info

    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)

    # Quality metrics
    response_rate = Column(Float, nullable=True)  # Percentage of responses received
    avg_response_time = Column(Float, nullable=True)  # Average response time in minutes
    bounce_rate = Column(Float, nullable=True)  # Bounce rate for email/SMS

    # Additional metadata
    channel_metadata = Column(JSONB, nullable=True)

    # Relationships
    contact = relationship("CustomerContact", back_populates="communication_channels")
    interactions = relationship("CommunicationInteraction", back_populates="channel")

    __table_args__ = (
        Index("ix_channels_contact_type", "contact_id", "channel_type"),
        Index("ix_channels_type_value", "channel_type", "channel_value"),
        UniqueConstraint(
            "contact_id",
            "channel_type",
            "channel_value",
            name="uq_contact_channel_value",
        ),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<ContactCommunicationChannel(contact_id='{self.contact_id}', type='{self.channel_type}', value='{self.channel_value}')>"


class CommunicationInteraction(TenantModel, AuditMixin):
    """Unified communication interaction history across all channels."""

    __tablename__ = "communication_interactions"

    # Interaction identification
    interaction_reference = Column(String(100), unique=True, nullable=False, index=True)

    # Core relationships
    customer_id = Column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True
    )
    contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_contacts.id"),
        nullable=True,
        index=True,
    )
    channel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contact_communication_channels.id"),
        nullable=True,
        index=True,
    )

    # Interaction classification
    channel_type = Column(SQLEnum(CommunicationChannel), nullable=False, index=True)
    interaction_type = Column(SQLEnum(InteractionType), nullable=False, index=True)
    status = Column(
        SQLEnum(InteractionStatus),
        default=InteractionStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Content and metadata
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    content_type = Column(
        String(50), default="text", nullable=False
    )  # text, html, json, etc.

    # Platform-specific data
    external_id = Column(String(255), nullable=True, index=True)  # Platform message ID
    external_thread_id = Column(
        String(255), nullable=True, index=True
    )  # Platform thread/conversation ID
    platform_data = Column(JSONB, nullable=True)

    # Agent and routing
    assigned_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_agents.id"),
        nullable=True,
        index=True,
    )
    assigned_team = Column(String(100), nullable=True, index=True)
    routing_data = Column(JSONB, nullable=True)

    # Timing
    received_at = Column(DateTime(timezone=True), nullable=False, index=True)
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    last_response_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Classification and analysis
    category = Column(String(100), nullable=True, index=True)
    subcategory = Column(String(100), nullable=True)
    intent = Column(String(100), nullable=True)  # AI-detected customer intent
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    language = Column(String(10), nullable=True)

    # Priority and urgency
    priority = Column(String(20), default="normal", nullable=False, index=True)
    urgency_score = Column(Float, nullable=True)  # 0.0 to 1.0
    escalation_level = Column(Integer, default=0, nullable=False)

    # Response metrics
    response_count = Column(Integer, default=0, nullable=False)
    response_time_seconds = Column(Integer, nullable=True)
    resolution_time_seconds = Column(Integer, nullable=True)
    customer_satisfaction = Column(Float, nullable=True)  # 1.0 to 5.0

    # Tags and categorization
    tags = Column(JSONB, nullable=True)
    keywords = Column(JSONB, nullable=True)  # Extracted keywords

    # Business context
    related_ticket_id = Column(
        UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=True, index=True
    )
    related_order_id = Column(String(100), nullable=True, index=True)
    related_service_id = Column(String(100), nullable=True, index=True)

    # Additional data
    custom_fields = Column(JSONB, nullable=True)
    attachments = Column(JSONB, nullable=True)  # File attachments metadata

    # Relationships
    customer = relationship("Customer")
    contact = relationship("CustomerContact", back_populates="interactions")
    channel = relationship("ContactCommunicationChannel", back_populates="interactions")
    assigned_agent = relationship("OmnichannelAgent", back_populates="interactions")
    related_ticket = relationship("Ticket")
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

    __table_args__ = (
        Index("ix_interactions_customer_channel", "customer_id", "channel_type"),
        Index("ix_interactions_agent_status", "assigned_agent_id", "status"),
        Index("ix_interactions_received", "received_at"),
        Index("ix_interactions_priority", "priority", "received_at"),
    )

    @hybrid_property
    def is_resolved(self) -> bool:
        """Check if interaction is resolved."""
        return self.status == InteractionStatus.COMPLETED

    @hybrid_property
    def response_time_minutes(self) -> Optional[float]:
        """Get response time in minutes."""
        if self.response_time_seconds:
            return self.response_time_seconds / 60.0
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<CommunicationInteraction(ref='{self.interaction_reference}', channel='{self.channel_type}', status='{self.status}')>"


class InteractionResponse(TenantModel, AuditMixin):
    """Individual responses within an interaction."""

    __tablename__ = "interaction_responses"

    # Response identification
    interaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("communication_interactions.id"),
        nullable=False,
        index=True,
    )
    sequence_number = Column(Integer, nullable=False)  # Order within interaction

    # Response details
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text", nullable=False)
    is_internal = Column(
        Boolean, default=False, nullable=False
    )  # Internal note vs customer-facing

    # Author information
    author_type = Column(String(50), nullable=False)  # agent, customer, system
    author_id = Column(UUID(as_uuid=True), nullable=True)  # Agent or user ID
    author_name = Column(String(255), nullable=True)

    # Timing
    sent_at = Column(DateTime(timezone=True), nullable=False, index=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Platform-specific
    external_id = Column(String(255), nullable=True)  # Platform response ID
    platform_data = Column(JSONB, nullable=True)

    # Analysis
    sentiment = Column(String(20), nullable=True)
    sentiment_score = Column(Float, nullable=True)

    # Attachments and metadata
    attachments = Column(JSONB, nullable=True)
    response_metadata = Column(JSONB, nullable=True)

    # Relationships
    interaction = relationship("CommunicationInteraction", back_populates="responses")

    __table_args__ = (
        Index("ix_responses_interaction_sequence", "interaction_id", "sequence_number"),
        Index("ix_responses_sent", "sent_at"),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<InteractionResponse(interaction_id='{self.interaction_id}', seq={self.sequence_number}, author='{self.author_type}')>"


# ===== AGENT MANAGEMENT =====


class OmnichannelAgent(TenantModel, AuditMixin):
    """Omnichannel support agents with skills and performance tracking."""

    __tablename__ = "omnichannel_agents"

    # Agent identification
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    agent_code = Column(String(50), unique=True, nullable=False, index=True)

    # Agent profile
    display_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)

    # Status and availability
    status = Column(
        SQLEnum(AgentStatus), default=AgentStatus.OFFLINE, nullable=False, index=True
    )
    last_activity = Column(DateTime(timezone=True), nullable=True)
    status_message = Column(String(500), nullable=True)

    # Team and hierarchy
    team_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_teams.id"), nullable=True, index=True
    )
    supervisor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_agents.id"),
        nullable=True,
        index=True,
    )
    role_level = Column(
        String(50), default="agent", nullable=False
    )  # agent, senior, lead, supervisor, manager

    # Skills and capabilities
    supported_channels = Column(
        JSONB, nullable=False
    )  # List of channels agent can handle
    skill_tags = Column(JSONB, nullable=True)  # Technical skills, languages, etc.
    max_concurrent_interactions = Column(Integer, default=5, nullable=False)

    # Work schedule
    work_schedule = Column(JSONB, nullable=True)  # Weekly schedule
    timezone = Column(String(50), default="UTC", nullable=False)
    is_24x7 = Column(Boolean, default=False, nullable=False)

    # Performance configuration
    target_response_time = Column(Integer, default=300, nullable=False)  # Seconds
    target_resolution_time = Column(Integer, default=3600, nullable=False)  # Seconds
    quality_threshold = Column(Float, default=4.0, nullable=False)  # 1-5 scale

    # Current workload
    current_interactions = Column(Integer, default=0, nullable=False)
    current_load_percentage = Column(Float, default=0.0, nullable=False)

    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    hire_date = Column(DateTime(timezone=True), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Performance metrics (cached for quick access)
    total_interactions = Column(Integer, default=0, nullable=False)
    avg_response_time = Column(Float, nullable=True)  # Minutes
    avg_resolution_time = Column(Float, nullable=True)  # Minutes
    customer_satisfaction = Column(Float, nullable=True)  # 1-5 scale
    resolution_rate = Column(Float, nullable=True)  # Percentage

    # Additional data
    custom_fields = Column(JSONB, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User")
    team = relationship("AgentTeam", back_populates="agents")
    supervisor = relationship("OmnichannelAgent", remote_side="OmnichannelAgent.id")
    subordinates = relationship("OmnichannelAgent")
    interactions = relationship(
        "CommunicationInteraction", back_populates="assigned_agent"
    )
    performance_metrics = relationship(
        "AgentPerformanceMetric", back_populates="agent", cascade="all, delete-orphan"
    )
    schedules = relationship(
        "AgentSchedule", back_populates="agent", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_agents_status_team", "status", "team_id"),
        Index("ix_agents_activity", "last_activity"),
    )

    @hybrid_property
    def is_available(self) -> bool:
        """Check if agent is available for new interactions."""
        return (
            self.status == AgentStatus.AVAILABLE
            and self.current_interactions < self.max_concurrent_interactions
            and self.is_active
        )

    @hybrid_property
    def utilization_rate(self) -> float:
        """Calculate current utilization rate."""
        if self.max_concurrent_interactions > 0:
            return self.current_interactions / self.max_concurrent_interactions
        return 0.0

    def __repr__(self):
        """  Repr   operation."""
        return f"<OmnichannelAgent(code='{self.agent_code}', name='{self.display_name}', status='{self.status}')>"


class AgentTeam(TenantModel, AuditMixin):
    """Agent teams for organization and routing."""

    __tablename__ = "agent_teams"

    # Team identification
    team_name = Column(String(200), nullable=False)
    team_code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Team configuration
    supported_channels = Column(JSONB, nullable=False)  # Channels this team handles
    specializations = Column(JSONB, nullable=True)  # What this team specializes in

    # Routing configuration
    routing_strategy = Column(
        SQLEnum(RoutingStrategy), default=RoutingStrategy.ROUND_ROBIN, nullable=False
    )
    max_queue_size = Column(Integer, default=50, nullable=False)
    escalation_team_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_teams.id"), nullable=True
    )

    # Team lead
    team_lead_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_agents.id"),
        nullable=True,
        index=True,
    )

    # Business hours
    business_hours = Column(JSONB, nullable=True)  # Team availability schedule
    timezone = Column(String(50), default="UTC", nullable=False)

    # Performance targets
    target_response_time = Column(Integer, default=300, nullable=False)  # Seconds
    target_resolution_time = Column(Integer, default=3600, nullable=False)  # Seconds
    target_satisfaction = Column(Float, default=4.0, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Additional data
    custom_fields = Column(JSONB, nullable=True)

    # Relationships
    agents = relationship("OmnichannelAgent", back_populates="team")
    team_lead = relationship("OmnichannelAgent")
    escalation_team = relationship("AgentTeam", remote_side="AgentTeam.id")
    routing_rules = relationship("RoutingRule", back_populates="team")

    __table_args__ = (Index("ix_teams_active", "is_active"),)

    def __repr__(self):
        """  Repr   operation."""
        return f"<AgentTeam(code='{self.team_code}', name='{self.team_name}')>"


# ===== ROUTING AND ESCALATION =====


class RoutingRule(TenantModel, AuditMixin):
    """Intelligent routing rules for interactions."""

    __tablename__ = "routing_rules"

    # Rule identification
    rule_name = Column(String(255), nullable=False)
    rule_code = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Rule configuration
    priority = Column(
        Integer, default=0, nullable=False, index=True
    )  # Higher number = higher priority
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Conditions (JSON rules engine)
    conditions = Column(JSONB, nullable=False)  # When this rule applies

    # Routing actions
    target_team_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_teams.id"), nullable=True, index=True
    )
    target_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_agents.id"),
        nullable=True,
        index=True,
    )
    routing_strategy = Column(SQLEnum(RoutingStrategy), nullable=True)

    # Priority adjustments
    priority_boost = Column(Integer, default=0, nullable=False)
    urgency_multiplier = Column(Float, default=1.0, nullable=False)

    # Time-based rules
    business_hours_only = Column(Boolean, default=False, nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)
    success_rate = Column(Float, nullable=True)

    # Additional configuration
    custom_fields = Column(JSONB, nullable=True)

    # Relationships
    team = relationship("AgentTeam", back_populates="routing_rules")
    target_agent = relationship("OmnichannelAgent")

    __table_args__ = (Index("ix_routing_rules_priority", "priority", "is_active"),)

    def __repr__(self):
        """  Repr   operation."""
        return f"<RoutingRule(code='{self.rule_code}', name='{self.rule_name}')>"


class InteractionEscalation(TenantModel, AuditMixin):
    """Interaction escalation tracking."""

    __tablename__ = "interaction_escalations"

    # Escalation identification
    interaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("communication_interactions.id"),
        nullable=False,
        index=True,
    )
    escalation_level = Column(Integer, nullable=False)  # 1, 2, 3, etc.

    # Escalation trigger
    trigger_type = Column(SQLEnum(EscalationTrigger), nullable=False, index=True)
    trigger_details = Column(JSONB, nullable=True)

    # From/To assignment
    from_agent_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agents.id"), nullable=True
    )
    from_team_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_teams.id"), nullable=True
    )
    to_agent_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agents.id"), nullable=True
    )
    to_team_id = Column(UUID(as_uuid=True), ForeignKey("agent_teams.id"), nullable=True)

    # Escalation timing
    escalated_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Escalation details
    reason = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)

    # Status
    status = Column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, acknowledged, resolved

    # Relationships
    interaction = relationship("CommunicationInteraction", back_populates="escalations")
    from_agent = relationship("OmnichannelAgent", foreign_keys=[from_agent_id])
    from_team = relationship("AgentTeam", foreign_keys=[from_team_id])
    to_agent = relationship("OmnichannelAgent", foreign_keys=[to_agent_id])
    to_team = relationship("AgentTeam", foreign_keys=[to_team_id])

    __table_args__ = (
        Index("ix_escalations_interaction_level", "interaction_id", "escalation_level"),
        Index("ix_escalations_status", "status", "escalated_at"),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<InteractionEscalation(interaction_id='{self.interaction_id}', level={self.escalation_level})>"


# ===== ANALYTICS AND PERFORMANCE =====


class AgentPerformanceMetric(TenantModel):
    """Agent performance metrics tracking."""

    __tablename__ = "agent_performance_metrics"

    # Metric identification
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_agents.id"),
        nullable=False,
        index=True,
    )
    metric_date = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_period = Column(
        String(20), nullable=False, index=True
    )  # daily, weekly, monthly, yearly

    # Volume metrics
    total_interactions = Column(Integer, default=0, nullable=False)
    interactions_by_channel = Column(JSONB, nullable=True)  # Channel breakdown

    # Response time metrics
    avg_response_time_seconds = Column(Float, nullable=True)
    median_response_time_seconds = Column(Float, nullable=True)
    first_response_sla_met_count = Column(Integer, default=0, nullable=False)
    first_response_sla_total_count = Column(Integer, default=0, nullable=False)

    # Resolution metrics
    avg_resolution_time_seconds = Column(Float, nullable=True)
    median_resolution_time_seconds = Column(Float, nullable=True)
    resolution_sla_met_count = Column(Integer, default=0, nullable=False)
    resolution_sla_total_count = Column(Integer, default=0, nullable=False)

    # Quality metrics
    customer_satisfaction_avg = Column(Float, nullable=True)  # 1-5 scale
    customer_satisfaction_count = Column(Integer, default=0, nullable=False)
    resolution_rate = Column(Float, nullable=True)  # Percentage
    escalation_rate = Column(Float, nullable=True)  # Percentage

    # Activity metrics
    active_time_minutes = Column(Float, default=0.0, nullable=False)
    idle_time_minutes = Column(Float, default=0.0, nullable=False)
    break_time_minutes = Column(Float, default=0.0, nullable=False)

    # Workload metrics
    max_concurrent_interactions = Column(Integer, default=0, nullable=False)
    avg_concurrent_interactions = Column(Float, default=0.0, nullable=False)
    utilization_rate = Column(Float, default=0.0, nullable=False)  # Percentage

    # Channel-specific metrics
    channel_performance = Column(JSONB, nullable=True)  # Performance by channel

    # Quality scores
    qa_score_avg = Column(Float, nullable=True)  # Quality assurance scores
    qa_score_count = Column(Integer, default=0, nullable=False)

    # Additional metrics
    custom_metrics = Column(JSONB, nullable=True)

    # Relationships
    agent = relationship("OmnichannelAgent", back_populates="performance_metrics")

    __table_args__ = (
        Index("ix_metrics_agent_date", "agent_id", "metric_date"),
        Index("ix_metrics_period", "metric_period", "metric_date"),
        UniqueConstraint(
            "agent_id", "metric_date", "metric_period", name="uq_agent_metric_period"
        ),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<AgentPerformanceMetric(agent_id='{self.agent_id}', date='{self.metric_date}', period='{self.metric_period}')>"


class AgentSchedule(TenantModel, AuditMixin):
    """Agent work schedules and availability."""

    __tablename__ = "agent_schedules"

    # Schedule identification
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_agents.id"),
        nullable=False,
        index=True,
    )
    schedule_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Schedule details
    shift_start = Column(DateTime(timezone=True), nullable=False)
    shift_end = Column(DateTime(timezone=True), nullable=False)
    break_start = Column(DateTime(timezone=True), nullable=True)
    break_end = Column(DateTime(timezone=True), nullable=True)

    # Schedule type
    schedule_type = Column(
        String(50), default="regular", nullable=False
    )  # regular, overtime, on_call, training
    is_flexible = Column(Boolean, default=False, nullable=False)

    # Availability
    is_available = Column(Boolean, default=True, nullable=False)
    max_interactions = Column(Integer, nullable=True)  # Override default
    supported_channels = Column(JSONB, nullable=True)  # Override default

    # Status
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        String(50), default="scheduled", nullable=False
    )  # scheduled, active, completed, no_show

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    agent = relationship("OmnichannelAgent", back_populates="schedules")

    __table_args__ = (
        Index("ix_schedules_agent_date", "agent_id", "schedule_date"),
        Index("ix_schedules_shift", "shift_start", "shift_end"),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<AgentSchedule(agent_id='{self.agent_id}', date='{self.schedule_date}', type='{self.schedule_type}')>"


# ===== COMMUNICATION ANALYTICS =====


class ChannelAnalytics(TenantModel):
    """Channel-specific analytics and performance metrics."""

    __tablename__ = "channel_analytics"

    # Analytics identification
    channel_type = Column(SQLEnum(CommunicationChannel), nullable=False, index=True)
    metric_date = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_period = Column(
        String(20), nullable=False, index=True
    )  # hourly, daily, weekly, monthly

    # Volume metrics
    total_interactions = Column(Integer, default=0, nullable=False)
    inbound_interactions = Column(Integer, default=0, nullable=False)
    outbound_interactions = Column(Integer, default=0, nullable=False)

    # Response metrics
    avg_response_time_seconds = Column(Float, nullable=True)
    median_response_time_seconds = Column(Float, nullable=True)
    response_rate = Column(
        Float, nullable=True
    )  # Percentage of interactions with responses

    # Resolution metrics
    avg_resolution_time_seconds = Column(Float, nullable=True)
    resolution_rate = Column(Float, nullable=True)  # Percentage resolved
    escalation_rate = Column(Float, nullable=True)  # Percentage escalated

    # Quality metrics
    customer_satisfaction_avg = Column(Float, nullable=True)
    customer_satisfaction_count = Column(Integer, default=0, nullable=False)

    # Engagement metrics
    bounce_rate = Column(Float, nullable=True)  # Percentage of failed deliveries
    click_through_rate = Column(Float, nullable=True)  # For channels with links
    conversion_rate = Column(Float, nullable=True)  # Percentage leading to resolution

    # Sentiment analysis
    sentiment_positive = Column(Integer, default=0, nullable=False)
    sentiment_neutral = Column(Integer, default=0, nullable=False)
    sentiment_negative = Column(Integer, default=0, nullable=False)
    avg_sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0

    # Cost metrics
    total_cost = Column(Float, nullable=True)  # Cost for this channel/period
    cost_per_interaction = Column(Float, nullable=True)
    cost_currency = Column(String(3), default="USD", nullable=True)

    # Additional metrics
    custom_metrics = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_channel_analytics_channel_date", "channel_type", "metric_date"),
        Index("ix_channel_analytics_period", "metric_period", "metric_date"),
        UniqueConstraint(
            "channel_type",
            "metric_date",
            "metric_period",
            name="uq_channel_metric_period",
        ),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<ChannelAnalytics(channel='{self.channel_type}', date='{self.metric_date}', period='{self.metric_period}')>"


class CustomerCommunicationSummary(TenantModel, AuditMixin):
    """Customer communication summary and history overview."""

    __tablename__ = "customer_communication_summaries"

    # Customer identification
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Overall statistics
    total_interactions = Column(Integer, default=0, nullable=False)
    first_interaction_date = Column(DateTime(timezone=True), nullable=True)
    last_interaction_date = Column(DateTime(timezone=True), nullable=True)

    # Channel preferences (inferred from usage)
    preferred_channels = Column(JSONB, nullable=True)  # Ordered list
    channel_usage_stats = Column(JSONB, nullable=True)  # Usage count by channel

    # Response patterns
    avg_response_time_minutes = Column(Float, nullable=True)
    typical_response_hours = Column(
        JSONB, nullable=True
    )  # When customer typically responds

    # Satisfaction and sentiment
    avg_satisfaction_score = Column(Float, nullable=True)
    overall_sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    sentiment_trend = Column(String(20), nullable=True)  # improving, declining, stable

    # Issue patterns
    common_categories = Column(JSONB, nullable=True)  # Most common issue categories
    resolution_rate = Column(Float, nullable=True)  # Percentage of issues resolved
    escalation_frequency = Column(
        Float, nullable=True
    )  # How often issues are escalated

    # Communication preferences
    marketing_engaged = Column(Boolean, default=False, nullable=False)
    prefers_self_service = Column(Boolean, default=False, nullable=False)
    communication_frequency_preference = Column(
        String(20), nullable=True
    )  # high, medium, low

    # Risk indicators
    churn_risk_score = Column(Float, nullable=True)  # 0.0 to 1.0
    satisfaction_trend = Column(
        String(20), nullable=True
    )  # improving, declining, stable
    last_complaint_date = Column(DateTime(timezone=True), nullable=True)

    # Profile tags
    communication_profile_tags = Column(JSONB, nullable=True)  # AI-generated tags

    # Cache timestamps
    last_calculated = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Relationships
    customer = relationship("Customer")

    __table_args__ = (
        Index("ix_comm_summary_last_interaction", "last_interaction_date"),
        Index("ix_comm_summary_churn_risk", "churn_risk_score"),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<CustomerCommunicationSummary(customer_id='{self.customer_id}', interactions={self.total_interactions})>"
