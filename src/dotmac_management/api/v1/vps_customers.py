from dotmac_shared.api.dependencies import (
    StandardDependencies,
    get_standard_deps
)
"""
Customer VPS Management API
Handles customer-managed VPS deployments and support
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, IPvAnyAddress, field_validator, ConfigDict
import secrets
import asyncio
from datetime import datetime

from dotmac_shared.auth.dependencies import get_current_active_user, get_current_active_superuser
from dotmac_shared.auth.models import User
from dotmac_shared.database.base import get_db_session
from dotmac_shared.observability.logging import get_logger
from dotmac_shared.api.response import APIResponse
from dotmac_shared.api.exceptions import StandardExceptions, standard_exception_handler
from dotmac_shared.validation.common_validators import CommonValidators
from dotmac_management.models.tenant import CustomerTenant, TenantStatus, TenantPlan
from dotmac_management.services.vps_provisioning import VPSProvisioningService
from dotmac_management.services.vps_requirements import VPSRequirementsService
from dotmac_management.models.vps_customer import VPSCustomer, VPSStatus, SupportTier

logger = get_logger(__name__)
router = APIRouter(prefix="/vps-customers", tags=["vps-customers"])


class VPSSetupRequest(BaseModel):
    """Customer VPS setup request schema"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Company information
    company_name: str
    subdomain: str
    
    # Admin user information
    admin_name: str
    admin_email: str
    
    # VPS information
    vps_ip: IPvAnyAddress
    ssh_port: int = 22
    ssh_username: str = "root"
    ssh_key: Optional[str] = None  # Public key for authentication
    ssh_password: Optional[str] = None  # Alternative to key
    
    # Service configuration
    plan: TenantPlan = TenantPlan.STARTER
    support_tier: SupportTier = SupportTier.BASIC
    
    # Optional
    custom_domain: Optional[str] = None
    expected_customers: int = 100
    estimated_traffic: str = "low"  # low, medium, high
    
    # Business information
    contact_phone: Optional[str] = None
    timezone: str = "UTC"
    preferred_backup_time: str = "02:00"
    
    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        return CommonValidators.validate_company_name(v)
    
    @field_validator('subdomain')
    @classmethod
    def validate_subdomain(cls, v: str) -> str:
        return CommonValidators.validate_subdomain(v)
    
    @field_validator('admin_email')
    @classmethod
    def validate_admin_email(cls, v: str) -> str:
        return CommonValidators.validate_email(v)
    
    @field_validator('ssh_port')
    @classmethod
    def validate_ssh_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError('SSH port must be between 1 and 65535')
        return v


class VPSRequirements(BaseModel):
    """VPS requirements response"""
    model_config = ConfigDict(from_attributes=True)
    
    plan: TenantPlan
    expected_customers: int
    
    # Hardware requirements
    min_cpu_cores: int
    recommended_cpu_cores: int
    min_ram_gb: int
    recommended_ram_gb: int
    min_storage_gb: int
    recommended_storage_gb: int
    
    # Network requirements
    min_bandwidth_mbps: int
    monthly_transfer_gb: int
    
    # Software requirements
    supported_os: List[str]
    required_ports: List[int]
    recommended_provider: List[str]
    
    # Estimated costs
    estimated_monthly_cost_usd: Dict[str, int]  # provider -> cost
    setup_fee_usd: int
    monthly_support_fee_usd: int


