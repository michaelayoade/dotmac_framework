"""Captive Portal Pydantic schemas for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import AuthMethodType, PortalStatus, SessionStatus, VoucherStatus


# Base schemas
class TenantAwareSchema(BaseModel):
    """Base schema for tenant-aware models."""

    model_config = ConfigDict(from_attributes=True)

    tenant_id: str = Field(..., description="Tenant identifier")


# Portal Configuration Schemas
class CaptivePortalConfigBase(BaseModel):
    """Base captive portal configuration."""

    name: str = Field(..., min_length=1, max_length=255, description="Portal name")
    ssid: str = Field(..., min_length=1, max_length=100, description="WiFi SSID")
    location: Optional[str] = Field(
        None, max_length=500, description="Physical location"
    )
    description: Optional[str] = Field(None, description="Portal description")

    # Network settings
    network_range: Optional[str] = Field(None, description="Network CIDR range")
    gateway_ip: Optional[str] = Field(None, description="Gateway IP address")
    dns_servers: Optional[List[str]] = Field(None, description="DNS server list")

    # Portal URLs
    portal_url: Optional[str] = Field(None, description="Portal landing page URL")
    redirect_url: Optional[str] = Field(None, description="Post-auth redirect URL")
    success_url: Optional[str] = Field(None, description="Success page URL")
    terms_url: Optional[str] = Field(None, description="Terms of service URL")

    # Authentication settings
    auth_methods: List[str] = Field(
        default=["social"], description="Enabled auth methods"
    )
    require_terms: bool = Field(default=True, description="Require terms acceptance")
    require_email_verification: bool = Field(
        default=True, description="Require email verification"
    )

    # Session limits
    session_timeout: int = Field(
        default=3600, ge=60, le=86400, description="Session timeout in seconds"
    )
    idle_timeout: int = Field(
        default=1800, ge=60, le=7200, description="Idle timeout in seconds"
    )
    max_concurrent_sessions: int = Field(
        default=100, ge=1, le=10000, description="Max concurrent sessions"
    )
    data_limit_mb: int = Field(
        default=0, ge=0, description="Data limit in MB (0 = unlimited)"
    )

    # Bandwidth limits
    bandwidth_limit_down: int = Field(
        default=0, ge=0, description="Download bandwidth limit in kbps"
    )
    bandwidth_limit_up: int = Field(
        default=0, ge=0, description="Upload bandwidth limit in kbps"
    )

    # Billing
    billing_enabled: bool = Field(
        default=False, description="Enable billing integration"
    )

    # Customization
    theme_config: Optional[Dict[str, Any]] = Field(
        None, description="Theme configuration"
    )
    custom_css: Optional[str] = Field(None, description="Custom CSS")
    logo_url: Optional[str] = Field(None, description="Logo URL")


class CaptivePortalConfigCreate(CaptivePortalConfigBase):
    """Schema for creating a captive portal configuration."""

    customer_id: Optional[str] = Field(None, description="Associated customer ID")
    default_billing_plan_id: Optional[str] = Field(
        None, description="Default billing plan"
    )


class CaptivePortalConfigUpdate(BaseModel):
    """Schema for updating a captive portal configuration."""

    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    auth_methods: Optional[List[str]] = None
    session_timeout: Optional[int] = Field(None, ge=60, le=86400)
    max_concurrent_sessions: Optional[int] = Field(None, ge=1, le=10000)
    billing_enabled: Optional[bool] = None
    portal_status: Optional[PortalStatus] = None


class CaptivePortalConfigResponse(CaptivePortalConfigBase, TenantAwareSchema):
    """Schema for captive portal configuration responses."""

    id: str = Field(..., description="Portal configuration ID")
    customer_id: Optional[str] = Field(None, description="Associated customer ID")
    portal_status: PortalStatus = Field(..., description="Portal status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Authentication Schemas
class AuthenticationRequest(BaseModel):
    """Base authentication request."""

    model_config = ConfigDict(from_attributes=True)

    portal_id: str = Field(..., description="Portal configuration ID")
    auth_method: AuthMethodType = Field(..., description="Authentication method")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    client_mac: Optional[str] = Field(None, description="Client MAC address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    device_info: Optional[Dict[str, Any]] = Field(
        None, description="Device information"
    )


class EmailAuthRequest(AuthenticationRequest):
    """Email authentication request."""

    email: str = Field(..., description="User email address")
    verification_code: Optional[str] = Field(
        None, description="Email verification code"
    )
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")


class SocialAuthRequest(AuthenticationRequest):
    """Social media authentication request."""

    provider: str = Field(..., description="Social provider (google, facebook, etc.)")
    code: Optional[str] = Field(None, description="OAuth authorization code")
    state: Optional[str] = Field(None, description="OAuth state parameter")


class VoucherAuthRequest(AuthenticationRequest):
    """Voucher authentication request."""

    voucher_code: str = Field(..., min_length=4, description="Voucher code")


class RadiusAuthRequest(AuthenticationRequest):
    """RADIUS authentication request."""

    username: str = Field(..., description="RADIUS username")
    password: str = Field(..., description="RADIUS password")


class AuthenticationResponse(BaseModel):
    """Authentication response."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(..., description="Authentication success status")
    session_id: Optional[str] = Field(None, description="Session ID if successful")
    session_token: Optional[str] = Field(None, description="Session token")
    expires_at: Optional[datetime] = Field(None, description="Session expiration")
    user_id: Optional[str] = Field(None, description="User ID")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    redirect_url: Optional[str] = Field(None, description="Redirect URL for OAuth")
    requires_verification: bool = Field(
        default=False, description="Requires additional verification"
    )


