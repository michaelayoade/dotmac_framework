"""
Strategic Communication Bridge for ISP Framework

Modern communication bridge that connects the ISP Framework with the strategic plugin system.
Provides clean integration without legacy fallback patterns.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import sys

# Add path to strategic plugin system
sys.path.append(str(Path(__file__).parents[4]))

from shared.communication.plugin_system import global_plugin_registry, initialize_plugin_system

logger = logging.getLogger(__name__)


class ISPCommunicationBridge:
    """Strategic bridge between ISP Framework and plugin system."""
    
    def __init__(self):
        """Initialize communication bridge."""
        self.strategic_registry = global_plugin_registry
        self._strategic_initialized = False
        self._bridge_initialized = False
        
    async def _ensure_strategic_system_ready(self):
        """Ensure strategic plugin system is initialized."""
        if not self._strategic_initialized:
            try:
                config_path = Path(__file__).parent.parent.parent / "config" / "communication_plugins.yml"
                await initialize_plugin_system(str(config_path))
                self._strategic_initialized = True
                logger.info("✅ Strategic plugin system initialized for ISP Framework")
            except Exception as e:
                logger.error(f"Strategic plugin system initialization failed: {e}")
                raise RuntimeError("Communication system initialization failed") from e
    
    async def initialize_bridge(self):
        """Initialize the communication bridge."""
        if self._bridge_initialized:
            return
            
        await self._ensure_strategic_system_ready()
        
        self._bridge_initialized = True
        logger.info("🌉 ISP Communication Bridge initialized")
    
    async def send_message(
        self, 
        channel_type: str, 
        recipient: str, 
        content: str, 
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Send message via strategic plugin system.
        
        Args:
            channel_type: Communication channel type (email, sms, whatsapp, etc.)
            recipient: Message recipient (email address, phone number, etc.)
            content: Message content
            metadata: Additional metadata (customer_id, template, etc.)
        
        Returns:
            Dict containing success status and delivery details
            
        Raises:
            RuntimeError: If communication system is not properly initialized
        """
        await self.initialize_bridge()
        
        if not self._strategic_initialized:
            raise RuntimeError("Strategic plugin system not available")
        
        try:
            result = await self.strategic_registry.send_message(
                channel_type=channel_type,
                recipient=recipient,
                content=content,
                metadata=metadata or {}
            )
            
            if result.get("success"):
                logger.debug(f"✅ Message sent via strategic plugin system: {channel_type} to {recipient}")
                return result
            else:
                logger.error(f"Strategic plugin failed: {result.get('error')}")
                return result
                    
        except Exception as e:
            logger.error(f"Strategic plugin system error: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": "strategic_plugin"
            }
    
    async def send_customer_notification(
        self,
        customer_id: str,
        channel_type: str,
        template: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Send notification to customer via specified channel.
        
        Args:
            customer_id: Customer identifier
            channel_type: Communication channel (email, sms, whatsapp)
            template: Message template name
            context: Template rendering context
        
        Returns:
            Dict containing delivery status and details
        """
        try:
            # Get customer contact info (placeholder - implement actual customer lookup)
            recipient = await self._get_customer_recipient(customer_id, channel_type)
            if not recipient:
                return {
                    "success": False,
                    "error": f"No {channel_type} contact info for customer {customer_id}"
                }
            
            # Render template (placeholder - implement actual template rendering)
            content = await self._render_template(template, context or {})
            
            # Send via bridge
            return await self.send_message(
                channel_type=channel_type,
                recipient=recipient,
                content=content,
                metadata={
                    "customer_id": customer_id,
                    "template": template,
                    "source": "isp_framework"
                }
            )
            
        except Exception as e:
            logger.error(f"Customer notification failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_customer_recipient(self, customer_id: str, channel_type: str) -> Optional[str]:
        """Get customer's recipient address for specified channel."""
        # Placeholder - implement actual customer lookup
        # This would integrate with ISP Framework's customer service
        
        if channel_type == "email":
            return f"customer{customer_id}@example.com"  # Placeholder
        elif channel_type == "sms":
            return f"+1555000{customer_id[-4:]}"  # Placeholder  
        else:
            return None
    
    async def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render notification template with context."""
        # Placeholder - implement actual template rendering
        # This would integrate with ISP Framework's template system
        
        template_content = {
            "service_outage": "Service outage alert: {services}. Estimated resolution: {estimated_resolution}",
            "payment_reminder": "Payment reminder for invoice {invoice_id}. Amount due: ${amount}",
            "password_reset": "Password reset requested. Click here: {reset_link}",
            "maintenance_notification": "Scheduled maintenance on {scheduled_time}. Duration: {duration}",
            "service_activation": "Your service {service_name} has been activated successfully!"
        }.get(template, "Notification: {content}")
        
        try:
            return template_content.format(**context)
        except KeyError as e:
            logger.warning(f"Template rendering warning - missing context key: {e}")
            return template_content
    
    async def get_available_channels(self) -> List[str]:
        """Get list of all available communication channels."""
        await self.initialize_bridge()
        
        if not self._strategic_initialized:
            return []
        
        try:
            status = await self.strategic_registry.get_system_status()
            strategic_channels = list(status.get("plugins_by_type", {}).keys())
            return strategic_channels
        except Exception as e:
            logger.error(f"Error getting strategic channels: {e}")
            return []
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        await self.initialize_bridge()
        
        status = {
            "bridge_initialized": self._bridge_initialized,
            "strategic_system": {
                "initialized": self._strategic_initialized,
                "available": False,
                "plugins": 0,
                "channels": []
            }
        }
        
        # Strategic system status
        if self._strategic_initialized:
            try:
                strategic_status = await self.strategic_registry.get_system_status()
                status["strategic_system"].update({
                    "available": True,
                    "plugins": strategic_status.get("total_plugins", 0),
                    "channels": list(strategic_status.get("plugins_by_type", {}).keys())
                })
            except Exception as e:
                logger.error(f"Error getting strategic system status: {e}")
        
        return status


# Global bridge instance
isp_communication_bridge = ISPCommunicationBridge()


# Convenience functions for ISP Framework integration
async def send_notification(
    channel_type: str, 
    recipient: str, 
    content: str, 
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Send notification via strategic plugin system with ISP Framework integration."""
    return await isp_communication_bridge.send_message(channel_type, recipient, content, metadata)


async def send_customer_notification(
    customer_id: str,
    channel_type: str,
    template: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Send notification to customer via specified channel."""
    return await isp_communication_bridge.send_customer_notification(
        customer_id, channel_type, template, context
    )


async def initialize_isp_communication_system():
    """Initialize ISP Framework communication system."""
    return await isp_communication_bridge.initialize_bridge()