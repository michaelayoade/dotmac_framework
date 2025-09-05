"""
DotMac Ticketing System

Universal ticketing system for customer support, technical issues, and service requests.
Provides unified ticket management across Management Platform and ISP Framework.
"""

from typing import Optional

from .adapters.platform_adapter import TicketingPlatformAdapter
from .core.models import (
    Ticket,
    TicketAttachment,
    TicketCategory,
    TicketComment,
    TicketEscalation,
    TicketPriority,
    TicketStatus,
)
from .core.ticket_manager import GlobalTicketManager, TicketManager
from .services.escalation_service import TicketEscalationService

# TicketNotificationService now uses unified notification service
from .services.notification_service import TicketNotificationService
from .services.ticket_service import TicketService

# NOTE: Workflows have been migrated to dotmac.ticketing.workflows
# from .workflows.ticket_workflows import (
#     BillingIssueWorkflow,
#     CustomerSupportWorkflow,
#     TechnicalSupportWorkflow,
#     TicketWorkflow,
# )

# For backward compatibility, import from new location
try:
    from dotmac.ticketing.workflows import (
        BillingIssueWorkflow,
        CustomerSupportWorkflow,
        TechnicalSupportWorkflow,
        TicketWorkflow,
    )
except ImportError:
    # Fallback classes for when new package is not available
    class TicketWorkflow:
        """Placeholder for migrated workflow class."""

        pass

    class CustomerSupportWorkflow(TicketWorkflow):
        """Placeholder for migrated workflow class."""

        pass

    class TechnicalSupportWorkflow(TicketWorkflow):
        """Placeholder for migrated workflow class."""

        pass

    class BillingIssueWorkflow(TicketWorkflow):
        """Placeholder for migrated workflow class."""

        pass


__version__ = "1.0.0"

__all__ = [
    # Core components
    "TicketManager",
    "GlobalTicketManager",
    # Models
    "Ticket",
    "TicketStatus",
    "TicketPriority",
    "TicketCategory",
    "TicketComment",
    "TicketAttachment",
    "TicketEscalation",
    # Services
    "TicketService",
    "TicketNotificationService",
    "TicketEscalationService",
    # Workflows
    "TicketWorkflow",
    "CustomerSupportWorkflow",
    "TechnicalSupportWorkflow",
    "BillingIssueWorkflow",
    # Adapters
    "TicketingPlatformAdapter",
]

# Global instance for easy access
global_ticket_manager = GlobalTicketManager()


def initialize_ticketing(config: Optional[dict] = None) -> TicketManager:
    """Initialize the global ticketing system."""
    return global_ticket_manager.initialize(config or {})


def get_ticket_manager() -> TicketManager:
    """Get the global ticket manager instance."""
    return global_ticket_manager.get_instance()
