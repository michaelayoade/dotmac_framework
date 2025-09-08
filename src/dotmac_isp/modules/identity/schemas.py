"""Identity schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from dotmac_isp.modules.identity.models import AccountStatus, CustomerType
from dotmac_isp.sdks.identity.schemas import CustomerCreate as SDKCustomerCreate
from dotmac_isp.sdks.identity.schemas import CustomerResponse as SDKCustomerResponse
from dotmac_isp.sdks.identity.schemas import CustomerUpdate as SDKCustomerUpdate
from dotmac_isp.shared.schemas import AddressSchema, ContactSchema, TenantModelSchema


class UserBase(ContactSchema):
    """Base user schema."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    timezone: str = "UTC"
    language: str = "en"


class UserCreate(UserBase):
    """Schema for creating users."""

    password: str = Field(..., min_length=8, max_length=128)
    role_ids: Optional[list[UUID]] = None


class UserUpdate(UserBase):
    """Schema for updating users."""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    timezone: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[list[UUID]] = None


class UserResponse(TenantModelSchema, UserBase):
    """Schema for user responses."""

    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    avatar_url: Optional[str] = None
    roles: list["RoleResponse"] = []

    @property
    def full_name(self) -> str:
        """Full Name operation."""
        return f"{self.first_name} {self.last_name}"


class RoleBase(BaseModel):
    """Base role schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[str] = None


class RoleCreate(RoleBase):
    """Schema for creating roles."""

    pass


class RoleUpdate(BaseModel):
    """Schema for updating roles."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[str] = None


class RoleResponse(TenantModelSchema, RoleBase):
    """Schema for role responses."""

    is_system_role: bool


# Compose API schemas using SDK schemas to follow DRY principles
class CustomerCreateAPI(SDKCustomerCreate):
    """API schema for creating customers - extends SDK schema with contact/address info."""

    # Contact information - direct fields for easier API usage
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email_primary: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    company_name: Optional[str] = Field(None, max_length=200)

    # Address information
    street_address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)

    # Additional API-specific fields
    primary_user_id: Optional[UUID] = None
    notes: Optional[str] = Field(None, max_length=1000)


class CustomerUpdateAPI(SDKCustomerUpdate, ContactSchema, AddressSchema):
    """API schema for updating customers - extends SDK schema with contact/address info."""

    # Additional API-specific fields
    primary_user_id: Optional[UUID] = None
    account_status: Optional[AccountStatus] = None
    credit_limit: Optional[str] = Field(None, max_length=20)
    payment_terms: Optional[str] = Field(None, max_length=50)
    installation_date: Optional[datetime] = None
    communication_preferences: Optional[str] = None
    marketing_opt_in: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)


class CustomerResponseAPI(TenantModelSchema):
    """API schema for customer responses - includes portal_id as primary identifier."""

    # Primary identifier - Portal ID
    portal_id: str = Field(..., description="Primary portal identifier for the customer")
    # Generated password for portal access (only returned on creation)
    portal_password: Optional[str] = Field(None, description="Generated password for portal access")
    # Core fields from SDK
    customer_id: UUID
    customer_number: str
    display_name: str
    customer_type: str
    customer_segment: str
    state: str
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    # Contact information - direct fields (customers can have multiple contacts)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None

    # Address information
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    # Additional API-specific fields
    account_status: AccountStatus
    credit_limit: str = Field(default="0.00")
    payment_terms: str = Field(default="net_30")
    installation_date: Optional[datetime] = None
    primary_user_id: Optional[UUID] = None
    primary_user: Optional[UserResponse] = None
    notes: Optional[str] = None

    # Lifecycle dates from SDK
    prospect_date: Optional[datetime] = None
    activation_date: Optional[datetime] = None
    churn_date: Optional[datetime] = None

    # Business metrics from SDK
    monthly_recurring_revenue: Optional[float] = None
    lifetime_value: Optional[float] = None

    @classmethod
    def from_sdk_response(cls, sdk_response: SDKCustomerResponse, **additional_fields):
        """Create API response from SDK response."""
        return cls(
            id=sdk_response.customer_id,
            customer_id=sdk_response.customer_id,
            customer_number=sdk_response.customer_number,
            display_name=sdk_response.display_name,
            customer_type=sdk_response.customer_type,
            customer_segment=sdk_response.customer_segment,
            state=sdk_response.state,
            tags=sdk_response.tags,
            custom_fields=sdk_response.custom_fields,
            created_at=sdk_response.created_at,
            updated_at=sdk_response.updated_at,
            prospect_date=sdk_response.prospect_date,
            activation_date=sdk_response.activation_date,
            churn_date=sdk_response.churn_date,
            monthly_recurring_revenue=sdk_response.monthly_recurring_revenue,
            lifetime_value=sdk_response.lifetime_value,
            **additional_fields,
        )


# Aliases for backward compatibility
CustomerCreate = CustomerCreateAPI
CustomerUpdate = CustomerUpdateAPI
CustomerResponse = CustomerResponseAPI


class LoginRequest(BaseModel):
    """Schema for login requests."""

    username: str
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Schema for login responses."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenResponse(BaseModel):
    """Schema for token refresh responses."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh requests."""

    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Schema for password change requests."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    """Schema for password reset requests."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserProfileUpdate(BaseModel):
    """Schema for user profile updates."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_primary: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


# Customer state transition schemas
class CustomerStateTransition(BaseModel):
    """Schema for customer state transitions."""

    reason: Optional[str] = Field(None, max_length=500)
    changed_by: Optional[str] = None


class CustomerActivation(CustomerStateTransition):
    """Schema for customer activation."""

    activation_date: Optional[datetime] = None


class CustomerSuspension(CustomerStateTransition):
    """Schema for customer suspension."""

    suspension_reason: str = Field(..., max_length=500)


class CustomerCancellation(CustomerStateTransition):
    """Schema for customer cancellation."""

    cancellation_reason: str = Field(..., max_length=500)
    effective_date: Optional[datetime] = None


# Customer search and filtering
class CustomerFilters(BaseModel):
    """Schema for customer filtering and search."""

    customer_type: Optional[CustomerType] = None
    customer_segment: Optional[str] = None
    account_status: Optional[AccountStatus] = None
    search_query: Optional[str] = Field(None, max_length=200)
    tags: Optional[list[str]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    has_services: Optional[bool] = None


class CustomerListResponse(BaseModel):
    """Schema for paginated customer list responses."""

    customers: list[CustomerResponseAPI]
    total_count: int
    limit: int
    offset: int


# Forward references
UserResponse.model_rebuild()
RoleResponse.model_rebuild()
CustomerResponseAPI.model_rebuild()
