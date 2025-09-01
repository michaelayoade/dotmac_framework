"""
License Management API Endpoints
Provides license contract lookup and management for ISP instances
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from dotmac_shared.database.base import get_db_session
from dotmac_shared.core.logging import get_logger
from dotmac_shared.api.response import APIResponse
from dotmac_shared.api.exceptions import standard_exception_handler
from dotmac_shared.auth.dependencies import get_current_user
from dotmac_management.models.tenant import CustomerTenant

logger = get_logger(__name__)
router = APIRouter(prefix="/licensing", tags=["licensing"])


class LicenseContractResponse(BaseModel):
    """License contract response for ISP instances"""
    model_config = ConfigDict()
    
    contract_id: str
    tenant_id: str
    status: str
    contract_type: str
    valid_from: str
    valid_until: str
    max_customers: Optional[int]
    max_concurrent_users: Optional[int]
    max_bandwidth_gbps: Optional[int]
    max_storage_gb: Optional[int]
    max_api_calls_per_hour: Optional[int]
    max_network_devices: Optional[int]
    enabled_features: list
    disabled_features: list
    feature_limits: dict
    enforcement_mode: str
    current_usage: dict
    violation_count: int


@router.get("/contracts/by-tenant/{tenant_id}")
@standard_exception_handler
async def get_license_by_tenant_id(
    tenant_id: str,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_user)  # Service token auth
) -> APIResponse[LicenseContractResponse]:
    """
    Get active license contract for a tenant ID
    Used by ISP instances to fetch their license details
    """
    
    try:
        # Find tenant by tenant_id
        tenant = db.query(CustomerTenant).filter_by(tenant_id=tenant_id).first()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )
        
        # Get license contract from tenant settings or license table
        license_info = await _get_tenant_license_info(db, tenant)
        
        if not license_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No license found for tenant {tenant_id}"
            )
        
        return APIResponse(
            success=True,
            message="License contract retrieved",
            data=license_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving license for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve license contract"
        )


@router.post("/contracts/{contract_id}/usage")
@standard_exception_handler 
async def update_license_usage(
    contract_id: str,
    usage_data: Dict[str, Any],
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> APIResponse:
    """
    Update license usage data from ISP instance
    """
    
    try:
        from dotmac_shared.licensing.models import LicenseContract
        
        # Find license contract
        contract = db.query(LicenseContract).filter_by(contract_id=contract_id).first()
        
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License contract not found"
            )
        
        # Update usage data
        contract.current_usage = usage_data
        contract.updated_at = datetime.utcnow()
        
        # Check for violations
        violations = await _check_usage_violations(contract, usage_data)
        if violations:
            contract.violation_count += len(violations)
            logger.warning(f"License violations detected for {contract_id}: {violations}")
        
        db.commit()
        
        return APIResponse(
            success=True,
            message="License usage updated",
            data={
                "contract_id": contract_id,
                "violations": violations,
                "updated_at": contract.updated_at.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating license usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update license usage"
        )


@router.get("/plans/{plan_type}/preview")
@standard_exception_handler
async def get_plan_license_preview(
    plan_type: str,
    db: Session = Depends(get_db_session)
) -> APIResponse[Dict[str, Any]]:
    """
    Get preview of license limits for a plan type
    Used during signup to show what limits customer will have
    """
    
    try:
        from dotmac_management.services.auto_license_provisioning import AutoLicenseProvisioningService
        from dotmac_management.models.tenant import TenantPlan
        
        # Validate plan type
        try:
            plan_enum = TenantPlan(plan_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan type: {plan_type}"
            )
        
        # Get plan preview
        license_service = AutoLicenseProvisioningService()
        plan_preview = await license_service.get_plan_preview(plan_enum)
        
        return APIResponse(
            success=True,
            message="Plan preview retrieved",
            data=plan_preview
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan preview"
        )


async def _get_tenant_license_info(db: Session, tenant: CustomerTenant) -> Optional[LicenseContractResponse]:
    """Get license information for tenant"""
    
    try:
        from dotmac_shared.licensing.models import LicenseContract
        from datetime import datetime
        
        # Try to find license contract in database
        contract = db.query(LicenseContract).filter_by(
            target_isp_instance=tenant.tenant_id
        ).first()
        
        if not contract:
            # Check if license info is stored in tenant settings (from auto-provisioning)
            settings = tenant.settings or {}
            if not settings.get("license_provisioned"):
                return None
            
            # Create virtual license response from tenant plan
            from dotmac_management.services.auto_license_provisioning import AutoLicenseProvisioningService
            service = AutoLicenseProvisioningService()
            plan_limits = service._get_plan_limits(tenant.plan)
            
            return LicenseContractResponse(
                contract_id=settings.get("contract_id", f"auto-{tenant.tenant_id}"),
                tenant_id=tenant.tenant_id,
                status="active",
                contract_type=tenant.plan.value,
                valid_from=tenant.created_at.isoformat(),
                valid_until=(tenant.created_at + timedelta(days=365)).isoformat(),
                max_customers=plan_limits.max_customers,
                max_concurrent_users=plan_limits.max_concurrent_users,
                max_bandwidth_gbps=plan_limits.max_bandwidth_gbps,
                max_storage_gb=plan_limits.max_storage_gb,
                max_api_calls_per_hour=plan_limits.max_api_calls_per_hour,
                max_network_devices=plan_limits.max_network_devices,
                enabled_features=plan_limits.enabled_features,
                disabled_features=plan_limits.disabled_features,
                feature_limits=plan_limits.feature_limits,
                enforcement_mode="strict",
                current_usage={},
                violation_count=0
            )
        
        # Return actual license contract
        return LicenseContractResponse(
            contract_id=contract.contract_id,
            tenant_id=contract.target_isp_instance,
            status=contract.status.value,
            contract_type=contract.contract_type,
            valid_from=contract.valid_from.isoformat(),
            valid_until=contract.valid_until.isoformat(),
            max_customers=contract.max_customers,
            max_concurrent_users=contract.max_concurrent_users,
            max_bandwidth_gbps=contract.max_bandwidth_gbps,
            max_storage_gb=contract.max_storage_gb,
            max_api_calls_per_hour=contract.max_api_calls_per_hour,
            max_network_devices=contract.max_network_devices,
            enabled_features=contract.enabled_features or [],
            disabled_features=contract.disabled_features or [],
            feature_limits=contract.feature_limits or {},
            enforcement_mode=contract.enforcement_mode,
            current_usage=contract.current_usage or {},
            violation_count=contract.violation_count
        )
        
    except Exception as e:
        logger.error(f"Error getting tenant license info: {e}")
        return None


async def _check_usage_violations(contract, usage_data: Dict[str, Any]) -> list:
    """Check for license usage violations"""
    
    violations = []
    
    try:
        # Check customer count limit
        if contract.max_customers and usage_data.get("customer_count", 0) > contract.max_customers:
            violations.append({
                "type": "customer_limit_exceeded",
                "limit": contract.max_customers,
                "current": usage_data.get("customer_count", 0)
            })
        
        # Check concurrent users
        if contract.max_concurrent_users and usage_data.get("concurrent_users", 0) > contract.max_concurrent_users:
            violations.append({
                "type": "concurrent_users_exceeded",
                "limit": contract.max_concurrent_users,
                "current": usage_data.get("concurrent_users", 0)
            })
        
        # Check API calls per hour
        if contract.max_api_calls_per_hour and usage_data.get("api_calls_hour", 0) > contract.max_api_calls_per_hour:
            violations.append({
                "type": "api_rate_limit_exceeded", 
                "limit": contract.max_api_calls_per_hour,
                "current": usage_data.get("api_calls_hour", 0)
            })
        
        # Check storage usage
        if contract.max_storage_gb and usage_data.get("storage_used_gb", 0) > contract.max_storage_gb:
            violations.append({
                "type": "storage_limit_exceeded",
                "limit": contract.max_storage_gb,
                "current": usage_data.get("storage_used_gb", 0)
            })
        
        # Check network devices
        if contract.max_network_devices and usage_data.get("network_devices", 0) > contract.max_network_devices:
            violations.append({
                "type": "network_devices_exceeded",
                "limit": contract.max_network_devices,
                "current": usage_data.get("network_devices", 0)
            })
        
    except Exception as e:
        logger.error(f"Error checking usage violations: {e}")
    
    return violations