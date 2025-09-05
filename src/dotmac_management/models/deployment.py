"""
Deployment and infrastructure models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class DeploymentStatus(str, Enum):
    """Deployment status enumeration."""

    PENDING = "pending"
    PROVISIONING = "provisioning"
    DEPLOYING = "deploying"
    RUNNING = "running"
    UPDATING = "updating"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


class CloudProvider(str, Enum):
    """Cloud provider enumeration."""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    DIGITALOCEAN = "digitalocean"
    KUBERNETES = "kubernetes"


class ResourceTier(str, Enum):
    """Resource tier enumeration."""

    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


class DeploymentEventType(str, Enum):
    """Deployment event types."""

    CREATED = "created"
    STARTED = "started"
    PROVISIONED = "provisioned"
    DEPLOYED = "deployed"
    UPDATED = "updated"
    SCALED = "scaled"
    STOPPED = "stopped"
    FAILED = "failed"
    DELETED = "deleted"


class InfrastructureTemplate(BaseModel):
    """Infrastructure deployment templates."""

    __tablename__ = "infrastructure_templates"

    # Template information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False)

    # Cloud configuration
    cloud_provider = Column(SQLEnum(CloudProvider), nullable=False, index=True)
    resource_tier = Column(SQLEnum(ResourceTier), nullable=False, index=True)

    # Resource specifications
    cpu_cores = Column(Integer, nullable=False)
    memory_gb = Column(Integer, nullable=False)
    storage_gb = Column(Integer, nullable=False)
    network_bandwidth_mbps = Column(Integer, nullable=False)

    # Cost estimation
    hourly_cost_cents = Column(Integer, nullable=False)
    monthly_cost_cents = Column(Integer, nullable=False)

    # Template configuration
    template_config = Column(JSON, nullable=False)  # Terraform/OpenTofu config
    environment_variables = Column(JSON, default=dict, nullable=False)

    # Template status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_public = Column(Boolean, default=True, nullable=False)

    # Relationships
    deployments = relationship("Deployment", back_populates="infrastructure_template")

    def __repr__(self) -> str:
        return f"<InfrastructureTemplate(name='{self.name}', provider='{self.cloud_provider}')>"

    @property
    def estimated_monthly_cost(self) -> float:
        """Get estimated monthly cost in dollars."""
        return self.monthly_cost_cents / 100


class Deployment(BaseModel):
    """Tenant deployment tracking."""

    __tablename__ = "deployments"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_tenants.id"),
        nullable=False,
        index=True,
    )
    infrastructure_template_id = Column(
        UUID(as_uuid=True), ForeignKey("infrastructure_templates.id"), nullable=True
    )

    # Deployment identification
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), nullable=False, index=True)

    # Deployment status
    status = Column(
        SQLEnum(DeploymentStatus),
        default=DeploymentStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Cloud configuration
    cloud_provider = Column(SQLEnum(CloudProvider), nullable=False, index=True)
    region = Column(String(100), nullable=False)
    availability_zone = Column(String(100), nullable=True)

    # Resource allocation
    resource_tier = Column(SQLEnum(ResourceTier), nullable=False, index=True)
    allocated_cpu = Column(Integer, nullable=False)
    allocated_memory_gb = Column(Integer, nullable=False)
    allocated_storage_gb = Column(Integer, nullable=False)

    # Network configuration
    public_ip = Column(String(45), nullable=True)  # IPv6 support
    private_ip = Column(String(45), nullable=True)
    domain_name = Column(String(255), nullable=True, index=True)
    ssl_enabled = Column(Boolean, default=True, nullable=False)

    # Deployment configuration
    dotmac_version = Column(String(50), nullable=False)
    environment_variables = Column(JSON, default=dict, nullable=False)
    custom_configuration = Column(JSON, default=dict, nullable=False)

    # Deployment timeline
    deployment_started_at = Column(DateTime, nullable=True)
    deployment_completed_at = Column(DateTime, nullable=True)
    last_update_at = Column(DateTime, nullable=True)

    # Health monitoring
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(20), default="unknown", nullable=False)
    health_details = Column(JSON, default=dict, nullable=False)

    # Cost tracking
    current_hourly_cost_cents = Column(Integer, default=0, nullable=False)
    estimated_monthly_cost_cents = Column(Integer, default=0, nullable=False)
    actual_monthly_cost_cents = Column(Integer, default=0, nullable=False)

    # Scaling configuration
    min_instances = Column(Integer, default=1, nullable=False)
    max_instances = Column(Integer, default=3, nullable=False)
    current_instances = Column(Integer, default=1, nullable=False)
    auto_scaling_enabled = Column(Boolean, default=True, nullable=False)

    # Backup configuration
    backup_enabled = Column(Boolean, default=True, nullable=False)
    backup_retention_days = Column(Integer, default=30, nullable=False)
    last_backup_at = Column(DateTime, nullable=True)

    # Monitoring configuration
    monitoring_enabled = Column(Boolean, default=True, nullable=False)
    alerting_enabled = Column(Boolean, default=True, nullable=False)

    # External references
    cloud_resource_id = Column(
        String(255), nullable=True
    )  # Instance ID from cloud provider
    kubernetes_namespace = Column(String(255), nullable=True)
    load_balancer_id = Column(String(255), nullable=True)

    # Deployment metadata
    deployment_logs = Column(JSON, default=list, nullable=False)
    error_message = Column(Text, nullable=True)

    # User tracking
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="deployments")
    infrastructure_template = relationship(
        "InfrastructureTemplate", back_populates="deployments"
    )
    created_by_user = relationship("User", back_populates="created_deployments")
    events = relationship(
        "DeploymentEvent", back_populates="deployment", cascade="all, delete-orphan"
    )
    resources = relationship(
        "DeploymentResource", back_populates="deployment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Deployment(name='{self.name}', status='{self.status}')>"

    @property
    def is_running(self) -> bool:
        """Check if deployment is running."""
        return self.status == DeploymentStatus.RUNNING

    @property
    def is_healthy(self) -> bool:
        """Check if deployment is healthy."""
        return self.health_status == "healthy"

    @property
    def estimated_monthly_cost(self) -> float:
        """Get estimated monthly cost in dollars."""
        return self.estimated_monthly_cost_cents / 100

    @property
    def current_hourly_cost(self) -> float:
        """Get current hourly cost in dollars."""
        return self.current_hourly_cost_cents / 100

    def start_deployment(self) -> None:
        """Start deployment process."""
        self.status = DeploymentStatus.PROVISIONING
        self.deployment_started_at = datetime.now(timezone.utc)

    def complete_deployment(self) -> None:
        """Mark deployment as completed."""
        self.status = DeploymentStatus.RUNNING
        self.deployment_completed_at = datetime.now(timezone.utc)

    def fail_deployment(self, error_message: str) -> None:
        """Mark deployment as failed."""
        self.status = DeploymentStatus.FAILED
        self.error_message = error_message

    def update_health(
        self, status: str, details: Optional[dict[str, Any]] = None
    ) -> None:
        """Update health status."""
        self.health_status = status
        self.health_details = details or {}
        self.last_health_check = datetime.now(timezone.utc)

    def scale(self, instance_count: int) -> None:
        """Scale deployment."""
        if self.min_instances <= instance_count <= self.max_instances:
            self.current_instances = instance_count
            self.status = DeploymentStatus.UPDATING


class DeploymentEvent(BaseModel):
    """Deployment event tracking."""

    __tablename__ = "deployment_events"

    deployment_id = Column(
        UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=False, index=True
    )

    # Event details
    event_type = Column(SQLEnum(DeploymentEventType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Event status
    is_success = Column(Boolean, nullable=True)  # None for info events
    error_message = Column(Text, nullable=True)

    # Event metadata
    event_data = Column(JSON, default=dict, nullable=False)
    duration_seconds = Column(Integer, nullable=True)

    # User tracking
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    deployment = relationship("Deployment", back_populates="events")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<DeploymentEvent(type='{self.event_type}', deployment_id='{self.deployment_id}')>"


class DeploymentResource(BaseModel):
    """Cloud resources created for deployments."""

    __tablename__ = "deployment_resources"

    deployment_id = Column(
        UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=False, index=True
    )

    # Resource details
    resource_type = Column(
        String(100), nullable=False, index=True
    )  # instance, load_balancer, etc.
    resource_name = Column(String(255), nullable=False)
    resource_id = Column(String(255), nullable=False)  # Cloud provider resource ID

    # Resource configuration
    configuration = Column(JSON, default=dict, nullable=False)

    # Resource status
    status = Column(String(50), default="creating", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Cost tracking
    hourly_cost_cents = Column(Integer, default=0, nullable=False)

    # Relationships
    deployment = relationship("Deployment", back_populates="resources")

    def __repr__(self) -> str:
        return f"<DeploymentResource(type='{self.resource_type}', name='{self.resource_name}')>"

    @property
    def hourly_cost(self) -> float:
        """Get hourly cost in dollars."""
        return self.hourly_cost_cents / 100
