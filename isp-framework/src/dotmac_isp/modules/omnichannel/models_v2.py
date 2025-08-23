"""Omnichannel communication system models with plugin-based architecture."""

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


# ===== ENUMS (Keep non-channel enums) =====


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


class RegisteredChannel(TenantModel, AuditMixin):
    """Registry of available communication channels."""

    __tablename__ = "omnichannel_registered_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(String(50), nullable=False)  # Plugin identifier
    channel_name = Column(String(100), nullable=False)  # Human readable name
    plugin_class = Column(String(200), nullable=False)  # Fully qualified class name
    capabilities = Column(JSONB, default=list)  # List of supported capabilities
    is_active = Column(Boolean, default=True)
    configuration_schema = Column(JSONB, default=dict)  # Required config fields

    # Plugin configuration per tenant
    channel_configs = relationship("ChannelConfiguration", back_populates="channel")

    __table_args__ = (
        UniqueConstraint("tenant_id", "channel_id", name="_tenant_channel_uc"),
        Index("idx_registered_channel_tenant", "tenant_id"),
        Index("idx_registered_channel_active", "is_active"),
    )


class ChannelConfiguration(TenantModel, AuditMixin):
    """Channel configuration per tenant."""

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

    # Relationships
    channel = relationship("RegisteredChannel", back_populates="channel_configs")

    __table_args__ = (
        UniqueConstraint("tenant_id", "channel_id", name="_tenant_channel_config_uc"),
        Index("idx_channel_config_tenant", "tenant_id"),
        Index("idx_channel_config_enabled", "is_enabled"),
    )


class CustomerContact(TenantModel, AuditMixin):
    """Customer contacts with dynamic channel support."""

    __tablename__ = "omnichannel_customer_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to customer
    contact_type = Column(SQLEnum(ContactType), nullable=False)

    # Contact information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email_primary = Column(String(255))
    phone_primary = Column(String(50))

    # Status and preferences
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    preferred_language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")

    # Communication preferences
    communication_channels = relationship(
        "ContactCommunicationChannel", back_populates="contact"
    )
    interactions = relationship("CommunicationInteraction", back_populates="contact")

    @hybrid_property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    __table_args__ = (
        Index("idx_customer_contact_customer", "customer_id"),
        Index("idx_customer_contact_tenant", "tenant_id"),
        Index("idx_customer_contact_primary", "is_primary"),
    )


class ContactCommunicationChannel(TenantModel, AuditMixin):
    """Contact's communication channels (dynamic based on registered plugins)."""

    __tablename__ = "omnichannel_contact_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_customer_contacts.id"),
        nullable=False,
    )
    channel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("omnichannel_registered_channels.id"),
        nullable=False,
    )

    # Channel-specific contact information
    channel_address = Column(
        String(500), nullable=False
    )  # Email, phone, username, etc.
    is_verified = Column(Boolean, default=False)
    is_preferred = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Channel metadata (plugin-specific data)
    channel_metadata = Column(JSONB, default=dict)

    # Communication preferences
    opt_in_marketing = Column(Boolean, default=False)
    opt_in_notifications = Column(Boolean, default=True)
    quiet_hours_start = Column(String(8))  # HH:MM:SS format
    quiet_hours_end = Column(String(8))

    # Relationships
    contact = relationship("CustomerContact", back_populates="communication_channels")
    channel = relationship("RegisteredChannel")
    interactions = relationship(
        "CommunicationInteraction", back_populates="channel_info"
    )

    __table_args__ = (
        UniqueConstraint(
            "contact_id",
            "channel_id",
            "channel_address",
            name="_contact_channel_addr_uc",
        ),
        Index("idx_contact_channel_contact", "contact_id"),
        Index("idx_contact_channel_verified", "is_verified"),
        Index("idx_contact_channel_active", "is_active"),
    )


class CommunicationInteraction(TenantModel, AuditMixin):
    """Unified communication interaction with plugin-based channels."""

    __tablename__ = "omnichannel_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interaction_reference = Column(String(100), unique=True, nullable=False)

    # Contact and channel information
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

    # Interaction details
    interaction_type = Column(SQLEnum(InteractionType), nullable=False)
    status = Column(SQLEnum(InteractionStatus), default=InteractionStatus.PENDING)
    subject = Column(String(500))
    content = Column(Text, nullable=False)

    # Plugin-specific data
    channel_message_id = Column(String(200))  # External message ID from channel
    channel_metadata = Column(JSONB, default=dict)  # Channel-specific metadata

    # Routing and assignment
    assigned_agent_id = Column(UUID(as_uuid=True), ForeignKey("omnichannel_agents.id"))
    assigned_team_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agent_teams.id")
    )
    priority_level = Column(Integer, default=3)  # 1=highest, 5=lowest

    # Timing
    interaction_start = Column(DateTime, default=datetime.utcnow)
    first_response_time = Column(DateTime)
    resolution_time = Column(DateTime)

    # Analytics
    sentiment_score = Column(Float)  # -1 to 1 range
    satisfaction_rating = Column(Integer)  # 1-5 scale
    tags = Column(JSONB, default=list)

    # Relationships
    contact = relationship("CustomerContact", back_populates="interactions")
    channel_info = relationship(
        "ContactCommunicationChannel", back_populates="interactions"
    )
    assigned_agent = relationship(
        "OmnichannelAgent", back_populates="assigned_interactions"
    )
    assigned_team = relationship("AgentTeam", back_populates="team_interactions")
    responses = relationship("InteractionResponse", back_populates="interaction")
    escalations = relationship("InteractionEscalation", back_populates="interaction")

    @hybrid_property
    def response_time_minutes(self):
        """Calculate response time in minutes."""
        if self.first_response_time and self.interaction_start:
            delta = self.first_response_time - self.interaction_start
            return delta.total_seconds() / 60
        return None

    __table_args__ = (
        Index("idx_interaction_contact", "contact_id"),
        Index("idx_interaction_channel", "channel_info_id"),
        Index("idx_interaction_agent", "assigned_agent_id"),
        Index("idx_interaction_status", "status"),
        Index("idx_interaction_priority", "priority_level"),
        Index("idx_interaction_tenant", "tenant_id"),
    )


