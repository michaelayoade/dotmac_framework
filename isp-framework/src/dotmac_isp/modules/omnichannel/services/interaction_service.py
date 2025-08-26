"""Communication interaction management service."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from uuid import UUID, uuid4

from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
)

from ..models import (
    CommunicationInteraction,
    InteractionResponse,
    InteractionEscalation,
    InteractionType,
    InteractionStatus,
    EscalationTrigger,
)
from ..schemas import (
    CommunicationInteractionCreate,
    InteractionResponseCreate,
    InteractionEscalationCreate,
    InteractionSearchFilters,
)
from .base_service import BaseOmnichannelService

logger = logging.getLogger(__name__)


class InteractionService(BaseOmnichannelService):
    """Service for communication interaction management."""

    async def create_interaction(
        self, interaction_data: CommunicationInteractionCreate
    ) -> str:
        """Create a new communication interaction."""
        try:
            logger.info(
                f"Creating interaction for contact: {interaction_data.contact_id}"
            )

            # Validate contact exists
            contact = await self.repository.get_customer_contact(
                interaction_data.contact_id
            )
            if not contact:
                raise EntityNotFoundError(
                    f"Contact not found: {interaction_data.contact_id}"
                )

            # Generate interaction reference
            interaction_ref = f"INT-{uuid4().hex[:8].upper()}"

            # Determine routing based on channel and interaction type
            routing_info = await self._determine_routing(
                interaction_data.channel_type,
                interaction_data.interaction_type,
                interaction_data.priority or "medium",
            )

            # Create interaction
            interaction = await self.repository.create_interaction(
                {
                    **interaction_data.model_dump(),
                    "tenant_id": self.tenant_id,
                    "interaction_reference": interaction_ref,
                    "status": InteractionStatus.OPEN,
                    "assigned_agent_id": routing_info.get("agent_id"),
                    "assigned_team_id": routing_info.get("team_id"),
                    "created_at": datetime.now(timezone.utc),
                }
            )

            # Log interaction creation
            await self._log_interaction_event(
                interaction.id,
                "CREATED",
                f"Interaction created via {interaction_data.channel_type}",
            )

            logger.info(f"Created interaction: {interaction_ref}")
            return interaction_ref

        except Exception as e:
            logger.error(f"Error creating interaction: {e}")
            raise

    async def add_interaction_response(
        self, response_data: InteractionResponseCreate
    ) -> UUID:
        """Add response to interaction."""
        try:
            logger.info(
                f"Adding response to interaction: {response_data.interaction_id}"
            )

            # Validate interaction exists
            interaction = await self.repository.get_interaction(
                response_data.interaction_id
            )
            if not interaction:
                raise EntityNotFoundError(
                    f"Interaction not found: {response_data.interaction_id}"
                )

            # Create response
            response = await self.repository.create_interaction_response(
                {
                    **response_data.model_dump(),
                    "tenant_id": self.tenant_id,
                    "created_at": datetime.now(timezone.utc),
                }
            )

            # Update interaction last activity
            await self.repository.update_interaction(
                interaction.id,
                {
                    "last_activity_at": datetime.now(timezone.utc),
                    "response_count": interaction.response_count + 1,
                },
            )

            # Check if interaction should be auto-resolved
            if response_data.response_type == "resolution":
                await self._auto_resolve_interaction(interaction.id, response.id)

            logger.info(f"Added response: {response.id}")
            return response.id

        except Exception as e:
            logger.error(f"Error adding interaction response: {e}")
            raise

    async def resolve_interaction(
        self, interaction_id: UUID, resolution_notes: Optional[str] = None
    ) -> bool:
        """Resolve interaction with optional notes."""
        try:
            logger.info(f"Resolving interaction: {interaction_id}")

            interaction = await self.repository.get_interaction(interaction_id)
            if not interaction:
                raise EntityNotFoundError(f"Interaction not found: {interaction_id}")

            if interaction.status == InteractionStatus.RESOLVED:
                raise BusinessRuleError("Interaction is already resolved")

            # Update interaction status
            await self.repository.update_interaction(
                interaction_id,
                {
                    "status": InteractionStatus.RESOLVED,
                    "resolved_at": datetime.now(timezone.utc),
                    "resolution_notes": resolution_notes,
                },
            )

            # Log resolution event
            await self._log_interaction_event(
                interaction_id, "RESOLVED", resolution_notes or "Interaction resolved"
            )

            # Update agent metrics if assigned
            if interaction.assigned_agent_id:
                await self._update_agent_resolution_metrics(
                    interaction.assigned_agent_id, interaction_id
                )

            logger.info(f"Resolved interaction: {interaction_id}")
            return True

        except Exception as e:
            logger.error(f"Error resolving interaction: {e}")
            return False

    async def escalate_interaction(
        self, escalation_data: InteractionEscalationCreate
    ) -> UUID:
        """Escalate interaction to higher tier or specialist."""
        try:
            logger.info(f"Escalating interaction: {escalation_data.interaction_id}")

            # Validate interaction
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
                    "tenant_id": self.tenant_id,
                    "escalated_at": datetime.now(timezone.utc),
                }
            )

            # Update interaction with escalation info
            await self.repository.update_interaction(
                interaction.id,
                {
                    "is_escalated": True,
                    "escalation_level": escalation_data.escalation_level,
                    "assigned_agent_id": escalation_data.escalated_to_agent_id,
                    "assigned_team_id": escalation_data.escalated_to_team_id,
                },
            )

            # Log escalation event
            await self._log_interaction_event(
                interaction.id,
                "ESCALATED",
                f"Escalated to level {escalation_data.escalation_level}: {escalation_data.reason}",
            )

            logger.info(f"Escalated interaction: {escalation.id}")
            return escalation.id

        except Exception as e:
            logger.error(f"Error escalating interaction: {e}")
            raise

    async def search_interactions(
        self, filters: InteractionSearchFilters
    ) -> Tuple[List[Dict], int]:
        """Search interactions with filters and pagination."""
        try:
            interactions, total = await self.repository.search_interactions(
                tenant_id=self.tenant_id,
                contact_id=filters.contact_id,
                customer_id=filters.customer_id,
                channel_type=filters.channel_type,
                interaction_type=filters.interaction_type,
                status=filters.status,
                assigned_agent_id=filters.assigned_agent_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
                limit=filters.limit,
                offset=filters.offset,
            )

            # Format response
            results = []
            for interaction in interactions:
                results.append(
                    {
                        "id": interaction.id,
                        "reference": interaction.interaction_reference,
                        "contact_id": interaction.contact_id,
                        "channel_type": interaction.channel_type,
                        "interaction_type": interaction.interaction_type,
                        "status": interaction.status,
                        "priority": interaction.priority,
                        "assigned_agent": (
                            interaction.assigned_agent.display_name
                            if interaction.assigned_agent
                            else None
                        ),
                        "created_at": interaction.created_at,
                        "last_activity": interaction.last_activity_at,
                        "response_count": interaction.response_count,
                    }
                )

            return results, total

        except Exception as e:
            logger.error(f"Error searching interactions: {e}")
            raise

    async def _determine_routing(
        self, channel_type: str, interaction_type: str, priority: str
    ) -> Dict[str, Any]:
        """Determine routing for new interaction."""
        # Get active routing rules
        rules = await self.repository.get_active_routing_rules(
            channel_type=channel_type, interaction_type=interaction_type
        )

        routing_info = {}

        for rule in rules:
            if rule.priority_filter and rule.priority_filter != priority:
                continue

            # Apply routing strategy
            if rule.routing_strategy == "round_robin":
                agent = await self._get_next_round_robin_agent(rule.team_id)
                if agent:
                    routing_info["agent_id"] = agent.id
                    routing_info["team_id"] = rule.team_id
                    break
            elif rule.routing_strategy == "skill_based":
                agent = await self._get_skilled_agent(
                    rule.required_skills, rule.team_id
                )
                if agent:
                    routing_info["agent_id"] = agent.id
                    routing_info["team_id"] = rule.team_id
                    break

        return routing_info

    async def _auto_resolve_interaction(
        self, interaction_id: UUID, resolution_response_id: UUID
    ) -> None:
        """Auto-resolve interaction based on response."""
        await self.repository.update_interaction(
            interaction_id,
            {
                "status": InteractionStatus.RESOLVED,
                "resolved_at": datetime.now(timezone.utc),
                "auto_resolved": True,
                "resolution_response_id": resolution_response_id,
            },
        )

    async def _log_interaction_event(
        self, interaction_id: UUID, event_type: str, description: str
    ) -> None:
        """Log interaction event for audit trail."""
        await self.repository.create_interaction_event(
            {
                "interaction_id": interaction_id,
                "event_type": event_type,
                "description": description,
                "created_at": datetime.now(timezone.utc),
                "tenant_id": self.tenant_id,
            }
        )

    async def _update_agent_resolution_metrics(
        self, agent_id: UUID, interaction_id: UUID
    ) -> None:
        """Update agent metrics after resolution."""
        # This would integrate with analytics service
        pass

    async def _get_next_round_robin_agent(
        self, team_id: Optional[UUID]
    ) -> Optional[Any]:
        """Get next available agent using round-robin."""
        return await self.repository.get_next_available_agent(team_id, "round_robin")

    async def _get_skilled_agent(
        self, required_skills: List[str], team_id: Optional[UUID]
    ) -> Optional[Any]:
        """Get agent with required skills."""
        return await self.repository.get_skilled_agent(required_skills, team_id)
