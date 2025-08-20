"""
Configuration management for dotmac_services.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = field(default_factory=lambda: os.getenv("DOTMAC_DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("DOTMAC_DB_PORT", "5432")))
    name: str = field(default_factory=lambda: os.getenv("DOTMAC_DB_NAME", "dotmac_services"))
    user: str = field(default_factory=lambda: os.getenv("DOTMAC_DB_USER", "dotmac"))
    password: str = field(default_factory=lambda: os.getenv("DOTMAC_DB_PASSWORD", ""))
    ssl_mode: str = field(default_factory=lambda: os.getenv("DOTMAC_DB_SSL_MODE", "prefer"))
    pool_size: int = field(default_factory=lambda: int(os.getenv("DOTMAC_DB_POOL_SIZE", "10")))
    max_overflow: int = field(default_factory=lambda: int(os.getenv("DOTMAC_DB_MAX_OVERFLOW", "20")))


@dataclass
class CacheConfig:
    """Cache configuration."""
    type: str = field(default_factory=lambda: os.getenv("DOTMAC_CACHE_TYPE", "redis"))
    host: str = field(default_factory=lambda: os.getenv("DOTMAC_CACHE_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("DOTMAC_CACHE_PORT", "6379")))
    db: int = field(default_factory=lambda: int(os.getenv("DOTMAC_CACHE_DB", "0")))
    password: str = field(default_factory=lambda: os.getenv("DOTMAC_CACHE_PASSWORD", ""))
    ttl_seconds: int = field(default_factory=lambda: int(os.getenv("DOTMAC_CACHE_TTL", "3600")))


@dataclass
class ServiceCatalogConfig:
    """Service catalog configuration."""
    default_currency: str = field(default_factory=lambda: os.getenv("DOTMAC_CATALOG_CURRENCY", "USD"))
    enable_versioning: bool = field(default_factory=lambda: os.getenv("DOTMAC_CATALOG_VERSIONING", "true").lower() == "true")
    auto_publish: bool = field(default_factory=lambda: os.getenv("DOTMAC_CATALOG_AUTO_PUBLISH", "false").lower() == "true")
    max_bundle_depth: int = field(default_factory=lambda: int(os.getenv("DOTMAC_CATALOG_MAX_BUNDLE_DEPTH", "5")))
    enable_addons: bool = field(default_factory=lambda: os.getenv("DOTMAC_CATALOG_ENABLE_ADDONS", "true").lower() == "true")


@dataclass
class ServiceManagementConfig:
    """Service management configuration."""
    default_provisioning_timeout: int = field(default_factory=lambda: int(os.getenv("DOTMAC_SVC_PROVISIONING_TIMEOUT", "300")))
    enable_auto_activation: bool = field(default_factory=lambda: os.getenv("DOTMAC_SVC_AUTO_ACTIVATION", "true").lower() == "true")
    suspension_grace_period: int = field(default_factory=lambda: int(os.getenv("DOTMAC_SVC_SUSPENSION_GRACE", "86400")))
    termination_retention_days: int = field(default_factory=lambda: int(os.getenv("DOTMAC_SVC_TERMINATION_RETENTION", "30")))
    enable_state_callbacks: bool = field(default_factory=lambda: os.getenv("DOTMAC_SVC_STATE_CALLBACKS", "true").lower() == "true")
    max_retry_attempts: int = field(default_factory=lambda: int(os.getenv("DOTMAC_SVC_MAX_RETRIES", "3")))


@dataclass
class TariffConfig:
    """Tariff and pricing configuration."""
    default_currency: str = field(default_factory=lambda: os.getenv("DOTMAC_TARIFF_CURRENCY", "USD"))
    enable_dynamic_pricing: bool = field(default_factory=lambda: os.getenv("DOTMAC_TARIFF_DYNAMIC_PRICING", "false").lower() == "true")
    price_precision: int = field(default_factory=lambda: int(os.getenv("DOTMAC_TARIFF_PRECISION", "4")))
    enable_discounts: bool = field(default_factory=lambda: os.getenv("DOTMAC_TARIFF_DISCOUNTS", "true").lower() == "true")
    enable_promotions: bool = field(default_factory=lambda: os.getenv("DOTMAC_TARIFF_PROMOTIONS", "true").lower() == "true")
    tax_calculation: str = field(default_factory=lambda: os.getenv("DOTMAC_TARIFF_TAX_CALC", "inclusive"))  # inclusive, exclusive, none


@dataclass
class ProvisioningConfig:
    """Provisioning bindings configuration."""
    enable_resource_validation: bool = field(default_factory=lambda: os.getenv("DOTMAC_PROV_VALIDATE_RESOURCES", "true").lower() == "true")
    enable_dependency_checking: bool = field(default_factory=lambda: os.getenv("DOTMAC_PROV_CHECK_DEPS", "true").lower() == "true")
    parallel_provisioning: bool = field(default_factory=lambda: os.getenv("DOTMAC_PROV_PARALLEL", "true").lower() == "true")
    max_concurrent_provisions: int = field(default_factory=lambda: int(os.getenv("DOTMAC_PROV_MAX_CONCURRENT", "10")))
    resource_timeout: int = field(default_factory=lambda: int(os.getenv("DOTMAC_PROV_RESOURCE_TIMEOUT", "60")))
    enable_rollback: bool = field(default_factory=lambda: os.getenv("DOTMAC_PROV_ENABLE_ROLLBACK", "true").lower() == "true")


@dataclass
class EventConfig:
    """Event publishing configuration."""
    enable_events: bool = field(default_factory=lambda: os.getenv("DOTMAC_EVENTS_ENABLED", "true").lower() == "true")
    event_broker_url: str = field(default_factory=lambda: os.getenv("DOTMAC_EVENTS_BROKER_URL", "redis://localhost:6379"))
    event_retention_hours: int = field(default_factory=lambda: int(os.getenv("DOTMAC_EVENTS_RETENTION", "168")))
    batch_size: int = field(default_factory=lambda: int(os.getenv("DOTMAC_EVENTS_BATCH_SIZE", "100")))
    flush_interval: int = field(default_factory=lambda: int(os.getenv("DOTMAC_EVENTS_FLUSH_INTERVAL", "5")))

    # Event topics
    service_activation_requested: str = "svc.activation.requested.v1"
    service_activated: str = "svc.activation.activated.v1"
    service_suspended: str = "svc.activation.suspended.v1"
    service_resumed: str = "svc.activation.resumed.v1"
    service_changed: str = "svc.activation.changed.v1"
    policy_intent_updated: str = "policy.intent.updated.v1"


@dataclass
class IntegrationConfig:
    """External integration configuration."""
    # Billing system
    billing_api_url: str = field(default_factory=lambda: os.getenv("DOTMAC_BILLING_API_URL", ""))
    billing_api_key: str = field(default_factory=lambda: os.getenv("DOTMAC_BILLING_API_KEY", ""))

    # CRM system
    crm_api_url: str = field(default_factory=lambda: os.getenv("DOTMAC_CRM_API_URL", ""))
    crm_api_key: str = field(default_factory=lambda: os.getenv("DOTMAC_CRM_API_KEY", ""))

    # Inventory system
    inventory_api_url: str = field(default_factory=lambda: os.getenv("DOTMAC_INVENTORY_API_URL", ""))
    inventory_api_key: str = field(default_factory=lambda: os.getenv("DOTMAC_INVENTORY_API_KEY", ""))

    # Network provisioning
    network_api_url: str = field(default_factory=lambda: os.getenv("DOTMAC_NETWORK_API_URL", ""))
    network_api_key: str = field(default_factory=lambda: os.getenv("DOTMAC_NETWORK_API_KEY", ""))


@dataclass
class ServicesConfig:
    """Main services configuration."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    service_catalog: ServiceCatalogConfig = field(default_factory=ServiceCatalogConfig)
    service_management: ServiceManagementConfig = field(default_factory=ServiceManagementConfig)
    tariff: TariffConfig = field(default_factory=TariffConfig)
    provisioning: ProvisioningConfig = field(default_factory=ProvisioningConfig)
    events: EventConfig = field(default_factory=EventConfig)
    integrations: IntegrationConfig = field(default_factory=IntegrationConfig)

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Database validation
        if not self.database.host:
            errors.append("Database host is required")
        if not self.database.name:
            errors.append("Database name is required")

        # Cache validation
        if self.cache.type not in ["redis", "memory"]:
            errors.append("Cache type must be 'redis' or 'memory'")

        # Service catalog validation
        if self.service_catalog.max_bundle_depth < 1:
            errors.append("Max bundle depth must be at least 1")

        # Tariff validation
        if self.tariff.price_precision < 0 or self.tariff.price_precision > 10:
            errors.append("Price precision must be between 0 and 10")

        if self.tariff.tax_calculation not in ["inclusive", "exclusive", "none"]:
            errors.append("Tax calculation must be 'inclusive', 'exclusive', or 'none'")

        # Provisioning validation
        if self.provisioning.max_concurrent_provisions < 1:
            errors.append("Max concurrent provisions must be at least 1")

        return errors


# Global configuration instance
_config: Optional[ServicesConfig] = None


def get_config() -> ServicesConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = ServicesConfig()

        # Validate configuration
        errors = _config.validate()
        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

    return _config


def reset_config():
    """Reset global configuration (mainly for testing)."""
    global _config
    _config = None
