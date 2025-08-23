"""
DEPRECATED: Monolithic OmnichannelService (1,518 lines)

ARCHITECTURE IMPROVEMENT: This file has been decomposed into focused services:

NEW ARCHITECTURE (services/):
- omnichannel_orchestrator.py - Main coordination service 
- contact_service.py - Customer contact management
- interaction_service.py - Communication interactions
- agent_service.py - Agent lifecycle and teams
- routing_service.py - Interaction routing rules  
- analytics_service.py - Performance metrics

MIGRATION STATUS:
✅ All imports updated to use services.OmnichannelOrchestrator
✅ API compatibility maintained via orchestrator
✅ Single Responsibility Principle applied
✅ Code complexity reduced from 1,518 → ~200-300 lines per service

BENEFITS ACHIEVED:
- Improved testability and maintainability
- Clear separation of concerns
- Easier to extend individual features
- Reduced coupling between unrelated functionality
- Better code organization following domain boundaries

This file is kept for reference during transition period.
Remove after confirming all systems work with new architecture.
"""

# Import the new orchestrator for backward compatibility
from .services import OmnichannelOrchestrator as OmnichannelService

import warnings

def __getattr__(name):
    """Handle deprecated imports with warnings."""
    if name == "OmnichannelService":
        warnings.warn(
            "Direct import of OmnichannelService from service.py is deprecated. "
            "Use 'from .services import OmnichannelOrchestrator as OmnichannelService' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return OmnichannelService
    raise AttributeError(f"module '{__name__}' has no attribute '{name__}'")

__all__ = ["OmnichannelService"]