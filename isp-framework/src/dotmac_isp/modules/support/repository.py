"""Repository pattern for support/ticket database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func, desc, asc

from .models import (
    Ticket,
    TicketComment,
    TicketAttachment,
    KnowledgeBaseArticle,
    SLARule,
    EscalationRule,
    TicketStatus,
    TicketPriority,
    TicketType,
    TicketCategory,
    EscalationStatus,
)
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class TicketRepository:
    """Repository for ticket database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, ticket_data: Dict[str, Any]) -> Ticket:
        """Create a new ticket."""
        try:
            ticket = Ticket(
                id=str(uuid4()), tenant_id=str(self.tenant_id), **ticket_data
            )

            self.db.add(ticket)
            self.db.commit()
            self.db.refresh(ticket)
            return ticket

        except IntegrityError as e:
            self.db.rollback()
            if "ticket_number" in str(e):
                raise ConflictError(
                    f"Ticket number {ticket_data.get('ticket_number')} already exists"
                )
            raise ConflictError("Ticket creation failed due to data conflict")

    def get_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Get ticket by ID."""
        return (
            self.db.query(Ticket)
            .filter(
                and_(
                    Ticket.id == ticket_id,
                    Ticket.tenant_id == str(self.tenant_id),
                    Ticket.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_ticket_number(self, ticket_number: str) -> Optional[Ticket]:
        """Get ticket by ticket number."""
        return (
            self.db.query(Ticket)
            .filter(
                and_(
                    Ticket.ticket_number == ticket_number,
                    Ticket.tenant_id == str(self.tenant_id),
                    Ticket.is_deleted == False,
                )
            )
            .first()
        )

    def list_tickets(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        category: Optional[TicketCategory] = None,
        assigned_to: Optional[str] = None,
        customer_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> List[Ticket]:
        """List tickets with filtering."""
        query = self.db.query(Ticket).filter(
            and_(Ticket.tenant_id == str(self.tenant_id), Ticket.is_deleted == False)
        )

        if status:
            query = query.filter(Ticket.ticket_status == status)
        if priority:
            query = query.filter(Ticket.priority == priority)
        if category:
            query = query.filter(Ticket.category == category)
        if assigned_to:
            query = query.filter(Ticket.assigned_to == assigned_to)
        if customer_id:
            query = query.filter(Ticket.customer_id == customer_id)
        if created_by:
            query = query.filter(Ticket.created_by == created_by)

        return query.order_by(desc(Ticket.created_at)).offset(skip).limit(limit).all()

    def update(self, ticket_id: str, update_data: Dict[str, Any]) -> Optional[Ticket]:
        """Update ticket."""
        ticket = self.get_by_id(ticket_id)
        if not ticket:
            return None

        for key, value in update_data.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)

        ticket.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def delete(self, ticket_id: str) -> bool:
        """Soft delete ticket."""
        ticket = self.get_by_id(ticket_id)
        if not ticket:
            return False

        ticket.soft_delete()
        self.db.commit()
        return True

    def get_tickets_by_sla_breach(self) -> List[Ticket]:
        """Get tickets that have breached SLA."""
        return (
            self.db.query(Ticket)
            .filter(
                and_(
                    Ticket.tenant_id == str(self.tenant_id),
                    Ticket.is_deleted == False,
                    Ticket.sla_breached == True,
                    Ticket.ticket_status.in_(
                        [
                            TicketStatus.OPEN,
                            TicketStatus.IN_PROGRESS,
                            TicketStatus.WAITING_FOR_CUSTOMER,
                            TicketStatus.ESCALATED,
                        ]
                    ),
                )
            )
            .all()
        )

    def get_overdue_tickets(self) -> List[Ticket]:
        """Get overdue tickets."""
        now = datetime.utcnow()
        return (
            self.db.query(Ticket)
            .filter(
                and_(
                    Ticket.tenant_id == str(self.tenant_id),
                    Ticket.is_deleted == False,
                    Ticket.due_date < now,
                    Ticket.ticket_status.in_(
                        [
                            TicketStatus.OPEN,
                            TicketStatus.IN_PROGRESS,
                            TicketStatus.WAITING_FOR_CUSTOMER,
                            TicketStatus.ESCALATED,
                        ]
                    ),
                )
            )
            .all()
        )

    def count_by_status(self) -> List[Dict[str, Any]]:
        """Count tickets by status."""
        result = (
            self.db.query(Ticket.ticket_status, func.count(Ticket.id).label("count"))
            .filter(
                and_(
                    Ticket.tenant_id == str(self.tenant_id), Ticket.is_deleted == False
                )
            )
            .group_by(Ticket.ticket_status)
            .all()
        )

        return [{"status": row.ticket_status, "count": row.count} for row in result]


class TicketCommentRepository:
    """Repository for ticket comment operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, comment_data: Dict[str, Any]) -> TicketComment:
        """Create a new ticket comment."""
        comment = TicketComment(
            id=str(uuid4()), tenant_id=str(self.tenant_id), **comment_data
        )

        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def get_by_ticket_id(self, ticket_id: str) -> List[TicketComment]:
        """Get all comments for a ticket."""
        return (
            self.db.query(TicketComment)
            .filter(
                and_(
                    TicketComment.ticket_id == ticket_id,
                    TicketComment.tenant_id == str(self.tenant_id),
                    TicketComment.is_deleted == False,
                )
            )
            .order_by(asc(TicketComment.created_at))
            .all()
        )

    def update(
        self, comment_id: str, update_data: Dict[str, Any]
    ) -> Optional[TicketComment]:
        """Update ticket comment."""
        comment = (
            self.db.query(TicketComment)
            .filter(
                and_(
                    TicketComment.id == comment_id,
                    TicketComment.tenant_id == str(self.tenant_id),
                    TicketComment.is_deleted == False,
                )
            )
            .first()
        )

        if not comment:
            return None

        for key, value in update_data.items():
            if hasattr(comment, key):
                setattr(comment, key, value)

        comment.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(comment)
        return comment


