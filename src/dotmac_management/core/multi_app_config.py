"""
Enhanced tenant configuration for multi-application deployments.

Extends the existing TenantConfig to support multiple applications within a single tenant container.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from dotmac_shared.application.config import (
    DeploymentContext,
    ResourceLimits,
    TenantConfig,
)

from .application_registry import ApplicationTemplate, get_application_registry

logger = logging.getLogger(__name__)


class ApplicationStatus(str, Enum):
    """Status of an application deployment."""

    PENDING = "pending"  # Awaiting deployment
    DEPLOYING = "deploying"  # Currently being deployed
    RUNNING = "running"  # Successfully running
    STOPPED = "stopped"  # Stopped (intentionally)
    FAILED = "failed"  # Deployment or runtime failure
    UPDATING = "updating"  # Being updated
    REMOVING = "removing"  # Being removed


@dataclass
class ApplicationDeployment:
    """Configuration for a single application deployment within a tenant."""

    # Basic Configuration
    app_type: str  # From ApplicationRegistry
    instance_name: str  # Unique within tenant
    version: Optional[str] = None  # Override template version

    # Status and Control
    enabled: bool = True
    status: ApplicationStatus = ApplicationStatus.PENDING

    # Configuration Overrides
    config_overrides: dict[str, Any] = field(default_factory=dict)
    environment_overrides: dict[str, str] = field(default_factory=dict)

    # Resource Overrides
    resource_overrides: Optional[ResourceLimits] = None

    # Scaling Configuration
    auto_scale: bool = False
    min_instances: int = 1
    max_instances: int = 1

    # Network Configuration
    custom_domain: Optional[str] = None  # Custom subdomain
    port_overrides: dict[int, int] = field(default_factory=dict)  # internal -> external

    # Health and Monitoring
    health_check_overrides: Optional[dict[str, Any]] = None

    # Metadata
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)

    def get_effective_config(self, template: ApplicationTemplate) -> dict[str, Any]:
        """Get effective configuration by merging template defaults with overrides."""

        config = template.default_config.copy()
        config.update(self.config_overrides)
        return config

    def get_effective_environment(self, base_env: dict[str, str]) -> dict[str, str]:
        """Get effective environment variables."""

        env = base_env.copy()
        env.update(self.environment_overrides)
        return env

    def get_deployment_name(self, tenant_id: str) -> str:
        """Get unique deployment name for Kubernetes/Docker."""
        return f"{self.app_type}-{self.instance_name}-{tenant_id}".lower().replace("_", "-")


@dataclass
class NetworkConfiguration:
    """Network configuration for tenant applications."""

    # Network Isolation
    isolated_network: bool = True
    network_name: Optional[str] = None  # Custom network name

    # Load Balancing
    load_balancer_enabled: bool = True
    load_balancer_algorithm: str = "round_robin"  # round_robin, least_conn, ip_hash

    # SSL/TLS
    ssl_enabled: bool = True
    ssl_redirect: bool = True
    custom_certificates: dict[str, str] = field(default_factory=dict)  # domain -> cert_path

    # Domain Configuration
    base_domain: str = "dotmac.cloud"
    custom_domains: list[str] = field(default_factory=list)


@dataclass
class MultiAppTenantConfig:
    """Enhanced tenant configuration supporting multiple applications."""

    # Base Configuration (from original TenantConfig)
    tenant_id: str
    partner_id: str = "default"
    plan_type: str = "standard"
    deployment_context: Optional[DeploymentContext] = None

    # Multi-Application Configuration
    applications: list[ApplicationDeployment] = field(default_factory=list)

    # Shared Infrastructure
    shared_services: list[str] = field(default_factory=lambda: ["postgres", "redis"])
    shared_volumes: dict[str, str] = field(default_factory=dict)  # name -> mount_path

    # Network Configuration
    network_config: Optional[NetworkConfiguration] = None

    # Resource Management
    total_resource_limits: Optional[ResourceLimits] = None
    resource_quotas: dict[str, str] = field(default_factory=dict)

    # Security Configuration
    security_policies: dict[str, Any] = field(default_factory=dict)
    secrets: dict[str, str] = field(default_factory=dict)

    # Backup and Persistence
    backup_enabled: bool = True
    backup_schedule: str = "0 2 * * *"  # Daily at 2 AM
    retention_days: int = 30

    # Monitoring and Logging
    monitoring_enabled: bool = True
    logging_level: str = "INFO"
    metrics_retention_days: int = 7

    # Metadata
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation and setup."""

        if not self.network_config:
            self.network_config = NetworkConfiguration()

        # Validate applications
        registry = get_application_registry()
        for app_deployment in self.applications:
            template = registry.get_application(app_deployment.app_type)
            if not template:
                raise ValueError(f"Unknown application type: {app_deployment.app_type}")

    def add_application(self, app_deployment: ApplicationDeployment) -> None:
        """Add application to tenant configuration."""

        # Validate application type exists
        registry = get_application_registry()
        template = registry.get_application(app_deployment.app_type)
        if not template:
            raise ValueError(f"Unknown application type: {app_deployment.app_type}")

        # Validate unique instance name
        existing_names = {app.instance_name for app in self.applications}
        if app_deployment.instance_name in existing_names:
            raise ValueError(f"Instance name '{app_deployment.instance_name}' already exists")

        self.applications.append(app_deployment)
        logger.info(
            f"Added application {app_deployment.app_type}:{app_deployment.instance_name} to tenant {self.tenant_id}"
        )

    def remove_application(self, instance_name: str) -> bool:
        """Remove application from tenant configuration."""

        for i, app in enumerate(self.applications):
            if app.instance_name == instance_name:
                removed_app = self.applications.pop(i)
                logger.info(f"Removed application {removed_app.app_type}:{instance_name} from tenant {self.tenant_id}")
                return True

        return False

    def get_application(self, instance_name: str) -> Optional[ApplicationDeployment]:
        """Get application deployment by instance name."""

        for app in self.applications:
            if app.instance_name == instance_name:
                return app

        return None

    def get_applications_by_type(self, app_type: str) -> list[ApplicationDeployment]:
        """Get all applications of a specific type."""

        return [app for app in self.applications if app.app_type == app_type]

    def validate_configuration(self) -> dict[str, list[str]]:
        """Validate the entire tenant configuration and return any issues."""

        issues = {}

        # Validate application dependencies
        registry = get_application_registry()
        app_types = [app.app_type for app in self.applications]
        dependency_issues = registry.validate_dependencies(app_types)
        if dependency_issues:
            issues["dependencies"] = dependency_issues

        # Validate resource limits
        if self.total_resource_limits:
            total_cpu_request = 0
            total_memory_request = 0

            for app in self.applications:
                template = registry.get_application(app.app_type)
                if template:
                    # Parse CPU and memory requests
                    cpu_request = template.resource_requirements.cpu_request
                    memory_request = template.resource_requirements.memory_request

                    # Simple validation (could be enhanced with proper parsing)
                    if cpu_request.endswith("m"):
                        total_cpu_request += int(cpu_request[:-1])

                    if memory_request.endswith("Mi"):
                        total_memory_request += int(memory_request[:-2])
                    elif memory_request.endswith("Gi"):
                        total_memory_request += int(memory_request[:-2]) * 1024

            # Check against limits (simplified)
            tenant_cpu_limit = self.total_resource_limits.cpu_limit

            resource_issues = []
            if tenant_cpu_limit and tenant_cpu_limit.endswith("m"):
                if total_cpu_request > int(tenant_cpu_limit[:-1]):
                    resource_issues.append(f"CPU request ({total_cpu_request}m) exceeds limit ({tenant_cpu_limit})")

            if resource_issues:
                issues["resources"] = resource_issues

        return issues

    def get_deployment_order(self) -> list[str]:
        """Get deployment order for applications based on dependencies."""

        registry = get_application_registry()
        app_types = [app.app_type for app in self.applications]
        return registry.get_deployment_order(app_types)

    def to_legacy_tenant_config(self) -> TenantConfig:
        """Convert to legacy TenantConfig for backward compatibility."""

        return TenantConfig(
            tenant_id=self.tenant_id,
            partner_id=self.partner_id,
            plan_type=self.plan_type,
            deployment_context=self.deployment_context or DeploymentContext(),
        )

    @classmethod
    def from_legacy_tenant_config(
        cls,
        legacy_config: TenantConfig,
        applications: Optional[list[ApplicationDeployment]] = None,
    ) -> "MultiAppTenantConfig":
        """Create MultiAppTenantConfig from legacy TenantConfig."""

        if applications is None:
            # Default to ISP Framework for backward compatibility
            applications = [
                ApplicationDeployment(
                    app_type="isp_framework",
                    instance_name="main",
                    config_overrides={
                        "tenant_id": legacy_config.tenant_id,
                        "partner_id": legacy_config.partner_id,
                        "plan_type": legacy_config.plan_type,
                    },
                )
            ]

        return cls(
            tenant_id=legacy_config.tenant_id,
            partner_id=legacy_config.partner_id,
            plan_type=legacy_config.plan_type,
            deployment_context=legacy_config.deployment_context,
            applications=applications,
        )
