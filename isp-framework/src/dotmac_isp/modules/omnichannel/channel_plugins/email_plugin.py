"""Email communication channel plugin."""

import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any

from .base import BaseChannelPlugin, ChannelMessage, ChannelConfig, ChannelCapability
from .registry import register_channel_plugin
from . import channel_registry


@register_channel_plugin(channel_registry)
class EmailChannelPlugin(BaseChannelPlugin):
    """Email communication channel plugin."""

    @property
    def channel_id(self) -> str:
        return "email"

    @property
    def channel_name(self) -> str:
        return "Email"

    @property
    def capabilities(self) -> List[ChannelCapability]:
        return [
            ChannelCapability.SEND_MESSAGE,
            ChannelCapability.FILE_ATTACHMENT,
            ChannelCapability.RICH_CONTENT,
        ]

    @property
    def required_config_fields(self) -> List[str]:
        return ["smtp_server", "smtp_port", "username", "password"]

    def _get_config_value(self, key: str, default=None):
        """Get configuration value from config or additional_settings."""
        return getattr(self.config, key, None) or self.config.additional_settings.get(
            key, default
        )

    async def initialize(self) -> bool:
        """Initialize SMTP connection."""
        try:
            smtp_server = self._get_config_value("smtp_server")
            smtp_port = int(self._get_config_value("smtp_port", 587))
            username = self._get_config_value("username")
            password = self._get_config_value("password")
            use_tls = self._get_config_value("use_tls", True)

            # Test SMTP connection
            server = smtplib.SMTP(smtp_server, smtp_port)
            if use_tls:
                server.starttls()
            server.login(username, password)
            server.quit()

            self.is_initialized = True
            return True

        except Exception as e:
            print(f"Email plugin initialization failed: {e}")
            return False

    async def send_message(self, message: ChannelMessage) -> Dict[str, Any]:
        """Send email message."""
        try:
            smtp_server = self._get_config_value("smtp_server")
            smtp_port = int(self._get_config_value("smtp_port", 587))
            username = self._get_config_value("username")
            password = self._get_config_value("password")
            use_tls = self._get_config_value("use_tls", True)

            # Create message
            msg = MIMEMultipart()
            msg["From"] = message.sender_id
            msg["To"] = message.recipient_id
            msg["Subject"] = message.metadata.get("subject", "Message from Support")

            # Add body
            if message.message_type == "html":
                msg.attach(MIMEText(message.content, "html"))
            else:
                msg.attach(MIMEText(message.content, "plain"))

            # Add attachments
            for attachment in message.attachments:
                if "path" in attachment:
                    with open(attachment["path"], "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f'attachment; filename= {attachment.get("filename", "attachment")}',
                        )
                        msg.attach(part)

            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            if use_tls:
                server.starttls()
            server.login(username, password)

            text = msg.as_string()
            server.sendmail(message.sender_id, message.recipient_id, text)
            server.quit()

            return {
                "success": True,
                "message_id": message.metadata.get("message_id", "email_sent"),
                "delivery_status": "sent",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "delivery_status": "failed"}

    async def receive_message(
        self, webhook_data: Dict[str, Any]
    ) -> Optional[ChannelMessage]:
        """Process incoming email webhook (if using service like SendGrid)."""
        try:
            return ChannelMessage(
                content=webhook_data.get("text", ""),
                message_type="text",
                sender_id=webhook_data.get("from", ""),
                recipient_id=webhook_data.get("to", ""),
                channel_specific_data=webhook_data,
                metadata={
                    "subject": webhook_data.get("subject", ""),
                    "timestamp": webhook_data.get("timestamp"),
                },
            )
        except Exception:
            return None

    async def get_delivery_status(self, message_id: str) -> str:
        """Get delivery status (basic implementation)."""
        return "delivered"  # Email doesn't typically provide real-time delivery status

    async def validate_recipient(self, recipient_id: str) -> bool:
        """Validate email address format."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, recipient_id) is not None
