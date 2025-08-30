"""Routing Engine for DotMac Omnichannel Service.

Intelligent routing system that directs customer interactions to the most
appropriate agents based on skills, availability, workload, and business rules.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Routing strategy types."""

    ROUND_ROBIN = "round_robin"
    LEAST_BUSY = "least_busy"
    SKILL_BASED = "skill_based"
    PRIORITY_BASED = "priority_based"
    GEOGRAPHIC = "geographic"
    LANGUAGE_BASED = "language_based"
    CUSTOM = "custom"


class ConditionOperator(str, Enum):
    """Condition operators for routing rules."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IN = "in"
    NOT_IN = "not_in"
    REGEX = "regex"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


@dataclass
class AgentSkill:
    """Agent skill definition."""

    skill_name: str
    proficiency_level: int  # 1-10 scale
    certified: bool = False
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentStatus:
    """Current agent status and availability."""

    agent_id: str
    status: str  # available, busy, away, offline
    current_interactions: int = 0
    max_interactions: int = 5
    skills: List[AgentSkill] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    timezone: str = "UTC"
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_available(self) -> bool:
        """Check if agent is available for new interactions."""
        return (
            self.status == "available"
            and self.current_interactions < self.max_interactions
        )

    def get_workload_ratio(self) -> float:
        """Get current workload as ratio (0.0 = free, 1.0 = at capacity)."""
        if self.max_interactions == 0:
            return 1.0
        return self.current_interactions / self.max_interactions

    def has_skill(self, skill_name: str, min_proficiency: int = 1) -> bool:
        """Check if agent has required skill."""
        for skill in self.skills:
            if (
                skill.skill_name.lower() == skill_name.lower()
                and skill.proficiency_level >= min_proficiency
            ):
                return True
        return False


class RoutingCondition(BaseModel):
    """Routing rule condition."""

    field: str  # Field to check (e.g., "channel", "priority", "customer.segment")
    operator: ConditionOperator
    value: Any  # Value to compare against
    case_sensitive: bool = False

    def evaluate(self, interaction_data: Dict[str, Any]) -> bool:
        """Evaluate condition against interaction data.

        Args:
            interaction_data: Interaction data to evaluate

        Returns:
            True if condition matches
        """
        try:
            # Get field value using dot notation
            field_value = self._get_field_value(interaction_data, self.field)

            if not self.case_sensitive and isinstance(field_value, str):
                field_value = field_value.lower()
                if isinstance(self.value, str):
                    compare_value = self.value.lower()
                else:
                    compare_value = self.value
            else:
                compare_value = self.value

            # Apply operator
            if self.operator == ConditionOperator.EQUALS:
                return field_value == compare_value
            elif self.operator == ConditionOperator.NOT_EQUALS:
                return field_value != compare_value
            elif self.operator == ConditionOperator.CONTAINS:
                return str(compare_value) in str(field_value)
            elif self.operator == ConditionOperator.NOT_CONTAINS:
                return str(compare_value) not in str(field_value)
            elif self.operator == ConditionOperator.GREATER_THAN:
                return field_value > compare_value
            elif self.operator == ConditionOperator.LESS_THAN:
                return field_value < compare_value
            elif self.operator == ConditionOperator.IN:
                return field_value in compare_value
            elif self.operator == ConditionOperator.NOT_IN:
                return field_value not in compare_value
            elif self.operator == ConditionOperator.EXISTS:
                return field_value is not None
            elif self.operator == ConditionOperator.NOT_EXISTS:
                return field_value is None
            elif self.operator == ConditionOperator.REGEX:
                import re

                pattern = re.compile(str(compare_value))
                return bool(pattern.search(str(field_value)))

            return False

        except Exception as e:
            logger.error(
                f"Error evaluating condition {self.field} {self.operator} {self.value}: {e}"
            )
            return False

    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get field value using dot notation."""
        keys = field_path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif hasattr(value, key):
                value = getattr(value, key)
            else:
                return None

        return value


