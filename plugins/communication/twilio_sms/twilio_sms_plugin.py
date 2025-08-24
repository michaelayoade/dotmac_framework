"""
Twilio SMS Plugin

Example plugin implementation showing the plugin architecture.
This plugin can be distributed separately and loaded at runtime.
"""

import aiohttp
import asyncio
import time
from typing import Dict, Any
from urllib.parse import parse_qs

# Import from the plugin system
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[3]))

from shared.communication.plugin_system import PluginInterface, PluginManifest


class TwilioSMSPlugin(PluginInterface):
    """Twilio SMS plugin implementation."""
    
    async def initialize(self) -> bool:
        """Initialize Twilio plugin."""
        try:
            # Extract configuration
            self.account_sid = self.config.get("account_sid")
            self.auth_token = self.config.get("auth_token")
            self.from_number = self.config.get("from_number")
            self.webhook_url = self.config.get("webhook_url")
            self.max_retries = self.config.get("max_retries", 3)
            self.timeout = self.config.get("timeout_seconds", 30)
            
            # Validate configuration
            if not await self.validate_config():
                return False
            
            # Test API connection
            if not await self._test_connection():
                return False
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Twilio plugin initialization failed: {e}")
            return False
    
    async def validate_config(self) -> bool:
        """Validate Twilio configuration."""
        required_fields = ["account_sid", "auth_token", "from_number"]
        
        for field in required_fields:
            if not self.config.get(field):
                print(f"Missing required Twilio configuration: {field}")
                return False
        
        return True
    
    async def send_message(self, recipient: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send SMS via Twilio."""
        start_time = time.time()
        
        try:
            # Twilio API endpoint
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            
            # Message data
            data = {
                "From": self.from_number,
                "To": recipient,
                "Body": content
            }
            
            # Add webhook for delivery receipts if configured
            if self.webhook_url:
                data["StatusCallback"] = self.webhook_url
            
            # Add custom metadata
            if metadata:
                # Twilio supports custom parameters
                for key, value in metadata.items():
                    if key.startswith("custom_"):
                        data[key] = str(value)
            
            # Send request with retry logic
            result = await self._send_with_retry(url, data)
            
            delivery_time = (time.time() - start_time) * 1000
            
            if result.get("success"):
                return {
                    "success": True,
                    "message_id": result.get("sid"),
                    "delivery_time_ms": delivery_time,
                    "provider": "twilio",
                    "metadata": {
                        "status": result.get("status"),
                        "price": result.get("price"),
                        "price_unit": result.get("price_unit")
                    }
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown Twilio error"),
                    "delivery_time_ms": delivery_time,
                    "provider": "twilio"
                }
                
        except Exception as e:
            delivery_time = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": str(e),
                "delivery_time_ms": delivery_time,
                "provider": "twilio"
            }
    
    async def _send_with_retry(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send message with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, data=data, auth=auth) as response:
                        response_data = await response.json()
                        
                        if response.status == 201:
                            return {
                                "success": True,
                                "sid": response_data.get("sid"),
                                "status": response_data.get("status"),
                                "price": response_data.get("price"),
                                "price_unit": response_data.get("price_unit")
                            }
                        else:
                            last_error = response_data.get("message", f"HTTP {response.status}")
                            
                            # Don't retry on client errors
                            if 400 <= response.status < 500:
                                break
                                
            except asyncio.TimeoutError:
                last_error = "Request timeout"
            except Exception as e:
                last_error = str(e)
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return {
            "success": False,
            "error": f"Failed after {self.max_retries} attempts. Last error: {last_error}"
        }
    
    async def _test_connection(self) -> bool:
        """Test Twilio API connection."""
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}.json"
            auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, auth=auth) as response:
                    if response.status == 200:
                        return True
                    else:
                        print(f"Twilio connection test failed: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"Twilio connection test error: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Twilio plugin health."""
        base_health = await super().health_check()
        
        # Add Twilio-specific health info
        try:
            connection_ok = await self._test_connection()
            base_health.update({
                "connection_status": "ok" if connection_ok else "failed",
                "account_sid": self.account_sid[:8] + "..." if self.account_sid else None,
                "from_number": self.from_number
            })
        except Exception as e:
            base_health["connection_error"] = str(e)
        
        return base_health
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Twilio webhook (delivery receipts, inbound messages)."""
        try:
            # Parse Twilio form data
            if isinstance(webhook_data.get("body"), bytes):
                parsed_data = parse_qs(webhook_data["body"].decode())
                data = {k: v[0] if v else "" for k, v in parsed_data.items()}
            else:
                data = webhook_data
            
            # Process webhook
            webhook_type = "delivery_receipt" if data.get("MessageStatus") else "inbound_message"
            
            return {
                "webhook_type": webhook_type,
                "message_sid": data.get("MessageSid", data.get("SmsSid")),
                "from": data.get("From"),
                "to": data.get("To"),
                "status": data.get("MessageStatus", data.get("SmsStatus")),
                "body": data.get("Body"),
                "timestamp": data.get("DateSent"),
                "provider": "twilio",
                "raw_data": data
            }
            
        except Exception as e:
            return {
                "error": f"Webhook processing failed: {e}",
                "provider": "twilio"
            }
    
    def get_required_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for this plugin."""
        return {
            "type": "object",
            "required": ["account_sid", "auth_token", "from_number"],
            "properties": {
                "account_sid": {
                    "type": "string",
                    "description": "Twilio Account SID",
                    "pattern": "^AC[a-zA-Z0-9]{32}$"
                },
                "auth_token": {
                    "type": "string", 
                    "description": "Twilio Auth Token",
                    "minLength": 32
                },
                "from_number": {
                    "type": "string",
                    "description": "Twilio phone number in E.164 format",
                    "pattern": "^\\+[1-9]\\d{1,14}$"
                },
                "webhook_url": {
                    "type": "string",
                    "description": "URL for delivery receipt webhooks",
                    "format": "uri"
                },
                "max_retries": {
                    "type": "integer",
                    "description": "Maximum retry attempts",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 3
                },
                "timeout_seconds": {
                    "type": "integer", 
                    "description": "Request timeout in seconds",
                    "minimum": 5,
                    "maximum": 120,
                    "default": 30
                }
            }
        }