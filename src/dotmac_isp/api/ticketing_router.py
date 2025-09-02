"""Ticketing API router for ISP Framework.
Uses the shared dotmac_shared.ticketing package.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import \1, Dependsndscio import AsyncSession

from dotmac_isp.core.database import get_db
from dotmac_isp.modules.identity.models import Customer, User
from dotmac_isp.shared.auth import get_current_customer, get_current_user
from dotmac_shared.api.dependencies import (
    StandardDependencies,
    PaginatedDependencies,
    SearchParams,
    get_standard_deps,
    get_paginated_deps,
    get_admin_deps

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.rate_limiting_decorators import rate_limit, rate_limit_strict
from dotmac_shared.api.router_factory import (
    Depends,
    HTTPException,
    Query,
    RouterFactory,
    status,
)

# Import shared ticketing components
from dotmac_shared.ticketing import (
    CommentCreate,
    CommentResponse,
    ISPPlatformAdapter,
    TicketCategory,
    TicketCreate,
    TicketManager,
    TicketPriority,
    TicketResponse,
    TicketService,
    TicketStatus,
    TicketUpdate,
)

# REPLACED: Direct APIRouter with RouterFactory
router = RouterFactory.create_crud_router(
    service_class=TicketService,  # Production implementation pending for service class
    create_schema=TicketCreate,  # Production implementation pending for create schema
    update_schema=TicketUpdate,  # Production implementation pending for update schema
    response_schema=TicketResponse,  # Production implementation pending for response schema
    prefix="/tickets",
    tags=["tickets"],
    enable_search=True,
    enable_bulk_operations=True,
)
# Initialize services (this would be moved to app startup)
ticket_manager = TicketManager()
ticket_service = TicketService(ticket_manager)
isp_adapter = ISPPlatformAdapter(ticket_service)


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(
    max_requests=20, time_window_seconds=60
)  # Reasonable limit for ticket creation
@standard_exception_handler
async def create_customer_ticket(
    deps: StandardDependencies = Depends(get_standard_deps),
    ticket_data: TicketCreate,
) -> TicketResponse:
    """Create a support ticket for a customer."""
    ticket = await ticket_service.create_customer_ticket(
        db=deps.db,
        tenant_id=str(deps.current_customer.tenant_id),
        customer_id=str(deps.current_customer.id),
        title=ticket_data.title,
        description=ticket_data.description,
        category=ticket_data.category,
        priority=ticket_data.priority,
        customer_email=deps.current_customer.email,
        metadata=ticket_data.metadata,
    )
    return ticket


@router.get("/", response_model=List[TicketResponse])
@standard_exception_handler
async def list_customer_tickets(
    deps: PaginatedDependencies = Depends(get_paginated_deps),
    status_filter: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List tickets for the current customer."""
    tickets, total = await ticket_service.get_customer_tickets(
        db=deps.db,
        tenant_id=str(deps.current_customer.tenant_id),
        customer_id=str(deps.current_customer.id),
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    return tickets


@router.get("/{ticket_id}", response_model=TicketResponse)
@standard_exception_handler
async def get_ticket(
    deps: StandardDependencies = Depends(get_standard_deps),
    ticket_id: str,
) -> TicketResponse:
    """Get a specific ticket by ID."""
    ticket = await ticket_manager.get_ticket(
        db=deps.db, tenant_id=str(deps.current_customer.tenant_id), ticket_id=ticket_id
    )
    if not ticket or ticket.customer_id != str(deps.current_customer.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    return TicketResponse.model_validate(ticket)


@router.post(
    "/{ticket_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
@standard_exception_handler
async def add_ticket_comment(
    deps: StandardDependencies = Depends(get_standard_deps),
    ticket_id: str,
    comment_data: CommentCreate,
) -> CommentResponse:
    """Add a comment to a ticket."""
    # Verify ticket belongs to customer
    ticket = await ticket_manager.get_ticket(
        db=deps.db, tenant_id=str(deps.current_customer.tenant_id), ticket_id=ticket_id
    )
    if not ticket or ticket.customer_id != str(deps.current_customer.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    comment = await ticket_manager.add_comment(
        db=deps.db,
        tenant_id=str(deps.current_customer.tenant_id),
        ticket_id=ticket_id,
        comment_data=comment_data,
        author_id=str(deps.current_customer.id),
        author_name=deps.current_customer.name or deps.current_customer.email,
        author_email=deps.current_customer.email,
        author_type="customer",
    )
    return CommentResponse.model_validate(comment)


# Admin endpoints
# REPLACED: Direct APIRouter with RouterFactory
router = RouterFactory.create_crud_router(
    service_class=TicketService,  # Production implementation pending for service class
    create_schema=TicketCreate,  # Production implementation pending for create schema
    update_schema=TicketUpdate,  # Production implementation pending for update schema
    response_schema=TicketResponse,  # Production implementation pending for response schema
    prefix="/admin/tickets",
    tags=["admin-tickets"],
    enable_search=True,
    enable_bulk_operations=True,
)


@router.get("/", response_model=List[TicketResponse])
async def list_all_tickets(
    deps: PaginatedDependencies = Depends(get_paginated_deps),
    status_filter: Optional[List[str]] = Query(None),
    priority_filter: Optional[List[str]] = Query(None),
    assigned_team: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """List all tickets for admin/staff."""
    filters = {}
    if status_filter:
        filters["status"] = status_filter
    if priority_filter:
        filters["priority"] = priority_filter
    if assigned_team:
        filters["assigned_team"] = assigned_team

    tickets, total = await ticket_manager.list_tickets(
        db=deps.db,
        tenant_id=str(deps.current_user.tenant_id),
        filters=filters,
        page=page,
        page_size=page_size,
    )
    return [TicketResponse.model_validate(ticket) for ticket in tickets]


@router.put("/{ticket_id}/assign")
async def assign_ticket(
    deps: StandardDependencies = Depends(get_standard_deps),
    ticket_id: str,
    assignment_data: Dict[str, Any],
) -> TicketResponse:
    """Assign ticket to a staff member."""
    ticket = await ticket_service.assign_ticket(
        db=deps.db,
        tenant_id=str(deps.current_user.tenant_id),
        ticket_id=ticket_id,
        assigned_to_id=assignment_data["assigned_to_id"],
        assigned_to_name=assignment_data.get("assigned_to_name", "Unknown"),
        assigned_team=assignment_data.get("assigned_team"),
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    return ticket


@router.post(
    "/network-issue", response_model=TicketResponse, status_code=status.HTTP_201_CREATED
)
async def create_network_issue_ticket(
    deps: StandardDependencies = Depends(get_standard_deps),
    ticket_data: Dict[str, Any],
) -> TicketResponse:
    """Create a network issue ticket (ISP-specific)."""
    ticket = await isp_adapter.create_network_issue_ticket(
        db=deps.db,
        tenant_id=str(deps.current_user.tenant_id),
        customer_id=ticket_data["customer_id"],
        service_id=ticket_data["service_id"],
        issue_description=ticket_data["description"],
        network_data=ticket_data.get("network_data", {}),
    )
    return ticket


# Include both routers
def get_ticketing_routers() -> List[APIRouter]:
    """Get all ticketing routers."""
    return [router, admin_router]
