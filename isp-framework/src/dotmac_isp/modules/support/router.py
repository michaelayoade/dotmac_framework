"""Support API endpoints for ticket management, knowledge base, and SLA policies."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4
import secrets
import string

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
    Path,
    BackgroundTasks,
    UploadFile,
    File,
)

from sqlalchemy.orm import Session
from sqlalchemy import func

from dotmac_isp.core.database import get_db
from dotmac_isp.core.middleware import get_tenant_id_dependency
from dotmac_isp.modules.support import models, schemas
from dotmac_isp.modules.support.service import (
    SupportTicketService,
    KnowledgeBaseService,
)
from datetime import timezone
from dotmac_isp.shared.exceptions import NotFoundError, ValidationError, ServiceError

router = APIRouter(prefix="/support", tags=["support"])
support_router = router  # Export with expected name


def generate_ticket_number() -> str:
    """Generate a unique ticket number."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    random_chars = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)
    )
    return f"TKT-{timestamp}-{random_chars}"


# Ticket Endpoints
@router.post("/tickets", response_model=schemas.TicketResponse, status_code=201)
async def create_ticket(
    ticket: schemas.TicketCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create a new support ticket."""
    try:
        service = SupportTicketService(db, tenant_id)
        created_ticket = await service.create_ticket(ticket, created_by="api_user")
        return created_ticket
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickets", response_model=List[schemas.TicketResponse])
async def list_tickets(
    status: Optional[schemas.TicketStatus] = None,
    priority: Optional[schemas.TicketPriority] = None,
    category: Optional[schemas.TicketCategory] = None,
    assigned_to: Optional[str] = None,
    customer_id: Optional[str] = None,
    overdue_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List support tickets with filtering."""
    try:
        service = SupportTicketService(db, tenant_id)
        tickets = await service.list_tickets(
            skip=skip,
            limit=limit,
            status=status,
            priority=priority,
            category=category,
            assigned_to=assigned_to,
            customer_id=customer_id,
        )
        return tickets
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if customer_id:
        query = query.filter(models.Ticket.customer_id == customer_id)
    if overdue_only:
        query = query.filter(
            models.Ticket.sla_due_date < datetime.now(timezone.utc),
            models.Ticket.status.notin_(
                [schemas.TicketStatus.RESOLVED, schemas.TicketStatus.CLOSED]
            ),
        )

    tickets = (
        query.order_by(models.Ticket.opened_at.desc()).offset(skip).limit(limit).all()
    )

    # Add computed fields for each ticket
    for ticket in tickets:
        ticket.comment_count = len(ticket.comments)
        ticket.attachment_count = len(ticket.attachments)

    return tickets


@router.get("/tickets/{ticket_id}", response_model=schemas.TicketResponse)
async def get_ticket(
    ticket_id: str = Path(...),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get a specific support ticket."""
    ticket = (
        db.query(models.Ticket)
        .filter(models.Ticket.id == ticket_id, models.Ticket.tenant_id == tenant_id)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Add computed fields
    ticket.comment_count = len(ticket.comments)
    ticket.attachment_count = len(ticket.attachments)

    return ticket


@router.put("/tickets/{ticket_id}", response_model=schemas.TicketResponse)
async def update_ticket(
    ticket_id: str,
    ticket_update: schemas.TicketUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update a support ticket."""
    ticket = (
        db.query(models.Ticket)
        .filter(models.Ticket.id == ticket_id, models.Ticket.tenant_id == tenant_id)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    update_data = ticket_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ticket, field, value)

    # Update status-specific timestamps
    if "status" in update_data:
        if (
            update_data["status"] == schemas.TicketStatus.RESOLVED
            and not ticket.resolved_at
        ):
            ticket.resolved_at = datetime.now(timezone.utc)
        elif (
            update_data["status"] == schemas.TicketStatus.CLOSED and not ticket.closed_at
        ):
            ticket.closed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(ticket)

    # Add computed fields
    ticket.comment_count = len(ticket.comments)
    ticket.attachment_count = len(ticket.attachments)

    return ticket


@router.delete("/tickets/{ticket_id}", status_code=204)
async def delete_ticket(
    ticket_id: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Delete a support ticket."""
    ticket = (
        db.query(models.Ticket)
        .filter(models.Ticket.id == ticket_id, models.Ticket.tenant_id == tenant_id)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    db.delete(ticket)
    db.commit()


# Ticket Comment Endpoints
@router.post(
    "/tickets/{ticket_id}/comments",
    response_model=schemas.TicketCommentResponse,
    status_code=201,
)
async def create_ticket_comment(
    ticket_id: str,
    comment: schemas.TicketCommentCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Add a comment to a ticket."""
    # Validate ticket exists
    ticket = (
        db.query(models.Ticket)
        .filter(models.Ticket.id == ticket_id, models.Ticket.tenant_id == tenant_id)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    comment_data = comment.model_dump()
    comment_data["tenant_id"] = tenant_id
    comment_data["ticket_id"] = ticket_id

    db_comment = models.TicketComment(**comment_data)
    db.add(db_comment)

    # Update first response time if this is the first response
    if not ticket.first_response_at and not comment.is_internal:
        ticket.first_response_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(db_comment)
    return db_comment


@router.get(
    "/tickets/{ticket_id}/comments", response_model=List[schemas.TicketCommentResponse]
)
async def list_ticket_comments(
    ticket_id: str,
    include_internal: bool = False,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List comments for a ticket."""
    # Validate ticket exists
    ticket = (
        db.query(models.Ticket)
        .filter(models.Ticket.id == ticket_id, models.Ticket.tenant_id == tenant_id)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    query = db.query(models.TicketComment).filter(
        models.TicketComment.ticket_id == ticket_id
    )

    if not include_internal:
        query = query.filter(models.TicketComment.is_internal == False)

    comments = query.order_by(models.TicketComment.created_at.asc()).all()
    return comments


@router.put("/comments/{comment_id}", response_model=schemas.TicketCommentResponse)
async def update_ticket_comment(
    comment_id: str,
    comment_update: schemas.TicketCommentUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update a ticket comment."""
    comment = (
        db.query(models.TicketComment)
        .filter(
            models.TicketComment.id == comment_id,
            models.TicketComment.tenant_id == tenant_id,
        )
        .first()
    )

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    update_data = comment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(comment, field, value)

    db.commit()
    db.refresh(comment)
    return comment


# Ticket Attachment Endpoints
@router.post(
    "/tickets/{ticket_id}/attachments",
    response_model=schemas.TicketAttachmentResponse,
    status_code=201,
)
async def upload_ticket_attachment(
    ticket_id: str,
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Upload an attachment to a ticket."""
    # Validate ticket exists
    ticket = (
        db.query(models.Ticket)
        .filter(models.Ticket.id == ticket_id, models.Ticket.tenant_id == tenant_id)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=413, detail="File too large. Maximum size is 10MB."
        )

    # Generate unique filename
    file_extension = file.filename.split(".")[-1] if "." in file.filename else ""
    unique_filename = f"{uuid4()}.{file_extension}" if file_extension else str(uuid4())
    file_path = f"attachments/tickets/{ticket_id}/{unique_filename}"

    # In a real implementation, you would save the file to storage (S3, local disk, etc.)
    # For this example, we'll just store the path

    db_attachment = models.TicketAttachment(
        tenant_id=tenant_id,
        ticket_id=ticket_id,
        filename=unique_filename,
        original_filename=file.filename,
        file_size=len(file_content),
        content_type=file.content_type,
        file_path=file_path,
        uploaded_by=tenant_id,  # In real implementation, get from authenticated user
    )

    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment


@router.get(
    "/tickets/{ticket_id}/attachments",
    response_model=List[schemas.TicketAttachmentResponse],
)
async def list_ticket_attachments(
    ticket_id: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List attachments for a ticket."""
    # Validate ticket exists
    ticket = (
        db.query(models.Ticket)
        .filter(models.Ticket.id == ticket_id, models.Ticket.tenant_id == tenant_id)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    attachments = (
        db.query(models.TicketAttachment)
        .filter(models.TicketAttachment.ticket_id == ticket_id)
        .all()
    )

    return attachments


# Knowledge Base Category Endpoints
@router.post(
    "/kb/categories",
    response_model=schemas.KnowledgeBaseCategoryResponse,
    status_code=201,
)
async def create_kb_category(
    category: schemas.KnowledgeBaseCategoryCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create a knowledge base category."""
    category_data = category.model_dump()
    category_data["tenant_id"] = tenant_id

    db_category = models.KnowledgeBaseCategory(**category_data)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)

    # Add computed fields
    db_category.article_count = 0

    return db_category


@router.get(
    "/kb/categories", response_model=List[schemas.KnowledgeBaseCategoryResponse]
)
async def list_kb_categories(
    is_public: Optional[bool] = None,
    is_active: Optional[bool] = None,
    parent_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List knowledge base categories."""
    query = db.query(models.KnowledgeBaseCategory).filter(
        models.KnowledgeBaseCategory.tenant_id == tenant_id
    )

    if is_public is not None:
        query = query.filter(models.KnowledgeBaseCategory.is_public == is_public)
    if is_active is not None:
        query = query.filter(models.KnowledgeBaseCategory.is_active == is_active)
    if parent_id is not None:
        query = query.filter(models.KnowledgeBaseCategory.parent_id == parent_id)

    categories = query.order_by(models.KnowledgeBaseCategory.sort_order).all()

    # Add computed fields
    for category in categories:
        category.article_count = len(category.articles)

    return categories


@router.get(
    "/kb/categories/{category_id}", response_model=schemas.KnowledgeBaseCategoryResponse
)
async def get_kb_category(
    category_id: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get a specific knowledge base category."""
    category = (
        db.query(models.KnowledgeBaseCategory)
        .filter(
            models.KnowledgeBaseCategory.id == category_id,
            models.KnowledgeBaseCategory.tenant_id == tenant_id,
        )
        .first()
    )

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Add computed fields
    category.article_count = len(category.articles)

    return category


@router.put(
    "/kb/categories/{category_id}", response_model=schemas.KnowledgeBaseCategoryResponse
)
async def update_kb_category(
    category_id: str,
    category_update: schemas.KnowledgeBaseCategoryUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update a knowledge base category."""
    category = (
        db.query(models.KnowledgeBaseCategory)
        .filter(
            models.KnowledgeBaseCategory.id == category_id,
            models.KnowledgeBaseCategory.tenant_id == tenant_id,
        )
        .first()
    )

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    # Add computed fields
    category.article_count = len(category.articles)

    return category


# Knowledge Base Article Endpoints
@router.post(
    "/kb/articles", response_model=schemas.KnowledgeBaseArticleResponse, status_code=201
)
async def create_kb_article(
    article: schemas.KnowledgeBaseArticleCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create a knowledge base article."""
    # Validate category exists
    category = (
        db.query(models.KnowledgeBaseCategory)
        .filter(
            models.KnowledgeBaseCategory.id == article.category_id,
            models.KnowledgeBaseCategory.tenant_id == tenant_id,
        )
        .first()
    )

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    article_data = article.model_dump()
    article_data["tenant_id"] = tenant_id
    article_data["author_id"] = (
        tenant_id  # In real implementation, get from authenticated user
    )

    if article.is_published:
        article_data["published_at"] = datetime.now(timezone.utc)

    db_article = models.KnowledgeBaseArticle(**article_data)
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article


@router.get("/kb/articles", response_model=List[schemas.KnowledgeBaseArticleResponse])
async def list_kb_articles(
    category_id: Optional[str] = None,
    is_published: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List knowledge base articles."""
    query = db.query(models.KnowledgeBaseArticle).filter(
        models.KnowledgeBaseArticle.tenant_id == tenant_id
    )

    if category_id:
        query = query.filter(models.KnowledgeBaseArticle.category_id == category_id)
    if is_published is not None:
        query = query.filter(models.KnowledgeBaseArticle.is_published == is_published)
    if is_featured is not None:
        query = query.filter(models.KnowledgeBaseArticle.is_featured == is_featured)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            models.KnowledgeBaseArticle.title.ilike(search_term)
            | models.KnowledgeBaseArticle.content.ilike(search_term)
            | models.KnowledgeBaseArticle.summary.ilike(search_term)
        )

    articles = (
        query.order_by(models.KnowledgeBaseArticle.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return articles


@router.get(
    "/kb/articles/{article_id}", response_model=schemas.KnowledgeBaseArticleResponse
)
async def get_kb_article(
    article_id: str,
    increment_view: bool = True,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get a specific knowledge base article."""
    article = (
        db.query(models.KnowledgeBaseArticle)
        .filter(
            models.KnowledgeBaseArticle.id == article_id,
            models.KnowledgeBaseArticle.tenant_id == tenant_id,
        )
        .first()
    )

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Increment view count
    if increment_view:
        article.view_count += 1
        db.commit()

    return article


@router.put(
    "/kb/articles/{article_id}", response_model=schemas.KnowledgeBaseArticleResponse
)
async def update_kb_article(
    article_id: str,
    article_update: schemas.KnowledgeBaseArticleUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update a knowledge base article."""
    article = (
        db.query(models.KnowledgeBaseArticle)
        .filter(
            models.KnowledgeBaseArticle.id == article_id,
            models.KnowledgeBaseArticle.tenant_id == tenant_id,
        )
        .first()
    )

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    update_data = article_update.model_dump(exclude_unset=True)

    # Handle publication status change
    if (
        "is_published" in update_data
        and update_data["is_published"]
        and not article.published_at
    ):
        update_data["published_at"] = datetime.now(timezone.utc)

    # Set last updated by
    update_data["last_updated_by"] = (
        tenant_id  # In real implementation, get from authenticated user
    )

    for field, value in update_data.items():
        setattr(article, field, value)

    db.commit()
    db.refresh(article)
    return article


# SLA Policy Endpoints
@router.post("/sla-policies", response_model=schemas.SLAPolicyResponse, status_code=201)
async def create_sla_policy(
    policy: schemas.SLAPolicyCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create an SLA policy."""
    policy_data = policy.model_dump()
    policy_data["tenant_id"] = tenant_id

    # If this is set as default, unset other defaults
    if policy.is_default:
        db.query(models.SLAPolicy).filter(
            models.SLAPolicy.tenant_id == tenant_id
        ).update({"is_default": False})

    db_policy = models.SLAPolicy(**policy_data)
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy


@router.get("/sla-policies", response_model=List[schemas.SLAPolicyResponse])
async def list_sla_policies(
    is_active: Optional[bool] = None,
    is_default: Optional[bool] = None,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List SLA policies."""
    query = db.query(models.SLAPolicy).filter(models.SLAPolicy.tenant_id == tenant_id)

    if is_active is not None:
        query = query.filter(models.SLAPolicy.is_active == is_active)
    if is_default is not None:
        query = query.filter(models.SLAPolicy.is_default == is_default)

    policies = query.order_by(models.SLAPolicy.created_at.desc()).all()
    return policies


@router.get("/sla-policies/{policy_id}", response_model=schemas.SLAPolicyResponse)
async def get_sla_policy(
    policy_id: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get a specific SLA policy."""
    policy = (
        db.query(models.SLAPolicy)
        .filter(
            models.SLAPolicy.id == policy_id, models.SLAPolicy.tenant_id == tenant_id
        )
        .first()
    )

    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")

    return policy


@router.put("/sla-policies/{policy_id}", response_model=schemas.SLAPolicyResponse)
async def update_sla_policy(
    policy_id: str,
    policy_update: schemas.SLAPolicyUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update an SLA policy."""
    policy = (
        db.query(models.SLAPolicy)
        .filter(
            models.SLAPolicy.id == policy_id, models.SLAPolicy.tenant_id == tenant_id
        )
        .first()
    )

    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")

    update_data = policy_update.model_dump(exclude_unset=True)

    # If this is set as default, unset other defaults
    if update_data.get("is_default"):
        db.query(models.SLAPolicy).filter(
            models.SLAPolicy.tenant_id == tenant_id, models.SLAPolicy.id != policy_id
        ).update({"is_default": False})

    for field, value in update_data.items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)
    return policy


# Dashboard and Analytics Endpoints
@router.get("/dashboard", response_model=schemas.SupportDashboard)
async def get_support_dashboard(
    tenant_id: str = Depends(get_tenant_id_dependency), db: Session = Depends(get_db)
):
    """Get support dashboard metrics."""
    # Ticket counts by status
    total_tickets = (
        db.query(models.Ticket).filter(models.Ticket.tenant_id == tenant_id).count()
    )
    open_tickets = (
        db.query(models.Ticket)
        .filter(
            models.Ticket.tenant_id == tenant_id,
            models.Ticket.status == schemas.TicketStatus.OPEN,
        )
        .count()
    )
    in_progress_tickets = (
        db.query(models.Ticket)
        .filter(
            models.Ticket.tenant_id == tenant_id,
            models.Ticket.status == schemas.TicketStatus.IN_PROGRESS,
        )
        .count()
    )
    resolved_tickets = (
        db.query(models.Ticket)
        .filter(
            models.Ticket.tenant_id == tenant_id,
            models.Ticket.status == schemas.TicketStatus.RESOLVED,
        )
        .count()
    )

    # Overdue tickets
    overdue_tickets = (
        db.query(models.Ticket)
        .filter(
            models.Ticket.tenant_id == tenant_id,
            models.Ticket.sla_due_date < datetime.now(timezone.utc),
            models.Ticket.status.notin_(
                [schemas.TicketStatus.RESOLVED, schemas.TicketStatus.CLOSED]
            ),
        )
        .count()
    )

    # Critical tickets
    critical_tickets = (
        db.query(models.Ticket)
        .filter(
            models.Ticket.tenant_id == tenant_id,
            models.Ticket.priority == schemas.TicketPriority.CRITICAL,
            models.Ticket.status.notin_(
                [schemas.TicketStatus.RESOLVED, schemas.TicketStatus.CLOSED]
            ),
        )
        .count()
    )

    # Knowledge base articles
    total_kb_articles = (
        db.query(models.KnowledgeBaseArticle)
        .filter(models.KnowledgeBaseArticle.tenant_id == tenant_id)
        .count()
    )
    published_kb_articles = (
        db.query(models.KnowledgeBaseArticle)
        .filter(
            models.KnowledgeBaseArticle.tenant_id == tenant_id,
            models.KnowledgeBaseArticle.is_published == True,
        )
        .count()
    )

    # Calculate average response and resolution times (simplified)
    avg_response_time_hours = 2.5  # Mock data
    avg_resolution_time_hours = 24.5  # Mock data
    sla_compliance_rate = 92.5  # Mock data
    customer_satisfaction_score = 8.2  # Mock data

    return schemas.SupportDashboard(
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        resolved_tickets=resolved_tickets,
        overdue_tickets=overdue_tickets,
        critical_tickets=critical_tickets,
        avg_response_time_hours=avg_response_time_hours,
        avg_resolution_time_hours=avg_resolution_time_hours,
        sla_compliance_rate=sla_compliance_rate,
        customer_satisfaction_score=customer_satisfaction_score,
        total_kb_articles=total_kb_articles,
        published_kb_articles=published_kb_articles,
    )


@router.get("/analytics/tickets", response_model=List[schemas.TicketMetrics])
async def get_ticket_analytics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get ticket analytics and metrics."""
    query = db.query(models.Ticket).filter(models.Ticket.tenant_id == tenant_id)

    if start_date:
        query = query.filter(models.Ticket.opened_at >= start_date)
    if end_date:
        query = query.filter(models.Ticket.opened_at <= end_date)

    tickets = query.order_by(models.Ticket.opened_at.desc()).limit(limit).all()

    metrics = []
    for ticket in tickets:
        # Calculate response time
        response_time_hours = None
        if ticket.first_response_at:
            response_time = ticket.first_response_at - ticket.opened_at
            response_time_hours = response_time.total_seconds() / 3600

        # Calculate resolution time
        resolution_time_hours = None
        if ticket.resolved_at:
            resolution_time = ticket.resolved_at - ticket.opened_at
            resolution_time_hours = resolution_time.total_seconds() / 3600

        metrics.append(
            schemas.TicketMetrics(
                ticket_id=str(ticket.id),
                ticket_number=ticket.ticket_number,
                title=ticket.title,
                status=ticket.status,
                priority=ticket.priority,
                category=ticket.category,
                sla_status=ticket.sla_status,
                response_time_hours=response_time_hours,
                resolution_time_hours=resolution_time_hours,
                is_overdue=ticket.is_overdue,
                assigned_team=ticket.assigned_team,
                created_at=ticket.opened_at,
            )
        )

    return metrics


# Bulk Operations
@router.post("/tickets/bulk-operation", response_model=schemas.BulkOperationResponse)
async def bulk_ticket_operation(
    operation: schemas.BulkTicketOperation,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Perform bulk operations on tickets."""
    # Validate that all tickets exist
    tickets = (
        db.query(models.Ticket)
        .filter(
            models.Ticket.id.in_(operation.ticket_ids),
            models.Ticket.tenant_id == tenant_id,
        )
        .all()
    )

    if len(tickets) != len(operation.ticket_ids):
        raise HTTPException(status_code=404, detail="Some tickets not found")

    results = []
    successful = 0
    failed = 0

    for ticket in tickets:
        try:
            if operation.operation == "close":
                ticket.status = schemas.TicketStatus.CLOSED
                ticket.closed_at = datetime.now(timezone.utc)
            elif operation.operation == "assign":
                if "assigned_to" in operation.parameters:
                    ticket.assigned_to = operation.parameters["assigned_to"]
            elif operation.operation == "change_priority":
                if "priority" in operation.parameters:
                    ticket.priority = operation.parameters["priority"]
            elif operation.operation == "change_status":
                if "status" in operation.parameters:
                    ticket.status = operation.parameters["status"]

            successful += 1
            results.append(
                {
                    "ticket_id": str(ticket.id),
                    "ticket_number": ticket.ticket_number,
                    "status": "success",
                    "message": f"Operation {operation.operation} completed",
                }
            )

        except Exception as e:
            failed += 1
            results.append(
                {
                    "ticket_id": str(ticket.id),
                    "ticket_number": ticket.ticket_number,
                    "status": "failed",
                    "message": str(e),
                }
            )

    db.commit()

    return schemas.BulkOperationResponse(
        operation_id=str(uuid4()),
        total_tickets=len(tickets),
        successful=successful,
        failed=failed,
        results=results,
    )
