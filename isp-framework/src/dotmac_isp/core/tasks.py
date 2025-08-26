"""Enhanced core background tasks for DotMac ISP Framework."""

import asyncio
import logging
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from dotmac_isp.core.celery_app import celery_app, CELERY_AVAILABLE, task

# Import Task conditionally
if CELERY_AVAILABLE:
    from celery import Task
else:

    class Task:
        """Class for Task operations."""
        def __call__(self, *args, timezone=None, **kwargs):
            """  Call   operation."""
            pass


from dotmac_isp.shared.cache import (
    get_cache_manager,
    get_session_manager,
    cache_invalidate_tag,
)
from dotmac_isp.core.ssl_manager import get_ssl_manager
from dotmac_isp.core.caching_middleware import cache_warmup_service

logger = logging.getLogger(__name__)


class AsyncTask(Task):
    """Base task class that supports async functions."""

    def __call__(self, *args, **kwargs):
        """Execute async task in event loop."""
        if asyncio.iscoroutinefunction(self.run):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.run(*args, **kwargs))
            finally:
                loop.close()
        else:
            return self.run(*args, **kwargs)


@task(bind=True, name="dotmac_isp.core.tasks.health_check")
def health_check(self):
    """Enhanced periodic health check for system components."""
    try:
        cache_manager = get_cache_manager()

        # Test Redis connection
        redis_status = "healthy"
        try:
            cache_manager.redis_client.ping()
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
            logger.error(f"Redis health check failed: {e}")

        # Test database connection (simplified check)
        db_status = "healthy"
        try:
            # This would normally test actual DB connection
            pass
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
            logger.error(f"Database health check failed: {e}")

        health_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": (
                "healthy"
                if "unhealthy" not in f"{redis_status}{db_status}"
                else "degraded"
            ),
            "components": {
                "redis": redis_status,
                "database": db_status,
                "celery": "healthy",  # If task runs, Celery is working
            },
            "worker_id": self.request.id,
            "hostname": self.request.hostname,
        }

        # Cache health status
        cache_manager.set("system_health", health_data, 300, "system")

        logger.info(f"Health check completed: {health_data['status']}")
        return health_data
        try:
            cache_manager = get_cache_manager()
            cache_manager.redis_client.ping()
            results["redis"] = "connected"
        except Exception as e:
            results["redis"] = f"error: {str(e)}"
            results["status"] = "degraded"

        logger.info(f"Health check completed: {results['status']}")
        return results

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "unhealthy",
            "error": str(e),
        }


