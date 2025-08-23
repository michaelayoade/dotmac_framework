"""Omnichannel orchestrator service that coordinates all omnichannel operations."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_isp.core.settings import get_settings

from .models import AgentStatus
from .schemas import (
    AgentSearchFilters,
    AgentTeamCreate,
    CommunicationInteractionCreate,
    ContactCommunicationChannelCreate,
    CustomerContactCreate,
    CustomerContactResponse,
    CustomerContactUpdate,
    InteractionEscalationCreate,
    InteractionResponseCreate,
    InteractionSearchFilters,
    OmnichannelAgentCreate,
    OmnichannelAgentUpdate,
    OmnichannelDashboardStats,
)
from .service_agent_manager import AgentManager
from .service_contact_manager import ContactManager
from .service_interaction_manager import InteractionManager

logger = logging.getLogger(__name__)


class OmnichannelOrchestrator:
    """Main orchestrator service for all omnichannel operations."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize omnichannel orchestrator."""
        self.db = db
        self.settings = get_settings()
        self.tenant_id = UUID(tenant_id) if tenant_id else UUID(self.settings.tenant_id)

        # Initialize service managers
        self.contact_manager = ContactManager(db, self.tenant_id)
        self.interaction_manager = InteractionManager(db, self.tenant_id)
        self.agent_manager = AgentManager(db, self.tenant_id)

        logger.info(f"Initialized OmnichannelOrchestrator for tenant: {self.tenant_id}")

    # ===== CONTACT MANAGEMENT DELEGATION =====

    async def create_customer_contact(
        self, contact_data: CustomerContactCreate
    ) -> CustomerContactResponse:
        """Create a new customer contact with communication channels."""
        return await self.contact_manager.create_customer_contact(contact_data)

    async def update_customer_contact(
        self, contact_id: UUID, update_data: CustomerContactUpdate
    ) -> CustomerContactResponse:
        """Update existing customer contact."""
        return await self.contact_manager.update_customer_contact(
            contact_id, update_data
        )

    async def add_communication_channel(
        self, channel_data: ContactCommunicationChannelCreate
    ) -> ContactCommunicationChannelCreate:
        """Add communication channel to contact."""
        return await self.contact_manager.add_communication_channel(channel_data)

    async def get_customer_contacts(
        self, customer_id: UUID
    ) -> List[CustomerContactResponse]:
        """Get all contacts for a customer."""
        return await self.contact_manager.get_customer_contacts(customer_id)

    async def verify_communication_channel(
        self, channel_id: UUID, verification_code: Optional[str] = None
    ) -> bool:
        """Verify communication channel with optional code."""
        return await self.contact_manager.verify_communication_channel(
            channel_id, verification_code
        )

    # ===== INTERACTION MANAGEMENT DELEGATION =====

    async def create_interaction(
        self, interaction_data: CommunicationInteractionCreate
    ) -> str:
        """Create a new communication interaction."""
        return await self.interaction_manager.create_interaction(interaction_data)

    async def add_interaction_response(
        self, response_data: InteractionResponseCreate
    ) -> UUID:
        """Add response to an interaction."""
        return await self.interaction_manager.add_interaction_response(response_data)

    async def resolve_interaction(
        self, interaction_id: UUID, resolution_notes: Optional[str] = None
    ) -> bool:
        """Resolve an interaction."""
        return await self.interaction_manager.resolve_interaction(
            interaction_id, resolution_notes
        )

    async def escalate_interaction(
        self, escalation_data: InteractionEscalationCreate
    ) -> UUID:
        """Escalate an interaction to a higher level."""
        return await self.interaction_manager.escalate_interaction(escalation_data)

    async def search_interactions(
        self, filters: InteractionSearchFilters
    ) -> Tuple[List[Dict], int]:
        """Search interactions with filters."""
        return await self.interaction_manager.search_interactions(filters)

    # ===== AGENT MANAGEMENT DELEGATION =====

    async def create_agent(self, agent_data: OmnichannelAgentCreate) -> UUID:
        """Create a new omnichannel agent."""
        return await self.agent_manager.create_agent(agent_data)

    async def update_agent_status(
        self, agent_id: UUID, status: AgentStatus, message: Optional[str] = None
    ) -> bool:
        """Update agent status."""
        return await self.agent_manager.update_agent_status(agent_id, status, message)

    async def create_team(self, team_data: AgentTeamCreate) -> UUID:
        """Create a new agent team."""
        return await self.agent_manager.create_team(team_data)

    async def assign_agent_to_team(self, agent_id: UUID, team_id: UUID) -> bool:
        """Assign agent to a team."""
        return await self.agent_manager.assign_agent_to_team(agent_id, team_id)

    async def get_available_agents(
        self, skills: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get list of available agents optionally filtered by skills."""
        return await self.agent_manager.get_available_agents(skills)

    async def get_agent_performance(self, agent_id: UUID, days: int = 30) -> Dict:
        """Get agent performance metrics."""
        return await self.agent_manager.get_agent_performance(agent_id, days)

    # ===== DASHBOARD AND ANALYTICS =====

    async def get_dashboard_stats(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> OmnichannelDashboardStats:
        """Get dashboard statistics for omnichannel operations."""
        try:
            # This would typically aggregate data from all managers
            # For now, return a basic structure
            stats = OmnichannelDashboardStats(
                total_interactions=0,
                open_interactions=0,
                resolved_interactions=0,
                escalated_interactions=0,
                active_agents=0,
                average_response_time=0,
                customer_satisfaction_score=0,
                channel_breakdown={},
                interaction_trends=[],
                agent_performance_summary={},
            )

            logger.info("Generated dashboard statistics")
            return stats

        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            raise


# Backward compatibility alias
OmnichannelService = OmnichannelOrchestrator
