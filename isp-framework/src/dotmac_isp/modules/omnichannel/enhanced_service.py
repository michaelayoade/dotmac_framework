"""Enhanced omnichannel service with full modular monolith integration."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, desc, func

from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
    DuplicateEntityError,
    ServiceError,
)

from .models_production import (
    RegisteredChannel,
    ChannelConfiguration,
    CustomerContact,
    ContactCommunicationChannel,
    ConversationThread,
    CommunicationInteraction,
    OmnichannelAgent,
    AgentTeam,
    RoutingRule,
    InteractionResponse,
    InteractionEscalation,
    InteractionStatus,
    InteractionType,
    AgentStatus,
)
from .cache import omnichannel_cache
from .integration_service import OmnichannelIntegrationService
from .plugin_service import ChannelPluginService
from .channel_plugins.base import ChannelMessage

logger = logging.getLogger(__name__)


class EnhancedOmnichannelService:
    """Enhanced omnichannel service with full monolith integration."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id
        self.cache = omnichannel_cache

        # Integration services
        self.integration_service = OmnichannelIntegrationService(db, tenant_id)
        self.plugin_service = ChannelPluginService(db, tenant_id)

    # ===== ENHANCED INTERACTION CREATION =====

    async def create_interaction_with_context(
        self, interaction_data: Dict[str, Any]
    ) -> CommunicationInteraction:
        """Create interaction with full context enrichment."""
        try:
            # 1. Validate and create basic interaction
            interaction = await self._create_base_interaction(interaction_data)

            # 2. Enrich with customer context
            context = await self.integration_service.enrich_interaction_context(
                str(interaction.id), interaction_data["customer_id"]
            )

            # 3. Update interaction with context-based priority
            if "priority_indicators" in context:
                priority_info = context["priority_indicators"]
                interaction.priority_level = priority_info.get("priority_level", 3)

                # Add priority context to internal notes
                if priority_info.get("urgent_flags"):
                    flags = ", ".join(priority_info["urgent_flags"])
                    interaction.internal_notes = f"Priority factors: {flags}"

            # 4. Calculate SLA based on customer type and priority
            sla_minutes = self._calculate_sla_time(context, interaction.priority_level)
            if sla_minutes:
                interaction.sla_due_time = datetime.utcnow() + timedelta(
                    minutes=sla_minutes
                )

            # 5. Create or link to conversation thread
            thread = await self._get_or_create_conversation_thread(interaction, context)
            if thread:
                interaction.conversation_thread_id = thread.id

            self.db.commit()

            # 6. Start routing process asynchronously
            from .tasks import process_interaction_routing

            process_interaction_routing.delay(self.tenant_id, str(interaction.id))

            # 7. Cache interaction for quick access
            self.cache.cache_interaction_context(
                self.tenant_id, str(interaction.id), context, ttl=3600
            )

            logger.info(f"Created enhanced interaction {interaction.id} with context")
            return interaction

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create enhanced interaction: {e}")
            raise ServiceError(f"Interaction creation failed: {str(e)}")

    async def _create_base_interaction(
        self, data: Dict[str, Any]
    ) -> CommunicationInteraction:
        """Create basic interaction record."""
        # Get contact and channel info
        contact = (
            self.db.query(CustomerContact)
            .filter(
                CustomerContact.customer_id == data["customer_id"],
                CustomerContact.tenant_id == self.tenant_id,
                CustomerContact.is_active == True,
            )
            .first()
        )

        if not contact:
            raise EntityNotFoundError(
                f"No active contact found for customer {data['customer_id']}"
            )

        # Get or create channel info
        channel_info = await self._get_or_create_channel_info(
            contact.id,
            data.get("channel_id", "email"),
            data.get("channel_address", contact.email_primary),
        )

        # Create interaction
        interaction = CommunicationInteraction(
            tenant_id=self.tenant_id,
            interaction_reference=data.get("reference")
            or f"INT-{uuid4().hex[:8].upper()}",
            contact_id=contact.id,
            channel_info_id=channel_info.id,
            interaction_type=InteractionType(data.get("type", "inbound")),
            status=InteractionStatus.PENDING,
            subject=data.get("subject"),
            content=data["content"],
            content_type=data.get("content_type", "text"),
            channel_message_id=data.get("channel_message_id"),
            channel_metadata=data.get("channel_metadata", {}),
            priority_level=data.get("priority_level", 3),
            interaction_start=datetime.utcnow(),
        )

        self.db.add(interaction)
        self.db.flush()  # Get ID without committing

        return interaction

    async def _get_or_create_channel_info(
        self, contact_id: str, channel_id: str, channel_address: str
    ) -> ContactCommunicationChannel:
        """Get or create channel information for contact."""
        # Get registered channel
        registered_channel = (
            self.db.query(RegisteredChannel)
            .filter(
                RegisteredChannel.tenant_id == self.tenant_id,
                RegisteredChannel.channel_id == channel_id,
                RegisteredChannel.is_active == True,
            )
            .first()
        )

        if not registered_channel:
            raise EntityNotFoundError(f"Channel {channel_id} not registered")

        # Check if channel info exists
        channel_info = (
            self.db.query(ContactCommunicationChannel)
            .filter(
                ContactCommunicationChannel.contact_id == contact_id,
                ContactCommunicationChannel.registered_channel_id
                == registered_channel.id,
                ContactCommunicationChannel.channel_address == channel_address,
            )
            .first()
        )

        if not channel_info:
            # Create new channel info
            channel_info = ContactCommunicationChannel(
                tenant_id=self.tenant_id,
                contact_id=contact_id,
                registered_channel_id=registered_channel.id,
                channel_address=channel_address,
                is_verified=False,  # Will be verified later
                is_active=True,
            )
            self.db.add(channel_info)
            self.db.flush()

        return channel_info

    def _calculate_sla_time(
        self, context: Dict[str, Any], priority_level: int
    ) -> Optional[int]:
        """Calculate SLA time in minutes based on context and priority."""
        try:
            # Base SLA times (in minutes)
            base_sla = {
                1: 15,  # High priority - 15 minutes
                2: 60,  # Medium-high - 1 hour
                3: 240,  # Normal - 4 hours
                4: 480,  # Low - 8 hours
                5: 1440,  # Very low - 24 hours
            }

            sla_minutes = base_sla.get(priority_level, 240)

            # Adjust based on customer type
            customer = context.get("customer", {})
            customer_type = customer.get("customer_type")

            if customer_type == "enterprise":
                sla_minutes = int(sla_minutes * 0.5)  # 50% faster SLA
            elif customer_type == "business":
                sla_minutes = int(sla_minutes * 0.75)  # 25% faster SLA

            # Adjust based on business hours (if outside hours, extend SLA)
            now = datetime.utcnow()
            if (
                now.weekday() >= 5 or now.hour < 8 or now.hour > 18
            ):  # Weekend or outside business hours
                sla_minutes = int(sla_minutes * 1.5)

            return sla_minutes

        except Exception as e:
            logger.error(f"Failed to calculate SLA time: {e}")
            return 240  # Default 4 hours

    async def _get_or_create_conversation_thread(
        self, interaction: CommunicationInteraction, context: Dict[str, Any]
    ) -> Optional[ConversationThread]:
        """Get existing or create new conversation thread."""
        try:
            # Look for existing active thread for this customer on same channel
            existing_thread = (
                self.db.query(ConversationThread)
                .filter(
                    ConversationThread.contact_id == interaction.contact_id,
                    ConversationThread.registered_channel_id
                    == interaction.channel_info.registered_channel_id,
                    ConversationThread.tenant_id == self.tenant_id,
                    ConversationThread.is_active == True,
                    ConversationThread.is_resolved == False,
                )
                .order_by(desc(ConversationThread.last_interaction_at))
                .first()
            )

            if existing_thread:
                # Update thread with new interaction
                existing_thread.last_interaction_at = datetime.utcnow()
                return existing_thread
            else:
                # Create new thread
                thread = ConversationThread(
                    tenant_id=self.tenant_id,
                    contact_id=interaction.contact_id,
                    registered_channel_id=interaction.channel_info.registered_channel_id,
                    thread_subject=interaction.subject or "Customer Inquiry",
                    thread_reference=f"THREAD-{uuid4().hex[:8].upper()}",
                    first_interaction_at=datetime.utcnow(),
                    last_interaction_at=datetime.utcnow(),
                    priority_level=interaction.priority_level,
                )

                self.db.add(thread)
                self.db.flush()
                return thread

        except Exception as e:
            logger.error(f"Failed to manage conversation thread: {e}")
            return None

    # ===== INTELLIGENT ROUTING =====

    async def route_interaction_with_context(self, interaction_id: str) -> bool:
        """Route interaction using context-aware logic."""
        try:
            interaction = (
                self.db.query(CommunicationInteraction)
                .filter(
                    CommunicationInteraction.id == interaction_id,
                    CommunicationInteraction.tenant_id == self.tenant_id,
                )
                .first()
            )

            if not interaction:
                raise EntityNotFoundError(f"Interaction {interaction_id} not found")

            # Get cached context
            context = self.cache.get_interaction_context(self.tenant_id, interaction_id)

            if not context:
                # Rebuild context
                customer_id = interaction.contact.customer_id
                context = await self.integration_service.enrich_interaction_context(
                    interaction_id, str(customer_id)
                )

            # Apply routing rules with context
            routing_success = await self._apply_contextual_routing_rules(
                interaction, context
            )

            if routing_success:
                # Send notification to assigned agent
                if interaction.assigned_agent_id:
                    await self.integration_service.send_interaction_notification(
                        interaction_id,
                        "assignment",
                        [str(interaction.assigned_agent_id)],
                        {
                            "customer_name": context.get("customer", {}).get(
                                "display_name", "Unknown"
                            ),
                            "channel": interaction.channel_info.registered_channel.channel_name,
                            "priority": interaction.priority_level,
                            "subject": interaction.subject,
                        },
                    )

                return True

            return False

        except Exception as e:
            logger.error(
                f"Contextual routing failed for interaction {interaction_id}: {e}"
            )
            return False

    async def _apply_contextual_routing_rules(
        self, interaction: CommunicationInteraction, context: Dict[str, Any]
    ) -> bool:
        """Apply routing rules with customer context."""
        try:
            # Get cached routing rules
            routing_rules = self.cache.get_routing_rules(self.tenant_id)

            if not routing_rules:
                # Load from database and cache
                rules_query = (
                    self.db.query(RoutingRule)
                    .filter(
                        RoutingRule.tenant_id == self.tenant_id,
                        RoutingRule.is_active == True,
                    )
                    .order_by(RoutingRule.priority.asc())
                )

                routing_rules = [
                    self._serialize_routing_rule(rule) for rule in rules_query.all()
                ]
                self.cache.cache_routing_rules(self.tenant_id, routing_rules)

            # Apply rules in priority order
            for rule in routing_rules:
                if await self._evaluate_routing_rule(rule, interaction, context):
                    assigned = await self._assign_based_on_rule(rule, interaction)
                    if assigned:
                        logger.info(
                            f"Interaction {interaction.id} routed via rule: {rule['name']}"
                        )
                        return True

            # Fallback to default routing
            return await self._apply_default_routing(interaction, context)

        except Exception as e:
            logger.error(f"Routing rules application failed: {e}")
            return False

    def _serialize_routing_rule(self, rule: RoutingRule) -> Dict[str, Any]:
        """Convert routing rule to dictionary for caching."""
        return {
            "id": str(rule.id),
            "name": rule.name,
            "priority": rule.priority,
            "channel_id": str(rule.channel_id) if rule.channel_id else None,
            "priority_condition": rule.priority_condition,
            "customer_tier_condition": rule.customer_tier_condition,
            "time_condition": rule.time_condition,
            "keyword_conditions": rule.keyword_conditions,
            "language_condition": rule.language_condition,
            "target_team_id": str(rule.target_team_id) if rule.target_team_id else None,
            "target_agent_id": (
                str(rule.target_agent_id) if rule.target_agent_id else None
            ),
            "priority_override": rule.priority_override,
            "sla_override_minutes": rule.sla_override_minutes,
        }

    async def _evaluate_routing_rule(
        self,
        rule: Dict[str, Any],
        interaction: CommunicationInteraction,
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate if routing rule matches interaction and context."""
        try:
            # Channel condition
            if rule["channel_id"]:
                if (
                    str(interaction.channel_info.registered_channel_id)
                    != rule["channel_id"]
                ):
                    return False

            # Priority condition
            if rule["priority_condition"]:
                if interaction.priority_level != rule["priority_condition"]:
                    return False

            # Customer tier condition
            if rule["customer_tier_condition"]:
                customer_type = context.get("customer", {}).get("customer_type")
                if customer_type != rule["customer_tier_condition"]:
                    return False

            # Time condition (business hours, weekends, etc.)
            if rule["time_condition"]:
                if not self._evaluate_time_condition(rule["time_condition"]):
                    return False

            # Keyword conditions
            if rule["keyword_conditions"]:
                content_lower = interaction.content.lower()
                subject_lower = (interaction.subject or "").lower()

                keyword_match = any(
                    keyword.lower() in content_lower or keyword.lower() in subject_lower
                    for keyword in rule["keyword_conditions"]
                )

                if not keyword_match:
                    return False

            # Language condition
            if rule["language_condition"]:
                customer_language = context.get("customer", {}).get(
                    "preferred_language", "en"
                )
                if customer_language != rule["language_condition"]:
                    return False

            return True

        except Exception as e:
            logger.error(f"Failed to evaluate routing rule: {e}")
            return False

    def _evaluate_time_condition(self, time_condition: Dict[str, Any]) -> bool:
        """Evaluate time-based routing conditions."""
        try:
            now = datetime.utcnow()

            # Business hours condition
            if "business_hours" in time_condition:
                business_hours = time_condition["business_hours"]
                start_hour = business_hours.get("start", 8)
                end_hour = business_hours.get("end", 18)

                if not (start_hour <= now.hour < end_hour):
                    return False

            # Weekend condition
            if "weekends_only" in time_condition:
                is_weekend = now.weekday() >= 5
                if time_condition["weekends_only"] and not is_weekend:
                    return False
                if not time_condition["weekends_only"] and is_weekend:
                    return False

            # Specific days
            if "allowed_days" in time_condition:
                allowed_days = time_condition["allowed_days"]  # [0-6, Mon=0]
                if now.weekday() not in allowed_days:
                    return False

            return True

        except Exception as e:
            logger.error(f"Time condition evaluation failed: {e}")
            return False

    async def _assign_based_on_rule(
        self, rule: Dict[str, Any], interaction: CommunicationInteraction
    ) -> bool:
        """Assign interaction based on routing rule."""
        try:
            # Direct agent assignment
            if rule["target_agent_id"]:
                agent = (
                    self.db.query(OmnichannelAgent)
                    .filter(
                        OmnichannelAgent.id == rule["target_agent_id"],
                        OmnichannelAgent.tenant_id == self.tenant_id,
                        OmnichannelAgent.status == AgentStatus.AVAILABLE,
                    )
                    .first()
                )

                if agent and agent.is_available:
                    interaction.assigned_agent_id = agent.id
                    agent.current_workload += 1

                    # Apply rule overrides
                    if rule["priority_override"]:
                        interaction.priority_level = rule["priority_override"]

                    if rule["sla_override_minutes"]:
                        interaction.sla_due_time = datetime.utcnow() + timedelta(
                            minutes=rule["sla_override_minutes"]
                        )

                    self.db.commit()
                    return True

            # Team assignment
            elif rule["target_team_id"]:
                available_agent = await self._get_next_available_agent_in_team(
                    rule["target_team_id"]
                )

                if available_agent:
                    interaction.assigned_agent_id = available_agent.id
                    interaction.assigned_team_id = rule["target_team_id"]
                    available_agent.current_workload += 1

                    # Apply rule overrides
                    if rule["priority_override"]:
                        interaction.priority_level = rule["priority_override"]

                    if rule["sla_override_minutes"]:
                        interaction.sla_due_time = datetime.utcnow() + timedelta(
                            minutes=rule["sla_override_minutes"]
                        )

                    self.db.commit()
                    return True

            return False

        except Exception as e:
            logger.error(f"Rule-based assignment failed: {e}")
            return False

    async def _get_next_available_agent_in_team(
        self, team_id: str
    ) -> Optional[OmnichannelAgent]:
        """Get next available agent in team using team's routing strategy."""
        try:
            team = (
                self.db.query(AgentTeam)
                .filter(AgentTeam.id == team_id, AgentTeam.tenant_id == self.tenant_id)
                .first()
            )

            if not team:
                return None

            # Get available agents in team
            available_agents = (
                self.db.query(OmnichannelAgent)
                .join(OmnichannelAgent.team_memberships)
                .filter(
                    AgentTeamMembership.team_id == team_id,
                    AgentTeamMembership.is_active == True,
                    OmnichannelAgent.status == AgentStatus.AVAILABLE,
                    OmnichannelAgent.current_workload
                    < OmnichannelAgent.max_concurrent_interactions,
                )
                .all()
            )

            if not available_agents:
                return None

            # Apply team's routing strategy
            if team.routing_strategy.value == "least_busy":
                return min(available_agents, key=lambda a: a.current_workload)
            elif team.routing_strategy.value == "round_robin":
                # Simple round robin - could be enhanced with persistent state
                return available_agents[hash(str(team_id)) % len(available_agents)]
            else:
                # Default to first available
                return available_agents[0]

        except Exception as e:
            logger.error(f"Failed to get next available agent in team {team_id}: {e}")
            return None

    async def _apply_default_routing(
        self, interaction: CommunicationInteraction, context: Dict[str, Any]
    ) -> bool:
        """Apply default routing when no rules match."""
        try:
            # Get any available agent
            available_agent = (
                self.db.query(OmnichannelAgent)
                .filter(
                    OmnichannelAgent.tenant_id == self.tenant_id,
                    OmnichannelAgent.status == AgentStatus.AVAILABLE,
                    OmnichannelAgent.current_workload
                    < OmnichannelAgent.max_concurrent_interactions,
                )
                .order_by(OmnichannelAgent.current_workload.asc())
                .first()
            )

            if available_agent:
                interaction.assigned_agent_id = available_agent.id
                available_agent.current_workload += 1
                self.db.commit()

                logger.info(f"Applied default routing to agent {available_agent.id}")
                return True

            logger.warning(f"No available agents for interaction {interaction.id}")
            return False

        except Exception as e:
            logger.error(f"Default routing failed: {e}")
            return False

    # ===== RESPONSE HANDLING =====

    async def send_response_via_channel(
        self,
        interaction_id: str,
        response_content: str,
        agent_id: str,
        is_internal: bool = False,
    ) -> bool:
        """Send response through appropriate channel plugin."""
        try:
            interaction = (
                self.db.query(CommunicationInteraction)
                .filter(
                    CommunicationInteraction.id == interaction_id,
                    CommunicationInteraction.tenant_id == self.tenant_id,
                )
                .first()
            )

            if not interaction:
                raise EntityNotFoundError(f"Interaction {interaction_id} not found")

            # Create response record
            response = InteractionResponse(
                tenant_id=self.tenant_id,
                interaction_id=interaction.id,
                agent_id=agent_id,
                content=response_content,
                is_internal=is_internal,
                delivery_status="pending",
            )
            self.db.add(response)
            self.db.flush()

            if not is_internal:
                # Send via channel plugin
                channel_info = interaction.channel_info
                channel_id = channel_info.registered_channel.channel_id

                message = ChannelMessage(
                    content=response_content,
                    sender_id="support@company.com",  # Configure per tenant
                    recipient_id=channel_info.channel_address,
                    metadata={
                        "interaction_id": str(interaction_id),
                        "response_id": str(response.id),
                    },
                )

                # Send asynchronously
                from .tasks import send_channel_message_async

                send_channel_message_async.delay(
                    self.tenant_id, channel_id, message.dict()
                )

            # Update interaction timestamps
            if not interaction.first_response_time:
                interaction.first_response_time = datetime.utcnow()

            self.db.commit()

            logger.info(f"Response sent for interaction {interaction_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to send response: {e}")
            return False

    # ===== DASHBOARD AND ANALYTICS =====

    async def get_enhanced_dashboard_stats(self) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics with caching."""
        try:
            # Check cache first
            cached_stats = self.cache.get_dashboard_stats(self.tenant_id)
            if cached_stats:
                return cached_stats

            # Calculate current stats
            now = datetime.utcnow()
            today_start = datetime.combine(now.date(), datetime.min.time())

            # Basic interaction stats
            total_interactions = (
                self.db.query(func.count(CommunicationInteraction.id))
                .filter(
                    CommunicationInteraction.tenant_id == self.tenant_id,
                    CommunicationInteraction.created_at >= today_start,
                )
                .scalar()
            )

            pending_interactions = (
                self.db.query(func.count(CommunicationInteraction.id))
                .filter(
                    CommunicationInteraction.tenant_id == self.tenant_id,
                    CommunicationInteraction.status == InteractionStatus.PENDING,
                )
                .scalar()
            )

            overdue_interactions = (
                self.db.query(func.count(CommunicationInteraction.id))
                .filter(
                    CommunicationInteraction.tenant_id == self.tenant_id,
                    CommunicationInteraction.sla_due_time < now,
                    CommunicationInteraction.status.in_(
                        [InteractionStatus.PENDING, InteractionStatus.IN_PROGRESS]
                    ),
                )
                .scalar()
            )

            # Agent stats
            total_agents = (
                self.db.query(func.count(OmnichannelAgent.id))
                .filter(OmnichannelAgent.tenant_id == self.tenant_id)
                .scalar()
            )

            available_agents = (
                self.db.query(func.count(OmnichannelAgent.id))
                .filter(
                    OmnichannelAgent.tenant_id == self.tenant_id,
                    OmnichannelAgent.status == AgentStatus.AVAILABLE,
                )
                .scalar()
            )

            # Channel stats
            channel_stats = {}
            registered_channels = (
                self.db.query(RegisteredChannel)
                .filter(
                    RegisteredChannel.tenant_id == self.tenant_id,
                    RegisteredChannel.is_active == True,
                )
                .all()
            )

            for channel in registered_channels:
                channel_interactions = (
                    self.db.query(func.count(CommunicationInteraction.id))
                    .join(ContactCommunicationChannel)
                    .filter(
                        ContactCommunicationChannel.registered_channel_id == channel.id,
                        CommunicationInteraction.created_at >= today_start,
                    )
                    .scalar()
                )

                channel_stats[channel.channel_name] = channel_interactions

            # Average response time (in minutes)
            avg_response_time = (
                self.db.query(
                    func.avg(
                        func.extract(
                            "epoch",
                            CommunicationInteraction.first_response_time
                            - CommunicationInteraction.interaction_start,
                        )
                        / 60
                    )
                )
                .filter(
                    CommunicationInteraction.tenant_id == self.tenant_id,
                    CommunicationInteraction.first_response_time.isnot(None),
                    CommunicationInteraction.created_at >= today_start,
                )
                .scalar()
            )

            # Customer satisfaction average
            avg_satisfaction = (
                self.db.query(func.avg(CommunicationInteraction.satisfaction_rating))
                .filter(
                    CommunicationInteraction.tenant_id == self.tenant_id,
                    CommunicationInteraction.satisfaction_rating.isnot(None),
                    CommunicationInteraction.created_at >= today_start,
                )
                .scalar()
            )

            stats = {
                "interactions": {
                    "total_today": total_interactions or 0,
                    "pending": pending_interactions or 0,
                    "overdue": overdue_interactions or 0,
                    "sla_breach_rate": (
                        (overdue_interactions / max(total_interactions, 1)) * 100
                        if overdue_interactions
                        else 0
                    ),
                },
                "agents": {
                    "total": total_agents or 0,
                    "available": available_agents or 0,
                    "utilization_rate": (
                        ((total_agents - available_agents) / max(total_agents, 1)) * 100
                        if total_agents
                        else 0
                    ),
                },
                "channels": channel_stats,
                "performance": {
                    "avg_response_time_minutes": round(avg_response_time or 0, 2),
                    "customer_satisfaction": (
                        round(avg_satisfaction or 0, 2) if avg_satisfaction else None
                    ),
                },
                "generated_at": datetime.utcnow().isoformat(),
            }

            # Cache for 5 minutes
            self.cache.cache_dashboard_stats(self.tenant_id, stats, ttl=300)

            return stats

        except Exception as e:
            logger.error(f"Failed to generate dashboard stats: {e}")
            return {"error": str(e), "generated_at": datetime.utcnow().isoformat()}

    # ===== HEALTH CHECK =====

    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of all omnichannel components."""
        health_status = {
            "service_status": "healthy",
            "components": {},
            "checked_at": datetime.utcnow().isoformat(),
        }

        try:
            # Database connectivity
            try:
                self.db.execute("SELECT 1").scalar()
                health_status["components"]["database"] = {"status": "healthy"}
            except Exception as e:
                health_status["components"]["database"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_status["service_status"] = "unhealthy"

            # Cache connectivity
            try:
                cache_stats = self.cache.get_cache_stats(self.tenant_id)
                if "error" in cache_stats:
                    health_status["components"]["cache"] = {
                        "status": "unhealthy",
                        "error": cache_stats["error"],
                    }
                    health_status["service_status"] = "degraded"
                else:
                    health_status["components"]["cache"] = {
                        "status": "healthy",
                        "entries": cache_stats["total_entries"],
                    }
            except Exception as e:
                health_status["components"]["cache"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_status["service_status"] = "degraded"

            # Plugin service health
            try:
                plugin_health = await self.plugin_service.health_check_all_channels()
                unhealthy_channels = [
                    ch
                    for ch, data in plugin_health.items()
                    if not data.get("is_healthy", False)
                ]

                if unhealthy_channels:
                    health_status["components"]["plugins"] = {
                        "status": "degraded",
                        "unhealthy_channels": unhealthy_channels,
                        "total_channels": len(plugin_health),
                    }
                    health_status["service_status"] = "degraded"
                else:
                    health_status["components"]["plugins"] = {
                        "status": "healthy",
                        "total_channels": len(plugin_health),
                    }
            except Exception as e:
                health_status["components"]["plugins"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_status["service_status"] = "degraded"

            # Integration services health
            integration_health = (
                await self.integration_service.integration_health_check()
            )
            if integration_health["overall_status"] != "healthy":
                health_status["service_status"] = "degraded"
            health_status["components"]["integrations"] = integration_health

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status["service_status"] = "unhealthy"
            health_status["error"] = str(e)

        return health_status