class KnowledgeBaseRepository:
    """Repository for knowledge base operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, article_data: Dict[str, Any]) -> KnowledgeBaseArticle:
        """Create a new knowledge base article."""
        article = KnowledgeBaseArticle(
            id=str(uuid4()), tenant_id=str(self.tenant_id), **article_data
        )

        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)
        return article

    def get_by_id(self, article_id: str) -> Optional[KnowledgeBaseArticle]:
        """Get article by ID."""
        return (
            self.db.query(KnowledgeBaseArticle)
            .filter(
                and_(
                    KnowledgeBaseArticle.id == article_id,
                    KnowledgeBaseArticle.tenant_id == str(self.tenant_id),
                    KnowledgeBaseArticle.is_deleted == False,
                )
            )
            .first()
        )

    def search_articles(
        self, query: str, category: Optional[str] = None
    ) -> List[KnowledgeBaseArticle]:
        """Search articles by content."""
        db_query = self.db.query(KnowledgeBaseArticle).filter(
            and_(
                KnowledgeBaseArticle.tenant_id == str(self.tenant_id),
                KnowledgeBaseArticle.is_deleted == False,
                KnowledgeBaseArticle.is_published == True,
                or_(
                    KnowledgeBaseArticle.title.ilike(f"%{query}%"),
                    KnowledgeBaseArticle.content.ilike(f"%{query}%"),
                    KnowledgeBaseArticle.tags.op("?")(query),
                ),
            )
        )

        if category:
            db_query = db_query.filter(KnowledgeBaseArticle.category == category)

        return db_query.order_by(desc(KnowledgeBaseArticle.view_count)).all()

    def get_popular_articles(self, limit: int = 10) -> List[KnowledgeBaseArticle]:
        """Get most popular articles."""
        return (
            self.db.query(KnowledgeBaseArticle)
            .filter(
                and_(
                    KnowledgeBaseArticle.tenant_id == str(self.tenant_id),
                    KnowledgeBaseArticle.is_deleted == False,
                    KnowledgeBaseArticle.is_published == True,
                )
            )
            .order_by(desc(KnowledgeBaseArticle.view_count))
            .limit(limit)
            .all()
        )

    def increment_view_count(self, article_id: str):
        """Increment article view count."""
        article = self.get_by_id(article_id)
        if article:
            article.view_count = (article.view_count or 0) + 1
            article.last_viewed = datetime.utcnow()
            self.db.commit()


class SLARepository:
    """Repository for SLA rule operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def get_active_rules(self) -> List[SLARule]:
        """Get all active SLA rules."""
        return (
            self.db.query(SLARule)
            .filter(
                and_(
                    SLARule.tenant_id == str(self.tenant_id),
                    SLARule.is_deleted == False,
                    SLARule.status == "active",
                )
            )
            .all()
        )

    def get_rule_for_ticket(
        self, priority: TicketPriority, category: TicketCategory
    ) -> Optional[SLARule]:
        """Get applicable SLA rule for a ticket."""
        return (
            self.db.query(SLARule)
            .filter(
                and_(
                    SLARule.tenant_id == str(self.tenant_id),
                    SLARule.is_deleted == False,
                    SLARule.status == "active",
                    or_(SLARule.priority == priority, SLARule.priority.is_(None)),
                    or_(SLARule.category == category, SLARule.category.is_(None)),
                )
            )
            .order_by(
                # More specific rules first
                SLARule.priority.is_(None).asc(),
                SLARule.category.is_(None).asc(),
            )
            .first()
        )
