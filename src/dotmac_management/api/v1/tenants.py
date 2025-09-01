"""
Tenant Management API
Handles tenant signup, provisioning, and lifecycle management
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, validator
import secrets
import re
from datetime import datetime

from dotmac_shared.auth.dependencies import get_current_active_user, get_current_active_superuser
from dotmac_shared.auth.models import User
from dotmac_shared.database.base import get_db_session
from dotmac_shared.core.logging import get_logger
from dotmac_shared.api.response import APIResponse
from dotmac_shared.api.exceptions import StandardExceptions, tenant_not_found, subdomain_taken
from dotmac_shared.validation.common_validators import CommonValidators
from dotmac_management.models.tenant import CustomerTenant, TenantStatus, TenantPlan
from dotmac_management.services.tenant_provisioning import TenantProvisioningService

logger = get_logger(__name__)
router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantSignupRequest(BaseModel):
    """Tenant signup request schema"""
    
    # Company information
    company_name: str
    subdomain: str
    
    # Admin user information
    admin_name: str
    admin_email: EmailStr
    
    # Service configuration
    plan: TenantPlan = TenantPlan.STARTER
    region: str = "us-east-1"
    
    # Optional
    description: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    payment_method_id: Optional[str] = None
    
    # Features
    enabled_features: List[str] = []
    
    # Marketing/source tracking
    source: Optional[str] = None
    referrer: Optional[str] = None
    
    @validator('company_name')
    def validate_company_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Company name must be at least 2 characters')
        if len(v.strip()) > 100:
            raise ValueError('Company name must be less than 100 characters')
        return v.strip()
    
    @validator('subdomain')
    def validate_subdomain(cls, v):
        if not v:
            raise ValueError('Subdomain is required')
        
        # Clean subdomain
        subdomain = v.lower().strip()
        
        # Validate format: letters, numbers, hyphens only
        if not re.match(r'^[a-z0-9-]+$', subdomain):
            raise ValueError('Subdomain can only contain lowercase letters, numbers, and hyphens')
        
        # Length limits
        if len(subdomain) < 3:
            raise ValueError('Subdomain must be at least 3 characters')
        if len(subdomain) > 30:
            raise ValueError('Subdomain must be less than 30 characters')
        
        # Cannot start or end with hyphen
        if subdomain.startswith('-') or subdomain.endswith('-'):
            raise ValueError('Subdomain cannot start or end with a hyphen')
        
        # Reserved subdomains
        reserved = ['api', 'www', 'admin', 'app', 'mail', 'ftp', 'blog', 'shop', 'test', 'staging', 'dev']
        if subdomain in reserved:
            raise ValueError(f'Subdomain "{subdomain}" is reserved')
        
        return subdomain
    
    @validator('admin_name')
    def validate_admin_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Admin name must be at least 2 characters')
        return v.strip()
    
    @validator('region')
    def validate_region(cls, v):
        allowed_regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
        if v not in allowed_regions:
            raise ValueError(f'Region must be one of: {allowed_regions}')
        return v


class TenantResponse(BaseModel):
    """Tenant response schema"""
    
    id: str
    tenant_id: str
    subdomain: str
    name: str
    company_name: str
    status: TenantStatus
    plan: TenantPlan
    domain: Optional[str]
    admin_email: str
    created_at: datetime
    provisioning_started_at: Optional[datetime]
    provisioning_completed_at: Optional[datetime]
    health_status: str
    
    class Config:
        from_attributes = True


class TenantProvisioningStatus(BaseModel):
    """Tenant provisioning status response"""
    
    tenant_id: str
    status: TenantStatus
    progress_percentage: int
    current_step: Optional[str]
    estimated_completion: Optional[datetime]
    error_message: Optional[str]
    logs: List[Dict[str, Any]]


@router.post("/", response_model=APIResponse[TenantResponse])
async def create_tenant(
    signup_request: TenantSignupRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_superuser),  # Only superusers can create tenants initially
    db: Session = Depends(get_db_session)
) -> APIResponse[TenantResponse]:
    """
    Create a new tenant and start provisioning process
    
    This endpoint:
    1. Validates signup data
    2. Creates tenant record in database
    3. Queues provisioning job in background
    4. Returns tenant details and provisioning status URL
    """
    
    try:
        # Check if subdomain is already taken
        existing_tenant = db.query(CustomerTenant).filter_by(
            subdomain=signup_request.subdomain
        ).first()
        
        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Subdomain '{signup_request.subdomain}' is already taken"
            )
        
        # Generate unique tenant ID
        tenant_id = f"tenant-{signup_request.subdomain}-{secrets.token_hex(4)}"
        
        # Create tenant record
        tenant = CustomerTenant(
            tenant_id=tenant_id,
            subdomain=signup_request.subdomain,
            name=signup_request.company_name,
            company_name=signup_request.company_name,
            description=signup_request.description,
            plan=signup_request.plan,
            region=signup_request.region,
            owner_id=current_user.id,  # For now, admin creates tenants
            admin_email=signup_request.admin_email,
            admin_name=signup_request.admin_name,
            billing_email=signup_request.billing_email or signup_request.admin_email,
            payment_method_id=signup_request.payment_method_id,
            enabled_features=signup_request.enabled_features,
            settings={
                "source": signup_request.source,
                "referrer": signup_request.referrer,
                "signup_timestamp": datetime.utcnow().isoformat(),
                "created_by": current_user.email
            },
            status=TenantStatus.REQUESTED,
            provisioning_started_at=datetime.utcnow()
        )
        
        # Save tenant to database
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        
        logger.info(f"Tenant created: {tenant_id} for company {signup_request.company_name}")
        
        # Queue provisioning in background
        provisioning_service = TenantProvisioningService()
        background_tasks.add_task(
            provisioning_service.provision_tenant,
            tenant.id,
            db
        )
        
        # Convert to response model
        tenant_response = TenantResponse.from_orm(tenant)
        
        return APIResponse(
            success=True,
            message=f"Tenant '{signup_request.subdomain}' created successfully. Provisioning started.",
            data=tenant_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tenant"
        )


@router.get("/", response_model=APIResponse[List[TenantResponse]])
async def list_tenants(
    status_filter: Optional[TenantStatus] = None,
    plan_filter: Optional[TenantPlan] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> APIResponse[List[TenantResponse]]:
    """List tenants with optional filtering"""
    
    try:
        query = db.query(CustomerTenant)
        
        # Apply filters
        if status_filter:
            query = query.filter(CustomerTenant.status == status_filter)
        if plan_filter:
            query = query.filter(CustomerTenant.plan == plan_filter)
        
        # Pagination
        tenants = query.offset(offset).limit(limit).all()
        
        tenant_responses = [TenantResponse.from_orm(tenant) for tenant in tenants]
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(tenant_responses)} tenants",
            data=tenant_responses
        )
        
    except Exception as e:
        logger.error(f"Failed to list tenants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tenants"
        )


@router.get("/{tenant_id}", response_model=APIResponse[TenantResponse])
async def get_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> APIResponse[TenantResponse]:
    """Get tenant details by ID"""
    
    tenant = db.query(CustomerTenant).filter_by(tenant_id=tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found"
        )
    
    tenant_response = TenantResponse.from_orm(tenant)
    
    return APIResponse(
        success=True,
        message="Tenant retrieved successfully",
        data=tenant_response
    )


@router.get("/{tenant_id}/status", response_model=APIResponse[TenantProvisioningStatus])
async def get_tenant_provisioning_status(
    tenant_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> APIResponse[TenantProvisioningStatus]:
    """Get detailed provisioning status for a tenant"""
    
    tenant = db.query(CustomerTenant).filter_by(tenant_id=tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found"
        )
    
    # Calculate progress percentage based on status
    progress_map = {
        TenantStatus.REQUESTED: 5,
        TenantStatus.VALIDATING: 10,
        TenantStatus.QUEUED: 15,
        TenantStatus.PROVISIONING: 40,
        TenantStatus.MIGRATING: 70,
        TenantStatus.SEEDING: 85,
        TenantStatus.TESTING: 95,
        TenantStatus.READY: 100,
        TenantStatus.ACTIVE: 100,
        TenantStatus.FAILED: 0,
    }
    
    # Get current step description
    step_descriptions = {
        TenantStatus.REQUESTED: "Processing signup request",
        TenantStatus.VALIDATING: "Validating configuration",
        TenantStatus.QUEUED: "Queued for provisioning",
        TenantStatus.PROVISIONING: "Creating infrastructure",
        TenantStatus.MIGRATING: "Setting up database",
        TenantStatus.SEEDING: "Initializing data",
        TenantStatus.TESTING: "Running health checks",
        TenantStatus.READY: "Tenant ready for use",
        TenantStatus.ACTIVE: "Tenant active and serving traffic",
        TenantStatus.FAILED: "Provisioning failed",
    }
    
    status_response = TenantProvisioningStatus(
        tenant_id=tenant.tenant_id,
        status=tenant.status,
        progress_percentage=progress_map.get(tenant.status, 0),
        current_step=step_descriptions.get(tenant.status),
        estimated_completion=None,  # Would calculate based on provisioning time
        error_message=None,  # Would extract from provisioning logs
        logs=tenant.provisioning_logs or []
    )
    
    return APIResponse(
        success=True,
        message="Provisioning status retrieved",
        data=status_response
    )


@router.post("/{tenant_id}/retry-provisioning")
async def retry_tenant_provisioning(
    tenant_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db_session)
) -> APIResponse:
    """Retry failed tenant provisioning"""
    
    tenant = db.query(CustomerTenant).filter_by(tenant_id=tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found"
        )
    
    if tenant.status not in [TenantStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry provisioning for tenant in status '{tenant.status}'"
        )
    
    # Reset status and retry
    tenant.status = TenantStatus.QUEUED
    tenant.provisioning_started_at = datetime.utcnow()
    db.commit()
    
    # Queue provisioning in background
    provisioning_service = TenantProvisioningService()
    background_tasks.add_task(
        provisioning_service.provision_tenant,
        tenant.id,
        db
    )
    
    logger.info(f"Retrying provisioning for tenant: {tenant_id}")
    
    return APIResponse(
        success=True,
        message=f"Provisioning retry started for tenant '{tenant_id}'"
    )


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db_session)
) -> APIResponse:
    """Delete (deprovision) a tenant"""
    
    tenant = db.query(CustomerTenant).filter_by(tenant_id=tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found"
        )
    
    # Mark for deprovisioning (actual cleanup would be done by background job)
    tenant.status = TenantStatus.DEPROVISIONING
    db.commit()
    
    logger.warning(f"Tenant marked for deprovisioning: {tenant_id} by {current_user.email}")
    
    return APIResponse(
        success=True,
        message=f"Tenant '{tenant_id}' marked for deprovisioning"
    )