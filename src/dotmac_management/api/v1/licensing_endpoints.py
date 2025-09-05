"""
License Management API Endpoints
Provides license contract lookup and management for ISP instances
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from dotmac.application import (
    StandardDependencies,
    get_standard_deps,
    standard_exception_handler,
)
from dotmac.platform.observability.logging import get_logger
from dotmac_management.models.tenant import CustomerTenant
from dotmac_shared.api.response import APIResponse

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
    deps: StandardDependencies = Depends(get_standard_deps),
) -> APIResponse[LicenseContractResponse]:
    """
    Get active license contract for a tenant ID
    Used by ISP instances to fetch their license details
    """
    start_time = time.time()

    # Input validation logging for security auditing
    logger.info(
        "License contract lookup requested",
        extra={
            "requesting_user_id": getattr(deps.current_user, "id", None),
            "tenant_id": tenant_id,
            "operation": "get_license_by_tenant_id",
            "license_lookup": True,
        },
    )

    try:
        # Find tenant by tenant_id
        result = await deps.db.execute(
            select(CustomerTenant).where(CustomerTenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            logger.warning(
                "Tenant not found for license lookup",
                extra={
                    "requesting_user_id": getattr(deps.current_user, "id", None),
                    "tenant_id": tenant_id,
                    "operation": "get_license_by_tenant_id",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found",
            )

        # Get license contract from tenant settings or license table
        license_info = await _get_tenant_license_info(deps.db, tenant)

        if not license_info:
            logger.warning(
                "No license found for tenant",
                extra={
                    "requesting_user_id": getattr(deps.current_user, "id", None),
                    "tenant_id": tenant_id,
                    "tenant_company": getattr(tenant, "company_name", None),
                    "tenant_plan": getattr(tenant, "plan", None),
                    "operation": "get_license_by_tenant_id",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No license found for tenant {tenant_id}",
            )

        # Log successful lookup with performance metrics
        execution_time = time.time() - start_time
        logger.info(
            "License contract retrieved successfully",
            extra={
                "requesting_user_id": getattr(deps.current_user, "id", None),
                "tenant_id": tenant_id,
                "tenant_company": getattr(tenant, "company_name", None),
                "contract_id": getattr(license_info, "contract_id", None),
                "contract_type": getattr(license_info, "contract_type", None),
                "execution_time_ms": round(execution_time * 1000, 2),
                "operation": "get_license_by_tenant_id",
                "status": "success",
            },
        )

        # Performance logging for slow operations
        if execution_time > 1.0:
            logger.warning(
                "Slow license lookup detected",
                extra={
                    "tenant_id": tenant_id,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "performance_threshold_exceeded": True,
                    "operation": "get_license_by_tenant_id",
                },
            )

        return APIResponse(
            success=True, message="License contract retrieved", data=license_info
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error retrieving license contract",
            extra={
                "requesting_user_id": getattr(deps.current_user, "id", None),
                "tenant_id": tenant_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "operation": "get_license_by_tenant_id",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve license contract",
        ) from e


@router.post("/contracts/{contract_id}/usage")
@standard_exception_handler
async def update_license_usage(
    contract_id: str,
    usage_data: dict[str, Any],
    deps: StandardDependencies = Depends(get_standard_deps),
) -> APIResponse:
    """
    Update license usage data from ISP instance
    """
    start_time = time.time()

    # Input validation logging for security auditing
    logger.info(
        "License usage update requested",
        extra={
            "requesting_user_id": getattr(deps.current_user, "id", None),
            "contract_id": contract_id,
            "usage_metrics": list(usage_data.keys()) if usage_data else [],
            "operation": "update_license_usage",
            "license_usage": True,
        },
    )

    try:
        from dotmac_shared.licensing.models import LicenseContract

        # Find license contract
        result = await deps.db.execute(
            select(LicenseContract).where(LicenseContract.contract_id == contract_id)
        )
        contract = result.scalar_one_or_none()

        if not contract:
            logger.warning(
                "License contract not found for usage update",
                extra={
                    "requesting_user_id": getattr(deps.current_user, "id", None),
                    "contract_id": contract_id,
                    "operation": "update_license_usage",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License contract not found",
            )

        # Store previous usage for comparison
        contract.current_usage.copy() if contract.current_usage else {}

        # Update usage data
        contract.current_usage = usage_data
        contract.updated_at = datetime.now(timezone.utc)

        # Check for violations
        violations = await _check_usage_violations(contract, usage_data)

        if violations:
            contract.violation_count += len(violations)
            logger.warning(
                "License violations detected",
                extra={
                    "requesting_user_id": getattr(deps.current_user, "id", None),
                    "contract_id": contract_id,
                    "violations": violations,
                    "violation_count": len(violations),
                    "total_violations": contract.violation_count,
                    "license_enforcement": True,
                    "operation": "update_license_usage",
                },
            )

        from dotmac_shared.core.error_utils import async_db_transaction

        async with async_db_transaction(deps.db):
            pass

        # Log successful update with performance metrics
        execution_time = time.time() - start_time
        logger.info(
            "License usage updated successfully",
            extra={
                "requesting_user_id": getattr(deps.current_user, "id", None),
                "contract_id": contract_id,
                "usage_metrics_updated": list(usage_data.keys()) if usage_data else [],
                "violations_detected": len(violations),
                "execution_time_ms": round(execution_time * 1000, 2),
                "operation": "update_license_usage",
                "status": "success",
            },
        )

        return APIResponse(
            success=True,
            message="License usage updated",
            data={
                "contract_id": contract_id,
                "violations": violations,
                "updated_at": contract.updated_at.isoformat(),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error updating license usage",
            extra={
                "requesting_user_id": getattr(deps.current_user, "id", None),
                "contract_id": contract_id,
                "usage_data_keys": list(usage_data.keys()) if usage_data else [],
                "error": str(e),
                "error_type": type(e).__name__,
                "operation": "update_license_usage",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update license usage",
        ) from e


@router.get("/plans/{plan_type}/preview")
@standard_exception_handler
async def get_plan_license_preview(
    plan_type: str,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> APIResponse[dict[str, Any]]:
    """
    Get preview of license limits for a plan type
    Used during signup to show what limits customer will have
    """
    start_time = time.time()

    # Input validation logging for security auditing
    logger.info(
        "Plan preview requested",
        extra={
            "requesting_user_id": getattr(deps.current_user, "id", None),
            "plan_type": plan_type,
            "operation": "get_plan_license_preview",
            "plan_preview": True,
        },
    )

    try:
        from dotmac_management.models.tenant import TenantPlan
        from dotmac_management.services.auto_license_provisioning import (
            AutoLicenseProvisioningService,
        )

        # Validate plan type
        try:
            plan_enum = TenantPlan(plan_type)
        except ValueError as err:
            logger.warning(
                "Invalid plan type requested",
                extra={
                    "requesting_user_id": getattr(deps.current_user, "id", None),
                    "invalid_plan_type": plan_type,
                    "operation": "get_plan_license_preview",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan type: {plan_type}",
            ) from err

        # Get plan preview
        license_service = AutoLicenseProvisioningService()
        plan_preview = await license_service.get_plan_preview(plan_enum)

        # Log successful preview retrieval with performance metrics
        execution_time = time.time() - start_time
        logger.info(
            "Plan preview retrieved successfully",
            extra={
                "requesting_user_id": getattr(deps.current_user, "id", None),
                "plan_type": plan_type,
                "preview_data_keys": list(plan_preview.keys()) if plan_preview else [],
                "execution_time_ms": round(execution_time * 1000, 2),
                "operation": "get_plan_license_preview",
                "status": "success",
            },
        )

        return APIResponse(
            success=True, message="Plan preview retrieved", data=plan_preview
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error getting plan preview",
            extra={
                "requesting_user_id": getattr(deps.current_user, "id", None),
                "plan_type": plan_type,
                "error": str(e),
                "error_type": type(e).__name__,
                "operation": "get_plan_license_preview",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan preview",
        ) from e


async def _get_tenant_license_info(
    db: Session, tenant: CustomerTenant
) -> Optional[LicenseContractResponse]:
    """Get license information for tenant"""

    try:
        from dotmac_shared.licensing.models import LicenseContract

        # Try to find license contract in database
        contract = (
            db.query(LicenseContract)
            .filter_by(target_isp_instance=tenant.tenant_id)
            .first()
        )

        if not contract:
            # Check if license info is stored in tenant settings (from auto-provisioning)
            settings = tenant.settings or {}
            if not settings.get("license_provisioned"):
                return None

            # Create virtual license response from tenant plan
            from dotmac_management.services.auto_license_provisioning import (
                AutoLicenseProvisioningService,
            )

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
                violation_count=0,
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
            violation_count=contract.violation_count,
        )

    except Exception as e:
        logger.error(f"Error getting tenant license info: {e}")
        return None


async def _check_usage_violations(contract, usage_data: dict[str, Any]) -> list:
    """Check for license usage violations"""

    violations = []

    try:
        # Check customer count limit
        if (
            contract.max_customers
            and usage_data.get("customer_count", 0) > contract.max_customers
        ):
            violations.append(
                {
                    "type": "customer_limit_exceeded",
                    "limit": contract.max_customers,
                    "current": usage_data.get("customer_count", 0),
                }
            )

        # Check concurrent users
        if (
            contract.max_concurrent_users
            and usage_data.get("concurrent_users", 0) > contract.max_concurrent_users
        ):
            violations.append(
                {
                    "type": "concurrent_users_exceeded",
                    "limit": contract.max_concurrent_users,
                    "current": usage_data.get("concurrent_users", 0),
                }
            )

        # Check API calls per hour
        if (
            contract.max_api_calls_per_hour
            and usage_data.get("api_calls_hour", 0) > contract.max_api_calls_per_hour
        ):
            violations.append(
                {
                    "type": "api_rate_limit_exceeded",
                    "limit": contract.max_api_calls_per_hour,
                    "current": usage_data.get("api_calls_hour", 0),
                }
            )

        # Check storage usage
        if (
            contract.max_storage_gb
            and usage_data.get("storage_used_gb", 0) > contract.max_storage_gb
        ):
            violations.append(
                {
                    "type": "storage_limit_exceeded",
                    "limit": contract.max_storage_gb,
                    "current": usage_data.get("storage_used_gb", 0),
                }
            )

        # Check network devices
        if (
            contract.max_network_devices
            and usage_data.get("network_devices", 0) > contract.max_network_devices
        ):
            violations.append(
                {
                    "type": "network_devices_exceeded",
                    "limit": contract.max_network_devices,
                    "current": usage_data.get("network_devices", 0),
                }
            )

    except Exception as e:
        logger.error(f"Error checking usage violations: {e}")

    return violations
