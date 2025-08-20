"""
API models with comprehensive OpenAPI documentation.
Pydantic models with Field descriptions for automatic OpenAPI schema generation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum


# Enumerations
class CustomerState(str, Enum):
    """Customer lifecycle state."""
    PROSPECT = "prospect"
    LEAD = "lead"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CHURNED = "churned"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"


class CustomerType(str, Enum):
    """Customer account type."""
    RESIDENTIAL = "residential"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"


class CustomerSegment(str, Enum):
    """Customer value segment."""
    HIGH_VALUE = "high_value"
    STANDARD = "standard"
    BUDGET = "budget"
    PREMIUM = "premium"
    VIP = "vip"


# Request Models
class CustomerCreateRequest(BaseModel):
    """Request model for creating a new customer."""
    
    display_name: str = Field(
        ...,
        description="Customer display name",
        example="Acme Corporation",
        min_length=1,
        max_length=255
    )
    customer_type: CustomerType = Field(
        default=CustomerType.RESIDENTIAL,
        description="Type of customer account",
        example=CustomerType.BUSINESS
    )
    customer_segment: CustomerSegment = Field(
        default=CustomerSegment.STANDARD,
        description="Customer value segment for tiered services",
        example=CustomerSegment.PREMIUM
    )
    organization_id: Optional[UUID] = Field(
        default=None,
        description="Parent organization ID for B2B customers",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    primary_email: EmailStr = Field(
        ...,
        description="Primary contact email address",
        example="contact@acme.com"
    )
    primary_phone: str = Field(
        ...,
        description="Primary contact phone number",
        example="+1-555-0123",
        regex="^\\+?[1-9]\\d{1,14}$"
    )
    billing_email: Optional[EmailStr] = Field(
        default=None,
        description="Billing contact email (if different from primary)",
        example="billing@acme.com"
    )
    service_address: Dict[str, Any] = Field(
        ...,
        description="Service installation address",
        example={
            "street": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "US"
        }
    )
    tax_exempt: bool = Field(
        default=False,
        description="Whether customer is tax exempt",
        example=False
    )
    preferred_language: str = Field(
        default="en",
        description="Preferred language for communications (ISO 639-1)",
        example="en",
        regex="^[a-z]{2}$"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional customer metadata",
        example={"source": "web", "campaign": "summer2024"}
    )
    
    class Config:
        schema_extra = {
            "example": {
                "display_name": "Acme Corporation",
                "customer_type": "business",
                "customer_segment": "premium",
                "primary_email": "contact@acme.com",
                "primary_phone": "+1-555-0123",
                "service_address": {
                    "street": "123 Main St",
                    "city": "Springfield",
                    "state": "IL",
                    "postal_code": "62701",
                    "country": "US"
                },
                "tax_exempt": False,
                "preferred_language": "en"
            }
        }


class CustomerUpdateRequest(BaseModel):
    """Request model for updating customer information."""
    
    display_name: Optional[str] = Field(
        default=None,
        description="Updated customer display name",
        example="Acme Corp International",
        min_length=1,
        max_length=255
    )
    customer_segment: Optional[CustomerSegment] = Field(
        default=None,
        description="Updated customer segment",
        example=CustomerSegment.VIP
    )
    primary_email: Optional[EmailStr] = Field(
        default=None,
        description="Updated primary email",
        example="newcontact@acme.com"
    )
    primary_phone: Optional[str] = Field(
        default=None,
        description="Updated primary phone",
        example="+1-555-9876",
        regex="^\\+?[1-9]\\d{1,14}$"
    )
    tax_exempt: Optional[bool] = Field(
        default=None,
        description="Update tax exempt status",
        example=True
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated metadata",
        example={"account_manager": "john.doe"}
    )


# Response Models
class CustomerResponse(BaseModel):
    """Response model for customer data."""
    
    id: UUID = Field(
        ...,
        description="Unique customer identifier",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    customer_number: str = Field(
        ...,
        description="Human-readable customer number",
        example="CUST-2024-001234"
    )
    display_name: str = Field(
        ...,
        description="Customer display name",
        example="Acme Corporation"
    )
    customer_type: CustomerType = Field(
        ...,
        description="Type of customer account",
        example=CustomerType.BUSINESS
    )
    customer_segment: CustomerSegment = Field(
        ...,
        description="Customer value segment",
        example=CustomerSegment.PREMIUM
    )
    state: CustomerState = Field(
        ...,
        description="Current customer lifecycle state",
        example=CustomerState.ACTIVE
    )
    state_changed_at: datetime = Field(
        ...,
        description="Timestamp of last state change",
        example="2024-01-15T10:30:00Z"
    )
    activation_date: Optional[datetime] = Field(
        default=None,
        description="Date customer was activated",
        example="2024-01-01T00:00:00Z"
    )
    monthly_recurring_revenue: Optional[float] = Field(
        default=None,
        description="Monthly recurring revenue in base currency",
        example=149.99
    )
    lifetime_value: Optional[float] = Field(
        default=None,
        description="Total lifetime value of customer",
        example=5429.50
    )
    service_count: int = Field(
        ...,
        description="Number of active services",
        example=3
    )
    open_tickets: int = Field(
        ...,
        description="Number of open support tickets",
        example=1
    )
    created_at: datetime = Field(
        ...,
        description="Customer creation timestamp",
        example="2024-01-01T00:00:00Z"
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
        example="2024-01-15T10:30:00Z"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "customer_number": "CUST-2024-001234",
                "display_name": "Acme Corporation",
                "customer_type": "business",
                "customer_segment": "premium",
                "state": "active",
                "state_changed_at": "2024-01-15T10:30:00Z",
                "activation_date": "2024-01-01T00:00:00Z",
                "monthly_recurring_revenue": 149.99,
                "lifetime_value": 5429.50,
                "service_count": 3,
                "open_tickets": 1,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class CustomerListResponse(BaseModel):
    """Paginated list of customers."""
    
    items: List[CustomerResponse] = Field(
        ...,
        description="List of customers for current page"
    )
    total: int = Field(
        ...,
        description="Total number of customers matching query",
        example=1250
    )
    page: int = Field(
        ...,
        description="Current page number (1-based)",
        example=1
    )
    limit: int = Field(
        ...,
        description="Number of items per page",
        example=20
    )
    pages: int = Field(
        ...,
        description="Total number of pages",
        example=63
    )
    has_next: bool = Field(
        ...,
        description="Whether there is a next page",
        example=True
    )
    has_prev: bool = Field(
        ...,
        description="Whether there is a previous page",
        example=False
    )


# Authentication Models
class LoginRequest(BaseModel):
    """Request model for user login."""
    
    username: str = Field(
        ...,
        description="Username or email address",
        example="john.doe@example.com",
        min_length=3,
        max_length=255
    )
    password: str = Field(
        ...,
        description="User password",
        example="SecurePassword123!",
        min_length=8
    )
    remember_me: bool = Field(
        default=False,
        description="Whether to create a long-lived session",
        example=True
    )
    
    class Config:
        schema_extra = {
            "example": {
                "username": "john.doe@example.com",
                "password": "SecurePassword123!",
                "remember_me": True
            }
        }


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    
    access_token: str = Field(
        ...,
        description="JWT access token for API authentication",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    refresh_token: str = Field(
        ...,
        description="Refresh token for obtaining new access tokens",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        default="Bearer",
        description="Token type for Authorization header",
        example="Bearer"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        example=3600
    )
    scope: str = Field(
        default="",
        description="Token scope/permissions",
        example="read write admin"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "read write"
            }
        }


# Error Models
class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    field: str = Field(
        ...,
        description="Field that caused the error",
        example="email"
    )
    message: str = Field(
        ...,
        description="Error message",
        example="Invalid email format"
    )
    code: str = Field(
        ...,
        description="Error code",
        example="INVALID_FORMAT"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str = Field(
        ...,
        description="Error code for programmatic handling",
        example="VALIDATION_ERROR"
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        example="The provided input data is invalid"
    )
    details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="Detailed error information",
        example=[{
            "field": "email",
            "message": "Invalid email format",
            "code": "INVALID_FORMAT"
        }]
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID for debugging",
        example="req_1234567890"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp",
        example="2024-01-15T10:30:00Z"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "The provided input data is invalid",
                "details": [
                    {
                        "field": "email",
                        "message": "Invalid email format",
                        "code": "INVALID_FORMAT"
                    }
                ],
                "request_id": "req_1234567890",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }