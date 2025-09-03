"""
Data models for the DotMac Container Provisioning Service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from pydantic_settings import BaseSettings


class PlanType(str, Enum):
    """ISP Framework service plan types."""

    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class DeploymentStatus(str, Enum):
    """Container deployment status."""

    PENDING = "pending"
    PROVISIONING = "provisioning"
    DEPLOYING = "deploying"
    CONFIGURING = "configuring"
    VALIDATING = "validating"
    READY = "ready"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class HealthStatus(str, Enum):
    """Container health status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    UNKNOWN = "unknown"


class InfrastructureType(str, Enum):
    """Infrastructure deployment type."""

    KUBERNETES = "kubernetes"
    DOCKER = "docker"
    DOCKER_COMPOSE = "docker_compose"


class ResourceRequirements(BaseModel):
    """Container resource requirements specification."""

    cpu_cores: float = Field(
        default=1.0, ge=0.1, le=16.0, description="CPU cores (0.1-16.0)"
    )
    memory_gb: float = Field(
        default=2.0, ge=0.5, le=64.0, description="Memory in GB (0.5-64.0)"
    )
    storage_gb: float = Field(
        default=10.0, ge=1.0, le=500.0, description="Storage in GB (1.0-500.0)"
    )
    max_connections: int = Field(
        default=100, ge=10, le=2000, description="Maximum database connections"
    )
    max_concurrent_requests: int = Field(
        default=50, ge=5, le=1000, description="Maximum concurrent HTTP requests"
    )

    @field_validator("cpu_cores")
    @classmethod
    def validate_cpu(cls, v):
        """Ensure CPU is in valid increments."""
        if v < 0.1 or abs(round(v * 10) - v * 10) > 1e-10:
            raise ValueError("CPU must be in 0.1 core increments")
        return v

    @field_validator("memory_gb")
    @classmethod
    def validate_memory(cls, v):
        """Ensure memory is in valid increments."""
        if v < 0.5 or v % 0.5 != 0:
            raise ValueError("Memory must be in 0.5 GB increments")
        return v

    def to_kubernetes_limits(self) -> Dict[str, str]:
        """Convert to Kubernetes resource limit format."""
        return {
            "cpu": f"{int(self.cpu_cores * 1000)}m",
            "memory": f"{int(self.memory_gb * 1024)}Mi",
            "ephemeral-storage": f"{int(self.storage_gb)}Gi",
        }

    def to_docker_limits(self) -> Dict[str, Any]:
        """Convert to Docker resource limit format."""
        return {
            "cpus": str(self.cpu_cores),
            "memory": f"{int(self.memory_gb)}g",
            "shm_size": "128m",
        }


class NetworkConfig(BaseModel):
    """Network configuration for container deployment."""

    domain: Optional[str] = Field(
        default=None, description="Custom domain for the ISP instance"
    )
    subdomain: Optional[str] = Field(
        default=None, description="Subdomain prefix (auto-generated if not provided)"
    )
    ssl_enabled: bool = Field(default=True, description="Enable SSL/TLS certificates")
    port_mapping: Dict[int, int] = Field(
        default_factory=lambda: {8000: 80, 8443: 443},
        description="Port mapping (internal:external)",
    )
    allowed_origins: List[str] = Field(
        default_factory=list, description="CORS allowed origins"
    )

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        """Validate domain format."""
        if v and not v.replace(".", "").replace("-", "").isalnum():
            raise ValueError(
                "Domain must contain only alphanumeric characters, dots, and hyphens"
            )
        return v


class DatabaseConfig(BaseModel):
    """Database configuration for ISP instance."""

    create_dedicated_db: bool = Field(
        default=True, description="Create dedicated database instance"
    )
    database_size: str = Field(
        default="standard",
        pattern="^(minimal|standard|large|xlarge)$",
        description="Database size tier",
    )
    backup_enabled: bool = Field(default=True, description="Enable automated backups")
    replication_enabled: bool = Field(
        default=False, description="Enable database replication"
    )
    connection_pool_size: int = Field(
        default=20, ge=5, le=100, description="Database connection pool size"
    )


