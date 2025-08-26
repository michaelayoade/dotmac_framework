"""
Omnichannel Communication System

This module provides comprehensive omnichannel customer communication capabilities including:
- Multi-contact management per customer
- Social media platform integrations
- Unified communication history across all channels
- Intelligent routing and escalation
- Agent management with team assignments
- Real-time analytics and reporting
"""

__version__ = "1.0.0"
__author__ = "DotMac ISP Framework"

# ARCHITECTURE IMPROVEMENT: Explicit imports replace wildcard imports  
from .models import (
    # Enums
    ContactType, InteractionType, InteractionStatus,
    AgentStatus, RoutingStrategy, EscalationTrigger,
    # Main models
    CustomerContact, ContactCommunicationChannel, CommunicationInteraction,
    InteractionResponse, OmnichannelAgent, AgentTeam, RoutingRule, 
    InteractionEscalation
)
from .repository import OmnichannelRepository
from .schemas import (
    CustomerContactCreate, CustomerContactUpdate, CustomerContactResponse,
    ContactCommunicationChannelCreate, CommunicationInteractionCreate,
    InteractionResponseCreate, OmnichannelAgentCreate, AgentTeamCreate,
    RoutingRuleCreate, InteractionEscalationCreate
)
from .service_agent_manager import AgentManager
from .service_contact_manager import ContactManager
from .service_interaction_manager import InteractionManager

# Import refactored service structure
from .service_omnichannel_orchestrator import (
    OmnichannelOrchestrator,
    OmnichannelService,
)

# Legacy imports for backward compatibility
try:
    from .services import (
        AgentService,
        AnalyticsService,
        ContactService,
        InteractionService,
        RoutingService,
    )
except ImportError:
    # If services directory doesn't exist, create aliases
    ContactService = ContactManager
    InteractionService = InteractionManager
    AgentService = AgentManager
    RoutingService = None
    AnalyticsService = None

__all__ = [
    # Legacy service (now orchestrator)
    "OmnichannelService",
    # New focused services
    "ContactService",
    "InteractionService",
    "AgentService",
    "RoutingService",
    "AnalyticsService",
    "OmnichannelOrchestrator",
    # Repository
    "OmnichannelRepository",
]
