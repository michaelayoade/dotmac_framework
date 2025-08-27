"""
Notification service for email, SMS, and push notifications.
Integrates with SendGrid, Twilio, and other communication providers.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from jinja2 import Template, Environment, DictLoader
import aiofiles

from core.exceptions import NotificationError, ValidationError
from core.logging import get_logger
from models.notifications import NotificationTemplate, NotificationLog
from schemas.notifications import ()
    NotificationType,
    NotificationPriority,
    EmailNotification,
    SMSNotification,
    PushNotification,
    NotificationStatus
, timezone)

# Import plugin system
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[4])

from shared.communication.plugin_system import global_plugin_registry, initialize_plugin_system

logger = get_logger(__name__)


class DeliveryChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    SLACK = "slack"
    WEBHOOK = "webhook"


class NotificationProvider(str, Enum):
    """Notification providers."""
    SENDGRID = "sendgrid"
    SMTP = "smtp"
    TWILIO = "twilio"
    FCM = "fcm"  # Firebase Cloud Messaging
    APNS = "apns"  # Apple Push Notification Service


class NotificationService:
    """Service for managing notifications across multiple channels."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.template_cache = {}
        self.jinja_env = Environment()
            loader=DictLoader({})
        self._plugin_system_initialized = False
    
    async def _ensure_plugin_system_ready(self):
        """Ensure plugin system is initialized."""
        if not self._plugin_system_initialized:
            try:
                await initialize_plugin_system("config/communication_plugins.yml")
                self._plugin_system_initialized = True
                logger.info("✅ Communication plugin system initialized")
            except Exception as e:
                logger.error(f"❌ Plugin system initialization failed: {e}")
                raise NotificationError(f"Communication system unavailable: {e}")
    
    async def send_notification(self,
        tenant_id): UUID,
        notification_type: NotificationType,
        recipients: List[str],
        channel: DeliveryChannel,
        template_id: Optional[UUID] = None,
        template_data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification via specified channel.
        
        Args:
            tenant_id: Tenant identifier
            notification_type: Type of notification
            recipients: List of recipient addresses/phone numbers
            channel: Delivery channel
            template_id: Optional notification template
            template_data: Data for template rendering
            priority: Notification priority
            user_id: User triggering the notification
            
        Returns:
            Dict containing notification status and delivery details
        """
        try:
            logger.info(f"Sending {channel} notification to {len(recipients)} recipients")
            
            # 0. Ensure plugin system is ready
            await self._ensure_plugin_system_ready()
            
            # 1. Load and render template
            rendered_content = await self._render_notification_template()
                template_id, notification_type, template_data or {}
            
            # 2. Create notification log entries
            notification_logs = await self._create_notification_logs()
                tenant_id, notification_type, recipients, channel, 
                rendered_content, priority, user_id
            
            # 3. Send notifications via plugin system - NO HARDCODED CHANNELS
            delivery_results = []
            
            # Use plugin system for all channels - zero hardcoding
            for i, recipient in enumerate(recipients):
                try:
                    # Send via plugin system
                    result = await global_plugin_registry.send_message()
                        channel_type=channel.value,
                        recipient=recipient,
                        content=rendered_content,
                        metadata={
                            "notification_id": str(notification_logs[i].id) if i < len(notification_logs) else None,
                            "tenant_id": str(tenant_id),
                            "notification_type": notification_type.value,
                            "priority": priority.value
                    delivery_results.append(result)
                    
                except Exception as e:
                    logger.error(f"Plugin system failed for {channel.value} to {recipient}: {e}")
                    delivery_results.append({)
                        "success": False,
                        "error": str(e),
                        "recipient": recipient
                    })
            
            # 4. Update notification logs with delivery status
            await self._update_notification_logs(notification_logs, delivery_results)
            
            # 5. Calculate overall success rate
            successful_deliveries = sum(1 for result in delivery_results if result.get("success", False)
            success_rate = (successful_deliveries / len(recipients) * 100 if recipients else 0
            
            return {
                "notification_id": str(notification_logs[0].id) if notification_logs else None,
                "tenant_id": str(tenant_id),
                "channel": channel,
                "total_recipients": len(recipients),
                "successful_deliveries": successful_deliveries,
                "success_rate": success_rate,
                "delivery_results": delivery_results,
                "sent_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Notification sending failed: {e}")
            raise NotificationError(f"Notification sending failed: {e}")
    
    async def send_bulk_notifications(self,
        tenant_id): UUID,
        notifications: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send multiple notifications in bulk with optimization.
        
        Args:
            tenant_id: Tenant identifier
            notifications: List of notification configurations
            user_id: User triggering the notifications
            
        Returns:
            Dict containing bulk sending results
        """
        try:
            logger.info(f"Sending {len(notifications)} bulk notifications for tenant {tenant_id}")
            
            # 0. Ensure plugin system is ready
            await self._ensure_plugin_system_ready()
            
            # Group notifications by channel for optimization
            grouped_notifications = {}
            for notification in notifications:
                channel = notification["channel"]
                if channel not in grouped_notifications:
                    grouped_notifications[channel] = []
                grouped_notifications[channel].append(notification)
            
            # Send notifications by channel
            all_results = []
            
            for channel, channel_notifications in grouped_notifications.items():
                # Use plugin system for ALL channels - zero hardcoding
                channel_results = []
                
                # Check if plugin supports bulk sending
                plugins = global_plugin_registry.get_plugins_by_channel_type(channel.value)
                bulk_capable = any(hasattr(plugin, 'send_bulk_message') for plugin in plugins)
                
                if bulk_capable and len(channel_notifications) > 1:
                    # Try bulk sending via plugin system
                    try:
                        bulk_result = await global_plugin_registry.send_bulk_message()
                            channel_type=channel.value,
                            notifications=channel_notifications
                        channel_results.append(bulk_result)
                    except Exception as e:
                        logger.warning(f"Bulk sending failed for {channel.value}, falling back to individual: {e}")
                        bulk_capable = False
                
                if not bulk_capable:
                    # Send individual notifications via plugin system
                    for notification in channel_notifications:
                        result = await self.send_notification()
                            tenant_id=tenant_id,
                            notification_type=notification["type"],
                            recipients=notification["recipients"],
                            channel=channel,
                            template_id=notification.get("template_id"),
                            template_data=notification.get("template_data"),
                            priority=notification.get("priority", NotificationPriority.NORMAL),
                            user_id=user_id
                        channel_results.append(result)
                
                all_results.extend(channel_results)
            
            # Calculate overall statistics
            total_recipients = sum(result["total_recipients"] for result in all_results)
            total_successful = sum(result["successful_deliveries"] for result in all_results)
            overall_success_rate = (total_successful / total_recipients) * 100 if total_recipients else 0
            
            return {
                "tenant_id": str(tenant_id),
                "total_notifications": len(notifications),
                "total_recipients": total_recipients,
                "total_successful": total_successful,
                "overall_success_rate": overall_success_rate,
                "results_by_channel": {
                    channel: [r for r in all_results if r.get("channel") == channel]
                    for channel in grouped_notifications.keys()
                },
                "sent_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Bulk notification sending failed: {e}")
            raise NotificationError(f"Bulk notification sending failed: {e}")
    
    async def create_notification_template(self,
        tenant_id): UUID,
        name: str,
        notification_type: NotificationType,
        channel: DeliveryChannel,
        subject_template: Optional[str],
        body_template: str,
        variables: List[str],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Create a new notification template.
        
        Args:
            tenant_id: Tenant identifier
            name: Template name
            notification_type: Type of notification
            channel: Delivery channel
            subject_template: Subject line template (for email)
            body_template: Message body template
            variables: List of template variables
            user_id: User creating the template
            
        Returns:
            Dict containing created template details
        """
        try:
            logger.info(f"Creating notification template {name} for tenant {tenant_id}")
            
            # Validate template syntax
            await self._validate_template_syntax(body_template, variables)
            
            if subject_template:
                await self._validate_template_syntax(subject_template, variables)
            
            # Create template
            template = NotificationTemplate()
                tenant_id=tenant_id,
                name=name,
                notification_type=notification_type,
                channel=channel,
                subject_template=subject_template,
                body_template=body_template,
                variables=variables,
                is_active=True,
                metadata={
                    "created_by": user_id,
                    "variable_count": len(variables)
                }
            
            self.db.add(template)
            await self.db.commit()
            await self.db.refresh(template)
            
            # Clear template cache
            self.template_cache.clear()
            
            return {
                "template_id": str(template.id),
                "tenant_id": str(tenant_id),
                "name": name,
                "notification_type": notification_type,
                "channel": channel,
                "variables": variables,
                "created_at": template.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Template creation failed: {e}")
            raise NotificationError(f"Template creation failed: {e}")
    
    async def get_notification_history(self,
        tenant_id): UUID,
        notification_type: Optional[NotificationType] = None,
        channel: Optional[DeliveryChannel] = None,
        status: Optional[NotificationStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get notification history for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            notification_type: Optional filter by notification type
            channel: Optional filter by channel
            status: Optional filter by status
            limit: Maximum number of records
            offset: Number of records to skip
            
        Returns:
            Dict containing notification history
        """
        try:
            # Build query filters
            filters = [NotificationLog.tenant_id == tenant_id]
            
            if notification_type:
                filters.append(NotificationLog.notification_type == notification_type)
            
            if channel:
                filters.append(NotificationLog.channel == channel)
            
            if status:
                filters.append(NotificationLog.status == status)
            
            # Execute query
            result = await self.db.execute()
                select(NotificationLog)
                .where(*filters)
                .order_by(NotificationLog.created_at.desc()
                .limit(limit)
                .offset(offset)
            notifications = result.scalars().all()
            
            # Format response
            notification_list = []
            for notification in notifications:
                notification_list.append({)
                    "notification_id": str(notification.id),
                    "type": notification.notification_type,
                    "channel": notification.channel,
                    "recipient": notification.recipient,
                    "status": notification.status,
                    "subject": notification.subject,
                    "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
                    "delivered_at": notification.delivered_at.isoformat() if notification.delivered_at else None,
                    "error_message": notification.error_message,
                    "metadata": notification.metadata
                })
            
            return {
                "tenant_id": str(tenant_id),
                "total_records": len(notification_list),
                "limit": limit,
                "offset": offset,
                "notifications": notification_list
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification history: {e}")
            raise NotificationError(f"Failed to get notification history: {e}")
    
    async def get_notification_statistics(self,
        tenant_id): UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get notification statistics for a tenant within date range.
        
        Args:
            tenant_id: Tenant identifier
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dict containing notification statistics
        """
        try:
            logger.info(f"Getting notification statistics for tenant {tenant_id}")
            
            # Query notifications within date range
            result = await self.db.execute()
                select(NotificationLog).where()
                    NotificationLog.tenant_id == tenant_id,
                    NotificationLog.created_at >= start_date,
                    NotificationLog.created_at <= end_date
            notifications = result.scalars().all()
            
            # Calculate statistics
            stats = {
                "total_notifications": len(notifications),
                "by_channel": {},
                "by_type": {},
                "by_status": {},
                "delivery_rates": {},
                "response_times": {}
            }
            
            # Group by channel
            for notification in notifications:
                channel = notification.channel
                if channel not in stats["by_channel"]:
                    stats["by_channel"][channel] = 0
                stats["by_channel"][channel] += 1
            
            # Group by type
            for notification in notifications:
                notif_type = notification.notification_type
                if notif_type not in stats["by_type"]:
                    stats["by_type"][notif_type] = 0
                stats["by_type"][notif_type] += 1
            
            # Group by status
            for notification in notifications:
                status = notification.status
                if status not in stats["by_status"]:
                    stats["by_status"][status] = 0
                stats["by_status"][status] += 1
            
            # Calculate delivery rates by channel
            for channel in stats["by_channel"]:
                channel_notifications = [n for n in notifications if n.channel == channel]
                delivered = len([n for n in channel_notifications if n.status == NotificationStatus.DELIVERED])
                total = len(channel_notifications)
                stats["delivery_rates"][channel] = (delivered / total) * 100 if total > 0 else 0
            
            # Calculate average response times
            for channel in stats["by_channel"]:
                channel_notifications = [n for n in notifications if n.channel == channel and n.sent_at and n.delivered_at]
                if channel_notifications:
                    response_times = [(n.delivered_at - n.sent_at).total_seconds() for n in channel_notifications]
                    stats["response_times"][channel] = sum(response_times) / len(response_times)
                else:
                    stats["response_times"][channel] = 0
            
            return {
                "tenant_id": str(tenant_id),
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "statistics": stats,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification statistics: {e}")
            raise NotificationError(f"Failed to get notification statistics: {e}")
    
    # Private methods
    
    async def _render_notification_template(self,
        template_id): Optional[UUID],
        notification_type: NotificationType,
        template_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Render notification template with provided data."""
        if template_id:
            # Load custom template
            template = await self._get_notification_template(template_id)
            if not template:
                raise ValidationError(f"Template {template_id} not found")
            
            subject_template = template.subject_template
            body_template = template.body_template
        else:
            # Use default template
            subject_template, body_template = await self._get_default_template(notification_type)
        
        # Render templates
        rendered_content = {}
        
        if subject_template:
            subject_jinja = Template(subject_template)
            rendered_content["subject"] = subject_jinja.render(**template_data)
        
        body_jinja = Template(body_template)
        rendered_content["body"] = body_jinja.render(**template_data)
        
        return rendered_content
    
    async def _get_notification_template(self, template_id: UUID) -> Optional[NotificationTemplate]:
        """Get notification template by ID."""
        if template_id in self.template_cache:
            return self.template_cache[template_id]
        
        result = await self.db.execute()
            select(NotificationTemplate).where()
                NotificationTemplate.id == template_id,
                NotificationTemplate.is_active == True
        template = result.scalar_one_or_none()
        
        if template:
            self.template_cache[template_id] = template
        
        return template
    
    async def _get_default_template(self, notification_type: NotificationType) -> tuple[Optional[str], str]:
        """Get default template for notification type."""
        templates = {
            NotificationType.WELCOME: (
                "Welcome to {{ company_name }}!",
                "Hello {{ user_name }},\n\nWelcome to {{ company_name }}! We're excited to have you on board.\n\nBest regards,\nThe {{ company_name }} Team"
            ),
            NotificationType.PASSWORD_RESET: (
                "Reset Your Password",
                "Hello {{ user_name }},\n\nPlease click the following link to reset your password:\n{{ reset_link }}\n\nThis link will expire in 24 hours.\n\nBest regards,\nThe {{ company_name }} Team"
            ),
            NotificationType.BILLING_REMINDER: (
                "Billing Reminder",
                "Hello {{ user_name }},\n\nThis is a reminder that your payment of ${{ amount }} is due on {{ due_date }}.\n\nPlease log in to your account to make a payment.\n\nThank you,\nThe {{ company_name }} Team"
            ),
            NotificationType.SYSTEM_ALERT: (
                "System Alert: {{ alert_type }}",
                "Alert: {{ alert_message }}\n\nTime: {{ timestamp }}\nSeverity: {{ severity }}\n\nPlease take appropriate action."
            ),
            NotificationType.MAINTENANCE_NOTICE: (
                "Scheduled Maintenance Notice",
                "Hello {{ user_name }},\n\nWe will be performing scheduled maintenance on {{ maintenance_date }} from {{ start_time }} to {{ end_time }}.\n\nDuring this time, {{ affected_services }} may be unavailable.\n\nWe apologize for any inconvenience.\n\nBest regards,\nThe {{ company_name }} Team"
            }
        }
        
        return templates.get(notification_type, (None, "{{ message }}"}
    
    async def _create_notification_logs(self,
        tenant_id): UUID,
        notification_type: NotificationType,
        recipients: List[str],
        channel: DeliveryChannel,
        content: Dict[str, str],
        priority: NotificationPriority,
        user_id: Optional[str]
    ) -> List[NotificationLog]:
        """Create notification log entries."""
        logs = []
        
        for recipient in recipients:
            log = NotificationLog(}
                tenant_id=tenant_id,
                notification_type=notification_type,
                channel=channel,
                recipient=recipient,
                subject=content.get("subject"),
                body=content["body"],
                status=NotificationStatus.PENDING,
                priority=priority,
                metadata={
                    "triggered_by": user_id,
                    "template_variables": list(content.keys(}
                }
            }
            
            self.db.add(log}
            logs.append(log}
        
        await self.db.commit(}
        
        for log in logs:
            await self.db.refresh(log}
        
        return logs
    
    async def _send_email_notifications(self,
        recipients): List[str],
        content: Dict[str, str],
        notification_logs: List[NotificationLog]
    ) -> List[Dict[str, Any]]:
        """Send email notifications."""
        results = []
        
        for i, recipient in enumerate(recipients):
            try:
                # Simulate email sending
                # In real implementation, this would use SendGrid or SMTP
                await asyncio.sleep(0.1)  # Simulate sending delay
                
                # Update log
                log = notification_logs[i]
                log.status = NotificationStatus.SENT
                log.sent_at = datetime.now(timezone.utc}
                
                # Simulate delivery confirmation
                await asyncio.sleep(0.5}
                log.status = NotificationStatus.DELIVERED
                log.delivered_at = datetime.now(timezone.utc}
                
                results.append({}
                    "recipient": recipient,
                    "success": True,
                    "message_id": f"email-{log.id.hex[:16]}",
                    "sent_at": log.sent_at.isoformat(),
                    "delivered_at": log.delivered_at.isoformat(}
                }}
                
            except Exception as e:
                # Update log with error
                log = notification_logs[i]
                log.status = NotificationStatus.FAILED
                log.error_message = str(e}
                
                results.append({}
                    "recipient": recipient,
                    "success": False,
                    "error": str(e}
                }}
        
        await self.db.commit(}
        return results
    
    async def _send_sms_notifications(self,
        recipients): List[str],
        content: Dict[str, str],
        notification_logs: List[NotificationLog]
    ) -> List[Dict[str, Any]]:
        """Send SMS notifications."""
        results = []
        
        for i, recipient in enumerate(recipients):
            try:
                # Simulate SMS sending via Twilio
                await asyncio.sleep(0.1}
                
                log = notification_logs[i]
                log.status = NotificationStatus.SENT
                log.sent_at = datetime.now(timezone.utc}
                
                # Simulate delivery
                await asyncio.sleep(0.3}
                log.status = NotificationStatus.DELIVERED
                log.delivered_at = datetime.now(timezone.utc}
                
                results.append({}
                    "recipient": recipient,
                    "success": True,
                    "message_id": f"sms-{log.id.hex[:16]}",
                    "sent_at": log.sent_at.isoformat(),
                    "delivered_at": log.delivered_at.isoformat(}
                }}
                
            except Exception as e:
                log = notification_logs[i]
                log.status = NotificationStatus.FAILED
                log.error_message = str(e}
                
                results.append({}
                    "recipient": recipient,
                    "success": False,
                    "error": str(e}
                }}
        
        await self.db.commit(}
        return results
    
    async def _send_push_notifications(self,
        recipients): List[str],
        content: Dict[str, str],
        notification_logs: List[NotificationLog]
    ) -> List[Dict[str, Any]]:
        """Send push notifications."""
        results = []
        
        for i, recipient in enumerate(recipients):
            try:
                # Simulate push notification sending
                await asyncio.sleep(0.05}
                
                log = notification_logs[i]
                log.status = NotificationStatus.SENT
                log.sent_at = datetime.now(timezone.utc}
                
                # Push notifications are typically delivered immediately
                log.status = NotificationStatus.DELIVERED
                log.delivered_at = datetime.now(timezone.utc}
                
                results.append({}
                    "recipient": recipient,
                    "success": True,
                    "message_id": f"push-{log.id.hex[:16]}",
                    "sent_at": log.sent_at.isoformat(),
                    "delivered_at": log.delivered_at.isoformat(}
                }}
                
            except Exception as e:
                log = notification_logs[i]
                log.status = NotificationStatus.FAILED
                log.error_message = str(e}
                
                results.append({}
                    "recipient": recipient,
                    "success": False,
                    "error": str(e}
                }}
        
        await self.db.commit(}
        return results
    
    async def _send_slack_notifications(self,
        recipients): List[str],
        content: Dict[str, str],
        notification_logs: List[NotificationLog]
    ) -> List[Dict[str, Any]]:
        """Send Slack notifications."""
        results = []
        
        for i, recipient in enumerate(recipients):
            try:
                # Simulate Slack webhook
                await asyncio.sleep(0.2}
                
                log = notification_logs[i]
                log.status = NotificationStatus.SENT
                log.sent_at = datetime.now(timezone.utc}
                log.status = NotificationStatus.DELIVERED
                log.delivered_at = datetime.now(timezone.utc}
                
                results.append({}
                    "recipient": recipient,
                    "success": True,
                    "message_id": f"slack-{log.id.hex[:16]}",
                    "sent_at": log.sent_at.isoformat(),
                    "delivered_at": log.delivered_at.isoformat(}
                }}
                
            except Exception as e:
                log = notification_logs[i]
                log.status = NotificationStatus.FAILED
                log.error_message = str(e}
                
                results.append({}
                    "recipient": recipient,
                    "success": False,
                    "error": str(e}
                }}
        
        await self.db.commit(}
        return results
    
    async def _send_webhook_notifications(self,
        recipients): List[str],
        content: Dict[str, str],
        notification_logs: List[NotificationLog]
    ) -> List[Dict[str, Any]]:
        """Send webhook notifications."""
        results = []
        
        for i, recipient in enumerate(recipients):
            try:
                # Simulate webhook POST
                await asyncio.sleep(0.3}
                
                log = notification_logs[i]
                log.status = NotificationStatus.SENT
                log.sent_at = datetime.now(timezone.utc}
                log.status = NotificationStatus.DELIVERED
                log.delivered_at = datetime.now(timezone.utc}
                
                results.append({}
                    "recipient": recipient,
                    "success": True,
                    "message_id": f"webhook-{log.id.hex[:16]}",
                    "sent_at": log.sent_at.isoformat(),
                    "delivered_at": log.delivered_at.isoformat(}
                }}
                
            except Exception as e:
                log = notification_logs[i]
                log.status = NotificationStatus.FAILED
                log.error_message = str(e}
                
                results.append({}
                    "recipient": recipient,
                    "success": False,
                    "error": str(e}
                }}
        
        await self.db.commit(}
        return results
    
    async def _send_bulk_emails(self,
        tenant_id): UUID,
        notifications: List[Dict[str, Any]],
        user_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Send bulk emails with optimization."""
        # Group by template for batch processing
        template_groups = {}
        for notification in notifications:
            template_key = (notification.get("template_id"), notification["type"])
            if template_key not in template_groups:
                template_groups[template_key] = []
            template_groups[template_key].append(notification}
        
        all_results = []
        
        for template_key, group_notifications in template_groups.items():
            # Process each template group
            for notification in group_notifications:
                result = await self.send_notification(}
                    tenant_id=tenant_id,
                    notification_type=notification["type"],
                    recipients=notification["recipients"],
                    channel=DeliveryChannel.EMAIL,
                    template_id=notification.get("template_id"),
                    template_data=notification.get("template_data"),
                    priority=notification.get("priority", NotificationPriority.NORMAL),
                    user_id=user_id
                }
                all_results.append(result}
        
        return all_results
    
    async def _send_bulk_sms(self,
        tenant_id): UUID,
        notifications: List[Dict[str, Any]],
        user_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Send bulk SMS with optimization."""
        all_results = []
        
        # SMS can be sent in batches more efficiently
        for notification in notifications:
            result = await self.send_notification(}
                tenant_id=tenant_id,
                notification_type=notification["type"],
                recipients=notification["recipients"],
                channel=DeliveryChannel.SMS,
                template_id=notification.get("template_id"),
                template_data=notification.get("template_data"),
                priority=notification.get("priority", NotificationPriority.NORMAL),
                user_id=user_id
            }
            all_results.append(result}
        
        return all_results
    
    async def _update_notification_logs(self,
        notification_logs): List[NotificationLog],
        delivery_results: List[Dict[str, Any]]
    ):
        """Update notification logs with delivery results."""
        for i, result in enumerate(delivery_results):
            if i < len(notification_logs):
                log = notification_logs[i]
                if result.get("success"):
                    log.status = NotificationStatus.DELIVERED
                    log.delivered_at = datetime.now(timezone.utc}
                    log.provider_message_id = result.get("message_id"}
                else:
                    log.status = NotificationStatus.FAILED
                    log.error_message = result.get("error"}
        
        await self.db.commit(}
    
    async def _validate_template_syntax(self, template: str, variables: List[str]):
        """Validate Jinja2 template syntax."""
        try:
            jinja_template = Template(template}
            # Test render with dummy data
            test_data = {var: f"test_{var}" for var in variables}
            jinja_template.render(**test_data}
        except Exception as e:
            raise ValidationError(f"Invalid template syntax: {e}"}