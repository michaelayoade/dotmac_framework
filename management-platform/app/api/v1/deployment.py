"""
Deployment API endpoints for infrastructure and service management.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...services.deployment_service import DeploymentService
from ...schemas.deployment import (
    DeploymentTemplate, DeploymentTemplateCreate, DeploymentTemplateUpdate, DeploymentTemplateListResponse,
    Infrastructure, InfrastructureCreate, InfrastructureUpdate, InfrastructureListResponse,
    Deployment, DeploymentCreate, DeploymentUpdate, DeploymentListResponse,
    ServiceInstance, ServiceInstanceCreate, ServiceInstanceUpdate, ServiceInstanceListResponse,
    DeploymentLog, DeploymentLogListResponse,
    DeploymentRequest, ScalingRequest, RollbackRequest,
    DeploymentStatus, InfrastructureHealth, TenantDeploymentOverview
)
from ...core.auth import get_current_user, require_deployment_read, require_deployment_write
from ...core.pagination import PaginationParams

router = APIRouter()


# Deployment Templates
@router.post("/templates", response_model=DeploymentTemplate)
async def create_deployment_template():
    template_data: DeploymentTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_write()
):
    """Create a new deployment template."""
    service = DeploymentService(db)
    return await service.create_template(template_data, current_user.user_id)


@router.get("/templates", response_model=DeploymentTemplateListResponse)
async def list_deployment_templates():
    category: Optional[str] = None,
    cloud_provider: Optional[str] = None,
    active_only: bool = True,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """List deployment templates with optional filters."""
    service = DeploymentService(db)
    
    filters = {}
    if category:
        filters["category"] = category
    if cloud_provider:
        filters["cloud_provider"] = cloud_provider
    if active_only:
        filters["is_active"] = True
    
    templates = await service.template_repo.list()
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.template_repo.count(filters)
    
    return DeploymentTemplateListResponse()
        items=templates,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/templates/{template_id}", response_model=DeploymentTemplate)
async def get_deployment_template():
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """Get a specific deployment template."""
    service = DeploymentService(db)
    template = await service.template_repo.get_by_id(template_id)
    if not template:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment template not found"
        )
    return template


@router.put("/templates/{template_id}", response_model=DeploymentTemplate)
async def update_deployment_template():
    template_id: UUID,
    template_update: DeploymentTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_write()
):
    """Update a deployment template."""
    service = DeploymentService(db)
    template = await service.template_repo.update()
        template_id, template_update.model_dump(exclude_unset=True), current_user.user_id
    )
    if not template:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment template not found"
        )
    return template


@router.delete("/templates/{template_id}")
async def delete_deployment_template():
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_write()
):
    """Delete a deployment template."""
    service = DeploymentService(db)
    success = await service.template_repo.delete(template_id)
    if not success:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment template not found"
        )
    return {"message": "Deployment template deleted successfully"}


# Infrastructure
@router.post("/infrastructure", response_model=Infrastructure)
async def provision_infrastructure():
    tenant_id: UUID,
    infrastructure_data: InfrastructureCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_write()
):
    """Provision infrastructure for a tenant."""
    service = DeploymentService(db)
    return await service.provision_infrastructure()
        tenant_id, infrastructure_data, current_user.user_id
    )


@router.get("/infrastructure", response_model=InfrastructureListResponse)
async def list_infrastructure():
    tenant_id: Optional[UUID] = None,
    cloud_provider: Optional[str] = None,
    environment: Optional[str] = None,
    status: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """List infrastructure with optional filters."""
    service = DeploymentService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    if cloud_provider:
        filters["cloud_provider"] = cloud_provider
    if environment:
        filters["environment"] = environment
    if status:
        filters["status"] = status
    
    infrastructure = await service.infrastructure_repo.list()
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.infrastructure_repo.count(filters)
    
    return InfrastructureListResponse()
        items=infrastructure,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/infrastructure/{infrastructure_id}", response_model=Infrastructure)
async def get_infrastructure():
    infrastructure_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """Get a specific infrastructure."""
    service = DeploymentService(db)
    infrastructure = await service.infrastructure_repo.get_by_id(infrastructure_id)
    if not infrastructure:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infrastructure not found"
        )
    return infrastructure


@router.put("/infrastructure/{infrastructure_id}", response_model=Infrastructure)
async def update_infrastructure():
    infrastructure_id: UUID,
    infrastructure_update: InfrastructureUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_write()
):
    """Update infrastructure configuration."""
    service = DeploymentService(db)
    infrastructure = await service.infrastructure_repo.update()
        infrastructure_id, infrastructure_update.model_dump(exclude_unset=True), current_user.user_id
    )
    if not infrastructure:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infrastructure not found"
        )
    return infrastructure


@router.get("/infrastructure/{infrastructure_id}/health", response_model=InfrastructureHealth)
async def get_infrastructure_health():
    infrastructure_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """Get infrastructure health status."""
    service = DeploymentService(db)
    return await service.get_infrastructure_health(infrastructure_id)


# Deployments
@router.post("/deployments", response_model=Deployment)
async def deploy_service():
    tenant_id: UUID,
    deployment_request: DeploymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_write()
):
    """Deploy a service using a template."""
    service = DeploymentService(db)
    return await service.deploy_service()
        deployment_request, tenant_id, current_user.user_id
    )


@router.get("/deployments", response_model=DeploymentListResponse)
async def list_deployments():
    tenant_id: Optional[UUID] = None,
    infrastructure_id: Optional[UUID] = None,
    environment: Optional[str] = None,
    status: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """List deployments with optional filters."""
    service = DeploymentService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    if infrastructure_id:
        filters["infrastructure_id"] = infrastructure_id
    if environment:
        filters["environment"] = environment
    if status:
        filters["status"] = status
    
    deployments = await service.deployment_repo.list()
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.deployment_repo.count(filters)
    
    return DeploymentListResponse()
        items=deployments,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/deployments/{deployment_id}", response_model=Deployment)
async def get_deployment():
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """Get a specific deployment."""
    service = DeploymentService(db)
    deployment = await service.deployment_repo.get_with_relations(deployment_id)
    if not deployment:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    return deployment


@router.put("/deployments/{deployment_id}", response_model=Deployment)
async def update_deployment():
    deployment_id: UUID,
    deployment_update: DeploymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_write()
):
    """Update deployment configuration."""
    service = DeploymentService(db)
    deployment = await service.deployment_repo.update()
        deployment_id, deployment_update.model_dump(exclude_unset=True), current_user.user_id
    )
    if not deployment:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    return deployment


@router.get("/deployments/{deployment_id}/status", response_model=DeploymentStatus)
async def get_deployment_status():
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """Get comprehensive deployment status."""
    service = DeploymentService(db)
    return await service.get_deployment_status(deployment_id)


@router.post("/deployments/{deployment_id}/scale")
async def scale_deployment():
    deployment_id: UUID,
    scaling_request: ScalingRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_write()
):
    """Scale a deployed service."""
    service = DeploymentService(db)
    success = await service.scale_service()
        deployment_id, scaling_request, current_user.user_id
    )
    
    if success:
        return {"message": "Service scaling initiated successfully"}
    else:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to scale service"
        )


@router.post("/deployments/{deployment_id}/rollback")
async def rollback_deployment():
    deployment_id: UUID,
    rollback_request: RollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_write()
):
    """Rollback a deployment to a previous version."""
    service = DeploymentService(db)
    success = await service.rollback_deployment()
        deployment_id, rollback_request, current_user.user_id
    )
    
    if success:
        return {"message": "Deployment rollback initiated successfully"}
    else:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rollback deployment"
        )


# Service Instances
@router.get("/services", response_model=ServiceInstanceListResponse)
async def list_service_instances():
    tenant_id: Optional[UUID] = None,
    deployment_id: Optional[UUID] = None,
    service_type: Optional[str] = None,
    status: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """List service instances with optional filters."""
    service = DeploymentService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    if deployment_id:
        filters["deployment_id"] = deployment_id
    if service_type:
        filters["service_type"] = service_type
    if status:
        filters["status"] = status
    
    services = await service.service_repo.list()
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.service_repo.count(filters)
    
    return ServiceInstanceListResponse()
        items=services,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/services/{service_id}", response_model=ServiceInstance)
async def get_service_instance():
    service_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """Get a specific service instance."""
    service = DeploymentService(db)
    service_instance = await service.service_repo.get_by_id(service_id)
    if not service_instance:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service instance not found"
        )
    return service_instance


@router.put("/services/{service_id}", response_model=ServiceInstance)
async def update_service_instance():
    service_id: UUID,
    service_update: ServiceInstanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_write()
):
    """Update service instance configuration."""
    service = DeploymentService(db)
    service_instance = await service.service_repo.update()
        service_id, service_update.model_dump(exclude_unset=True), current_user.user_id
    )
    if not service_instance:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service instance not found"
        )
    return service_instance


# Deployment Logs
@router.get("/deployments/{deployment_id}/logs", response_model=DeploymentLogListResponse)
async def get_deployment_logs():
    deployment_id: UUID,
    log_level: Optional[str] = None,
    component: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """Get logs for a specific deployment."""
    service = DeploymentService(db)
    
    filters = {"deployment_id": deployment_id}
    if log_level:
        filters["log_level"] = log_level
    if component:
        filters["component"] = component
    
    logs = await service.log_repo.list()
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.log_repo.count(filters)
    
    return DeploymentLogListResponse()
        items=logs,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


# Tenant Overview
@router.get("/tenants/{tenant_id}/overview", response_model=TenantDeploymentOverview)
async def get_tenant_deployment_overview():
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_deployment_read()
):
    """Get comprehensive deployment overview for a tenant."""
    service = DeploymentService(db)
    return await service.get_tenant_deployment_overview(tenant_id)