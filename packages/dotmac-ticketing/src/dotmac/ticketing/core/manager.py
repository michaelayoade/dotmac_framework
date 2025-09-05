"""
Core ticket management system.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    CommentCreate,
    Ticket,
    TicketComment,
    TicketCreate,
    TicketPriority,
    TicketStatus,
    TicketUpdate,
)

logger = logging.getLogger(__name__)


class TicketManager:
    """Core ticket management system."""

    def __init__(self, db_session_factory=None, config: dict[str, Any] | None = None):
        """Initialize ticket manager."""
        self.db_session_factory = db_session_factory
        self.config = config or {}
        self._ticket_number_counter = 1000

        # SLA configurations (in minutes)
        self.sla_config = {
            TicketPriority.CRITICAL: {"response": 15, "resolution": 240},  # 15min, 4hr
            TicketPriority.URGENT: {"response": 60, "resolution": 480},  # 1hr, 8hr
            TicketPriority.HIGH: {"response": 240, "resolution": 1440},  # 4hr, 24hr
            TicketPriority.NORMAL: {
                "response": 1440,
                "resolution": 4320,
            },  # 24hr, 3days
            TicketPriority.LOW: {"response": 2880, "resolution": 10080},  # 2days, 7days
        }

    def generate_ticket_number(self, tenant_id: str) -> str:
        """Generate unique ticket number."""
        # In production, this would use a proper sequence or UUID
        timestamp = int(datetime.now(timezone.utc).timestamp())
        tenant_prefix = tenant_id[:3].upper() if tenant_id else "TKT"
        return f"{tenant_prefix}-{timestamp}"

    async def create_ticket(
        self,
        db: AsyncSession,
        tenant_id: str,
        ticket_data: TicketCreate,
        customer_id: str | None = None,
    ) -> Ticket:
        """Create a new ticket."""
        try:
            # Generate ticket number
            ticket_number = self.generate_ticket_number(tenant_id)

            # Calculate SLA times
            sla = self.sla_config.get(
                ticket_data.priority, self.sla_config[TicketPriority.NORMAL]
            )
            sla_breach_time = datetime.now(timezone.utc) + timedelta(
                minutes=sla["resolution"]
            )

            # Create ticket
            ticket = Ticket(
                tenant_id=tenant_id,
                ticket_number=ticket_number,
                title=ticket_data.title,
                description=ticket_data.description,
                category=ticket_data.category,
                priority=ticket_data.priority,
                source=ticket_data.source,
                customer_id=customer_id,
                customer_email=ticket_data.customer_email,
                customer_name=ticket_data.customer_name,
                customer_phone=ticket_data.customer_phone,
                tags=ticket_data.tags,
                extra_data=ticket_data.extra_data,
                sla_breach_time=sla_breach_time,
            )

            db.add(ticket)
            await db.commit()
            await db.refresh(ticket)

            logger.info(f"Created ticket {ticket.ticket_number} for tenant {tenant_id}")

            # Trigger notifications and workflows
            await self._trigger_ticket_created_events(ticket)

            return ticket

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating ticket: {str(e)}")
            raise

    async def get_ticket(
        self, db: AsyncSession, tenant_id: str, ticket_id: str
    ) -> Ticket | None:
        """Get ticket by ID."""
        query = (
            select(Ticket)
            .where(and_(Ticket.id == ticket_id, Ticket.tenant_id == tenant_id))
            .options(
                selectinload(Ticket.comments),
                selectinload(Ticket.attachments),
                selectinload(Ticket.escalations),
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_ticket_by_number(
        self, db: AsyncSession, tenant_id: str, ticket_number: str
    ) -> Ticket | None:
        """Get ticket by ticket number."""
        query = (
            select(Ticket)
            .where(
                and_(
                    Ticket.ticket_number == ticket_number, Ticket.tenant_id == tenant_id
                )
            )
            .options(
                selectinload(Ticket.comments),
                selectinload(Ticket.attachments),
                selectinload(Ticket.escalations),
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_ticket(
        self,
        db: AsyncSession,
        tenant_id: str,
        ticket_id: str,
        update_data: TicketUpdate,
        updated_by: str | None = None,
    ) -> Ticket | None:
        """Update ticket."""
        try:
            # Get existing ticket
            ticket = await self.get_ticket(db, tenant_id, ticket_id)
            if not ticket:
                return None

            # Track status changes
            old_status = ticket.status

            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(ticket, field, value)

            ticket.updated_at = datetime.now(timezone.utc)

            # Handle status changes
            if update_data.status and update_data.status != old_status:
                await self._handle_status_change(ticket, old_status, update_data.status)

            await db.commit()
            await db.refresh(ticket)

            logger.info(f"Updated ticket {ticket.ticket_number}")

            # Trigger events
            await self._trigger_ticket_updated_events(ticket, old_status)

            return ticket

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating ticket {ticket_id}: {str(e)}")
            raise

    async def add_comment(
        self,
        db: AsyncSession,
        tenant_id: str,
        ticket_id: str,
        comment_data: CommentCreate,
        author_id: str | None = None,
        author_name: str | None = None,
        author_email: str | None = None,
        author_type: str = "staff",
    ) -> TicketComment | None:
        """Add comment to ticket."""
        try:
            # Verify ticket exists
            ticket = await self.get_ticket(db, tenant_id, ticket_id)
            if not ticket:
                return None

            comment = TicketComment(
                ticket_id=ticket_id,
                tenant_id=tenant_id,
                content=comment_data.content,
                is_internal=comment_data.is_internal,
                is_solution=comment_data.is_solution,
                author_id=author_id,
                author_name=author_name or "Unknown",
                author_email=author_email,
                author_type=author_type,
            )

            db.add(comment)

            # Update ticket timestamp
            ticket.updated_at = datetime.now(timezone.utc)

            # If this is marked as solution, update ticket status
            if comment_data.is_solution and ticket.status not in [
                TicketStatus.RESOLVED,
                TicketStatus.CLOSED,
            ]:
                ticket.status = TicketStatus.RESOLVED
                ticket.resolved_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(comment)

            logger.info(f"Added comment to ticket {ticket.ticket_number}")

            # Trigger notifications
            await self._trigger_comment_added_events(ticket, comment)

            return comment

        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding comment to ticket {ticket_id}: {str(e)}")
            raise

    async def list_tickets(
        self,
        db: AsyncSession,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Ticket], int]:
        """List tickets with filtering, pagination, and sorting."""
        try:
            # Build base query
            query = select(Ticket).where(Ticket.tenant_id == tenant_id)

            # Apply filters
            if filters:
                if "status" in filters:
                    if isinstance(filters["status"], list):
                        query = query.where(Ticket.status.in_(filters["status"]))
                    else:
                        query = query.where(Ticket.status == filters["status"])

                if "priority" in filters:
                    if isinstance(filters["priority"], list):
                        query = query.where(Ticket.priority.in_(filters["priority"]))
                    else:
                        query = query.where(Ticket.priority == filters["priority"])

                if "category" in filters:
                    query = query.where(Ticket.category == filters["category"])

                if "assigned_to_id" in filters:
                    query = query.where(
                        Ticket.assigned_to_id == filters["assigned_to_id"]
                    )

                if "customer_id" in filters:
                    query = query.where(Ticket.customer_id == filters["customer_id"])

                if "search" in filters and filters["search"]:
                    search_term = f"%{filters['search']}%"
                    query = query.where(
                        or_(
                            Ticket.title.ilike(search_term),
                            Ticket.description.ilike(search_term),
                            Ticket.ticket_number.ilike(search_term),
                        )
                    )

                if "created_after" in filters:
                    query = query.where(Ticket.created_at >= filters["created_after"])

                if "created_before" in filters:
                    query = query.where(Ticket.created_at <= filters["created_before"])

            # Get total count
            count_query = select(func.count(Ticket.id)).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total_count = count_result.scalar()

            # Apply sorting
            sort_column = getattr(Ticket, sort_by, Ticket.created_at)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))

            # Apply pagination
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

            # Execute query
            result = await db.execute(query)
            tickets = result.scalars().all()

            return list(tickets), total_count

        except Exception as e:
            logger.error(f"Error listing tickets: {str(e)}")
            raise

    async def get_ticket_metrics(
        self,
        db: AsyncSession,
        tenant_id: str,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> dict[str, Any]:
        """Get ticket metrics and analytics."""
        try:
            base_query = select(Ticket).where(Ticket.tenant_id == tenant_id)

            if date_range:
                start_date, end_date = date_range
                base_query = base_query.where(
                    and_(Ticket.created_at >= start_date, Ticket.created_at <= end_date)
                )

            # Total tickets
            total_result = await db.execute(
                select(func.count()).select_from(base_query.subquery())
            )
            total_tickets = total_result.scalar()

            # Status breakdown
            status_query = (
                select(Ticket.status, func.count(Ticket.id).label("count"))
                .where(Ticket.tenant_id == tenant_id)
                .group_by(Ticket.status)
            )

            if date_range:
                status_query = status_query.where(
                    and_(
                        Ticket.created_at >= date_range[0],
                        Ticket.created_at <= date_range[1],
                    )
                )

            status_result = await db.execute(status_query)
            status_breakdown = {row.status: row.count for row in status_result}

            # Priority breakdown
            priority_query = (
                select(Ticket.priority, func.count(Ticket.id).label("count"))
                .where(Ticket.tenant_id == tenant_id)
                .group_by(Ticket.priority)
            )

            if date_range:
                priority_query = priority_query.where(
                    and_(
                        Ticket.created_at >= date_range[0],
                        Ticket.created_at <= date_range[1],
                    )
                )

            priority_result = await db.execute(priority_query)
            priority_breakdown = {row.priority: row.count for row in priority_result}

            # Average resolution time
            resolution_query = select(
                func.avg(
                    func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600
                ).label("avg_hours")
            ).where(and_(Ticket.tenant_id == tenant_id, Ticket.resolved_at.isnot(None)))

            if date_range:
                resolution_query = resolution_query.where(
                    and_(
                        Ticket.created_at >= date_range[0],
                        Ticket.created_at <= date_range[1],
                    )
                )

            resolution_result = await db.execute(resolution_query)
            avg_resolution_hours = resolution_result.scalar() or 0

            return {
                "total_tickets": total_tickets,
                "status_breakdown": status_breakdown,
                "priority_breakdown": priority_breakdown,
                "avg_resolution_hours": round(avg_resolution_hours, 2),
                "date_range": {
                    "start": date_range[0].isoformat() if date_range else None,
                    "end": date_range[1].isoformat() if date_range else None,
                },
            }

        except Exception as e:
            logger.error(f"Error getting ticket metrics: {str(e)}")
            raise

    async def _handle_status_change(
        self, ticket: Ticket, old_status: TicketStatus, new_status: TicketStatus
    ):
        """Handle ticket status changes."""
        if new_status == TicketStatus.RESOLVED and old_status != TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.now(timezone.utc)
        elif new_status == TicketStatus.CLOSED and old_status != TicketStatus.CLOSED:
            ticket.closed_at = datetime.now(timezone.utc)
            if not ticket.resolved_at:
                ticket.resolved_at = datetime.now(timezone.utc)

    async def _trigger_ticket_created_events(self, ticket: Ticket):
        """Trigger events when ticket is created."""
        # This would integrate with event system, notifications, etc.
        logger.info(f"Ticket created events triggered for {ticket.ticket_number}")

    async def _trigger_ticket_updated_events(self, ticket: Ticket, old_status: str):
        """Trigger events when ticket is updated."""
        logger.info(f"Ticket updated events triggered for {ticket.ticket_number}")

    async def _trigger_comment_added_events(
        self, ticket: Ticket, comment: TicketComment
    ):
        """Trigger events when comment is added."""
        logger.info(f"Comment added events triggered for ticket {ticket.ticket_number}")


class GlobalTicketManager:
    """Global singleton ticket manager."""

    def __init__(self):
        self._instance: TicketManager | None = None
        self._initialized = False

    def initialize(self, config: dict[str, Any]) -> TicketManager:
        """Initialize the global ticket manager."""
        if not self._initialized:
            self._instance = TicketManager(config=config)
            self._initialized = True
        return self._instance

    def get_instance(self) -> TicketManager | None:
        """Get the global instance."""
        return self._instance