class RoutingAction(BaseModel):
    """Routing rule action."""

    action_type: str  # route_to_agent, route_to_team, escalate, queue
    target_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

    # Routing preferences
    strategy: RoutingStrategy = RoutingStrategy.SKILL_BASED
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    min_skill_level: int = 1

    # Queue settings
    max_queue_time_minutes: Optional[int] = None
    escalate_after_minutes: Optional[int] = None


class RoutingRule(BaseModel):
    """Complete routing rule definition."""

    id: str = Field(default_factory=lambda: str(UUID.uuid4()))
    name: str
    description: str = ""
    tenant_id: str

    # Rule logic
    conditions: List[RoutingCondition]
    condition_logic: str = "AND"  # AND, OR
    action: RoutingAction

    # Rule metadata
    priority: int = 100  # Lower = higher priority
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Usage tracking
    usage_count: int = 0
    last_used: Optional[datetime] = None

    def evaluate(self, interaction_data: Dict[str, Any]) -> bool:
        """Evaluate if rule matches interaction.

        Args:
            interaction_data: Interaction data to evaluate

        Returns:
            True if rule matches
        """
        if not self.enabled or not self.conditions:
            return False

        results = [
            condition.evaluate(interaction_data) for condition in self.conditions
        ]

        if self.condition_logic == "OR":
            return any(results)
        else:  # AND
            return all(results)


@dataclass
class RoutingResult:
    """Result of routing operation."""

    success: bool
    agent_id: Optional[str] = None
    team_id: Optional[str] = None
    queue_id: Optional[str] = None
    rule_id: Optional[str] = None
    strategy_used: Optional[RoutingStrategy] = None
    reason: str = ""
    estimated_wait_minutes: Optional[int] = None
    alternative_agents: List[str] = field(default_factory=list)


class RoutingStrategy_ABC(ABC):
    """Abstract base class for routing strategies."""

    @abstractmethod
    async def route(
        self,
        interaction_data: Dict[str, Any],
        available_agents: List[AgentStatus],
        routing_context: Dict[str, Any],
    ) -> RoutingResult:
        """Execute routing strategy.

        Args:
            interaction_data: Interaction data
            available_agents: List of available agents
            routing_context: Additional routing context

        Returns:
            Routing result
        """
        pass


class RoundRobinStrategy(RoutingStrategy_ABC):
    """Round-robin routing strategy."""

    def __init__(self):
        self._last_agent_index = {}  # Per team tracking

    async def route(
        self,
        interaction_data: Dict[str, Any],
        available_agents: List[AgentStatus],
        routing_context: Dict[str, Any],
    ) -> RoutingResult:
        """Route using round-robin algorithm."""
        if not available_agents:
            return RoutingResult(success=False, reason="No available agents")

        team_id = routing_context.get("team_id", "default")

        # Get next agent in rotation
        last_index = self._last_agent_index.get(team_id, -1)
        next_index = (last_index + 1) % len(available_agents)
        selected_agent = available_agents[next_index]

        # Update rotation tracker
        self._last_agent_index[team_id] = next_index

        return RoutingResult(
            success=True,
            agent_id=selected_agent.agent_id,
            strategy_used=RoutingStrategy.ROUND_ROBIN,
            reason=f"Round-robin selection (index {next_index})",
        )


class LeastBusyStrategy(RoutingStrategy_ABC):
    """Least busy routing strategy."""

    async def route(
        self,
        interaction_data: Dict[str, Any],
        available_agents: List[AgentStatus],
        routing_context: Dict[str, Any],
    ) -> RoutingResult:
        """Route to least busy agent."""
        if not available_agents:
            return RoutingResult(success=False, reason="No available agents")

        # Sort by workload ratio (ascending)
        sorted_agents = sorted(available_agents, key=lambda a: a.get_workload_ratio())
        selected_agent = sorted_agents[0]

        return RoutingResult(
            success=True,
            agent_id=selected_agent.agent_id,
            strategy_used=RoutingStrategy.LEAST_BUSY,
            reason=f"Least busy agent (workload: {selected_agent.get_workload_ratio():.1%})",
            alternative_agents=[
                a.agent_id for a in sorted_agents[1:5]
            ],  # Top 5 alternatives
        )


