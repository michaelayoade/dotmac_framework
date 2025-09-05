"""
Core ticketing components - models, managers, and services.
"""

from .manager import GlobalTicketManager, TicketManager
from .models import (
    CommentCreate,
    CommentResponse,
    Ticket,
    TicketAttachment,
    TicketCategory,
    TicketComment,
    TicketCreate,
    TicketEscalation,
    TicketPriority,
    TicketResponse,
    TicketSource,
    TicketStatus,
    TicketUpdate,
)
from .service import TicketService

__all__ = [
    # Models
    "Ticket",
    "TicketComment",
    "TicketAttachment",
    "TicketEscalation",
    "TicketStatus",
    "TicketPriority",
    "TicketCategory",
    "TicketSource",
    # Pydantic schemas
    "TicketCreate",
    "TicketUpdate",
    "TicketResponse",
    "CommentCreate",
    "CommentResponse",
    # Managers
    "TicketManager",
    "GlobalTicketManager",
    # Services
    "TicketService",
]
