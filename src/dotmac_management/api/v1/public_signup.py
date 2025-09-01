"""
Public tenant signup endpoints with email verification.
Allows self-serve tenant provisioning with proper verification.
"""

import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from dotmac_shared.database.base import get_db_session
from dotmac_shared.core.logging import get_logger
from dotmac_shared.api.response import APIResponse
from dotmac_shared.api.exceptions import StandardExceptions, subdomain_taken
from dotmac_shared.validation.common_validators import ValidatorMixins
from dotmac_shared.notifications.service import NotificationService
from dotmac_management.models.tenant import CustomerTenant, TenantStatus, TenantPlan
from dotmac_management.services.tenant_provisioning import TenantProvisioningService

logger = get_logger(__name__)
router = APIRouter(prefix="/public", tags=["public-signup"])


class PublicSignupRequest(BaseModel, ValidatorMixins):
    """Public tenant signup request with DRY validation"""
    
    # Company information
    company_name: str
    subdomain: str
    
    # Admin user information
    admin_name: str
    admin_email: EmailStr
    
    # Service configuration
    plan: TenantPlan = TenantPlan.STARTER
    region: str = "us-east-1"
    
    # Optional information
    description: Optional[str] = None
    phone: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    
    # Marketing/source tracking
    source: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    
    # Terms acceptance
    accept_terms: bool = True
    accept_privacy: bool = True
    
    # Anti-spam verification
    captcha_token: Optional[str] = None


class PublicSignupResponse(BaseModel):
    """Public signup response"""
    
    success: bool
    message: str
    tenant_id: str
    verification_required: bool
    next_steps: List[str]
    estimated_setup_time: str
    status_check_url: str


class EmailVerificationRequest(BaseModel):
    """Email verification request"""
    tenant_id: str
    verification_code: str


@router.post("/signup", response_model=APIResponse[PublicSignupResponse])
async def public_tenant_signup(
    signup_request: PublicSignupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session)
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
        existing_tenant = db.query(CustomerTenant).filter_by(
            subdomain=signup_request.subdomain
        ).first()
        
        if existing_tenant:
            raise subdomain_taken(signup_request.subdomain)
        
        # Rate limiting check (basic implementation)
        recent_signups = db.query(CustomerTenant).filter(
            CustomerTenant.admin_email == signup_request.admin_email,
            CustomerTenant.created_at > datetime.utcnow() - timedelta(hours=1)
        ).count()
        
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
                "signup_timestamp": datetime.utcnow().isoformat(),
                "signup_ip": "0.0.0.0",  # Would get from request
                "verification_code": verification_code,
                "verification_expires": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                "public_signup": True
            },
            status=TenantStatus.PENDING_VERIFICATION,
            created_at=datetime.utcnow()
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
            signup_request.subdomain
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
                "You'll receive login details once provisioning is complete"
            ],
            estimated_setup_time="5-10 minutes after verification",
            status_check_url=f"/api/v1/public/signup/{tenant_id}/status"
        )
        
        return APIResponse(
            success=True,
            message="Signup successful! Verification email sent.",
            data=response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Public signup failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signup failed. Please try again."
        )


@router.post("/verify-email")
async def verify_email_and_provision(
    verification_request: EmailVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session)
) -> APIResponse:
    """
    Verify email and start tenant provisioning.
    """
    
    try:
        # Find tenant by ID
        tenant = db.query(CustomerTenant).filter_by(
            tenant_id=verification_request.tenant_id,
            status=TenantStatus.PENDING_VERIFICATION
        ).first()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found or already verified"
            )
        
        # Check verification code and expiry
        settings = tenant.settings or {}
        stored_code = settings.get("verification_code")
        expires_str = settings.get("verification_expires")
        
        if not stored_code or stored_code != verification_request.verification_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
        
        if expires_str:
            expires = datetime.fromisoformat(expires_str)
            if datetime.utcnow() > expires:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification code has expired"
                )
        
        # Mark as verified and queue provisioning
        tenant.status = TenantStatus.REQUESTED
        tenant.provisioning_started_at = datetime.utcnow()
        
        # Clear verification data
        settings["email_verified"] = True
        settings["email_verified_at"] = datetime.utcnow().isoformat()
        settings.pop("verification_code", None)
        settings.pop("verification_expires", None)
        tenant.settings = settings
        
        db.commit()
        
        logger.info(f"Email verified for tenant {tenant.tenant_id}, starting provisioning")
        
        # Start provisioning
        provisioning_service = TenantProvisioningService()
        background_tasks.add_task(
            provisioning_service.provision_tenant,
            tenant.id,
            db
        )
        
        return APIResponse(
            success=True,
            message="Email verified successfully! Your tenant is being provisioned.",
            data={
                "tenant_id": tenant.tenant_id,
                "status": "provisioning_started",
                "estimated_completion": "5-10 minutes"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed"
        )


@router.get("/signup/{tenant_id}/status")
async def get_signup_status(
    tenant_id: str,
    db: Session = Depends(get_db_session)
) -> APIResponse:
    """
    Get public signup status (no auth required for transparency).
    """
    
    try:
        tenant = db.query(CustomerTenant).filter_by(tenant_id=tenant_id).first()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
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
                "domain": tenant.domain if tenant.status in [TenantStatus.READY, TenantStatus.ACTIVE] else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get signup status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get status"
        )


async def _send_verification_email(
    email: str, 
    name: str, 
    company: str, 
    tenant_id: str, 
    verification_code: str,
    subdomain: str
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
                "expires_hours": 24
            }
        )
        
        logger.info(f"Verification email sent to {email}")
        
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")


# Export router
__all__ = ["router"]