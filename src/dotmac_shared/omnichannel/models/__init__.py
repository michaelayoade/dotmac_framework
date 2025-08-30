"""
Omnichannel service data models.
"""

from .agent import (
    AgentAvailability,
    AgentModel,
    AgentPerformanceMetrics,
    AgentSkill,
    AgentStatus,
    CreateAgentRequest,
    UpdateAgentRequest,
)
from .channel import ChannelConfig, ChannelStatus
from .enums import ChannelType, MessageStatus
from .interaction import (
    CreateInteractionRequest,
    InteractionMessage,
    InteractionModel,
    InteractionPriority,
    InteractionStatus,
    UpdateInteractionRequest,
)
from .message import Message, MessageResult, MessageStatus
from .routing import RoutingAction, RoutingResult, RoutingRule, RoutingStrategy

__all__ = [
    # Interaction models
    "InteractionModel",
    "InteractionPriority",
    "InteractionStatus",
    "InteractionMessage",
    "CreateInteractionRequest",
    "UpdateInteractionRequest",
    # Agent models
    "AgentModel",
    "AgentStatus",
    "AgentSkill",
    "AgentPerformanceMetrics",
    "AgentAvailability",
    "CreateAgentRequest",
    "UpdateAgentRequest",
    # Message models
    "Message",
    "MessageResult",
    "MessageStatus",
    # Routing models
    "RoutingResult",
    "RoutingStrategy",
    "RoutingRule",
    "RoutingAction",
    # Channel models
    "ChannelConfig",
    "ChannelStatus",
    # Enums
    "ChannelType",
    "MessageStatus",
]
