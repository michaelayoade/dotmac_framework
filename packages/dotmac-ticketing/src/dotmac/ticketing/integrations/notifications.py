"""
Integration with DotMac communications system for ticket notifications.
"""

import logging
from typing import Any, Optional

from ..core.models import Ticket, TicketComment, TicketStatus
from .templates import NotificationTemplateManager

logger = logging.getLogger(__name__)


class TicketNotificationManager:
    """Manages notifications for ticket events."""

    def __init__(self, communication_service=None, template_manager: Optional[NotificationTemplateManager] = None):
        """Initialize notification manager."""
        self.communication_service = communication_service
        self.template_manager = template_manager or NotificationTemplateManager()

    async def notify_ticket_created(
        self, ticket: Ticket, additional_context: dict[str, Any] | None = None
    ):
        """Send notification when ticket is created."""
        if not ticket.customer_email:
            logger.warning(f"No customer email for ticket {ticket.id}")
            return

        context = {
            "ticket": ticket,
            "ticket_number": ticket.ticket_number,
            "title": ticket.title,
            "description": ticket.description,
            "priority": ticket.priority.value,
            "category": ticket.category.value,
            "status": ticket.status.value,
            "created_at": ticket.created_at.isoformat(),
            **(additional_context or {}),
        }

        await self._send_notification(
            notification_type="ticket_created",
            recipient=ticket.customer_email,
            context=context,
        )

    async def notify_ticket_assigned(
        self,
        ticket: Ticket,
        assigned_to_name: str,
        assigned_team: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ):
        """Send notification when ticket is assigned."""
        if not ticket.customer_email:
            return

        context = {
            "ticket": ticket,
            "ticket_number": ticket.ticket_number,
            "title": ticket.title,
            "assigned_to": assigned_to_name,
            "assigned_team": assigned_team or "Support Team",
            "status": ticket.status.value,
            **(additional_context or {}),
        }

        await self._send_notification(
            notification_type="ticket_assigned",
            recipient=ticket.customer_email,
            context=context,
        )

        # Also notify the assigned person if available
        if ticket.assigned_to_id and hasattr(self, "_get_user_email"):
            assigned_email = await self._get_user_email(ticket.assigned_to_id)
            if assigned_email:
                await self._send_notification(
                    notification_type="ticket_assigned",
                    recipient=assigned_email,
                    context={**context, "is_assignee": True},
                )

    async def notify_ticket_updated(
        self,
        ticket: Ticket,
        old_status: TicketStatus,
        updated_by: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ):
        """Send notification when ticket is updated."""
        if not ticket.customer_email:
            return

        context = {
            "ticket": ticket,
            "ticket_number": ticket.ticket_number,
            "title": ticket.title,
            "old_status": old_status.value,
            "new_status": ticket.status.value,
            "updated_by": updated_by or "Support Team",
            "updated_at": ticket.updated_at.isoformat(),
            **(additional_context or {}),
        }

        await self._send_notification(
            notification_type="ticket_updated",
            recipient=ticket.customer_email,
            context=context,
        )

    async def notify_ticket_resolved(
        self,
        ticket: Ticket,
        resolution_comment: str | None = None,
        resolved_by: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ):
        """Send notification when ticket is resolved."""
        if not ticket.customer_email:
            return

        context = {
            "ticket": ticket,
            "ticket_number": ticket.ticket_number,
            "title": ticket.title,
            "resolution_comment": resolution_comment,
            "resolved_by": resolved_by or "Support Team",
            "resolved_at": ticket.resolved_at.isoformat()
            if ticket.resolved_at
            else None,
            **(additional_context or {}),
        }

        await self._send_notification(
            notification_type="ticket_resolved",
            recipient=ticket.customer_email,
            context=context,
        )

    async def notify_ticket_closed(
        self,
        ticket: Ticket,
        closing_comment: str | None = None,
        closed_by: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ):
        """Send notification when ticket is closed."""
        if not ticket.customer_email:
            return

        context = {
            "ticket": ticket,
            "ticket_number": ticket.ticket_number,
            "title": ticket.title,
            "closing_comment": closing_comment,
            "closed_by": closed_by or "Support Team",
            "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
            **(additional_context or {}),
        }

        await self._send_notification(
            notification_type="ticket_closed",
            recipient=ticket.customer_email,
            context=context,
        )

    async def notify_comment_added(
        self,
        ticket: Ticket,
        comment: TicketComment,
        additional_context: dict[str, Any] | None = None,
    ):
        """Send notification when comment is added."""
        # Don't notify for internal comments
        if comment.is_internal:
            return

        if not ticket.customer_email:
            return

        context = {
            "ticket": ticket,
            "ticket_number": ticket.ticket_number,
            "title": ticket.title,
            "comment": comment,
            "comment_content": comment.content,
            "comment_author": comment.author_name,
            "comment_date": comment.created_at.isoformat(),
            "is_solution": comment.is_solution,
            **(additional_context or {}),
        }

        await self._send_notification(
            notification_type="comment_added",
            recipient=ticket.customer_email,
            context=context,
        )

    async def notify_escalation(
        self,
        ticket: Ticket,
        escalation_reason: str,
        escalated_to: str,
        escalated_to_team: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ):
        """Send notification when ticket is escalated."""
        # Notify customer
        if ticket.customer_email:
            context = {
                "ticket": ticket,
                "ticket_number": ticket.ticket_number,
                "title": ticket.title,
                "escalation_reason": escalation_reason,
                "escalated_to": escalated_to,
                "escalated_to_team": escalated_to_team or "Senior Support",
                **(additional_context or {}),
            }

            await self._send_notification(
                notification_type="escalation_notification",
                recipient=ticket.customer_email,
                context=context,
            )

        # Notify the escalation team/person
        if hasattr(self, "_get_team_notifications"):
            team_emails = await self._get_team_notifications(escalated_to_team)
            for email in team_emails:
                await self._send_notification(
                    notification_type="escalation_notification",
                    recipient=email,
                    context={**context, "is_escalation_team": True},
                )

    async def notify_sla_warning(
        self, tickets: list[Ticket], additional_context: dict[str, Any] | None = None
    ):
        """Send SLA warning notifications for tickets approaching breach."""
        for ticket in tickets:
            if not ticket.customer_email:
                continue

            context = {
                "ticket": ticket,
                "ticket_number": ticket.ticket_number,
                "title": ticket.title,
                "sla_breach_time": ticket.sla_breach_time.isoformat()
                if ticket.sla_breach_time
                else None,
                "priority": ticket.priority.value,
                **(additional_context or {}),
            }

            await self._send_notification(
                notification_type="sla_warning",
                recipient=ticket.customer_email,
                context=context,
            )

    async def _send_notification(
        self,
        notification_type: str,
        recipient: str,
        context: dict[str, Any],
        channel: str = "email",
    ):
        """Send a notification using the communication service."""
        if not self.communication_service:
            logger.info(
                f"No communication service configured. "
                f"Would send {notification_type} to {recipient}"
            )
            return

        try:
            # Render subject and body using template manager
            subject = self.template_manager.render_notification(notification_type, context, "subject")
            body = self.template_manager.render_notification(notification_type, context, "body")
            html_body = self.template_manager.render_notification(notification_type, context, "html_body")
            
            if not subject or not body:
                logger.error(f"Failed to render template for notification type: {notification_type}")
                return

            # Use the communication service to send notification
            await self.communication_service.send_notification(
                recipient=recipient,
                subject=subject,
                template=notification_type,  # Template name for reference
                context={
                    **context,
                    "body": body,
                    "html_body": html_body,
                    "rendered_subject": subject,
                },
                channel=channel,
            )

            logger.info(
                f"Sent {notification_type} notification to {recipient} "
                f"for ticket {context.get('ticket_number')}"
            )

        except Exception as e:
            logger.error(
                f"Failed to send {notification_type} notification to {recipient}: {str(e)}"
            )

    async def _get_user_email(self, user_id: str) -> str | None:
        """Get user email by ID (to be implemented with user service integration)."""
        # This would integrate with user management service
        return None

    async def _get_team_notifications(self, team_name: str) -> list[str]:
        """Get notification emails for a team (to be implemented)."""
        # This would integrate with team/organization service
        return []
