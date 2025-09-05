"""
Configuration system for deployment-aware application factory.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class DeploymentMode(str, Enum):
    """Deployment modes for different application contexts."""

    MANAGEMENT_PLATFORM = "management_platform"
    TENANT_CONTAINER = "tenant_container"
    STANDALONE = "standalone"
    DEVELOPMENT = "development"


class IsolationLevel(str, Enum):
    """Tenant isolation levels."""

    CONTAINER = "container"  # Full container isolation (K8s)
    PROCESS = "process"  # Process-level isolation
    DATABASE = "database"  # Database-level isolation only
    NONE = "none"  # No isolation (development)


@dataclass
class ResourceLimits:
    """Container resource limits."""

    memory_limit: str = "512Mi"
    cpu_limit: str = "500m"
    storage_limit: str = "1Gi"
    max_connections: int = 100
    max_concurrent_requests: int = 50

    @classmethod
    def from_plan_type(
        cls, plan_type: str, custom_limits: dict[str, Any] | None = None
    ) -> "ResourceLimits":
        """Create resource limits based on plan type with optional customization."""
        # Default plan configurations
        plan_defaults = {
            "standard": {
                "memory_limit": "512Mi",
                "cpu_limit": "500m",
                "storage_limit": "2Gi",
                "max_connections": 50,
                "max_concurrent_requests": 25,
            },
            "premium": {
                "memory_limit": "1Gi",
                "cpu_limit": "1000m",
                "storage_limit": "5Gi",
                "max_connections": 100,
                "max_concurrent_requests": 50,
            },
            "enterprise": {
                "memory_limit": "2Gi",
                "cpu_limit": "2000m",
                "storage_limit": "10Gi",
                "max_connections": 200,
                "max_concurrent_requests": 100,
            },
        }

        # Get plan defaults
        defaults = plan_defaults.get(plan_type.lower(), plan_defaults["standard"])

        # Apply custom overrides if provided
        if custom_limits:
            defaults.update(custom_limits)

        return cls(**defaults)


@dataclass
class DeploymentContext:
    """Context information for deployment-specific configuration."""

    mode: DeploymentMode
    tenant_id: str | None = None
    isolation_level: IsolationLevel = IsolationLevel.CONTAINER
    resource_limits: ResourceLimits | None = None
    kubernetes_namespace: str | None = None
    container_name: str | None = None

    def __post_init__(self):
        if self.mode == DeploymentMode.TENANT_CONTAINER and not self.tenant_id:
            raise ValueError("tenant_id is required for tenant container deployment")


@dataclass
class RouterConfig:
    """Configuration for router registration."""

    module_path: str
    prefix: str = ""
    auto_discover: bool = False
    required: bool = False
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.auto_discover and not self.tags:
            # Generate tags from prefix
            self.tags = [self.prefix.split("/")[-1]] if self.prefix else ["api"]


@dataclass
class HealthCheckConfig:
    """Health check configuration."""

    enabled_checks: list[str] = field(
        default_factory=lambda: ["database", "cache", "observability"]
    )
    additional_filesystem_paths: list[str] = field(
        default_factory=lambda: ["logs", "uploads", "static"]
    )
    custom_checks: dict[str, Callable] = field(default_factory=dict)


@dataclass
class FeatureConfig:
    """Feature flag configuration."""

    enabled_features: list[str] = field(default_factory=list)
    disabled_features: list[str] = field(default_factory=list)
    plan_based_features: dict[str, list[str]] = field(
        default_factory=lambda: {
            "standard": [
                "customer_portal",
                "technician_portal",
                "billing",
                "notifications",
                "ssl_management",
            ],
            "premium": [
                "customer_portal",
                "technician_portal",
                "billing",
                "notifications",
                "ssl_management",
                "advanced_analytics",
            ],
            "enterprise": [
                "customer_portal",
                "technician_portal",
                "billing",
                "notifications",
                "ssl_management",
                "advanced_analytics",
                "bulk_operations",
                "api_webhooks",
            ],
        }
    )

    def get_features_for_plan(
        self, plan_type: str, tenant_id: str | None = None
    ) -> list[str]:
        """Get enabled features for a specific plan type and tenant."""
        # Start with plan-based features
        features = self.plan_based_features.get(
            plan_type.lower(), self.plan_based_features["standard"]
        ).copy()

        # Add any additional enabled features
        features.extend(self.enabled_features)

        # Remove disabled features
        for disabled in self.disabled_features:
            if disabled in features:
                features.remove(disabled)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(features))

    def is_feature_enabled(
        self, feature: str, plan_type: str, tenant_id: str | None = None
    ) -> bool:
        """Check if a specific feature is enabled."""
        return feature in self.get_features_for_plan(plan_type, tenant_id)


@dataclass
class ObservabilityConfig:
    """Observability configuration."""

    enabled: bool = True
    tier: str = "standard"  # minimal, standard, comprehensive, enterprise
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    logging_level: str = "INFO"
    custom_metrics: list[str] = field(default_factory=list)


@dataclass
class KubernetesConfig:
    """Kubernetes deployment configuration."""

    namespace_pattern: str = "tenant-{tenant_id}"
    container_pattern: str = "isp-framework-{tenant_id}"
    service_pattern: str = "{tenant_id}-service"
    ingress_pattern: str = "{tenant_id}.dotmac.app"

    def get_names(self, tenant_id: str) -> dict[str, str]:
        """Generate Kubernetes resource names for a tenant."""
        # Clean tenant ID for Kubernetes naming
        clean_tenant_id = tenant_id.lower().replace("_", "-").replace(".", "-")

        return {
            "namespace": self.namespace_pattern.format(tenant_id=clean_tenant_id),
            "container": self.container_pattern.format(tenant_id=clean_tenant_id),
            "service": self.service_pattern.format(tenant_id=clean_tenant_id),
            "ingress": self.ingress_pattern.format(tenant_id=clean_tenant_id),
        }


@dataclass
class SecurityConfig:
    """Security configuration."""

    csrf_enabled: bool = True
    cors_enabled: bool = True
    rate_limiting_enabled: bool = True
    api_security_suite: bool = True
    tenant_isolation: bool = True
    ssl_enabled: bool = False


# Provider Protocol Definitions
class SecurityProvider(Protocol):
    """Protocol for security middleware providers."""

    def apply_jwt_authentication(self, app: Any, config: dict[str, Any]) -> None:
        """Apply JWT authentication middleware."""
        ...

    def apply_csrf_protection(self, app: Any, config: dict[str, Any]) -> None:
        """Apply CSRF protection middleware."""
        ...

    def apply_rate_limiting(self, app: Any, config: dict[str, Any]) -> None:
        """Apply rate limiting middleware."""
        ...


class TenantBoundaryProvider(Protocol):
    """Protocol for tenant boundary enforcement providers."""

    def apply_tenant_security(self, app: Any, config: dict[str, Any]) -> None:
        """Apply tenant security middleware."""
        ...

    def apply_tenant_isolation(self, app: Any, config: dict[str, Any]) -> None:
        """Apply tenant isolation middleware."""
        ...


class ObservabilityProvider(Protocol):
    """Protocol for observability providers."""

    def apply_metrics(self, app: Any, config: dict[str, Any]) -> None:
        """Apply metrics collection middleware."""
        ...

    def apply_tracing(self, app: Any, config: dict[str, Any]) -> None:
        """Apply tracing middleware."""
        ...

    def apply_logging(self, app: Any, config: dict[str, Any]) -> None:
        """Apply structured logging middleware."""
        ...


@dataclass
class Providers:
    """Container for middleware providers."""

    security: SecurityProvider | None = None
    tenant: TenantBoundaryProvider | None = None
    observability: ObservabilityProvider | None = None


@dataclass
class PlatformConfig:
    """Main platform configuration."""

    # Basic application info
    platform_name: str
    title: str
    description: str
    version: str = "1.0.0"

    # Deployment context
    deployment_context: DeploymentContext | None = None

    # FastAPI configuration
    fastapi_kwargs: dict[str, Any] = field(default_factory=dict)

    # Router configuration
    routers: list[RouterConfig] = field(default_factory=list)

    # Feature configurations
    health_config: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    observability_config: ObservabilityConfig = field(
        default_factory=ObservabilityConfig
    )
    security_config: SecurityConfig = field(default_factory=SecurityConfig)
    feature_config: FeatureConfig = field(default_factory=FeatureConfig)
    kubernetes_config: KubernetesConfig = field(default_factory=KubernetesConfig)

    # Startup tasks
    startup_tasks: list[str] = field(default_factory=list)
    shutdown_tasks: list[str] = field(default_factory=list)

    # Middleware providers
    middleware_providers: Providers | None = None

    # Custom settings
    custom_settings: dict[str, Any] = field(default_factory=dict)

    def customize_for_deployment(self, context: DeploymentContext) -> "PlatformConfig":
        """Create a deployment-specific configuration."""
        config = self.__class__(**self.__dict__)
        config.deployment_context = context

        # Apply deployment-specific customizations
        if context.mode == DeploymentMode.TENANT_CONTAINER:
            config._apply_tenant_container_customizations()
        elif context.mode == DeploymentMode.MANAGEMENT_PLATFORM:
            config._apply_management_platform_customizations()

        return config

    def _apply_tenant_container_customizations(self):
        """Apply customizations for tenant container deployment."""
        context = self.deployment_context

        # Update FastAPI config for tenant container
        self.fastapi_kwargs.update(
            {
                "docs_url": None,  # Disable docs in tenant containers
                "redoc_url": None,
                "openapi_url": None,
            }
        )

        # Enhanced security for tenant isolation
        self.security_config.tenant_isolation = True
        self.security_config.api_security_suite = True

        # Resource-aware observability
        if context.resource_limits:
            if (
                context.resource_limits.memory_limit.endswith("Mi")
                and int(context.resource_limits.memory_limit[:-2]) < 1024
            ):
                # Reduce observability tier for low-memory containers
                self.observability_config.tier = "minimal"

    def _apply_management_platform_customizations(self):
        """Apply customizations for management platform."""
        # Enhanced observability for platform monitoring
        self.observability_config.tier = "comprehensive"
        self.observability_config.custom_metrics = [
            "tenant_container_count",
            "partner_connection_count",
            "deployment_success_rate",
        ]

        # Management-specific health checks
        self.health_config.enabled_checks.extend(
            ["kubernetes_connectivity", "tenant_containers", "websocket_connections"]
        )


@dataclass
class TenantConfig:
    """Configuration for individual tenant containers."""

    tenant_id: str
    deployment_context: DeploymentContext

    # Tenant-specific isolation settings
    database_config: dict[str, Any] = field(default_factory=dict)
    redis_config: dict[str, Any] = field(default_factory=dict)
    networking_config: dict[str, Any] = field(default_factory=dict)
    storage_config: dict[str, Any] = field(default_factory=dict)

    # Feature flags for tenant
    enabled_features: list[str] = field(default_factory=list)
    disabled_features: list[str] = field(default_factory=list)
    plan_type: str = "standard"  # standard, premium, enterprise

    def __post_init__(self):
        """Initialize tenant-specific configurations."""
        self._setup_database_isolation()
        self._setup_redis_isolation()
        self._setup_networking_isolation()
        self._setup_storage_isolation()

    def _setup_database_isolation(self):
        """Set up database isolation configuration."""
        if not self.database_config:
            self.database_config = {
                "url": f"postgresql://tenant_{self.tenant_id}_user:password@tenant-{self.tenant_id}-db:5432/tenant_{self.tenant_id}",
                "schema": f"tenant_{self.tenant_id}",
                "connection_pool": f"tenant_{self.tenant_id}_pool",
                "max_connections": (
                    self.deployment_context.resource_limits.max_connections
                    if self.deployment_context.resource_limits
                    else 20
                ),
            }

    def _setup_redis_isolation(self):
        """Set up Redis isolation configuration."""
        if not self.redis_config:
            self.redis_config = {
                "url": f"redis://tenant-{self.tenant_id}-redis:6379/0",
                "key_prefix": f"tenant:{self.tenant_id}:",
                "max_connections": 10,
            }

    def _setup_networking_isolation(self):
        """Set up networking isolation configuration."""
        if not self.networking_config:
            self.networking_config = {
                "allowed_hosts": [
                    f"tenant-{self.tenant_id}.dotmac.app",
                    f"tenant-{self.tenant_id}.internal",
                    "localhost",
                ],
                "cors_origins": [
                    f"https://tenant-{self.tenant_id}.dotmac.app",
                    f"https://{self.tenant_id}.portal.dotmac.app",
                ],
                "internal_network": f"tenant-{self.tenant_id}-network",
            }

    def _setup_storage_isolation(self):
        """Set up storage isolation configuration."""
        if not self.storage_config:
            base_path = f"/data/tenant-{self.tenant_id}"
            self.storage_config = {
                "base_path": base_path,
                "uploads_path": f"{base_path}/uploads",
                "logs_path": f"{base_path}/logs",
                "cache_path": f"{base_path}/cache",
                "ssl_path": f"{base_path}/ssl",
            }

    def to_platform_config(self, base_config: PlatformConfig) -> PlatformConfig:
        """Convert tenant config to platform config."""
        config = base_config.customize_for_deployment(self.deployment_context)

        # Apply tenant-specific settings
        config.custom_settings.update(
            {
                "tenant_id": self.tenant_id,
                "database": self.database_config,
                "redis": self.redis_config,
                "networking": self.networking_config,
                "storage": self.storage_config,
                "enabled_features": self.enabled_features,
                "disabled_features": self.disabled_features,
            }
        )

        return config