class VPSCustomerResponse(BaseModel):
    """VPS customer response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    customer_id: str
    company_name: str
    subdomain: str
    status: VPSStatus
    plan: TenantPlan
    support_tier: SupportTier
    
    # VPS information
    vps_ip: str
    custom_domain: Optional[str]
    
    # Status information
    created_at: datetime
    deployment_started_at: Optional[datetime]
    deployment_completed_at: Optional[datetime]
    last_health_check: Optional[datetime]
    health_status: str
    
    # Support information
    setup_instructions_url: Optional[str]
    monitoring_dashboard_url: Optional[str]
    support_portal_url: Optional[str]


class DeploymentStatus(BaseModel):
    """VPS deployment status"""
    model_config = ConfigDict(from_attributes=True)
    
    customer_id: str
    status: VPSStatus
    progress_percentage: int
    current_step: Optional[str]
    estimated_completion_minutes: Optional[int]
    error_message: Optional[str]
    logs: List[Dict[str, Any]]
    
    # Connection test results
    ssh_connection_test: Optional[bool]
    server_requirements_check: Optional[bool]
    deployment_readiness: Optional[bool]


@router.post("/requirements", response_model=APIResponse[VPSRequirements])
@standard_exception_handler
async def get_vps_requirements(
    plan: TenantPlan = TenantPlan.STARTER,
    expected_customers: int = 100,
    estimated_traffic: str = "low",
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[VPSRequirements]:
    """
    Get VPS requirements for a given plan and usage expectations
    """
    
    requirements_service = VPSRequirementsService()
    requirements = await requirements_service.calculate_requirements(
        plan=plan,
        expected_customers=expected_customers,
        estimated_traffic=estimated_traffic
    )
    
    return APIResponse(
        success=True,
        message=f"VPS requirements calculated for {plan} plan",
        data=requirements
    )


@router.post("/", response_model=APIResponse[VPSCustomerResponse])
@standard_exception_handler
async def setup_vps_customer(
    setup_request: VPSSetupRequest,
    background_tasks: BackgroundTasks,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> APIResponse[VPSCustomerResponse]:
    """
    Set up a new VPS customer and start deployment process
    
    This endpoint:
    1. Validates VPS accessibility and requirements
    2. Creates customer record in database
    3. Generates setup instructions
    4. Queues deployment job in background
    5. Returns customer details and access URLs
    """
    
    try:
        # Check if subdomain is already taken
        existing_customer = db.query(VPSCustomer).filter_by(
            subdomain=setup_request.subdomain
        ).first()
        
        if existing_customer:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Subdomain '{setup_request.subdomain}' is already taken"
            )
        
        # Generate unique customer ID
        customer_id = f"vps-{setup_request.subdomain}-{secrets.token_hex(4)}"
        
        # Create VPS customer record
        vps_customer = VPSCustomer(
            customer_id=customer_id,
            subdomain=setup_request.subdomain,
            company_name=setup_request.company_name,
            admin_email=setup_request.admin_email,
            admin_name=setup_request.admin_name,
            plan=setup_request.plan,
            support_tier=setup_request.support_tier,
            vps_ip=str(setup_request.vps_ip),
            ssh_port=setup_request.ssh_port,
            ssh_username=setup_request.ssh_username,
            ssh_key=setup_request.ssh_key,
            ssh_password_hash=setup_request.ssh_password,  # Should be hashed
            custom_domain=setup_request.custom_domain,
            expected_customers=setup_request.expected_customers,
            estimated_traffic=setup_request.estimated_traffic,
            contact_phone=setup_request.contact_phone,
            timezone=setup_request.timezone,
            preferred_backup_time=setup_request.preferred_backup_time,
            owner_id=current_user.id,
            status=VPSStatus.VALIDATING,
            deployment_started_at=datetime.now(timezone.utc),
            settings={
                "created_by": current_user.email,
                "signup_timestamp": datetime.now(timezone.utc).isoformat(),
                "requirements_checked": False
            }
        )
        
        # Save to database
        db.add(vps_customer)
        db.commit()
        db.refresh(vps_customer)
        
        logger.info(f"VPS customer created: {customer_id} for {setup_request.company_name}")
        
        # Queue deployment validation and setup in background
        provisioning_service = VPSProvisioningService()
        background_tasks.add_task(
            provisioning_service.setup_vps_customer,
            vps_customer.id,
            db
        )
        
        # Generate URLs for customer access
        base_url = "https://admin.yourdomain.com"  # Should come from config
        setup_instructions_url = f"{base_url}/customers/{customer_id}/setup"
        monitoring_dashboard_url = f"{base_url}/customers/{customer_id}/monitoring"
        support_portal_url = f"{base_url}/customers/{customer_id}/support"
        
        # Convert to response model using Pydantic v2 model_validate
        customer_response = VPSCustomerResponse.model_validate({
            "id": str(vps_customer.id),
            "customer_id": customer_id,
            "company_name": setup_request.company_name,
            "subdomain": setup_request.subdomain,
            "status": vps_customer.status,
            "plan": setup_request.plan,
            "support_tier": setup_request.support_tier,
            "vps_ip": str(setup_request.vps_ip),
            "custom_domain": setup_request.custom_domain,
            "created_at": vps_customer.created_at,
            "deployment_started_at": vps_customer.deployment_started_at,
            "deployment_completed_at": vps_customer.deployment_completed_at,
            "last_health_check": vps_customer.last_health_check,
            "health_status": vps_customer.health_status or "checking",
            "setup_instructions_url": setup_instructions_url,
            "monitoring_dashboard_url": monitoring_dashboard_url,
            "support_portal_url": support_portal_url
        })
        
        return APIResponse(
            success=True,
            message=f"VPS customer '{setup_request.subdomain}' setup initiated. Validation in progress.",
            data=customer_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to setup VPS customer: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup VPS customer"
        )


@router.get("/", response_model=APIResponse[List[VPSCustomerResponse]])
@standard_exception_handler
async def list_vps_customers(
    status_filter: Optional[VPSStatus] = None,
    plan_filter: Optional[TenantPlan] = None,
    limit: int = 50,
    offset: int = 0,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> APIResponse[List[VPSCustomerResponse]]:
    """List VPS customers with optional filtering"""
    
    try:
        query = db.query(VPSCustomer)
        
        # Apply filters
        if status_filter:
            query = query.filter(VPSCustomer.status == status_filter)
        if plan_filter:
            query = query.filter(VPSCustomer.plan == plan_filter)
        
        # Pagination
        customers = query.offset(offset).limit(limit).all()
        
        base_url = "https://admin.yourdomain.com"  # Should come from config
        customer_responses = []
        
        for customer in customers:
            customer_responses.append(VPSCustomerResponse.model_validate({
                "id": str(customer.id),
                "customer_id": customer.customer_id,
                "company_name": customer.company_name,
                "subdomain": customer.subdomain,
                "status": customer.status,
                "plan": customer.plan,
                "support_tier": customer.support_tier,
                "vps_ip": customer.vps_ip,
                "custom_domain": customer.custom_domain,
                "created_at": customer.created_at,
                "deployment_started_at": customer.deployment_started_at,
                "deployment_completed_at": customer.deployment_completed_at,
                "last_health_check": customer.last_health_check,
                "health_status": customer.health_status or "unknown",
                "setup_instructions_url": f"{base_url}/customers/{customer.customer_id}/setup",
                "monitoring_dashboard_url": f"{base_url}/customers/{customer.customer_id}/monitoring",
                "support_portal_url": f"{base_url}/customers/{customer.customer_id}/support"
            }))
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(customer_responses)} VPS customers",
            data=customer_responses
        )
        
    except Exception as e:
        logger.error(f"Failed to list VPS customers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list VPS customers"
        )


@router.get("/{customer_id}/status", response_model=APIResponse[DeploymentStatus])
@standard_exception_handler
async def get_deployment_status(
    customer_id: str,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> APIResponse[DeploymentStatus]:
    """Get detailed deployment status for VPS customer"""
    
    customer = db.query(VPSCustomer).filter_by(customer_id=customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPS customer '{customer_id}' not found"
        )
    
    # Calculate progress based on status
    progress_map = {
        VPSStatus.VALIDATING: 10,
        VPSStatus.REQUIREMENTS_CHECK: 20,
        VPSStatus.CONNECTION_TEST: 30,
        VPSStatus.DEPLOYING: 50,
        VPSStatus.CONFIGURING: 70,
        VPSStatus.TESTING: 85,
        VPSStatus.READY: 100,
        VPSStatus.ACTIVE: 100,
        VPSStatus.FAILED: 0,
    }
    
    # Estimate completion time based on current status
    completion_estimates = {
        VPSStatus.VALIDATING: 30,
        VPSStatus.REQUIREMENTS_CHECK: 25,
        VPSStatus.CONNECTION_TEST: 20,
        VPSStatus.DEPLOYING: 15,
        VPSStatus.CONFIGURING: 10,
        VPSStatus.TESTING: 5,
    }
    
    status_response = DeploymentStatus(
        customer_id=customer.customer_id,
        status=customer.status,
        progress_percentage=progress_map.get(customer.status, 0),
        current_step=customer.status.value.replace('_', ' ').title(),
        estimated_completion_minutes=completion_estimates.get(customer.status),
        error_message=customer.settings.get("last_error") if customer.settings else None,
        logs=customer.deployment_logs or [],
        ssh_connection_test=customer.settings.get("ssh_test_passed") if customer.settings else None,
        server_requirements_check=customer.settings.get("requirements_passed") if customer.settings else None,
        deployment_readiness=customer.settings.get("deployment_ready") if customer.settings else None
    )
    
    return APIResponse(
        success=True,
        message="Deployment status retrieved",
        data=status_response
    )


@router.post("/{customer_id}/retry-deployment")
@standard_exception_handler
async def retry_deployment(
    customer_id: str,
    background_tasks: BackgroundTasks,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> APIResponse:
    """Retry failed VPS deployment"""
    
    customer = db.query(VPSCustomer).filter_by(customer_id=customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPS customer '{customer_id}' not found"
        )
    
    if customer.status not in [VPSStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry deployment for customer in status '{customer.status}'"
        )
    
    # Reset status and retry
    customer.status = VPSStatus.VALIDATING
    customer.deployment_started_at = datetime.now(timezone.utc)
    db.commit()
    
    # Queue deployment in background
    provisioning_service = VPSProvisioningService()
    background_tasks.add_task(
        provisioning_service.setup_vps_customer,
        customer.id,
        db
    )
    
    logger.info(f"Retrying deployment for VPS customer: {customer_id}")
    
    return APIResponse(
        success=True,
        message=f"Deployment retry started for VPS customer '{customer_id}'"
    )


@router.get("/{customer_id}/setup-instructions", response_model=APIResponse[Dict[str, Any]])
@standard_exception_handler
async def get_setup_instructions(
    customer_id: str,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> APIResponse[Dict[str, Any]]:
    """Get setup instructions for VPS customer"""
    
    customer = db.query(VPSCustomer).filter_by(customer_id=customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPS customer '{customer_id}' not found"
        )
    
    # Generate setup instructions based on customer's VPS and plan
    requirements_service = VPSRequirementsService()
    requirements = await requirements_service.calculate_requirements(
        plan=customer.plan,
        expected_customers=customer.expected_customers,
        estimated_traffic=customer.estimated_traffic
    )
    
    instructions = {
        "customer_info": {
            "company": customer.company_name,
            "subdomain": customer.subdomain,
            "plan": customer.plan.value,
            "support_tier": customer.support_tier.value
        },
        "vps_requirements": requirements.dict(),
        "preparation_steps": [
            "Ensure VPS meets minimum requirements above",
            f"Configure firewall to allow ports: {', '.join(map(str, requirements.required_ports))}",
            "Install Docker and Docker Compose (if not already installed)",
            "Ensure SSH access is configured with provided credentials",
            "Backup any existing data on the server"
        ],
        "deployment_process": [
            "Our team will connect to your VPS via SSH",
            "System requirements will be validated",
            "DotMac ISP Framework will be installed and configured",
            "Database and monitoring will be set up",
            "SSL certificates will be configured",
            "Health checks and testing will be performed",
            "You'll receive access credentials and documentation"
        ],
        "estimated_timeline": {
            "preparation": "30 minutes (customer)",
            "deployment": "2-4 hours (our team)",
            "testing": "30 minutes",
            "handover": "30 minutes"
        },
        "support_contacts": {
            "primary": "support@yourdomain.com",
            "phone": "+1-800-DOTMAC-1",
            "emergency": "emergency@yourdomain.com"
        },
        "next_steps": [
            "Review and complete preparation steps",
            "Schedule deployment with our team",
            "Be available during deployment for any questions",
            "Test the system after deployment completion"
        ]
    }
    
    return APIResponse(
        success=True,
        message="Setup instructions generated",
        data=instructions
    )