class SkillBasedStrategy(RoutingStrategy_ABC):
    """Skill-based routing strategy."""

    async def route(
        self,
        interaction_data: Dict[str, Any],
        available_agents: List[AgentStatus],
        routing_context: Dict[str, Any],
    ) -> RoutingResult:
        """Route based on required skills."""
        if not available_agents:
            return RoutingResult(success=False, reason="No available agents")

        required_skills = routing_context.get("required_skills", [])
        preferred_skills = routing_context.get("preferred_skills", [])
        min_skill_level = routing_context.get("min_skill_level", 1)

        # Filter agents with required skills
        qualified_agents = []
        for agent in available_agents:
            if all(
                agent.has_skill(skill, min_skill_level) for skill in required_skills
            ):
                qualified_agents.append(agent)

        if not qualified_agents:
            return RoutingResult(
                success=False,
                reason=f"No agents with required skills: {required_skills}",
            )

        # Score agents based on preferred skills
        if preferred_skills:
            agent_scores = []
            for agent in qualified_agents:
                score = sum(
                    skill.proficiency_level
                    for skill in agent.skills
                    if skill.skill_name in preferred_skills
                )
                agent_scores.append((agent, score))

            # Sort by score (descending), then by workload (ascending)
            agent_scores.sort(key=lambda x: (-x[1], x[0].get_workload_ratio()))
            selected_agent = agent_scores[0][0]

            return RoutingResult(
                success=True,
                agent_id=selected_agent.agent_id,
                strategy_used=RoutingStrategy.SKILL_BASED,
                reason=f"Best skill match (score: {agent_scores[0][1]})",
                alternative_agents=[a[0].agent_id for a in agent_scores[1:5]],
            )

        # No preferred skills, use least busy qualified agent
        selected_agent = min(qualified_agents, key=lambda a: a.get_workload_ratio())

        return RoutingResult(
            success=True,
            agent_id=selected_agent.agent_id,
            strategy_used=RoutingStrategy.SKILL_BASED,
            reason="Qualified agent with lowest workload",
        )