class FeatureFlags(BaseModel):
    """Feature flags for ISP Framework instance."""

    customer_portal: bool = Field(default=True)
    technician_portal: bool = Field(default=True)
    admin_portal: bool = Field(default=True)
    billing_system: bool = Field(default=True)
    notification_system: bool = Field(default=True)
    analytics_dashboard: bool = Field(default=False)
    api_webhooks: bool = Field(default=False)
    bulk_operations: bool = Field(default=False)
    advanced_reporting: bool = Field(default=False)
    multi_language: bool = Field(default=False)

    @classmethod
    def from_plan_type(cls, plan_type: PlanType) -> "FeatureFlags":
        """Create feature flags based on plan type."""
        base_features = cls()

        if plan_type == PlanType.PREMIUM:
            base_features.analytics_dashboard = True
            base_features.advanced_reporting = True

        elif plan_type == PlanType.ENTERPRISE:
            base_features.analytics_dashboard = True
            base_features.api_webhooks = True
            base_features.bulk_operations = True
            base_features.advanced_reporting = True
            base_features.multi_language = True

        return base_features


class ISPConfig(BaseModel):
    """Complete ISP Framework configuration."""

    tenant_name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$",
        description="Tenant identifier (3-50 chars, alphanumeric + hyphens)",
    )
    display_name: str = Field(
        ..., min_length=1, max_length=100, description="Human-readable display name"
    )
    plan_type: PlanType = Field(
        default=PlanType.STANDARD, description="Service plan type"
    )

    # Configuration objects
    network_config: NetworkConfig = Field(default_factory=NetworkConfig)
    database_config: DatabaseConfig = Field(default_factory=DatabaseConfig)
    feature_flags: Optional[FeatureFlags] = Field(default=None)

    # Environment-specific settings
    environment_variables: Dict[str, str] = Field(
        default_factory=dict, description="Additional environment variables"
    )
    secrets: Dict[str, str] = Field(
        default_factory=dict, description="Secret values (will be stored securely)"
    )

    # Branding and customization
    branding_config: Dict[str, Any] = Field(
        default_factory=dict, description="Branding and UI customization settings"
    )

    @model_validator(mode="before")
    @classmethod
    def set_defaults(cls, values):
        """Set default values based on other fields."""
        if isinstance(values, dict):
            if not values.get("feature_flags"):
                values["feature_flags"] = FeatureFlags.from_plan_type(
                    values.get("plan_type", PlanType.STANDARD)
                )

            # Set default subdomain if not provided
            network_config = values.get("network_config", NetworkConfig())
            if not network_config.subdomain:
                network_config.subdomain = values.get("tenant_name", "").lower()
                values["network_config"] = network_config

        return values


class ProvisioningRequest(BaseModel):
    """Request to provision a new ISP Framework container."""

    request_id: UUID = Field(default_factory=uuid4)
    isp_id: UUID = Field(..., description="Unique ISP instance identifier")
    customer_count: int = Field(
        ..., ge=1, le=50000, description="Expected number of customers (1-50,000)"
    )
    config: ISPConfig = Field(..., description="ISP Framework configuration")

    # Resource overrides
    custom_resources: Optional[ResourceRequirements] = Field(
        default=None,
        description="Custom resource requirements (overrides auto-calculation)",
    )

    # Infrastructure preferences
    infrastructure_type: InfrastructureType = Field(
        default=InfrastructureType.KUBERNETES,
        description="Preferred infrastructure type",
    )
    region: str = Field(default="us-east-1", description="Deployment region")
    availability_zone: Optional[str] = Field(
        default=None, description="Specific availability zone"
    )

    # Timing and behavior
    provisioning_timeout: int = Field(
        default=300,
        ge=120,
        le=1800,
        description="Provisioning timeout in seconds (2-30 minutes)",
    )
    enable_rollback: bool = Field(
        default=True, description="Enable automatic rollback on failure"
    )

    # Metadata
    requested_by: Optional[str] = Field(
        default=None, description="User or system requesting provisioning"
    )
    tags: Dict[str, str] = Field(
        default_factory=dict, description="Custom tags for resource management"
    )

    model_config = ConfigDict(
        json_encoders={UUID: str, datetime: lambda v: v.isoformat()}
    )


