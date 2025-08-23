"""Channel plugin registry for dynamic channel management."""

from typing import Dict, List, Type, Optional
import logging
from .base import BaseChannelPlugin, ChannelConfig, ChannelCapability

logger = logging.getLogger(__name__)


class ChannelPluginRegistry:
    """Registry for managing communication channel plugins."""

    def __init__(self):
        self._plugins: Dict[str, Type[BaseChannelPlugin]] = {}
        self._initialized_plugins: Dict[str, BaseChannelPlugin] = {}
        self._plugin_configs: Dict[str, ChannelConfig] = {}

    def register_plugin(self, plugin_class: Type[BaseChannelPlugin]):
        """Register a channel plugin class."""
        # Create temporary instance to get channel_id with validation skipped
        temp_config = ChannelConfig()
        try:
            temp_instance = plugin_class(temp_config, skip_validation=True)
            channel_id = temp_instance.channel_id

            if channel_id in self._plugins:
                logger.warning(f"Plugin {channel_id} already registered, overriding")

            self._plugins[channel_id] = plugin_class
            logger.info(f"Registered channel plugin: {channel_id}")

        except Exception as e:
            logger.error(f"Failed to register plugin {plugin_class.__name__}: {e}")
            # Try alternative registration with just class name
            try:
                fallback_id = plugin_class.__name__.lower().replace("channelplugin", "")
                self._plugins[fallback_id] = plugin_class
                logger.info(f"Registered plugin with fallback ID: {fallback_id}")
            except Exception:
                pass

    def get_available_channels(self) -> List[str]:
        """Get list of all registered channel IDs."""
        return list(self._plugins.keys())

    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, any]]:
        """Get information about a specific channel."""
        if channel_id not in self._plugins:
            return None

        plugin_class = self._plugins[channel_id]
        temp_config = ChannelConfig()
        try:
            temp_instance = plugin_class(temp_config, skip_validation=True)
            return {
                "channel_id": temp_instance.channel_id,
                "channel_name": temp_instance.channel_name,
                "capabilities": temp_instance.capabilities,
                "required_config": temp_instance.required_config_fields,
                "is_initialized": channel_id in self._initialized_plugins,
            }
        except Exception as e:
            logger.error(f"Failed to get info for channel {channel_id}: {e}")
            return None

    def configure_channel(self, channel_id: str, config: ChannelConfig) -> bool:
        """Configure a channel with specific settings."""
        if channel_id not in self._plugins:
            logger.error(f"Unknown channel: {channel_id}")
            return False

        try:
            plugin_class = self._plugins[channel_id]
            plugin_instance = plugin_class(config)

            self._plugin_configs[channel_id] = config
            self._initialized_plugins[channel_id] = plugin_instance

            logger.info(f"Configured channel: {channel_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to configure channel {channel_id}: {e}")
            return False

    async def initialize_channel(self, channel_id: str) -> bool:
        """Initialize a configured channel."""
        if channel_id not in self._initialized_plugins:
            logger.error(f"Channel {channel_id} not configured")
            return False

        try:
            plugin = self._initialized_plugins[channel_id]
            success = await plugin.initialize()

            if success:
                logger.info(f"Successfully initialized channel: {channel_id}")
            else:
                logger.error(f"Failed to initialize channel: {channel_id}")

            return success

        except Exception as e:
            logger.error(f"Error initializing channel {channel_id}: {e}")
            return False

    def get_plugin(self, channel_id: str) -> Optional[BaseChannelPlugin]:
        """Get an initialized plugin instance."""
        return self._initialized_plugins.get(channel_id)

    def get_channels_by_capability(self, capability: ChannelCapability) -> List[str]:
        """Get all channels that support a specific capability."""
        matching_channels = []

        for channel_id, plugin in self._initialized_plugins.items():
            if plugin.supports_capability(capability):
                matching_channels.append(channel_id)

        return matching_channels

    async def send_message(self, channel_id: str, message) -> Optional[Dict[str, any]]:
        """Send message through a specific channel."""
        plugin = self.get_plugin(channel_id)
        if not plugin:
            logger.error(f"Plugin {channel_id} not available")
            return None

        try:
            return await plugin.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send message via {channel_id}: {e}")
            return None

    async def process_webhook(self, channel_id: str, webhook_data: Dict[str, any]):
        """Process webhook data from a specific channel."""
        plugin = self.get_plugin(channel_id)
        if not plugin:
            logger.error(f"Plugin {channel_id} not available for webhook")
            return None

        try:
            return await plugin.receive_message(webhook_data)
        except Exception as e:
            logger.error(f"Failed to process webhook for {channel_id}: {e}")
            return None

    def is_channel_healthy(self, channel_id: str) -> bool:
        """Check if a channel is healthy and operational."""
        plugin = self.get_plugin(channel_id)
        return plugin is not None and plugin.is_initialized

    def unregister_channel(self, channel_id: str):
        """Unregister a channel plugin."""
        self._plugins.pop(channel_id, None)
        self._initialized_plugins.pop(channel_id, None)
        self._plugin_configs.pop(channel_id, None)
        logger.info(f"Unregistered channel: {channel_id}")


# Decorator for easy plugin registration
def register_channel_plugin(registry: ChannelPluginRegistry):
    """Decorator to automatically register channel plugins."""

    def decorator(plugin_class: Type[BaseChannelPlugin]):
        registry.register_plugin(plugin_class)
        return plugin_class

    return decorator
