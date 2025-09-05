"""
Deployment and infrastructure schemas for validation and serialization.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .common import BaseSchema, PaginatedResponse


class DeploymentTemplateBase(BaseModel):
    """DeploymentTemplateBase implementation."""

    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field(..., description="Template category")
    cloud_provider: str = Field(..., description="Target cloud provider")
    template_type: str = Field(
        ..., description="Template type (terraform, cloudformation, etc.)"
    )
    template_content: dict[str, Any] = Field(..., description="Template definition")
    variables: dict[str, Any] = Field(
        default_factory=dict, description="Template variables"
    )
    requirements: dict[str, Any] = Field(
        default_factory=dict, description="Resource requirements"
    )
    tags: list[str] = Field(default_factory=list, description="Template tags")
    is_active: bool = Field(default=True, description="Whether template is active")


class DeploymentTemplateCreate(DeploymentTemplateBase):
    """DeploymentTemplateCreate implementation."""

    pass


class DeploymentTemplateUpdate(BaseModel):
    """DeploymentTemplateUpdate implementation."""

    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    template_content: Optional[dict[str, Any]] = None
    variables: Optional[dict[str, Any]] = None
    requirements: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = None


class DeploymentTemplate(DeploymentTemplateBase, BaseSchema):
    """DeploymentTemplate implementation."""

    pass


class InfrastructureBase(BaseModel):
    """InfrastructureBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., description="Infrastructure name")
    cloud_provider: str = Field(..., description="Cloud provider")
    region: str = Field(..., description="Deployment region")
    environment: str = Field(..., description="Environment (dev, staging, prod)")
    status: str = Field(..., description="Infrastructure status")
    configuration: dict[str, Any] = Field(
        default_factory=dict, description="Infrastructure configuration"
    )
    resources: dict[str, Any] = Field(
        default_factory=dict, description="Deployed resources"
    )
    endpoints: dict[str, str] = Field(
        default_factory=dict, description="Service endpoints"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class InfrastructureCreate(InfrastructureBase):
    """InfrastructureCreate implementation."""

    pass


class InfrastructureUpdate(BaseModel):
    """InfrastructureUpdate implementation."""

    name: Optional[str] = None
    status: Optional[str] = None
    configuration: Optional[dict[str, Any]] = None
    resources: Optional[dict[str, Any]] = None
    endpoints: Optional[dict[str, str]] = None
    metadata: Optional[dict[str, Any]] = None


class Infrastructure(InfrastructureBase, BaseSchema):
    """Infrastructure implementation."""

    pass


class DeploymentBase(BaseModel):
    """DeploymentBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    infrastructure_id: Optional[UUID] = Field(None, description="Infrastructure ID")
    template_id: Optional[UUID] = Field(None, description="Template ID")
    name: str = Field(..., description="Deployment name")
    version: str = Field(..., description="Deployment version")
    status: str = Field(..., description="Deployment status")
    environment: str = Field(..., description="Target environment")
    configuration: dict[str, Any] = Field(
        default_factory=dict, description="Deployment configuration"
    )
    variables: dict[str, Any] = Field(
        default_factory=dict, description="Deployment variables"
    )
    deployed_at: Optional[datetime] = Field(None, description="Deployment timestamp")
    metadata: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class DeploymentCreate(DeploymentBase):
    """DeploymentCreate implementation."""

    pass


class DeploymentUpdate(BaseModel):
    """DeploymentUpdate implementation."""

    name: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    configuration: Optional[dict[str, Any]] = None
    variables: Optional[dict[str, Any]] = None
    deployed_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None


class Deployment(DeploymentBase, BaseSchema):
    """Deployment implementation."""

    infrastructure: Optional[Infrastructure] = None
    template: Optional[DeploymentTemplate] = None


class ServiceInstanceBase(BaseModel):
    """ServiceInstanceBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    deployment_id: UUID = Field(..., description="Deployment ID")
    service_name: str = Field(..., description="Service name")
    service_type: str = Field(..., description="Service type")
    status: str = Field(..., description="Service status")
    health_status: str = Field(..., description="Health status")
    version: str = Field(..., description="Service version")
    configuration: dict[str, Any] = Field(
        default_factory=dict, description="Service configuration"
    )
    endpoints: dict[str, str] = Field(
        default_factory=dict, description="Service endpoints"
    )
    resource_usage: dict[str, Any] = Field(
        default_factory=dict, description="Resource usage metrics"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ServiceInstanceCreate(ServiceInstanceBase):
    """ServiceInstanceCreate implementation."""

    pass


class ServiceInstanceUpdate(BaseModel):
    """ServiceInstanceUpdate implementation."""

    status: Optional[str] = None
    health_status: Optional[str] = None
    version: Optional[str] = None
    configuration: Optional[dict[str, Any]] = None
    endpoints: Optional[dict[str, str]] = None
    resource_usage: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None


class ServiceInstance(ServiceInstanceBase, BaseSchema):
    """ServiceInstance implementation."""

    deployment: Optional[Deployment] = None


class DeploymentLogBase(BaseModel):
    """DeploymentLogBase implementation."""

    deployment_id: UUID = Field(..., description="Deployment ID")
    log_level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    component: Optional[str] = Field(None, description="Component name")
    timestamp: datetime = Field(..., description="Log timestamp")
    metadata: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class DeploymentLogCreate(DeploymentLogBase):
    """DeploymentLogCreate implementation."""

    pass


class DeploymentLog(DeploymentLogBase, BaseSchema):
    """DeploymentLog implementation."""

    pass


# Response schemas
class DeploymentTemplateListResponse(PaginatedResponse):
    """DeploymentTemplateListResponse implementation."""

    items: list[DeploymentTemplate]


class InfrastructureListResponse(PaginatedResponse):
    """InfrastructureListResponse implementation."""

    items: list[Infrastructure]


class DeploymentListResponse(PaginatedResponse):
    """DeploymentListResponse implementation."""

    items: list[Deployment]


class ServiceInstanceListResponse(PaginatedResponse):
    """ServiceInstanceListResponse implementation."""

    items: list[ServiceInstance]


class DeploymentLogListResponse(PaginatedResponse):
    """DeploymentLogListResponse implementation."""

    items: list[DeploymentLog]


# Complex operation schemas
class DeploymentRequest(BaseModel):
    """DeploymentRequest implementation."""

    template_id: UUID = Field(..., description="Template to deploy")
    name: str = Field(..., description="Deployment name")
    environment: str = Field(..., description="Target environment")
    variables: dict[str, Any] = Field(
        default_factory=dict, description="Deployment variables"
    )
    configuration: dict[str, Any] = Field(
        default_factory=dict, description="Additional configuration"
    )


class ScalingRequest(BaseModel):
    """ScalingRequest implementation."""

    service_name: str = Field(..., description="Service to scale")
    target_instances: int = Field(..., ge=1, description="Target instance count")
    resource_limits: Optional[dict[str, str]] = Field(
        None, description="Resource limits"
    )


class RollbackRequest(BaseModel):
    """RollbackRequest implementation."""

    target_version: str = Field(..., description="Version to rollback to")
    reason: Optional[str] = Field(None, description="Rollback reason")


# Status and monitoring schemas
class DeploymentStatus(BaseModel):
    """DeploymentStatus implementation."""

    deployment_id: UUID
    status: str
    health_score: float
    uptime_percentage: float
    last_deployed: Optional[datetime]
    active_services: int
    failed_services: int
    resource_utilization: dict[str, float]
    recent_logs: list[DeploymentLog]


class InfrastructureHealth(BaseModel):
    """InfrastructureHealth implementation."""

    infrastructure_id: UUID
    overall_health: str
    health_score: float
    active_deployments: int
    resource_usage: dict[str, float]
    alerts: list[dict[str, Any]]
    last_check: datetime


class TenantDeploymentOverview(BaseModel):
    """TenantDeploymentOverview implementation."""

    tenant_id: UUID
    total_deployments: int
    active_deployments: int
    failed_deployments: int
    total_services: int
    healthy_services: int
    infrastructure_count: int
    monthly_deployment_cost: Optional[float]
    recent_deployments: list[Deployment]