class RoutingEngine:
    """Intelligent routing engine for customer interactions.

    Provides sophisticated routing capabilities including:
    - Rule-based routing with complex conditions
    - Multiple routing strategies (round-robin, skill-based, least-busy)
    - Agent availability and workload management
    - Queue management and escalation
    - Analytics and performance tracking
    """

    def __init__(
        self,
        agent_manager=None,
        team_manager=None,
        analytics_service=None,
        cache_service=None,
    ):
        """Initialize routing engine.

        Args:
            agent_manager: Agent management service
            team_manager: Team management service
            analytics_service: Analytics service
            cache_service: Caching service
        """
        self.agent_manager = agent_manager
        self.team_manager = team_manager
        self.analytics_service = analytics_service
        self.cache_service = cache_service

        # Routing rules storage
        self.routing_rules: Dict[str, List[RoutingRule]] = {}  # tenant_id -> rules

        # Strategy implementations
        self.strategies: Dict[RoutingStrategy, RoutingStrategy_ABC] = {
            RoutingStrategy.ROUND_ROBIN: RoundRobinStrategy(),
            RoutingStrategy.LEAST_BUSY: LeastBusyStrategy(),
            RoutingStrategy.SKILL_BASED: SkillBasedStrategy(),
        }

        # Custom strategy handlers
        self.custom_strategies: Dict[str, Callable] = {}

        logger.info("Routing Engine initialized")

    async def route_interaction(self, interaction) -> RoutingResult:
        """Route interaction to appropriate agent.

        Args:
            interaction: Interaction to route

        Returns:
            Routing result with agent assignment
        """
        interaction_data = self._interaction_to_dict(interaction)

        # Get applicable routing rules
        rules = await self._get_routing_rules(interaction.tenant_id)

        # Find matching rule
        matching_rule = None
        for rule in sorted(rules, key=lambda r: r.priority):
            if rule.evaluate(interaction_data):
                matching_rule = rule
                break

        if not matching_rule:
            # Use default routing
            return await self._default_routing(interaction_data)

        # Update rule usage
        matching_rule.usage_count += 1
        matching_rule.last_used = datetime.now(timezone.utc)

        # Execute rule action
        result = await self._execute_routing_action(
            matching_rule.action, interaction_data, matching_rule.id
        )

        # Track analytics
        if self.analytics_service:
            await self.analytics_service.track_routing_decision(
                interaction.id, result, matching_rule.id
            )

        logger.info(
            f"Routed interaction {interaction.id} using rule {matching_rule.name}: "
            f"agent={result.agent_id}, strategy={result.strategy_used}"
        )

        return result

    async def add_routing_rule(self, rule: RoutingRule):
        """Add routing rule.

        Args:
            rule: Routing rule to add
        """
        if rule.tenant_id not in self.routing_rules:
            self.routing_rules[rule.tenant_id] = []

        self.routing_rules[rule.tenant_id].append(rule)

        # Sort by priority
        self.routing_rules[rule.tenant_id].sort(key=lambda r: r.priority)

        logger.info(f"Added routing rule {rule.name} for tenant {rule.tenant_id}")

    async def remove_routing_rule(self, tenant_id: str, rule_id: str) -> bool:
        """Remove routing rule.

        Args:
            tenant_id: Tenant identifier
            rule_id: Rule identifier

        Returns:
            True if rule was removed
        """
        if tenant_id not in self.routing_rules:
            return False

        rules = self.routing_rules[tenant_id]
        original_count = len(rules)

        self.routing_rules[tenant_id] = [r for r in rules if r.id != rule_id]

        removed = len(self.routing_rules[tenant_id]) < original_count

        if removed:
            logger.info(f"Removed routing rule {rule_id} from tenant {tenant_id}")

        return removed

    async def update_routing_rule(self, rule: RoutingRule):
        """Update routing rule.

        Args:
            rule: Updated routing rule
        """
        if rule.tenant_id not in self.routing_rules:
            return

        rules = self.routing_rules[rule.tenant_id]

        for i, existing_rule in enumerate(rules):
            if existing_rule.id == rule.id:
                rule.updated_at = datetime.now(timezone.utc)
                rules[i] = rule

                # Re-sort by priority
                rules.sort(key=lambda r: r.priority)

                logger.info(f"Updated routing rule {rule.name}")
                break

    def register_custom_strategy(self, name: str, strategy_func: Callable):
        """Register custom routing strategy.

        Args:
            name: Strategy name
            strategy_func: Strategy function
        """
        self.custom_strategies[name] = strategy_func
        logger.info(f"Registered custom routing strategy: {name}")

    async def _get_routing_rules(self, tenant_id: str) -> List[RoutingRule]:
        """Get routing rules for tenant."""
        return self.routing_rules.get(tenant_id, [])

    async def _default_routing(self, interaction_data: Dict[str, Any]) -> RoutingResult:
        """Execute default routing when no rules match."""
        tenant_id = interaction_data.get("tenant_id")

        # Get available agents
        available_agents = []
        if self.agent_manager:
            available_agents = await self.agent_manager.get_available_agents(tenant_id)

        if not available_agents:
            return RoutingResult(
                success=False, reason="No available agents for default routing"
            )

        # Use least busy strategy as default
        strategy = self.strategies[RoutingStrategy.LEAST_BUSY]
        return await strategy.route(interaction_data, available_agents, {})

    async def _execute_routing_action(
        self, action: RoutingAction, interaction_data: Dict[str, Any], rule_id: str
    ) -> RoutingResult:
        """Execute routing action."""
        if action.action_type == "route_to_agent":
            return RoutingResult(
                success=True,
                agent_id=action.target_id,
                rule_id=rule_id,
                reason=f"Direct agent assignment: {action.target_id}",
            )

        elif action.action_type == "route_to_team":
            return await self._route_to_team(action, interaction_data, rule_id)

        elif action.action_type == "escalate":
            return await self._escalate_interaction(action, interaction_data, rule_id)

        elif action.action_type == "queue":
            return await self._queue_interaction(action, interaction_data, rule_id)

        else:
            return RoutingResult(
                success=False, reason=f"Unknown action type: {action.action_type}"
            )

    async def _route_to_team(
        self, action: RoutingAction, interaction_data: Dict[str, Any], rule_id: str
    ) -> RoutingResult:
        """Route to team using specified strategy."""
        team_id = action.target_id

        # Get available agents in team
        available_agents = []
        if self.agent_manager:
            available_agents = await self.agent_manager.get_team_available_agents(
                team_id
            )

        if not available_agents:
            return RoutingResult(
                success=False,
                team_id=team_id,
                rule_id=rule_id,
                reason=f"No available agents in team {team_id}",
            )

        # Apply routing strategy
        strategy = self.strategies.get(action.strategy)
        if not strategy:
            return RoutingResult(
                success=False,
                team_id=team_id,
                rule_id=rule_id,
                reason=f"Unknown routing strategy: {action.strategy}",
            )

        routing_context = {
            "team_id": team_id,
            "required_skills": action.required_skills,
            "preferred_skills": action.preferred_skills,
            "min_skill_level": action.min_skill_level,
        }

        result = await strategy.route(
            interaction_data, available_agents, routing_context
        )
        result.team_id = team_id
        result.rule_id = rule_id

        return result

    async def _escalate_interaction(
        self, action: RoutingAction, interaction_data: Dict[str, Any], rule_id: str
    ) -> RoutingResult:
        """Escalate interaction."""
        escalation_team = action.target_id or action.parameters.get("escalation_team")

        if escalation_team:
            # Route to escalation team
            escalation_action = RoutingAction(
                action_type="route_to_team",
                target_id=escalation_team,
                strategy=action.strategy,
                required_skills=action.required_skills,
            )
            result = await self._route_to_team(
                escalation_action, interaction_data, rule_id
            )
            result.reason = f"Escalated to team {escalation_team}: {result.reason}"
            return result

        return RoutingResult(
            success=False,
            rule_id=rule_id,
            reason="Escalation failed: no escalation team specified",
        )

    async def _queue_interaction(
        self, action: RoutingAction, interaction_data: Dict[str, Any], rule_id: str
    ) -> RoutingResult:
        """Queue interaction."""
        queue_id = action.target_id or "default"

        # Estimate wait time based on queue length and agent availability
        estimated_wait = await self._estimate_queue_wait_time(queue_id)

        return RoutingResult(
            success=True,
            queue_id=queue_id,
            rule_id=rule_id,
            reason=f"Queued in {queue_id}",
            estimated_wait_minutes=estimated_wait,
        )

    async def _estimate_queue_wait_time(self, queue_id: str) -> int:
        """Estimate queue wait time in minutes."""
        # Simplified estimation - would integrate with actual queue service
        return 15  # Default 15 minute estimate

    def _interaction_to_dict(self, interaction) -> Dict[str, Any]:
        """Convert interaction to dictionary for rule evaluation."""
        return {
            "id": interaction.id,
            "tenant_id": interaction.tenant_id,
            "customer_id": interaction.customer_id,
            "channel": str(interaction.channel),
            "status": str(interaction.status),
            "priority": str(interaction.priority),
            "content": interaction.content,
            "subject": interaction.subject,
            "tags": interaction.tags,
            "custom_fields": interaction.custom_fields,
            "context": interaction.context,
            "created_at": interaction.created_at,
            "age_minutes": (
                datetime.now(timezone.utc) - interaction.created_at
            ).total_seconds()
            / 60,
        }

    async def get_routing_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get routing statistics for tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Routing statistics
        """
        rules = await self._get_routing_rules(tenant_id)

        total_rules = len(rules)
        active_rules = len([r for r in rules if r.enabled])
        total_usage = sum(r.usage_count for r in rules)

        most_used_rule = max(rules, key=lambda r: r.usage_count) if rules else None

        return {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "total_rule_usage": total_usage,
            "most_used_rule": most_used_rule.name if most_used_rule else None,
            "strategies_available": list(self.strategies.keys()),
            "custom_strategies": list(self.custom_strategies.keys()),
        }
