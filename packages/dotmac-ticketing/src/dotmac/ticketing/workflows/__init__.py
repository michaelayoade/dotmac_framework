"""
Ticketing workflow system for automating ticket lifecycle and processes.
"""

from .automation import (
    AutoAssignmentRule,
    EscalationRule,
    SLAMonitor,
    TicketAutomationEngine,
)
from .base import TicketWorkflow, WorkflowResult, WorkflowStatus
from .implementations import (
    BillingIssueWorkflow,
    CustomerSupportWorkflow,
    TechnicalSupportWorkflow,
)

__all__ = [
    # Base classes
    "TicketWorkflow",
    "WorkflowResult",
    "WorkflowStatus",
    # Automation
    "AutoAssignmentRule",
    "EscalationRule",
    "SLAMonitor",
    "TicketAutomationEngine",
    # Specific workflows
    "CustomerSupportWorkflow",
    "TechnicalSupportWorkflow",
    "BillingIssueWorkflow",
]
