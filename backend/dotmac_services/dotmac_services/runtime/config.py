"""
Runtime configuration for dotmac_services.
"""

import os

from pydantic import BaseModel, Field


class ServiceCatalogConfig(BaseModel):
    """Service catalog configuration."""

    currency: str = Field("USD", description="Default currency")
    versioning: bool = Field(True, description="Enable catalog versioning")
    enable_addons: bool = Field(True, description="Enable service add-ons")


class ServiceManagementConfig(BaseModel):
    """Service management configuration."""

    provisioning_timeout: int = Field(300, description="Provisioning timeout in seconds")
    auto_activation: bool = Field(True, description="Auto-activate services after provisioning")
    max_retries: int = Field(3, description="Max provisioning retries")


class TariffConfig(BaseModel):
    """Tariff configuration."""

    currency: str = Field("USD", description="Default currency")
    dynamic_pricing: bool = Field(False, description="Enable dynamic pricing")
    discounts: bool = Field(True, description="Enable discount processing")


class EventsConfig(BaseModel):
    """Events configuration."""

    enabled: bool = Field(True, description="Enable event publishing")
    broker_url: str = Field("redis://localhost:6379", description="Event broker URL")


class DatabaseConfig(BaseModel):
    """Database configuration."""

    host: str = Field("localhost", description="Database host")
    port: int = Field(5432, description="Database port")
    name: str = Field("dotmac_services", description="Database name")
    user: str = Field("dotmac", description="Database user")
    password: str = Field("secret", description="Database password")


class CacheConfig(BaseModel):
    """Cache configuration."""

    type: str = Field("redis", description="Cache type")
    host: str = Field("localhost", description="Cache host")
    port: int = Field(6379, description="Cache port")


class RuntimeConfig(BaseModel):
    """Complete runtime configuration for services."""

    environment: str = Field("development", description="Runtime environment")
    debug: bool = Field(False, description="Debug mode")

    service_catalog: ServiceCatalogConfig
    service_management: ServiceManagementConfig
    tariff: TariffConfig
    events: EventsConfig
    database: DatabaseConfig
    cache: CacheConfig


def load_config() -> RuntimeConfig:
    """Load configuration from environment variables."""

    catalog_config = ServiceCatalogConfig(
        currency=os.getenv("DOTMAC_CATALOG_CURRENCY", "USD"),
        versioning=os.getenv("DOTMAC_CATALOG_VERSIONING", "true").lower() == "true",
        enable_addons=os.getenv("DOTMAC_CATALOG_ENABLE_ADDONS", "true").lower() == "true"
    )

    management_config = ServiceManagementConfig(
        provisioning_timeout=int(os.getenv("DOTMAC_SVC_PROVISIONING_TIMEOUT", "300")),
        auto_activation=os.getenv("DOTMAC_SVC_AUTO_ACTIVATION", "true").lower() == "true",
        max_retries=int(os.getenv("DOTMAC_SVC_MAX_RETRIES", "3"))
    )

    tariff_config = TariffConfig(
        currency=os.getenv("DOTMAC_TARIFF_CURRENCY", "USD"),
        dynamic_pricing=os.getenv("DOTMAC_TARIFF_DYNAMIC_PRICING", "false").lower() == "true",
        discounts=os.getenv("DOTMAC_TARIFF_DISCOUNTS", "true").lower() == "true"
    )

    events_config = EventsConfig(
        enabled=os.getenv("DOTMAC_EVENTS_ENABLED", "true").lower() == "true",
        broker_url=os.getenv("DOTMAC_EVENTS_BROKER_URL", "redis://localhost:6379")
    )

    database_config = DatabaseConfig(
        host=os.getenv("DOTMAC_DB_HOST", "localhost"),
        port=int(os.getenv("DOTMAC_DB_PORT", "5432")),
        name=os.getenv("DOTMAC_DB_NAME", "dotmac_services"),
        user=os.getenv("DOTMAC_DB_USER", "dotmac"),
        password=os.getenv("DOTMAC_DB_PASSWORD", "secret")
    )

    cache_config = CacheConfig(
        type=os.getenv("DOTMAC_CACHE_TYPE", "redis"),
        host=os.getenv("DOTMAC_CACHE_HOST", "localhost"),
        port=int(os.getenv("DOTMAC_CACHE_PORT", "6379"))
    )

    return RuntimeConfig(
        environment=os.getenv("ENVIRONMENT", "development"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        service_catalog=catalog_config,
        service_management=management_config,
        tariff=tariff_config,
        events=events_config,
        database=database_config,
        cache=cache_config
    )
