"""
Universal Email Provider

Supports multiple email backends (SMTP, SendGrid, SES, etc.) through
configuration without hardcoded provider checks.
"""

import aiosmtplib
import aiohttp
import time
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

from ..channel_provider_registry import (
    BaseChannelProvider,
    ChannelConfiguration,
    Message,
    DeliveryResult,
    ChannelCapability,
    MessageType,
    register_provider
)
import logging

logger = logging.getLogger(__name__)


@register_provider
class UniversalEmailProvider(BaseChannelProvider):
    """Universal email provider supporting multiple backends."""
    
    @property
    def provider_name(self) -> str:
        return f"{self._backend}_email"
    
    @property
    def channel_type(self) -> str:
        return "email"
    
    def __init__(self, config: ChannelConfiguration):
        """Initialize email provider."""
        super().__init__(config)
        
        # Set capabilities
        self._capabilities = [
            ChannelCapability.RICH_MESSAGING,
            ChannelCapability.FILE_ATTACHMENTS,
            ChannelCapability.DELIVERY_RECEIPTS,
            ChannelCapability.TEMPLATE_MESSAGING,
            ChannelCapability.BULK_MESSAGING
        ]
        
        # Determine backend from config
        self._backend = config.config.get("backend", "smtp")
        
        # Common configuration
        self.from_email = config.config.get("from_email")
        self.from_name = config.config.get("from_name", "DotMac Platform")
        
        # Backend-specific configuration
        if self._backend == "smtp":
            self.smtp_host = config.config.get("smtp_host")
            self.smtp_port = config.config.get("smtp_port", 587)
            self.smtp_user = config.config.get("smtp_user")
            self.smtp_password = config.config.get("smtp_password")
            self.use_tls = config.config.get("use_tls", True)
            
        elif self._backend == "sendgrid":
            self.sendgrid_api_key = config.config.get("sendgrid_api_key")
            
        elif self._backend == "ses":
            self.aws_access_key = config.config.get("aws_access_key")
            self.aws_secret_key = config.config.get("aws_secret_key")
            self.aws_region = config.config.get("aws_region", "us-east-1")
        
        # Email templates
        self._templates = {
            "welcome": {
                "subject": "Welcome to DotMac - {name}",
                "html": """
                <h2>Welcome {name}!</h2>
                <p>Your DotMac account has been activated successfully.</p>
                <p>You can now access your services at: <a href="{portal_url}">{portal_url}</a></p>
                <p>If you need assistance, contact our support team.</p>
                """,
                "text": "Welcome {name}! Your DotMac account is active. Access: {portal_url}"
            },
            "password_reset": {
                "subject": "Password Reset - DotMac Account",
                "html": """
                <h2>Password Reset Request</h2>
                <p>Hi {name},</p>
                <p>Click the link below to reset your password:</p>
                <p><a href="{reset_url}">Reset Password</a></p>
                <p>This link expires in 1 hour.</p>
                """,
                "text": "Password reset link: {reset_url} (expires in 1 hour)"
            },
            "service_alert": {
                "subject": "Service Alert - {service_name}",
                "html": """
                <h2>Service Alert</h2>
                <p><strong>Service:</strong> {service_name}</p>
                <p><strong>Status:</strong> {status}</p>
                <p><strong>Message:</strong> {message}</p>
                <p><strong>Time:</strong> {timestamp}</p>
                """,
                "text": "Alert: {service_name} - {status}. {message} at {timestamp}"
            },
            "payment_confirmation": {
                "subject": "Payment Confirmation - ${amount}",
                "html": """
                <h2>Payment Received</h2>
                <p>Thank you {name}!</p>
                <p>We've received your payment of <strong>${amount}</strong></p>
                <p><strong>Transaction ID:</strong> {transaction_id}</p>
                <p>Your services will continue uninterrupted.</p>
                """,
                "text": "Payment received: ${amount}. Transaction ID: {transaction_id}"
            }
        }
    
    async def validate_configuration(self) -> bool:
        """Validate email configuration based on backend."""
        if not self.from_email:
            logger.error("Missing required field: from_email")
            return False
        
        if self._backend == "smtp":
            required_fields = ["smtp_host", "smtp_user", "smtp_password"]
            for field in required_fields:
                if not getattr(self, field, None):
                    logger.error(f"Missing required SMTP field: {field}")
                    return False
                    
        elif self._backend == "sendgrid":
            if not self.sendgrid_api_key:
                logger.error("Missing required SendGrid API key")
                return False
                
        elif self._backend == "ses":
            required_fields = ["aws_access_key", "aws_secret_key"]
            for field in required_fields:
                if not getattr(self, field, None):
                    logger.error(f"Missing required AWS field: {field}")
                    return False
        
        return True
    
    async def initialize(self) -> bool:
        """Initialize the email provider."""
        if not await self.validate_configuration():
            return False
        
        # Test connection based on backend
        try:
            if self._backend == "smtp":
                await self._test_smtp_connection()
            elif self._backend == "sendgrid":
                await self._test_sendgrid_connection()
            elif self._backend == "ses":
                await self._test_ses_connection()
            
            self._is_initialized = True
            logger.info(f"Email provider initialized successfully: {self._backend}")
            return True
            
        except Exception as e:
            logger.error(f"Email provider initialization failed: {e}")
            return False
    
    async def send_message(self, message: Message) -> DeliveryResult:
        """Send email via configured backend."""
        start_time = time.time()
        
        try:
            # Build email content
            email_data = self._build_email_content(message)
            
            # Send via appropriate backend
            if self._backend == "smtp":
                result = await self._send_via_smtp(email_data)
            elif self._backend == "sendgrid":
                result = await self._send_via_sendgrid(email_data)
            elif self._backend == "ses":
                result = await self._send_via_ses(email_data)
            else:
                raise ValueError(f"Unsupported email backend: {self._backend}")
            
            delivery_time = (time.time() - start_time) * 1000
            result.delivery_time_ms = delivery_time
            
            return result
            
        except Exception as e:
            delivery_time = (time.time() - start_time) * 1000
            logger.error(f"Email send failed: {e}")
            
            return DeliveryResult(
                success=False,
                error_message=str(e),
                delivery_time_ms=delivery_time
            )
    
    def _build_email_content(self, message: Message) -> Dict[str, Any]:
        """Build email content from template or direct content."""
        if message.template_name and message.template_name in self._templates:
            template = self._templates[message.template_name]
            
            try:
                return {
                    "to": message.recipient,
                    "subject": template["subject"].format(**message.template_vars),
                    "html_content": template["html"].format(**message.template_vars),
                    "text_content": template["text"].format(**message.template_vars)
                }
            except KeyError as e:
                logger.warning(f"Missing template variable {e}, using fallback")
        
        # Fallback to direct content
        return {
            "to": message.recipient,
            "subject": message.metadata.get("subject", "Notification"),
            "html_content": f"<p>{message.content}</p>",
            "text_content": message.content
        }
    
    async def _send_via_smtp(self, email_data: Dict[str, Any]) -> DeliveryResult:
        """Send email via SMTP."""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = email_data["to"]
            message["Subject"] = email_data["subject"]
            
            # Add content
            text_part = MIMEText(email_data["text_content"], "plain")
            html_part = MIMEText(email_data["html_content"], "html")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=self.use_tls
            )
            
            return DeliveryResult(
                success=True,
                provider_message_id=f"smtp_{int(time.time())}"
            )
            
        except Exception as e:
            return DeliveryResult(
                success=False,
                error_message=f"SMTP error: {e}"
            )
    
    async def _send_via_sendgrid(self, email_data: Dict[str, Any]) -> DeliveryResult:
        """Send email via SendGrid API."""
        try:
            url = "https://api.sendgrid.com/v3/mail/send"
            
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "personalizations": [{
                    "to": [{"email": email_data["to"]}],
                    "subject": email_data["subject"]
                }],
                "from": {
                    "email": self.from_email,
                    "name": self.from_name
                },
                "content": [
                    {
                        "type": "text/plain",
                        "value": email_data["text_content"]
                    },
                    {
                        "type": "text/html", 
                        "value": email_data["html_content"]
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 202:
                        # SendGrid returns 202 for successful sends
                        message_id = response.headers.get("X-Message-Id", f"sg_{int(time.time())}")
                        return DeliveryResult(
                            success=True,
                            provider_message_id=message_id
                        )
                    else:
                        error_data = await response.text()
                        return DeliveryResult(
                            success=False,
                            error_message=f"SendGrid error: {response.status} - {error_data}"
                        )
                        
        except Exception as e:
            return DeliveryResult(
                success=False,
                error_message=f"SendGrid error: {e}"
            )
    
    async def _send_via_ses(self, email_data: Dict[str, Any]) -> DeliveryResult:
        """Send email via AWS SES."""
        # AWS SES implementation would go here
        # This is a placeholder for the complete implementation
        return DeliveryResult(
            success=False,
            error_message="AWS SES implementation not yet available"
        )
    
    async def _test_smtp_connection(self):
        """Test SMTP connection."""
        async with aiosmtplib.SMTP(hostname=self.smtp_host, port=self.smtp_port) as server:
            if self.use_tls:
                await server.starttls()
            await server.login(self.smtp_user, self.smtp_password)
    
    async def _test_sendgrid_connection(self):
        """Test SendGrid connection."""
        url = "https://api.sendgrid.com/v3/user/profile"
        headers = {"Authorization": f"Bearer {self.sendgrid_api_key}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"SendGrid connection test failed: {response.status}")
    
    async def _test_ses_connection(self):
        """Test AWS SES connection."""
        # AWS SES connection test would go here
        pass