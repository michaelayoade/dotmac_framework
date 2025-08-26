"""
Omnichannel models - imports from production models.

This file exists to maintain compatibility while we migrate to models_production.py
as the canonical model definitions.
"""

# Import all models from production to maintain compatibility
from .models_production import *

# Explicitly import commonly used models to avoid any import issues
from .models_production import (
    ContactType,
    CustomerContact,
    ContactCommunicationChannel,
    CommunicationInteraction,
    OmnichannelAgent as Agent,
    AgentTeam,
    RegisteredChannel,
    ChannelConfiguration,
    RoutingRule,
    InteractionStatus,
    InteractionResponse,
    InteractionEscalation,
    ConversationThread,
    AgentTeamMembership,
    AgentPerformanceMetric,
    ChannelAnalytics,
    InteractionResponse as InteractionResponseModel,
)
