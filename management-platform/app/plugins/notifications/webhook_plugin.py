"""
Webhook notification channel plugin.
"""

import logging
import json
from typing import Dict, Any, List
import aiohttp
import asyncio

from ...core.plugins.interfaces import NotificationChannelPlugin
from ...core.plugins.base import PluginMeta, PluginType

logger = logging.getLogger(__name__)


class WebhookNotificationPlugin(NotificationChannelPlugin):
    """Webhook notification channel implementation."""
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="webhook_notification",
            version="1.0.0",
            plugin_type=PluginType.NOTIFICATION_CHANNEL,
            description="HTTP webhook notification delivery",
            author="DotMac Platform",
            configuration_schema={
                "webhook_url": {"type": "string", "required": True},
                "http_method": {"type": "string", "default": "POST", "enum": ["POST", "PUT", "PATCH"]},
                "headers": {"type": "object", "default": {"Content-Type": "application/json"}},
                "timeout": {"type": "integer", "default": 30},
                "retry_attempts": {"type": "integer", "default": 3},
                "retry_delay": {"type": "integer", "default": 5},
                "verify_ssl": {"type": "boolean", "default": True},
                "auth_header": {"type": "string", "required": False, "sensitive": True}
            }
        )
    
    async def initialize(self) -> bool:
        """Initialize webhook plugin."""
        try:
            # Validate configuration
            if 'webhook_url' not in self.config:
                raise ValueError("Missing required configuration: webhook_url")
            
            # Test webhook connection
            await self._test_webhook_connection()
            return True
            
        except Exception as e:
            self.log_error(e, "initialization")
            return False
    
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate webhook plugin configuration."""
        try:
            if 'webhook_url' not in config:
                logger.error("Missing required configuration key: webhook_url")
                return False
            
            # Validate URL format
            url = config['webhook_url']
            if not (url.startswith('http://') or url.startswith('https://')):
                logger.error(f"Invalid webhook URL format: {url}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            await self._test_webhook_connection()
            return {
                "status": "healthy",
                "webhook_url": self.config.get("webhook_url"),
                "connection": "ok",
                "response_time": "< 1s"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "webhook_url": self.config.get("webhook_url")
            }
    
    async def send_notification(self, message: str, recipients: List[str], options: Dict[str, Any] = None) -> bool:
        """Send notification via webhook."""
        try:
            payload = {
                "message": message,
                "recipients": recipients,
                "timestamp": self._get_timestamp(),
                "source": "dotmac_platform",
                "type": "notification"
            }
            
            # Add any additional options
            if options:
                payload.update(options)
            
            return await self._send_webhook_request(payload)
            
        except Exception as e:
            self.log_error(e, "send_notification")
            return False
    
    async def send_alert(self, alert_data: Dict[str, Any], recipients: List[str]) -> bool:
        """Send alert notification."""
        try:
            payload = {
                "alert": alert_data,
                "recipients": recipients,
                "timestamp": self._get_timestamp(),
                "source": "dotmac_platform",
                "type": "alert",
                "severity": alert_data.get("severity", "medium")
            }
            
            return await self._send_webhook_request(payload)
            
        except Exception as e:
            self.log_error(e, "send_alert")
            return False
    
    async def send_digest(self, digest_data: Dict[str, Any], recipients: List[str]) -> bool:
        """Send digest notification."""
        try:
            payload = {
                "digest": digest_data,
                "recipients": recipients,
                "timestamp": self._get_timestamp(),
                "source": "dotmac_platform",
                "type": "digest"
            }
            
            return await self._send_webhook_request(payload)
            
        except Exception as e:
            self.log_error(e, "send_digest")
            return False
    
    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient format for webhook channel."""
        # For webhooks, recipients can be any string identifiers
        return bool(recipient and recipient.strip())
    
    def get_channel_type(self) -> str:
        """Return channel identifier."""
        return "webhook"
    
    def get_supported_message_types(self) -> List[str]:
        """Return supported message types."""
        return ["json", "text", "structured"]
    
    async def _test_webhook_connection(self) -> None:
        """Test webhook connection."""
        test_payload = {
            "test": True,
            "message": "Connection test from DotMac Platform",
            "timestamp": self._get_timestamp()
        }
        
        timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", 30))
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = self.config.get("headers", {"Content-Type": "application/json"})
            
            # Add auth header if configured
            if "auth_header" in self.config:
                headers["Authorization"] = self.config["auth_header"]
            
            async with session.request(
                method=self.config.get("http_method", "POST"),
                url=self.config["webhook_url"],
                json=test_payload,
                headers=headers,
                ssl=self.config.get("verify_ssl", True)
            ) as response:
                if response.status >= 400:
                    raise Exception(f"Webhook test failed: {response.status} {response.reason}")
    
    async def _send_webhook_request(self, payload: Dict[str, Any]) -> bool:
        """Send webhook request with retry logic."""
        retry_attempts = self.config.get("retry_attempts", 3)
        retry_delay = self.config.get("retry_delay", 5)
        
        for attempt in range(retry_attempts):
            try:
                await self._make_webhook_request(payload)
                return True
                
            except Exception as e:
                logger.warning(f"Webhook attempt {attempt + 1} failed: {e}")
                if attempt < retry_attempts - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise
        
        return False
    
    async def _make_webhook_request(self, payload: Dict[str, Any]) -> None:
        """Make the actual webhook HTTP request."""
        timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", 30))
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = self.config.get("headers", {"Content-Type": "application/json"})
            
            # Add auth header if configured
            if "auth_header" in self.config:
                headers["Authorization"] = self.config["auth_header"]
            
            async with session.request(
                method=self.config.get("http_method", "POST"),
                url=self.config["webhook_url"],
                json=payload,
                headers=headers,
                ssl=self.config.get("verify_ssl", True)
            ) as response:
                if response.status >= 400:
                    response_text = await response.text()
                    raise Exception(f"Webhook request failed: {response.status} {response.reason} - {response_text}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()