# Rest of the models remain largely the same...
class OmnichannelAgent(TenantModel, AuditMixin):
    """Agent information with dynamic channel skills."""

    __tablename__ = "omnichannel_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to system user
    employee_id = Column(String(50))

    # Agent details
    display_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    avatar_url = Column(String(500))

    # Status and availability
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.OFFLINE)
    max_concurrent_interactions = Column(Integer, default=5)
    current_workload = Column(Integer, default=0)

    # Skills (includes channel skills dynamically)
    channel_skills = Column(JSONB, default=dict)  # {channel_id: skill_level}
    language_skills = Column(JSONB, default=list)  # ['en', 'es', 'fr']
    department_skills = Column(JSONB, default=list)  # ['billing', 'technical', 'sales']

    # Performance metrics
    total_interactions = Column(Integer, default=0)
    average_response_time = Column(Float, default=0.0)  # in minutes
    customer_satisfaction = Column(Float, default=0.0)  # average rating

    # Relationships
    team_memberships = relationship(
        "AgentTeam",
        secondary="omnichannel_agent_team_members",
        back_populates="members",
    )
    assigned_interactions = relationship(
        "CommunicationInteraction", back_populates="assigned_agent"
    )
    schedules = relationship("AgentSchedule", back_populates="agent")
    performance_metrics = relationship("AgentPerformanceMetric", back_populates="agent")

    __table_args__ = (
        Index("idx_agent_user", "user_id"),
        Index("idx_agent_status", "status"),
        Index("idx_agent_tenant", "tenant_id"),
    )


# Agent Teams table remains the same...
class AgentTeam(TenantModel, AuditMixin):
    """Agent team for workload distribution."""

    __tablename__ = "omnichannel_agent_teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    # Team capabilities (dynamic channel support)
    supported_channels = Column(JSONB, default=list)  # List of channel_ids
    supported_languages = Column(JSONB, default=list)
    supported_departments = Column(JSONB, default=list)

    # Team settings
    max_queue_size = Column(Integer, default=100)
    routing_strategy = Column(
        SQLEnum(RoutingStrategy), default=RoutingStrategy.ROUND_ROBIN
    )

    # Relationships
    members = relationship(
        "OmnichannelAgent",
        secondary="omnichannel_agent_team_members",
        back_populates="team_memberships",
    )
    team_interactions = relationship(
        "CommunicationInteraction", back_populates="assigned_team"
    )
    routing_rules = relationship("RoutingRule", back_populates="target_team")

    __table_args__ = (
        Index("idx_agent_team_active", "is_active"),
        Index("idx_agent_team_tenant", "tenant_id"),
    )


# Association table for agent-team many-to-many relationship
from sqlalchemy import Table

agent_team_members = Table(
    "omnichannel_agent_team_members",
    TenantModel.metadata,
    Column(
        "agent_id",
        UUID(as_uuid=True),
        ForeignKey("omnichannel_agents.id"),
        primary_key=True,
    ),
    Column(
        "team_id",
        UUID(as_uuid=True),
        ForeignKey("omnichannel_agent_teams.id"),
        primary_key=True,
    ),
    Column("is_team_lead", Boolean, default=False),
    Column("joined_at", DateTime, default=datetime.utcnow),
    Column("tenant_id", UUID(as_uuid=True), nullable=False),
)


# Other supporting models remain similar but with dynamic channel references...


class RoutingRule(TenantModel, AuditMixin):
    """Routing rules with dynamic channel support."""

    __tablename__ = "omnichannel_routing_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=5)

    # Rule conditions (now supports any registered channel)
    channel_condition = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_registered_channels.id")
    )
    priority_condition = Column(Integer)
    sentiment_condition = Column(String(20))
    customer_tier_condition = Column(String(50))
    time_condition = Column(JSONB)  # Flexible time-based conditions
    keyword_conditions = Column(JSONB, default=list)

    # Rule actions
    target_team_id = Column(
        UUID(as_uuid=True), ForeignKey("omnichannel_agent_teams.id")
    )
    target_agent_id = Column(UUID(as_uuid=True), ForeignKey("omnichannel_agents.id"))
    priority_override = Column(Integer)

    # Relationships
    channel = relationship("RegisteredChannel")
    target_team = relationship("AgentTeam", back_populates="routing_rules")
    target_agent = relationship("OmnichannelAgent")

    __table_args__ = (
        Index("idx_routing_rule_active", "is_active"),
        Index("idx_routing_rule_priority", "priority"),
        Index("idx_routing_rule_tenant", "tenant_id"),
    )


# The rest of the models (InteractionResponse, InteractionEscalation, etc.)
# remain largely the same but reference the new dynamic channel system
