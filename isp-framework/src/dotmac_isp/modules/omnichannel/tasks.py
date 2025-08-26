"""Omnichannel background tasks using existing Celery infrastructure."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID

from dotmac_isp.core.celery_app import celery_app
from dotmac_isp.core.database import get_db
from dotmac_isp.shared.exceptions import EntityNotFoundError, ValidationError

logger = logging.getLogger(__name__)


# ===== PLUGIN MESSAGE SENDING TASKS =====


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_channel_message_async(
    self, tenant_id: str, channel_id: str, message_data: Dict[str, Any]
):
    """Send message through channel plugin asynchronously."""
    try:
        from dotmac_isp.modules.omnichannel.plugin_service import ChannelPluginService
        from dotmac_isp.modules.omnichannel.channel_plugins.base import ChannelMessage

        # Get database session
        db = next(get_db())
        try:
            service = ChannelPluginService(db, tenant_id)

            # Create channel message
            message = ChannelMessage(**message_data)

            # Send message
            result = service.send_message(channel_id, message)

            if result and result.get("success"):
                logger.info(
                    f"Message sent successfully via {channel_id}: {result.get('message_id')}"
                )
                return result
            else:
                logger.error(f"Message sending failed via {channel_id}: {result}")
                raise Exception(
                    f"Message sending failed: {result.get('error', 'Unknown error')}"
                )

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Channel message task failed: {exc}")
        if self.request.retries < self.max_retries:
            # Exponential backoff
            countdown = 60 * (2**self.request.retries)
            raise self.retry(countdown=countdown, exc=exc)
        else:
            # Final failure - log and update interaction status
            update_interaction_delivery_failure.delay(
                message_data.get("interaction_id"), str(exc)
            )
            raise


@celery_app.task
def process_interaction_routing(tenant_id: str, interaction_id: str):
    """Process interaction routing in background."""
    try:
        # ARCHITECTURE IMPROVEMENT: Use decomposed services instead of monolithic service
        from dotmac_isp.modules.omnichannel.services import OmnichannelOrchestrator as OmnichannelService

        # Get database session
        db = next(get_db())
        try:
            service = OmnichannelService(db, tenant_id)

            # Route the interaction (remove await - not needed in Celery task)
            success = service.route_interaction(interaction_id)

            if success:
                logger.info(f"Interaction {interaction_id} routed successfully")
                return {"success": True, "interaction_id": interaction_id}
            else:
                logger.warning(
                    f"Interaction {interaction_id} routing failed - no available agents"
                )
                # Schedule retry in 5 minutes
                process_interaction_routing.apply_async(
                    args=[tenant_id, interaction_id], countdown=300  # 5 minutes
                )
                return {"success": False, "retry_scheduled": True}

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Interaction routing task failed: {exc}")
        raise


@celery_app.task
def update_interaction_delivery_failure(interaction_id: str, error_message: str):
    """Update interaction when message delivery fails."""
    try:
        from dotmac_isp.modules.omnichannel.models_production import (
            CommunicationInteraction,
            InteractionStatus,
        )
        from sqlalchemy.orm import Session

        db = next(get_db())
        try:
            interaction = (
                db.query(CommunicationInteraction)
                .filter(CommunicationInteraction.id == interaction_id)
                .first()
            )

            if interaction:
                interaction.status = InteractionStatus.FAILED
                interaction.internal_notes = f"Message delivery failed: {error_message}"
                db.commit()
                logger.info(f"Updated interaction {interaction_id} status to FAILED")

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Failed to update interaction delivery status: {exc}")


# ===== SLA MONITORING TASKS =====


@celery_app.task
def monitor_sla_breaches():
    """Monitor and handle SLA breaches across all tenants."""
    try:
        from dotmac_isp.modules.omnichannel.models_production import (
            CommunicationInteraction,
            InteractionStatus,
        )
        from sqlalchemy.orm import Session

        db = next(get_db())
        try:
            # Find overdue interactions
            overdue_interactions = (
                db.query(CommunicationInteraction)
                .filter(
                    CommunicationInteraction.sla_due_time <= datetime.now(timezone.utc),
                    CommunicationInteraction.status.in_(
                        [InteractionStatus.PENDING, InteractionStatus.IN_PROGRESS]
                    ),
                    CommunicationInteraction.is_sla_breached == False,
                )
                .all()
            )

            breach_count = 0
            for interaction in overdue_interactions:
                # Mark as SLA breached
                interaction.is_sla_breached = True

                # Trigger escalation
                escalate_interaction.delay(
                    interaction.tenant_id,
                    str(interaction.id),
                    "TIME_BASED",
                    "SLA breach - interaction overdue",
                )
                breach_count += 1

            if breach_count > 0:
                db.commit()
                logger.warning(f"Processed {breach_count} SLA breaches")

            return {"processed": breach_count}

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"SLA monitoring task failed: {exc}")
        raise


@celery_app.task
def escalate_interaction(
    tenant_id: str, interaction_id: str, trigger_type: str, reason: str
):
    """Escalate an interaction."""
    try:
        # ARCHITECTURE IMPROVEMENT: Use decomposed services instead of monolithic service
        from dotmac_isp.modules.omnichannel.services import OmnichannelOrchestrator as OmnichannelService

        db = next(get_db())
        try:
            service = OmnichannelService(db, tenant_id)

            escalation_data = {"trigger_type": trigger_type, "trigger_reason": reason}

            escalation = service.create_escalation(interaction_id, escalation_data)

            if escalation:
                logger.info(f"Escalation created for interaction {interaction_id}")

                # Send notification to management
                send_escalation_notification.delay(
                    tenant_id, str(escalation.id), trigger_type, reason
                )

                return {"success": True, "escalation_id": str(escalation.id)}
            else:
                raise Exception("Failed to create escalation")

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Escalation task failed: {exc}")
        raise


# ===== NOTIFICATION TASKS =====


@celery_app.task
def send_escalation_notification(
    tenant_id: str, escalation_id: str, trigger_type: str, reason: str
):
    """Send notification about escalation."""
    try:
        # Integrate with existing notification system
        from dotmac_isp.modules.notifications.tasks import send_notification

        notification_data = {
            "type": "escalation_alert",
            "tenant_id": tenant_id,
            "data": {
                "escalation_id": escalation_id,
                "trigger_type": trigger_type,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "channels": ["email", "slack"],  # Use existing notification channels
            "priority": "high",
        }

        # Use existing notification task
        send_notification.delay(notification_data)

        logger.info(f"Escalation notification sent for {escalation_id}")

    except Exception as exc:
        logger.error(f"Escalation notification task failed: {exc}")


@celery_app.task
def send_agent_assignment_notification(
    tenant_id: str, agent_id: str, interaction_id: str
):
    """Notify agent about new interaction assignment."""
    try:
        from dotmac_isp.modules.notifications.tasks import send_notification

        notification_data = {
            "type": "interaction_assigned",
            "tenant_id": tenant_id,
            "recipient_id": agent_id,
            "data": {
                "interaction_id": interaction_id,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            },
            "channels": ["push", "email"],
            "priority": "normal",
        }

        send_notification.delay(notification_data)

    except Exception as exc:
        logger.error(f"Agent assignment notification failed: {exc}")


# ===== ANALYTICS TASKS =====


@celery_app.task
def update_agent_performance_metrics(
    tenant_id: str, agent_id: str, metric_date: str = None
):
    """Update agent performance metrics (daily aggregation)."""
    try:
        from dotmac_isp.modules.omnichannel.models_production import (
            OmnichannelAgent,
            CommunicationInteraction,
            AgentPerformanceMetric,
            InteractionStatus,
        )
        from sqlalchemy import func

        if not metric_date:
            metric_date = datetime.now(timezone.utc).date()
        else:
            metric_date = datetime.fromisoformat(metric_date).date()

        db = next(get_db())
        try:
            # Calculate daily metrics
            start_of_day = datetime.combine(metric_date, datetime.min.time())
            end_of_day = datetime.combine(metric_date, datetime.max.time())

            # Query interaction metrics
            interaction_stats = (
                db.query(
                    func.count(CommunicationInteraction.id).label("total"),
                    func.count(CommunicationInteraction.id)
                    .filter(
                        CommunicationInteraction.status == InteractionStatus.COMPLETED
                    )
                    .label("resolved"),
                    func.avg(
                        func.extract(
                            "epoch",
                            CommunicationInteraction.first_response_time
                            - CommunicationInteraction.interaction_start,
                        )
                        / 60
                    )
                    .filter(CommunicationInteraction.first_response_time.isnot(None))
                    .label("avg_response_minutes"),
                    func.avg(
                        func.extract(
                            "epoch",
                            CommunicationInteraction.resolution_time
                            - CommunicationInteraction.interaction_start,
                        )
                        / 60
                    )
                    .filter(CommunicationInteraction.resolution_time.isnot(None))
                    .label("avg_resolution_minutes"),
                    func.avg(CommunicationInteraction.satisfaction_rating)
                    .filter(CommunicationInteraction.satisfaction_rating.isnot(None))
                    .label("avg_satisfaction"),
                )
                .filter(
                    CommunicationInteraction.assigned_agent_id == agent_id,
                    CommunicationInteraction.created_at >= start_of_day,
                    CommunicationInteraction.created_at <= end_of_day,
                )
                .first()
            )

            # Create or update performance metric
            metric = (
                db.query(AgentPerformanceMetric)
                .filter(
                    AgentPerformanceMetric.tenant_id == tenant_id,
                    AgentPerformanceMetric.agent_id == agent_id,
                    func.date(AgentPerformanceMetric.metric_date) == metric_date,
                )
                .first()
            )

            if not metric:
                metric = AgentPerformanceMetric(
                    tenant_id=tenant_id, agent_id=agent_id, metric_date=start_of_day
                )
                db.add(metric)

            # Update metrics
            metric.total_interactions = interaction_stats.total or 0
            metric.interactions_resolved = interaction_stats.resolved or 0
            metric.average_response_time_minutes = (
                interaction_stats.avg_response_minutes or 0.0
            )
            metric.average_resolution_time_minutes = (
                interaction_stats.avg_resolution_minutes or 0.0
            )
            metric.customer_satisfaction_average = (
                interaction_stats.avg_satisfaction or 0.0
            )

            db.commit()

            logger.info(
                f"Updated performance metrics for agent {agent_id} on {metric_date}"
            )

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Agent performance metrics task failed: {exc}")
        raise


@celery_app.task
def update_channel_analytics(tenant_id: str, channel_id: str, metric_date: str = None):
    """Update channel analytics (daily aggregation)."""
    try:
        from dotmac_isp.modules.omnichannel.models_production import (
            RegisteredChannel,
            CommunicationInteraction,
            ChannelAnalytics,
            InteractionType,
        )
        from sqlalchemy import func

        if not metric_date:
            metric_date = datetime.now(timezone.utc).date()
        else:
            metric_date = datetime.fromisoformat(metric_date).date()

        db = next(get_db())
        try:
            start_of_day = datetime.combine(metric_date, datetime.min.time())
            end_of_day = datetime.combine(metric_date, datetime.max.time())

            # Get registered channel
            channel = (
                db.query(RegisteredChannel)
                .filter(
                    RegisteredChannel.tenant_id == tenant_id,
                    RegisteredChannel.channel_id == channel_id,
                )
                .first()
            )

            if not channel:
                raise EntityNotFoundError(f"Channel {channel_id} not found")

            # Calculate analytics
            analytics_stats = (
                db.query(
                    func.count(CommunicationInteraction.id).label("total"),
                    func.count(CommunicationInteraction.id)
                    .filter(
                        CommunicationInteraction.interaction_type
                        == InteractionType.INBOUND
                    )
                    .label("inbound"),
                    func.count(CommunicationInteraction.id)
                    .filter(
                        CommunicationInteraction.interaction_type
                        == InteractionType.OUTBOUND
                    )
                    .label("outbound"),
                    func.avg(
                        func.extract(
                            "epoch",
                            CommunicationInteraction.first_response_time
                            - CommunicationInteraction.interaction_start,
                        )
                        / 60
                    ).label("avg_response_minutes"),
                    func.avg(CommunicationInteraction.satisfaction_rating)
                    .filter(CommunicationInteraction.satisfaction_rating.isnot(None))
                    .label("avg_satisfaction"),
                )
                .join(CommunicationInteraction.channel_info)
                .filter(
                    ContactCommunicationChannel.registered_channel_id == channel.id,
                    CommunicationInteraction.created_at >= start_of_day,
                    CommunicationInteraction.created_at <= end_of_day,
                )
                .first()
            )

            # Create or update analytics
            analytics = (
                db.query(ChannelAnalytics)
                .filter(
                    ChannelAnalytics.tenant_id == tenant_id,
                    ChannelAnalytics.registered_channel_id == channel.id,
                    func.date(ChannelAnalytics.metric_date) == metric_date,
                )
                .first()
            )

            if not analytics:
                analytics = ChannelAnalytics(
                    tenant_id=tenant_id,
                    registered_channel_id=channel.id,
                    metric_date=start_of_day,
                )
                db.add(analytics)

            # Update analytics
            analytics.total_interactions = analytics_stats.total or 0
            analytics.inbound_interactions = analytics_stats.inbound or 0
            analytics.outbound_interactions = analytics_stats.outbound or 0
            analytics.average_response_time_minutes = (
                analytics_stats.avg_response_minutes or 0.0
            )
            analytics.customer_satisfaction_average = (
                analytics_stats.avg_satisfaction or 0.0
            )

            db.commit()

            logger.info(f"Updated analytics for channel {channel_id} on {metric_date}")

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Channel analytics task failed: {exc}")
        raise


# ===== PLUGIN HEALTH MONITORING TASKS =====


@celery_app.task
def monitor_plugin_health():
    """Monitor health of all channel plugins across tenants."""
    try:
        from dotmac_isp.modules.omnichannel.models_production import (
            ChannelConfiguration,
        )

        db = next(get_db())
        try:
            # Get all enabled channel configurations
            configs = (
                db.query(ChannelConfiguration)
                .filter(ChannelConfiguration.is_enabled == True)
                .all()
            )

            health_checks = 0
            for config in configs:
                # Schedule individual health checks
                check_plugin_health.delay(config.tenant_id, str(config.channel_id))
                health_checks += 1

            logger.info(f"Scheduled {health_checks} plugin health checks")
            return {"scheduled": health_checks}

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Plugin health monitoring task failed: {exc}")
        raise


@celery_app.task
def check_plugin_health(tenant_id: str, channel_id: str):
    """Check health of specific plugin."""
    try:
        from dotmac_isp.modules.omnichannel.plugin_service import ChannelPluginService

        db = next(get_db())
        try:
            service = ChannelPluginService(db, tenant_id)

            # Perform health check
            health_results = service.health_check_all_channels()

            channel_health = health_results.get(channel_id)
            if channel_health:
                logger.info(
                    f"Plugin {channel_id} health check: {channel_health['is_healthy']}"
                )

                if not channel_health["is_healthy"]:
                    # Send alert for unhealthy plugin
                    send_plugin_health_alert.delay(
                        tenant_id,
                        channel_id,
                        channel_health.get("error_message", "Unknown error"),
                    )

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Plugin health check failed for {channel_id}: {exc}")


@celery_app.task
def send_plugin_health_alert(tenant_id: str, channel_id: str, error_message: str):
    """Send alert when plugin health check fails."""
    try:
        from dotmac_isp.modules.notifications.tasks import send_notification

        notification_data = {
            "type": "plugin_health_alert",
            "tenant_id": tenant_id,
            "data": {
                "channel_id": channel_id,
                "error_message": error_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "channels": ["email", "slack"],
            "priority": "high",
        }

        send_notification.delay(notification_data)

    except Exception as exc:
        logger.error(f"Plugin health alert failed: {exc}")


# ===== CONVERSATION MANAGEMENT TASKS =====


@celery_app.task
def close_inactive_conversations():
    """Close conversations that have been inactive for too long."""
    try:
        from dotmac_isp.modules.omnichannel.models_production import ConversationThread

        # Define inactivity threshold (e.g., 7 days)
        inactivity_threshold = datetime.now(timezone.utc) - timedelta(days=7)

        db = next(get_db())
        try:
            inactive_threads = (
                db.query(ConversationThread)
                .filter(
                    ConversationThread.is_active == True,
                    ConversationThread.is_resolved == False,
                    ConversationThread.last_interaction_at <= inactivity_threshold,
                )
                .all()
            )

            closed_count = 0
            for thread in inactive_threads:
                thread.is_active = False
                thread.is_resolved = True
                thread.context_summary = (
                    f"Auto-closed due to inactivity after {inactivity_threshold}"
                )
                closed_count += 1

            if closed_count > 0:
                db.commit()
                logger.info(f"Auto-closed {closed_count} inactive conversations")

            return {"closed": closed_count}

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Conversation cleanup task failed: {exc}")
        raise


# ===== PERIODIC TASK SCHEDULING =====

# Schedule periodic tasks using Celery Beat (when available)
if hasattr(celery_app.conf, "beat_schedule"):
    celery_app.conf.beat_schedule.update(
        {
            "monitor-sla-breaches": {
                "task": "dotmac_isp.modules.omnichannel.tasks.monitor_sla_breaches",
                "schedule": 60.0,  # Every minute
            },
            "monitor-plugin-health": {
                "task": "dotmac_isp.modules.omnichannel.tasks.monitor_plugin_health",
                "schedule": 300.0,  # Every 5 minutes
            },
            "close-inactive-conversations": {
                "task": "dotmac_isp.modules.omnichannel.tasks.close_inactive_conversations",
                "schedule": 3600.0,  # Every hour
            },
        }
    )
