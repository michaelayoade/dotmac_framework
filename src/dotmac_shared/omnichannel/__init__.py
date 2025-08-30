"""
DotMac Omnichannel Communication Service

A comprehensive, multi-tenant omnichannel communication platform for the DotMac framework,
providing unified customer interaction management across multiple communication channels
with intelligent routing, agent management, and real-time analytics.

Properly integrated with the DotMac plugin system for extensible communication channels.

Author: DotMac Framework Team
License: MIT
"""

from .core.agent_manager import AgentManager, AgentModel, TeamModel
from .core.channel_orchestrator import (
    ChannelOrchestrator,
    InboundMessage,
    OutboundMessage,
)

# Core omnichannel components
from .core.interaction_manager import InteractionManager, InteractionModel
from .core.routing_engine import RoutingEngine, RoutingResult, RoutingRule

# Plugin system integration
from .integrations.plugin_system_integration import (
    OmnichannelCommunicationPlugin,
    OmnichannelPluginManager,
)
from .models.enums import ChannelType, MessageStatus

# Plugin implementations are loaded dynamically through the plugin system

__version__ = "1.0.0"

__all__ = [
    # Core components
    "InteractionManager",
    "InteractionModel",
    "RoutingEngine",
    "RoutingResult",
    "RoutingRule",
    "AgentManager",
    "AgentModel",
    "TeamModel",
    "ChannelOrchestrator",
    "ChannelType",
    "MessageStatus",
    "OutboundMessage",
    "InboundMessage",
    # Plugin system
    "OmnichannelPluginManager",
    "OmnichannelCommunicationPlugin",
]
