"""
Deployment and infrastructure schemas for validation and serialization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.common import BaseSchema, PaginatedResponse


class DeploymentTemplateBase(BaseModel):
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field(..., description="Template category")
    cloud_provider: str = Field(..., description="Target cloud provider")
    template_type: str = Field(..., description="Template type (terraform, cloudformation, etc.)")
    template_content: Dict[str, Any] = Field(..., description="Template definition")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Template variables")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="Resource requirements")
    tags: List[str] = Field(default_factory=list, description="Template tags")
    is_active: bool = Field(default=True, description="Whether template is active")


class DeploymentTemplateCreate(DeploymentTemplateBase):
    pass


class DeploymentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    template_content: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    requirements: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class DeploymentTemplate(DeploymentTemplateBase, BaseSchema):
    pass


class InfrastructureBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., description="Infrastructure name")
    cloud_provider: str = Field(..., description="Cloud provider")
    region: str = Field(..., description="Deployment region")
    environment: str = Field(..., description="Environment (dev, staging, prod)")
    status: str = Field(..., description="Infrastructure status")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Infrastructure configuration")
    resources: Dict[str, Any] = Field(default_factory=dict, description="Deployed resources")
    endpoints: Dict[str, str] = Field(default_factory=dict, description="Service endpoints")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class InfrastructureCreate(InfrastructureBase):
    pass


class InfrastructureUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    endpoints: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class Infrastructure(InfrastructureBase, BaseSchema):
    pass


class DeploymentBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    infrastructure_id: Optional[UUID] = Field(None, description="Infrastructure ID")
    template_id: Optional[UUID] = Field(None, description="Template ID")
    name: str = Field(..., description="Deployment name")
    version: str = Field(..., description="Deployment version")
    status: str = Field(..., description="Deployment status")
    environment: str = Field(..., description="Target environment")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Deployment configuration")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Deployment variables")
    deployed_at: Optional[datetime] = Field(None, description="Deployment timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class DeploymentCreate(DeploymentBase):
    pass


class DeploymentUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    deployed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class Deployment(DeploymentBase, BaseSchema):
    infrastructure: Optional[Infrastructure] = None
    template: Optional[DeploymentTemplate] = None


class ServiceInstanceBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    deployment_id: UUID = Field(..., description="Deployment ID")
    service_name: str = Field(..., description="Service name")
    service_type: str = Field(..., description="Service type")
    status: str = Field(..., description="Service status")
    health_status: str = Field(..., description="Health status")
    version: str = Field(..., description="Service version")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Service configuration")
    endpoints: Dict[str, str] = Field(default_factory=dict, description="Service endpoints")
    resource_usage: Dict[str, Any] = Field(default_factory=dict, description="Resource usage metrics")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class ServiceInstanceCreate(ServiceInstanceBase):
    pass


class ServiceInstanceUpdate(BaseModel):
    status: Optional[str] = None
    health_status: Optional[str] = None
    version: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    endpoints: Optional[Dict[str, str]] = None
    resource_usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ServiceInstance(ServiceInstanceBase, BaseSchema):
    deployment: Optional[Deployment] = None


class DeploymentLogBase(BaseModel):
    deployment_id: UUID = Field(..., description="Deployment ID")
    log_level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    component: Optional[str] = Field(None, description="Component name")
    timestamp: datetime = Field(..., description="Log timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class DeploymentLogCreate(DeploymentLogBase):
    pass


class DeploymentLog(DeploymentLogBase, BaseSchema):
    pass


# Response schemas
class DeploymentTemplateListResponse(PaginatedResponse):
    items: List[DeploymentTemplate]


class InfrastructureListResponse(PaginatedResponse):
    items: List[Infrastructure]


class DeploymentListResponse(PaginatedResponse):
    items: List[Deployment]


class ServiceInstanceListResponse(PaginatedResponse):
    items: List[ServiceInstance]


class DeploymentLogListResponse(PaginatedResponse):
    items: List[DeploymentLog]


# Complex operation schemas
class DeploymentRequest(BaseModel):
    template_id: UUID = Field(..., description="Template to deploy")
    name: str = Field(..., description="Deployment name")
    environment: str = Field(..., description="Target environment")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Deployment variables")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


class ScalingRequest(BaseModel):
    service_name: str = Field(..., description="Service to scale")
    target_instances: int = Field(..., ge=1, description="Target instance count")
    resource_limits: Optional[Dict[str, str]] = Field(None, description="Resource limits")


class RollbackRequest(BaseModel):
    target_version: str = Field(..., description="Version to rollback to")
    reason: Optional[str] = Field(None, description="Rollback reason")


# Status and monitoring schemas
class DeploymentStatus(BaseModel):
    deployment_id: UUID
    status: str
    health_score: float
    uptime_percentage: float
    last_deployed: Optional[datetime]
    active_services: int
    failed_services: int
    resource_utilization: Dict[str, float]
    recent_logs: List[DeploymentLog]


class InfrastructureHealth(BaseModel):
    infrastructure_id: UUID
    overall_health: str
    health_score: float
    active_deployments: int
    resource_usage: Dict[str, float]
    alerts: List[Dict[str, Any]]
    last_check: datetime


class TenantDeploymentOverview(BaseModel):
    tenant_id: UUID
    total_deployments: int
    active_deployments: int
    failed_deployments: int
    total_services: int
    healthy_services: int
    infrastructure_count: int
    monthly_deployment_cost: Optional[float]
    recent_deployments: List[Deployment]