"""
Public tenant signup endpoints with email verification.
Allows self-serve tenant provisioning with proper verification.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotmac.application import StandardDependencies, get_standard_deps
from dotmac.communications.notifications import UnifiedNotificationService as NotificationService
from dotmac.database.base import get_db_session
from dotmac.platform.observability.logging import get_logger
from dotmac_management.models.tenant import CustomerTenant, TenantPlan, TenantStatus
from dotmac_management.services.tenant_provisioning import TenantProvisioningService
from dotmac_shared.api.exceptions import StandardExceptions, subdomain_taken
from dotmac_shared.api.rate_limiting_decorators import RateLimitType, rate_limit
from dotmac_shared.api.response import APIResponse
from dotmac_shared.validation.common_validators import ValidatorMixins
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
)
from sqlalchemy.orm import Session

logger = get_logger(__name__)
router = APIRouter(prefix="/public", tags=["public-signup"])


class PublicSignupRequest(BaseModel, ValidatorMixins):
    """Public tenant signup request with comprehensive DRY validation"""

    # Company information
    company_name: str = Field(..., min_length=2, max_length=100)
    subdomain: str = Field(..., min_length=3, max_length=30)

    # Admin user information
    admin_name: str = Field(..., min_length=2, max_length=80)
    admin_email: EmailStr = Field(..., description="Administrator email address")

    # Service configuration
    plan: TenantPlan = Field(default=TenantPlan.STARTER, description="Service plan")
    region: str = Field(default="us-east-1", description="Deployment region")

    # Optional information
    description: Optional[str] = Field(None, max_length=500, description="Company description")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone number")
    billing_email: Optional[EmailStr] = Field(None, description="Billing email if different from admin")

    # Marketing/source tracking
    source: Optional[str] = Field(None, max_length=100, description="Signup source")
    utm_campaign: Optional[str] = Field(None, max_length=100, description="UTM campaign")
    utm_source: Optional[str] = Field(None, max_length=100, description="UTM source")
    utm_medium: Optional[str] = Field(None, max_length=100, description="UTM medium")

    # Terms acceptance
    accept_terms: bool = Field(default=True, description="Accept terms of service")
    accept_privacy: bool = Field(default=True, description="Accept privacy policy")

    # Anti-spam verification
    captcha_token: Optional[str] = Field(None, max_length=1000, description="Captcha verification token")

    @field_validator("description")
    @classmethod
    def validate_description_field(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced description validation"""
        from dotmac_shared.validation.common_validators import CommonValidators

        return CommonValidators.validate_description(v, 500)

    @field_validator("source", "utm_campaign", "utm_source", "utm_medium")
    @classmethod
    def validate_tracking_fields(cls, v: Optional[str], info) -> Optional[str]:
        """Validate marketing tracking fields"""
        if v is None:
            return None

        clean_value = v.strip()
        if len(clean_value) == 0:
            return None

        # Length validation
        if len(clean_value) > 100:
            raise ValueError(f"{info.field_name} must be less than 100 characters")

        # Basic content validation - alphanumeric, spaces, hyphens, underscores
        import re

        if not re.match(r"^[a-zA-Z0-9\s\-_]+$", clean_value):
            raise ValueError(f"{info.field_name} contains invalid characters")

        return clean_value

    @field_validator("captcha_token")
    @classmethod
    def validate_captcha_token(cls, v: Optional[str]) -> Optional[str]:
        """Validate captcha token"""
        if v is None:
            return None

        clean_token = v.strip()
        if len(clean_token) == 0:
            return None

        # Length validation
        if len(clean_token) > 1000:
            raise ValueError("Captcha token is too long")

        # Basic format validation - should be base64-like
        import re

        if not re.match(r"^[a-zA-Z0-9+/=\-_]+$", clean_token):
            raise ValueError("Invalid captcha token format")

        return clean_token

    @field_validator("billing_email")
    @classmethod
    def validate_billing_email(cls, v: Optional[EmailStr], info) -> Optional[EmailStr]:
        """Validate billing email and check if different from admin email"""
        if v is None:
            return None

        # Check if same as admin email (discouraged but not blocked)
        admin_email = info.data.get("admin_email")
        if admin_email and v.lower() == admin_email.lower():
            # Could log a warning but allow it
            pass

        return v


class PublicSignupResponse(BaseModel):
    """Public signup response"""

    success: bool
    message: str
    tenant_id: str
    verification_required: bool
    next_steps: list[str]
    estimated_setup_time: str
    status_check_url: str


