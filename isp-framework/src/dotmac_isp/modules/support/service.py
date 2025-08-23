"""Support service layer for ticket management and knowledge base."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import secrets
import string

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .repository import (
    TicketRepository,
    TicketCommentRepository,
    KnowledgeBaseRepository,
    SLARepository,
)
from .models import TicketStatus, TicketPriority, TicketType, TicketCategory
from . import schemas
from dotmac_isp.shared.exceptions import (
    ServiceError,
    NotFoundError,
    ValidationError,
    ConflictError,
)


def generate_ticket_number() -> str:
    """Generate a unique ticket number."""
    timestamp = int(datetime.utcnow().timestamp())
    random_chars = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)
    )
    return f"TKT-{timestamp}-{random_chars}"


class SupportTicketService:
    """Service layer for support ticket management."""

    def __init__(self, db: Session, tenant_id: str):
        """Initialize support ticket service with database session."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.ticket_repo = TicketRepository(db, self.tenant_id)
        self.comment_repo = TicketCommentRepository(db, self.tenant_id)
        self.sla_repo = SLARepository(db, self.tenant_id)

    async def create_ticket(
        self, ticket_data: schemas.TicketCreate, created_by: str
    ) -> schemas.TicketResponse:
        """Create a new support ticket."""
        try:
            # Generate ticket number
            ticket_number = generate_ticket_number()

            # Calculate SLA due date
            sla_rule = self.sla_repo.get_rule_for_ticket(
                ticket_data.priority, ticket_data.category
            )

            due_date = None
            if sla_rule:
                due_date = datetime.utcnow() + timedelta(
                    hours=sla_rule.response_time_hours
                )

            # Create ticket data
            create_data = {
                "ticket_number": ticket_number,
                "title": ticket_data.title,
                "description": ticket_data.description,
                "ticket_type": ticket_data.ticket_type,
                "category": ticket_data.category,
                "priority": ticket_data.priority,
                "customer_id": ticket_data.customer_id,
                "ticket_status": TicketStatus.OPEN,
                "due_date": due_date,
                "created_by": created_by,
                "tags": ticket_data.tags,
            }

            ticket = self.ticket_repo.create(create_data)

            # Create initial comment if description provided
            if ticket_data.description:
                await self.add_comment(
                    ticket.id,
                    schemas.TicketCommentCreate(
                        content=f"Ticket created: {ticket_data.description}",
                        comment_type="internal",
                        is_internal=True,
                    ),
                    created_by,
                )

            return schemas.TicketResponse.from_orm(ticket)

        except Exception as e:
            raise ServiceError(f"Failed to create ticket: {str(e)}")

    async def get_ticket(self, ticket_id: str) -> Optional[schemas.TicketResponse]:
        """Get ticket by ID."""
        try:
            ticket = self.ticket_repo.get_by_id(ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket {ticket_id} not found")

            return schemas.TicketResponse.from_orm(ticket)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to get ticket: {str(e)}")

    async def get_ticket_by_number(
        self, ticket_number: str
    ) -> Optional[schemas.TicketResponse]:
        """Get ticket by ticket number."""
        try:
            ticket = self.ticket_repo.get_by_ticket_number(ticket_number)
            if not ticket:
                raise NotFoundError(f"Ticket {ticket_number} not found")

            return schemas.TicketResponse.from_orm(ticket)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to get ticket: {str(e)}")

    async def list_tickets(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        category: Optional[TicketCategory] = None,
        assigned_to: Optional[str] = None,
        customer_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> List[schemas.TicketResponse]:
        """List tickets with filtering."""
        try:
            tickets = self.ticket_repo.list_tickets(
                skip=skip,
                limit=limit,
                status=status,
                priority=priority,
                category=category,
                assigned_to=assigned_to,
                customer_id=customer_id,
                created_by=created_by,
            )

            return [schemas.TicketResponse.from_orm(ticket) for ticket in tickets]

        except Exception as e:
            raise ServiceError(f"Failed to list tickets: {str(e)}")

    async def update_ticket(
        self, ticket_id: str, update_data: schemas.TicketUpdate, updated_by: str
    ) -> Optional[schemas.TicketResponse]:
        """Update ticket."""
        try:
            ticket = self.ticket_repo.get_by_id(ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket {ticket_id} not found")

            # Build update data
            update_dict = {}
            if update_data.title is not None:
                update_dict["title"] = update_data.title
            if update_data.description is not None:
                update_dict["description"] = update_data.description
            if update_data.priority is not None:
                update_dict["priority"] = update_data.priority
            if update_data.assigned_to is not None:
                update_dict["assigned_to"] = update_data.assigned_to
            if update_data.ticket_status is not None:
                update_dict["ticket_status"] = update_data.ticket_status

                # Handle status transitions
                if update_data.ticket_status == TicketStatus.RESOLVED:
                    update_dict["resolved_at"] = datetime.utcnow()
                elif update_data.ticket_status == TicketStatus.CLOSED:
                    update_dict["closed_at"] = datetime.utcnow()

            update_dict["updated_by"] = updated_by

            updated_ticket = self.ticket_repo.update(ticket_id, update_dict)
            return schemas.TicketResponse.from_orm(updated_ticket)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to update ticket: {str(e)}")

    async def assign_ticket(
        self, ticket_id: str, assigned_to: str, assigned_by: str
    ) -> Optional[schemas.TicketResponse]:
        """Assign ticket to a user."""
        try:
            ticket = self.ticket_repo.get_by_id(ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket {ticket_id} not found")

            update_data = {
                "assigned_to": assigned_to,
                "ticket_status": TicketStatus.IN_PROGRESS,
                "updated_by": assigned_by,
            }

            updated_ticket = self.ticket_repo.update(ticket_id, update_data)

            # Add assignment comment
            await self.add_comment(
                ticket_id,
                schemas.TicketCommentCreate(
                    content=f"Ticket assigned to {assigned_to}",
                    comment_type="internal",
                    is_internal=True,
                ),
                assigned_by,
            )

            return schemas.TicketResponse.from_orm(updated_ticket)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to assign ticket: {str(e)}")

    async def add_comment(
        self, ticket_id: str, comment_data: schemas.TicketCommentCreate, created_by: str
    ) -> schemas.TicketCommentResponse:
        """Add comment to ticket."""
        try:
            # Verify ticket exists
            ticket = self.ticket_repo.get_by_id(ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket {ticket_id} not found")

            comment_dict = {
                "ticket_id": ticket_id,
                "content": comment_data.content,
                "comment_type": comment_data.comment_type,
                "is_internal": comment_data.is_internal,
                "created_by": created_by,
            }

            comment = self.comment_repo.create(comment_dict)
            return schemas.TicketCommentResponse.from_orm(comment)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to add comment: {str(e)}")

    async def get_ticket_comments(
        self, ticket_id: str
    ) -> List[schemas.TicketCommentResponse]:
        """Get all comments for a ticket."""
        try:
            # Verify ticket exists
            ticket = self.ticket_repo.get_by_id(ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket {ticket_id} not found")

            comments = self.comment_repo.get_by_ticket_id(ticket_id)
            return [
                schemas.TicketCommentResponse.from_orm(comment) for comment in comments
            ]

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to get ticket comments: {str(e)}")

    async def escalate_ticket(
        self, ticket_id: str, escalation_reason: str, escalated_by: str
    ) -> schemas.TicketResponse:
        """Escalate ticket."""
        try:
            ticket = self.ticket_repo.get_by_id(ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket {ticket_id} not found")

            # Update ticket status and priority
            update_data = {
                "ticket_status": TicketStatus.ESCALATED,
                "priority": (
                    TicketPriority.HIGH
                    if ticket.priority != TicketPriority.CRITICAL
                    else TicketPriority.CRITICAL
                ),
                "escalated_at": datetime.utcnow(),
                "escalation_reason": escalation_reason,
                "updated_by": escalated_by,
            }

            updated_ticket = self.ticket_repo.update(ticket_id, update_data)

            # Add escalation comment
            await self.add_comment(
                ticket_id,
                schemas.TicketCommentCreate(
                    content=f"Ticket escalated: {escalation_reason}",
                    comment_type="internal",
                    is_internal=True,
                ),
                escalated_by,
            )

            return schemas.TicketResponse.from_orm(updated_ticket)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to escalate ticket: {str(e)}")

    async def get_overdue_tickets(self) -> List[schemas.TicketResponse]:
        """Get overdue tickets."""
        try:
            tickets = self.ticket_repo.get_overdue_tickets()
            return [schemas.TicketResponse.from_orm(ticket) for ticket in tickets]

        except Exception as e:
            raise ServiceError(f"Failed to get overdue tickets: {str(e)}")

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get support dashboard statistics."""
        try:
            status_counts = self.ticket_repo.count_by_status()
            overdue_tickets = len(self.ticket_repo.get_overdue_tickets())
            sla_breached = len(self.ticket_repo.get_tickets_by_sla_breach())

            # Calculate totals
            total_tickets = sum(item["count"] for item in status_counts)
            open_tickets = sum(
                item["count"]
                for item in status_counts
                if item["status"]
                in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED]
            )

            return {
                "total_tickets": total_tickets,
                "open_tickets": open_tickets,
                "overdue_tickets": overdue_tickets,
                "sla_breached": sla_breached,
                "status_breakdown": status_counts,
            }

        except Exception as e:
            raise ServiceError(f"Failed to get dashboard stats: {str(e)}")


class KnowledgeBaseService:
    """Service layer for knowledge base management."""

    def __init__(self, db: Session, tenant_id: str):
        """Initialize knowledge base service."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.kb_repo = KnowledgeBaseRepository(db, self.tenant_id)

    async def create_article(
        self, article_data: schemas.KnowledgeBaseArticleCreate, created_by: str
    ) -> schemas.KnowledgeBaseArticleResponse:
        """Create a new knowledge base article."""
        try:
            create_data = {
                "title": article_data.title,
                "content": article_data.content,
                "category": article_data.category,
                "tags": article_data.tags,
                "is_published": article_data.is_published,
                "created_by": created_by,
            }

            article = self.kb_repo.create(create_data)
            return schemas.KnowledgeBaseArticleResponse.from_orm(article)

        except Exception as e:
            raise ServiceError(f"Failed to create article: {str(e)}")

    async def search_articles(
        self, query: str, category: Optional[str] = None
    ) -> List[schemas.KnowledgeBaseArticleResponse]:
        """Search knowledge base articles."""
        try:
            articles = self.kb_repo.search_articles(query, category)
            return [
                schemas.KnowledgeBaseArticleResponse.from_orm(article)
                for article in articles
            ]

        except Exception as e:
            raise ServiceError(f"Failed to search articles: {str(e)}")

    async def get_popular_articles(
        self, limit: int = 10
    ) -> List[schemas.KnowledgeBaseArticleResponse]:
        """Get most popular articles."""
        try:
            articles = self.kb_repo.get_popular_articles(limit)
            return [
                schemas.KnowledgeBaseArticleResponse.from_orm(article)
                for article in articles
            ]

        except Exception as e:
            raise ServiceError(f"Failed to get popular articles: {str(e)}")

    async def view_article(
        self, article_id: str
    ) -> schemas.KnowledgeBaseArticleResponse:
        """View article and increment view count."""
        try:
            article = self.kb_repo.get_by_id(article_id)
            if not article:
                raise NotFoundError(f"Article {article_id} not found")

            # Increment view count
            self.kb_repo.increment_view_count(article_id)

            return schemas.KnowledgeBaseArticleResponse.from_orm(article)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to view article: {str(e)}")
