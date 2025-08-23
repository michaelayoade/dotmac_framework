"""Agent management service for omnichannel communication."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_isp.core.settings import get_settings
from dotmac_isp.shared.exceptions import EntityNotFoundError, ValidationError

from .models import AgentStatus
from .repository import OmnichannelRepository
from .schemas import (
    AgentSearchFilters,
    AgentTeamCreate,
    OmnichannelAgentCreate,
    OmnichannelAgentUpdate,
)

logger = logging.getLogger(__name__)


class AgentManager:
    """Service class for managing omnichannel agents."""

    def __init__(self, db: Session, tenant_id: UUID):
        """Initialize agent manager."""
        self.db = db
        self.tenant_id = tenant_id
        self.repository = OmnichannelRepository(db, tenant_id)
        self.settings = get_settings()

    async def create_agent(self, agent_data: OmnichannelAgentCreate) -> UUID:
        """Create a new omnichannel agent."""
        try:
            logger.info(f"Creating agent: {agent_data.email}")

            # Check for duplicate email
            existing_agent = await self.repository.get_agent_by_email(agent_data.email)
            if existing_agent:
                raise ValidationError(
                    f"Agent with email {agent_data.email} already exists"
                )

            # Create agent
            agent_dict = agent_data.dict()
            agent_dict.update(
                {
                    "tenant_id": self.tenant_id,
                    "status": agent_data.status or AgentStatus.INACTIVE,
                    "created_at": datetime.utcnow(),
                }
            )

            agent = await self.repository.create_agent(agent_dict)

            logger.info(f"Created agent: {agent.id}")
            return agent.id

        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            raise

    async def update_agent_status(
        self, agent_id: UUID, status: AgentStatus, message: Optional[str] = None
    ) -> bool:
        """Update agent status."""
        try:
            # Validate agent exists
            agent = await self.repository.get_agent(agent_id)
            if not agent:
                raise EntityNotFoundError(f"Agent not found: {agent_id}")

            # Update status
            update_data = {
                "status": status,
                "status_message": message,
                "updated_at": datetime.utcnow(),
            }

            # Record status change timestamp
            if status == AgentStatus.ONLINE:
                update_data["last_online_at"] = datetime.utcnow()
            elif status == AgentStatus.OFFLINE:
                update_data["last_offline_at"] = datetime.utcnow()

            await self.repository.update_agent(agent_id, update_data)

            logger.info(f"Updated agent {agent_id} status to {status.value}")
            return True

        except Exception as e:
            logger.error(f"Error updating agent status: {e}")
            raise

    async def create_team(self, team_data: AgentTeamCreate) -> UUID:
        """Create a new agent team."""
        try:
            logger.info(f"Creating team: {team_data.name}")

            # Create team
            team_dict = team_data.dict()
            team_dict.update(
                {"tenant_id": self.tenant_id, "created_at": datetime.utcnow()}
            )

            team = await self.repository.create_team(team_dict)

            logger.info(f"Created team: {team.id}")
            return team.id

        except Exception as e:
            logger.error(f"Error creating team: {e}")
            raise

    async def assign_agent_to_team(self, agent_id: UUID, team_id: UUID) -> bool:
        """Assign agent to a team."""
        try:
            # Validate agent exists
            agent = await self.repository.get_agent(agent_id)
            if not agent:
                raise EntityNotFoundError(f"Agent not found: {agent_id}")

            # Validate team exists
            team = await self.repository.get_team(team_id)
            if not team:
                raise EntityNotFoundError(f"Team not found: {team_id}")

            # Update agent's team assignment
            await self.repository.update_agent(
                agent_id, {"team_id": team_id, "updated_at": datetime.utcnow()}
            )

            logger.info(f"Assigned agent {agent_id} to team {team_id}")
            return True

        except Exception as e:
            logger.error(f"Error assigning agent to team: {e}")
            raise

    async def get_available_agents(
        self, skills: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get list of available agents optionally filtered by skills."""
        try:
            agents = await self.repository.get_available_agents(skills)

            return [
                {
                    "id": str(agent.id),
                    "name": f"{agent.first_name} {agent.last_name}".strip(),
                    "email": agent.email,
                    "status": agent.status.value,
                    "skills": agent.skills or [],
                    "current_interactions": agent.current_interactions or 0,
                    "max_interactions": agent.max_interactions or 5,
                    "last_online_at": (
                        agent.last_online_at.isoformat()
                        if agent.last_online_at
                        else None
                    ),
                }
                for agent in agents
            ]

        except Exception as e:
            logger.error(f"Error getting available agents: {e}")
            raise

    async def get_agent_performance(self, agent_id: UUID, days: int = 30) -> Dict:
        """Get agent performance metrics."""
        try:
            # Validate agent exists
            agent = await self.repository.get_agent(agent_id)
            if not agent:
                raise EntityNotFoundError(f"Agent not found: {agent_id}")

            # Get performance metrics
            metrics = await self.repository.get_agent_performance_metrics(
                agent_id, days
            )

            return {
                "agent_id": str(agent_id),
                "period_days": days,
                "total_interactions": metrics.get("total_interactions", 0),
                "resolved_interactions": metrics.get("resolved_interactions", 0),
                "escalated_interactions": metrics.get("escalated_interactions", 0),
                "average_response_time": metrics.get("avg_response_time_minutes", 0),
                "average_resolution_time": metrics.get("avg_resolution_time_hours", 0),
                "customer_satisfaction_score": metrics.get("avg_satisfaction_score", 0),
                "online_time_hours": metrics.get("total_online_hours", 0),
            }

        except Exception as e:
            logger.error(f"Error getting agent performance: {e}")
            raise
