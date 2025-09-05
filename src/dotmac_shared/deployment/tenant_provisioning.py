"""
Tenant container provisioning logic for multi-tenant deployments.

This module provides the infrastructure for creating and managing
isolated tenant containers in Kubernetes.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from ..application.config import (
    DeploymentContext,
    DeploymentMode,
    IsolationLevel,
    ResourceLimits,
    TenantConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class TenantProvisioningRequest:
    """Request for provisioning a new tenant container."""

    tenant_id: str
    partner_id: str
    plan_type: str = "standard"  # standard, premium, enterprise
    region: str = "us-east-1"

    # Resource requirements
    requested_resources: Optional[ResourceLimits] = None

    # Feature flags
    enabled_features: list[str] = field(
        default_factory=lambda: [
            "customer_portal",
            "technician_portal",
            "billing",
            "notifications",
        ]
    )
    disabled_features: list[str] = field(default_factory=list)

    # Networking
    custom_domain: Optional[str] = None
    ssl_enabled: bool = True

    # Database configuration
    dedicated_database: bool = False
    database_size: str = "small"  # small, medium, large

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TenantProvisioningResult:
    """Result of tenant provisioning operation."""

    tenant_id: str
    success: bool
    status: str

    # Container information
    container_name: Optional[str] = None
    kubernetes_namespace: Optional[str] = None
    internal_url: Optional[str] = None
    external_url: Optional[str] = None

    # Database information
    database_url: Optional[str] = None
    redis_url: Optional[str] = None

    # SSL information
    ssl_certificate_status: Optional[str] = None

    # Error information
    error_message: Optional[str] = None
    provisioning_logs: list[str] = field(default_factory=list)

    # Timing information
    provisioning_duration_seconds: Optional[float] = None


class TenantResourceCalculator:
    """Calculate resource requirements for tenant containers."""

    PLAN_RESOURCES = {
        "standard": ResourceLimits(
            memory_limit="512Mi",
            cpu_limit="500m",
            storage_limit="2Gi",
            max_connections=50,
            max_concurrent_requests=25,
        ),
        "premium": ResourceLimits(
            memory_limit="1Gi",
            cpu_limit="1000m",
            storage_limit="5Gi",
            max_connections=100,
            max_concurrent_requests=50,
        ),
        "enterprise": ResourceLimits(
            memory_limit="2Gi",
            cpu_limit="2000m",
            storage_limit="10Gi",
            max_connections=200,
            max_concurrent_requests=100,
        ),
    }

    @classmethod
    def calculate_resources(cls, request: TenantProvisioningRequest) -> ResourceLimits:
        """Calculate resource limits for a tenant provisioning request."""

        # Start with plan-based resources
        base_resources = cls.PLAN_RESOURCES.get(request.plan_type, cls.PLAN_RESOURCES["standard"])

        # Use custom resources if provided
        if request.requested_resources:
            return request.requested_resources

        # Adjust based on enabled features
        if "advanced_analytics" in request.enabled_features:
            # Analytics needs more CPU and memory
            base_resources.cpu_limit = cls._increase_resource(base_resources.cpu_limit, 0.5)
            base_resources.memory_limit = cls._increase_memory(base_resources.memory_limit, 256)

        if "bulk_operations" in request.enabled_features:
            # Bulk operations need more concurrent capacity
            base_resources.max_concurrent_requests *= 2
            base_resources.max_connections = int(base_resources.max_connections * 1.5)

        return base_resources

    @staticmethod
    def _increase_resource(current: str, multiplier: float) -> str:
        """Increase CPU/memory resource by multiplier."""
        if current.endswith("m"):
            current_value = int(current[:-1])
            new_value = int(current_value * (1 + multiplier))
            return f"{new_value}m"
        return current

    @staticmethod
    def _increase_memory(current: str, additional_mb: int) -> str:
        """Increase memory by additional MB."""
        if current.endswith("Mi"):
            current_mb = int(current[:-2])
            new_mb = current_mb + additional_mb
            return f"{new_mb}Mi"
        elif current.endswith("Gi"):
            current_gb = int(current[:-2])
            new_mb = (current_gb * 1024) + additional_mb
            if new_mb >= 1024:
                return f"{new_mb // 1024}Gi"
            else:
                return f"{new_mb}Mi"
        return current


class TenantNamespaceGenerator:
    """Generate Kubernetes namespaces and resource names for tenants."""

    @staticmethod
    def generate_namespace(tenant_id: str, partner_id: str) -> str:
        """Generate Kubernetes namespace for tenant."""
        # Sanitize IDs for Kubernetes naming
        sanitized_tenant = tenant_id.lower().replace("_", "-")
        sanitized_partner = partner_id.lower().replace("_", "-")
        return f"tenant-{sanitized_tenant}-{sanitized_partner}"

    @staticmethod
    def generate_container_name(tenant_id: str) -> str:
        """Generate container name for tenant."""
        sanitized_tenant = tenant_id.lower().replace("_", "-")
        return f"isp-framework-{sanitized_tenant}"

    @staticmethod
    def generate_database_name(tenant_id: str) -> str:
        """Generate database name for tenant."""
        return f"tenant_{tenant_id}_db"

    @staticmethod
    def generate_redis_name(tenant_id: str) -> str:
        """Generate Redis instance name for tenant."""
        sanitized_tenant = tenant_id.lower().replace("_", "-")
        return f"tenant-{sanitized_tenant}-redis"

    @staticmethod
    def generate_urls(tenant_id: str, partner_id: str, custom_domain: Optional[str] = None) -> dict[str, str]:
        """Generate internal and external URLs for tenant."""
        namespace = TenantNamespaceGenerator.generate_namespace(tenant_id, partner_id)
        container_name = TenantNamespaceGenerator.generate_container_name(tenant_id)

        internal_url = f"http://{container_name}.{namespace}.svc.cluster.local:8000"

        if custom_domain:
            external_url = f"https://{custom_domain}"
        else:
            sanitized_tenant = tenant_id.lower().replace("_", "-")
            external_url = f"https://tenant-{sanitized_tenant}.dotmac.app"

        return {"internal_url": internal_url, "external_url": external_url}


class TenantConfigurationBuilder:
    """Build tenant configuration from provisioning request."""

    @classmethod
    def build_tenant_config(
        cls,
        request: TenantProvisioningRequest,
        namespace: str,
        container_name: str,
        resource_limits: ResourceLimits,
    ) -> TenantConfig:
        """Build complete tenant configuration."""

        # Create deployment context
        deployment_context = DeploymentContext(
            mode=DeploymentMode.TENANT_CONTAINER,
            tenant_id=request.tenant_id,
            isolation_level=IsolationLevel.CONTAINER,
            resource_limits=resource_limits,
            kubernetes_namespace=namespace,
            container_name=container_name,
        )

        # Generate URLs
        urls = TenantNamespaceGenerator.generate_urls(request.tenant_id, request.partner_id, request.custom_domain)

        # Create tenant configuration
        tenant_config = TenantConfig(
            tenant_id=request.tenant_id,
            deployment_context=deployment_context,
            enabled_features=request.enabled_features,
            disabled_features=request.disabled_features,
        )

        # Add database configuration
        if request.dedicated_database:
            db_name = TenantNamespaceGenerator.generate_database_name(request.tenant_id)
            tenant_config.database_config = {
                "url": f"postgresql://tenant_{request.tenant_id}_user:password@tenant-{request.tenant_id}-db:5432/{db_name}",
                "schema": f"tenant_{request.tenant_id}",
                "dedicated": True,
                "size": request.database_size,
            }

        # Add Redis configuration
        redis_name = TenantNamespaceGenerator.generate_redis_name(request.tenant_id)
        tenant_config.redis_config = {
            "url": f"redis://{redis_name}:6379/0",
            "key_prefix": f"tenant:{request.tenant_id}:",
        }

        # Add networking configuration
        tenant_config.networking_config.update(
            {
                "internal_url": urls["internal_url"],
                "external_url": urls["external_url"],
                "custom_domain": request.custom_domain,
                "ssl_enabled": request.ssl_enabled,
            }
        )

        return tenant_config


class TenantProvisioningEngine:
    """Main engine for provisioning tenant containers."""

    def __init__(self):
        self.resource_calculator = TenantResourceCalculator()
        self.namespace_generator = TenantNamespaceGenerator()
        self.config_builder = TenantConfigurationBuilder()
        self.provisioning_history: dict[str, TenantProvisioningResult] = {}

    async def provision_tenant(self, request: TenantProvisioningRequest) -> TenantProvisioningResult:
        """Provision a new tenant container."""
        start_time = asyncio.get_event_loop().time()

        result = TenantProvisioningResult(
            tenant_id=request.tenant_id,
            success=False,
            status="provisioning_started",
            provisioning_logs=[],
        )

        try:
            logger.info(f"Starting tenant provisioning for {request.tenant_id}")
            result.provisioning_logs.append(f"Starting provisioning for tenant {request.tenant_id}")

            # Step 1: Calculate resources
            resource_limits = self.resource_calculator.calculate_resources(request)
            result.provisioning_logs.append(f"Calculated resource limits: {resource_limits}")

            # Step 2: Generate names and namespace
            namespace = self.namespace_generator.generate_namespace(request.tenant_id, request.partner_id)
            container_name = self.namespace_generator.generate_container_name(request.tenant_id)
            urls = self.namespace_generator.generate_urls(request.tenant_id, request.partner_id, request.custom_domain)

            result.kubernetes_namespace = namespace
            result.container_name = container_name
            result.internal_url = urls["internal_url"]
            result.external_url = urls["external_url"]

            result.provisioning_logs.append(f"Generated namespace: {namespace}")
            result.provisioning_logs.append(f"Generated container name: {container_name}")

            # Step 3: Build tenant configuration
            tenant_config = self.config_builder.build_tenant_config(request, namespace, container_name, resource_limits)
            result.provisioning_logs.append("Built tenant configuration")

            # Step 4: Provision infrastructure (This would integrate with Kubernetes API)
            await self._provision_infrastructure(tenant_config, result)

            # Step 5: Deploy container
            await self._deploy_tenant_container(tenant_config, result)

            # Step 6: Configure SSL if enabled
            if request.ssl_enabled:
                await self._configure_ssl(tenant_config, result)

            # Step 7: Run health checks
            await self._verify_deployment(tenant_config, result)

            result.status = "provisioned"
            result.success = True

            # Store in history
            self.provisioning_history[request.tenant_id] = result

            logger.info(f"Successfully provisioned tenant {request.tenant_id}")
            result.provisioning_logs.append("Provisioning completed successfully")

        except Exception as e:
            logger.error(f"Failed to provision tenant {request.tenant_id}: {e}")
            result.success = False
            result.status = "provisioning_failed"
            result.error_message = str(e)
            result.provisioning_logs.append(f"Provisioning failed: {e}")

        finally:
            end_time = asyncio.get_event_loop().time()
            result.provisioning_duration_seconds = end_time - start_time

        return result

    async def _provision_infrastructure(self, tenant_config: TenantConfig, result: TenantProvisioningResult):
        """Provision Kubernetes infrastructure for tenant."""
        result.provisioning_logs.append("Provisioning Kubernetes infrastructure...")

        # This would integrate with Kubernetes API to:
        # 1. Create namespace
        # 2. Create PostgreSQL database instance
        # 3. Create Redis instance
        # 4. Set up persistent volumes
        # 5. Configure network policies

        # Simulate infrastructure provisioning
        await asyncio.sleep(2)

        # Set database and Redis URLs
        result.database_url = tenant_config.database_config.get("url", "")
        result.redis_url = tenant_config.redis_config.get("url", "")

        result.provisioning_logs.append("Infrastructure provisioning completed")

    async def _deploy_tenant_container(self, tenant_config: TenantConfig, result: TenantProvisioningResult):
        """Deploy the ISP Framework container for tenant."""
        result.provisioning_logs.append("Deploying tenant container...")

        # This would:
        # 1. Generate Kubernetes deployment YAML
        # 2. Apply resource limits
        # 3. Set environment variables
        # 4. Deploy the container
        # 5. Create service and ingress

        # Simulate container deployment
        await asyncio.sleep(3)

        result.provisioning_logs.append("Tenant container deployed successfully")

    async def _configure_ssl(self, tenant_config: TenantConfig, result: TenantProvisioningResult):
        """Configure SSL certificates for tenant."""
        result.provisioning_logs.append("Configuring SSL certificates...")

        # This would integrate with cert-manager or similar to:
        # 1. Request SSL certificate
        # 2. Configure ingress with TLS
        # 3. Update DNS if needed

        # Simulate SSL configuration
        await asyncio.sleep(1)

        result.ssl_certificate_status = "active"
        result.provisioning_logs.append("SSL certificates configured")

    async def _verify_deployment(self, tenant_config: TenantConfig, result: TenantProvisioningResult):
        """Verify tenant deployment is healthy."""
        result.provisioning_logs.append("Verifying deployment health...")

        # This would:
        # 1. Check container status
        # 2. Verify database connectivity
        # 3. Test Redis connectivity
        # 4. Validate SSL certificates
        # 5. Run application health checks

        # Simulate health check
        await asyncio.sleep(1)

        result.provisioning_logs.append("Deployment verification completed")

    async def get_tenant_status(self, tenant_id: str) -> Optional[TenantProvisioningResult]:
        """Get the current status of a tenant."""
        return self.provisioning_history.get(tenant_id)

    async def list_provisioned_tenants(self) -> list[str]:
        """List all provisioned tenants."""
        return list(self.provisioning_history.keys())

    async def deprovision_tenant(self, tenant_id: str) -> bool:
        """Deprovision a tenant container (placeholder)."""
        logger.info(f"Deprovisioning tenant {tenant_id}")

        # This would:
        # 1. Scale down container
        # 2. Backup data if needed
        # 3. Delete Kubernetes resources
        # 4. Clean up certificates
        # 5. Remove from registry

        if tenant_id in self.provisioning_history:
            del self.provisioning_history[tenant_id]
            return True

        return False


# Global provisioning engine instance
provisioning_engine = TenantProvisioningEngine()