class EmailVerificationRequest(BaseModel):
    """Email verification request with validation"""

    tenant_id: str = Field(..., min_length=10, max_length=100, description="Tenant identifier")
    verification_code: str = Field(..., min_length=20, max_length=100, description="Email verification code")

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """Validate tenant ID format"""
        clean_id = v.strip()

        # Basic format validation
        import re

        if not re.match(r"^[a-zA-Z0-9\-]+$", clean_id):
            raise ValueError("Tenant ID contains invalid characters")

        # Should start with tenant- prefix for public signups
        if not clean_id.startswith("tenant-"):
            raise ValueError("Invalid tenant ID format")

        return clean_id

    @field_validator("verification_code")
    @classmethod
    def validate_verification_code(cls, v: str) -> str:
        """Validate verification code format"""
        clean_code = v.strip()

        # Length validation
        if len(clean_code) < 20 or len(clean_code) > 100:
            raise ValueError("Invalid verification code length")

        # Format validation - should be URL-safe base64
        import re

        if not re.match(r"^[a-zA-Z0-9\-_]+$", clean_code):
            raise ValueError("Invalid verification code format")

        return clean_code


@router.post("/signup", response_model=APIResponse[PublicSignupResponse])
@rate_limit(
    max_requests=3,
    time_window_seconds=60,
    rule_type=RateLimitType.PER_IP,
    custom_message="Too many signup attempts. Please wait before trying again.",
)  # Anti-spam for public signups
async def public_tenant_signup(
    signup_request: PublicSignupRequest,
    background_tasks: BackgroundTasks,
    deps: StandardDependencies = Depends(get_standard_deps),
    db: Session = Depends(get_db_session),
) -> APIResponse[PublicSignupResponse]:
    """
    Public self-serve tenant signup with email verification.

    Process:
    1. Validate signup data and check subdomain availability
    2. Create tenant record with PENDING_VERIFICATION status
    3. Send email verification link
    4. Queue provisioning for after verification
    """

    try:
        # TODO: Verify captcha token if provided
        # if signup_request.captcha_token:
        #     if not await verify_captcha(signup_request.captcha_token):
        #         raise HTTPException(status_code=400, detail="Invalid captcha")

        # Check subdomain availability
        existing_tenant = db.query(CustomerTenant).filter_by(subdomain=signup_request.subdomain).first()

        if existing_tenant:
            raise subdomain_taken(signup_request.subdomain)

        # Rate limiting check (basic implementation)
        recent_signups = (
            db.query(CustomerTenant)
            .filter(
                CustomerTenant.admin_email == signup_request.admin_email,
                CustomerTenant.created_at > datetime.now(timezone.utc) - timedelta(hours=1),
            )
            .count()
        )

        if recent_signups >= 3:
            raise StandardExceptions.rate_limited("Too many signup attempts. Please try again later.")

        # Generate tenant ID and verification code
        tenant_id = f"tenant-{signup_request.subdomain}-{secrets.token_hex(4)}"
        verification_code = secrets.token_urlsafe(32)

        # Create tenant record with PENDING_VERIFICATION status
        tenant = CustomerTenant(
            tenant_id=tenant_id,
            subdomain=signup_request.subdomain,
            name=signup_request.company_name,
            company_name=signup_request.company_name,
            description=signup_request.description,
            plan=signup_request.plan,
            region=signup_request.region,
            admin_email=signup_request.admin_email,
            admin_name=signup_request.admin_name,
            billing_email=signup_request.billing_email or signup_request.admin_email,
            phone=signup_request.phone,
            settings={
                "source": signup_request.source,
                "utm_campaign": signup_request.utm_campaign,
                "utm_source": signup_request.utm_source,
                "utm_medium": signup_request.utm_medium,
                "signup_timestamp": datetime.now(timezone.utc).isoformat(),
                "signup_ip": "0.0.0.0",  # Would get from request
                "verification_code": verification_code,
                "verification_expires": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
                "public_signup": True,
            },
            status=TenantStatus.PENDING_VERIFICATION,
            created_at=datetime.now(timezone.utc),
        )

        # Save tenant to database
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        logger.info(f"Public signup received: {tenant_id} for {signup_request.company_name}")

        # Send verification email
        background_tasks.add_task(
            _send_verification_email,
            tenant.admin_email,
            tenant.admin_name,
            tenant.company_name,
            tenant_id,
            verification_code,
            signup_request.subdomain,
        )

        response = PublicSignupResponse(
            success=True,
            message="Signup received! Please check your email to verify your account.",
            tenant_id=tenant_id,
            verification_required=True,
            next_steps=[
                "Check your email for verification link",
                "Click the verification link to confirm your account",
                "Your tenant will be automatically provisioned after verification",
                "You'll receive login details once provisioning is complete",
            ],
            estimated_setup_time="5-10 minutes after verification",
            status_check_url=f"/api/v1/public/signup/{tenant_id}/status",
        )

        return APIResponse(success=True, message="Signup successful! Verification email sent.", data=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Public signup failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Signup failed. Please try again."
        ) from e


