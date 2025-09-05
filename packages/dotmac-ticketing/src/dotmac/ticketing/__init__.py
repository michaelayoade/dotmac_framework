"""
DotMac Ticketing System - Comprehensive Support Ticket Management

Universal ticketing system for customer support, technical issues, and service requests.
Provides unified ticket management with workflows, automation, and integrations.
"""

from .api import (
    TicketAPI,
    create_ticket_router,
)
from .core import (
    CommentCreate,
    CommentResponse,
    GlobalTicketManager,
    # Models
    Ticket,
    TicketAttachment,
    TicketCategory,
    TicketComment,
    # Pydantic schemas
    TicketCreate,
    TicketEscalation,
    # Managers and Services
    TicketManager,
    TicketPriority,
    TicketResponse,
    TicketService,
    TicketSource,
    TicketStatus,
    TicketUpdate,
)

# Integrations
from .integrations import (
    TicketNotificationManager,
)

# Workflows
from .workflows import (
    # Automation
    AutoAssignmentRule,
    BillingIssueWorkflow,
    # Specific workflows
    CustomerSupportWorkflow,
    EscalationRule,
    SLAMonitor,
    TechnicalSupportWorkflow,
    TicketAutomationEngine,
    # Base classes
    TicketWorkflow,
    WorkflowResult,
    WorkflowStatus,
)

__version__ = "1.0.0"

__all__ = [
    # Core Models
    "Ticket",
    "TicketComment",
    "TicketAttachment",
    "TicketEscalation",
    "TicketStatus",
    "TicketPriority",
    "TicketCategory",
    "TicketSource",
    # Pydantic Schemas
    "TicketCreate",
    "TicketUpdate",
    "TicketResponse",
    "CommentCreate",
    "CommentResponse",
    # Core Services
    "TicketManager",
    "GlobalTicketManager",
    "TicketService",
    # Workflows
    "TicketWorkflow",
    "WorkflowResult",
    "WorkflowStatus",
    "CustomerSupportWorkflow",
    "TechnicalSupportWorkflow",
    "BillingIssueWorkflow",
    # Automation
    "AutoAssignmentRule",
    "EscalationRule",
    "SLAMonitor",
    "TicketAutomationEngine",
    # API
    "create_ticket_router",
    "TicketAPI",
    # Integrations
    "TicketNotificationManager",
]

# Global instance for easy access
global_ticket_manager = GlobalTicketManager()


def initialize_ticketing(config: dict | None = None) -> TicketManager:
    """Initialize the global ticketing system."""
    return global_ticket_manager.initialize(config or {})


def get_ticket_manager() -> TicketManager:
    """Get the global ticket manager instance."""
    return global_ticket_manager.get_instance()
