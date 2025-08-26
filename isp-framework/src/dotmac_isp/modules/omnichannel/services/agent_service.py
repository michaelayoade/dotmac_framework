"""Agent management service."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
)

from ..models import AgentStatus, CommunicationChannel
from ..schemas import (
    OmnichannelAgentCreate,
    OmnichannelAgentUpdate,
    AgentTeamCreate,
    AgentSearchFilters,
)
from .base_service import BaseOmnichannelService

logger = logging.getLogger(__name__)


class AgentService(BaseOmnichannelService):
    """Service for agent management operations."""

    async def create_agent(self, agent_data: OmnichannelAgentCreate) -> UUID:
        """Create new omnichannel agent."""
        try:
            logger.info(f"Creating agent: {agent_data.display_name}")

            # Check for duplicate agent email/username
            existing = await self.repository.get_agent_by_email(agent_data.email)
            if existing:
                raise BusinessRuleError(
                    f"Agent already exists with email: {agent_data.email}"
                )

            # Create agent
            agent = await self.repository.create_agent(
                {
                    **agent_data.model_dump(),
                    "tenant_id": self.tenant_id,
                    "status": AgentStatus.OFFLINE,
                    "created_at": datetime.now(timezone.utc),
                }
            )

            # Initialize agent schedule if provided
            if agent_data.schedule:
                await self._create_agent_schedule(agent.id, agent_data.schedule)

            logger.info(f"Created agent: {agent.id}")
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

            # Validate status transition
            if not self._is_valid_status_transition(agent.status, status):
                raise BusinessRuleError(
                    f"Invalid status transition: {agent.status} -> {status}"
                )

            # Update agent status
            update_data = {
                "status": status,
                "status_message": message,
                "last_activity_at": datetime.now(timezone.utc),
            }

            # Set online/offline timestamps
            if status == AgentStatus.AVAILABLE:
                update_data["online_since"] = datetime.now(timezone.utc)
            elif status == AgentStatus.OFFLINE:
                update_data["offline_since"] = datetime.now(timezone.utc)
                update_data["online_since"] = None

            await self.repository.update_agent(agent_id, update_data)

            # Log status change for metrics
            await self._log_agent_status_change(agent_id, agent.status, status)

            logger.info(f"Updated agent status: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating agent status: {e}")
            return False

    async def create_team(self, team_data: AgentTeamCreate) -> UUID:
        """Create new agent team."""
        try:
            logger.info(f"Creating team: {team_data.name}")

            # Check for duplicate team name
            existing = await self.repository.get_team_by_name(team_data.name)
            if existing:
                raise BusinessRuleError(f"Team already exists: {team_data.name}")

            # Create team
            team = await self.repository.create_team(
                {
                    **team_data.model_dump(),
                    "tenant_id": self.tenant_id,
                    "created_at": datetime.now(timezone.utc),
                }
            )

            logger.info(f"Created team: {team.id}")
            return team.id

        except Exception as e:
            logger.error(f"Error creating team: {e}")
            raise

    async def assign_agent_to_team(self, agent_id: UUID, team_id: UUID) -> bool:
        """Assign agent to team."""
        try:
            logger.info(f"Assigning agent {agent_id} to team {team_id}")

            # Validate agent exists
            agent = await self.repository.get_agent(agent_id)
            if not agent:
                raise EntityNotFoundError(f"Agent not found: {agent_id}")

            # Validate team exists
            team = await self.repository.get_team(team_id)
            if not team:
                raise EntityNotFoundError(f"Team not found: {team_id}")

            # Update agent team assignment
            await self.repository.update_agent(
                agent_id, {"team_id": team_id, "assigned_to_team_at": datetime.now(timezone.utc)}
            )

            logger.info(f"Assigned agent to team: {agent_id} -> {team_id}")
            return True

        except Exception as e:
            logger.error(f"Error assigning agent to team: {e}")
            return False

    async def get_available_agents(
        self,
        channel_type: Optional[CommunicationChannel] = None,
        team_id: Optional[UUID] = None,
        skills: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of available agents with optional filtering."""
        try:
            agents = await self.repository.get_available_agents(
                channel_type=channel_type,
                team_id=team_id,
                skills=skills,
                tenant_id=self.tenant_id,
            )

            return [
                {
                    "id": agent.id,
                    "display_name": agent.display_name,
                    "email": agent.email,
                    "status": agent.status,
                    "team": agent.team.name if agent.team else None,
                    "skills": agent.skills or [],
                    "current_workload": await self._get_agent_workload(agent.id),
                    "online_since": agent.online_since,
                }
                for agent in agents
            ]

        except Exception as e:
            logger.error(f"Error getting available agents: {e}")
            raise

    async def get_agent_performance_metrics(
        self, agent_id: UUID, date_from: datetime, date_to: datetime
    ) -> Dict[str, Any]:
        """Get agent performance metrics for date range."""
        try:
            metrics = await self.repository.get_agent_performance_metrics(
                agent_id, date_from, date_to
            )

            if not metrics:
                return {
                    "agent_id": agent_id,
                    "period_start": date_from,
                    "period_end": date_to,
                    "interactions_handled": 0,
                    "avg_response_time": 0,
                    "avg_resolution_time": 0,
                    "customer_satisfaction": 0,
                    "utilization_rate": 0,
                }

            return {
                "agent_id": agent_id,
                "period_start": date_from,
                "period_end": date_to,
                "interactions_handled": metrics.interactions_handled,
                "avg_response_time": metrics.avg_response_time_seconds,
                "avg_resolution_time": metrics.avg_resolution_time_seconds,
                "customer_satisfaction": metrics.avg_satisfaction_score,
                "utilization_rate": metrics.utilization_percentage,
            }

        except Exception as e:
            logger.error(f"Error getting agent performance: {e}")
            raise

    def _is_valid_status_transition(
        self, current_status: AgentStatus, new_status: AgentStatus
    ) -> bool:
        """Validate agent status transition."""
        valid_transitions = {
            AgentStatus.OFFLINE: [AgentStatus.AVAILABLE, AgentStatus.AWAY],
            AgentStatus.AVAILABLE: [
                AgentStatus.BUSY,
                AgentStatus.AWAY,
                AgentStatus.OFFLINE,
            ],
            AgentStatus.BUSY: [
                AgentStatus.AVAILABLE,
                AgentStatus.AWAY,
                AgentStatus.OFFLINE,
            ],
            AgentStatus.AWAY: [AgentStatus.AVAILABLE, AgentStatus.OFFLINE],
        }

        return new_status in valid_transitions.get(current_status, [])

    async def _log_agent_status_change(
        self, agent_id: UUID, old_status: AgentStatus, new_status: AgentStatus
    ) -> None:
        """Log agent status change for analytics."""
        await self.repository.create_agent_activity_log(
            {
                "agent_id": agent_id,
                "activity_type": "STATUS_CHANGE",
                "old_value": old_status,
                "new_value": new_status,
                "timestamp": datetime.now(timezone.utc),
                "tenant_id": self.tenant_id,
            }
        )

    async def _create_agent_schedule(
        self, agent_id: UUID, schedule_data: Dict[str, Any]
    ) -> None:
        """Create agent schedule."""
        await self.repository.create_agent_schedule(
            {
                "agent_id": agent_id,
                **schedule_data,
                "tenant_id": self.tenant_id,
                "created_at": datetime.now(timezone.utc),
            }
        )

    async def _get_agent_workload(self, agent_id: UUID) -> Dict[str, Any]:
        """Get current agent workload."""
        active_interactions = await self.repository.get_agent_active_interactions(
            agent_id
        )

        return {
            "active_interactions": len(active_interactions),
            "max_capacity": 10,  # This should come from agent settings
            "utilization": len(active_interactions) / 10 * 100,
        }
