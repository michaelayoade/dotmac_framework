"""
Background tasks for notification operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import UUID

from celery import current_task
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from ...core.config import settings
from ...services.monitoring_service import MonitoringService
from ...workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Create async database session for workers
engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, max_retries=3)
def send_email_notification(self, notification_id: str, channel_config: Dict[str, Any], alert_data: Dict[str, Any]):
    """Send email notification."""
    import asyncio
    
    async def _send_email():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                notification_uuid = UUID(notification_id)
                
                # Update notification status
                await service.notification_repo.update_status(
                    notification_uuid, "sending", "email_worker"
                )
                
                # Extract email configuration
                to_addresses = channel_config.get("to", [])
                if isinstance(to_addresses, str):
                    to_addresses = [to_addresses]
                
                smtp_server = channel_config.get("smtp_server")
                smtp_port = channel_config.get("smtp_port", 587)
                username = channel_config.get("username")
                password = channel_config.get("password")
                use_tls = channel_config.get("use_tls", True)
                
                # Create email content
                subject = f"Alert: {alert_data['message']}"
                body = self._create_email_body(alert_data)
                
                # TODO: Implement actual email sending
                # For now, simulate email sending
                await asyncio.sleep(1)
                
                # Simulate success/failure
                if "test_fail" not in alert_data.get("labels", {}):
                    # Success
                    await service.notification_repo.update(
                        notification_uuid,
                        {
                            "status": "delivered",
                            "delivered_at": datetime.utcnow()
                        },
                        "email_worker"
                    )
                    
                    logger.info(f"Email notification sent successfully: {notification_id}")
                    return {"status": "delivered", "notification_id": notification_id}
                else:
                    # Simulate failure
                    raise Exception("SMTP server connection failed")
                
            except Exception as e:
                # Mark as failed
                await service.notification_repo.update(
                    UUID(notification_id),
                    {
                        "status": "failed",
                        "error_message": str(e),
                        "retry_count": self.request.retries + 1
                    },
                    "email_worker"
                )
                
                logger.error(f"Email notification failed: {e}")
                raise self.retry(countdown=60, exc=e)
    
    def _create_email_body(self, alert_data: Dict[str, Any]) -> str:
        """Create email body for alert."""
        return f"""
Alert Details:
- Message: {alert_data['message']}
- Severity: {alert_data['severity']}
- Status: {alert_data['status']}
- Started At: {alert_data['started_at']}
- Labels: {alert_data.get('labels', {})}