# Session Schemas
class SessionResponse(TenantAwareSchema):
    """Session information response."""

    id: str = Field(..., description="Session ID")
    session_token: str = Field(..., description="Session token")
    portal_id: str = Field(..., description="Portal ID")
    user_id: Optional[str] = Field(None, description="User ID")
    customer_id: Optional[str] = Field(None, description="Customer ID")

    # Client info
    client_ip: Optional[str] = Field(None, description="Client IP")
    client_mac: Optional[str] = Field(None, description="Client MAC")
    device_type: Optional[str] = Field(None, description="Device type")

    # Timing
    start_time: datetime = Field(..., description="Session start time")
    expires_at: datetime = Field(..., description="Session expiration")
    last_activity: datetime = Field(..., description="Last activity time")

    # Usage
    bytes_downloaded: int = Field(..., description="Bytes downloaded")
    bytes_uploaded: int = Field(..., description="Bytes uploaded")
    duration_minutes: Optional[int] = Field(None, description="Session duration")

    # Status
    session_status: SessionStatus = Field(..., description="Session status")
    auth_method_used: AuthMethodType = Field(..., description="Authentication method")


class SessionTerminateRequest(BaseModel):
    """Request to terminate a session."""

    reason: str = Field(default="User logout", description="Termination reason")


class SessionListResponse(BaseModel):
    """List of sessions response."""

    sessions: List[SessionResponse] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total session count")
    active: int = Field(..., description="Active session count")


# Voucher Schemas
class VoucherBase(BaseModel):
    """Base voucher schema."""

    duration_minutes: int = Field(..., ge=1, description="Access duration in minutes")
    data_limit_mb: int = Field(default=0, ge=0, description="Data limit in MB")
    bandwidth_limit_down: int = Field(
        default=0, ge=0, description="Download bandwidth limit"
    )
    bandwidth_limit_up: int = Field(
        default=0, ge=0, description="Upload bandwidth limit"
    )
    max_devices: int = Field(
        default=1, ge=1, le=10, description="Maximum devices per voucher"
    )
    price: float = Field(default=0.0, ge=0, description="Voucher price")
    currency: str = Field(default="USD", description="Currency code")
    valid_until: Optional[datetime] = Field(None, description="Expiration date")


class VoucherCreateRequest(VoucherBase):
    """Request to create vouchers."""

    portal_id: str = Field(..., description="Portal ID")
    quantity: int = Field(
        default=1, ge=1, le=1000, description="Number of vouchers to create"
    )
    batch_name: Optional[str] = Field(None, description="Batch name for bulk creation")
    generation_notes: Optional[str] = Field(None, description="Generation notes")


class VoucherResponse(VoucherBase, TenantAwareSchema):
    """Voucher information response."""

    id: str = Field(..., description="Voucher ID")
    code: str = Field(..., description="Voucher code")
    portal_id: str = Field(..., description="Portal ID")
    batch_id: Optional[str] = Field(None, description="Batch ID")

    # Status
    voucher_status: VoucherStatus = Field(..., description="Voucher status")
    redemption_count: int = Field(..., description="Times redeemed")

    # Dates
    valid_from: datetime = Field(..., description="Valid from date")
    created_at: datetime = Field(..., description="Creation date")
    first_redeemed_at: Optional[datetime] = Field(
        None, description="First redemption date"
    )
    last_redeemed_at: Optional[datetime] = Field(
        None, description="Last redemption date"
    )


