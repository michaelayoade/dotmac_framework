"""Omnichannel system repository layer for database operations."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import and_, or_, func, text, desc, asc, distinct
from sqlalchemy.exc import IntegrityError, NoResultFound

from datetime import timezone
from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    DatabaseError,
    DuplicateEntityError,
)
from dotmac_isp.modules.identity.repository import CustomerRepository, UserRepository

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

logger = logging.getLogger(__name__)


class OmnichannelRepository:
    """Repository for omnichannel database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """Initialize repository with database session and tenant context."""
        self.db = db
        self.tenant_id = tenant_id
        
        # Initialize related repositories
        self.customer_repository = CustomerRepository(db, tenant_id)
        self.user_repository = UserRepository(db, tenant_id)

        logger.debug(f"Initialized OmnichannelRepository for tenant: {tenant_id}")

    # ===== CUSTOMER CONTACT OPERATIONS =====

    async def create_customer_contact(
        self, contact_data: Dict[str, Any]
    ) -> CustomerContact:
        """Create new customer contact."""
        try:
            contact = CustomerContact(**contact_data)
            self.db.add(contact)
            self.db.commit()
            self.db.refresh(contact)

            logger.debug(f"Created customer contact: {contact.id}")
            return contact

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating customer contact: {e}")
            raise DuplicateEntityError("Contact already exists")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating customer contact: {e}")
            raise DatabaseError(f"Failed to create contact: {str(e)}")

    async def get_customer_contact(self, contact_id: UUID) -> Optional[CustomerContact]:
        """Get customer contact by ID."""
        try:
            return (
                self.db.query(CustomerContact)
                .filter(
                    and_(
                        CustomerContact.id == contact_id,
                        CustomerContact.tenant_id == self.tenant_id,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting customer contact: {e}")
            raise DatabaseError(f"Failed to get contact: {str(e)}")

    async def get_customer_contacts(self, customer_id: UUID) -> List[CustomerContact]:
        """Get all contacts for a customer."""
        try:
            return (
                self.db.query(CustomerContact)
                .filter(
                    and_(
                        CustomerContact.customer_id == customer_id,
                        CustomerContact.tenant_id == self.tenant_id,
                        CustomerContact.is_active == True,
                    )
                )
                .order_by(
                    desc(CustomerContact.is_primary),
                    CustomerContact.contact_type,
                    CustomerContact.first_name,
                )
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting customer contacts: {e}")
            raise DatabaseError(f"Failed to get contacts: {str(e)}")

    async def get_primary_contact(self, customer_id: UUID) -> Optional[CustomerContact]:
        """Get primary contact for customer."""
        try:
            return (
                self.db.query(CustomerContact)
                .filter(
                    and_(
                        CustomerContact.customer_id == customer_id,
                        CustomerContact.tenant_id == self.tenant_id,
                        CustomerContact.is_primary == True,
                        CustomerContact.is_active == True,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting primary contact: {e}")
            raise DatabaseError(f"Failed to get primary contact: {str(e)}")

    async def update_customer_contact(
        self, contact_id: UUID, update_data: Dict[str, Any]
    ) -> CustomerContact:
        """Update customer contact."""
        try:
            contact = await self.get_customer_contact(contact_id)
            if not contact:
                raise EntityNotFoundError(f"Contact not found: {contact_id}")

            for key, value in update_data.items():
                if hasattr(contact, key):
                    setattr(contact, key, value)

            contact.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(contact)

            logger.debug(f"Updated customer contact: {contact_id}")
            return contact

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating customer contact: {e}")
            raise DatabaseError(f"Failed to update contact: {str(e)}")

    async def update_contact(
        self, contact_id: UUID, update_data: Dict[str, Any]
    ) -> bool:
        """Update contact fields."""
        try:
            result = (
                self.db.query(CustomerContact)
                .filter(
                    and_(
                        CustomerContact.id == contact_id,
                        CustomerContact.tenant_id == self.tenant_id,
                    )
                )
                .update(update_data)
            )

            self.db.commit()
            return result > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating contact: {e}")
            raise DatabaseError(f"Failed to update contact: {str(e)}")

    # ===== COMMUNICATION CHANNEL OPERATIONS =====

    async def create_communication_channel(
        self, channel_data: Dict[str, Any]
    ) -> ContactCommunicationChannel:
        """Create communication channel."""
        try:
            channel = ContactCommunicationChannel(**channel_data)
            self.db.add(channel)
            self.db.commit()
            self.db.refresh(channel)

            logger.debug(f"Created communication channel: {channel.id}")
            return channel

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating communication channel: {e}")
            raise DuplicateEntityError("Channel already exists")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating communication channel: {e}")
            raise DatabaseError(f"Failed to create channel: {str(e)}")

    async def get_communication_channel(
        self, channel_id: UUID
    ) -> Optional[ContactCommunicationChannel]:
        """Get communication channel by ID."""
        try:
            return (
                self.db.query(ContactCommunicationChannel)
                .filter(
                    and_(
                        ContactCommunicationChannel.id == channel_id,
                        ContactCommunicationChannel.tenant_id == self.tenant_id,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting communication channel: {e}")
            raise DatabaseError(f"Failed to get channel: {str(e)}")

    async def get_contact_channels(
        self, contact_id: UUID
    ) -> List[ContactCommunicationChannel]:
        """Get all channels for a contact."""
        try:
            return (
                self.db.query(ContactCommunicationChannel)
                .filter(
                    and_(
                        ContactCommunicationChannel.contact_id == contact_id,
                        ContactCommunicationChannel.tenant_id == self.tenant_id,
                        ContactCommunicationChannel.is_active == True,
                    )
                )
                .order_by(
                    desc(ContactCommunicationChannel.is_primary),
                    ContactCommunicationChannel.channel_type,
                )
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting contact channels: {e}")
            raise DatabaseError(f"Failed to get channels: {str(e)}")

    async def get_contact_channels_by_type(
        self, contact_id: UUID, channel_type: CommunicationChannel
    ) -> List[ContactCommunicationChannel]:
        """Get contact channels by type."""
        try:
            return (
                self.db.query(ContactCommunicationChannel)
                .filter(
                    and_(
                        ContactCommunicationChannel.contact_id == contact_id,
                        ContactCommunicationChannel.channel_type == channel_type,
                        ContactCommunicationChannel.tenant_id == self.tenant_id,
                        ContactCommunicationChannel.is_active == True,
                    )
                )
                .order_by(desc(ContactCommunicationChannel.is_primary))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting contact channels by type: {e}")
            raise DatabaseError(f"Failed to get channels by type: {str(e)}")

    async def get_channel_by_value(
        self, channel_type: CommunicationChannel, channel_value: str
    ) -> Optional[ContactCommunicationChannel]:
        """Get channel by type and value."""
        try:
            return (
                self.db.query(ContactCommunicationChannel)
                .filter(
                    and_(
                        ContactCommunicationChannel.channel_type == channel_type,
                        ContactCommunicationChannel.channel_value == channel_value,
                        ContactCommunicationChannel.tenant_id == self.tenant_id,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting channel by value: {e}")
            raise DatabaseError(f"Failed to get channel by value: {str(e)}")

    async def get_primary_channel(
        self, contact_id: UUID, channel_type: CommunicationChannel
    ) -> Optional[ContactCommunicationChannel]:
        """Get primary channel for contact and type."""
        try:
            return (
                self.db.query(ContactCommunicationChannel)
                .filter(
                    and_(
                        ContactCommunicationChannel.contact_id == contact_id,
                        ContactCommunicationChannel.channel_type == channel_type,
                        ContactCommunicationChannel.is_primary == True,
                        ContactCommunicationChannel.tenant_id == self.tenant_id,
                        ContactCommunicationChannel.is_active == True,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting primary channel: {e}")
            raise DatabaseError(f"Failed to get primary channel: {str(e)}")

    async def update_channel(
        self, channel_id: UUID, update_data: Dict[str, Any]
    ) -> bool:
        """Update communication channel."""
        try:
            result = (
                self.db.query(ContactCommunicationChannel)
                .filter(
                    and_(
                        ContactCommunicationChannel.id == channel_id,
                        ContactCommunicationChannel.tenant_id == self.tenant_id,
                    )
                )
                .update(update_data)
            )

            self.db.commit()
            return result > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating channel: {e}")
            raise DatabaseError(f"Failed to update channel: {str(e)}")

    # ===== INTERACTION OPERATIONS =====

    async def create_interaction(
        self, interaction_data: Dict[str, Any]
    ) -> CommunicationInteraction:
        """Create communication interaction."""
        try:
            interaction = CommunicationInteraction(**interaction_data)
            self.db.add(interaction)
            self.db.commit()
            self.db.refresh(interaction)

            logger.debug(f"Created interaction: {interaction.id}")
            return interaction

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating interaction: {e}")
            raise DatabaseError(f"Failed to create interaction: {str(e)}")

    async def get_interaction(
        self, interaction_id: UUID
    ) -> Optional[CommunicationInteraction]:
        """Get interaction by ID."""
        try:
            return (
                self.db.query(CommunicationInteraction)
                .filter(
                    and_(
                        CommunicationInteraction.id == interaction_id,
                        CommunicationInteraction.tenant_id == self.tenant_id,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting interaction: {e}")
            raise DatabaseError(f"Failed to get interaction: {str(e)}")

    async def get_interaction_by_reference(
        self, reference: str
    ) -> Optional[CommunicationInteraction]:
        """Get interaction by reference."""
        try:
            return (
                self.db.query(CommunicationInteraction)
                .filter(
                    and_(
                        CommunicationInteraction.interaction_reference == reference,
                        CommunicationInteraction.tenant_id == self.tenant_id,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting interaction by reference: {e}")
            raise DatabaseError(f"Failed to get interaction by reference: {str(e)}")

    async def update_interaction(
        self, interaction_id: UUID, update_data: Dict[str, Any]
    ) -> bool:
        """Update interaction."""
        try:
            result = (
                self.db.query(CommunicationInteraction)
                .filter(
                    and_(
                        CommunicationInteraction.id == interaction_id,
                        CommunicationInteraction.tenant_id == self.tenant_id,
                    )
                )
                .update(update_data)
            )

            self.db.commit()
            return result > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating interaction: {e}")
            raise DatabaseError(f"Failed to update interaction: {str(e)}")

    async def get_customer_interactions(
        self, customer_id: UUID, limit: Optional[int] = None
    ) -> List[CommunicationInteraction]:
        """Get customer interactions."""
        try:
            query = (
                self.db.query(CommunicationInteraction)
                .filter(
                    and_(
                        CommunicationInteraction.customer_id == customer_id,
                        CommunicationInteraction.tenant_id == self.tenant_id,
                    )
                )
                .order_by(desc(CommunicationInteraction.received_at))
            )

            if limit:
                query = query.limit(limit)

            return query.all()
        except Exception as e:
            logger.error(f"Error getting customer interactions: {e}")
            raise DatabaseError(f"Failed to get customer interactions: {str(e)}")

    async def search_interactions(
        self, filters: Dict[str, Any]
    ) -> Tuple[List[CommunicationInteraction], int]:
        """
        Search interactions with filters.
        
        REFACTORED: Replaced 25-complexity filter chain with Query Builder pattern.
        Complexity reduced from 25 to 3 McCabe score.
        """
        from .query_builders import search_interactions
        
        try:
            # Extract pagination parameters
            page = filters.pop('page', 1)
            per_page = filters.pop('per_page', 20)
            sort_field = filters.pop('sort_field', 'created_at')
            sort_direction = filters.pop('sort_direction', 'desc')
            
            # Use the new query builder
            return search_interactions(
                session=self.db,
                tenant_id=self.tenant_id,
                filters=filters,
                sort_field=sort_field,
                sort_direction=sort_direction,
                page=page,
                per_page=per_page
            )
        except Exception as e:
            logger.error(f"Error searching interactions: {e}")
            raise DatabaseError(f"Failed to search interactions: {str(e)}")

    # ===== INTERACTION RESPONSE OPERATIONS =====

    async def create_interaction_response(
        self, response_data: Dict[str, Any]
    ) -> InteractionResponse:
        """Create interaction response."""
        try:
            response = InteractionResponse(**response_data)
            self.db.add(response)
            self.db.commit()
            self.db.refresh(response)

            logger.debug(f"Created interaction response: {response.id}")
            return response

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating interaction response: {e}")
            raise DatabaseError(f"Failed to create response: {str(e)}")

    async def get_last_interaction_response(
        self, interaction_id: UUID
    ) -> Optional[InteractionResponse]:
        """Get last response for interaction."""
        try:
            return (
                self.db.query(InteractionResponse)
                .filter(
                    and_(
                        InteractionResponse.interaction_id == interaction_id,
                        InteractionResponse.tenant_id == self.tenant_id,
                    )
                )
                .order_by(desc(InteractionResponse.sequence_number))
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting last interaction response: {e}")
            raise DatabaseError(f"Failed to get last response: {str(e)}")

    # ===== AGENT OPERATIONS =====

    async def create_agent(self, agent_data: Dict[str, Any]) -> OmnichannelAgent:
        """Create omnichannel agent."""
        try:
            agent = OmnichannelAgent(**agent_data)
            self.db.add(agent)
            self.db.commit()
            self.db.refresh(agent)

            logger.debug(f"Created omnichannel agent: {agent.id}")
            return agent

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating agent: {e}")
            raise DuplicateEntityError("Agent already exists")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating agent: {e}")
            raise DatabaseError(f"Failed to create agent: {str(e)}")

    async def get_agent(self, agent_id: UUID) -> Optional[OmnichannelAgent]:
        """Get agent by ID."""
        try:
            return (
                self.db.query(OmnichannelAgent)
                .filter(
                    and_(
                        OmnichannelAgent.id == agent_id,
                        OmnichannelAgent.tenant_id == self.tenant_id,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting agent: {e}")
            raise DatabaseError(f"Failed to get agent: {str(e)}")

    async def get_agent_by_user(self, user_id: UUID) -> Optional[OmnichannelAgent]:
        """Get agent by user ID."""
        try:
            return (
                self.db.query(OmnichannelAgent)
                .filter(
                    and_(
                        OmnichannelAgent.user_id == user_id,
                        OmnichannelAgent.tenant_id == self.tenant_id,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting agent by user: {e}")
            raise DatabaseError(f"Failed to get agent by user: {str(e)}")

    async def update_agent(self, agent_id: UUID, update_data: Dict[str, Any]) -> bool:
        """Update agent."""
        try:
            result = (
                self.db.query(OmnichannelAgent)
                .filter(
                    and_(
                        OmnichannelAgent.id == agent_id,
                        OmnichannelAgent.tenant_id == self.tenant_id,
                    )
                )
                .update(update_data)
            )

            self.db.commit()
            return result > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating agent: {e}")
            raise DatabaseError(f"Failed to update agent: {str(e)}")

    async def get_available_agents(
        self,
        channel_type: Optional[CommunicationChannel] = None,
        skill_tags: Optional[List[str]] = None,
    ) -> List[OmnichannelAgent]:
        """Get available agents with optional filters."""
        try:
            query = self.db.query(OmnichannelAgent).filter(
                and_(
                    OmnichannelAgent.tenant_id == self.tenant_id,
                    OmnichannelAgent.status == AgentStatus.AVAILABLE,
                    OmnichannelAgent.is_active == True,
                    OmnichannelAgent.current_interactions
                    < OmnichannelAgent.max_concurrent_interactions,
                )
            )

            if channel_type:
                query = query.filter(
                    OmnichannelAgent.supported_channels.contains([channel_type.value])
                )

            if skill_tags:
                for tag in skill_tags:
                    query = query.filter(OmnichannelAgent.skill_tags.contains([tag]))

            return query.order_by(
                OmnichannelAgent.current_interactions,
                desc(OmnichannelAgent.customer_satisfaction),
            ).all()

        except Exception as e:
            logger.error(f"Error getting available agents: {e}")
            raise DatabaseError(f"Failed to get available agents: {str(e)}")

    async def get_agent_count_by_status(self, status: AgentStatus) -> int:
        """Get count of agents by status."""
        try:
            return (
                self.db.query(OmnichannelAgent)
                .filter(
                    and_(
                        OmnichannelAgent.tenant_id == self.tenant_id,
                        OmnichannelAgent.status == status,
                        OmnichannelAgent.is_active == True,
                    )
                )
                .count()
            )
        except Exception as e:
            logger.error(f"Error getting agent count by status: {e}")
            raise DatabaseError(f"Failed to get agent count: {str(e)}")

    async def get_agent_interactions(
        self, agent_id: UUID, date_from: datetime, date_to: datetime
    ) -> List[CommunicationInteraction]:
        """Get agent interactions for period."""
        try:
            return (
                self.db.query(CommunicationInteraction)
                .filter(
                    and_(
                        CommunicationInteraction.assigned_agent_id == agent_id,
                        CommunicationInteraction.tenant_id == self.tenant_id,
                        CommunicationInteraction.received_at >= date_from,
                        CommunicationInteraction.received_at <= date_to,
                    )
                )
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting agent interactions: {e}")
            raise DatabaseError(f"Failed to get agent interactions: {str(e)}")

    async def get_agent_active_interactions(
        self, agent_id: UUID
    ) -> List[CommunicationInteraction]:
        """Get agent's active interactions."""
        try:
            return (
                self.db.query(CommunicationInteraction)
                .filter(
                    and_(
                        CommunicationInteraction.assigned_agent_id == agent_id,
                        CommunicationInteraction.tenant_id == self.tenant_id,
                        CommunicationInteraction.status.in_(
                            [InteractionStatus.PENDING, InteractionStatus.IN_PROGRESS]
                        ),
                    )
                )
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting agent active interactions: {e}")
            raise DatabaseError(f"Failed to get active interactions: {str(e)}")

    # ===== TEAM OPERATIONS =====

    async def create_team(self, team_data: Dict[str, Any]) -> AgentTeam:
        """Create agent team."""
        try:
            team = AgentTeam(**team_data)
            self.db.add(team)
            self.db.commit()
            self.db.refresh(team)

            logger.debug(f"Created agent team: {team.id}")
            return team

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating team: {e}")
            raise DuplicateEntityError("Team code already exists")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating team: {e}")
            raise DatabaseError(f"Failed to create team: {str(e)}")

    async def get_team(self, team_id: UUID) -> Optional[AgentTeam]:
        """Get team by ID."""
        try:
            return (
                self.db.query(AgentTeam)
                .filter(
                    and_(AgentTeam.id == team_id, AgentTeam.tenant_id == self.tenant_id)
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting team: {e}")
            raise DatabaseError(f"Failed to get team: {str(e)}")

    async def get_team_by_code(self, team_code: str) -> Optional[AgentTeam]:
        """Get team by code."""
        try:
            return (
                self.db.query(AgentTeam)
                .filter(
                    and_(
                        AgentTeam.team_code == team_code,
                        AgentTeam.tenant_id == self.tenant_id,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting team by code: {e}")
            raise DatabaseError(f"Failed to get team by code: {str(e)}")

    async def get_available_team_agents(self, team_id: UUID) -> List[OmnichannelAgent]:
        """Get available agents in team."""
        try:
            return (
                self.db.query(OmnichannelAgent)
                .filter(
                    and_(
                        OmnichannelAgent.team_id == team_id,
                        OmnichannelAgent.tenant_id == self.tenant_id,
                        OmnichannelAgent.status == AgentStatus.AVAILABLE,
                        OmnichannelAgent.is_active == True,
                        OmnichannelAgent.current_interactions
                        < OmnichannelAgent.max_concurrent_interactions,
                    )
                )
                .order_by(OmnichannelAgent.current_interactions)
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting available team agents: {e}")
            raise DatabaseError(f"Failed to get available team agents: {str(e)}")

    # ===== ROUTING OPERATIONS =====

    async def create_routing_rule(self, rule_data: Dict[str, Any]) -> RoutingRule:
        """Create routing rule."""
        try:
            rule = RoutingRule(**rule_data)
            self.db.add(rule)
            self.db.commit()
            self.db.refresh(rule)

            logger.debug(f"Created routing rule: {rule.id}")
            return rule

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating routing rule: {e}")
            raise DuplicateEntityError("Routing rule code already exists")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating routing rule: {e}")
            raise DatabaseError(f"Failed to create routing rule: {str(e)}")

    async def get_active_routing_rules(self) -> List[RoutingRule]:
        """Get active routing rules."""
        try:
            return (
                self.db.query(RoutingRule)
                .filter(
                    and_(
                        RoutingRule.tenant_id == self.tenant_id,
                        RoutingRule.is_active == True,
                    )
                )
                .order_by(desc(RoutingRule.priority))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting active routing rules: {e}")
            raise DatabaseError(f"Failed to get routing rules: {str(e)}")

    async def update_routing_rule(
        self, rule_id: UUID, update_data: Dict[str, Any]
    ) -> bool:
        """Update routing rule."""
        try:
            result = (
                self.db.query(RoutingRule)
                .filter(
                    and_(
                        RoutingRule.id == rule_id,
                        RoutingRule.tenant_id == self.tenant_id,
                    )
                )
                .update(update_data)
            )

            self.db.commit()
            return result > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating routing rule: {e}")
            raise DatabaseError(f"Failed to update routing rule: {str(e)}")

    # ===== ESCALATION OPERATIONS =====

    async def create_escalation(
        self, escalation_data: Dict[str, Any]
    ) -> InteractionEscalation:
        """Create interaction escalation."""
        try:
            escalation = InteractionEscalation(**escalation_data)
            self.db.add(escalation)
            self.db.commit()
            self.db.refresh(escalation)

            logger.debug(f"Created interaction escalation: {escalation.id}")
            return escalation

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating escalation: {e}")
            raise DatabaseError(f"Failed to create escalation: {str(e)}")

    # ===== ANALYTICS OPERATIONS =====

    async def get_interaction_count_by_status(self, status: InteractionStatus) -> int:
        """Get interaction count by status."""
        try:
            return (
                self.db.query(CommunicationInteraction)
                .filter(
                    and_(
                        CommunicationInteraction.tenant_id == self.tenant_id,
                        CommunicationInteraction.status == status,
                    )
                )
                .count()
            )
        except Exception as e:
            logger.error(f"Error getting interaction count by status: {e}")
            raise DatabaseError(f"Failed to get interaction count: {str(e)}")

    async def get_avg_response_time(
        self, date_from: datetime, date_to: datetime
    ) -> Optional[float]:
        """Get average response time for period."""
        try:
            result = (
                self.db.query(func.avg(CommunicationInteraction.response_time_seconds))
                .filter(
                    and_(
                        CommunicationInteraction.tenant_id == self.tenant_id,
                        CommunicationInteraction.received_at >= date_from,
                        CommunicationInteraction.received_at <= date_to,
                        CommunicationInteraction.response_time_seconds.isnot(None),
                    )
                )
                .scalar()
            )

            return float(result) if result else None
        except Exception as e:
            logger.error(f"Error getting average response time: {e}")
            raise DatabaseError(f"Failed to get average response time: {str(e)}")

    async def get_avg_resolution_time(
        self, date_from: datetime, date_to: datetime
    ) -> Optional[float]:
        """Get average resolution time for period."""
        try:
            result = (
                self.db.query(
                    func.avg(CommunicationInteraction.resolution_time_seconds)
                )
                .filter(
                    and_(
                        CommunicationInteraction.tenant_id == self.tenant_id,
                        CommunicationInteraction.received_at >= date_from,
                        CommunicationInteraction.received_at <= date_to,
                        CommunicationInteraction.resolution_time_seconds.isnot(None),
                    )
                )
                .scalar()
            )

            return float(result) if result else None
        except Exception as e:
            logger.error(f"Error getting average resolution time: {e}")
            raise DatabaseError(f"Failed to get average resolution time: {str(e)}")

    async def get_avg_satisfaction(
        self, date_from: datetime, date_to: datetime
    ) -> Optional[float]:
        """Get average satisfaction score for period."""
        try:
            result = (
                self.db.query(func.avg(CommunicationInteraction.customer_satisfaction))
                .filter(
                    and_(
                        CommunicationInteraction.tenant_id == self.tenant_id,
                        CommunicationInteraction.received_at >= date_from,
                        CommunicationInteraction.received_at <= date_to,
                        CommunicationInteraction.customer_satisfaction.isnot(None),
                    )
                )
                .scalar()
            )

            return float(result) if result else None
        except Exception as e:
            logger.error(f"Error getting average satisfaction: {e}")
            raise DatabaseError(f"Failed to get average satisfaction: {str(e)}")

    async def get_sla_compliance_rate(
        self, date_from: datetime, date_to: datetime
    ) -> Optional[float]:
        """Get SLA compliance rate for period."""
        try:
            total_with_response = (
                self.db.query(CommunicationInteraction)
                .filter(
                    and_(
                        CommunicationInteraction.tenant_id == self.tenant_id,
                        CommunicationInteraction.received_at >= date_from,
                        CommunicationInteraction.received_at <= date_to,
                        CommunicationInteraction.response_time_seconds.isnot(None),
                    )
                )
                .count()
            )

            if total_with_response == 0:
                return None

            sla_met = (
                self.db.query(CommunicationInteraction)
                .filter(
                    and_(
                        CommunicationInteraction.tenant_id == self.tenant_id,
                        CommunicationInteraction.received_at >= date_from,
                        CommunicationInteraction.received_at <= date_to,
                        CommunicationInteraction.response_time_seconds
                        <= 300,  # 5 minutes SLA
                    )
                )
                .count()
            )

            return (sla_met / total_with_response) * 100
        except Exception as e:
            logger.error(f"Error getting SLA compliance rate: {e}")
            raise DatabaseError(f"Failed to get SLA compliance rate: {str(e)}")

    async def get_interactions_by_channel(
        self, date_from: datetime, date_to: datetime
    ) -> Dict[str, int]:
        """Get interaction counts by channel for period."""
        try:
            results = (
                self.db.query(
                    CommunicationInteraction.channel_type,
                    func.count(CommunicationInteraction.id).label("count"),
                )
                .filter(
                    and_(
                        CommunicationInteraction.tenant_id == self.tenant_id,
                        CommunicationInteraction.received_at >= date_from,
                        CommunicationInteraction.received_at <= date_to,
                    )
                )
                .group_by(CommunicationInteraction.channel_type)
                .all()
            )

            return {str(result.channel_type.value): result.count for result in results}
        except Exception as e:
            logger.error(f"Error getting interactions by channel: {e}")
            raise DatabaseError(f"Failed to get interactions by channel: {str(e)}")

    async def get_response_times_by_channel(
        self, date_from: datetime, date_to: datetime
    ) -> Dict[str, float]:
        """Get average response times by channel."""
        try:
            results = (
                self.db.query(
                    CommunicationInteraction.channel_type,
                    func.avg(CommunicationInteraction.response_time_seconds).label(
                        "avg_response_time"
                    ),
                )
                .filter(
                    and_(
                        CommunicationInteraction.tenant_id == self.tenant_id,
                        CommunicationInteraction.received_at >= date_from,
                        CommunicationInteraction.received_at <= date_to,
                        CommunicationInteraction.response_time_seconds.isnot(None),
                    )
                )
                .group_by(CommunicationInteraction.channel_type)
                .all()
            )

            return {
                str(result.channel_type.value): float(
                    result.avg_response_time / 60
                )  # Convert to minutes
                for result in results
                if result.avg_response_time
            }
        except Exception as e:
            logger.error(f"Error getting response times by channel: {e}")
            raise DatabaseError(f"Failed to get response times by channel: {str(e)}")

    # ===== UTILITY OPERATIONS =====

    async def get_customer(self, customer_id: UUID) -> Optional[Any]:
        """Get customer from identity module."""
        try:
            customer = self.customer_repository.get_by_id(customer_id)
            if customer:
                return {
                    "id": customer.id,
                    "customer_number": customer.customer_number,
                    "first_name": customer.first_name,
                    "last_name": customer.last_name,
                    "email": customer.email,
                    "phone": customer.phone,
                    "status": customer.account_status.value if customer.account_status else None,
                    "created_at": customer.created_at,
                    "exists": True
                }
            return None
        except Exception as e:
            logger.error(f"Error getting customer {customer_id}: {e}")
            return None

    async def get_user(self, user_id: UUID) -> Optional[Any]:
        """Get user from identity module."""
        try:
            user = self.user_repository.get_by_id(user_id)
            if user:
                return {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "is_active": user.is_active,
                    "role": user.role.value if user.role else None,
                    "created_at": user.created_at,
                    "exists": True
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def upsert_customer_summary(
        self, customer_id: UUID, summary_data: Dict[str, Any]
    ) -> CustomerCommunicationSummary:
        """Upsert customer communication summary."""
        try:
            existing = (
                self.db.query(CustomerCommunicationSummary)
                .filter(
                    and_(
                        CustomerCommunicationSummary.customer_id == customer_id,
                        CustomerCommunicationSummary.tenant_id == self.tenant_id,
                    )
                )
                .first()
            )

            if existing:
                for key, value in summary_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                self.db.commit()
                self.db.refresh(existing)
                return existing
            else:
                summary = CustomerCommunicationSummary(**summary_data)
                self.db.add(summary)
                self.db.commit()
                self.db.refresh(summary)
                return summary

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error upserting customer summary: {e}")
            raise DatabaseError(f"Failed to upsert customer summary: {str(e)}")

    # ===== PLACEHOLDER METHODS FOR MISSING ANALYTICS =====

    async def get_team_utilization_rates(self) -> Dict[str, float]:
        """Get team utilization rates (placeholder)."""
        # Basic placeholder - detailed analytics not needed for ISP core
        return {}

    async def get_team_queue_sizes(self) -> Dict[str, int]:
        """Get team queue sizes (placeholder)."""
        # Basic placeholder - detailed analytics not needed for ISP core
        return {}

    async def get_hourly_interaction_volume(self) -> List[int]:
        """Get hourly interaction volume for last 24 hours (placeholder)."""
        # Basic placeholder - detailed analytics not needed for ISP core
        return [0] * 24

    async def get_hourly_response_times(self) -> List[float]:
        """Get hourly response times for last 24 hours (placeholder)."""
        # Basic placeholder - detailed analytics not needed for ISP core
        return [0.0] * 24

    async def get_breached_sla_count(self) -> int:
        """Get count of breached SLA interactions (placeholder)."""
        # Basic placeholder - detailed analytics not needed for ISP core
        return 0

    async def get_high_priority_queue_size(self) -> int:
        """Get high priority queue size (placeholder)."""
        # Basic placeholder - detailed analytics not needed for ISP core
        return 0

    async def get_escalated_interactions_count(self) -> int:
        """Get count of escalated interactions (placeholder)."""
        # Basic placeholder - detailed analytics not needed for ISP core
        return 0

    async def add_to_team_queue(self, team_id: UUID, interaction_id: UUID) -> bool:
        """Add interaction to team queue (placeholder)."""
        # Basic queue system - track interactions waiting for assignment
        try:
            # For now, we'll use the interactions table with a queue status
            # In a real system, you'd have a separate queue table
            interaction = self.db.query(CommunicationInteraction).filter(
                CommunicationInteraction.id == interaction_id,
                CommunicationInteraction.tenant_id == self.tenant_id
            ).first()
            
            if interaction:
                interaction.status = "queued"
                interaction.assigned_team_id = team_id
                self.db.commit()
                logger.info(f"Added interaction {interaction_id} to team {team_id} queue")
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding to team queue: {e}")
            self.db.rollback()
            return False
    
    async def get_pending_interactions_for_agent(self, agent_id: UUID) -> List[CommunicationInteraction]:
        """Get pending interactions that could be assigned to an agent."""
        try:
            # Get interactions that are queued and waiting for assignment
            interactions = self.db.query(CommunicationInteraction).filter(
                CommunicationInteraction.tenant_id == self.tenant_id,
                CommunicationInteraction.status == "queued",
                CommunicationInteraction.assigned_agent_id.is_(None)
            ).order_by(CommunicationInteraction.created_at).limit(10).all()
            
            return interactions
        except Exception as e:
            logger.error(f"Error getting pending interactions: {e}")
            return []
