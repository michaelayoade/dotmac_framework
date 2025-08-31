"""
Agent Management System for Omnichannel Service

Provides comprehensive agent workforce management including:
- Agent status and availability tracking
- Team and hierarchy management
- Performance analytics and KPI tracking
- Workload distribution and capacity planning
- Skill-based matching and routing
- Shift management and scheduling

Author: DotMac Framework Team
License: MIT
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent availability status"""

    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    BREAK = "break"
    AWAY = "away"
    DO_NOT_DISTURB = "do_not_disturb"


class SkillLevel(str, Enum):
    """Agent skill proficiency levels"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class AgentSkill:
    """Agent skill with proficiency level"""

    skill_name: str
    level: SkillLevel
    priority: int = 1
    certified: bool = False
    certification_date: Optional[datetime] = None


@dataclass
class AgentMetrics:
    """Agent performance metrics"""

    total_interactions: int = 0
    avg_response_time: float = 0.0
    avg_resolution_time: float = 0.0
    customer_satisfaction: float = 0.0
    first_contact_resolution: float = 0.0
    active_interactions: int = 0
    max_concurrent: int = 5
    utilization_rate: float = 0.0

    # Time-based metrics
    online_time: timedelta = field(default_factory=lambda: timedelta(0))
    busy_time: timedelta = field(default_factory=lambda: timedelta(0))
    idle_time: timedelta = field(default_factory=lambda: timedelta(0))


@dataclass
class TeamConfiguration:
    """Team configuration and settings"""

    team_id: UUID
    name: str
    description: str
    max_concurrent_per_agent: int = 10
    auto_assignment: bool = True
    escalation_enabled: bool = True
    escalation_timeout: int = 15  # minutes
    required_skills: List[str] = field(default_factory=list)
    priority_multiplier: float = 1.0


class AgentModel(BaseModel):
    """Agent data model"""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    user_id: UUID
    email: str
    full_name: str

    # Status and availability
    status: AgentStatus = AgentStatus.OFFLINE
    status_message: Optional[str] = None
    last_activity: datetime = Field(default_factory=datetime.utcnow)

    # Capacity management
    max_concurrent_interactions: int = 5
    current_interaction_count: int = 0
    capacity_utilization: float = 0.0

    # Skills and capabilities
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    channels: List[str] = Field(default_factory=list)

    # Team and hierarchy
    team_ids: List[UUID] = Field(default_factory=list)
    supervisor_id: Optional[UUID] = None
    role: str = "agent"

    # Scheduling
    shift_start: Optional[str] = None  # HH:MM format
    shift_end: Optional[str] = None
    timezone: str = "UTC"

    # Performance
    performance_rating: float = 5.0
    total_interactions: int = 0
    avg_response_time: float = 0.0
    customer_satisfaction: float = 5.0

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict()
        use_enum_values = True


class TeamModel(BaseModel):
    """Team data model"""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    name: str
    description: str

    # Configuration
    max_concurrent_per_agent: int = 10
    auto_assignment: bool = True
    escalation_enabled: bool = True
    escalation_timeout: int = 15

    # Skills and requirements
    required_skills: List[str] = Field(default_factory=list)
    supported_channels: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)

    # Performance settings
    priority_multiplier: float = 1.0
    sla_target_response: int = 300  # seconds
    sla_target_resolution: int = 3600  # seconds

    # Agent management
    agent_ids: List[UUID] = Field(default_factory=list)
    supervisor_ids: List[UUID] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")


class AgentManager:
    """
    Comprehensive agent management system for omnichannel operations

    Handles agent lifecycle, team management, performance tracking,
    and intelligent workload distribution across the organization.
    """

    def __init__(self, db_session: AsyncSession, tenant_id: UUID):
        self.db = db_session
        self.tenant_id = tenant_id
        self.agent_cache: Dict[UUID, AgentModel] = {}
        self.team_cache: Dict[UUID, TeamModel] = {}
        self.metrics_cache: Dict[UUID, AgentMetrics] = {}

        # Performance tracking
        self.performance_window = timedelta(hours=1)
        self.metrics_update_interval = 60  # seconds

        # Skill matching weights
        self.skill_weights = {
            SkillLevel.EXPERT: 4.0,
            SkillLevel.ADVANCED: 3.0,
            SkillLevel.INTERMEDIATE: 2.0,
            SkillLevel.BEGINNER: 1.0,
        }

    async def create_agent(self, agent_data: Dict[str, Any]) -> AgentModel:
        """Create a new agent"""
        try:
            agent = AgentModel(tenant_id=self.tenant_id, **agent_data)

            # Store in database (implementation depends on your ORM)
            # await self._store_agent(agent)

            # Cache the agent
            self.agent_cache[agent.id] = agent

            # Initialize metrics
            self.metrics_cache[agent.id] = AgentMetrics()

            logger.info(f"Created agent {agent.id} for tenant {self.tenant_id}")
            return agent

        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise

    async def update_agent_status(
        self,
        agent_id: UUID,
        status: AgentStatus,
        status_message: Optional[str] = None,
        max_concurrent: Optional[int] = None,
    ) -> AgentModel:
        """Update agent availability status"""
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            # Update status and timestamp
            old_status = agent.status
            agent.status = status
            agent.status_message = status_message
            agent.last_activity = datetime.utcnow()

            if max_concurrent is not None:
                agent.max_concurrent_interactions = max_concurrent

            # Update capacity based on status
            if status in [AgentStatus.OFFLINE, AgentStatus.DO_NOT_DISTURB]:
                agent.current_interaction_count = 0
                agent.capacity_utilization = 0.0
            else:
                agent.capacity_utilization = (
                    agent.current_interaction_count / agent.max_concurrent_interactions
                )

            # Track status change metrics
            await self._track_status_change(agent, old_status, status)

            # Update cache and database
            self.agent_cache[agent_id] = agent
            # await self._update_agent(agent)

            logger.info(f"Agent {agent_id} status updated: {old_status} -> {status}")
            return agent

        except Exception as e:
            logger.error(f"Failed to update agent status: {e}")
            raise

    async def get_agent(self, agent_id: UUID) -> Optional[AgentModel]:
        """Get agent by ID"""
        try:
            # Check cache first
            if agent_id in self.agent_cache:
                return self.agent_cache[agent_id]

            # Load from database
            # agent = await self._load_agent(agent_id)
            # if agent:
            #     self.agent_cache[agent_id] = agent
            # return agent

            # Temporary return None for missing database implementation
            return self.agent_cache.get(agent_id)

        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None

    async def get_available_agents(
        self,
        channel: Optional[str] = None,
        skills: Optional[List[str]] = None,
        team_id: Optional[UUID] = None,
        min_capacity: float = 0.1,
    ) -> List[AgentModel]:
        """Get available agents matching criteria"""
        try:
            available_agents = []

            for agent in self.agent_cache.values():
                if not self._is_agent_available(agent, min_capacity):
                    continue

                # Filter by channel support
                if channel and channel not in agent.channels:
                    continue

                # Filter by team membership
                if team_id and team_id not in agent.team_ids:
                    continue

                # Filter by skills
                if skills and not self._agent_has_skills(agent, skills):
                    continue

                available_agents.append(agent)

            # Sort by availability score
            available_agents.sort(
                key=lambda a: self._calculate_availability_score(a), reverse=True
            )

            return available_agents

        except Exception as e:
            logger.error(f"Failed to get available agents: {e}")
            return []

    async def assign_interaction(self, agent_id: UUID, interaction_id: UUID) -> bool:
        """Assign interaction to agent"""
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                return False

            # Check capacity
            if agent.current_interaction_count >= agent.max_concurrent_interactions:
                logger.warning(f"Agent {agent_id} at capacity")
                return False

            # Update interaction count
            agent.current_interaction_count += 1
            agent.capacity_utilization = (
                agent.current_interaction_count / agent.max_concurrent_interactions
            )

            # Update status if needed
            if agent.status == AgentStatus.ONLINE and agent.capacity_utilization > 0.8:
                agent.status = AgentStatus.BUSY

            # Update metrics
            metrics = self.metrics_cache.get(agent_id, AgentMetrics())
            metrics.active_interactions = agent.current_interaction_count
            metrics.utilization_rate = agent.capacity_utilization
            self.metrics_cache[agent_id] = metrics

            # Update cache and database
            self.agent_cache[agent_id] = agent
            # await self._update_agent(agent)

            logger.info(f"Assigned interaction {interaction_id} to agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to assign interaction: {e}")
            return False

    async def complete_interaction(self, agent_id: UUID, interaction_id: UUID) -> bool:
        """Mark interaction as completed for agent"""
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                return False

            # Update interaction count
            if agent.current_interaction_count > 0:
                agent.current_interaction_count -= 1

            agent.capacity_utilization = (
                agent.current_interaction_count / agent.max_concurrent_interactions
            )

            # Update status if needed
            if agent.status == AgentStatus.BUSY and agent.capacity_utilization < 0.8:
                agent.status = AgentStatus.ONLINE

            # Update metrics
            metrics = self.metrics_cache.get(agent_id, AgentMetrics())
            metrics.active_interactions = agent.current_interaction_count
            metrics.total_interactions += 1
            metrics.utilization_rate = agent.capacity_utilization
            self.metrics_cache[agent_id] = metrics

            # Update cache and database
            self.agent_cache[agent_id] = agent
            # await self._update_agent(agent)

            logger.info(f"Completed interaction {interaction_id} for agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to complete interaction: {e}")
            return False

    async def create_team(self, team_data: Dict[str, Any]) -> TeamModel:
        """Create a new team"""
        try:
            team = TeamModel(tenant_id=self.tenant_id, **team_data)

            # Store in database
            # await self._store_team(team)

            # Cache the team
            self.team_cache[team.id] = team

            logger.info(f"Created team {team.id} for tenant {self.tenant_id}")
            return team

        except Exception as e:
            logger.error(f"Failed to create team: {e}")
            raise

    async def assign_agent_to_team(self, agent_id: UUID, team_id: UUID) -> bool:
        """Assign agent to team"""
        try:
            agent = await self.get_agent(agent_id)
            team = self.team_cache.get(team_id)

            if not agent or not team:
                return False

            # Add to team
            if team_id not in agent.team_ids:
                agent.team_ids.append(team_id)

            if agent_id not in team.agent_ids:
                team.agent_ids.append(agent_id)

            # Update caches
            self.agent_cache[agent_id] = agent
            self.team_cache[team_id] = team

            # Update database
            # await self._update_agent(agent)
            # await self._update_team(team)

            logger.info(f"Assigned agent {agent_id} to team {team_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to assign agent to team: {e}")
            return False

    async def get_team_performance(
        self, team_id: UUID, date_range: Optional[tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """Get team performance metrics"""
        try:
            team = self.team_cache.get(team_id)
            if not team:
                return {}

            # Aggregate metrics from team agents
            team_metrics = {
                "team_id": team_id,
                "team_name": team.name,
                "agent_count": len(team.agent_ids),
                "online_agents": 0,
                "busy_agents": 0,
                "total_capacity": 0,
                "used_capacity": 0,
                "avg_response_time": 0.0,
                "avg_resolution_time": 0.0,
                "customer_satisfaction": 0.0,
                "total_interactions": 0,
                "active_interactions": 0,
            }

            if not team.agent_ids:
                return team_metrics

            response_times = []
            resolution_times = []
            satisfaction_scores = []

            for agent_id in team.agent_ids:
                agent = self.agent_cache.get(agent_id)
                if not agent:
                    continue

                # Count agent statuses
                if agent.status == AgentStatus.ONLINE:
                    team_metrics["online_agents"] += 1
                elif agent.status == AgentStatus.BUSY:
                    team_metrics["busy_agents"] += 1

                # Aggregate capacity
                team_metrics["total_capacity"] += agent.max_concurrent_interactions
                team_metrics["used_capacity"] += agent.current_interaction_count
                team_metrics["active_interactions"] += agent.current_interaction_count
                team_metrics["total_interactions"] += agent.total_interactions

                # Collect performance metrics
                if agent.avg_response_time > 0:
                    response_times.append(agent.avg_response_time)
                if agent.customer_satisfaction > 0:
                    satisfaction_scores.append(agent.customer_satisfaction)

                # Get detailed metrics from cache
                metrics = self.metrics_cache.get(agent_id)
                if metrics:
                    if metrics.avg_resolution_time > 0:
                        resolution_times.append(metrics.avg_resolution_time)

            # Calculate averages
            if response_times:
                team_metrics["avg_response_time"] = sum(response_times) / len(
                    response_times
                )
            if resolution_times:
                team_metrics["avg_resolution_time"] = sum(resolution_times) / len(
                    resolution_times
                )
            if satisfaction_scores:
                team_metrics["customer_satisfaction"] = sum(satisfaction_scores) / len(
                    satisfaction_scores
                )

            # Calculate utilization rate
            if team_metrics["total_capacity"] > 0:
                team_metrics["utilization_rate"] = (
                    team_metrics["used_capacity"] / team_metrics["total_capacity"]
                )
            else:
                team_metrics["utilization_rate"] = 0.0

            return team_metrics

        except Exception as e:
            logger.error(f"Failed to get team performance: {e}")
            return {}

    async def find_best_agent_for_interaction(
        self, interaction_data: Dict[str, Any]
    ) -> Optional[UUID]:
        """Find the best available agent for an interaction"""
        try:
            channel = interaction_data.get("channel")
            required_skills = interaction_data.get("skills", [])
            priority = interaction_data.get("priority", "medium")
            customer_language = interaction_data.get("customer_language")

            # Get available agents
            candidates = await self.get_available_agents(
                channel=channel,
                skills=required_skills,
                min_capacity=0.2 if priority == "high" else 0.1,
            )

            if not candidates:
                return None

            # Score each candidate
            scored_agents = []
            for agent in candidates:
                score = await self._calculate_agent_score(agent, interaction_data)
                scored_agents.append((agent.id, score))

            # Sort by score and return best match
            scored_agents.sort(key=lambda x: x[1], reverse=True)
            return scored_agents[0][0] if scored_agents else None

        except Exception as e:
            logger.error(f"Failed to find best agent: {e}")
            return None

    async def get_agent_performance(
        self, agent_id: UUID, period: str = "today"
    ) -> Dict[str, Any]:
        """Get detailed agent performance metrics"""
        try:
            agent = await self.get_agent(agent_id)
            metrics = self.metrics_cache.get(agent_id, AgentMetrics())

            if not agent:
                return {}

            return {
                "agent_id": agent_id,
                "agent_name": agent.full_name,
                "status": agent.status,
                "capacity_utilization": agent.capacity_utilization,
                "total_interactions": metrics.total_interactions,
                "active_interactions": metrics.active_interactions,
                "avg_response_time": metrics.avg_response_time,
                "avg_resolution_time": metrics.avg_resolution_time,
                "customer_satisfaction": metrics.customer_satisfaction,
                "first_contact_resolution": metrics.first_contact_resolution,
                "utilization_rate": metrics.utilization_rate,
                "online_time": str(metrics.online_time),
                "busy_time": str(metrics.busy_time),
                "idle_time": str(metrics.idle_time),
                "performance_rating": agent.performance_rating,
                "skills": agent.skills,
                "languages": agent.languages,
                "supported_channels": agent.channels,
            }

        except Exception as e:
            logger.error(f"Failed to get agent performance: {e}")
            return {}

    # Private helper methods

    def _is_agent_available(self, agent: AgentModel, min_capacity: float = 0.1) -> bool:
        """Check if agent is available for new interactions"""
        if agent.status in [AgentStatus.OFFLINE, AgentStatus.DO_NOT_DISTURB]:
            return False

        if agent.capacity_utilization >= 1.0:
            return False

        return (1.0 - agent.capacity_utilization) >= min_capacity

    def _agent_has_skills(self, agent: AgentModel, required_skills: List[str]) -> bool:
        """Check if agent has required skills"""
        agent_skills = [skill.get("skill_name", "") for skill in agent.skills]
        return all(skill in agent_skills for skill in required_skills)

    def _calculate_availability_score(self, agent: AgentModel) -> float:
        """Calculate agent availability score for prioritization"""
        base_score = 1.0 - agent.capacity_utilization

        # Bonus for better performance
        performance_bonus = agent.performance_rating / 10.0

        # Penalty for being busy
        status_penalty = 0.2 if agent.status == AgentStatus.BUSY else 0.0

        return max(0.0, base_score + performance_bonus - status_penalty)

    async def _calculate_agent_score(
        self, agent: AgentModel, interaction_data: Dict[str, Any]
    ) -> float:
        """Calculate agent suitability score for interaction"""
        try:
            score = 0.0

            # Base availability score (0-1)
            score += self._calculate_availability_score(agent)

            # Skill matching bonus (0-2)
            required_skills = interaction_data.get("skills", [])
            if required_skills:
                skill_score = self._calculate_skill_match_score(agent, required_skills)
                score += skill_score

            # Language matching bonus (0-1)
            customer_language = interaction_data.get("customer_language")
            if customer_language and customer_language in agent.languages:
                score += 1.0

            # Performance bonus (0-1)
            score += agent.performance_rating / 10.0

            # Priority handling bonus
            priority = interaction_data.get("priority", "medium")
            if priority == "high" and agent.capacity_utilization < 0.5:
                score += 0.5

            return score

        except Exception as e:
            logger.error(f"Failed to calculate agent score: {e}")
            return 0.0

    def _calculate_skill_match_score(
        self, agent: AgentModel, required_skills: List[str]
    ) -> float:
        """Calculate skill matching score"""
        if not required_skills:
            return 0.0

        total_score = 0.0
        matched_skills = 0

        for required_skill in required_skills:
            for skill_data in agent.skills:
                if skill_data.get("skill_name") == required_skill:
                    level = skill_data.get("level", "beginner")
                    skill_level = (
                        SkillLevel(level)
                        if level in SkillLevel
                        else SkillLevel.BEGINNER
                    )
                    total_score += self.skill_weights.get(skill_level, 1.0)
                    matched_skills += 1
                    break

        if matched_skills == 0:
            return 0.0

        # Normalize score (0-2 range)
        max_possible = len(required_skills) * self.skill_weights[SkillLevel.EXPERT]
        return min(2.0, (total_score / max_possible) * 2.0)

    async def _track_status_change(
        self, agent: AgentModel, old_status: AgentStatus, new_status: AgentStatus
    ):
        """Track agent status change for metrics"""
        try:
            metrics = self.metrics_cache.get(agent.id, AgentMetrics())

            # Update time tracking based on status
            now = datetime.utcnow()

            # This is a simplified implementation
            # In production, you'd track actual time differences
            if new_status == AgentStatus.ONLINE:
                metrics.online_time += timedelta(minutes=1)
            elif new_status == AgentStatus.BUSY:
                metrics.busy_time += timedelta(minutes=1)
            else:
                metrics.idle_time += timedelta(minutes=1)

            self.metrics_cache[agent.id] = metrics

        except Exception as e:
            logger.error(f"Failed to track status change: {e}")
