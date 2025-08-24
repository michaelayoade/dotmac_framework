"""
Test Communication Plugin

Simple plugin for testing the plugin architecture without external dependencies.
"""

import time
from typing import Dict, Any

# Import from the plugin system
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[3]))

from shared.communication.plugin_system import PluginInterface, PluginManifest


class TestChannelPlugin(PluginInterface):
    """Test communication plugin implementation."""
    
    async def initialize(self) -> bool:
        """Initialize test plugin."""
        try:
            # Simple validation
            if not await self.validate_config():
                return False
            
            self._initialized = True
            print(f"✅ Test plugin {self.plugin_id} initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Test plugin initialization failed: {e}")
            return False
    
    async def validate_config(self) -> bool:
        """Validate test configuration."""
        # No required config for test plugin
        return True
    
    async def send_message(self, recipient: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send test message."""
        start_time = time.time()
        
        try:
            # Simulate message sending
            delivery_time = (time.time() - start_time) * 1000
            
            # Simulate success
            return {
                "success": True,
                "message_id": f"test_{int(time.time())}",
                "delivery_time_ms": delivery_time,
                "provider": "test_channel",
                "recipient": recipient,
                "content_length": len(content),
                "metadata": metadata or {}
            }
                
        except Exception as e:
            delivery_time = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": str(e),
                "delivery_time_ms": delivery_time,
                "provider": "test_channel"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check test plugin health."""
        base_health = await super().health_check()
        
        # Add test-specific health info
        base_health.update({
            "connection_status": "ok",
            "test_mode": True,
            "capabilities": self.manifest.capabilities
        })
        
        return base_health
    
    def get_required_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for test plugin."""
        return {
            "type": "object",
            "required": [],
            "properties": {
                "test_mode": {
                    "type": "boolean",
                    "description": "Enable test mode",
                    "default": True
                }
            }
        }