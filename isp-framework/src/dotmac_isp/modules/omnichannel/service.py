"""Omnichannel system service layer with comprehensive business logic."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from uuid import UUID, uuid4
import asyncio
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import and_, or_, func, text, desc, asc
from sqlalchemy.exc import IntegrityError

from dotmac_isp.core.settings import get_settings
from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
    DuplicateEntityError,
    ExternalServiceError,
)

from .models import (
    CustomerContact,
    ContactCommunicationChannel,
    CommunicationInteraction,
    InteractionResponse,
    OmnichannelAgent,
    AgentTeam,
    RoutingRule,
    InteractionEscalation,
    AgentPerformanceMetric,
    AgentSchedule,
    ChannelAnalytics,
    CustomerCommunicationSummary,
    ContactType,
    CommunicationChannel,
    InteractionType,
    InteractionStatus,
    AgentStatus,
    RoutingStrategy,
    EscalationTrigger,
)
from .schemas import (
    CustomerContactCreate,
    CustomerContactUpdate,
    CustomerContactResponse,
    ContactCommunicationChannelCreate,
    ContactCommunicationChannelUpdate,
    CommunicationInteractionCreate,
    InteractionResponseCreate,
    OmnichannelAgentCreate,
    OmnichannelAgentUpdate,
    AgentTeamCreate,
    RoutingRuleCreate,
    InteractionEscalationCreate,
    InteractionSearchFilters,
    AgentSearchFilters,
    OmnichannelDashboardStats,
)
from .repository import OmnichannelRepository

logger = logging.getLogger(__name__)


class OmnichannelService:
    """Comprehensive omnichannel communication service."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize omnichannel service."""
        self.db = db
        self.settings = get_settings()
        self.tenant_id = UUID(tenant_id) if tenant_id else UUID(self.settings.tenant_id)
        self.repository = OmnichannelRepository(db, self.tenant_id)

        logger.info(f"Initialized OmnichannelService for tenant: {self.tenant_id}")

    # ===== CUSTOMER CONTACT MANAGEMENT =====

    async def create_customer_contact(
        self, contact_data: CustomerContactCreate
    ) -> CustomerContactResponse:
        """Create a new customer contact with communication channels."""
        try:
            logger.info(
                f"Creating customer contact for customer_id: {contact_data.customer_id}"
            )

            # Validate customer exists
            customer = await self.repository.get_customer(contact_data.customer_id)
            if not customer:
                raise EntityNotFoundError(
                    f"Customer not found: {contact_data.customer_id}"
                )

            # Check if this is being set as primary contact
            if contact_data.is_primary:
                # Ensure only one primary contact per customer
                existing_primary = await self.repository.get_primary_contact(
                    contact_data.customer_id
                )
                if existing_primary:
                    await self.repository.update_contact(
                        existing_primary.id, {"is_primary": False}
                    )

            # Create contact
            contact = await self.repository.create_customer_contact(
                {**contact_data.model_dump(), "tenant_id": self.tenant_id}
            )

            logger.info(f"Created customer contact: {contact.id}")
            return await self._build_contact_response(contact)

        except Exception as e:
            logger.error(f"Error creating customer contact: {e}")
            raise

    async def update_customer_contact(
        self, contact_id: UUID, update_data: CustomerContactUpdate
    ) -> CustomerContactResponse:
        """Update customer contact information."""
        try:
            logger.info(f"Updating customer contact: {contact_id}")

            contact = await self.repository.get_customer_contact(contact_id)
            if not contact:
                raise EntityNotFoundError(f"Contact not found: {contact_id}")

            # Handle primary contact logic
            if update_data.is_primary is True:
                existing_primary = await self.repository.get_primary_contact(
                    contact.customer_id
                )
                if existing_primary and existing_primary.id != contact_id:
                    await self.repository.update_contact(
                        existing_primary.id, {"is_primary": False}
                    )

            # Update contact
            updated_contact = await self.repository.update_customer_contact(
                contact_id, update_data.model_dump(exclude_unset=True)
            )

            logger.info(f"Updated customer contact: {contact_id}")
            return await self._build_contact_response(updated_contact)

        except Exception as e:
            logger.error(f"Error updating customer contact: {e}")
            raise

    async def add_communication_channel(
        self, channel_data: ContactCommunicationChannelCreate
    ) -> ContactCommunicationChannelCreate:
        """Add communication channel to contact."""
        try:
            logger.info(
                f"Adding communication channel for contact: {channel_data.contact_id}"
            )

            # Validate contact exists
            contact = await self.repository.get_customer_contact(
                channel_data.contact_id
            )
            if not contact:
                raise EntityNotFoundError(
                    f"Contact not found: {channel_data.contact_id}"
                )

            # Check for duplicate channel values
            existing = await self.repository.get_channel_by_value(
                channel_data.channel_type, channel_data.channel_value
            )
            if existing and existing.contact_id != channel_data.contact_id:
                raise DuplicateEntityError(
                    f"Channel {channel_data.channel_type}:{channel_data.channel_value} already exists"
                )

            # Handle primary channel logic
            if channel_data.is_primary:
                existing_primary = await self.repository.get_primary_channel(
                    channel_data.contact_id, channel_data.channel_type
                )
                if existing_primary:
                    await self.repository.update_channel(
                        existing_primary.id, {"is_primary": False}
                    )

            # Create channel
            channel = await self.repository.create_communication_channel(
                {**channel_data.model_dump(), "tenant_id": self.tenant_id}
            )

            logger.info(f"Created communication channel: {channel.id}")
            return channel

        except Exception as e:
            logger.error(f"Error adding communication channel: {e}")
            raise

    async def get_customer_contacts(
        self, customer_id: UUID
    ) -> List[CustomerContactResponse]:
        """Get all contacts for a customer."""
        try:
            contacts = await self.repository.get_customer_contacts(customer_id)
            return [await self._build_contact_response(contact) for contact in contacts]
        except Exception as e:
            logger.error(f"Error getting customer contacts: {e}")
            raise

    async def verify_communication_channel(
        self, channel_id: UUID, verification_code: Optional[str] = None
    ) -> bool:
        """Verify a communication channel."""
        try:
            logger.info(f"Verifying communication channel: {channel_id}")

            channel = await self.repository.get_communication_channel(channel_id)
            if not channel:
                raise EntityNotFoundError(f"Channel not found: {channel_id}")

            # Basic verification - mark as verified (complex verification not needed for ISP core)
            await self.repository.update_channel(
                channel_id,
                {"is_verified": True, "verification_date": datetime.now(timezone.utc)},
            )

            logger.info(f"Verified communication channel: {channel_id}")
            return True

        except Exception as e:
            logger.error(f"Error verifying communication channel: {e}")
            raise

    # ===== COMMUNICATION INTERACTION MANAGEMENT =====

    async def create_interaction(
        self, interaction_data: CommunicationInteractionCreate
    ) -> str:
        """Create new communication interaction with intelligent routing."""
        try:
            logger.info(
                f"Creating interaction for customer: {interaction_data.customer_id}"
            )

            # Generate unique interaction reference
            interaction_reference = (
                f"INT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
            )

            # Determine contact and channel if not provided
            contact, channel = await self._resolve_contact_and_channel(
                interaction_data.customer_id,
                interaction_data.contact_id,
                interaction_data.channel_id,
                interaction_data.channel_type,
            )

            # Analyze interaction for intent, sentiment, etc.
            analysis = await self._analyze_interaction_content(interaction_data.content)

            # Create interaction record
            interaction = await self.repository.create_interaction(
                {
                    **interaction_data.model_dump(),
                    "interaction_reference": interaction_reference,
                    "contact_id": contact.id if contact else None,
                    "channel_id": channel.id if channel else None,
                    "intent": analysis.get("intent"),
                    "sentiment": analysis.get("sentiment"),
                    "sentiment_score": analysis.get("sentiment_score"),
                    "language": analysis.get("language", "en"),
                    "urgency_score": analysis.get("urgency_score", 0.5),
                    "keywords": analysis.get("keywords", []),
                    "received_at": datetime.now(timezone.utc),
                    "tenant_id": self.tenant_id,
                }
            )

            # Perform intelligent routing
            await self._route_interaction(interaction)

            # Update channel usage statistics
            if channel:
                await self._update_channel_usage(channel.id)

            logger.info(f"Created interaction: {interaction_reference}")
            return interaction_reference

        except Exception as e:
            logger.error(f"Error creating interaction: {e}")
            raise

    async def add_interaction_response(
        self, response_data: InteractionResponseCreate
    ) -> UUID:
        """Add response to an interaction."""
        try:
            logger.info(
                f"Adding response to interaction: {response_data.interaction_id}"
            )

            interaction = await self.repository.get_interaction(
                response_data.interaction_id
            )
            if not interaction:
                raise EntityNotFoundError(
                    f"Interaction not found: {response_data.interaction_id}"
                )

            # Get next sequence number
            last_response = await self.repository.get_last_interaction_response(
                response_data.interaction_id
            )
            sequence_number = (
                (last_response.sequence_number + 1) if last_response else 1
            )

            # Analyze response content
            analysis = await self._analyze_interaction_content(response_data.content)

            # Create response
            response = await self.repository.create_interaction_response(
                {
                    **response_data.model_dump(),
                    "sequence_number": sequence_number,
                    "sent_at": datetime.now(timezone.utc),
                    "sentiment": analysis.get("sentiment"),
                    "sentiment_score": analysis.get("sentiment_score"),
                    "tenant_id": self.tenant_id,
                }
            )

            # Update interaction timestamps and statistics
            update_data = {
                "response_count": interaction.response_count + 1,
                "last_response_at": datetime.now(timezone.utc),
            }

            # Set first response time if this is the first agent response
            if (
                response_data.author_type == "agent"
                and not interaction.first_response_at
                and not response_data.is_internal
            ):
                update_data["first_response_at"] = datetime.now(timezone.utc)
                update_data["response_time_seconds"] = int(
                    (datetime.now(timezone.utc) - interaction.received_at).total_seconds()
                )

            await self.repository.update_interaction(interaction.id, update_data)

            logger.info(f"Added response to interaction: {response.id}")
            return response.id

        except Exception as e:
            logger.error(f"Error adding interaction response: {e}")
            raise

    async def resolve_interaction(
        self, interaction_id: UUID, resolution_notes: Optional[str] = None
    ) -> bool:
        """Mark interaction as resolved."""
        try:
            logger.info(f"Resolving interaction: {interaction_id}")

            interaction = await self.repository.get_interaction(interaction_id)
            if not interaction:
                raise EntityNotFoundError(f"Interaction not found: {interaction_id}")

            if interaction.status == InteractionStatus.COMPLETED:
                logger.warning(f"Interaction already resolved: {interaction_id}")
                return True

            resolved_at = datetime.now(timezone.utc)
            resolution_time_seconds = int(
                (resolved_at - interaction.received_at).total_seconds()
            )

            # Update interaction
            await self.repository.update_interaction(
                interaction_id,
                {
                    "status": InteractionStatus.COMPLETED,
                    "resolved_at": resolved_at,
                    "resolution_time_seconds": resolution_time_seconds,
                },
            )

            # Add resolution note if provided
            if resolution_notes:
                await self.add_interaction_response(
                    InteractionResponseCreate(
                        interaction_id=interaction_id,
                        content=f"Resolution: {resolution_notes}",
                        author_type="system",
                        is_internal=True,
                    )
                )

            # Update agent workload
            if interaction.assigned_agent_id:
                await self._update_agent_workload(interaction.assigned_agent_id, -1)

            logger.info(f"Resolved interaction: {interaction_id}")
            return True

        except Exception as e:
            logger.error(f"Error resolving interaction: {e}")
            raise

    async def escalate_interaction(
        self, escalation_data: InteractionEscalationCreate
    ) -> UUID:
        """Escalate interaction to higher level support."""
        try:
            logger.info(f"Escalating interaction: {escalation_data.interaction_id}")

            interaction = await self.repository.get_interaction(
                escalation_data.interaction_id
            )
            if not interaction:
                raise EntityNotFoundError(
                    f"Interaction not found: {escalation_data.interaction_id}"
                )

            # Create escalation record
            escalation = await self.repository.create_escalation(
                {
                    **escalation_data.model_dump(),
                    "escalated_at": datetime.now(timezone.utc),
                    "tenant_id": self.tenant_id,
                }
            )

            # Update interaction escalation level and priority
            await self.repository.update_interaction(
                escalation_data.interaction_id,
                {
                    "escalation_level": escalation_data.escalation_level,
                    "priority": (
                        "high" if escalation_data.escalation_level > 1 else "urgent"
                    ),
                },
            )

            # Reassign to escalation target
            if escalation_data.to_agent_id:
                await self._assign_interaction_to_agent(
                    escalation_data.interaction_id, escalation_data.to_agent_id
                )
            elif escalation_data.to_team_id:
                await self._route_interaction_to_team(
                    interaction, escalation_data.to_team_id
                )

            logger.info(f"Escalated interaction: {escalation.id}")
            return escalation.id

        except Exception as e:
            logger.error(f"Error escalating interaction: {e}")
            raise

    async def search_interactions(
        self, filters: InteractionSearchFilters
    ) -> Tuple[List[Dict], int]:
        """Search interactions with advanced filtering."""
        try:
            interactions, total_count = await self.repository.search_interactions(
                filters.model_dump(exclude_unset=True)
            )

            # Build response data
            interaction_data = []
            for interaction in interactions:
                data = {
                    "id": interaction.id,
                    "interaction_reference": interaction.interaction_reference,
                    "customer_id": interaction.customer_id,
                    "contact_id": interaction.contact_id,
                    "channel_type": interaction.channel_type,
                    "interaction_type": interaction.interaction_type,
                    "status": interaction.status,
                    "subject": interaction.subject,
                    "priority": interaction.priority,
                    "sentiment": interaction.sentiment,
                    "assigned_agent_id": interaction.assigned_agent_id,
                    "assigned_team": interaction.assigned_team,
                    "received_at": interaction.received_at,
                    "first_response_at": interaction.first_response_at,
                    "resolved_at": interaction.resolved_at,
                    "escalation_level": interaction.escalation_level,
                    "response_count": interaction.response_count,
                    "tags": interaction.tags,
                }
                interaction_data.append(data)

            return interaction_data, total_count

        except Exception as e:
            logger.error(f"Error searching interactions: {e}")
            raise

    # ===== AGENT MANAGEMENT =====

    async def create_agent(self, agent_data: OmnichannelAgentCreate) -> UUID:
        """Create new omnichannel agent."""
        try:
            logger.info(f"Creating omnichannel agent: {agent_data.agent_code}")

            # Validate user exists and is not already an agent
            user = await self.repository.get_user(agent_data.user_id)
            if not user:
                raise EntityNotFoundError(f"User not found: {agent_data.user_id}")

            existing_agent = await self.repository.get_agent_by_user(agent_data.user_id)
            if existing_agent:
                raise DuplicateEntityError(
                    f"User already has agent profile: {agent_data.user_id}"
                )

            # Create agent
            agent = await self.repository.create_agent(
                {
                    **agent_data.model_dump(),
                    "status": AgentStatus.OFFLINE,
                    "tenant_id": self.tenant_id,
                }
            )

            logger.info(f"Created omnichannel agent: {agent.id}")
            return agent.id

        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            raise

    async def update_agent_status(
        self, agent_id: UUID, status: AgentStatus, message: Optional[str] = None
    ) -> bool:
        """Update agent status and availability."""
        try:
            logger.info(f"Updating agent status: {agent_id} -> {status}")

            agent = await self.repository.get_agent(agent_id)
            if not agent:
                raise EntityNotFoundError(f"Agent not found: {agent_id}")

            # Update status
            update_data = {
                "status": status,
                "last_activity": datetime.now(timezone.utc),
                "status_message": message,
            }

            if status == AgentStatus.AVAILABLE:
                update_data["last_login"] = datetime.now(timezone.utc)

            await self.repository.update_agent(agent_id, update_data)

            # Handle routing implications
            if status == AgentStatus.AVAILABLE:
                # Agent became available - check for queued interactions
                await self._process_agent_queue(agent_id)
            elif status in [AgentStatus.OFFLINE, AgentStatus.AWAY]:
                # Agent became unavailable - reassign active interactions
                await self._reassign_agent_interactions(agent_id)

            logger.info(f"Updated agent status: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating agent status: {e}")
            raise

    async def create_team(self, team_data: AgentTeamCreate) -> UUID:
        """Create new agent team."""
        try:
            logger.info(f"Creating agent team: {team_data.team_code}")

            # Check for duplicate team code
            existing = await self.repository.get_team_by_code(team_data.team_code)
            if existing:
                raise DuplicateEntityError(
                    f"Team code already exists: {team_data.team_code}"
                )

            # Create team
            team = await self.repository.create_team(
                {**team_data.model_dump(), "tenant_id": self.tenant_id}
            )

            logger.info(f"Created agent team: {team.id}")
            return team.id

        except Exception as e:
            logger.error(f"Error creating team: {e}")
            raise

    async def assign_agent_to_team(self, agent_id: UUID, team_id: UUID) -> bool:
        """Assign agent to team."""
        try:
            logger.info(f"Assigning agent {agent_id} to team {team_id}")

            # Validate agent and team exist
            agent = await self.repository.get_agent(agent_id)
            if not agent:
                raise EntityNotFoundError(f"Agent not found: {agent_id}")

            team = await self.repository.get_team(team_id)
            if not team:
                raise EntityNotFoundError(f"Team not found: {team_id}")

            # Update agent team assignment
            await self.repository.update_agent(agent_id, {"team_id": team_id})

            logger.info(f"Assigned agent to team: {agent_id} -> {team_id}")
            return True

        except Exception as e:
            logger.error(f"Error assigning agent to team: {e}")
            raise

    async def get_available_agents(
        self,
        channel_type: Optional[CommunicationChannel] = None,
        skill_tags: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Get available agents optionally filtered by channel and skills."""
        try:
            agents = await self.repository.get_available_agents(
                channel_type, skill_tags
            )

            agent_data = []
            for agent in agents:
                data = {
                    "id": agent.id,
                    "agent_code": agent.agent_code,
                    "display_name": agent.display_name,
                    "team_id": agent.team_id,
                    "current_interactions": agent.current_interactions,
                    "max_concurrent_interactions": agent.max_concurrent_interactions,
                    "utilization_rate": agent.utilization_rate,
                    "supported_channels": agent.supported_channels,
                    "skill_tags": agent.skill_tags,
                    "avg_response_time": agent.avg_response_time,
                    "customer_satisfaction": agent.customer_satisfaction,
                }
                agent_data.append(data)

            return agent_data

        except Exception as e:
            logger.error(f"Error getting available agents: {e}")
            raise

    # ===== INTELLIGENT ROUTING =====

    async def create_routing_rule(self, rule_data: RoutingRuleCreate) -> UUID:
        """Create new routing rule."""
        try:
            logger.info(f"Creating routing rule: {rule_data.rule_code}")

            # Validate rule conditions JSON
            self._validate_routing_conditions(rule_data.conditions)

            rule = await self.repository.create_routing_rule(
                {**rule_data.model_dump(), "tenant_id": self.tenant_id}
            )

            logger.info(f"Created routing rule: {rule.id}")
            return rule.id

        except Exception as e:
            logger.error(f"Error creating routing rule: {e}")
            raise

    # ===== ANALYTICS AND REPORTING =====

    async def get_dashboard_stats(
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> OmnichannelDashboardStats:
        """Get comprehensive dashboard statistics."""
        try:
            logger.info("Generating omnichannel dashboard statistics")

            if not date_from:
                date_from = datetime.now(timezone.utc) - timedelta(days=1)
            if not date_to:
                date_to = datetime.now(timezone.utc)

            # Get current status counts
            active_interactions = await self.repository.get_interaction_count_by_status(
                InteractionStatus.IN_PROGRESS
            )
            pending_interactions = (
                await self.repository.get_interaction_count_by_status(
                    InteractionStatus.PENDING
                )
            )
            available_agents = await self.repository.get_agent_count_by_status(
                AgentStatus.AVAILABLE
            )
            busy_agents = await self.repository.get_agent_count_by_status(
                AgentStatus.BUSY
            )

            # Get performance metrics
            avg_response_time = await self.repository.get_avg_response_time(
                date_from, date_to
            )
            avg_resolution_time = await self.repository.get_avg_resolution_time(
                date_from, date_to
            )
            satisfaction_score = await self.repository.get_avg_satisfaction(
                date_from, date_to
            )
            sla_compliance = await self.repository.get_sla_compliance_rate(
                date_from, date_to
            )

            # Get channel breakdown
            channel_stats = await self.repository.get_interactions_by_channel(
                date_from, date_to
            )
            channel_response_times = (
                await self.repository.get_response_times_by_channel(date_from, date_to)
            )

            # Get team utilization
            team_utilization = await self.repository.get_team_utilization_rates()
            team_queues = await self.repository.get_team_queue_sizes()

            # Get trend data (last 24 hours)
            hourly_volume = await self.repository.get_hourly_interaction_volume()
            hourly_response_times = await self.repository.get_hourly_response_times()

            # Get alerts and issues
            breached_sla = await self.repository.get_breached_sla_count()
            high_priority_queue = await self.repository.get_high_priority_queue_size()
            escalated_count = await self.repository.get_escalated_interactions_count()

            return OmnichannelDashboardStats(
                total_active_interactions=active_interactions,
                total_pending_interactions=pending_interactions,
                total_available_agents=available_agents,
                total_busy_agents=busy_agents,
                avg_response_time_minutes=(
                    avg_response_time / 60 if avg_response_time else None
                ),
                avg_resolution_time_hours=(
                    avg_resolution_time / 3600 if avg_resolution_time else None
                ),
                current_satisfaction_score=satisfaction_score,
                sla_compliance_rate=sla_compliance,
                interactions_by_channel=channel_stats,
                channel_response_times=channel_response_times,
                team_utilization_rates=team_utilization,
                team_queue_sizes=team_queues,
                hourly_interaction_volume=hourly_volume,
                hourly_response_times=hourly_response_times,
                breached_sla_count=breached_sla,
                high_priority_queue_size=high_priority_queue,
                escalated_interactions_count=escalated_count,
                calculated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Error generating dashboard stats: {e}")
            raise

    async def calculate_agent_performance(
        self,
        agent_id: UUID,
        date_from: datetime,
        date_to: datetime,
        period: str = "daily",
    ) -> Dict[str, Any]:
        """Calculate comprehensive agent performance metrics."""
        try:
            logger.info(f"Calculating agent performance: {agent_id} ({period})")

            # Get agent interactions for period
            interactions = await self.repository.get_agent_interactions(
                agent_id, date_from, date_to
            )

            if not interactions:
                return self._empty_performance_metrics(agent_id, date_from, period)

            # Calculate volume metrics
            total_interactions = len(interactions)
            channel_breakdown = {}

            # Calculate response and resolution metrics
            response_times = []
            resolution_times = []
            first_response_sla_met = 0
            resolution_sla_met = 0
            satisfactions = []
            escalated_count = 0

            for interaction in interactions:
                # Channel breakdown
                channel = interaction.channel_type.value
                channel_breakdown[channel] = channel_breakdown.get(channel, 0) + 1

                # Response times
                if interaction.response_time_seconds:
                    response_times.append(interaction.response_time_seconds)
                    if interaction.response_time_seconds <= 300:  # 5 minutes SLA
                        first_response_sla_met += 1

                # Resolution times
                if interaction.resolution_time_seconds:
                    resolution_times.append(interaction.resolution_time_seconds)
                    if interaction.resolution_time_seconds <= 3600:  # 1 hour SLA
                        resolution_sla_met += 1

                # Satisfaction scores
                if interaction.customer_satisfaction:
                    satisfactions.append(interaction.customer_satisfaction)

                # Escalations
                if interaction.escalation_level > 0:
                    escalated_count += 1

            # Calculate averages and rates
            avg_response_time = (
                sum(response_times) / len(response_times) if response_times else None
            )
            median_response_time = (
                sorted(response_times)[len(response_times) // 2]
                if response_times
                else None
            )

            avg_resolution_time = (
                sum(resolution_times) / len(resolution_times)
                if resolution_times
                else None
            )
            median_resolution_time = (
                sorted(resolution_times)[len(resolution_times) // 2]
                if resolution_times
                else None
            )

            avg_satisfaction = (
                sum(satisfactions) / len(satisfactions) if satisfactions else None
            )

            resolution_rate = (
                (len(resolution_times) / total_interactions * 100)
                if total_interactions
                else 0
            )
            escalation_rate = (
                (escalated_count / total_interactions * 100)
                if total_interactions
                else 0
            )

            first_response_sla_rate = (
                (first_response_sla_met / len(response_times) * 100)
                if response_times
                else 0
            )
            resolution_sla_rate = (
                (resolution_sla_met / len(resolution_times) * 100)
                if resolution_times
                else 0
            )

            return {
                "agent_id": agent_id,
                "metric_date": date_from,
                "metric_period": period,
                "total_interactions": total_interactions,
                "interactions_by_channel": channel_breakdown,
                "avg_response_time_seconds": avg_response_time,
                "median_response_time_seconds": median_response_time,
                "first_response_sla_met_count": first_response_sla_met,
                "first_response_sla_total_count": len(response_times),
                "first_response_sla_rate": first_response_sla_rate,
                "avg_resolution_time_seconds": avg_resolution_time,
                "median_resolution_time_seconds": median_resolution_time,
                "resolution_sla_met_count": resolution_sla_met,
                "resolution_sla_total_count": len(resolution_times),
                "resolution_sla_rate": resolution_sla_rate,
                "customer_satisfaction_avg": avg_satisfaction,
                "customer_satisfaction_count": len(satisfactions),
                "resolution_rate": resolution_rate,
                "escalation_rate": escalation_rate,
                "calculated_at": datetime.now(timezone.utc),
            }

        except Exception as e:
            logger.error(f"Error calculating agent performance: {e}")
            raise

    async def update_customer_communication_summary(self, customer_id: UUID) -> bool:
        """Update customer communication summary with latest data."""
        try:
            logger.info(f"Updating customer communication summary: {customer_id}")

            # Get all customer interactions
            interactions = await self.repository.get_customer_interactions(customer_id)

            if not interactions:
                return True

            # Calculate statistics
            total_interactions = len(interactions)
            first_interaction = min(interactions, key=lambda x: x.received_at)
            last_interaction = max(interactions, key=lambda x: x.received_at)

            # Channel preferences and usage
            channel_usage = {}
            response_times = []
            satisfaction_scores = []
            categories = {}
            sentiment_scores = []

            resolved_count = 0
            escalated_count = 0
            complaint_dates = []

            for interaction in interactions:
                # Channel usage
                channel = interaction.channel_type.value
                channel_usage[channel] = channel_usage.get(channel, 0) + 1

                # Response times
                if interaction.response_time_seconds:
                    response_times.append(
                        interaction.response_time_seconds / 60
                    )  # Convert to minutes

                # Satisfaction
                if interaction.customer_satisfaction:
                    satisfaction_scores.append(interaction.customer_satisfaction)

                # Categories
                if interaction.category:
                    categories[interaction.category] = (
                        categories.get(interaction.category, 0) + 1
                    )

                # Sentiment
                if interaction.sentiment_score:
                    sentiment_scores.append(interaction.sentiment_score)

                # Resolution and escalation
                if interaction.status == InteractionStatus.COMPLETED:
                    resolved_count += 1
                if interaction.escalation_level > 0:
                    escalated_count += 1

                # Complaint tracking
                if interaction.category and interaction.category.lower() in [
                    "complaint",
                    "issue",
                    "problem",
                ]:
                    complaint_dates.append(interaction.received_at)

            # Calculate derived metrics
            preferred_channels = sorted(
                channel_usage.items(), key=lambda x: x[1], reverse=True
            )
            preferred_channels = [ch[0] for ch in preferred_channels[:3]]  # Top 3

            avg_response_time = (
                sum(response_times) / len(response_times) if response_times else None
            )
            avg_satisfaction = (
                sum(satisfaction_scores) / len(satisfaction_scores)
                if satisfaction_scores
                else None
            )
            avg_sentiment = (
                sum(sentiment_scores) / len(sentiment_scores)
                if sentiment_scores
                else None
            )

            overall_sentiment = "neutral"
            if avg_sentiment and avg_sentiment > 0.1:
                overall_sentiment = "positive"
            elif avg_sentiment and avg_sentiment < -0.1:
                overall_sentiment = "negative"

            common_categories = sorted(
                categories.items(), key=lambda x: x[1], reverse=True
            )
            common_categories = [cat[0] for cat in common_categories[:5]]  # Top 5

            resolution_rate = (
                (resolved_count / total_interactions * 100) if total_interactions else 0
            )
            escalation_frequency = (
                (escalated_count / total_interactions * 100)
                if total_interactions
                else 0
            )

            # Calculate churn risk (simplified algorithm)
            churn_risk = 0.0
            if avg_satisfaction and avg_satisfaction < 3.0:
                churn_risk += 0.3
            if escalation_frequency > 10:
                churn_risk += 0.2
            if avg_sentiment and avg_sentiment < -0.2:
                churn_risk += 0.3
            if complaint_dates and complaint_dates[-1] > datetime.now(timezone.utc) - timedelta(
                days=30
            ):
                churn_risk += 0.2

            churn_risk = min(churn_risk, 1.0)

            # Update or create summary
            summary_data = {
                "customer_id": customer_id,
                "total_interactions": total_interactions,
                "first_interaction_date": first_interaction.received_at,
                "last_interaction_date": last_interaction.received_at,
                "preferred_channels": preferred_channels,
                "channel_usage_stats": channel_usage,
                "avg_response_time_minutes": avg_response_time,
                "avg_satisfaction_score": avg_satisfaction,
                "overall_sentiment": overall_sentiment,
                "common_categories": common_categories,
                "resolution_rate": resolution_rate,
                "escalation_frequency": escalation_frequency,
                "churn_risk_score": churn_risk,
                "last_complaint_date": (
                    max(complaint_dates) if complaint_dates else None
                ),
                "last_calculated": datetime.now(timezone.utc),
                "tenant_id": self.tenant_id,
            }

            await self.repository.upsert_customer_summary(customer_id, summary_data)

            logger.info(f"Updated customer communication summary: {customer_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating customer communication summary: {e}")
            raise

    # ===== PRIVATE HELPER METHODS =====

    async def _build_contact_response(
        self, contact: CustomerContact
    ) -> CustomerContactResponse:
        """Build complete contact response with channels."""
        channels = await self.repository.get_contact_channels(contact.id)

        return CustomerContactResponse(
            id=contact.id,
            tenant_id=contact.tenant_id,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            customer_id=contact.customer_id,
            contact_type=contact.contact_type,
            first_name=contact.first_name,
            last_name=contact.last_name,
            display_name=contact.display_name,
            title=contact.title,
            department=contact.department,
            primary_language=contact.primary_language,
            timezone=contact.timezone,
            preferred_contact_method=contact.preferred_contact_method,
            is_primary=contact.is_primary,
            is_active=contact.is_active,
            can_authorize_changes=contact.can_authorize_changes,
            can_receive_billing=contact.can_receive_billing,
            can_receive_technical=contact.can_receive_technical,
            marketing_opt_in=contact.marketing_opt_in,
            sms_opt_in=contact.sms_opt_in,
            email_opt_in=contact.email_opt_in,
            notes=contact.notes,
            custom_fields=contact.custom_fields,
            tags=contact.tags,
            full_name=contact.full_name,
            communication_channels=[
                ContactCommunicationChannelResponse(
                    id=ch.id,
                    tenant_id=ch.tenant_id,
                    created_at=ch.created_at,
                    updated_at=ch.updated_at,
                    contact_id=ch.contact_id,
                    channel_type=ch.channel_type,
                    channel_value=ch.channel_value,
                    channel_display_name=ch.channel_display_name,
                    is_verified=ch.is_verified,
                    is_primary=ch.is_primary,
                    is_active=ch.is_active,
                    verification_date=ch.verification_date,
                    platform_user_id=ch.platform_user_id,
                    platform_username=ch.platform_username,
                    platform_data=ch.platform_data,
                    last_used=ch.last_used,
                    usage_count=ch.usage_count,
                    success_count=ch.success_count,
                    failure_count=ch.failure_count,
                    response_rate=ch.response_rate,
                    avg_response_time=ch.avg_response_time,
                    bounce_rate=ch.bounce_rate,
                    metadata=ch.metadata,
                )
                for ch in channels
            ],
        )

    async def _resolve_contact_and_channel(
        self,
        customer_id: UUID,
        contact_id: Optional[UUID],
        channel_id: Optional[UUID],
        channel_type: CommunicationChannel,
    ) -> Tuple[Optional[CustomerContact], Optional[ContactCommunicationChannel]]:
        """Resolve contact and channel for interaction."""
        contact = None
        channel = None

        if contact_id:
            contact = await self.repository.get_customer_contact(contact_id)
        elif customer_id:
            # Try to find primary contact
            contact = await self.repository.get_primary_contact(customer_id)
            if not contact:
                # Get any contact
                contacts = await self.repository.get_customer_contacts(customer_id)
                contact = contacts[0] if contacts else None

        if channel_id:
            channel = await self.repository.get_communication_channel(channel_id)
        elif contact:
            # Try to find primary channel of the specified type
            channel = await self.repository.get_primary_channel(
                contact.id, channel_type
            )
            if not channel:
                # Get any channel of the specified type
                channels = await self.repository.get_contact_channels_by_type(
                    contact.id, channel_type
                )
                channel = channels[0] if channels else None

        return contact, channel

    async def _analyze_interaction_content(self, content: str) -> Dict[str, Any]:
        """Analyze interaction content for intent, sentiment, etc."""
        # Basic keyword analysis - AI/ML not needed for ISP core functionality

        # Simple keyword-based intent detection
        content_lower = content.lower()
        intent = "general"

        if any(word in content_lower for word in ["cancel", "disconnect", "stop"]):
            intent = "cancellation"
        elif any(
            word in content_lower for word in ["bill", "payment", "invoice", "charge"]
        ):
            intent = "billing"
        elif any(
            word in content_lower for word in ["slow", "outage", "down", "not working"]
        ):
            intent = "technical_support"
        elif any(word in content_lower for word in ["upgrade", "new service", "add"]):
            intent = "sales"

        # Simple sentiment analysis
        sentiment_score = 0.0
        sentiment = "neutral"

        positive_words = ["thank", "great", "good", "excellent", "satisfied", "happy"]
        negative_words = [
            "angry",
            "frustrated",
            "terrible",
            "awful",
            "hate",
            "disappointed",
        ]

        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        if positive_count > negative_count:
            sentiment = "positive"
            sentiment_score = 0.3 + (positive_count * 0.1)
        elif negative_count > positive_count:
            sentiment = "negative"
            sentiment_score = -0.3 - (negative_count * 0.1)

        sentiment_score = max(-1.0, min(1.0, sentiment_score)

        # Urgency score
        urgency_keywords = ["urgent", "emergency", "asap", "immediately", "critical"]
        urgency_score = 0.5
        for keyword in urgency_keywords:
            if keyword in content_lower:
                urgency_score = min(1.0, urgency_score + 0.2)
                break

        # Extract keywords
        words = content_lower.split()
        keywords = [word for word in words if len(word) > 4][
            :10
        ]  # First 10 words > 4 chars

        return {
            "intent": intent,
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "urgency_score": urgency_score,
            "language": "en",  # Default to English - language detection not needed for ISP core
            "keywords": keywords,
        }

    async def _route_interaction(self, interaction: CommunicationInteraction) -> bool:
        """Perform intelligent routing for interaction."""
        try:
            # Get applicable routing rules
            rules = await self.repository.get_active_routing_rules()

            # Evaluate rules in priority order
            for rule in sorted(rules, key=lambda x: x.priority, reverse=True):
                if await self._evaluate_routing_rule(interaction, rule):
                    # Rule matched - apply routing
                    if rule.target_agent_id:
                        await self._assign_interaction_to_agent(
                            interaction.id, rule.target_agent_id
                        )
                    elif rule.target_team_id:
                        await self._route_interaction_to_team(
                            interaction, rule.target_team_id
                        )

                    # Update rule usage
                    await self.repository.update_routing_rule(
                        rule.id,
                        {
                            "usage_count": rule.usage_count + 1,
                            "last_used": datetime.now(timezone.utc),
                        },
                    )

                    return True

            # No specific rule matched - use default routing
            await self._default_route_interaction(interaction)
            return True

        except Exception as e:
            logger.error(f"Error routing interaction: {e}")
            return False

    async def _evaluate_routing_rule(
        self, interaction: CommunicationInteraction, rule: RoutingRule
    ) -> bool:
        """Evaluate if routing rule conditions are met."""
        conditions = rule.conditions

        # Simple condition evaluation
        # Simple rules engine - complex rule evaluation not needed for ISP operations

        if "channel_type" in conditions:
            if interaction.channel_type.value not in conditions["channel_type"]:
                return False

        if "priority" in conditions:
            if interaction.priority not in conditions["priority"]:
                return False

        if "category" in conditions:
            if (
                not interaction.category
                or interaction.category not in conditions["category"]
            ):
                return False

        if "sentiment" in conditions:
            if (
                not interaction.sentiment
                or interaction.sentiment not in conditions["sentiment"]
            ):
                return False

        if "keywords" in conditions:
            required_keywords = conditions["keywords"]
            interaction_keywords = interaction.keywords or []
            if not any(kw in interaction_keywords for kw in required_keywords):
                return False

        if "business_hours_only" in conditions and conditions["business_hours_only"]:
            # Simple business hours check (9 AM - 5 PM, Mon-Fri)
            from datetime import datetime
            now = datetime.now(timezone.utc)
            weekday = now.weekday()  # 0=Monday, 6=Sunday
            hour = now.hour
            
            if weekday >= 5 or hour < 9 or hour >= 17:  # Weekend or outside 9-5
                return False

        return True

    async def _assign_interaction_to_agent(
        self, interaction_id: UUID, agent_id: UUID
    ) -> bool:
        """Assign interaction to specific agent."""
        try:
            agent = await self.repository.get_agent(agent_id)
            if not agent or not agent.is_available:
                return False

            # Update interaction assignment
            await self.repository.update_interaction(
                interaction_id,
                {
                    "assigned_agent_id": agent_id,
                    "assigned_team": agent.team.team_name if agent.team else None,
                    "status": InteractionStatus.IN_PROGRESS,
                },
            )

            # Update agent workload
            await self._update_agent_workload(agent_id, 1)

            return True

        except Exception as e:
            logger.error(f"Error assigning interaction to agent: {e}")
            return False

    async def _route_interaction_to_team(
        self, interaction: CommunicationInteraction, team_id: UUID
    ) -> bool:
        """Route interaction to team using team's routing strategy."""
        try:
            team = await self.repository.get_team(team_id)
            if not team:
                return False

            # Get available agents in team
            agents = await self.repository.get_available_team_agents(team_id)
            if not agents:
                # No available agents - add to team queue
                await self.repository.add_to_team_queue(team_id, interaction.id)
                return True

            # Apply team routing strategy
            selected_agent = None

            if team.routing_strategy == RoutingStrategy.ROUND_ROBIN:
                selected_agent = await self._round_robin_selection(agents)
            elif team.routing_strategy == RoutingStrategy.LEAST_BUSY:
                selected_agent = min(agents, key=lambda x: x.current_interactions)
            elif team.routing_strategy == RoutingStrategy.SKILL_BASED:
                selected_agent = await self._skill_based_selection(agents, interaction)
            else:
                selected_agent = agents[0]  # Fallback to first available

            if selected_agent:
                return await self._assign_interaction_to_agent(
                    interaction.id, selected_agent.id
                )

            return False

        except Exception as e:
            logger.error(f"Error routing interaction to team: {e}")
            return False

    async def _default_route_interaction(
        self, interaction: CommunicationInteraction
    ) -> bool:
        """Default routing when no specific rules match."""
        # Route to general support team or available agent
        general_team = await self.repository.get_team_by_code("GENERAL")
        if general_team:
            return await self._route_interaction_to_team(interaction, general_team.id)

        # Fallback: assign to any available agent
        agents = await self.repository.get_available_agents()
        if agents:
            return await self._assign_interaction_to_agent(interaction.id, agents[0].id)

        # No agents available - interaction remains unassigned
        logger.warning(f"No agents available for interaction: {interaction.id}")
        return False

    async def _update_agent_workload(self, agent_id: UUID, change: int) -> None:
        """Update agent current workload."""
        agent = await self.repository.get_agent(agent_id)
        if agent:
            new_count = max(0, agent.current_interactions + change)
            new_load = (new_count / agent.max_concurrent_interactions) * 100

            update_data = {
                "current_interactions": new_count,
                "current_load_percentage": new_load,
                "last_activity": datetime.now(timezone.utc),
            }

            # Update status based on workload
            if new_count == 0 and agent.status == AgentStatus.BUSY:
                update_data["status"] = AgentStatus.AVAILABLE
            elif new_count > 0 and agent.status == AgentStatus.AVAILABLE:
                update_data["status"] = AgentStatus.BUSY

            await self.repository.update_agent(agent_id, update_data)

    async def _update_channel_usage(self, channel_id: UUID) -> None:
        """Update communication channel usage statistics."""
        await self.repository.update_channel(
            channel_id,
            {
                "last_used": datetime.now(timezone.utc),
                "usage_count": func.coalesce(ContactCommunicationChannel.usage_count, 0)
                + 1,
            },
        )

    def _validate_routing_conditions(self, conditions: Dict[str, Any]) -> None:
        """Validate routing rule conditions format."""
        allowed_fields = [
            "channel_type",
            "priority",
            "category",
            "sentiment",
            "keywords",
            "business_hours_only",
            "customer_tier",
        ]

        for field in conditions.keys():
            if field not in allowed_fields:
                raise ValidationError(f"Invalid routing condition field: {field}")

    def _empty_performance_metrics(
        self, agent_id: UUID, date: datetime, period: str
    ) -> Dict[str, Any]:
        """Return empty performance metrics structure."""
        return {
            "agent_id": agent_id,
            "metric_date": date,
            "metric_period": period,
            "total_interactions": 0,
            "interactions_by_channel": {},
            "avg_response_time_seconds": None,
            "median_response_time_seconds": None,
            "first_response_sla_met_count": 0,
            "first_response_sla_total_count": 0,
            "first_response_sla_rate": 0,
            "avg_resolution_time_seconds": None,
            "median_resolution_time_seconds": None,
            "resolution_sla_met_count": 0,
            "resolution_sla_total_count": 0,
            "resolution_sla_rate": 0,
            "customer_satisfaction_avg": None,
            "customer_satisfaction_count": 0,
            "resolution_rate": 0,
            "escalation_rate": 0,
            "calculated_at": datetime.now(timezone.utc),
        }

    async def _round_robin_selection(
        self, agents: List[OmnichannelAgent]
    ) -> Optional[OmnichannelAgent]:
        """Select agent using round-robin strategy."""
        # Simple round-robin - return agent with least recent assignment
        return min(agents, key=lambda x: x.last_activity or datetime.min)

    async def _skill_based_selection(
        self, agents: List[OmnichannelAgent], interaction: CommunicationInteraction
    ) -> Optional[OmnichannelAgent]:
        """Select agent based on skills matching."""
        # Basic skill matching - return first available agent
        return agents[0] if agents else None

    async def _process_agent_queue(self, agent_id: UUID) -> None:
        """Process queued interactions when agent becomes available."""
        # Basic queue processing - assign pending interactions to available agent
        try:
            # Get pending interactions from queue
            pending_interactions = await self.repository.get_pending_interactions_for_agent(agent_id)
            
            # Assign up to 5 pending interactions to the agent
            for interaction in pending_interactions[:5]:
                await self._assign_interaction_to_agent(interaction.id, agent_id)
                logger.info(f"Assigned queued interaction {interaction.id} to agent {agent_id}")
        except Exception as e:
            logger.error(f"Error processing agent queue: {e}")

    async def _reassign_agent_interactions(self, agent_id: UUID) -> None:
        """Reassign active interactions when agent becomes unavailable."""
        active_interactions = await self.repository.get_agent_active_interactions(
            agent_id
        )

        for interaction in active_interactions:
            # Try to reassign to another available agent
            available_agents = await self.repository.get_available_agents(
                channel_type=interaction.channel_type
            )

            if available_agents:
                # Reassign to least busy agent
                target_agent = min(
                    available_agents, key=lambda x: x.current_interactions
                )
                await self._assign_interaction_to_agent(interaction.id, target_agent.id)
            else:
                # No agents available - mark as pending
                await self.repository.update_interaction(
                    interaction.id,
                    {"status": InteractionStatus.PENDING, "assigned_agent_id": None},
                )

        # Update original agent workload
        await self.repository.update_agent(
            agent_id, {"current_interactions": 0, "current_load_percentage": 0.0}
        )
