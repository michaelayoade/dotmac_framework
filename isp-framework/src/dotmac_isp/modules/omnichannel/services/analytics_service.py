"""Analytics and reporting service."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from dotmac_isp.shared.exceptions import EntityNotFoundError, ValidationError

from ..schemas import OmnichannelDashboardStats
from .base_service import BaseOmnichannelService

logger = logging.getLogger(__name__)


class AnalyticsService(BaseOmnichannelService):
    """Service for omnichannel analytics and reporting."""

    async def get_dashboard_stats(
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> OmnichannelDashboardStats:
        """Get comprehensive dashboard statistics."""
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()

            logger.info(f"Generating dashboard stats from {date_from} to {date_to}")

            # Get basic interaction metrics
            interaction_stats = await self.repository.get_interaction_stats(
                date_from, date_to, self.tenant_id
            )

            # Get agent performance metrics
            agent_stats = await self.repository.get_agent_stats(
                date_from, date_to, self.tenant_id
            )

            # Get channel performance
            channel_stats = await self.repository.get_channel_stats(
                date_from, date_to, self.tenant_id
            )

            # Get customer satisfaction
            satisfaction_stats = await self.repository.get_satisfaction_stats(
                date_from, date_to, self.tenant_id
            )

            # Calculate derived metrics
            avg_response_time = await self._calculate_avg_response_time(
                date_from, date_to
            )
            avg_resolution_time = await self._calculate_avg_resolution_time(
                date_from, date_to
            )

            return OmnichannelDashboardStats(
                total_interactions=interaction_stats.get("total", 0),
                pending_interactions=interaction_stats.get("pending", 0),
                resolved_interactions=interaction_stats.get("resolved", 0),
                avg_response_time_minutes=avg_response_time,
                avg_resolution_time_hours=avg_resolution_time,
                customer_satisfaction_score=satisfaction_stats.get("avg_score", 0),
                active_agents=agent_stats.get("active", 0),
                total_agents=agent_stats.get("total", 0),
                agent_utilization_percentage=agent_stats.get("utilization", 0),
                channel_breakdown=channel_stats,
                period_start=date_from,
                period_end=date_to,
            )

        except Exception as e:
            logger.error(f"Error generating dashboard stats: {e}")
            raise

    async def get_agent_performance_report(
        self,
        agent_id: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get detailed agent performance report."""
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=7)
            if not date_to:
                date_to = datetime.utcnow()

            if agent_id:
                agents = [await self.repository.get_agent(agent_id)]
                if not agents[0]:
                    raise EntityNotFoundError(f"Agent not found: {agent_id}")
            else:
                agents = await self.repository.get_all_agents(self.tenant_id)

            report_data = []

            for agent in agents:
                if not agent:
                    continue

                # Get agent metrics
                metrics = await self.repository.get_agent_performance_metrics(
                    agent.id, date_from, date_to
                )

                # Get interaction breakdown
                interaction_breakdown = (
                    await self.repository.get_agent_interaction_breakdown(
                        agent.id, date_from, date_to
                    )
                )

                # Calculate performance scores
                performance_score = await self._calculate_agent_performance_score(
                    agent.id, date_from, date_to
                )

                report_data.append(
                    {
                        "agent_id": agent.id,
                        "agent_name": agent.display_name,
                        "team": agent.team.name if agent.team else None,
                        "interactions_handled": metrics.get("interactions_handled", 0),
                        "avg_response_time_minutes": metrics.get("avg_response_time", 0)
                        / 60,
                        "avg_resolution_time_hours": metrics.get(
                            "avg_resolution_time", 0
                        )
                        / 3600,
                        "customer_satisfaction": metrics.get("avg_satisfaction", 0),
                        "utilization_percentage": metrics.get("utilization", 0),
                        "performance_score": performance_score,
                        "interaction_breakdown": interaction_breakdown,
                        "status_distribution": await self._get_agent_status_distribution(
                            agent.id, date_from, date_to
                        ),
                    }
                )

            return {
                "period_start": date_from,
                "period_end": date_to,
                "agents": report_data,
                "summary": await self._calculate_team_summary(report_data),
            }

        except Exception as e:
            logger.error(f"Error generating agent performance report: {e}")
            raise

    async def get_channel_analytics(
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get channel performance analytics."""
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()

            # Get channel metrics
            channel_metrics = await self.repository.get_detailed_channel_stats(
                date_from, date_to, self.tenant_id
            )

            analytics = {}

            for channel, metrics in channel_metrics.items():
                analytics[channel] = {
                    "total_interactions": metrics.get("total", 0),
                    "resolved_interactions": metrics.get("resolved", 0),
                    "avg_response_time": metrics.get("avg_response_time", 0),
                    "avg_resolution_time": metrics.get("avg_resolution_time", 0),
                    "customer_satisfaction": metrics.get("avg_satisfaction", 0),
                    "resolution_rate": (
                        metrics.get("resolved", 0) / max(metrics.get("total", 1), 1)
                    )
                    * 100,
                    "trend": await self._calculate_channel_trend(
                        channel, date_from, date_to
                    ),
                }

            return {
                "period_start": date_from,
                "period_end": date_to,
                "channels": analytics,
                "top_performing_channel": max(
                    analytics.keys(),
                    key=lambda c: analytics[c]["customer_satisfaction"],
                    default=None,
                ),
            }

        except Exception as e:
            logger.error(f"Error generating channel analytics: {e}")
            raise

    async def get_customer_journey_analytics(
        self,
        customer_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get customer journey analytics."""
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=90)
            if not date_to:
                date_to = datetime.utcnow()

            # Get customer interactions
            interactions = await self.repository.get_customer_interactions(
                customer_id, date_from, date_to
            )

            # Analyze journey patterns
            journey_data = {
                "customer_id": customer_id,
                "period_start": date_from,
                "period_end": date_to,
                "total_interactions": len(interactions),
                "channels_used": list(set(i.channel_type for i in interactions)),
                "interaction_timeline": [
                    {
                        "date": i.created_at,
                        "channel": i.channel_type,
                        "type": i.interaction_type,
                        "status": i.status,
                        "resolution_time": i.resolution_time_seconds,
                    }
                    for i in sorted(interactions, key=lambda x: x.created_at)
                ],
                "satisfaction_trend": await self._get_customer_satisfaction_trend(
                    customer_id, date_from, date_to
                ),
                "preferred_channels": await self._identify_preferred_channels(
                    interactions
                ),
                "escalation_rate": (
                    sum(1 for i in interactions if i.is_escalated)
                    / len(interactions)
                    * 100
                    if interactions
                    else 0
                ),
            }

            return journey_data

        except Exception as e:
            logger.error(f"Error generating customer journey analytics: {e}")
            raise

    async def _calculate_avg_response_time(
        self, date_from: datetime, date_to: datetime
    ) -> float:
        """Calculate average response time in minutes."""
        result = await self.repository.get_avg_response_time(
            date_from, date_to, self.tenant_id
        )
        return result / 60 if result else 0

    async def _calculate_avg_resolution_time(
        self, date_from: datetime, date_to: datetime
    ) -> float:
        """Calculate average resolution time in hours."""
        result = await self.repository.get_avg_resolution_time(
            date_from, date_to, self.tenant_id
        )
        return result / 3600 if result else 0

    async def _calculate_agent_performance_score(
        self, agent_id: UUID, date_from: datetime, date_to: datetime
    ) -> float:
        """Calculate composite agent performance score."""
        metrics = await self.repository.get_agent_performance_metrics(
            agent_id, date_from, date_to
        )

        if not metrics:
            return 0

        # Weighted scoring (weights should be configurable)
        satisfaction_score = (metrics.get("avg_satisfaction", 0) / 5) * 40  # 40% weight
        efficiency_score = min(metrics.get("utilization", 0), 100) * 0.3  # 30% weight
        quality_score = (
            min(100 - metrics.get("escalation_rate", 0), 100) * 0.3
        )  # 30% weight

        return round(satisfaction_score + efficiency_score + quality_score, 2)

    async def _get_agent_status_distribution(
        self, agent_id: UUID, date_from: datetime, date_to: datetime
    ) -> Dict[str, float]:
        """Get agent status time distribution."""
        status_logs = await self.repository.get_agent_status_logs(
            agent_id, date_from, date_to
        )

        # Calculate time spent in each status
        status_times = {}
        total_time = (date_to - date_from).total_seconds()

        for status, duration in status_logs.items():
            status_times[status] = (
                (duration / total_time) * 100 if total_time > 0 else 0
            )

        return status_times

    async def _calculate_team_summary(self, agent_data: List[Dict]) -> Dict[str, Any]:
        """Calculate team-level summary metrics."""
        if not agent_data:
            return {}

        total_agents = len(agent_data)
        total_interactions = sum(a["interactions_handled"] for a in agent_data)
        avg_satisfaction = (
            sum(a["customer_satisfaction"] for a in agent_data) / total_agents
        )
        avg_performance = sum(a["performance_score"] for a in agent_data) / total_agents

        return {
            "total_agents": total_agents,
            "total_interactions": total_interactions,
            "avg_customer_satisfaction": round(avg_satisfaction, 2),
            "avg_performance_score": round(avg_performance, 2),
            "top_performer": max(agent_data, key=lambda a: a["performance_score"])[
                "agent_name"
            ],
            "team_utilization": sum(a["utilization_percentage"] for a in agent_data)
            / total_agents,
        }

    async def _calculate_channel_trend(
        self, channel: str, date_from: datetime, date_to: datetime
    ) -> str:
        """Calculate trend for channel performance."""
        # Compare with previous period
        period_length = date_to - date_from
        previous_period_start = date_from - period_length
        previous_period_end = date_from

        current_metrics = await self.repository.get_channel_metrics(
            channel, date_from, date_to, self.tenant_id
        )
        previous_metrics = await self.repository.get_channel_metrics(
            channel, previous_period_start, previous_period_end, self.tenant_id
        )

        current_score = current_metrics.get("avg_satisfaction", 0)
        previous_score = previous_metrics.get("avg_satisfaction", 0)

        if current_score > previous_score * 1.05:
            return "improving"
        elif current_score < previous_score * 0.95:
            return "declining"
        else:
            return "stable"

    async def _get_customer_satisfaction_trend(
        self, customer_id: UUID, date_from: datetime, date_to: datetime
    ) -> List[Dict]:
        """Get customer satisfaction trend over time."""
        satisfaction_data = await self.repository.get_customer_satisfaction_over_time(
            customer_id, date_from, date_to
        )

        return [
            {"date": record["date"], "satisfaction_score": record["score"]}
            for record in satisfaction_data
        ]

    async def _identify_preferred_channels(
        self, interactions: List[Any]
    ) -> Dict[str, int]:
        """Identify customer's preferred communication channels."""
        channel_usage = {}

        for interaction in interactions:
            channel = interaction.channel_type
            channel_usage[channel] = channel_usage.get(channel, 0) + 1

        # Sort by usage frequency
        return dict(sorted(channel_usage.items(), key=lambda x: x[1], reverse=True))
