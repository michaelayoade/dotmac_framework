"""Service management API router."""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from dotmac_isp.shared.database import get_db
from dotmac_shared.api.dependencies import get_current_tenant, get_current_user
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.pagination import PaginationParams

from . import schemas
from .service import ServicesService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/services", tags=["services"])


def get_services_service(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
) -> ServicesService:
    """Get services service instance."""
    return ServicesService(db, tenant_id)


# =================================================================
# SERVICE PLAN ENDPOINTS
# =================================================================

@router.post("/plans", response_model=schemas.ServicePlanResponse, status_code=status.HTTP_201_CREATED)
@standard_exception_handler
async def create_service_plan(
    plan_data: schemas.ServicePlanCreate,
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Create a new service plan."""
    return await service.create_service_plan(plan_data)


@router.get("/plans", response_model=List[schemas.ServicePlanResponse])
@standard_exception_handler
async def list_service_plans(
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_public: Optional[bool] = Query(None, description="Filter by public visibility"),
    pagination: PaginationParams = Depends(),
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """List service plans with optional filtering."""
    filters = {}
    if service_type:
        filters["service_type"] = service_type
    if is_active is not None:
        filters["is_active"] = is_active
    if is_public is not None:
        filters["is_public"] = is_public

    return await service.list_service_plans(
        filters=filters,
        limit=pagination.limit,
        offset=pagination.offset
    )


@router.get("/plans/public", response_model=List[schemas.ServicePlanResponse])
@standard_exception_handler
async def get_public_service_plans(
    service: ServicesService = Depends(get_services_service)
):
    """Get all public service plans available for customer selection."""
    return await service.get_public_service_plans()


@router.get("/plans/by-type/{service_type}", response_model=List[schemas.ServicePlanResponse])
@standard_exception_handler
async def get_service_plans_by_type(
    service_type: str,
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Get service plans by type."""
    return await service.get_service_plans_by_type(service_type)


@router.get("/plans/{plan_id}", response_model=schemas.ServicePlanResponse)
@standard_exception_handler
async def get_service_plan(
    plan_id: UUID,
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Get service plan by ID."""
    plan = await service.get_service_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Service plan not found")
    return plan


@router.get("/plans/by-code/{plan_code}", response_model=schemas.ServicePlanResponse)
@standard_exception_handler
async def get_service_plan_by_code(
    plan_code: str,
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Get service plan by code."""
    plan = await service.get_service_plan_by_code(plan_code)
    if not plan:
        raise HTTPException(status_code=404, detail="Service plan not found")
    return plan


# =================================================================
# SERVICE INSTANCE ENDPOINTS
# =================================================================

@router.post("/activate", response_model=schemas.ServiceActivationResponse, status_code=status.HTTP_201_CREATED)
@standard_exception_handler
async def activate_service(
    activation_request: schemas.ServiceActivationRequest,
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Activate a new service for a customer."""
    return await service.activate_service(activation_request)


@router.get("/instances", response_model=List[schemas.ServiceInstanceResponse])
@standard_exception_handler
async def list_service_instances(
    customer_id: Optional[UUID] = Query(None, description="Filter by customer ID"),
    status: Optional[str] = Query(None, description="Filter by service status"),
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    pagination: PaginationParams = Depends(),
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """List service instances with optional filtering."""
    if customer_id:
        return await service.get_customer_services(customer_id)
    
    filters = {}
    if status:
        filters["status"] = status
    if service_type:
        filters["service_type"] = service_type

    return await service.list(
        filters=filters,
        limit=pagination.limit,
        offset=pagination.offset
    )


@router.get("/instances/{service_id}", response_model=schemas.ServiceInstanceResponse)
@standard_exception_handler
async def get_service_instance(
    service_id: UUID,
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Get service instance by ID."""
    instance = await service.get_service_instance(service_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Service instance not found")
    return instance


@router.get("/instances/by-number/{service_number}", response_model=schemas.ServiceInstanceResponse)
@standard_exception_handler
async def get_service_by_number(
    service_number: str,
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Get service instance by service number."""
    instance = await service.get_service_by_number(service_number)
    if not instance:
        raise HTTPException(status_code=404, detail="Service not found")
    return instance


@router.patch("/instances/{service_id}/status", response_model=schemas.ServiceInstanceResponse)
@standard_exception_handler
async def update_service_status(
    service_id: UUID,
    status_update: schemas.ServiceStatusUpdate,
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Update service status."""
    user_id = UUID(current_user.get("user_id")) if current_user.get("user_id") else None
    return await service.update_service_status(service_id, status_update, user_id)


@router.post("/instances/{service_id}/suspend", response_model=schemas.ServiceInstanceResponse)
@standard_exception_handler
async def suspend_service(
    service_id: UUID,
    reason: str = Query(..., description="Reason for suspension"),
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Suspend a service."""
    user_id = UUID(current_user.get("user_id")) if current_user.get("user_id") else None
    return await service.suspend_service(service_id, reason, user_id)


@router.post("/instances/{service_id}/reactivate", response_model=schemas.ServiceInstanceResponse)
@standard_exception_handler
async def reactivate_service(
    service_id: UUID,
    reason: str = Query(..., description="Reason for reactivation"),
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Reactivate a suspended service."""
    user_id = UUID(current_user.get("user_id")) if current_user.get("user_id") else None
    return await service.reactivate_service(service_id, reason, user_id)


@router.post("/instances/{service_id}/cancel", response_model=schemas.ServiceInstanceResponse)
@standard_exception_handler
async def cancel_service(
    service_id: UUID,
    reason: str = Query(..., description="Reason for cancellation"),
    effective_date: Optional[datetime] = Query(None, description="Effective cancellation date"),
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Cancel a service."""
    user_id = UUID(current_user.get("user_id")) if current_user.get("user_id") else None
    return await service.cancel_service(service_id, reason, effective_date, user_id)


# =================================================================
# PROVISIONING ENDPOINTS
# =================================================================

@router.get("/provisioning/pending", response_model=List[schemas.ProvisioningTaskResponse])
@standard_exception_handler
async def get_pending_provisioning(
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Get all pending provisioning tasks."""
    return await service.get_pending_provisioning()


@router.patch("/provisioning/{provisioning_id}/assign", response_model=schemas.ProvisioningTaskResponse)
@standard_exception_handler
async def assign_provisioning_technician(
    provisioning_id: UUID,
    technician_id: UUID = Query(..., description="Technician ID to assign"),
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Assign technician to provisioning task."""
    return await service.assign_provisioning_technician(provisioning_id, technician_id)


@router.patch("/provisioning/{provisioning_id}/complete", response_model=schemas.ProvisioningTaskResponse)
@standard_exception_handler
async def complete_provisioning(
    provisioning_id: UUID,
    completion_data: Dict[str, Any],
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Complete provisioning task."""
    return await service.complete_provisioning(provisioning_id, completion_data)


# =================================================================
# USAGE AND ANALYTICS ENDPOINTS
# =================================================================

@router.post("/instances/{service_id}/usage", response_model=schemas.ServiceUsageResponse, status_code=status.HTTP_201_CREATED)
@standard_exception_handler
async def record_service_usage(
    service_id: UUID,
    usage_data: schemas.ServiceUsageCreate,
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Record usage data for a service."""
    return await service.record_service_usage(
        service_id,
        usage_data.usage_date,
        usage_data.data_downloaded,
        usage_data.data_uploaded,
        peak_download_speed_mbps=usage_data.peak_download_speed,
        peak_upload_speed_mbps=usage_data.peak_upload_speed,
        uptime_minutes=int(usage_data.uptime_percentage * 24 * 60 / 100) if usage_data.uptime_percentage else 0,
        downtime_minutes=usage_data.downtime_minutes or 0,
        custom_metrics=usage_data.additional_metrics
    )


@router.get("/instances/{service_id}/usage", response_model=List[schemas.ServiceUsageResponse])
@standard_exception_handler
async def get_service_usage(
    service_id: UUID,
    start_date: date = Query(..., description="Start date for usage data"),
    end_date: date = Query(..., description="End date for usage data"),
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Get usage data for a service within date range."""
    return await service.get_service_usage(service_id, start_date, end_date)


@router.get("/dashboard", response_model=schemas.ServiceDashboard)
@standard_exception_handler
async def get_service_dashboard(
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Get service management dashboard data."""
    return await service.get_service_dashboard()


# =================================================================
# BULK OPERATIONS ENDPOINTS
# =================================================================

@router.post("/bulk-operation", response_model=schemas.BulkServiceOperationResponse)
@standard_exception_handler
async def bulk_service_operation(
    bulk_request: schemas.BulkServiceOperation,
    service: ServicesService = Depends(get_services_service),
    current_user: dict = Depends(get_current_user)
):
    """Perform bulk operations on multiple services."""
    results = []
    successful = 0
    failed = 0
    
    user_id = UUID(current_user.get("user_id")) if current_user.get("user_id") else None
    
    for service_id in bulk_request.service_instance_ids:
        try:
            if bulk_request.operation == "suspend":
                result = await service.suspend_service(service_id, bulk_request.reason, user_id)
                results.append({
                    "service_id": str(service_id),
                    "status": "success",
                    "service_number": result.service_number
                })
                successful += 1
                
            elif bulk_request.operation == "reactivate":
                result = await service.reactivate_service(service_id, bulk_request.reason, user_id)
                results.append({
                    "service_id": str(service_id),
                    "status": "success",
                    "service_number": result.service_number
                })
                successful += 1
                
            elif bulk_request.operation == "cancel":
                result = await service.cancel_service(
                    service_id, 
                    bulk_request.reason, 
                    bulk_request.effective_date,
                    user_id
                )
                results.append({
                    "service_id": str(service_id),
                    "status": "success",
                    "service_number": result.service_number
                })
                successful += 1
                
            else:
                results.append({
                    "service_id": str(service_id),
                    "status": "failed",
                    "error": f"Unsupported operation: {bulk_request.operation}"
                })
                failed += 1
                
        except Exception as e:
            results.append({
                "service_id": str(service_id),
                "status": "failed",
                "error": str(e)
            })
            failed += 1
    
    return schemas.BulkServiceOperationResponse(
        total_requested=len(bulk_request.service_instance_ids),
        successful=successful,
        failed=failed,
        results=results,
        operation_id=uuid4()
    )


# Export router
__all__ = ["router"]