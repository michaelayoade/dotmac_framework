"""SMS communication channel plugin using Twilio."""

import asyncio
from typing import Dict, List, Optional, Any

from .base import BaseChannelPlugin, ChannelMessage, ChannelConfig, ChannelCapability
from .registry import register_channel_plugin
from . import channel_registry


@register_channel_plugin(channel_registry)
class SMSChannelPlugin(BaseChannelPlugin):
    """SMS communication channel plugin."""

    @property
    def channel_id(self) -> str:
        return "sms"

    @property
    def channel_name(self) -> str:
        return "SMS"

    @property
    def capabilities(self) -> List[ChannelCapability]:
        return [
            ChannelCapability.SEND_MESSAGE,
            ChannelCapability.RECEIVE_MESSAGE,
            ChannelCapability.WEBHOOK_SUPPORT,
        ]

    @property
    def required_config_fields(self) -> List[str]:
        return ["account_sid", "auth_token", "phone_number"]

    def _get_config_value(self, key: str, default=None):
        """Get configuration value from config or additional_settings."""
        return getattr(self.config, key, None) or self.config.additional_settings.get(
            key, default
        )

    async def initialize(self) -> bool:
        """Initialize Twilio client."""
        try:
            # Try importing Twilio (optional dependency)
            try:
                from twilio.rest import Client

                self._twilio_available = True
            except ImportError:
                print("Twilio library not available. SMS plugin running in mock mode.")
                self._twilio_available = False
                return True  # Still initialize in mock mode

            account_sid = self._get_config_value("account_sid")
            auth_token = self._get_config_value("auth_token")

            if self._twilio_available:
                self.client = Client(account_sid, auth_token)
                # Test connection by fetching account info
                account = self.client.api.accounts(account_sid).fetch()

            self.is_initialized = True
            return True

        except Exception as e:
            print(f"SMS plugin initialization failed: {e}")
            return False

    async def send_message(self, message: ChannelMessage) -> Dict[str, Any]:
        """Send SMS message."""
        try:
            if not self._twilio_available:
                # Mock response for testing
                return {
                    "success": True,
                    "message_id": f"mock_sms_{hash(message.content)}",
                    "delivery_status": "sent",
                    "mock": True,
                }

            phone_number = self._get_config_value("phone_number")

            message_obj = self.client.messages.create(
                body=message.content, from_=phone_number, to=message.recipient_id
            )

            return {
                "success": True,
                "message_id": message_obj.sid,
                "delivery_status": message_obj.status,
                "cost": str(message_obj.price) if message_obj.price else None,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "delivery_status": "failed"}

    async def receive_message(
        self, webhook_data: Dict[str, Any]
    ) -> Optional[ChannelMessage]:
        """Process incoming SMS webhook from Twilio."""
        try:
            return ChannelMessage(
                content=webhook_data.get("Body", ""),
                message_type="text",
                sender_id=webhook_data.get("From", ""),
                recipient_id=webhook_data.get("To", ""),
                channel_specific_data=webhook_data,
                metadata={
                    "message_sid": webhook_data.get("MessageSid", ""),
                    "account_sid": webhook_data.get("AccountSid", ""),
                    "num_media": webhook_data.get("NumMedia", "0"),
                },
            )
        except Exception:
            return None

    async def get_delivery_status(self, message_id: str) -> str:
        """Get SMS delivery status from Twilio."""
        if not self._twilio_available:
            return "delivered"  # Mock status

        try:
            message = self.client.messages(message_id).fetch()
            return message.status
        except Exception:
            return "unknown"

    async def validate_recipient(self, recipient_id: str) -> bool:
        """Validate phone number format."""
        import re

        # Basic international phone number validation
        pattern = r"^\+[1-9]\d{1,14}$"
        return re.match(pattern, recipient_id) is not None
