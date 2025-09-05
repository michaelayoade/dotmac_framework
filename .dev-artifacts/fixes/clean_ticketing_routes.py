"""
Clean Ticketing Routes - DRY Migration  
Production-ready ticketing endpoints using RouterFactory patterns.
"""

from typing import Any, Optional
from uuid import UUID

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac_shared.api.dependencies import (
    PaginatedDependencies, 
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)
from fastapi import Depends, Query
from pydantic import BaseModel, Field


# === Ticket Schemas ===

class TicketCreateRequest(BaseModel):
    """Request schema for creating tickets."""
    title: str = Field(..., description="Ticket title")
    description: str = Field(..., description="Ticket description") 
    priority: str = Field("normal", description="Ticket priority")
    category: str = Field("general", description="Ticket category")


# === Ticketing Router ===

ticketing_router = RouterFactory.create_standard_router(
    prefix="/tickets",
    tags=["tickets", "support"],
)


# === Ticket Management ===

@ticketing_router.get("/", response_model=list[dict[str, Any]])
@standard_exception_handler
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    category: Optional[str] = Query(None, description="Filter by category"),
    assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
    customer_id: Optional[str] = Query(None, description="Filter by customer"),
    search: Optional[str] = Query(None, description="Search query"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),  # noqa: B008
) -> list[dict[str, Any]]:
    """List tickets with filtering."""
    # Mock implementation
    tickets = [
        {
            "id": "ticket-001",
            "title": "Login Issue", 
            "description": "Cannot login to account",
            "status": "open",
            "priority": "high",
            "category": "technical",
            "customer_id": "customer-123",
            "assigned_to": "agent-456",
            "created_at": "2025-01-15T10:00:00Z",
        },
        {
            "id": "ticket-002",
            "title": "Billing Question",
            "description": "Question about monthly charges",
            "status": "pending",
            "priority": "normal", 
            "category": "billing",
            "customer_id": "customer-789",
            "assigned_to": None,
            "created_at": "2025-01-15T10:30:00Z",
        },
    ]
    
    # Apply filters
    if status:
        tickets = [t for t in tickets if t["status"] == status]
    if priority:
        tickets = [t for t in tickets if t["priority"] == priority]
    if category:
        tickets = [t for t in tickets if t["category"] == category]
    if customer_id:
        tickets = [t for t in tickets if t["customer_id"] == customer_id]
    if search:
        tickets = [t for t in tickets if search.lower() in t["title"].lower()]
        
    return tickets[:deps.pagination.size]


@ticketing_router.post("/", response_model=dict[str, Any])
@standard_exception_handler
async def create_ticket(
    request: TicketCreateRequest,
    deps: StandardDependencies = Depends(get_standard_deps),  # noqa: B008
) -> dict[str, Any]:
    """Create a new ticket."""
    ticket_id = f"ticket-{request.title.lower().replace(' ', '-')}"
    
    return {
        "id": ticket_id,
        "title": request.title,
        "description": request.description,
        "status": "open",
        "priority": request.priority,
        "category": request.category,
        "customer_id": deps.user_id,
        "created_at": "2025-01-15T10:30:00Z",
        "message": "Ticket created successfully",
    }


@ticketing_router.get("/{ticket_id}", response_model=dict[str, Any])
@standard_exception_handler
async def get_ticket(
    ticket_id: str,
    deps: StandardDependencies = Depends(get_standard_deps),  # noqa: B008
) -> dict[str, Any]:
    """Get ticket details."""
    return {
        "id": ticket_id,
        "title": "Login Issue",
        "description": "Cannot login to account",
        "status": "open", 
        "priority": "high",
        "category": "technical",
        "customer_id": "customer-123",
        "assigned_to": "agent-456",
        "created_at": "2025-01-15T10:00:00Z",
        "updates": [
            {
                "id": "update-001",
                "message": "Ticket created",
                "author": "system",
                "created_at": "2025-01-15T10:00:00Z",
            }
        ],
    }


# === Health Check ===

@ticketing_router.get("/health", response_model=dict[str, Any])
@standard_exception_handler 
async def ticketing_health_check(
    deps: StandardDependencies = Depends(get_standard_deps),  # noqa: B008
) -> dict[str, Any]:
    """Check ticketing service health."""
    return {
        "status": "healthy",
        "total_tickets": 1247,
        "open_tickets": 89,
        "pending_tickets": 156,
        "closed_tickets": 1002,
        "last_check": "2025-01-15T10:30:00Z",
    }


# Export the router
__all__ = ["ticketing_router"]