"""Omnichannel orchestrator service that coordinates all domain services."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from dotmac_isp.shared.exceptions import ServiceError

from ..schemas import (
    CustomerContactCreate,
    CustomerContactUpdate,
    CustomerContactResponse,
    ContactCommunicationChannelCreate,
    CommunicationInteractionCreate,
    InteractionResponseCreate,
    OmnichannelAgentCreate,
    AgentTeamCreate,
    RoutingRuleCreate,
    InteractionEscalationCreate,
    InteractionSearchFilters,
    AgentSearchFilters,
    OmnichannelDashboardStats,
)
from .contact_service import ContactService
from .interaction_service import InteractionService
from .agent_service import AgentService
from .routing_service import RoutingService
from .analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class OmnichannelOrchestrator:
    """
    Orchestrator service that coordinates all omnichannel domain services.

    This maintains the same interface as the original monolithic OmnichannelService
    while delegating to focused domain services internally.
    """

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize orchestrator with all domain services."""
        self.db = db
        self.tenant_id = tenant_id

        # Initialize domain services
        self.contact_service = ContactService(db, tenant_id)
        self.interaction_service = InteractionService(db, tenant_id)
        self.agent_service = AgentService(db, tenant_id)
        self.routing_service = RoutingService(db, tenant_id)
        self.analytics_service = AnalyticsService(db, tenant_id)

        logger.info(f"Initialized OmnichannelOrchestrator for tenant: {tenant_id}")

    # ===== CUSTOMER CONTACT MANAGEMENT =====

    async def create_customer_contact(
        self, contact_data: CustomerContactCreate
    ) -> CustomerContactResponse:
        """Create a new customer contact with communication channels."""
        return await self.contact_service.create_customer_contact(contact_data)

    async def update_customer_contact(
        self, contact_id: UUID, update_data: CustomerContactUpdate
    ) -> CustomerContactResponse:
        """Update customer contact information."""
        return await self.contact_service.update_customer_contact(
            contact_id, update_data
        )

    async def add_communication_channel(
        self, channel_data: ContactCommunicationChannelCreate
    ) -> ContactCommunicationChannelCreate:
        """Add communication channel to contact."""
        return await self.contact_service.add_communication_channel(channel_data)

    async def get_customer_contacts(
        self, customer_id: UUID
    ) -> List[CustomerContactResponse]:
        """Get all contacts for a customer."""
        return await self.contact_service.get_customer_contacts(customer_id)

    async def verify_communication_channel(
        self, channel_id: UUID, verification_code: Optional[str] = None
    ) -> bool:
        """Verify communication channel with optional code."""
        return await self.contact_service.verify_communication_channel(
            channel_id, verification_code
        )

    # ===== COMMUNICATION INTERACTION MANAGEMENT =====

    async def create_interaction(
        self, interaction_data: CommunicationInteractionCreate
    ) -> str:
        """Create new communication interaction with intelligent routing."""
        try:
            # Create the interaction
            interaction_ref = await self.interaction_service.create_interaction(
                interaction_data
            )

            # Get the created interaction for routing
            interaction = (
                await self.interaction_service.repository.get_interaction_by_reference(
                    interaction_ref
                )
            )
            if interaction:
                # Route the interaction
                routing_result = await self.routing_service.route_interaction(
                    interaction.id
                )
                logger.info(f"Interaction {interaction_ref} routed: {routing_result}")

            return interaction_ref

        except Exception as e:
            logger.error(f"Error in orchestrated interaction creation: {e}")
            raise

    async def add_interaction_response(
        self, response_data: InteractionResponseCreate
    ) -> UUID:
        """Add response to an interaction."""
        return await self.interaction_service.add_interaction_response(response_data)

    async def resolve_interaction(
        self, interaction_id: UUID, resolution_notes: Optional[str] = None
    ) -> bool:
        """Mark interaction as resolved."""
        return await self.interaction_service.resolve_interaction(
            interaction_id, resolution_notes
        )

    async def escalate_interaction(
        self, escalation_data: InteractionEscalationCreate
    ) -> UUID:
        """Escalate interaction to higher tier or specialist."""
        return await self.interaction_service.escalate_interaction(escalation_data)

    async def search_interactions(
        self, filters: InteractionSearchFilters
    ) -> Tuple[List[Dict], int]:
        """Search interactions with filters and pagination."""
        return await self.interaction_service.search_interactions(filters)

    # ===== AGENT MANAGEMENT =====

    async def create_agent(self, agent_data: OmnichannelAgentCreate) -> UUID:
        """Create new omnichannel agent."""
        return await self.agent_service.create_agent(agent_data)

    async def update_agent_status(
        self, agent_id: UUID, status: Any, message: Optional[str] = None
    ) -> bool:
        """Update agent status and availability."""
        return await self.agent_service.update_agent_status(agent_id, status, message)

    async def create_team(self, team_data: AgentTeamCreate) -> UUID:
        """Create new agent team."""
        return await self.agent_service.create_team(team_data)

    async def assign_agent_to_team(self, agent_id: UUID, team_id: UUID) -> bool:
        """Assign agent to team."""
        return await self.agent_service.assign_agent_to_team(agent_id, team_id)

    async def get_available_agents(
        self,
        channel_type: Optional[Any] = None,
        team_id: Optional[UUID] = None,
        skills: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of available agents with optional filtering."""
        return await self.agent_service.get_available_agents(
            channel_type, team_id, skills
        )

    # ===== INTELLIGENT ROUTING =====

    async def create_routing_rule(self, rule_data: RoutingRuleCreate) -> UUID:
        """Create new routing rule."""
        return await self.routing_service.create_routing_rule(rule_data)

    async def route_interaction(self, interaction_id: UUID) -> Dict[str, Any]:
        """Route interaction to appropriate agent/team."""
        return await self.routing_service.route_interaction(interaction_id)

    # ===== ANALYTICS AND REPORTING =====

    async def get_dashboard_stats(
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> OmnichannelDashboardStats:
        """Get comprehensive dashboard statistics."""
        return await self.analytics_service.get_dashboard_stats(date_from, date_to)

    async def calculate_agent_performance(
        self, agent_id: UUID, date_from: datetime, date_to: datetime
    ) -> Dict[str, Any]:
        """Calculate comprehensive agent performance metrics."""
        return await self.agent_service.get_agent_performance_metrics(
            agent_id, date_from, date_to
        )

    async def get_channel_analytics(
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get channel performance analytics."""
        return await self.analytics_service.get_channel_analytics(date_from, date_to)

    async def get_customer_journey_analytics(
        self,
        customer_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get customer journey analytics."""
        return await self.analytics_service.get_customer_journey_analytics(
            customer_id, date_from, date_to
        )

    # ===== ORCHESTRATION METHODS =====

    async def handle_complex_workflow(
        self, workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle complex workflows that span multiple domains."""
        try:
            workflow_type = workflow_data.get("type")

            if workflow_type == "escalation_with_notification":
                return await self._handle_escalation_workflow(workflow_data)
            elif workflow_type == "customer_onboarding":
                return await self._handle_customer_onboarding_workflow(workflow_data)
            elif workflow_type == "agent_performance_review":
                return await self._handle_agent_review_workflow(workflow_data)
            else:
                raise ServiceError(f"Unknown workflow type: {workflow_type}")

        except Exception as e:
            logger.error(f"Error handling complex workflow: {e}")
            raise

    async def _handle_escalation_workflow(
        self, workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle escalation workflow across services."""
        interaction_id = workflow_data.get("interaction_id")
        escalation_data = workflow_data.get("escalation_data")

        # Escalate the interaction
        escalation_id = await self.interaction_service.escalate_interaction(
            escalation_data
        )

        # Re-route with higher priority
        routing_result = await self.routing_service.route_interaction(interaction_id)

        # Update analytics
        await self.analytics_service.repository.log_escalation_event(
            interaction_id, escalation_id, routing_result
        )

        return {
            "escalation_id": escalation_id,
            "routing_result": routing_result,
            "workflow_status": "completed",
        }

    async def _handle_customer_onboarding_workflow(
        self, workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle customer onboarding workflow."""
        customer_data = workflow_data.get("customer_data")

        # Create customer contact
        contact_response = await self.contact_service.create_customer_contact(
            customer_data
        )

        # Create welcome interaction
        welcome_interaction = await self.interaction_service.create_interaction(
            {
                "contact_id": contact_response.id,
                "channel_type": "email",
                "interaction_type": "onboarding",
                "content": "Welcome to our service!",
                "priority": "normal",
            }
        )

        return {
            "contact_id": contact_response.id,
            "welcome_interaction": welcome_interaction,
            "workflow_status": "completed",
        }

    async def _handle_agent_review_workflow(
        self, workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle agent performance review workflow."""
        agent_id = workflow_data.get("agent_id")
        review_period = workflow_data.get("review_period")

        # Get performance metrics
        performance_data = await self.agent_service.get_agent_performance_metrics(
            agent_id, review_period["start"], review_period["end"]
        )

        # Generate detailed analytics
        analytics_data = await self.analytics_service.get_agent_performance_report(
            agent_id, review_period["start"], review_period["end"]
        )

        return {
            "agent_id": agent_id,
            "performance_metrics": performance_data,
            "detailed_analytics": analytics_data,
            "workflow_status": "completed",
        }


# Maintain backward compatibility - create an alias
OmnichannelService = OmnichannelOrchestrator
