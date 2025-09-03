"""
High-level ticket service with business logic.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import (
    CommentCreate,
    CommentResponse,
    Ticket,
    TicketCreate,
    TicketPriority,
    TicketResponse,
    TicketStatus,
    TicketUpdate,
)
from ..core.ticket_manager import TicketManager

logger = logging.getLogger(__name__)


class TicketService:
    """High-level ticket service with business logic."""

    def __init__(self, ticket_manager: TicketManager):
        """Initialize service."""
        self.ticket_manager = ticket_manager

    async def create_customer_ticket(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        title: str,
        description: str,
        category: str,
        priority: str = "normal",
        customer_email: str = None,
        metadata: Dict[str, Any] = None,
    ) -> TicketResponse:
        """Create a ticket for a customer."""
        ticket_data = TicketCreate(
            title=title,
            description=description,
            category=category,
            priority=priority,
            customer_email=customer_email,
            metadata=metadata or {},
        )

        ticket = await self.ticket_manager.create_ticket(
            db, tenant_id, ticket_data, customer_id
        )

        # Convert to response format
        return TicketResponse.model_validate(ticket)

    async def assign_ticket(
        self,
        db: AsyncSession,
        tenant_id: str,
        ticket_id: str,
        assigned_to_id: str,
        assigned_to_name: str,
        assigned_team: str = None,
    ) -> Optional[TicketResponse]:
        """Assign ticket to a team member."""
        update_data = TicketUpdate(
            assigned_to_id=assigned_to_id,
            assigned_team=assigned_team,
            status=TicketStatus.IN_PROGRESS,
        )

        # Add internal comment about assignment
        await self.ticket_manager.add_comment(
            db,
            tenant_id,
            ticket_id,
            CommentCreate(
                content=f"Ticket assigned to {assigned_to_name}"
                + (f" ({assigned_team} team)" if assigned_team else ""),
                is_internal=True,
            ),
            author_name="System",
            author_type="system",
        )

        ticket = await self.ticket_manager.update_ticket(
            db, tenant_id, ticket_id, update_data
        )

        if ticket:
            return TicketResponse.model_validate(ticket)
        return None

    async def escalate_ticket(
        self,
        db: AsyncSession,
        tenant_id: str,
        ticket_id: str,
        escalation_reason: str,
        escalated_by: str,
        escalated_to: str,
        escalated_to_team: str = None,
    ) -> Optional[TicketResponse]:
        """Escalate ticket to higher level support."""
        # Update priority if not already critical
        ticket = await self.ticket_manager.get_ticket(db, tenant_id, ticket_id)
        if not ticket:
            return None

        new_priority = ticket.priority
        if ticket.priority not in [TicketPriority.CRITICAL, TicketPriority.URGENT]:
            if ticket.priority == TicketPriority.HIGH:
                new_priority = TicketPriority.URGENT
            else:
                new_priority = TicketPriority.HIGH

        update_data = TicketUpdate(
            status=TicketStatus.ESCALATED,
            priority=new_priority,
            assigned_to_id=escalated_to,
            assigned_team=escalated_to_team,
        )

        # Add escalation comment
        await self.ticket_manager.add_comment(
            db,
            tenant_id,
            ticket_id,
            CommentCreate(
                content=f"Ticket escalated: {escalation_reason}", is_internal=True
            ),
            author_name=escalated_by,
            author_type="staff",
        )

        updated_ticket = await self.ticket_manager.update_ticket(
            db, tenant_id, ticket_id, update_data
        )

        if updated_ticket:
            return TicketResponse.model_validate(updated_ticket)
        return None

    async def resolve_ticket(
        self,
        db: AsyncSession,
        tenant_id: str,
        ticket_id: str,
        resolution_comment: str,
        resolved_by: str,
    ) -> Optional[TicketResponse]:
        """Mark ticket as resolved with solution."""
        # Add solution comment
        await self.ticket_manager.add_comment(
            db,
            tenant_id,
            ticket_id,
            CommentCreate(content=resolution_comment, is_solution=True),
            author_name=resolved_by,
            author_type="staff",
        )

        # Ticket status will be updated automatically by comment system
        ticket = await self.ticket_manager.get_ticket(db, tenant_id, ticket_id)

        if ticket:
            return TicketResponse.model_validate(ticket)
        return None

    async def close_ticket(
        self,
        db: AsyncSession,
        tenant_id: str,
        ticket_id: str,
        closing_comment: str = None,
        closed_by: str = None,
    ) -> Optional[TicketResponse]:
        """Close ticket."""
        if closing_comment:
            await self.ticket_manager.add_comment(
                db,
                tenant_id,
                ticket_id,
                CommentCreate(content=closing_comment, is_internal=False),
                author_name=closed_by or "System",
                author_type="staff",
            )

        update_data = TicketUpdate(status=TicketStatus.CLOSED)
        ticket = await self.ticket_manager.update_ticket(
            db, tenant_id, ticket_id, update_data
        )

        if ticket:
            return TicketResponse.model_validate(ticket)
        return None

    async def get_customer_tickets(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        status_filter: List[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[TicketResponse], int]:
        """Get all tickets for a customer."""
        filters = {"customer_id": customer_id}
        if status_filter:
            filters["status"] = status_filter

        tickets, total = await self.ticket_manager.list_tickets(
            db, tenant_id, filters, page, page_size
        )

        ticket_responses = [TicketResponse.model_validate(ticket) for ticket in tickets]
        return ticket_responses, total

    async def get_team_tickets(
        self,
        db: AsyncSession,
        tenant_id: str,
        team_name: str,
        status_filter: List[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[TicketResponse], int]:
        """Get all tickets assigned to a team."""
        filters = {"assigned_team": team_name}
        if status_filter:
            filters["status"] = status_filter

        tickets, total = await self.ticket_manager.list_tickets(
            db, tenant_id, filters, page, page_size
        )

        ticket_responses = [TicketResponse.model_validate(ticket) for ticket in tickets]
        return ticket_responses, total

    async def get_overdue_tickets(
        self, db: AsyncSession, tenant_id: str
    ) -> List[TicketResponse]:
        """Get tickets that are past their SLA."""
        now = datetime.now(timezone.utc)
        filters = {"created_before": now}

        tickets, _ = await self.ticket_manager.list_tickets(db, tenant_id, filters)

        # Filter for actual overdue tickets
        overdue_tickets = []
        for ticket in tickets:
            if (
                ticket.sla_breach_time
                and ticket.sla_breach_time < now
                and ticket.status not in [TicketStatus.RESOLVED, TicketStatus.CLOSED]
            ):
                overdue_tickets.append(TicketResponse.model_validate(ticket))

        return overdue_tickets

    async def get_ticket_analytics(
        self,
        db: AsyncSession,
        tenant_id: str,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> Dict[str, Any]:
        """Get ticket analytics for dashboard."""
        date_range = None
        if start_date and end_date:
            date_range = (start_date, end_date)
        elif start_date:
            date_range = (start_date, datetime.now(timezone.utc))
        elif end_date:
            date_range = (datetime.now(timezone.utc) - timedelta(days=30), end_date)

        metrics = await self.ticket_manager.get_ticket_metrics(
            db, tenant_id, date_range
        )

        # Add additional analytics
        overdue_tickets = await self.get_overdue_tickets(db, tenant_id)
        metrics["overdue_count"] = len(overdue_tickets)

        return metrics
