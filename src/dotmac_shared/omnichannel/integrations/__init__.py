"""
Integration modules for omnichannel service

Provides bridges to external systems and DotMac framework components:
- plugin_system_integration: Integration with DotMac plugin system

Author: DotMac Framework Team
License: MIT
"""

from .plugin_system_integration import (
    OmnichannelCommunicationPlugin,
    OmnichannelPluginManager,
)

__all__ = ["OmnichannelPluginManager", "OmnichannelCommunicationPlugin"]