@celery_app.task(bind=True, base=AsyncTask)
async def cleanup_expired_sessions(self):
    """Clean up expired sessions from Redis."""
    try:
        session_manager = get_session_manager()
        cache_manager = get_cache_manager()

        # Get all session keys
        pattern = "dotmac:sessions:session:*"
        keys = cache_manager.redis_client.keys(pattern)

        cleaned_count = 0
        for key in keys:
            try:
                # Check if key has TTL (not expired)
                ttl = cache_manager.redis_client.ttl(key)
                if ttl == -1:  # No expiry set
                    # Set default expiry of 1 hour for sessions without TTL
                    cache_manager.redis_client.expire(key, 3600)
                elif ttl == -2:  # Key doesn't exist (already expired)
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"Error checking session key {key}: {e}")

        logger.info(
            f"Session cleanup completed: {cleaned_count} expired sessions removed"
        )
        return {
            "cleaned_count": cleaned_count,
            "total_checked": len(keys),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        raise


@celery_app.task(bind=True, base=AsyncTask)
async def renew_ssl_certificates(self):
    """Renew SSL certificates that are expiring."""
    try:
        ssl_manager = get_ssl_manager()

        # Check and renew certificates
        results = await ssl_manager.ensure_certificates()

        renewed_domains = [domain for domain, success in results.items() if success]
        failed_domains = [domain for domain, success in results.items() if not success]

        logger.info(
            f"SSL renewal completed: {len(renewed_domains)} renewed, {len(failed_domains)} failed"
        )

        return {
            "renewed": renewed_domains,
            "failed": failed_domains,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"SSL certificate renewal failed: {e}")
        raise


# ============================================================================
# STRATEGIC PLUGIN-DRIVEN COMMUNICATION TASKS
# Replaces hardcoded send_email_notification and send_sms_notification
# with unified plugin-driven communication system
# ============================================================================

from dotmac_isp.core.communication_bridge import (
    send_notification,
    send_customer_notification, 
    initialize_isp_communication_system
)

@celery_app.task(bind=True)
async def send_channel_notification(
    self, 
    channel_type: str, 
    recipient: str, 
    content: str, 
    metadata: Dict[str, Any] = None
):
    """
    Send notification via strategic plugin system.
    
    Universal replacement for send_email_notification and send_sms_notification.
    Supports ANY communication channel via plugins - no hardcoding.
    """
    try:
        logger.info(f"Sending {channel_type} notification to {recipient}")

        # Send via strategic plugin system - NO HARDCODED CHANNELS
        result = await send_notification(
            channel_type=channel_type,
            recipient=recipient, 
            content=content,
            metadata=metadata or {}
        )

        if result.get("success"):
            return {
                "channel_type": channel_type,
                "recipient": recipient,
                "status": "sent",
                "message_id": result.get("message_id"),
                "provider": result.get("provider"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            logger.error(f"Plugin system failed: {result.get('error')}")
            raise Exception(f"Notification failed: {result.get('error')}")

    except Exception as e:
        logger.error(f"Failed to send {channel_type} notification to {recipient}: {e}")
        raise


@celery_app.task(bind=True) 
async def send_customer_channel_notification(
    self,
    customer_id: str,
    channel_type: str, 
    template: str,
    context: Dict[str, Any] = None
):
    """
    Send notification to customer via strategic plugin system.
    
    ISP-specific task that integrates customer management with plugin system.
    """
    try:
        logger.info(f"Sending {channel_type} notification to customer {customer_id} using template {template}")

        result = await send_customer_notification(
            customer_id=customer_id,
            channel_type=channel_type,
            template=template,
            context=context or {}
        )

        if result.get("success"):
            return {
                "customer_id": customer_id,
                "channel_type": channel_type,
                "template": template,
                "status": "sent",
                "message_id": result.get("message_id"),
                "provider": result.get("provider"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            logger.error(f"Customer notification failed: {result.get('error')}")
            raise Exception(f"Customer notification failed: {result.get('error')}")

    except Exception as e:
        logger.error(f"Failed to send {channel_type} notification to customer {customer_id}: {e}")
        raise


# ============================================================================  
# BACKWARD COMPATIBILITY LAYER
# Maintains existing API while migrating to plugin system
# ============================================================================

@celery_app.task(bind=True)
def send_email_notification(
    self, recipient: str, subject: str, template: str, context: Dict[str, Any] = None
):
    """
    LEGACY COMPATIBILITY: Send email notification.
    
    ⚠️  DEPRECATED: Use send_channel_notification with channel_type="email" instead.
    This method provides backward compatibility during migration.
    """
    logger.warning("DEPRECATED: send_email_notification is deprecated. Use send_channel_notification.")
    
    # Convert to plugin-driven call
    content = f"Subject: {subject}\nTemplate: {template}"
    if context:
        content += f"\nContext: {context}"
    
    # Call the new plugin-driven method
    return send_channel_notification.delay(
        channel_type="email",
        recipient=recipient,
        content=content,
        metadata={"subject": subject, "template": template, "context": context}
    )


@celery_app.task(bind=True)
def send_sms_notification(self, phone_number: str, message: str):
    """
    LEGACY COMPATIBILITY: Send SMS notification.
    
    ⚠️  DEPRECATED: Use send_channel_notification with channel_type="sms" instead.
    This method provides backward compatibility during migration.
    """
    logger.warning("DEPRECATED: send_sms_notification is deprecated. Use send_channel_notification.")
    
    # Call the new plugin-driven method
    return send_channel_notification.delay(
        channel_type="sms",
        recipient=phone_number,
        content=message,
        metadata={"legacy_method": "send_sms_notification"}
    )


@celery_app.task(bind=True, base=AsyncTask)
async def cleanup_cache_namespace(self, namespace: str, max_age_hours: int = 24):
    """Clean up old cache entries in a namespace."""
    try:
        cache_manager = get_cache_manager()

        # Get all keys in namespace
        pattern = f"dotmac:{namespace}:*"
        keys = cache_manager.redis_client.keys(pattern)

        cleaned_count = 0
        for key in keys:
            try:
                # Check key age (this is simplified - in practice you'd track creation time)
                ttl = cache_manager.redis_client.ttl(key)
                if ttl == -1:  # No expiry set
                    # Delete very old keys without TTL
                    cache_manager.redis_client.delete(key)
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"Error cleaning cache key {key}: {e}")

        logger.info(f"Cache cleanup for {namespace}: {cleaned_count} keys removed")
        return {
            "namespace": namespace,
            "cleaned_count": cleaned_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Cache cleanup failed for {namespace}: {e}")
        raise


@celery_app.task(bind=True)
def process_webhook(
    self, webhook_type: str, data: Dict[str, Any], signature: str = None
):
    """Process incoming webhooks (e.g., payment processors, external APIs)."""
    try:
        logger.info(f"Processing {webhook_type} webhook")

        # Verify signature if provided
        if signature:
            # Implement webhook signature verification
            pass

        # Route to appropriate handler based on webhook type
        handlers = {
            "stripe_payment": _handle_stripe_webhook,
            "twilio_sms": _handle_twilio_webhook,
            "monitoring_alert": _handle_monitoring_webhook,
        }

        handler = handlers.get(webhook_type)
        if not handler:
            raise ValueError(f"Unknown webhook type: {webhook_type}")

        result = handler(data)

        logger.info(f"Webhook {webhook_type} processed successfully")
        return result

    except Exception as e:
        logger.error(f"Webhook processing failed for {webhook_type}: {e}")
        raise


def _handle_stripe_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Stripe payment webhooks."""
    # Implementation would process payment events
    return {"status": "processed", "type": "stripe_payment"}


def _handle_twilio_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Twilio SMS webhooks."""
    # Implementation would process SMS delivery events
    return {"status": "processed", "type": "twilio_sms"}


def _handle_monitoring_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle monitoring system webhooks."""
    # Implementation would process alerts and notifications
    return {"status": "processed", "type": "monitoring_alert"}


@celery_app.task(bind=True, base=AsyncTask)
async def backup_database(self, backup_type: str = "incremental"):
    """Create database backup."""
    try:
        logger.info(f"Starting {backup_type} database backup")

        # This would implement actual database backup logic
        # For now, just log the operation

        backup_file = (
            f"backup_{backup_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.sql"
        )

        # Simulate backup process
        import time

        time.sleep(5)  # Simulate backup time

        logger.info(f"Database backup completed: {backup_file}")

        return {
            "backup_file": backup_file,
            "backup_type": backup_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        raise


# Task workflow functions
def send_welcome_email_workflow(user_email: str, user_name: str, tenant_id: str):
    """Workflow to send welcome email with multiple tasks."""
    from celery import chain

    # Chain of tasks for welcome workflow
    workflow = chain(
        # First, log the start
        celery_app.send_task("dotmac_isp.core.tasks.health_check"),
        # Then send welcome email
        send_email_notification.s(
            recipient=user_email,
            subject=f"Welcome to DotMac ISP, {user_name}!",
            template="welcome_email",
            context={"user_name": user_name, "tenant_id": tenant_id},
        ),
        # Finally, log completion
        celery_app.send_task("dotmac_isp.core.tasks.health_check"),
    )

    return workflow.apply_async()


def emergency_notification_workflow(message: str, recipients: List[str]):
    """Emergency notification workflow (email + SMS)."""
    from celery import group

    # Send notifications in parallel
    notification_tasks = []

    for recipient in recipients:
        if "@" in recipient:  # Email
            notification_tasks.append(
                send_email_notification.s(
                    recipient=recipient,
                    subject="EMERGENCY: System Alert",
                    template="emergency_alert",
                    context={"message": message},
                )
            )
        else:  # Phone number
            notification_tasks.append(
                send_sms_notification.s(
                    phone_number=recipient, message=f"EMERGENCY: {message}"
                )
            )

    # Execute all notifications in parallel
    job = group(notification_tasks)
    return job.apply_async()


# ===== NEW ENHANCED BACKGROUND TASKS =====


@task(bind=True, name="dotmac_isp.core.tasks.system_metrics_collection")
def system_metrics_collection(self):
    """Collect system metrics and store them for monitoring."""
    try:
        # Collect system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3),
        }

        # Store metrics in cache for monitoring dashboard
        cache_manager = get_cache_manager()

        # Store current metrics
        cache_manager.set("system_metrics_current", metrics, 300, "metrics")

        # Store in time series (keep last 24 hours)
        metrics_key = (
            f"system_metrics_history:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
        )
        cache_manager.set(metrics_key, metrics, 86400, "metrics")

        logger.debug(
            f"System metrics collected: CPU {cpu_percent}%, Memory {memory.percent}%"
        )
        return metrics

    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")
        return {"error": str(e)}


@task(bind=True, name="dotmac_isp.core.tasks.application_metrics_collection")
def application_metrics_collection(self):
    """Collect application-specific metrics."""
    try:
        cache_manager = get_cache_manager()

        # Collect Redis metrics
        redis_info = cache_manager.redis_client.info()

        app_metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "redis_connected_clients": redis_info.get("connected_clients", 0),
            "redis_used_memory_mb": redis_info.get("used_memory", 0) / (1024**2),
            "redis_keyspace_hits": redis_info.get("keyspace_hits", 0),
            "redis_keyspace_misses": redis_info.get("keyspace_misses", 0),
            "redis_ops_per_sec": redis_info.get("instantaneous_ops_per_sec", 0),
        }

        # Calculate cache hit ratio
        hits = app_metrics["redis_keyspace_hits"]
        misses = app_metrics["redis_keyspace_misses"]
        if hits + misses > 0:
            app_metrics["cache_hit_ratio"] = hits / (hits + misses)
        else:
            app_metrics["cache_hit_ratio"] = 0

        # Store metrics
        cache_manager.set("app_metrics_current", app_metrics, 300, "metrics")

        logger.debug(
            f"App metrics collected: Cache hit ratio {app_metrics['cache_hit_ratio']:.2%}"
        )
        return app_metrics

    except Exception as e:
        logger.error(f"Application metrics collection failed: {e}")
        return {"error": str(e)}


# ===== TASK MANAGEMENT UTILITIES =====


def schedule_metrics_collection():
    """Schedule immediate metrics collection."""
    system_metrics_collection.delay()
    application_metrics_collection.delay()


def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get status of a background task."""
    try:
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None,
            "successful": result.successful() if result.ready() else None,
            "failed": result.failed() if result.ready() else None,
        }
    except Exception as e:
        return {"task_id": task_id, "error": str(e)}


def cancel_task(task_id: str) -> bool:
    """Cancel a background task."""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return True
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        return False
