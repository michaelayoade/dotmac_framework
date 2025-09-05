"""
Twilio SMS Plugin for Omnichannel Service

Proper implementation using DotMac plugin system architecture.
Provides SMS and WhatsApp communication through Twilio API.

Author: DotMac Framework Team
License: MIT
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from dotmac_plugins.adapters.communication import (
    BulkMessageResult,
    Message,
    MessageResult,
    MessageStatus,
)
from dotmac_plugins.core.plugin_base import PluginMetadata

from ..integrations.plugin_system_integration import OmnichannelCommunicationPlugin
from ..models.enums import ChannelType

logger = logging.getLogger(__name__)


class TwilioSMSPlugin(OmnichannelCommunicationPlugin):
    """
    Twilio SMS communication plugin following DotMac plugin architecture

    Provides SMS and WhatsApp messaging capabilities through Twilio API
    with proper plugin system integration.
    """

    def __init__(self, metadata: PluginMetadata, config: dict[str, Any]):
        """Initialize Twilio SMS plugin"""
        super().__init__(metadata, config)

        # Twilio-specific configuration
        self.account_sid = config.get("account_sid")
        self.auth_token = config.get("auth_token")
        self.from_number = config.get("from_number")
        self.webhook_url = config.get("webhook_url")

        # API settings
        self.base_url = "https://api.twilio.com/2010-04-01"
        self.timeout = config.get("timeout", 30)

        # Plugin metadata
        self.channel_type = ChannelType.SMS
        self.supports_interactions = True
        self.supports_agent_assignment = True
        self.max_concurrent_messages = config.get("max_concurrent_messages", 100)

        # Validation
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError(
                "Missing required Twilio configuration: account_sid, auth_token, from_number"
            )

    async def initialize(self) -> bool:
        """Initialize Twilio SMS plugin"""
        try:
            # Test Twilio credentials
            if await self._test_twilio_connection():
                self.enabled = True
                logger.info("Twilio SMS plugin initialized successfully")
                return True
            else:
                logger.error(
                    "Twilio SMS plugin initialization failed - invalid credentials"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to initialize Twilio SMS plugin: {e}")
            return False

    async def send_message(self, message: Message) -> MessageResult:
        """Send SMS message via Twilio"""
        try:
            # Build Twilio API request
            message_data = {
                "From": self.from_number,
                "To": message.recipient,
                "Body": message.content,
            }

            # Add status callback if configured
            if self.webhook_url:
                message_data["StatusCallback"] = self.webhook_url

            # Handle WhatsApp messages
            if message.metadata and message.metadata.get("channel_type") == "whatsapp":
                if not message.recipient.startswith("whatsapp:"):
                    message_data["To"] = f"whatsapp:{message.recipient}"
                if not self.from_number.startswith("whatsapp:"):
                    message_data["From"] = f"whatsapp:{self.from_number}"

            # Send via Twilio API
            auth = (self.account_sid, self.auth_token)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/Accounts/{self.account_sid}/Messages.json",
                    data=message_data,
                    auth=auth,
                    timeout=self.timeout,
                )

                if response.status_code == 201:
                    result_data = await response.json()

                    return MessageResult(
                        success=True,
                        message_id=result_data.get("sid"),
                        status=MessageStatus.SENT,
                        provider_response=result_data,
                        sent_at=datetime.now(timezone.utc).isoformat(),
                        metadata={
                            "provider": "twilio",
                            "channel_type": self.channel_type.value,
                            "price": result_data.get("price"),
                            "price_unit": result_data.get("price_unit"),
                            "twilio_status": result_data.get("status"),
                            "direction": result_data.get("direction"),
                        },
                    )
                else:
                    error_data = await response.json() if response.text else {}

                    error_message = (
                        f"Twilio API error: {response.status_code} - "
                        f"{error_data.get('message', 'Unknown error')}"
                    )
                    return MessageResult(
                        success=False,
                        status=MessageStatus.FAILED,
                        error_message=error_message,
                        provider_response=error_data,
                        metadata={
                            "provider": "twilio",
                            "channel_type": self.channel_type.value,
                            "status_code": response.status_code,
                        },
                    )

        except Exception as e:
            logger.error(f"Failed to send SMS via Twilio: {e}")
            return MessageResult(
                success=False,
                status=MessageStatus.FAILED,
                error_message=str(e),
                metadata={
                    "provider": "twilio",
                    "channel_type": self.channel_type.value,
                    "exception_type": type(e).__name__,
                },
            )

    async def send_bulk_messages(self, messages: list[Message]) -> BulkMessageResult:
        """Send multiple SMS messages"""
        try:
            results = []
            successful = 0
            failed = 0

            # Twilio doesn't have bulk API, so send individually
            for message in messages:
                result = await self.send_message(message)
                results.append(result)

                if result.success:
                    successful += 1
                else:
                    failed += 1

            return BulkMessageResult(
                total_messages=len(messages),
                successful=successful,
                failed=failed,
                results=results,
                metadata={
                    "provider": "twilio",
                    "channel_type": self.channel_type.value,
                    "bulk_method": "individual",
                },
            )

        except Exception as e:
            logger.error(f"Failed to send bulk SMS: {e}")
            return BulkMessageResult(
                total_messages=len(messages),
                successful=0,
                failed=len(messages),
                results=[],
                metadata={"provider": "twilio", "error": str(e)},
            )

    async def get_capabilities(self) -> dict[str, Any]:
        """Get Twilio SMS plugin capabilities"""
        return {
            "send_sms": True,
            "send_whatsapp": True,
            "delivery_receipts": True,
            "two_way_messaging": True,
            "media_attachments": True,  # WhatsApp only
            "bulk_messaging": True,
            "supports_priority": True,
            "max_message_length": 1600,  # SMS limit
            "supported_countries": "global",
            "rate_limit_per_second": 1,  # Twilio default
            "webhook_support": True,
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on Twilio service"""
        try:
            # Check account status
            auth = (self.account_sid, self.auth_token)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/Accounts/{self.account_sid}.json",
                    auth=auth,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    account_data = await response.json()

                    return {
                        "status": "healthy",
                        "provider": "twilio",
                        "account_status": account_data.get("status"),
                        "account_type": account_data.get("type"),
                        "from_number": self.from_number,
                        "webhook_configured": bool(self.webhook_url),
                        "current_messages": self.current_messages,
                        "max_concurrent": self.max_concurrent_messages,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "provider": "twilio",
                        "error": f"API returned {response.status_code}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

        except Exception as e:
            logger.error(f"Twilio health check failed: {e}")
            return {
                "status": "unhealthy",
                "provider": "twilio",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def handle_webhook(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle Twilio webhook for status updates"""
        try:
            events = []

            # Handle Twilio status callback
            if "MessageStatus" in payload and "MessageSid" in payload:
                events.append(
                    {
                        "type": "status_update",
                        "message_id": payload.get("MessageSid"),
                        "status": payload.get("MessageStatus"),
                        "error_code": payload.get("ErrorCode"),
                        "error_message": payload.get("ErrorMessage"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "provider": "twilio",
                        "raw_payload": payload,
                    }
                )

            # Handle incoming SMS
            elif "Body" in payload and "From" in payload:
                events.append(
                    {
                        "type": "incoming_message",
                        "from": payload.get("From"),
                        "to": payload.get("To"),
                        "content": payload.get("Body"),
                        "message_id": payload.get("MessageSid"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "provider": "twilio",
                        "channel_type": (
                            "whatsapp"
                            if payload.get("From", "").startswith("whatsapp:")
                            else "sms"
                        ),
                        "metadata": {
                            "from_city": payload.get("FromCity"),
                            "from_state": payload.get("FromState"),
                            "from_country": payload.get("FromCountry"),
                            "num_media": payload.get("NumMedia", 0),
                        },
                    }
                )

            return events

        except Exception as e:
            logger.error(f"Failed to handle Twilio webhook: {e}")
            return []

    async def get_message_status(self, message_id: str) -> Optional[dict[str, Any]]:
        """Get message delivery status from Twilio"""
        try:
            auth = (self.account_sid, self.auth_token)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/Accounts/{self.account_sid}/Messages/{message_id}.json",
                    auth=auth,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    return await response.json()
                else:
                    return None

        except Exception as e:
            logger.error(f"Failed to get Twilio message status: {e}")
            return None

    async def shutdown(self):
        """Shutdown Twilio plugin"""
        try:
            self.enabled = False
            logger.info("Twilio SMS plugin shut down")

        except Exception as e:
            logger.error(f"Error shutting down Twilio SMS plugin: {e}")

    # Private helper methods

    async def _test_twilio_connection(self) -> bool:
        """Test Twilio API connection"""
        try:
            auth = (self.account_sid, self.auth_token)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/Accounts/{self.account_sid}.json",
                    auth=auth,
                    timeout=self.timeout,
                )

                return response.status_code == 200

        except Exception as e:
            logger.error(f"Twilio connection test failed: {e}")
            return False


# Plugin factory function for registration
def create_twilio_sms_plugin(config: dict[str, Any]) -> TwilioSMSPlugin:
    """Create Twilio SMS plugin instance"""
    metadata = PluginMetadata(
        plugin_id="twilio_sms_omnichannel",
        name="Twilio SMS/WhatsApp Plugin",
        version="1.0.0",
        description="SMS and WhatsApp communication via Twilio API for omnichannel service",
        author="DotMac Framework Team",
        category="communication",
        category_data={"channel_type": "sms", "supports_whatsapp": True},
        tags=["sms", "whatsapp", "twilio", "messaging"],
        requirements=["httpx>=0.26.0"],
    )

    return TwilioSMSPlugin(metadata, config)
