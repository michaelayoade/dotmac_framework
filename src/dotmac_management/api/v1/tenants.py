"""
Tenant Management API

Provides comprehensive tenant lifecycle management including:
- Tenant signup and onboarding with validation
- Automated provisioning and infrastructure setup
- Multi-region deployment and scaling
- Tenant status monitoring and health checks
- Deprovisioning and cleanup workflows

Supports multi-tenant SaaS architecture with isolated tenant environments,
configurable plans, and automated resource allocation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, validator
import secrets
import re
import time
from datetime import datetime

from dotmac_shared.auth.dependencies import get_current_active_user, get_current_active_superuser
from dotmac_shared.auth.models import User
from dotmac_shared.database.base import get_db_session
from dotmac_shared.observability.logging import get_logger
from dotmac_shared.api.response import APIResponse
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.exceptions import StandardExceptions, tenant_not_found, subdomain_taken
from dotmac_shared.validation.common_validators import CommonValidators
from dotmac_shared.api.dependencies import (
    StandardDependencies,
    get_standard_deps
)
from dotmac_management.models.tenant import CustomerTenant, TenantStatus, TenantPlan
from dotmac_management.services.tenant_provisioning import TenantProvisioningService

logger = get_logger(__name__)
router = APIRouter(
    prefix="/tenants",
    tags=["Tenant Management"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"}
    }
)


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


@router.post(
    "/",
    response_model=APIResponse[TenantResponse],
    summary="Create New Tenant",
    description="""
    Create a new tenant and initiate the automated provisioning process.
    
    **Business Context:**
    This endpoint handles the complete tenant onboarding workflow including:
    - Tenant data validation and subdomain uniqueness checking
    - Multi-region deployment configuration
    - Plan-based resource allocation and feature enablement
    - Background provisioning job scheduling
    
    **Provisioning Process:**
    1. Validates signup data and checks subdomain availability
    2. Creates tenant record with initial status 'REQUESTED'
    3. Generates unique tenant identifier
    4. Queues background provisioning job
    5. Returns tenant details with provisioning status endpoint
    
    **Multi-Region Support:**
    - Supports deployment to US, EU, and APAC regions
    - Configurable based on customer requirements
    - Automatic resource allocation per region
    """,
    responses={
        201: {
            "description": "Tenant created and provisioning started",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Tenant 'acme' created successfully. Provisioning started.",
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "tenant_id": "tenant-acme-abc123",
                            "subdomain": "acme",
                            "company_name": "Acme Corporation",
                            "status": "REQUESTED",
                            "plan": "STARTER",
                            "region": "us-east-1",
                            "admin_email": "admin@acme.com",
                            "created_at": "2024-01-15T10:30:00Z",
                            "provisioning_started_at": "2024-01-15T10:30:05Z"
                        }
                    }
                }
            }
        },
        409: {"description": "Subdomain already taken"},
        400: {"description": "Invalid signup data provided"},
        500: {"description": "Tenant creation failed"}
    },
    tags=["Tenant Management"],
    operation_id="createTenant"
)
@standard_exception_handler
async def create_tenant(
    signup_request: TenantSignupRequest,
    background_tasks: BackgroundTasks,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> APIResponse[TenantResponse]:
    """
    Create a new tenant and initiate the automated provisioning process.
    
    Args:
        signup_request: Complete tenant signup information including company details,
                       admin user information, plan selection, and regional preferences
        background_tasks: FastAPI background task manager for provisioning jobs
        deps: Standard dependencies including database session and authentication
        
    Returns:
        APIResponse[TenantResponse]: Created tenant details with provisioning status
        
    Raises:
        HTTPException: 409 if subdomain is already taken
        HTTPException: 400 if signup data validation fails
        HTTPException: 500 if database operation or provisioning queue fails
    """
    start_time = time.time()
    
    # Input validation logging for security auditing
    logger.info("Tenant creation requested", extra={
        "user_id": getattr(deps.current_user, 'id', None),
        "user_email": getattr(deps.current_user, 'email', None),
        "requested_subdomain": signup_request.subdomain,
        "company_name": signup_request.company_name,
        "admin_email": signup_request.admin_email,
        "plan": signup_request.plan.value if signup_request.plan else None,
        "region": signup_request.region,
        "operation": "create_tenant"
    })
    
    try:
        # Check if subdomain is already taken
        existing_tenant = await deps.db.execute(
            select(CustomerTenant).where(CustomerTenant.subdomain == signup_request.subdomain)
        )
        existing = existing_tenant.scalar_one_or_none()
        
        if existing:
            logger.warning("Subdomain already taken", extra={
                "user_id": getattr(deps.current_user, 'id', None),
                "requested_subdomain": signup_request.subdomain,
                "existing_tenant_id": getattr(existing, 'tenant_id', None),
                "conflict": True,
                "operation": "create_tenant"
            })
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
            owner_id=deps.current_user.id,
            admin_email=signup_request.admin_email,
            admin_name=signup_request.admin_name,
            billing_email=signup_request.billing_email or signup_request.admin_email,
            payment_method_id=signup_request.payment_method_id,
            enabled_features=signup_request.enabled_features,
            settings={
                "source": signup_request.source,
                "referrer": signup_request.referrer,
                "signup_timestamp": datetime.utcnow().isoformat(),
                "created_by": getattr(deps.current_user, 'email', None)
            },
            status=TenantStatus.REQUESTED,
            provisioning_started_at=datetime.utcnow()
        )
        
        # Save tenant to database
        deps.db.add(tenant)
        await deps.db.commit()
        await deps.db.refresh(tenant)
        
        logger.info("Tenant record created in database", extra={
            "user_id": getattr(deps.current_user, 'id', None),
            "tenant_id": tenant_id,
            "subdomain": signup_request.subdomain,
            "company_name": signup_request.company_name,
            "plan": signup_request.plan.value if signup_request.plan else None,
            "operation": "create_tenant"
        })
        
        # Queue provisioning in background
        provisioning_service = TenantProvisioningService()
        background_tasks.add_task(
            provisioning_service.provision_tenant,
            tenant.id,
            deps.db
        )
        
        logger.info("Provisioning job queued", extra={
            "user_id": getattr(deps.current_user, 'id', None),
            "tenant_id": tenant_id,
            "subdomain": signup_request.subdomain,
            "operation": "create_tenant"
        })
        
        # Convert to response model
        tenant_response = TenantResponse.model_validate(tenant)
        
        # Log successful creation with performance metrics
        execution_time = time.time() - start_time
        logger.info("Tenant created successfully", extra={
            "user_id": getattr(deps.current_user, 'id', None),
            "tenant_id": tenant_id,
            "subdomain": signup_request.subdomain,
            "company_name": signup_request.company_name,
            "plan": signup_request.plan.value if signup_request.plan else None,
            "execution_time_ms": round(execution_time * 1000, 2),
            "operation": "create_tenant",
            "status": "success"
        })
        
        # Performance logging for slow operations
        if execution_time > 3.0:
            logger.warning("Slow tenant creation detected", extra={
                "tenant_id": tenant_id,
                "subdomain": signup_request.subdomain,
                "execution_time_ms": round(execution_time * 1000, 2),
                "performance_threshold_exceeded": True,
                "operation": "create_tenant"
            })
        
        return APIResponse(
            success=True,
            message=f"Tenant '{signup_request.subdomain}' created successfully. Provisioning started.",
            data=tenant_response
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Database rollback
        await deps.db.rollback()
        
        # Log unexpected errors with full context
        logger.error("Unexpected error creating tenant", extra={
            "user_id": getattr(deps.current_user, 'id', None),
            "requested_subdomain": signup_request.subdomain,
            "company_name": signup_request.company_name,
            "error": str(e),
            "error_type": type(e).__name__,
            "operation": "create_tenant"
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tenant"
        )


@router.get(
    "/",
    response_model=APIResponse[List[TenantResponse]],
    summary="List Tenants",
    description="""
    Retrieve a paginated list of tenants with optional filtering and sorting.
    
    **Business Context:**
    This endpoint provides comprehensive tenant management capabilities for administrators,
    enabling oversight of all tenant deployments across regions and plans.
    
    **Filtering Options:**
    - Filter by tenant status (REQUESTED, PROVISIONING, ACTIVE, etc.)
    - Filter by subscription plan (STARTER, PROFESSIONAL, ENTERPRISE)
    - Pagination support for large tenant bases
    
    **Use Cases:**
    - Administrative dashboards and reporting
    - Tenant health monitoring and status tracking
    - Resource planning and capacity management
    - Billing and subscription management workflows
    """,
    responses={
        200: {
            "description": "List of tenants retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Retrieved 25 tenants",
                        "data": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "tenant_id": "tenant-acme-abc123",
                                "subdomain": "acme",
                                "company_name": "Acme Corporation",
                                "status": "ACTIVE",
                                "plan": "PROFESSIONAL",
                                "region": "us-east-1",
                                "health_status": "healthy",
                                "created_at": "2024-01-15T10:30:00Z"
                            }
                        ]
                    }
                }
            }
        },
        500: {"description": "Failed to retrieve tenant list"}
    },
    tags=["Tenant Management"],
    operation_id="listTenants"
)
async def list_tenants(
    status_filter: Optional[TenantStatus] = Query(
        None,
        description="Filter tenants by status (e.g., ACTIVE, PROVISIONING, FAILED)",
        example="ACTIVE"
    ),
    plan_filter: Optional[TenantPlan] = Query(
        None,
        description="Filter tenants by subscription plan",
        example="PROFESSIONAL"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Maximum number of tenants to return (1-100)",
        example=25
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of tenants to skip for pagination",
        example=0
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
) -> APIResponse[List[TenantResponse]]:
    """
    Retrieve a paginated list of tenants with optional filtering and sorting.
    
    Args:
        status_filter: Optional filter by tenant status
        plan_filter: Optional filter by subscription plan
        limit: Maximum number of results to return (1-100)
        offset: Number of results to skip for pagination
        deps: Standard dependencies including database session and authentication
        
    Returns:
        APIResponse[List[TenantResponse]]: Paginated list of tenant information
        
    Raises:
        HTTPException: 500 if database query fails
    """
    
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


@router.get(
    "/{tenant_id}",
    response_model=APIResponse[TenantResponse],
    summary="Get Tenant Details",
    description="""
    Retrieve detailed information about a specific tenant by ID.
    
    **Business Context:**
    This endpoint provides comprehensive tenant information including current status,
    provisioning details, health metrics, and configuration settings.
    
    **Information Provided:**
    - Tenant identification and branding details
    - Current provisioning and operational status
    - Plan and feature configuration
    - Health status and performance metrics
    - Administrative contact information
    """,
    responses={
        200: {
            "description": "Tenant details retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Tenant retrieved successfully",
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "tenant_id": "tenant-acme-abc123",
                            "subdomain": "acme",
                            "company_name": "Acme Corporation",
                            "status": "ACTIVE",
                            "plan": "PROFESSIONAL",
                            "domain": "acme.dotmac.app",
                            "health_status": "healthy",
                            "created_at": "2024-01-15T10:30:00Z",
                            "provisioning_completed_at": "2024-01-15T10:45:00Z"
                        }
                    }
                }
            }
        },
        404: {"description": "Tenant not found"},
        500: {"description": "Failed to retrieve tenant"}
    },
    tags=["Tenant Management"],
    operation_id="getTenant"
)
async def get_tenant(
    tenant_id: str = Path(
        ...,
        description="Unique identifier of the tenant",
        example="tenant-acme-abc123"
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
) -> APIResponse[TenantResponse]:
    """
    Retrieve detailed information about a specific tenant by ID.
    
    Args:
        tenant_id: The unique tenant identifier
        deps: Standard dependencies including database session and authentication
        
    Returns:
        APIResponse[TenantResponse]: Complete tenant information and status
        
    Raises:
        HTTPException: 404 if tenant not found
        HTTPException: 500 if database query fails
    """
    
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


@router.get(
    "/{tenant_id}/status",
    response_model=APIResponse[TenantProvisioningStatus],
    summary="Get Tenant Provisioning Status",
    description="""
    Retrieve detailed provisioning status and progress for a specific tenant.
    
    **Business Context:**
    This endpoint provides real-time visibility into the tenant provisioning process,
    enabling administrators and customers to track deployment progress and identify issues.
    
    **Status Information:**
    - Current provisioning step and overall progress percentage
    - Estimated completion time based on historical data
    - Detailed provisioning logs and error messages
    - Resource allocation and infrastructure status
    
    **Provisioning Stages:**
    1. REQUESTED (5%) - Initial signup validation
    2. VALIDATING (10%) - Configuration validation
    3. QUEUED (15%) - Waiting in provisioning queue
    4. PROVISIONING (40%) - Infrastructure creation
    5. MIGRATING (70%) - Database and data setup
    6. SEEDING (85%) - Initial data population
    7. TESTING (95%) - Health checks and validation
    8. READY/ACTIVE (100%) - Fully operational
    """,
    responses={
        200: {
            "description": "Provisioning status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Provisioning status retrieved",
                        "data": {
                            "tenant_id": "tenant-acme-abc123",
                            "status": "PROVISIONING",
                            "progress_percentage": 65,
                            "current_step": "Setting up database",
                            "estimated_completion": "2024-01-15T11:00:00Z",
                            "error_message": None,
                            "logs": [
                                {
                                    "timestamp": "2024-01-15T10:30:00Z",
                                    "message": "Infrastructure provisioning started",
                                    "level": "INFO"
                                }
                            ]
                        }
                    }
                }
            }
        },
        404: {"description": "Tenant not found"},
        500: {"description": "Failed to retrieve provisioning status"}
    },
    tags=["Tenant Management"],
    operation_id="getTenantProvisioningStatus"
)
async def get_tenant_provisioning_status(
    tenant_id: str = Path(
        ...,
        description="Unique identifier of the tenant",
        example="tenant-acme-abc123"
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
) -> APIResponse[TenantProvisioningStatus]:
    """
    Retrieve detailed provisioning status and progress for a specific tenant.
    
    Args:
        tenant_id: The unique tenant identifier
        deps: Standard dependencies including database session and authentication
        
    Returns:
        APIResponse[TenantProvisioningStatus]: Detailed provisioning status and logs
        
    Raises:
        HTTPException: 404 if tenant not found
        HTTPException: 500 if status retrieval fails
    """
    
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
    deps: StandardDependencies = Depends(get_standard_deps)
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


@router.delete(
    "/{tenant_id}",
    summary="Delete Tenant",
    description="""
    Mark a tenant for deprovisioning and cleanup.
    
    **Business Context:**
    This operation initiates the tenant deprovisioning process, which includes:
    - Data backup and archival (if configured)
    - Resource cleanup and infrastructure teardown
    - DNS and domain cleanup
    - Billing and subscription termination
    
    **Deprovisioning Process:**
    1. Tenant status changed to DEPROVISIONING
    2. Background cleanup job scheduled
    3. Customer data archived according to retention policy
    4. Infrastructure resources released
    5. Billing and subscriptions terminated
    
    ⚠️ **WARNING**: This operation cannot be undone. All tenant data will be
    permanently deleted according to the data retention policy.
    """,
    responses={
        200: {
            "description": "Tenant marked for deprovisioning",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Tenant 'tenant-acme-abc123' marked for deprovisioning"
                    }
                }
            }
        },
        404: {"description": "Tenant not found"},
        500: {"description": "Failed to initiate tenant deletion"}
    },
    tags=["Tenant Management"],
    operation_id="deleteTenant"
)
@standard_exception_handler
async def delete_tenant(
    tenant_id: str = Path(
        ...,
        description="Unique identifier of the tenant to delete",
        example="tenant-acme-abc123"
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
) -> APIResponse:
    """
    Mark a tenant for deprovisioning and cleanup.
    
    Args:
        tenant_id: The unique tenant identifier
        deps: Standard dependencies including database session and authentication
        
    Returns:
        APIResponse: Confirmation of deprovisioning initiation
        
    Raises:
        HTTPException: 404 if tenant not found
        HTTPException: 500 if deprovisioning fails to start
    """
    start_time = time.time()
    
    # Input validation logging for security auditing
    logger.info("Tenant deletion requested", extra={
        "user_id": getattr(deps.current_user, 'id', None),
        "user_email": getattr(deps.current_user, 'email', None),
        "tenant_id": tenant_id,
        "operation": "delete_tenant",
        "critical_operation": True
    })
    
    try:
        result = await deps.db.execute(
            select(CustomerTenant).where(CustomerTenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.warning("Tenant not found for deletion", extra={
                "user_id": getattr(deps.current_user, 'id', None),
                "tenant_id": tenant_id,
                "operation": "delete_tenant"
            })
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found"
            )
        
        # Store tenant details for audit logging before status change
        company_name = getattr(tenant, 'company_name', None)
        subdomain = getattr(tenant, 'subdomain', None)
        current_status = getattr(tenant, 'status', None)
        
        # Mark for deprovisioning (actual cleanup would be done by background job)
        tenant.status = TenantStatus.DEPROVISIONING
        await deps.db.commit()
        
        # Log successful deletion marking with performance metrics
        execution_time = time.time() - start_time
        logger.warning("Tenant marked for deprovisioning", extra={
            "user_id": getattr(deps.current_user, 'id', None),
            "user_email": getattr(deps.current_user, 'email', None),
            "tenant_id": tenant_id,
            "company_name": company_name,
            "subdomain": subdomain,
            "previous_status": current_status.value if current_status else None,
            "execution_time_ms": round(execution_time * 1000, 2),
            "operation": "delete_tenant",
            "status": "success",
            "critical_operation": True
        })
        
        return APIResponse(
            success=True,
            message=f"Tenant '{tenant_id}' marked for deprovisioning"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Database rollback
        await deps.db.rollback()
        
        # Log unexpected errors with full context
        logger.error("Unexpected error deleting tenant", extra={
            "user_id": getattr(deps.current_user, 'id', None),
            "tenant_id": tenant_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "operation": "delete_tenant",
            "critical_operation": True
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tenant"
        )