This is an automated alert from the DotMac Management Platform.
"""
    
    return asyncio.run(_send_email())


@celery_app.task(bind=True, max_retries=3)
def send_slack_notification(self, notification_id: str, channel_config: Dict[str, Any], alert_data: Dict[str, Any]):
    """Send Slack notification."""
    import asyncio
    import json
    
    async def _send_slack():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                notification_uuid = UUID(notification_id)
                
                # Update notification status
                await service.notification_repo.update_status(
                    notification_uuid, "sending", "slack_worker"
                )
                
                # Extract Slack configuration
                webhook_url = channel_config.get("webhook_url")
                channel = channel_config.get("channel", "#alerts")
                username = channel_config.get("username", "DotMac Alerts")
                icon_emoji = channel_config.get("icon_emoji", ":warning:")
                
                # Create Slack message
                color = self._get_slack_color(alert_data["severity"])
                message = {
                    "channel": channel,
                    "username": username,
                    "icon_emoji": icon_emoji,
                    "attachments": [{
                        "color": color,
                        "title": f"Alert: {alert_data['severity'].upper()}",
                        "text": alert_data["message"],
                        "fields": [
                            {
                                "title": "Status",
                                "value": alert_data["status"],
                                "short": True
                            },
                            {
                                "title": "Started At",
                                "value": alert_data["started_at"],
                                "short": True
                            }
                        ],
                        "footer": "DotMac Management Platform",
                        "ts": int(datetime.utcnow().timestamp())
                    }]
                }
                
                # TODO: Implement actual Slack webhook call
                # For now, simulate sending
                await asyncio.sleep(1)
                
                # Simulate success/failure
                if "test_fail" not in alert_data.get("labels", {}):
                    # Success
                    await service.notification_repo.update(
                        notification_uuid,
                        {
                            "status": "delivered",
                            "delivered_at": datetime.utcnow()
                        },
                        "slack_worker"
                    )
                    
                    logger.info(f"Slack notification sent successfully: {notification_id}")
                    return {"status": "delivered", "notification_id": notification_id}
                else:
                    # Simulate failure
                    raise Exception("Slack webhook call failed")
                
            except Exception as e:
                # Mark as failed
                await service.notification_repo.update(
                    UUID(notification_id),
                    {
                        "status": "failed",
                        "error_message": str(e),
                        "retry_count": self.request.retries + 1
                    },
                    "slack_worker"
                )
                
                logger.error(f"Slack notification failed: {e}")
                raise self.retry(countdown=60, exc=e)
    
    def _get_slack_color(self, severity: str) -> str:
        """Get Slack attachment color based on severity."""
        color_map = {
            "critical": "danger",
            "warning": "warning",
            "info": "good"
        }
        return color_map.get(severity, "warning")
    
    return asyncio.run(_send_slack())


@celery_app.task(bind=True, max_retries=3)
def send_webhook_notification(self, notification_id: str, channel_config: Dict[str, Any], alert_data: Dict[str, Any]):
    """Send webhook notification."""
    import asyncio
    import json
    
    async def _send_webhook():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                notification_uuid = UUID(notification_id)
                
                # Update notification status
                await service.notification_repo.update_status(
                    notification_uuid, "sending", "webhook_worker"
                )
                
                # Extract webhook configuration
                url = channel_config.get("url")
                method = channel_config.get("method", "POST")
                headers = channel_config.get("headers", {"Content-Type": "application/json"})
                auth = channel_config.get("auth")
                
                # Create webhook payload
                payload = {
                    "alert": alert_data,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "dotmac_management_platform"
                }
                
                # TODO: Implement actual HTTP request
                # For now, simulate webhook call
                await asyncio.sleep(1)
                
                # Simulate success/failure based on configuration
                if "test_fail" not in alert_data.get("labels", {}):
                    # Success
                    await service.notification_repo.update(
                        notification_uuid,
                        {
                            "status": "delivered",
                            "delivered_at": datetime.utcnow(),
                            "metadata": {"webhook_response": "200 OK"}
                        },
                        "webhook_worker"
                    )
                    
                    logger.info(f"Webhook notification sent successfully: {notification_id}")
                    return {"status": "delivered", "notification_id": notification_id}
                else:
                    # Simulate failure
                    raise Exception("Webhook endpoint returned 500 error")
                
            except Exception as e:
                # Mark as failed
                await service.notification_repo.update(
                    UUID(notification_id),
                    {
                        "status": "failed",
                        "error_message": str(e),
                        "retry_count": self.request.retries + 1
                    },
                    "webhook_worker"
                )
                
                logger.error(f"Webhook notification failed: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_send_webhook())


@celery_app.task(bind=True, max_retries=3)
def retry_failed_notifications(self):
    """Retry failed notifications that are eligible for retry."""
    import asyncio
    
    async def _retry_notifications():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                
                # Get failed notifications that can be retried
                cutoff_time = datetime.utcnow() - timedelta(minutes=10)
                failed_notifications = await service.notification_repo.get_retryable_notifications(
                    cutoff_time, max_retries=3
                )
                
                retried = 0
                skipped = 0
                
                for notification in failed_notifications:
                    try:
                        # Get notification channel and alert details
                        channel = await service.notification_channel_repo.get_by_id(notification.channel_id)
                        alert = await service.alert_repo.get_by_id(notification.alert_id)
                        
                        if not channel or not alert:
                            continue
                        
                        # Retry the notification based on channel type
                        if channel.type == "email":
                            send_email_notification.delay(
                                str(notification.id),
                                channel.configuration,
                                {
                                    "message": alert.message,
                                    "severity": alert.severity,
                                    "status": alert.status,
                                    "started_at": alert.started_at.isoformat(),
                                    "labels": alert.labels
                                }
                            )
                        elif channel.type == "slack":
                            send_slack_notification.delay(
                                str(notification.id),
                                channel.configuration,
                                {
                                    "message": alert.message,
                                    "severity": alert.severity,
                                    "status": alert.status,
                                    "started_at": alert.started_at.isoformat(),
                                    "labels": alert.labels
                                }
                            )
                        elif channel.type == "webhook":
                            send_webhook_notification.delay(
                                str(notification.id),
                                channel.configuration,
                                {
                                    "message": alert.message,
                                    "severity": alert.severity,
                                    "status": alert.status,
                                    "started_at": alert.started_at.isoformat(),
                                    "labels": alert.labels
                                }
                            )
                        
                        retried += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to retry notification {notification.id}: {e}")
                        skipped += 1
                
                logger.info(f"Notification retry completed: {retried} retried, {skipped} skipped")
                return {"retried": retried, "skipped": skipped}
                
            except Exception as e:
                logger.error(f"Error retrying failed notifications: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_retry_notifications())


@celery_app.task(bind=True, max_retries=3)
def cleanup_old_notifications(self, retention_days: int = 30):
    """Clean up old notification records."""
    import asyncio
    
    async def _cleanup_notifications():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                
                # Clean up old delivered notifications
                deleted_count = await service.notification_repo.delete_old_notifications(cutoff_date)
                
                logger.info(f"Notification cleanup completed: {deleted_count} notifications deleted")
                return {"deleted_count": deleted_count}
                
            except Exception as e:
                logger.error(f"Error cleaning up notifications: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_cleanup_notifications())


@celery_app.task(bind=True, max_retries=3)
def send_digest_notifications(self, digest_type: str = "daily"):
    """Send digest notifications to subscribers."""
    import asyncio
    
    async def _send_digests():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                
                # Determine time range for digest
                end_time = datetime.utcnow()
                if digest_type == "daily":
                    start_time = end_time - timedelta(days=1)
                elif digest_type == "weekly":
                    start_time = end_time - timedelta(days=7)
                elif digest_type == "monthly":
                    start_time = end_time - timedelta(days=30)
                else:
                    raise ValueError(f"Unknown digest type: {digest_type}")
                
                # Get tenants that have digest subscriptions
                # TODO: Implement digest subscription management
                # For now, simulate with all tenants
                
                digests_sent = 0
                digests_failed = 0
                
                # Get alerts for the digest period
                alerts = await service.alert_repo.get_alerts_for_period(start_time, end_time)
                
                # Group alerts by tenant
                alerts_by_tenant = {}
                for alert in alerts:
                    tenant_id = alert.tenant_id
                    if tenant_id not in alerts_by_tenant:
                        alerts_by_tenant[tenant_id] = []
                    alerts_by_tenant[tenant_id].append(alert)
                
                # Send digest for each tenant
                for tenant_id, tenant_alerts in alerts_by_tenant.items():
                    try:
                        # Create digest content
                        digest_data = {
                            "tenant_id": str(tenant_id),
                            "digest_type": digest_type,
                            "period_start": start_time.isoformat(),
                            "period_end": end_time.isoformat(),
                            "total_alerts": len(tenant_alerts),
                            "critical_alerts": len([a for a in tenant_alerts if a.severity == "critical"]),
                            "warning_alerts": len([a for a in tenant_alerts if a.severity == "warning"]),
                            "info_alerts": len([a for a in tenant_alerts if a.severity == "info"]),
                            "alerts": [
                                {
                                    "message": alert.message,
                                    "severity": alert.severity,
                                    "started_at": alert.started_at.isoformat(),
                                    "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
                                }
                                for alert in tenant_alerts[:10]  # Include top 10 alerts
                            ]
                        }
                        
                        # TODO: Send digest via configured channels
                        # For now, just log the digest
                        logger.info(f"Digest prepared for tenant {tenant_id}: {digest_data['total_alerts']} alerts")
                        
                        digests_sent += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to send digest for tenant {tenant_id}: {e}")
                        digests_failed += 1
                
                logger.info(f"Digest notifications completed: {digests_sent} sent, {digests_failed} failed")
                return {"digests_sent": digests_sent, "digests_failed": digests_failed}
                
            except Exception as e:
                logger.error(f"Error sending digest notifications: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_send_digests())


@celery_app.task(bind=True, max_retries=3)
def test_notification_channels(self, tenant_id: str):
    """Test all notification channels for a tenant."""
    import asyncio
    
    async def _test_channels():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                tenant_uuid = UUID(tenant_id)
                
                # Get all notification channels for tenant
                channels = await service.notification_channel_repo.get_by_tenant(tenant_uuid)
                
                test_results = []
                
                for channel in channels:
                    try:
                        # Create test alert data
                        test_alert = {
                            "message": f"Test notification from channel {channel.name}",
                            "severity": "info",
                            "status": "firing",
                            "started_at": datetime.utcnow().isoformat(),
                            "labels": {"test": "true", "channel_id": str(channel.id)}
                        }
                        
                        # Create test notification record
                        notification_data = {
                            "tenant_id": tenant_uuid,
                            "alert_id": None,  # No actual alert for test
                            "channel_id": channel.id,
                            "status": "pending"
                        }
                        
                        notification = await service.notification_repo.create(
                            notification_data, "channel_tester"
                        )
                        
                        # Send test notification
                        if channel.type == "email":
                            result = send_email_notification.delay(
                                str(notification.id),
                                channel.configuration,
                                test_alert
                            )
                        elif channel.type == "slack":
                            result = send_slack_notification.delay(
                                str(notification.id),
                                channel.configuration,
                                test_alert
                            )
                        elif channel.type == "webhook":
                            result = send_webhook_notification.delay(
                                str(notification.id),
                                channel.configuration,
                                test_alert
                            )
                        else:
                            raise ValueError(f"Unknown channel type: {channel.type}")
                        
                        test_results.append({
                            "channel_id": str(channel.id),
                            "channel_name": channel.name,
                            "channel_type": channel.type,
                            "test_status": "initiated",
                            "task_id": result.id
                        })
                        
                    except Exception as e:
                        test_results.append({
                            "channel_id": str(channel.id),
                            "channel_name": channel.name,
                            "channel_type": channel.type,
                            "test_status": "failed",
                            "error": str(e)
                        })
                
                logger.info(f"Notification channel tests initiated for tenant {tenant_id}: {len(test_results)} channels")
                return {
                    "tenant_id": tenant_id,
                    "channels_tested": len(test_results),
                    "test_results": test_results
                }
                
            except Exception as e:
                logger.error(f"Error testing notification channels: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_test_channels())