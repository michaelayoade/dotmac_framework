"""Notification-related background tasks."""

import logging
from datetime import datetime
from typing import Dict, Any, List

from dotmac_isp.core.celery_app import celery_app

logger = logging.getLogger(__name__, timezone)


@celery_app.task(bind=True)
def send_service_outage_notification(
    self, affected_services: List[str], estimated_resolution: str, customers: List[str]
):
    """Send notifications about service outages."""
    try:
        logger.info(f"Sending outage notifications for services: {affected_services}")

        from dotmac_isp.core.tasks import send_email_notification, send_sms_notification

        # Prepare notification content
        services_text = ", ".join(affected_services)
        subject = f"Service Outage Alert - {services_text}"

        results = []

        # Send notifications to all affected customers
        for customer in customers:
            if "@" in customer:  # Email
                task = send_email_notification.delay(
                    recipient=customer,
                    subject=subject,
                    template="service_outage",
                    context={
                        "affected_services": affected_services,
                        "estimated_resolution": estimated_resolution,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                results.append(
                    {"type": "email", "recipient": customer, "task_id": task.id}
                )

            elif (
                customer.replace("+", "").replace("-", "").replace(" ", "").isdigit()
            ):  # Phone
                message = f"Service outage alert: {services_text}. Estimated resolution: {estimated_resolution}"
                task = send_sms_notification.delay(
                    phone_number=customer, message=message
                )
                results.append(
                    {"type": "sms", "recipient": customer, "task_id": task.id}
                )

        logger.info(f"Outage notifications queued: {len(results)} notifications")

        return {
            "affected_services": affected_services,
            "notifications_sent": len(results),
            "details": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to send outage notifications: {e}")
        raise


@celery_app.task(bind=True)
def send_maintenance_notification(
    self,
    maintenance_type: str,
    scheduled_time: str,
    duration_hours: int,
    affected_services: List[str],
    customers: List[str],
):
    """Send notifications about scheduled maintenance."""
    try:
        logger.info(f"Sending maintenance notifications for {scheduled_time}")

        from dotmac_isp.core.tasks import send_email_notification

        results = []
        subject = f"Scheduled Maintenance - {maintenance_type}"

        for customer in customers:
            if "@" in customer:  # Email
                task = send_email_notification.delay(
                    recipient=customer,
                    subject=subject,
                    template="maintenance_notification",
                    context={
                        "maintenance_type": maintenance_type,
                        "scheduled_time": scheduled_time,
                        "duration_hours": duration_hours,
                        "affected_services": affected_services,
                    },
                )
                results.append({"recipient": customer, "task_id": task.id})

        logger.info(f"Maintenance notifications queued: {len(results)} emails")

        return {
            "maintenance_type": maintenance_type,
            "scheduled_time": scheduled_time,
            "notifications_sent": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to send maintenance notifications: {e}")
        raise


@celery_app.task(bind=True)
def send_usage_alert(
    self,
    customer_email: str,
    service_name: str,
    usage_percentage: float,
    threshold: float,
):
    """Send usage threshold alert to customer."""
    try:
        logger.info(
            f"Sending usage alert to {customer_email}: {service_name} at {usage_percentage}%"
        )

        from dotmac_isp.core.tasks import send_email_notification

        # Determine alert level
        if usage_percentage >= 95:
            alert_level = "critical"
            subject = f"URGENT: {service_name} Usage Critical ({usage_percentage:.1f}%)"
        elif usage_percentage >= 85:
            alert_level = "warning"
            subject = f"Warning: {service_name} Usage High ({usage_percentage:.1f}%)"
        else:
            alert_level = "info"
            subject = f"Notice: {service_name} Usage Alert ({usage_percentage:.1f}%)"

        task = send_email_notification.delay(
            recipient=customer_email,
            subject=subject,
            template="usage_alert",
            context={
                "service_name": service_name,
                "usage_percentage": usage_percentage,
                "threshold": threshold,
                "alert_level": alert_level,
            },
        )

        return {
            "customer_email": customer_email,
            "service_name": service_name,
            "usage_percentage": usage_percentage,
            "alert_level": alert_level,
            "email_task_id": task.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to send usage alert to {customer_email}: {e}")
        raise


@celery_app.task(bind=True)
def send_service_activation_notification(
    self, customer_email: str, service_name: str, activation_details: Dict[str, Any]
):
    """Send notification when a new service is activated."""
    try:
        logger.info(
            f"Sending service activation notification to {customer_email}: {service_name}"
        )

        from dotmac_isp.core.tasks import send_email_notification

        task = send_email_notification.delay(
            recipient=customer_email,
            subject=f"Service Activated - {service_name}",
            template="service_activation",
            context={
                "service_name": service_name,
                "activation_details": activation_details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "customer_email": customer_email,
            "service_name": service_name,
            "email_task_id": task.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(
            f"Failed to send service activation notification to {customer_email}: {e}"
        )
        raise


@celery_app.task(bind=True)
def send_payment_confirmation(
    self, customer_email: str, invoice_id: str, amount: float, payment_method: str
):
    """Send payment confirmation notification."""
    try:
        logger.info(
            f"Sending payment confirmation to {customer_email}: invoice {invoice_id}"
        )

        from dotmac_isp.core.tasks import send_email_notification

        task = send_email_notification.delay(
            recipient=customer_email,
            subject=f"Payment Confirmation - Invoice {invoice_id}",
            template="payment_confirmation",
            context={
                "invoice_id": invoice_id,
                "amount": amount,
                "payment_method": payment_method,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "customer_email": customer_email,
            "invoice_id": invoice_id,
            "amount": amount,
            "email_task_id": task.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to send payment confirmation to {customer_email}: {e}")
        raise


@celery_app.task(bind=True)
def send_password_reset_notification(
    self, user_email: str, reset_token: str, expires_in_minutes: int = 60
):
    """Send password reset notification."""
    try:
        logger.info(f"Sending password reset notification to {user_email}")

        from dotmac_isp.core.tasks import send_email_notification

        # Generate reset link (in production, this would be a proper URL)
        reset_link = f"https://portal.example.com/reset-password?token={reset_token}"

        task = send_email_notification.delay(
            recipient=user_email,
            subject="Password Reset Request",
            template="password_reset",
            context={
                "reset_link": reset_link,
                "expires_in_minutes": expires_in_minutes,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "user_email": user_email,
            "reset_token": reset_token,
            "expires_in_minutes": expires_in_minutes,
            "email_task_id": task.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to send password reset notification to {user_email}: {e}")
        raise


@celery_app.task(bind=True)
def send_bulk_notification(
    self,
    notification_type: str,
    recipients: List[str],
    subject: str,
    template: str,
    context: Dict[str, Any],
):
    """Send bulk notifications to multiple recipients."""
    try:
        logger.info(
            f"Sending bulk {notification_type} notifications to {len(recipients)} recipients"
        )

        from dotmac_isp.core.tasks import send_email_notification, send_sms_notification
        from celery import group

        # Create tasks for all recipients
        tasks = []

        for recipient in recipients:
            if notification_type == "email" and "@" in recipient:
                tasks.append(
                    send_email_notification.s(
                        recipient=recipient,
                        subject=subject,
                        template=template,
                        context=context,
                    )
                )
            elif (
                notification_type == "sms"
                and recipient.replace("+", "")
                .replace("-", "")
                .replace(" ", "")
                .isdigit()
            ):
                # For SMS, use subject as message
                tasks.append(
                    send_sms_notification.s(phone_number=recipient, message=subject)
                )

        # Execute all notifications in parallel
        job = group(tasks)
        result = job.apply_async()

        logger.info(f"Bulk notification job created: {len(tasks)} tasks queued")

        return {
            "notification_type": notification_type,
            "recipients_count": len(recipients),
            "tasks_queued": len(tasks),
            "job_id": result.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to send bulk notifications: {e}")
        raise
