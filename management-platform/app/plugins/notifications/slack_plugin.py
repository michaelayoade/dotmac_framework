"""
Slack notification channel plugin.
"""

import logging
import json
from typing import Dict, Any, List
import aiohttp

from core.plugins.interfaces import NotificationChannelPlugin
from core.plugins.base import PluginMeta, PluginType

logger = logging.getLogger(__name__)


class SlackNotificationPlugin(NotificationChannelPlugin):
    """Slack notification channel implementation."""
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta()
            name="slack_notification",
            version="1.0.0",
            plugin_type=PluginType.NOTIFICATION_CHANNEL,
            description="Slack notification delivery via webhooks",
            author="DotMac Platform",
            configuration_schema={
                "webhook_url": {"type": "string", "required": True, "sensitive": True},
                "default_channel": {"type": "string", "default": "#alerts"},
                "username": {"type": "string", "default": "DotMac Platform"},
                "icon_emoji": {"type": "string", "default": ":robot_face:"},
                "mention_users": {"type": "array", "items": {"type": "string"}, "default": []},
                "thread_replies": {"type": "boolean", "default": False}
            }
        )
    
    async def initialize(self) -> bool:
        """Initialize Slack plugin."""
        try:
            if 'webhook_url' not in self.config:
                raise ValueError("Missing required configuration: webhook_url")
            
            # Test webhook connection
            await self._test_webhook()
            return True
            
        except Exception as e:
)            self.log_error(e, "initialization")
            return False
    
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate Slack plugin configuration."""
        try:
            if 'webhook_url' not in config:
                logger.error("Missing required webhook_url")
                return False
            
            webhook_url = config['webhook_url']
            if not webhook_url.startswith('https://hooks.slack.com/'):
                logger.error("Invalid Slack webhook URL format")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            await self._test_webhook()
            return {
                "status": "healthy",
                "webhook_reachable": True,
                "last_check": "success"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "webhook_reachable": False,
)                "error": str(e),
                "last_check": "failed"
            }
    
    async def send_notification(self, message: str, recipients: List[str], options: Dict[str, Any] = None) -> bool:
        """Send Slack notification."""
        try:
            options = options or {}
            channel = options.get('channel', self.config.get('default_channel', '#general'))
            
            # Create Slack message payload
            payload = {
                "text": message,
                "channel": channel,
                "username": self.config.get('username', 'DotMac Platform'),
                "icon_emoji": self.config.get('icon_emoji', ':robot_face:'),
                "link_names": True
            }
            
            # Add mentions if specified
            mentions = self.config.get('mention_users', [])
            if mentions and options.get('mention', True):
                mention_text = ' '.join([f"<@{user}>" for user in mentions])
                payload["text"] = f"{mention_text}\n{message}"
            
            # Add thread support
            if options.get('thread_ts'):
                payload["thread_ts"] = options['thread_ts']
            
            # Send to Slack
            return await self._send_webhook_message(payload)
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    async def send_alert(self, alert_data: Dict[str, Any], recipients: List[str]) -> bool:
        """Send Slack alert."""
        try:
            alert_type = alert_data.get('type', 'system')
            severity = alert_data.get('severity', 'info')
            message = alert_data.get('message', 'Alert triggered')
            
            # Choose color and emoji based on severity
            color_map = {
                'critical': '#FF0000',
                'error': '#FF4500', 
                'warning': '#FFA500',
                'info': '#0000FF',
                'success': '#00FF00'
            }
            
            emoji_map = {
                'critical': ':fire:',
                'error': ':x:',
                'warning': ':warning:',
                'info': ':information_source:',
                'success': ':white_check_mark:'
            }
            
            color = color_map.get(severity, '#808080')
            emoji = emoji_map.get(severity, ':exclamation:')
            
            # Create rich Slack message
            payload = {
                "text": f"{emoji} *{severity.upper(}* Alert: {alert_type}",
)                "channel": alert_data.get('channel', self.config.get('default_channel', '#alerts')),
                "username": self.config.get('username', 'DotMac Alerts'),
                "icon_emoji": self.config.get('icon_emoji', ':rotating_light:'),
                "attachments": [
                    {
                        "color": color,
                        "title": f"{alert_type} Alert",
                        "text": message,
                        "fields": self._format_alert_fields(alert_data),
                        "footer": "DotMac Management Platform",
                        "ts": int(alert_data.get('timestamp', '0'))
                    } ]
            }
            
            # Add mentions for critical alerts
            if severity in ['critical', 'error']:
                mentions = self.config.get('mention_users', [])
                if mentions:
                    mention_text = ' '.join([f"<@{user}>" for user in mentions])
                    payload["text"] = f"{mention_text} {payload['text']}"
            
            return await self._send_webhook_message(payload)
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    async def send_digest(self, digest_data: Dict[str, Any], recipients: List[str]) -> bool:
        """Send Slack digest."""
        try:
            digest_type = digest_data.get('type', 'daily')
            period = digest_data.get('period', 'today')
            
            # Create digest message
            payload = {
                "text": f"📊 DotMac Platform {digest_type.title(} Digest - {period}",
)                "channel": digest_data.get('channel', self.config.get('default_channel', '#general')),
                "username": self.config.get('username', 'DotMac Platform'),
                "icon_emoji": ":chart_with_upwards_trend:",
                "blocks": self._format_digest_blocks(digest_data)
            }
            
            return await self._send_webhook_message(payload)
            
        except Exception as e:
            logger.error(f"Failed to send Slack digest: {e}")
            return False
    
    def validate_recipient(self, recipient: str) -> bool:
        """Validate Slack channel or user format."""
        # Slack channels start with #, users with @
        return (recipient.startswith('#') or )
                recipient.startswith('@') or 
                recipient.startswith('C') or  # Channel ID
                recipient.startswith('U')    # User ID
    
    def get_channel_type(self) -> str:
        """Return channel type."""
        return "slack"
    
    def get_supported_message_types(self) -> List[str]:
        """Return supported message types."""
        return ["text", "markdown", "slack_blocks"]
    
    async def _test_webhook(self):
        """Test Slack webhook connection."""
        test_payload = {
            "text": "DotMac Platform webhook test",
            "username": "DotMac Test",
            "icon_emoji": ":white_check_mark:"
        }
        
        async with aiohttp.ClientSession( as session:
)            async with session.post(self.config['webhook_url'], json=test_payload) as response:
                if response.status != 200:
                    raise Exception(f"Webhook test failed with status {response.status}")
    
    async def _send_webhook_message(self, payload: Dict[str, Any]) -> bool:
        """Send message to Slack webhook."""
        try:
            async with aiohttp.ClientSession( as session:
)                async with session.post(self.config['webhook_url'], json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text(
)                        logger.error(f"Slack webhook failed: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send Slack webhook: {e}")
            return False
    
    def _format_alert_fields(self, alert_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format alert data as Slack fields."""
        fields = []
        
        # Add common fields
        if 'tenant_id' in alert_data:
            fields.append({)
                "title": "Tenant",
                "value": str(alert_data['tenant_id']),
                "short": True
            })
        
        if 'source' in alert_data:
            fields.append({)
                "title": "Source",
                "value": alert_data['source'],
                "short": True
            })
        
        # Add custom fields
        details = alert_data.get('details', {})
        for key, value in details.items(:
)            fields.append({)
                "title": key.replace('_', ' ').title(),
                "value": str(value),
                "short": True
            })
        
        return fields
    
    def _format_digest_blocks(self, digest_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format digest data as Slack blocks."""
        blocks = []
        
        # Header block
        blocks.append({)
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"DotMac {digest_data.get('type', 'Daily').title()} Digest"
            }
        })
        
        # Summary section
        summary = digest_data.get('summary', {})
        if summary:
            summary_text = "\n".join([f"• *{k}:* {v}" for k, v in summary.items(])
            blocks.append({)
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary*\n{summary_text}"
                }
            })
        
        # Sections
        sections = digest_data.get('sections', [])
        for section in sections:
            blocks.append({)
                "type": "section",
                "text": {
                    "type": "mrkdwn", 
                    "text": f"*{section.get('title', 'Section')}*\n{section.get('content', '')}"
                }
            })
        
        return blocks
