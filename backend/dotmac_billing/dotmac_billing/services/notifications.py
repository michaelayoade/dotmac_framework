"""
Notification service for email and SMS delivery.
"""

import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.mime.multipart import MimeMultipart
from email.mime.text import MimeText
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from jinja2 import DictLoader, Environment

from ..core.config import get_config
from ..core.exceptions import BillingError

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    PUSH = "push"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationTemplate:
    """Notification template definition."""
    name: str
    subject: str
    body: str
    notification_type: NotificationType
    variables: List[str] = None

    def render(self, variables: Dict[str, Any]) -> tuple[str, str]:
        """Render template with variables."""
        template_env = Environment(loader=DictLoader({
            'subject': self.subject,
            'body': self.body
        }))

        rendered_subject = template_env.get_template('subject').render(**variables)
        rendered_body = template_env.get_template('body').render(**variables)

        return rendered_subject, rendered_body


@dataclass
class NotificationRequest:
    """Notification delivery request."""
    recipient: str
    template_name: str
    variables: Dict[str, Any]
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""

    @abstractmethod
    async def send(self, request: NotificationRequest, subject: str, body: str) -> bool:
        """Send notification."""
        pass

    @abstractmethod
    def supports_type(self, notification_type: NotificationType) -> bool:
        """Check if provider supports notification type."""
        pass


class EmailProvider(NotificationProvider):
    """Email notification provider using SMTP."""

    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str,
                 use_tls: bool = True, from_email: str = None, from_name: str = None):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_email = from_email or username
        self.from_name = from_name or "DotMac Billing"

    async def send(self, request: NotificationRequest, subject: str, body: str) -> bool:
        """Send email notification."""
        try:
            # Create message
            msg = MimeMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = request.recipient

            # Add plain text and HTML parts
            text_part = MimeText(body, 'plain')
            html_part = MimeText(body, 'html')

            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)

            if self.use_tls:
                server.starttls()

            server.login(self.username, self.password)

            text = msg.as_string()
            server.sendmail(self.from_email, [request.recipient], text)
            server.quit()

            logger.info(f"Email sent successfully to {request.recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {request.recipient}: {e}")
            return False

    def supports_type(self, notification_type: NotificationType) -> bool:
        """Check if provider supports email."""
        return notification_type == NotificationType.EMAIL


