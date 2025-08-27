"""Intelligent routing service."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID

from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
)

from ..models import CommunicationChannel, RoutingStrategy
from ..schemas import RoutingRuleCreate
from .base_service import BaseOmnichannelService

logger = logging.getLogger(__name__)


class RoutingService(BaseOmnichannelService):
    """Service for intelligent interaction routing."""

    async def create_routing_rule(self, rule_data: RoutingRuleCreate) -> UUID:
        """Create new routing rule."""
        try:
            logger.info(f"Creating routing rule: {rule_data.rule_name}")

            # Validate rule doesn't conflict with existing rules
            conflicts = await self._check_routing_conflicts(rule_data)
            if conflicts:
                raise BusinessRuleError(
                    f"Routing rule conflicts with existing rules: {conflicts}"
                )

            # Create routing rule
            rule = await self.repository.create_routing_rule(
                {
                    **rule_data.model_dump(),
                    "tenant_id": self.tenant_id,
                    "created_at": datetime.now(timezone.utc),
                    "is_active": True,
                }
            )

            logger.info(f"Created routing rule: {rule.id}")
            return rule.id

        except Exception as e:
            logger.error(f"Error creating routing rule: {e}")
            raise

    async def route_interaction(self, interaction_id: UUID) -> Dict[str, Any]:
        """Route interaction to appropriate agent/team."""
        try:
            logger.info(f"Routing interaction: {interaction_id}")

            # Get interaction details
            interaction = await self.repository.get_interaction(interaction_id)
            if not interaction:
                raise EntityNotFoundError(f"Interaction not found: {interaction_id}")

            # Get applicable routing rules
            rules = await self.repository.get_routing_rules(
                channel_type=interaction.channel_type,
                interaction_type=interaction.interaction_type,
                priority=interaction.priority,
                tenant_id=self.tenant_id,
            )

            routing_result = None

            # Apply rules in priority order
            for rule in sorted(rules, key=lambda r: r.priority):
                if await self._evaluate_rule_conditions(rule, interaction):
                    routing_result = await self._apply_routing_strategy(
                        rule, interaction
                    )
                    if routing_result:
                        break

            # Fallback routing if no rules match
            if not routing_result:
                routing_result = await self._apply_fallback_routing(interaction)

            # Update interaction with routing result
            if routing_result:
                await self.repository.update_interaction(
                    interaction_id,
                    {
                        "assigned_agent_id": routing_result.get("agent_id"),
                        "assigned_team_id": routing_result.get("team_id"),
                        "routing_rule_id": routing_result.get("rule_id"),
                        "routed_at": datetime.now(timezone.utc),
                    },
                )

            logger.info(f"Routed interaction: {interaction_id} -> {routing_result}")
            return routing_result or {}

        except Exception as e:
            logger.error(f"Error routing interaction: {e}")
            raise

    async def get_routing_analytics(
        self, date_from: datetime, date_to: datetime
    ) -> Dict[str, Any]:
        """Get routing performance analytics."""
        try:
            analytics = await self.repository.get_routing_analytics(
                date_from, date_to, self.tenant_id
            )

            return {
                "period_start": date_from,
                "period_end": date_to,
                "total_interactions": analytics.get("total_interactions", 0),
                "successfully_routed": analytics.get("successfully_routed", 0),
                "routing_success_rate": analytics.get("routing_success_rate", 0),
                "avg_routing_time": analytics.get("avg_routing_time_seconds", 0),
                "rule_performance": analytics.get("rule_performance", []),
                "fallback_usage": analytics.get("fallback_count", 0),
            }

        except Exception as e:
            logger.error(f"Error getting routing analytics: {e}")
            raise

    async def _check_routing_conflicts(self, rule_data: RoutingRuleCreate) -> List[str]:
        """Check for conflicts with existing routing rules."""
        conflicts = []

        existing_rules = await self.repository.get_routing_rules(
            channel_type=rule_data.channel_type,
            interaction_type=rule_data.interaction_type,
            tenant_id=self.tenant_id,
        )

        for rule in existing_rules:
            if (
                rule.priority == rule_data.priority
                and rule.is_active
                and rule.conditions == rule_data.conditions
            ):
                conflicts.append(
                    f"Rule '{rule.rule_name}' has same priority and conditions"
                )

        return conflicts

    async def _evaluate_rule_conditions(self, rule: Any, interaction: Any) -> bool:
        """Evaluate if routing rule conditions are met."""
        if not rule.conditions:
            return True

        # Evaluate each condition
        for condition_key, condition_value in rule.conditions.items():
            interaction_value = getattr(interaction, condition_key, None)

            if condition_key == "priority" and interaction.priority != condition_value:
                return False
            elif condition_key == "keywords" and not any(
                kw in (interaction.keywords or []) for kw in condition_value
            ):
                return False
            elif (
                condition_key == "customer_tier"
                and interaction.customer_tier != condition_value
            ):
                return False
            elif (
                condition_key == "language" and interaction.language != condition_value
            ):
                return False

        return True

    async def _apply_routing_strategy(
        self, rule: Any, interaction: Any
    ) -> Optional[Dict[str, Any]]:
        """Apply routing strategy from rule."""
        if rule.routing_strategy == RoutingStrategy.ROUND_ROBIN:
            return await self._route_round_robin(rule.team_id)
        elif rule.routing_strategy == RoutingStrategy.SKILL_BASED:
            return await self._route_skill_based(rule.required_skills, rule.team_id)
        elif rule.routing_strategy == RoutingStrategy.WORKLOAD_BASED:
            return await self._route_workload_based(rule.team_id)
        elif rule.routing_strategy == RoutingStrategy.VIP:
            return await self._route_vip(rule.team_id)

        return None

    async def _route_round_robin(
        self, team_id: Optional[UUID]
    ) -> Optional[Dict[str, Any]]:
        """Route using round-robin strategy."""
        agents = await self.repository.get_available_agents(team_id=team_id)
        if not agents:
            return None

        # Get agent with least recent assignment
        agent = min(agents, key=lambda a: a.last_assignment_at or datetime.min)

        # Update assignment timestamp
        await self.repository.update_agent(
            agent.id, {"last_assignment_at": datetime.now(timezone.utc)}
        )

        return {"agent_id": agent.id, "team_id": team_id, "strategy": "round_robin"}

    async def _route_skill_based(
        self, required_skills: List[str], team_id: Optional[UUID]
    ) -> Optional[Dict[str, Any]]:
        """Route based on agent skills."""
        agents = await self.repository.get_agents_with_skills(
            required_skills, team_id=team_id
        )
        if not agents:
            return None

        # Select agent with best skill match
        best_agent = max(
            agents, key=lambda a: len(set(a.skills) & set(required_skills))
        )

        return {
            "agent_id": best_agent.id,
            "team_id": team_id,
            "strategy": "skill_based",
            "matched_skills": list(set(best_agent.skills) & set(required_skills)),
        }

    async def _route_workload_based(
        self, team_id: Optional[UUID]
    ) -> Optional[Dict[str, Any]]:
        """Route based on current agent workload."""
        agents = await self.repository.get_available_agents(team_id=team_id)
        if not agents:
            return None

        # Get workloads
        agent_workloads = []
        for agent in agents:
            workload = await self.repository.get_agent_workload(agent.id)
            agent_workloads.append((agent, workload))

        # Select agent with lowest workload
        best_agent, _ = min(agent_workloads, key=lambda x: x[1])

        return {
            "agent_id": best_agent.id,
            "team_id": team_id,
            "strategy": "workload_based",
        }

    async def _route_vip(self, team_id: Optional[UUID]) -> Optional[Dict[str, Any]]:
        """Route VIP customers to senior agents."""
        senior_agents = await self.repository.get_senior_agents(team_id=team_id)
        if not senior_agents:
            return await self._route_round_robin(team_id)

        # Select available senior agent with least workload
        available_senior = [a for a in senior_agents if a.status == "AVAILABLE"]
        if not available_senior:
            return None

        best_agent = min(available_senior, key=lambda a: a.current_workload or 0)

        return {"agent_id": best_agent.id, "team_id": team_id, "strategy": "vip"}

    async def _apply_fallback_routing(
        self, interaction: Any
    ) -> Optional[Dict[str, Any]]:
        """Apply fallback routing when no rules match."""
        # Route to general team with round-robin
        default_team = await self.repository.get_default_team(self.tenant_id)
        if default_team:
            return await self._route_round_robin(default_team.id)

        # Last resort: any available agent
        agents = await self.repository.get_available_agents()
        if agents:
            return {"agent_id": agents[0].id, "strategy": "fallback"}

        return None
