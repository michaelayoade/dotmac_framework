"""
API components for ticketing system.
"""

from .routes import TicketAPI, create_ticket_router

__all__ = [
    "create_ticket_router",
    "TicketAPI",
]
