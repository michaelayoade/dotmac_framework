"""Interaction management service for omnichannel communication."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from dotmac_isp.core.settings import get_settings
from dotmac_isp.shared.exceptions import (
    BusinessRuleError,
    EntityNotFoundError,
    ValidationError,
)

from .models import InteractionStatus, InteractionType
from .repository import OmnichannelRepository
from .schemas import (
    CommunicationInteractionCreate,
    InteractionEscalationCreate,
    InteractionResponseCreate,
    InteractionSearchFilters,
)

logger = logging.getLogger(__name__)


class InteractionManager:
    """Service class for managing communication interactions."""

    def __init__(self, db: Session, tenant_id: UUID):
        """Initialize interaction manager."""
        self.db = db
        self.tenant_id = tenant_id
        self.repository = OmnichannelRepository(db, tenant_id)
        self.settings = get_settings()

    async def create_interaction(
        self, interaction_data: CommunicationInteractionCreate
    ) -> str:
        """Create a new communication interaction."""
        try:
            logger.info(
                f"Creating interaction for customer: {interaction_data.customer_id}"
            )

            # Validate customer exists
            customer = await self.repository.get_customer(interaction_data.customer_id)
            if not customer:
                raise EntityNotFoundError(
                    f"Customer not found: {interaction_data.customer_id}"
                )

            # Validate contact if provided
            if interaction_data.contact_id:
                contact = await self.repository.get_customer_contact(
                    interaction_data.contact_id
                )
                if not contact:
                    raise EntityNotFoundError(
                        f"Contact not found: {interaction_data.contact_id}"
                    )

            # Set default values
            interaction_dict = interaction_data.model_dump()
            interaction_dict.update(
                {
                    "tenant_id": self.tenant_id,
                    "status": interaction_data.status or InteractionStatus.OPEN,
                    "priority": interaction_data.priority or "medium",
                    "created_at": datetime.now(timezone.utc),
                }
            )

            # Create interaction
            interaction = await self.repository.create_interaction(interaction_dict)

            logger.info(f"Created interaction: {interaction.id}")
            return str(interaction.id)

        except Exception as e:
            logger.error(f"Error creating interaction: {e}")
            raise

    async def add_interaction_response(
        self, response_data: InteractionResponseCreate
    ) -> UUID:
        """Add response to an interaction."""
        try:
            # Validate interaction exists
            interaction = await self.repository.get_interaction(
                response_data.interaction_id
            )
            if not interaction:
                raise EntityNotFoundError(
                    f"Interaction not found: {response_data.interaction_id}"
                )

            # Validate agent if provided
            if response_data.agent_id:
                agent = await self.repository.get_agent(response_data.agent_id)
                if not agent:
                    raise EntityNotFoundError(
                        f"Agent not found: {response_data.agent_id}"
                    )

            # Create response
            response_dict = response_data.model_dump()
            response_dict.update(
                {"tenant_id": self.tenant_id, "created_at": datetime.now(timezone.utc)}
            )

            response = await self.repository.create_interaction_response(response_dict)

            # Update interaction status if specified
            if (
                hasattr(response_data, "update_interaction_status")
                and response_data.update_interaction_status
            ):
                await self.repository.update_interaction(
                    response_data.interaction_id,
                    {
                        "status": response_data.update_interaction_status,
                        "updated_at": datetime.now(timezone.utc),
                    },
                )

            logger.info(
                f"Added response to interaction {response_data.interaction_id}: {response.id}"
            )
            return response.id

        except Exception as e:
            logger.error(f"Error adding interaction response: {e}")
            raise

    async def resolve_interaction(
        self, interaction_id: UUID, resolution_notes: Optional[str] = None
    ) -> bool:
        """Resolve an interaction."""
        try:
            # Validate interaction exists
            interaction = await self.repository.get_interaction(interaction_id)
            if not interaction:
                raise EntityNotFoundError(f"Interaction not found: {interaction_id}")

            # Check if interaction can be resolved
            if interaction.status == InteractionStatus.RESOLVED:
                raise BusinessRuleError("Interaction is already resolved")

            # Update interaction status
            update_data = {
                "status": InteractionStatus.RESOLVED,
                "resolved_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }

            if resolution_notes:
                update_data["resolution_notes"] = resolution_notes

            await self.repository.update_interaction(interaction_id, update_data)

            logger.info(f"Resolved interaction: {interaction_id}")
            return True

        except Exception as e:
            logger.error(f"Error resolving interaction: {e}")
            raise

    async def escalate_interaction(
        self, escalation_data: InteractionEscalationCreate
    ) -> UUID:
        """Escalate an interaction to a higher level."""
        try:
            # Validate interaction exists
            interaction = await self.repository.get_interaction(
                escalation_data.interaction_id
            )
            if not interaction:
                raise EntityNotFoundError(
                    f"Interaction not found: {escalation_data.interaction_id}"
                )

            # Validate escalation target
            if escalation_data.escalated_to_agent_id:
                agent = await self.repository.get_agent(
                    escalation_data.escalated_to_agent_id
                )
                if not agent:
                    raise EntityNotFoundError(
                        f"Target agent not found: {escalation_data.escalated_to_agent_id}"
                    )

            # Create escalation record
            escalation_dict = escalation_data.model_dump()
            escalation_dict.update(
                {"tenant_id": self.tenant_id, "escalated_at": datetime.now(timezone.utc)}
            )

            escalation = await self.repository.create_escalation(escalation_dict)

            # Update interaction status
            await self.repository.update_interaction(
                escalation_data.interaction_id,
                {
                    "status": InteractionStatus.ESCALATED,
                    "updated_at": datetime.now(timezone.utc),
                },
            )

            logger.info(
                f"Escalated interaction {escalation_data.interaction_id}: {escalation.id}"
            )
            return escalation.id

        except Exception as e:
            logger.error(f"Error escalating interaction: {e}")
            raise

    async def search_interactions(
        self, filters: InteractionSearchFilters
    ) -> Tuple[List[Dict], int]:
        """Search interactions with filters."""
        try:
            # Build query conditions
            query_conditions = []

            if filters.customer_id:
                query_conditions.append(f"customer_id = '{filters.customer_id}'")

            if filters.contact_id:
                query_conditions.append(f"contact_id = '{filters.contact_id}'")

            if filters.status:
                if isinstance(filters.status, list):
                    status_list = "', '".join([s.value for s in filters.status])
                    query_conditions.append(f"status IN ('{status_list}')")
                else:
                    query_conditions.append(f"status = '{filters.status.value}'")

            if filters.interaction_type:
                query_conditions.append(
                    f"interaction_type = '{filters.interaction_type.value}'"
                )

            if filters.priority:
                query_conditions.append(f"priority = '{filters.priority}'")

            if filters.date_from:
                query_conditions.append(f"created_at >= '{filters.date_from}'")

            if filters.date_to:
                query_conditions.append(f"created_at <= '{filters.date_to}'")

            # Execute search
            results = await self.repository.search_interactions(
                query_conditions, filters.page or 1, filters.page_size or 20
            )

            # Format results
            formatted_results = []
            for interaction in results["interactions"]:
                formatted_results.append(
                    {
                        "id": str(interaction.id),
                        "customer_id": str(interaction.customer_id),
                        "contact_id": (
                            str(interaction.contact_id)
                            if interaction.contact_id
                            else None
                        ),
                        "subject": interaction.subject,
                        "interaction_type": interaction.interaction_type.value,
                        "status": interaction.status.value,
                        "priority": interaction.priority,
                        "created_at": interaction.created_at.isoformat(),
                        "updated_at": (
                            interaction.updated_at.isoformat()
                            if interaction.updated_at
                            else None
                        ),
                    }
                )

            return formatted_results, results["total_count"]

        except Exception as e:
            logger.error(f"Error searching interactions: {e}")
            raise