class SMSProvider(NotificationProvider):
    """SMS notification provider using Twilio."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    async def send(self, request: NotificationRequest, subject: str, body: str) -> bool:
        """Send SMS notification."""
        try:
            # Use HTTP client to call Twilio API
            auth = (self.account_sid, self.auth_token)
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

            data = {
                'From': self.from_number,
                'To': request.recipient,
                'Body': body
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, auth=auth, data=data)
                response.raise_for_status()

            logger.info(f"SMS sent successfully to {request.recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS to {request.recipient}: {e}")
            return False

    def supports_type(self, notification_type: NotificationType) -> bool:
        """Check if provider supports SMS."""
        return notification_type == NotificationType.SMS


class WebhookProvider(NotificationProvider):
    """Webhook notification provider for platform integration."""

    def __init__(self, webhook_url: str, secret_key: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret_key = secret_key

    async def send(self, request: NotificationRequest, subject: str, body: str) -> bool:
        """Send webhook notification."""
        try:
            payload = {
                "type": "notification",
                "notification_type": request.notification_type.value,
                "recipient": request.recipient,
                "subject": subject,
                "body": body,
                "template_name": request.template_name,
                "priority": request.priority.value,
                "tenant_id": request.tenant_id,
                "user_id": request.user_id,
                "metadata": request.metadata or {}
            }

            headers = {"Content-Type": "application/json"}

            if self.secret_key:
                import hashlib
                import hmac
                import json

                payload_str = json.dumps(payload)
                signature = hmac.new(
                    self.secret_key.encode(),
                    payload_str.encode(),
                    hashlib.sha256
                ).hexdigest()
                headers["X-Signature"] = f"sha256={signature}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()

            logger.info(f"Webhook notification sent successfully for {request.recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False

    def supports_type(self, notification_type: NotificationType) -> bool:
        """Webhook provider supports all types for platform integration."""
        return True


class NotificationService:
    """Central notification service for the billing system."""

    def __init__(self):
        self.providers: List[NotificationProvider] = []
        self.templates: Dict[str, NotificationTemplate] = {}
        self._load_default_templates()
        self._initialize_providers()

    def _load_default_templates(self):
        """Load default notification templates."""
        self.templates.update({
            "invoice_created": NotificationTemplate(
                name="invoice_created",
                subject="New Invoice #{{ invoice_number }} - {{ company_name }}",
                body="""
                <h2>New Invoice</h2>
                <p>Dear {{ customer_name }},</p>
                <p>A new invoice has been generated for your account.</p>

                <h3>Invoice Details:</h3>
                <ul>
                    <li>Invoice Number: {{ invoice_number }}</li>
                    <li>Amount: {{ amount }} {{ currency }}</li>
                    <li>Due Date: {{ due_date }}</li>
                </ul>

                <p>Please pay this invoice by the due date to avoid any service interruption.</p>

                <p>Thank you for your business!</p>
                <p>{{ company_name }}</p>
                """,
                notification_type=NotificationType.EMAIL,
                variables=["invoice_number", "company_name", "customer_name", "amount", "currency", "due_date"]
            ),

            "payment_successful": NotificationTemplate(
                name="payment_successful",
                subject="Payment Confirmation - {{ company_name }}",
                body="""
                <h2>Payment Confirmation</h2>
                <p>Dear {{ customer_name }},</p>
                <p>We have successfully received your payment.</p>

                <h3>Payment Details:</h3>
                <ul>
                    <li>Payment ID: {{ payment_id }}</li>
                    <li>Amount: {{ amount }} {{ currency }}</li>
                    <li>Date: {{ payment_date }}</li>
                    <li>Method: {{ payment_method }}</li>
                </ul>

                <p>Thank you for your prompt payment!</p>
                <p>{{ company_name }}</p>
                """,
                notification_type=NotificationType.EMAIL,
                variables=["company_name", "customer_name", "payment_id", "amount", "currency", "payment_date", "payment_method"]
            ),

            "payment_failed": NotificationTemplate(
                name="payment_failed",
                subject="Payment Failed - Action Required - {{ company_name }}",
                body="""
                <h2>Payment Failed</h2>
                <p>Dear {{ customer_name }},</p>
                <p>We were unable to process your payment. Please update your payment method or contact us.</p>

                <h3>Failed Payment Details:</h3>
                <ul>
                    <li>Invoice Number: {{ invoice_number }}</li>
                    <li>Amount: {{ amount }} {{ currency }}</li>
                    <li>Failure Reason: {{ failure_reason }}</li>
                </ul>

                <p>Please take action to avoid service interruption.</p>
                <p>{{ company_name }}</p>
                """,
                notification_type=NotificationType.EMAIL,
                variables=["company_name", "customer_name", "invoice_number", "amount", "currency", "failure_reason"]
            ),

            "dunning_reminder": NotificationTemplate(
                name="dunning_reminder",
                subject="Payment Reminder - {{ company_name }}",
                body="""
                <h2>Payment Reminder</h2>
                <p>Dear {{ customer_name }},</p>
                <p>This is a reminder that you have an overdue invoice.</p>

                <h3>Overdue Invoice:</h3>
                <ul>
                    <li>Invoice Number: {{ invoice_number }}</li>
                    <li>Amount: {{ amount }} {{ currency }}</li>
                    <li>Due Date: {{ due_date }}</li>
                    <li>Days Overdue: {{ days_overdue }}</li>
                </ul>

                <p>Please pay immediately to avoid account suspension.</p>
                <p>{{ company_name }}</p>
                """,
                notification_type=NotificationType.EMAIL,
                variables=["company_name", "customer_name", "invoice_number", "amount", "currency", "due_date", "days_overdue"]
            ),

            "account_suspended": NotificationTemplate(
                name="account_suspended",
                subject="Account Suspended - {{ company_name }}",
                body="""Account suspended due to non-payment. Contact support immediately. Amount due: {{ amount }} {{ currency }}""",
                notification_type=NotificationType.SMS,
                variables=["company_name", "amount", "currency"]
            )
        })

    def _initialize_providers(self):
        """Initialize notification providers based on configuration."""
        config = get_config()

        # Email provider
        if config.notifications.smtp_host:
            email_provider = EmailProvider(
                smtp_host=config.notifications.smtp_host,
                smtp_port=config.notifications.smtp_port,
                username=config.notifications.smtp_username,
                password=config.notifications.smtp_password,
                use_tls=config.notifications.smtp_use_tls,
                from_email=config.notifications.from_email,
                from_name=config.notifications.from_name
            )
            self.providers.append(email_provider)

        # SMS provider
        if config.notifications.twilio_account_sid:
            sms_provider = SMSProvider(
                account_sid=config.notifications.twilio_account_sid,
                auth_token=config.notifications.twilio_auth_token,
                from_number=config.notifications.twilio_phone_number
            )
            self.providers.append(sms_provider)

        # Webhook provider for platform integration
        if hasattr(config, 'platform_webhook_url') and config.platform_webhook_url:
            webhook_provider = WebhookProvider(
                webhook_url=f"{config.platform_webhook_url}/notifications",
                secret_key=getattr(config, 'platform_webhook_secret', None)
            )
            self.providers.append(webhook_provider)

    async def send_notification(self, request: NotificationRequest) -> bool:
        """Send notification using appropriate provider."""
        try:
            # Get template
            template = self.templates.get(request.template_name)
            if not template:
                raise BillingError(f"Template not found: {request.template_name}")

            # Render template
            subject, body = template.render(request.variables)

            # Find appropriate provider
            provider = self._find_provider(request.notification_type)
            if not provider:
                raise BillingError(f"No provider available for {request.notification_type.value}")

            # Send notification
            success = await provider.send(request, subject, body)

            if success:
                logger.info(f"Notification sent successfully: {request.template_name} to {request.recipient}")
            else:
                logger.error(f"Failed to send notification: {request.template_name} to {request.recipient}")

            return success

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    async def send_invoice_notification(self, tenant_id: str, recipient: str, invoice_data: Dict[str, Any]) -> bool:
        """Send invoice created notification."""
        request = NotificationRequest(
            recipient=recipient,
            template_name="invoice_created",
            variables=invoice_data,
            notification_type=NotificationType.EMAIL,
            tenant_id=tenant_id
        )
        return await self.send_notification(request)

    async def send_payment_notification(self, tenant_id: str, recipient: str, payment_data: Dict[str, Any], success: bool) -> bool:
        """Send payment notification."""
        template_name = "payment_successful" if success else "payment_failed"
        request = NotificationRequest(
            recipient=recipient,
            template_name=template_name,
            variables=payment_data,
            notification_type=NotificationType.EMAIL,
            tenant_id=tenant_id
        )
        return await self.send_notification(request)

    async def send_dunning_notification(self, tenant_id: str, recipient: str, dunning_data: Dict[str, Any],
                                      use_sms: bool = False) -> bool:
        """Send dunning notification."""
        notification_type = NotificationType.SMS if use_sms else NotificationType.EMAIL
        template_name = "account_suspended" if use_sms else "dunning_reminder"

        request = NotificationRequest(
            recipient=recipient,
            template_name=template_name,
            variables=dunning_data,
            notification_type=notification_type,
            priority=NotificationPriority.HIGH,
            tenant_id=tenant_id
        )
        return await self.send_notification(request)

    def _find_provider(self, notification_type: NotificationType) -> Optional[NotificationProvider]:
        """Find provider that supports the notification type."""
        for provider in self.providers:
            if provider.supports_type(notification_type):
                return provider
        return None

    def add_provider(self, provider: NotificationProvider):
        """Add a custom notification provider."""
        self.providers.append(provider)

    def add_template(self, template: NotificationTemplate):
        """Add a custom notification template."""
        self.templates[template.name] = template


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get global notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def set_notification_service(service: NotificationService):
    """Set global notification service instance."""
    global _notification_service
    _notification_service = service