class ContainerHealth(BaseModel):
    """Container health check results."""

    overall_status: HealthStatus
    database_healthy: bool = False
    api_healthy: bool = False
    ssl_healthy: bool = False
    cache_healthy: bool = False

    # Detailed health information
    database_response_time: Optional[float] = None
    api_response_time: Optional[float] = None
    uptime_seconds: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

    # Health check errors
    failed_checks: List[str] = Field(default_factory=list)
    error_messages: Dict[str, str] = Field(default_factory=dict)

    # Timestamps
    last_check: datetime = Field(default_factory=datetime.utcnow)
    next_check: Optional[datetime] = None


class DeploymentArtifacts(BaseModel):
    """Artifacts created during deployment."""

    container_id: Optional[str] = None
    namespace: Optional[str] = None
    service_name: Optional[str] = None
    ingress_name: Optional[str] = None
    ssl_certificate_name: Optional[str] = None
    database_instance: Optional[str] = None
    redis_instance: Optional[str] = None

    # Generated URLs
    internal_url: Optional[str] = None
    external_url: Optional[str] = None
    admin_url: Optional[str] = None

    # Resource identifiers for cleanup
    created_resources: List[Dict[str, Any]] = Field(default_factory=list)


class ProvisioningResult(BaseModel):
    """Result of container provisioning operation."""

    request_id: UUID
    isp_id: UUID
    success: bool
    status: DeploymentStatus

    # Timing information
    start_time: datetime
    end_time: Optional[datetime] = None
    deployment_duration: Optional[float] = None

    # Deployment information
    artifacts: Optional[DeploymentArtifacts] = None
    allocated_resources: Optional[ResourceRequirements] = None
    health_status: Optional[ContainerHealth] = None

    # Error information
    error_message: Optional[str] = None
    error_stage: Optional[str] = None
    rollback_completed: bool = False

    # Detailed logs
    provisioning_logs: List[str] = Field(default_factory=list)

    # URLs for access
    endpoint_url: Optional[str] = None
    admin_dashboard_url: Optional[str] = None
    api_documentation_url: Optional[str] = None

    model_config = ConfigDict(
        json_encoders={UUID: str, datetime: lambda v: v.isoformat()}
    )

    def add_log(self, message: str, level: str = "INFO") -> None:
        """Add a log entry with timestamp."""
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = f"[{timestamp}] {level}: {message}"
        self.provisioning_logs.append(log_entry)

    def mark_completed(self, success: bool = True) -> None:
        """Mark provisioning as completed."""
        self.end_time = datetime.now(timezone.utc)
        self.success = success
        self.status = DeploymentStatus.READY if success else DeploymentStatus.FAILED

        if self.start_time and self.end_time:
            self.deployment_duration = (self.end_time - self.start_time).total_seconds()


class ProvisioningSettings(BaseSettings):
    """Settings for the provisioning service."""

    # Kubernetes settings
    kubeconfig_path: Optional[str] = None
    kubernetes_namespace: str = "dotmac-tenants"
    default_image_repository: str = "registry.dotmac.app/isp-framework"
    default_image_tag: str = "latest"

    # Docker settings
    docker_registry: str = "registry.dotmac.app"
    docker_network: str = "dotmac-network"

    # Resource defaults
    default_cpu_limit: float = 1.0
    default_memory_limit: float = 2.0
    default_storage_limit: float = 10.0

    # Timeouts
    default_provisioning_timeout: int = 300
    health_check_timeout: int = 60
    rollback_timeout: int = 120

    base_domain: str = "dotmac.app"
    ssl_issuer: str = "letsencrypt-prod"

    model_config = ConfigDict(
        env_prefix="DOTMAC_PROVISIONING_",
        case_sensitive=False
    )
