"""Interaction Manager for DotMac Omnichannel Service.

Central orchestrator for all customer interactions across multiple channels.
Manages the complete interaction lifecycle from creation to resolution.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.enums import ChannelType

logger = logging.getLogger(__name__)


class InteractionStatus(str, Enum):
    """Interaction status values."""

    PENDING = "pending"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    WAITING_INTERNAL = "waiting_internal"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class InteractionPriority(str, Enum):
    """Interaction priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


@dataclass
class InteractionContext:
    """Context information for an interaction."""

    customer_id: str
    tenant_id: str
    channel: ChannelType
    source_metadata: dict[str, Any] = field(default_factory=dict)
    customer_metadata: dict[str, Any] = field(default_factory=dict)
    session_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionSLA:
    """SLA configuration for interactions."""

    first_response_minutes: int = 120  # 2 hours
    resolution_hours: int = 24
    escalation_minutes: int = 240  # 4 hours
    priority_multiplier: dict[InteractionPriority, float] = field(
        default_factory=lambda: {
            InteractionPriority.LOW: 2.0,
            InteractionPriority.NORMAL: 1.0,
            InteractionPriority.HIGH: 0.5,
            InteractionPriority.URGENT: 0.25,
            InteractionPriority.CRITICAL: 0.1,
        }
    )


class InteractionModel(BaseModel):
    """Core interaction data model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    customer_id: str

    # Channel information
    channel: ChannelType
    channel_thread_id: Optional[str] = None
    external_id: Optional[str] = None

    # Content
    subject: Optional[str] = None
    content: str
    content_type: str = "text"
    attachments: list[dict[str, Any]] = Field(default_factory=list)

    # Status and routing
    status: InteractionStatus = InteractionStatus.PENDING
    priority: InteractionPriority = InteractionPriority.NORMAL
    assigned_agent_id: Optional[str] = None
    assigned_team_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    # SLA tracking
    sla_first_response_due: Optional[datetime] = None
    sla_resolution_due: Optional[datetime] = None
    sla_escalation_due: Optional[datetime] = None
    sla_breach_flags: list[str] = Field(default_factory=list)

    # Customer satisfaction
    customer_satisfaction_rating: Optional[int] = None
    customer_satisfaction_comment: Optional[str] = None

    # Metadata
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)

    # Conversation threading
    conversation_id: Optional[str] = None
    parent_interaction_id: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        if isinstance(v, str):
            return InteractionPriority(v)
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, str):
            return InteractionStatus(v)
        return v

    def is_active(self) -> bool:
        """Check if interaction is in an active state."""
        return self.status in [
            InteractionStatus.OPEN,
            InteractionStatus.IN_PROGRESS,
            InteractionStatus.WAITING_CUSTOMER,
            InteractionStatus.WAITING_INTERNAL,
            InteractionStatus.ESCALATED,
        ]

    def is_closed(self) -> bool:
        """Check if interaction is closed."""
        return self.status in [
            InteractionStatus.RESOLVED,
            InteractionStatus.CLOSED,
            InteractionStatus.CANCELLED,
        ]

    def time_to_first_response(self) -> Optional[timedelta]:
        """Calculate time to first response."""
        if self.first_response_at:
            return self.first_response_at - self.created_at
        return None

    def time_to_resolution(self) -> Optional[timedelta]:
        """Calculate time to resolution."""
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return None

    def get_age(self) -> timedelta:
        """Get current age of interaction."""
        return datetime.now(timezone.utc) - self.created_at


class InteractionResponse(BaseModel):
    """Response to an interaction."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    interaction_id: str
    tenant_id: str

    # Response details
    agent_id: Optional[str] = None
    content: str
    content_type: str = "text"
    attachments: list[dict[str, Any]] = Field(default_factory=list)

    # Channel information
    channel: ChannelType
    channel_message_id: Optional[str] = None
    external_id: Optional[str] = None

    # Response metadata
    response_type: str = "reply"  # reply, internal_note, system
    is_public: bool = True

    # Delivery tracking
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Metadata
    extra_data: dict[str, Any] = Field(default_factory=dict, alias="metadata")


