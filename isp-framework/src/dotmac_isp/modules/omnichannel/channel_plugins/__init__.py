import logging

logger = logging.getLogger(__name__)

"""Plugin-based communication channel system."""

from typing import Dict, Type
from .base import BaseChannelPlugin
from .registry import ChannelPluginRegistry

# Global plugin registry
channel_registry = ChannelPluginRegistry()


# Plugin discovery and registration
def discover_and_register_plugins():
    """Discover and register all channel plugins."""
    import os
    import importlib

    plugin_dir = os.path.dirname(__file__)
    for filename in os.listdir(plugin_dir):
        if filename.endswith("_plugin.py"):
            module_name = (
                f"dotmac_isp.modules.omnichannel.channel_plugins.{filename[:-3]}"
            )
            try:
                importlib.import_module(module_name)
            except ImportError as e:
logger.info(f"Failed to load plugin {filename}: {e}")


# Auto-discover plugins on import
discover_and_register_plugins()

__all__ = ["BaseChannelPlugin", "channel_registry"]
