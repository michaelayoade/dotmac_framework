"""
Email notification channel plugin.
"""

import logging
import re
from typing import Dict, Any, List
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ...core.plugins.interfaces import NotificationChannelPlugin
from ...core.plugins.base import PluginMeta, PluginType

logger = logging.getLogger(__name__)


class EmailNotificationPlugin(NotificationChannelPlugin):
    """Email notification channel implementation."""
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="email_notification",
            version="1.0.0",
            plugin_type=PluginType.NOTIFICATION_CHANNEL,
            description="Email notification delivery via SMTP",
            author="DotMac Platform",
            configuration_schema={
                "smtp_host": {"type": "string", "required": True},
                "smtp_port": {"type": "integer", "default": 587},
                "smtp_username": {"type": "string", "required": True},
                "smtp_password": {"type": "string", "required": True, "sensitive": True},
                "use_tls": {"type": "boolean", "default": True},
                "from_email": {"type": "string", "required": True},
                "from_name": {"type": "string", "default": "DotMac Platform"}
            }
        )
    
    async def initialize(self) -> bool:
        """Initialize email plugin."""
        try:
            # Validate SMTP configuration
            required_config = ['smtp_host', 'smtp_username', 'smtp_password', 'from_email']
            for key in required_config:
                if key not in self.config:
                    raise ValueError(f"Missing required configuration: {key}")
            
            # Test SMTP connection
            await self._test_smtp_connection()
            return True
            
        except Exception as e:
            self.log_error(e, "initialization")
            return False
    
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate email plugin configuration."""
        try:
            required_keys = ['smtp_host', 'smtp_username', 'smtp_password', 'from_email']
            
            for key in required_keys:
                if key not in config:
                    logger.error(f"Missing required configuration key: {key}")
                    return False
            
            # Validate email format
            if not self._is_valid_email(config['from_email']):
                logger.error(f"Invalid from_email format: {config['from_email']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            await self._test_smtp_connection()
            return {
                "status": "healthy",
                "smtp_host": self.config.get("smtp_host"),
                "smtp_port": self.config.get("smtp_port", 587),
                "last_check": "success"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": "failed"
            }
    
    async def send_notification(self, message: str, recipients: List[str], options: Dict[str, Any] = None) -> bool:
        """Send email notification."""
        try:
            options = options or {}
            subject = options.get('subject', 'DotMac Platform Notification')
            message_type = options.get('type', 'text')
            
            # Validate recipients
            valid_recipients = [r for r in recipients if self.validate_recipient(r)]
            if not valid_recipients:
                logger.error("No valid email recipients provided")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.config.get('from_name', 'DotMac Platform')} <{self.config['from_email']}>"
            msg['To'] = ', '.join(valid_recipients)
            
            # Add message content
            if message_type == 'html':
                msg.attach(MIMEText(message, 'html'))
            else:
                msg.attach(MIMEText(message, 'plain'))
            
            # Send email
            await self._send_smtp_message(msg, valid_recipients)
            
            logger.info(f"Email notification sent to {len(valid_recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    async def send_alert(self, alert_data: Dict[str, Any], recipients: List[str]) -> bool:
        """Send alert email."""
        try:
            alert_type = alert_data.get('type', 'system')
            severity = alert_data.get('severity', 'info')
            message = alert_data.get('message', 'Alert triggered')
            
            subject = f"🚨 DotMac Alert - {severity.upper()}: {alert_type}"
            
            # Create HTML email content
            html_content = f"""
            <html>
                <body>
                    <h2 style="color: {'red' if severity == 'critical' else 'orange' if severity == 'warning' else 'blue'};">
                        Alert: {alert_type}
                    </h2>
                    <p><strong>Severity:</strong> {severity}</p>
                    <p><strong>Message:</strong> {message}</p>
                    <p><strong>Time:</strong> {alert_data.get('timestamp', 'Unknown')}</p>
                    
                    {self._format_alert_details(alert_data)}
                    
                    <hr>
                    <p><small>DotMac Management Platform</small></p>
                </body>
            </html>
            """
            
            return await self.send_notification(
                html_content, 
                recipients, 
                {'subject': subject, 'type': 'html'}
            )
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
            return False
    
    async def send_digest(self, digest_data: Dict[str, Any], recipients: List[str]) -> bool:
        """Send digest email."""
        try:
            digest_type = digest_data.get('type', 'daily')
            period = digest_data.get('period', 'today')
            
            subject = f"📊 DotMac Platform {digest_type.title()} Digest - {period}"
            
            # Create digest HTML
            html_content = f"""
            <html>
                <body>
                    <h1>DotMac Platform {digest_type.title()} Digest</h1>
                    <p><strong>Period:</strong> {period}</p>
                    
                    {self._format_digest_content(digest_data)}
                    
                    <hr>
                    <p><small>DotMac Management Platform - Automated Digest</small></p>
                </body>
            </html>
            """
            
            return await self.send_notification(
                html_content,
                recipients,
                {'subject': subject, 'type': 'html'}
            )
            
        except Exception as e:
            logger.error(f"Failed to send digest email: {e}")
            return False
    
    def validate_recipient(self, recipient: str) -> bool:
        """Validate email address format."""
        return self._is_valid_email(recipient)
    
    def get_channel_type(self) -> str:
        """Return channel type."""
        return "email"
    
    def get_supported_message_types(self) -> List[str]:
        """Return supported message types."""
        return ["text", "html", "markdown"]
    
    async def _test_smtp_connection(self):
        """Test SMTP connection."""
        try:
            smtp = aiosmtplib.SMTP(
                hostname=self.config['smtp_host'],
                port=self.config.get('smtp_port', 587),
                use_tls=self.config.get('use_tls', True)
            )
            
            await smtp.connect()
            await smtp.starttls()
            await smtp.login(self.config['smtp_username'], self.config['smtp_password'])
            await smtp.quit()
            
            logger.debug("SMTP connection test successful")
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            raise
    
    async def _send_smtp_message(self, message: MIMEMultipart, recipients: List[str]):
        """Send message via SMTP."""
        try:
            smtp = aiosmtplib.SMTP(
                hostname=self.config['smtp_host'],
                port=self.config.get('smtp_port', 587),
                use_tls=self.config.get('use_tls', True)
            )
            
            await smtp.connect()
            await smtp.starttls()
            await smtp.login(self.config['smtp_username'], self.config['smtp_password'])
            
            await smtp.send_message(message, recipients=recipients)
            await smtp.quit()
            
        except Exception as e:
            logger.error(f"Failed to send SMTP message: {e}")
            raise
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email address format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _format_alert_details(self, alert_data: Dict[str, Any]) -> str:
        """Format alert details for HTML email."""
        details = alert_data.get('details', {})
        if not details:
            return ""
        
        html = "<h3>Alert Details:</h3><ul>"
        for key, value in details.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        html += "</ul>"
        
        return html
    
    def _format_digest_content(self, digest_data: Dict[str, Any]) -> str:
        """Format digest content for HTML email."""
        content = "<h2>Summary</h2>"
        
        summary = digest_data.get('summary', {})
        if summary:
            content += "<ul>"
            for key, value in summary.items():
                content += f"<li><strong>{key}:</strong> {value}</li>"
            content += "</ul>"
        
        # Add sections
        sections = digest_data.get('sections', [])
        for section in sections:
            content += f"<h3>{section.get('title', 'Section')}</h3>"
            content += f"<p>{section.get('content', '')}</p>"
        
        return content