@router.post("/verify-email")
@rate_limit(
    max_requests=10,
    time_window_seconds=60,
    rule_type=RateLimitType.PER_IP,
    custom_message="Too many verification attempts. Please wait before trying again.",
)  # Moderate limits for email verification
async def verify_email_and_provision(
    verification_request: EmailVerificationRequest,
    background_tasks: BackgroundTasks,
    deps: StandardDependencies = Depends(get_standard_deps),
    db: Session = Depends(get_db_session),
) -> APIResponse:
    """
    Verify email and start tenant provisioning.
    """

    try:
        # Find tenant by ID
        tenant = (
            db.query(CustomerTenant)
            .filter_by(tenant_id=verification_request.tenant_id, status=TenantStatus.PENDING_VERIFICATION)
            .first()
        )

        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found or already verified")

        # Check verification code and expiry
        settings = tenant.settings or {}
        stored_code = settings.get("verification_code")
        expires_str = settings.get("verification_expires")

        if not stored_code or stored_code != verification_request.verification_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")

        if expires_str:
            expires = datetime.fromisoformat(expires_str)
            if datetime.now(timezone.utc) > expires:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code has expired")

        # Mark as verified and queue provisioning
        tenant.status = TenantStatus.REQUESTED
        tenant.provisioning_started_at = datetime.now(timezone.utc)

        # Clear verification data
        settings["email_verified"] = True
        settings["email_verified_at"] = datetime.now(timezone.utc).isoformat()
        settings.pop("verification_code", None)
        settings.pop("verification_expires", None)
        tenant.settings = settings

        db.commit()

        logger.info(f"Email verified for tenant {tenant.tenant_id}, starting provisioning")

        # Start provisioning
        provisioning_service = TenantProvisioningService()
        background_tasks.add_task(provisioning_service.provision_tenant, tenant.id, db)

        return APIResponse(
            success=True,
            message="Email verified successfully! Your tenant is being provisioned.",
            data={
                "tenant_id": tenant.tenant_id,
                "status": "provisioning_started",
                "estimated_completion": "5-10 minutes",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Verification failed") from e


@router.get("/signup/{tenant_id}/status")
@rate_limit(
    max_requests=20,
    time_window_seconds=60,
    rule_type=RateLimitType.PER_IP,
    custom_message="Too many status check requests. Please wait before trying again.",
)  # Public status endpoint - moderate limits
async def get_signup_status(
    tenant_id: str,
    deps: StandardDependencies = Depends(get_standard_deps),
    db: Session = Depends(get_db_session),
) -> APIResponse:
    """
    Get public signup status (no auth required for transparency).
    """

    try:
        tenant = db.query(CustomerTenant).filter_by(tenant_id=tenant_id).first()

        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

        # Progress mapping for public display
        progress_map = {
            TenantStatus.PENDING_VERIFICATION: {"progress": 10, "message": "Awaiting email verification"},
            TenantStatus.REQUESTED: {"progress": 20, "message": "Verification complete, queued for provisioning"},
            TenantStatus.VALIDATING: {"progress": 25, "message": "Validating configuration"},
            TenantStatus.QUEUED: {"progress": 30, "message": "Queued for provisioning"},
            TenantStatus.PROVISIONING: {"progress": 50, "message": "Creating your infrastructure"},
            TenantStatus.MIGRATING: {"progress": 70, "message": "Setting up database"},
            TenantStatus.SEEDING: {"progress": 85, "message": "Initializing data"},
            TenantStatus.TESTING: {"progress": 95, "message": "Running final checks"},
            TenantStatus.READY: {"progress": 100, "message": "Ready! Check your email for login details"},
            TenantStatus.ACTIVE: {"progress": 100, "message": "Active and ready to use"},
            TenantStatus.FAILED: {"progress": 0, "message": "Provisioning failed - support has been notified"},
        }

        status_info = progress_map.get(tenant.status, {"progress": 0, "message": "Unknown status"})

        return APIResponse(
            success=True,
            message="Status retrieved",
            data={
                "tenant_id": tenant.tenant_id,
                "company_name": tenant.company_name,
                "subdomain": tenant.subdomain,
                "status": tenant.status.value,
                "progress_percentage": status_info["progress"],
                "status_message": status_info["message"],
                "created_at": tenant.created_at.isoformat(),
                "domain": tenant.domain if tenant.status in [TenantStatus.READY, TenantStatus.ACTIVE] else None,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get signup status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get status") from e


async def _send_verification_email(
    email: str, name: str, company: str, tenant_id: str, verification_code: str, subdomain: str
):
    """Send email verification link"""

    try:
        notification_service = NotificationService()

        # Create verification URL
        base_url = "https://signup.yourdomain.com"  # Would be configured
        verification_url = f"{base_url}/verify?tenant_id={tenant_id}&code={verification_code}"

        # Send email
        await notification_service.send_email(
            to_email=email,
            subject=f"Verify your {company} ISP platform signup",
            template="tenant_verification",
            data={
                "name": name,
                "company": company,
                "subdomain": subdomain,
                "verification_url": verification_url,
                "expires_hours": 24,
            },
        )

        logger.info(f"Verification email sent to {email}")

    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")


# Export router
__all__ = ["router"]
