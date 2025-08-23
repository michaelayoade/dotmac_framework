"""API endpoints for tenant orchestration and deployment management."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from mgmt.shared.database import get_async_session
from mgmt.shared.auth.permissions import require_permissions, get_current_user
from mgmt.shared.models import User
from mgmt.services.kubernetes_orchestrator import KubernetesOrchestrator
from mgmt.services.kubernetes_orchestrator.models import TenantDeployment, DeploymentStatus, ResourceTier
from mgmt.services.kubernetes_orchestrator.exceptions import (
    DeploymentNotFoundError, ResourceLimitExceededError, DeploymentFailedError
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tenant-orchestration", tags=["Tenant Orchestration"])


# Pydantic models for API
class DeploymentCreateRequest(BaseModel):
    """Request model for creating tenant deployment."""
    tenant_name: str = Field(..., min_length=1, max_length=255)
    domain_name: Optional[str] = Field(None, regex=r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$')
    resource_tier: ResourceTier = Field(default=ResourceTier.SMALL)
    license_tier: str = Field(default="basic", regex="^(basic|professional|enterprise)$")
    image_tag: str = Field(default="latest", min_length=1)
    cluster_name: str = Field(default="default", min_length=1)
    environment: str = Field(default="production", regex="^(development|staging|production)$")
    
    # Resource customization (optional)
    max_customers: Optional[int] = Field(None, ge=1, le=1000000)
    max_services: Optional[int] = Field(None, ge=1, le=100000)
    api_rate_limit: Optional[int] = Field(None, ge=100, le=1000000)
    
    # Database configuration
    database_url: Optional[str] = None
    redis_url: Optional[str] = None
    
    # Feature configuration
    features: Dict[str, bool] = Field(default_factory=dict)
    custom_config: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('domain_name')
    def validate_domain(cls, v):
        if v and (v.startswith('.') or v.endswith('.') or '..' in v):
            raise ValueError('Invalid domain name format')
        return v


class DeploymentUpdateRequest(BaseModel):
    """Request model for updating tenant deployment."""
    resource_tier: Optional[ResourceTier] = None
    image_tag: Optional[str] = Field(None, min_length=1)
    min_replicas: Optional[int] = Field(None, ge=1, le=20)
    max_replicas: Optional[int] = Field(None, ge=1, le=50)
    domain_name: Optional[str] = None
    features: Optional[Dict[str, bool]] = None


class DeploymentScaleRequest(BaseModel):
    """Request model for scaling tenant deployment."""
    replicas: int = Field(..., ge=1, le=20)
    reason: Optional[str] = Field(None, max_length=500)


class DeploymentResponse(BaseModel):
    """Response model for tenant deployment."""
    id: str
    tenant_id: str
    deployment_name: str
    namespace: str
    status: DeploymentStatus
    resource_tier: ResourceTier
    domain_name: Optional[str]
    license_tier: str
    pod_count: int
    ready_pods: int
    health_status: str
    created_at: datetime
    deployed_at: Optional[datetime]
    last_updated: Optional[datetime]
    
    class Config:
        from_attributes = True


class DeploymentListResponse(BaseModel):
    """Response model for deployment list."""
    deployments: List[DeploymentResponse]
    total_count: int
    page: int
    page_size: int


class ClusterHealthResponse(BaseModel):
    """Response model for cluster health."""
    cluster_healthy: bool
    total_nodes: int
    ready_nodes: int
    total_namespaces: int
    tenant_namespaces: int
    last_check: str
    error: Optional[str] = None


@router.post("/deployments", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_deployment(
    request: DeploymentCreateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permissions(["tenant:create", "deployment:create"]))
):
    """Create a new tenant deployment."""
    try:
        logger.info(f"Creating deployment for tenant: {request.tenant_name}")
        
        orchestrator = KubernetesOrchestrator(session)
        
        # Generate unique tenant ID
        import uuid
        tenant_id = f"{request.tenant_name.lower().replace(' ', '-')}-{str(uuid.uuid4())[:8]}"
        
        # Prepare deployment configuration
        deployment_config = {
            "tenant_name": request.tenant_name,
            "domain_name": request.domain_name,
            "resource_tier": request.resource_tier.value,
            "license_tier": request.license_tier,
            "image_tag": request.image_tag,
            "cluster_name": request.cluster_name,
            "environment": request.environment,
            "max_customers": request.max_customers or 1000,
            "max_services": request.max_services or 500,
            "api_rate_limit": request.api_rate_limit or 1000,
            "database_url": request.database_url,
            "redis_url": request.redis_url,
            "features": request.features,
            **request.custom_config
        }
        
        # Create deployment (this is async and may take time)
        deployment = await orchestrator.create_tenant_deployment(tenant_id, deployment_config)
        
        logger.info(f"✅ Deployment created successfully: {deployment.id}")
        
        return DeploymentResponse(
            id=str(deployment.id),
            tenant_id=deployment.tenant_id,
            deployment_name=deployment.deployment_name,
            namespace=deployment.namespace,
            status=deployment.status,
            resource_tier=deployment.resource_tier,
            domain_name=deployment.domain_name,
            license_tier=deployment.license_tier,
            pod_count=deployment.pod_count,
            ready_pods=deployment.ready_pods,
            health_status=deployment.health_status,
            created_at=deployment.created_at,
            deployed_at=deployment.deployed_at,
            last_updated=deployment.last_updated
        )
        
    except ResourceLimitExceededError as e:
        logger.warning(f"Resource limit exceeded: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Resource limit exceeded: {str(e)}"
        )
    except DeploymentFailedError as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating deployment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during deployment creation"
        )


@router.get("/deployments", response_model=DeploymentListResponse)
async def list_tenant_deployments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[DeploymentStatus] = Query(None),
    tenant_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permissions(["deployment:read"]))
):
    """List tenant deployments with pagination and filtering."""
    try:
        orchestrator = KubernetesOrchestrator(session)
        
        # Build query filters
        filters = []
        if status_filter:
            filters.append(f"status = '{status_filter.value}'")
        if tenant_id:
            filters.append(f"tenant_id = '{tenant_id}'")
        
        # This would be implemented in the orchestrator service
        # For now, returning mock data structure
        deployments = []  # orchestrator.list_deployments(page, page_size, filters)
        total_count = 0   # orchestrator.count_deployments(filters)
        
        return DeploymentListResponse(
            deployments=[
                DeploymentResponse(
                    id=str(deployment.id),
                    tenant_id=deployment.tenant_id,
                    deployment_name=deployment.deployment_name,
                    namespace=deployment.namespace,
                    status=deployment.status,
                    resource_tier=deployment.resource_tier,
                    domain_name=deployment.domain_name,
                    license_tier=deployment.license_tier,
                    pod_count=deployment.pod_count,
                    ready_pods=deployment.ready_pods,
                    health_status=deployment.health_status,
                    created_at=deployment.created_at,
                    deployed_at=deployment.deployed_at,
                    last_updated=deployment.last_updated
                ) for deployment in deployments
            ],
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing deployments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing deployments"
        )


@router.get("/deployments/{tenant_id}", response_model=DeploymentResponse)
async def get_tenant_deployment(
    tenant_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permissions(["deployment:read"]))
):
    """Get specific tenant deployment details."""
    try:
        orchestrator = KubernetesOrchestrator(session)
        
        # Update status from Kubernetes
        deployment = await orchestrator.update_deployment_status(tenant_id)
        
        return DeploymentResponse(
            id=str(deployment.id),
            tenant_id=deployment.tenant_id,
            deployment_name=deployment.deployment_name,
            namespace=deployment.namespace,
            status=deployment.status,
            resource_tier=deployment.resource_tier,
            domain_name=deployment.domain_name,
            license_tier=deployment.license_tier,
            pod_count=deployment.pod_count,
            ready_pods=deployment.ready_pods,
            health_status=deployment.health_status,
            created_at=deployment.created_at,
            deployed_at=deployment.deployed_at,
            last_updated=deployment.last_updated
        )
        
    except DeploymentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment not found for tenant: {tenant_id}"
        )
    except Exception as e:
        logger.error(f"Error getting deployment {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting deployment"
        )


@router.patch("/deployments/{tenant_id}", response_model=DeploymentResponse)
async def update_tenant_deployment(
    tenant_id: str,
    request: DeploymentUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permissions(["deployment:update"]))
):
    """Update tenant deployment configuration."""
    try:
        orchestrator = KubernetesOrchestrator(session)
        
        deployment = await orchestrator.get_tenant_deployment(tenant_id)
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment not found for tenant: {tenant_id}"
            )
        
        # Update deployment fields
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(deployment, field):
                setattr(deployment, field, value)
        
        deployment.last_updated = datetime.utcnow()
        await session.commit()
        
        logger.info(f"Updated deployment for tenant: {tenant_id}")
        
        return DeploymentResponse(
            id=str(deployment.id),
            tenant_id=deployment.tenant_id,
            deployment_name=deployment.deployment_name,
            namespace=deployment.namespace,
            status=deployment.status,
            resource_tier=deployment.resource_tier,
            domain_name=deployment.domain_name,
            license_tier=deployment.license_tier,
            pod_count=deployment.pod_count,
            ready_pods=deployment.ready_pods,
            health_status=deployment.health_status,
            created_at=deployment.created_at,
            deployed_at=deployment.deployed_at,
            last_updated=deployment.last_updated
        )
        
    except Exception as e:
        logger.error(f"Error updating deployment {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating deployment"
        )


@router.post("/deployments/{tenant_id}/scale", response_model=DeploymentResponse)
async def scale_tenant_deployment(
    tenant_id: str,
    request: DeploymentScaleRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permissions(["deployment:scale"]))
):
    """Scale tenant deployment to specified number of replicas."""
    try:
        orchestrator = KubernetesOrchestrator(session)
        
        deployment = await orchestrator.scale_deployment(tenant_id, request.replicas)
        
        logger.info(f"Scaled deployment {tenant_id} to {request.replicas} replicas")
        
        return DeploymentResponse(
            id=str(deployment.id),
            tenant_id=deployment.tenant_id,
            deployment_name=deployment.deployment_name,
            namespace=deployment.namespace,
            status=deployment.status,
            resource_tier=deployment.resource_tier,
            domain_name=deployment.domain_name,
            license_tier=deployment.license_tier,
            pod_count=deployment.pod_count,
            ready_pods=deployment.ready_pods,
            health_status=deployment.health_status,
            created_at=deployment.created_at,
            deployed_at=deployment.deployed_at,
            last_updated=deployment.last_updated
        )
        
    except DeploymentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment not found for tenant: {tenant_id}"
        )
    except Exception as e:
        logger.error(f"Error scaling deployment {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while scaling deployment"
        )


@router.delete("/deployments/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant_deployment(
    tenant_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permissions(["deployment:delete"]))
):
    """Delete tenant deployment and all associated resources."""
    try:
        orchestrator = KubernetesOrchestrator(session)
        
        success = await orchestrator.delete_tenant_deployment(tenant_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment not found for tenant: {tenant_id}"
            )
        
        logger.info(f"Deleted deployment for tenant: {tenant_id}")
        
    except Exception as e:
        logger.error(f"Error deleting deployment {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while deleting deployment"
        )


@router.get("/cluster/health", response_model=ClusterHealthResponse)
async def get_cluster_health(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permissions(["cluster:read"]))
):
    """Get Kubernetes cluster health status."""
    try:
        orchestrator = KubernetesOrchestrator(session)
        health_data = await orchestrator.get_cluster_health()
        
        return ClusterHealthResponse(**health_data)
        
    except Exception as e:
        logger.error(f"Error getting cluster health: {str(e)}")
        return ClusterHealthResponse(
            cluster_healthy=False,
            total_nodes=0,
            ready_nodes=0,
            total_namespaces=0,
            tenant_namespaces=0,
            last_check=datetime.utcnow().isoformat(),
            error=str(e)
        )


@router.post("/deployments/{tenant_id}/restart", response_model=DeploymentResponse)
async def restart_tenant_deployment(
    tenant_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permissions(["deployment:restart"]))
):
    """Restart tenant deployment by updating deployment timestamp."""
    try:
        orchestrator = KubernetesOrchestrator(session)
        
        # This would trigger a rolling restart of the deployment
        # Implementation would patch the deployment with a restart annotation
        
        deployment = await orchestrator.get_tenant_deployment(tenant_id)
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment not found for tenant: {tenant_id}"
            )
        
        # Update status and timestamp to trigger restart
        deployment.status = DeploymentStatus.UPDATING
        deployment.last_updated = datetime.utcnow()
        await session.commit()
        
        logger.info(f"Restarted deployment for tenant: {tenant_id}")
        
        return DeploymentResponse(
            id=str(deployment.id),
            tenant_id=deployment.tenant_id,
            deployment_name=deployment.deployment_name,
            namespace=deployment.namespace,
            status=deployment.status,
            resource_tier=deployment.resource_tier,
            domain_name=deployment.domain_name,
            license_tier=deployment.license_tier,
            pod_count=deployment.pod_count,
            ready_pods=deployment.ready_pods,
            health_status=deployment.health_status,
            created_at=deployment.created_at,
            deployed_at=deployment.deployed_at,
            last_updated=deployment.last_updated
        )
        
    except Exception as e:
        logger.error(f"Error restarting deployment {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while restarting deployment"
        )