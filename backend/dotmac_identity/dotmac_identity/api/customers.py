"""
Customer API endpoints with comprehensive OpenAPI documentation.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends
from fastapi.responses import JSONResponse

from ..models.api_models import (
    CustomerCreateRequest,
    CustomerUpdateRequest,
    CustomerResponse,
    CustomerListResponse,
    CustomerState,
    CustomerType,
    CustomerSegment,
    ErrorResponse,
)

# Create router with OpenAPI tags
router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
)


@router.post(
    "/",
    response_model=CustomerResponse,
    status_code=201,
    summary="Create new customer",
    description="""
    Create a new customer account with the provided details.
    
    This endpoint handles the complete customer onboarding process including:
    - Account creation
    - Contact information setup
    - Service address validation
    - Initial billing profile creation
    
    The customer will be created in PROSPECT state and can be activated later.
    """,
    responses={
        201: {
            "description": "Customer created successfully",
            "model": CustomerResponse,
        },
        400: {
            "description": "Invalid input data",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "VALIDATION_ERROR",
                        "message": "Invalid email format",
                        "details": [
                            {
                                "field": "primary_email",
                                "message": "Invalid email format",
                                "code": "INVALID_FORMAT"
                            }
                        ]
                    }
                }
            }
        },
        409: {
            "description": "Customer already exists",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "DUPLICATE_CUSTOMER",
                        "message": "A customer with this email already exists"
                    }
                }
            }
        },
    },
    operation_id="createCustomer",
)
async def create_customer(
    customer: CustomerCreateRequest = Body(
        ...,
        description="Customer details for account creation"
    )
) -> CustomerResponse:
    """Create a new customer account."""
    # Implementation would go here
    # This is a mock response for documentation
    return CustomerResponse(
        id="550e8400-e29b-41d4-a716-446655440000",
        customer_number="CUST-2024-001234",
        display_name=customer.display_name,
        customer_type=customer.customer_type,
        customer_segment=customer.customer_segment,
        state=CustomerState.PROSPECT,
        state_changed_at="2024-01-15T10:30:00Z",
        activation_date=None,
        monthly_recurring_revenue=0,
        lifetime_value=0,
        service_count=0,
        open_tickets=0,
        created_at="2024-01-15T10:30:00Z",
        updated_at="2024-01-15T10:30:00Z",
    )


@router.get(
    "/",
    response_model=CustomerListResponse,
    summary="List customers",
    description="""
    Retrieve a paginated list of customers with optional filtering.
    
    Supports filtering by:
    - Customer state (active, suspended, etc.)
    - Customer type (residential, business, etc.)
    - Customer segment (standard, premium, VIP, etc.)
    - Search query (searches name, email, phone)
    
    Results are sorted by creation date (newest first) by default.
    """,
    responses={
        200: {
            "description": "Customer list retrieved successfully",
            "model": CustomerListResponse,
        },
        400: {
            "description": "Invalid query parameters",
            "model": ErrorResponse,
        },
    },
    operation_id="listCustomers",
)
async def list_customers(
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (1-based)",
        example=1
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page",
        example=20
    ),
    state: Optional[CustomerState] = Query(
        default=None,
        description="Filter by customer state",
        example=CustomerState.ACTIVE
    ),
    customer_type: Optional[CustomerType] = Query(
        default=None,
        description="Filter by customer type",
        example=CustomerType.BUSINESS
    ),
    segment: Optional[CustomerSegment] = Query(
        default=None,
        description="Filter by customer segment",
        example=CustomerSegment.PREMIUM
    ),
    search: Optional[str] = Query(
        default=None,
        description="Search customers by name, email, or phone",
        example="acme",
        min_length=2,
        max_length=100
    ),
    sort_by: str = Query(
        default="created_at",
        description="Field to sort by",
        example="created_at",
        regex="^(created_at|updated_at|display_name|monthly_recurring_revenue)$"
    ),
    sort_order: str = Query(
        default="desc",
        description="Sort order",
        example="desc",
        regex="^(asc|desc)$"
    ),
) -> CustomerListResponse:
    """List customers with pagination and filtering."""
    # Mock implementation
    return CustomerListResponse(
        items=[],
        total=0,
        page=page,
        limit=limit,
        pages=0,
        has_next=False,
        has_prev=False,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer details",
    description="""
    Retrieve detailed information about a specific customer.
    
    Returns complete customer profile including:
    - Account information
    - Current state and lifecycle dates
    - Financial metrics (MRR, LTV)
    - Service summary
    - Support ticket count
    """,
    responses={
        200: {
            "description": "Customer details retrieved successfully",
            "model": CustomerResponse,
        },
        404: {
            "description": "Customer not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "NOT_FOUND",
                        "message": "Customer not found with ID: 550e8400-e29b-41d4-a716-446655440000"
                    }
                }
            }
        },
    },
    operation_id="getCustomer",
)
async def get_customer(
    customer_id: UUID = Path(
        ...,
        description="Customer unique identifier",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
) -> CustomerResponse:
    """Get customer by ID."""
    # Mock implementation
    return CustomerResponse(
        id=customer_id,
        customer_number="CUST-2024-001234",
        display_name="Acme Corporation",
        customer_type=CustomerType.BUSINESS,
        customer_segment=CustomerSegment.PREMIUM,
        state=CustomerState.ACTIVE,
        state_changed_at="2024-01-15T10:30:00Z",
        activation_date="2024-01-01T00:00:00Z",
        monthly_recurring_revenue=149.99,
        lifetime_value=5429.50,
        service_count=3,
        open_tickets=1,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-15T10:30:00Z",
    )


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update customer",
    description="""
    Update customer information.
    
    Supports partial updates - only provided fields will be updated.
    Some fields like customer_type cannot be changed after creation.
    
    State changes should use the dedicated state transition endpoints.
    """,
    responses={
        200: {
            "description": "Customer updated successfully",
            "model": CustomerResponse,
        },
        400: {
            "description": "Invalid update data",
            "model": ErrorResponse,
        },
        404: {
            "description": "Customer not found",
            "model": ErrorResponse,
        },
        409: {
            "description": "Update conflict",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "UPDATE_CONFLICT",
                        "message": "Cannot update customer in CANCELLED state"
                    }
                }
            }
        },
    },
    operation_id="updateCustomer",
)
async def update_customer(
    customer_id: UUID = Path(
        ...,
        description="Customer unique identifier",
        example="550e8400-e29b-41d4-a716-446655440000"
    ),
    customer: CustomerUpdateRequest = Body(
        ...,
        description="Customer fields to update"
    )
) -> CustomerResponse:
    """Update customer information."""
    # Mock implementation
    return CustomerResponse(
        id=customer_id,
        customer_number="CUST-2024-001234",
        display_name=customer.display_name or "Acme Corporation",
        customer_type=CustomerType.BUSINESS,
        customer_segment=customer.customer_segment or CustomerSegment.PREMIUM,
        state=CustomerState.ACTIVE,
        state_changed_at="2024-01-15T10:30:00Z",
        activation_date="2024-01-01T00:00:00Z",
        monthly_recurring_revenue=149.99,
        lifetime_value=5429.50,
        service_count=3,
        open_tickets=1,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-15T12:00:00Z",
    )


@router.post(
    "/{customer_id}/activate",
    response_model=CustomerResponse,
    summary="Activate customer",
    description="""
    Activate a customer account.
    
    Transitions customer from PROSPECT/LEAD state to ACTIVE.
    This typically happens after:
    - Service installation is complete
    - First payment is received
    - Account verification is done
    
    Sets the activation_date and triggers billing start.
    """,
    responses={
        200: {
            "description": "Customer activated successfully",
            "model": CustomerResponse,
        },
        400: {
            "description": "Invalid state transition",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "INVALID_STATE_TRANSITION",
                        "message": "Cannot activate customer in CANCELLED state"
                    }
                }
            }
        },
        404: {
            "description": "Customer not found",
            "model": ErrorResponse,
        },
    },
    operation_id="activateCustomer",
)
async def activate_customer(
    customer_id: UUID = Path(
        ...,
        description="Customer unique identifier",
        example="550e8400-e29b-41d4-a716-446655440000"
    ),
    reason: Optional[str] = Body(
        default=None,
        description="Activation reason or notes",
        example="Service installation completed"
    )
) -> CustomerResponse:
    """Activate a customer account."""
    # Mock implementation
    return CustomerResponse(
        id=customer_id,
        customer_number="CUST-2024-001234",
        display_name="Acme Corporation",
        customer_type=CustomerType.BUSINESS,
        customer_segment=CustomerSegment.PREMIUM,
        state=CustomerState.ACTIVE,
        state_changed_at="2024-01-15T14:00:00Z",
        activation_date="2024-01-15T14:00:00Z",
        monthly_recurring_revenue=149.99,
        lifetime_value=149.99,
        service_count=1,
        open_tickets=0,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-15T14:00:00Z",
    )


@router.post(
    "/{customer_id}/suspend",
    response_model=CustomerResponse,
    summary="Suspend customer",
    description="""
    Suspend a customer account.
    
    Temporarily disables customer services. Common reasons:
    - Non-payment
    - Fraud investigation
    - Customer request
    - Terms violation
    
    Services can be resumed using the reactivate endpoint.
    """,
    responses={
        200: {
            "description": "Customer suspended successfully",
            "model": CustomerResponse,
        },
        400: {
            "description": "Invalid state transition",
            "model": ErrorResponse,
        },
        404: {
            "description": "Customer not found",
            "model": ErrorResponse,
        },
    },
    operation_id="suspendCustomer",
)
async def suspend_customer(
    customer_id: UUID = Path(
        ...,
        description="Customer unique identifier",
        example="550e8400-e29b-41d4-a716-446655440000"
    ),
    reason: str = Body(
        ...,
        description="Suspension reason",
        example="Non-payment - 30 days overdue"
    ),
    auto_resume_date: Optional[str] = Body(
        default=None,
        description="Date to automatically resume services (ISO 8601)",
        example="2024-02-15T00:00:00Z"
    )
) -> CustomerResponse:
    """Suspend a customer account."""
    # Mock implementation
    return CustomerResponse(
        id=customer_id,
        customer_number="CUST-2024-001234",
        display_name="Acme Corporation",
        customer_type=CustomerType.BUSINESS,
        customer_segment=CustomerSegment.PREMIUM,
        state=CustomerState.SUSPENDED,
        state_changed_at="2024-01-15T15:00:00Z",
        activation_date="2024-01-01T00:00:00Z",
        monthly_recurring_revenue=0,  # Suspended, no revenue
        lifetime_value=5429.50,
        service_count=3,  # Services exist but suspended
        open_tickets=1,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-15T15:00:00Z",
    )


@router.delete(
    "/{customer_id}",
    status_code=204,
    summary="Delete customer",
    description="""
    Permanently delete a customer account.
    
    This is a destructive operation that:
    - Removes all customer data
    - Cancels all services
    - Voids pending invoices
    
    Only allowed for customers in CANCELLED or CHURNED state.
    Consider using soft delete (state transition) instead.
    """,
    responses={
        204: {
            "description": "Customer deleted successfully",
        },
        400: {
            "description": "Cannot delete active customer",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "DELETE_NOT_ALLOWED",
                        "message": "Cannot delete customer in ACTIVE state. Cancel first."
                    }
                }
            }
        },
        404: {
            "description": "Customer not found",
            "model": ErrorResponse,
        },
    },
    operation_id="deleteCustomer",
)
async def delete_customer(
    customer_id: UUID = Path(
        ...,
        description="Customer unique identifier",
        example="550e8400-e29b-41d4-a716-446655440000"
    ),
    force: bool = Query(
        default=False,
        description="Force delete even with active services",
        example=False
    )
) -> None:
    """Delete a customer permanently."""
    # Mock implementation
    return None