class InteractionManager:
    """Central interaction management service.

    Orchestrates the complete lifecycle of customer interactions including:
    - Interaction creation and routing
    - Status management and updates
    - SLA tracking and monitoring
    - Response handling and delivery
    - Analytics and reporting
    """

    def __init__(
        self,
        repository=None,
        routing_engine=None,
        channel_orchestrator=None,
        analytics_service=None,
        notification_service=None,
    ):
        """Initialize interaction manager.

        Args:
            repository: Data repository for persistence
            routing_engine: Intelligent routing engine
            channel_orchestrator: Multi-channel communication
            analytics_service: Analytics and metrics
            notification_service: Notification handling
        """
        self.repository = repository
        self.routing_engine = routing_engine
        self.channel_orchestrator = channel_orchestrator
        self.analytics_service = analytics_service
        self.notification_service = notification_service

        # SLA configuration
        self.default_sla = InteractionSLA()
        self.tenant_slas: dict[str, InteractionSLA] = {}

        # Active interaction tracking
        self.active_interactions: dict[str, InteractionModel] = {}

        logger.info("Interaction Manager initialized")

    async def create_interaction(
        self,
        tenant_id: str,
        customer_id: str,
        channel: Union[ChannelType, str],
        content: str,
        subject: Optional[str] = None,
        priority: Union[InteractionPriority, str] = InteractionPriority.NORMAL,
        attachments: Optional[list[dict[str, Any]]] = None,
        context: Optional[InteractionContext] = None,
        external_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> InteractionModel:
        """Create a new customer interaction.

        Args:
            tenant_id: Tenant identifier
            customer_id: Customer identifier
            channel: Communication channel
            content: Interaction content
            subject: Optional subject/title
            priority: Interaction priority
            attachments: Optional file attachments
            context: Additional context information
            external_id: External system identifier
            conversation_id: Conversation thread ID

        Returns:
            Created interaction model
        """
        # Normalize enums
        if isinstance(channel, str):
            channel = ChannelType(channel)
        if isinstance(priority, str):
            priority = InteractionPriority(priority)

        # Create interaction
        interaction = InteractionModel(
            tenant_id=tenant_id,
            customer_id=customer_id,
            channel=channel,
            content=content,
            subject=subject,
            priority=priority,
            attachments=attachments or [],
            external_id=external_id,
            conversation_id=conversation_id,
            context=context.source_metadata if context else {},
        )

        # Set SLA deadlines
        await self._calculate_sla_deadlines(interaction)

        # Store interaction
        if self.repository:
            await self.repository.create_interaction(interaction)

        # Add to active tracking
        self.active_interactions[interaction.id] = interaction

        # Route interaction
        if self.routing_engine:
            try:
                routing_result = await self.routing_engine.route_interaction(
                    interaction
                )
                if routing_result.agent_id:
                    interaction.assigned_agent_id = routing_result.agent_id
                    interaction.status = InteractionStatus.OPEN
                if routing_result.team_id:
                    interaction.assigned_team_id = routing_result.team_id
            except Exception as e:
                logger.error(f"Failed to route interaction {interaction.id}: {e}")

        # Send notifications
        if self.notification_service:
            await self._notify_interaction_created(interaction)

        # Track analytics
        if self.analytics_service:
            await self.analytics_service.track_interaction_created(interaction)

        logger.info(f"Created interaction {interaction.id} for customer {customer_id}")
        return interaction

    async def update_interaction(
        self,
        interaction_id: str,
        status: Optional[Union[InteractionStatus, str]] = None,
        assigned_agent_id: Optional[str] = None,
        assigned_team_id: Optional[str] = None,
        priority: Optional[Union[InteractionPriority, str]] = None,
        tags: Optional[list[str]] = None,
        custom_fields: Optional[dict[str, Any]] = None,
    ) -> InteractionModel:
        """Update interaction properties.

        Args:
            interaction_id: Interaction identifier
            status: New status
            assigned_agent_id: Assigned agent ID
            assigned_team_id: Assigned team ID
            priority: New priority level
            tags: Interaction tags
            custom_fields: Custom field updates

        Returns:
            Updated interaction model
        """
        interaction = await self.get_interaction(interaction_id)
        if not interaction:
            raise ValueError(f"Interaction {interaction_id} not found")

        # Update fields
        if status is not None:
            if isinstance(status, str):
                status = InteractionStatus(status)
            interaction.status = status

        if assigned_agent_id is not None:
            interaction.assigned_agent_id = assigned_agent_id

        if assigned_team_id is not None:
            interaction.assigned_team_id = assigned_team_id

        if priority is not None:
            if isinstance(priority, str):
                priority = InteractionPriority(priority)
            interaction.priority = priority
            # Recalculate SLA with new priority
            await self._calculate_sla_deadlines(interaction)

        if tags is not None:
            interaction.tags = tags

        if custom_fields is not None:
            interaction.custom_fields.update(custom_fields)

        interaction.updated_at = datetime.now(timezone.utc)

        # Handle status transitions
        if (
            status == InteractionStatus.IN_PROGRESS
            and not interaction.first_response_at
        ):
            interaction.first_response_at = datetime.now(timezone.utc)

        elif status == InteractionStatus.RESOLVED and not interaction.resolved_at:
            interaction.resolved_at = datetime.now(timezone.utc)

        elif status == InteractionStatus.CLOSED and not interaction.closed_at:
            interaction.closed_at = datetime.now(timezone.utc)

        # Persist changes
        if self.repository:
            await self.repository.update_interaction(interaction)

        # Update active tracking
        self.active_interactions[interaction_id] = interaction

        # Track analytics
        if self.analytics_service:
            await self.analytics_service.track_interaction_updated(interaction)

        logger.info(f"Updated interaction {interaction_id}")
        return interaction

    async def add_response(
        self,
        interaction_id: str,
        agent_id: Optional[str],
        content: str,
        channel: Optional[Union[ChannelType, str]] = None,
        response_type: str = "reply",
        is_public: bool = True,
        attachments: Optional[list[dict[str, Any]]] = None,
    ) -> InteractionResponse:
        """Add response to interaction.

        Args:
            interaction_id: Interaction identifier
            agent_id: Responding agent ID
            content: Response content
            channel: Response channel (defaults to interaction channel)
            response_type: Type of response (reply, internal_note, system)
            is_public: Whether response is visible to customer
            attachments: Optional file attachments

        Returns:
            Created response model
        """
        interaction = await self.get_interaction(interaction_id)
        if not interaction:
            raise ValueError(f"Interaction {interaction_id} not found")

        # Use interaction channel if not specified
        if channel is None:
            channel = interaction.channel
        elif isinstance(channel, str):
            channel = ChannelType(channel)

        # Create response
        response = InteractionResponse(
            interaction_id=interaction_id,
            tenant_id=interaction.tenant_id,
            agent_id=agent_id,
            content=content,
            channel=channel,
            response_type=response_type,
            is_public=is_public,
            attachments=attachments or [],
        )

        # Store response
        if self.repository:
            await self.repository.create_response(response)

        # Send through channel if public
        if is_public and self.channel_orchestrator:
            try:
                await self.channel_orchestrator.send_response(response)
                response.sent_at = datetime.now(timezone.utc)
            except Exception as e:
                response.failed_at = datetime.now(timezone.utc)
                response.failure_reason = str(e)
                logger.error(f"Failed to send response {response.id}: {e}")

        # Update interaction status and first response time
        if response_type == "reply" and not interaction.first_response_at:
            await self.update_interaction(
                interaction_id, status=InteractionStatus.IN_PROGRESS
            )

        # Track analytics
        if self.analytics_service:
            await self.analytics_service.track_response_added(response)

        logger.info(f"Added response {response.id} to interaction {interaction_id}")
        return response

    async def close_interaction(
        self,
        interaction_id: str,
        resolution: Optional[str] = None,
        customer_satisfaction_rating: Optional[int] = None,
        customer_satisfaction_comment: Optional[str] = None,
    ) -> InteractionModel:
        """Close an interaction.

        Args:
            interaction_id: Interaction identifier
            resolution: Resolution summary
            customer_satisfaction_rating: Customer satisfaction (1-5)
            customer_satisfaction_comment: Customer feedback

        Returns:
            Closed interaction model
        """
        interaction = await self.update_interaction(
            interaction_id, status=InteractionStatus.CLOSED
        )

        # Add resolution details
        if resolution:
            interaction.custom_fields["resolution"] = resolution

        if customer_satisfaction_rating is not None:
            interaction.customer_satisfaction_rating = customer_satisfaction_rating

        if customer_satisfaction_comment is not None:
            interaction.customer_satisfaction_comment = customer_satisfaction_comment

        # Remove from active tracking
        self.active_interactions.pop(interaction_id, None)

        # Track analytics
        if self.analytics_service:
            await self.analytics_service.track_interaction_closed(interaction)

        logger.info(f"Closed interaction {interaction_id}")
        return interaction

    async def get_interaction(self, interaction_id: str) -> Optional[InteractionModel]:
        """Get interaction by ID.

        Args:
            interaction_id: Interaction identifier

        Returns:
            Interaction model if found
        """
        # Check active cache first
        if interaction_id in self.active_interactions:
            return self.active_interactions[interaction_id]

        # Load from repository
        if self.repository:
            interaction = await self.repository.get_interaction(interaction_id)
            if interaction and interaction.is_active():
                self.active_interactions[interaction_id] = interaction
            return interaction

        return None

    async def get_customer_interactions(
        self,
        customer_id: str,
        tenant_id: str,
        status: Optional[InteractionStatus] = None,
        channel: Optional[ChannelType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InteractionModel]:
        """Get interactions for a customer.

        Args:
            customer_id: Customer identifier
            tenant_id: Tenant identifier
            status: Optional status filter
            channel: Optional channel filter
            limit: Maximum results
            offset: Result offset

        Returns:
            List of matching interactions
        """
        if not self.repository:
            return []

        return await self.repository.get_customer_interactions(
            customer_id=customer_id,
            tenant_id=tenant_id,
            status=status,
            channel=channel,
            limit=limit,
            offset=offset,
        )

    async def get_agent_interactions(
        self,
        agent_id: str,
        tenant_id: str,
        status: Optional[InteractionStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InteractionModel]:
        """Get interactions assigned to an agent.

        Args:
            agent_id: Agent identifier
            tenant_id: Tenant identifier
            status: Optional status filter
            limit: Maximum results
            offset: Result offset

        Returns:
            List of assigned interactions
        """
        if not self.repository:
            return []

        return await self.repository.get_agent_interactions(
            agent_id=agent_id,
            tenant_id=tenant_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def check_sla_breaches(self) -> list[InteractionModel]:
        """Check for SLA breaches across active interactions.

        Returns:
            List of interactions with SLA breaches
        """
        breached_interactions = []
        now = datetime.now(timezone.utc)

        for interaction in self.active_interactions.values():
            breaches = []

            # Check first response SLA
            if (
                interaction.sla_first_response_due
                and now > interaction.sla_first_response_due
                and not interaction.first_response_at
            ):
                breaches.append("first_response")

            # Check resolution SLA
            if (
                interaction.sla_resolution_due
                and now > interaction.sla_resolution_due
                and not interaction.resolved_at
            ):
                breaches.append("resolution")

            # Check escalation SLA
            if (
                interaction.sla_escalation_due
                and now > interaction.sla_escalation_due
                and interaction.status != InteractionStatus.ESCALATED
            ):
                breaches.append("escalation")

            if breaches:
                interaction.sla_breach_flags.extend(breaches)
                breached_interactions.append(interaction)

        return breached_interactions

    async def _calculate_sla_deadlines(self, interaction: InteractionModel):
        """Calculate SLA deadlines for interaction."""
        sla = self.tenant_slas.get(interaction.tenant_id, self.default_sla)
        multiplier = sla.priority_multiplier.get(interaction.priority, 1.0)

        # First response deadline
        first_response_minutes = int(sla.first_response_minutes * multiplier)
        interaction.sla_first_response_due = interaction.created_at + timedelta(
            minutes=first_response_minutes
        )

        # Resolution deadline
        resolution_hours = int(sla.resolution_hours * multiplier)
        interaction.sla_resolution_due = interaction.created_at + timedelta(
            hours=resolution_hours
        )

        # Escalation deadline
        escalation_minutes = int(sla.escalation_minutes * multiplier)
        interaction.sla_escalation_due = interaction.created_at + timedelta(
            minutes=escalation_minutes
        )

    async def _notify_interaction_created(self, interaction: InteractionModel):
        """Send notifications for new interaction."""
        if self.notification_service:
            await self.notification_service.notify_interaction_created(interaction)

    def configure_tenant_sla(self, tenant_id: str, sla_config: InteractionSLA):
        """Configure SLA for a specific tenant.

        Args:
            tenant_id: Tenant identifier
            sla_config: SLA configuration
        """
        self.tenant_slas[tenant_id] = sla_config
        logger.info(f"Configured SLA for tenant {tenant_id}")

    async def get_interaction_stats(self, tenant_id: str) -> dict[str, Any]:
        """Get interaction statistics for tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary of statistics
        """
        if not self.repository:
            return {}

        return await self.repository.get_interaction_stats(tenant_id)
