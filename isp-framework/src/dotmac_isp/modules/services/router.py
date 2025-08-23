"""Services API router for ISP service provisioning and management."""

from datetime import datetime, date, timedelta
from typing import List, Optional
from uuid import UUID, uuid4
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.core.middleware import get_tenant_id_dependency
from . import schemas
from .models import (
    ServicePlan,
    ServiceInstance,
    ProvisioningTask,
    ServiceAddon,
    ServiceUsage,
    ServiceAlert,
    ServiceInstanceAddon,
    ServiceType,
    ServiceStatus,
    ProvisioningStatus,
)
from .service import ServiceProvisioningService, ServicePlanService
from dotmac_isp.shared.exceptions import NotFoundError, ValidationError, ServiceError

router = APIRouter(tags=["services"])
services_router = router  # Export with expected name


# Service Plans Endpoints
@router.get("/plans", response_model=List[schemas.ServicePlanResponse])
async def list_service_plans(
    service_type: Optional[ServiceType] = None,
    is_active: Optional[bool] = None,
    is_public: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List all service plans with optional filtering."""
    try:
        service = ServicePlanService(db, tenant_id)
        plans = await service.list_plans(
            service_type=service_type,
            is_active=is_active,
            is_public=is_public,
            skip=skip,
            limit=limit,
        )
        return plans
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plans",
    response_model=schemas.ServicePlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_plan(
    plan_data: schemas.ServicePlanCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create a new service plan."""
    try:
        service = ServicePlanService(db, tenant_id)
        plan = await service.create_plan(plan_data)
        return plan
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans/{plan_id}", response_model=schemas.ServicePlanResponse)
async def get_service_plan(
    plan_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get service plan by ID."""
    try:
        service = ServicePlanService(db, tenant_id)
        plan = await service.get_plan(plan_id)
        return plan
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Service plan not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plans/{plan_id}", response_model=schemas.ServicePlanResponse)
async def update_service_plan(
    plan_id: UUID,
    plan_data: schemas.ServicePlanUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update service plan."""
    try:
        service = ServicePlanService(db, tenant_id)
        plan = await service.update_plan(plan_id, plan_data)
        return plan
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Service plan not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_plan(
    plan_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Delete service plan."""
    try:
        service = ServicePlanService(db, tenant_id)
        await service.delete_plan(plan_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Service plan not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Service Instance Endpoints
@router.post(
    "/instances",
    response_model=schemas.ServiceInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def provision_service(
    provisioning_request: schemas.ServiceProvisioningRequest,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Provision a new service for a customer."""
    try:
        service = ServiceProvisioningService(db, tenant_id)
        instance = await service.provision_service(
            customer_id=provisioning_request.customer_id,
            service_plan_id=provisioning_request.service_plan_id,
            provisioning_data=provisioning_request,
        )
        return instance
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instances", response_model=List[schemas.ServiceInstanceResponse])
async def list_service_instances(
    customer_id: Optional[UUID] = Query(None),
    status: Optional[ServiceStatus] = Query(None),
    service_plan_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List service instances with optional filtering."""
    try:
        service = ServiceProvisioningService(db, tenant_id)
        if customer_id:
            instances = await service.list_customer_services(customer_id, skip, limit)
        else:
            # This would need to be implemented in the service
            instances = []
        return instances
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instances/{instance_id}", response_model=schemas.ServiceInstanceResponse)
async def get_service_instance(
    instance_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get service instance by ID."""
    try:
        service = ServiceProvisioningService(db, tenant_id)
        instance = await service.get_service_instance(instance_id)
        return instance
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Service instance not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/instances/by-number/{service_number}",
    response_model=schemas.ServiceInstanceResponse,
)
async def get_service_by_number(
    service_number: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get service instance by service number."""
    try:
        service = ServiceProvisioningService(db, tenant_id)
        instance = await service.get_service_by_number(service_number)
        return instance
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Service not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/instances/{instance_id}/status", response_model=schemas.ServiceInstanceResponse
)
async def update_service_status(
    instance_id: UUID,
    status_update: schemas.ServiceStatusUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update service instance status."""
    try:
        service = ServiceProvisioningService(db, tenant_id)
        instance = await service.update_service_status(
            instance_id=instance_id,
            status=status_update.status,
            notes=status_update.notes,
        )
        return instance
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Service instance not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/instances/{instance_id}/modify", response_model=schemas.ServiceInstanceResponse
)
async def modify_service(
    instance_id: UUID,
    modification_request: schemas.ServiceModificationRequest,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Modify an existing service."""
    try:
        service = ServiceProvisioningService(db, tenant_id)
        instance = await service.modify_service(instance_id, modification_request)
        return instance
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Service instance not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Provisioning Task Endpoints
@router.get(
    "/instances/{instance_id}/tasks",
    response_model=List[schemas.ProvisioningTaskResponse],
)
async def get_service_tasks(
    instance_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get provisioning tasks for a service instance."""
    try:
        service = ServiceProvisioningService(db, tenant_id)
        tasks = await service.list_service_tasks(instance_id)
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=schemas.ProvisioningTaskResponse)
async def get_provisioning_task(
    task_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get provisioning task by ID."""
    try:
        service = ServiceProvisioningService(db, tenant_id)
        task = await service.get_provisioning_task(task_id)
        return task
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Provisioning task not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tasks/{task_id}/status", response_model=schemas.ProvisioningTaskResponse)
async def update_task_status(
    task_id: UUID,
    status_update: schemas.ProvisioningTaskStatusUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update provisioning task status."""
    try:
        service = ServiceProvisioningService(db, tenant_id)
        task = await service.update_task_status(
            task_id=task_id,
            status=status_update.status,
            result_data=status_update.result_data,
            error_message=status_update.error_message,
        )
        return task
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Provisioning task not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Customer Service Endpoints
@router.get(
    "/customers/{customer_id}/services",
    response_model=List[schemas.ServiceInstanceResponse],
)
async def get_customer_services(
    customer_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get all services for a specific customer."""
    try:
        service = ServiceProvisioningService(db, tenant_id)
        services = await service.list_customer_services(customer_id, skip, limit)
        return services
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for services module."""
    return {
        "status": "healthy",
        "module": "services",
        "timestamp": datetime.utcnow().isoformat(),
    }
