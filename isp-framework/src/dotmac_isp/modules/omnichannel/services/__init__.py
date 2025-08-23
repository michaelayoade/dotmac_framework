"""Omnichannel domain services."""

from .contact_service import ContactService
from .interaction_service import InteractionService
from .agent_service import AgentService
from .routing_service import RoutingService
from .analytics_service import AnalyticsService
from .omnichannel_orchestrator import OmnichannelOrchestrator

# Backward compatibility alias
OmnichannelService = OmnichannelOrchestrator

__all__ = [
    "ContactService",
    "InteractionService",
    "AgentService",
    "RoutingService",
    "AnalyticsService",
    "OmnichannelOrchestrator",
    "OmnichannelService",  # Backward compatibility
]