class VoucherBatchCreateRequest(BaseModel):
    """Request to create a voucher batch."""

    name: str = Field(..., description="Batch name")
    description: Optional[str] = Field(None, description="Batch description")
    voucher_count: int = Field(..., ge=1, le=10000, description="Number of vouchers")
    voucher_template: VoucherBase = Field(..., description="Template for vouchers")


class VoucherBatchResponse(TenantAwareSchema):
    """Voucher batch response."""

    id: str = Field(..., description="Batch ID")
    name: str = Field(..., description="Batch name")
    description: Optional[str] = Field(None, description="Batch description")
    voucher_count: int = Field(..., description="Total voucher count")
    generated_count: int = Field(..., description="Generated voucher count")
    created_at: datetime = Field(..., description="Creation date")


# Portal Customization Schemas
class PortalCustomizationBase(BaseModel):
    """Base portal customization schema."""

    company_name: Optional[str] = Field(
        None, max_length=255, description="Company name"
    )
    logo_url: Optional[str] = Field(None, description="Logo URL")
    background_url: Optional[str] = Field(None, description="Background image URL")

    # Colors
    primary_color: Optional[str] = Field(
        None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Primary color"
    )
    secondary_color: Optional[str] = Field(
        None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Secondary color"
    )

    # Content
    welcome_message: Optional[str] = Field(None, description="Welcome message")
    footer_text: Optional[str] = Field(None, description="Footer text")

    # Contact
    support_email: Optional[str] = Field(None, description="Support email")
    support_phone: Optional[str] = Field(None, description="Support phone")
    website_url: Optional[str] = Field(None, description="Website URL")

    # Legal
    terms_of_service_url: Optional[str] = Field(
        None, description="Terms of service URL"
    )
    privacy_policy_url: Optional[str] = Field(None, description="Privacy policy URL")


class PortalCustomizationUpdate(PortalCustomizationBase):
    """Schema for updating portal customization."""

    pass


class PortalCustomizationResponse(PortalCustomizationBase, TenantAwareSchema):
    """Portal customization response."""

    id: str = Field(..., description="Customization ID")
    portal_id: str = Field(..., description="Portal ID")
    created_at: datetime = Field(..., description="Creation date")
    updated_at: datetime = Field(..., description="Last update date")


# Analytics Schemas
class UsageStatsRequest(BaseModel):
    """Request for usage statistics."""

    portal_id: Optional[str] = Field(None, description="Portal ID filter")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
    period_type: str = Field(
        default="day", description="Period type (hour, day, week, month)"
    )


class UsageStatsResponse(BaseModel):
    """Usage statistics response."""

    portal_id: str = Field(..., description="Portal ID")
    period: str = Field(..., description="Time period")

    # Session stats
    total_sessions: int = Field(..., description="Total sessions")
    unique_users: int = Field(..., description="Unique users")
    avg_session_duration: float = Field(
        ..., description="Average session duration (minutes)"
    )

    # Data usage
    total_bytes_downloaded: int = Field(..., description="Total bytes downloaded")
    total_bytes_uploaded: int = Field(..., description="Total bytes uploaded")

    # Breakdown
    auth_method_breakdown: Dict[str, int] = Field(
        ..., description="Authentication method breakdown"
    )
    device_type_breakdown: Dict[str, int] = Field(
        ..., description="Device type breakdown"
    )

    # Revenue
    total_revenue: float = Field(..., description="Total revenue")


# Error Schemas
class ErrorDetail(BaseModel):
    """Error detail schema."""

    field: Optional[str] = Field(None, description="Field name if field-specific error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """API error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[List[ErrorDetail]] = Field(
        None, description="Detailed error information"
    )
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


# Pagination Schemas
class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Page size")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    total: int = Field(..., description="Total items")
    page: int = Field(..., description="Current page")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total pages")

    @classmethod
    def create(
        cls, items: List[Any], total: int, page: int, size: int
    ) -> "PaginatedResponse":
        """Create a paginated response."""
        pages = (total + size - 1) // size  # Ceiling division
        return cls(total=total, page=page, size=size, pages=pages)
