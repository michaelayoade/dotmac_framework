"""
Twilio SMS Provider

Implements the universal channel provider interface for Twilio SMS.
This eliminates hardcoded "twilio" checks throughout the codebase.
"""

import aiohttp
import time
from typing import Dict, Any, Optional
from urllib.parse import parse_qs

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
class TwilioSMSProvider(BaseChannelProvider):
    """Twilio SMS communication provider."""
    
    @property
    def provider_name(self) -> str:
        return "twilio_sms"
    
    @property
    def channel_type(self) -> str:
        return "sms"
    
    def __init__(self, config: ChannelConfiguration):
        """Initialize Twilio SMS provider."""
        super().__init__(config)
        
        # Set capabilities this provider supports
        self._capabilities = [
            ChannelCapability.TEXT_MESSAGING,
            ChannelCapability.DELIVERY_RECEIPTS,
            ChannelCapability.TWO_WAY_MESSAGING,
            ChannelCapability.WEBHOOK_SUPPORT,
            ChannelCapability.TEMPLATE_MESSAGING,
            ChannelCapability.BULK_MESSAGING
        ]
        
        # Extract Twilio configuration
        self.account_sid = config.config.get("account_sid")
        self.auth_token = config.config.get("auth_token") 
        self.from_number = config.config.get("from_number")
        
        # Template storage
        self._templates = {
            "welcome": "Welcome {name}! Your DotMac account is now active.",
            "payment_due": "Hi {name}, your payment of ${amount} is due. Please pay to avoid service interruption.",
            "verification": "Your verification code is: {code}",
            "alert": "Alert: {message}",
            "service_outage": "Service Notice: {message}. ETA: {eta}",
            "password_reset": "Password reset code: {code}. Expires in 10 minutes.",
            "account_suspended": "Account suspended: {reason}. Contact support: {support_phone}",
            "payment_received": "Payment received: ${amount}. Thank you!"
        }
    
    async def validate_configuration(self) -> bool:
        """Validate Twilio configuration."""
        required_fields = ["account_sid", "auth_token", "from_number"]
        
        for field in required_fields:
            if not self.config.config.get(field):
                logger.error(f"Missing required Twilio field: {field}")
                return False
        
        # Test API credentials
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}.json"
            auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, auth=auth) as response:
                    if response.status == 200:
                        logger.info("Twilio credentials validated successfully")
                        return True
                    else:
                        logger.error(f"Twilio credential validation failed: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error validating Twilio credentials: {e}")
            return False
    
    async def initialize(self) -> bool:
        """Initialize the Twilio provider."""
        if not await self.validate_configuration():
            return False
        
        self._is_initialized = True
        logger.info("Twilio SMS provider initialized successfully")
        return True
    
    async def send_message(self, message: Message) -> DeliveryResult:
        """Send SMS via Twilio."""
        start_time = time.time()
        
        try:
            # Build message content
            content = self._build_message_content(message)
            
            # Twilio API endpoint
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            
            # Message data
            data = {
                "From": self.from_number,
                "To": message.recipient,
                "Body": content
            }
            
            # Add additional Twilio-specific options
            if message.metadata.get("status_callback"):
                data["StatusCallback"] = message.metadata["status_callback"]
            
            # Send request
            auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, auth=auth) as response:
                    response_data = await response.model_dump_json()
                    delivery_time = (time.time() - start_time) * 1000
                    
                    if response.status == 201:
                        return DeliveryResult(
                            success=True,
                            provider_message_id=response_data.get("sid"),
                            delivery_time_ms=delivery_time,
                            provider_response=response_data
                        )
                    else:
                        return DeliveryResult(
                            success=False,
                            error_message=f"Twilio error: {response_data.get('message', 'Unknown error')}",
                            delivery_time_ms=delivery_time,
                            provider_response=response_data
                        )
                        
        except Exception as e:
            delivery_time = (time.time() - start_time) * 1000
            logger.error(f"Twilio SMS send failed: {e}")
            
            return DeliveryResult(
                success=False,
                error_message=str(e),
                delivery_time_ms=delivery_time
            )
    
    def _build_message_content(self, message: Message) -> str:
        """Build message content from template or direct content."""
        if message.template_name and message.template_name in self._templates:
            template = self._templates[message.template_name]
            try:
                return template.format(**message.template_vars)
            except KeyError as e:
                logger.warning(f"Missing template variable {e}, using fallback")
                return message.content
        
        return message.content
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle Twilio SMS webhook (delivery receipts, inbound messages)."""
        try:
            # Parse Twilio webhook data (form-encoded)
            if isinstance(webhook_data.get("body"), bytes):
                parsed_data = parse_qs(webhook_data["body"].decode()
                
                # Convert to single values
                data = {k: v[0] if v else "" for k, v in parsed_data.items()}
            else:
                data = webhook_data
            
            # Extract key information
            result = {
                "provider": self.provider_name,
                "webhook_type": self._determine_webhook_type(data),
                "message_sid": data.get("MessageSid", data.get("SmsSid"),
                "from": data.get("From"),
                "to": data.get("To"), 
                "body": data.get("Body"),
                "status": data.get("MessageStatus", data.get("SmsStatus"),
                "timestamp": data.get("DateSent"),
                "raw_data": data
            }
            
            logger.info(f"Processed Twilio webhook: {result['webhook_type']}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing Twilio webhook: {e}")
            return None
    
    def _determine_webhook_type(self, data: Dict[str, Any]) -> str:
        """Determine the type of webhook from Twilio."""
        if data.get("Body") and data.get("From"):
            return "inbound_message"
        elif data.get("MessageStatus") or data.get("SmsStatus"):
            return "delivery_receipt"
        else:
            return "unknown"
    
    async def get_delivery_status(self, provider_message_id: str) -> Optional[str]:
        """Get delivery status for a message from Twilio."""
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages/{provider_message_id}.json"
            auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, auth=auth) as response:
                    if response.status == 200:
                        data = await response.model_dump_json()
                        return data.get("status")
                    else:
                        logger.error(f"Failed to get message status: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting Twilio message status: {e}")
            return None