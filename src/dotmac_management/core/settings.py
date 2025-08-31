"""
Management Platform Configuration Settings

This module provides specific configuration for the DotMac Management Platform,
extending the shared framework settings.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings

# Import shared settings
from config.shared_settings import SharedSettings


class ManagementPlatformSettings(SharedSettings):
    """Management Platform specific settings that extend shared configuration."""

    # Override defaults for Management Platform
    app_name: str = Field(
        default="DotMac Management Platform", description="Management Platform name"
    )
    app_version: str = Field(default="1.0.0", description="Management Platform version")
    port: int = Field(
        default_factory=lambda: int(os.getenv("PORT", "8002")),
        description="Server port for Management Platform",
    )

    # Management Platform specific settings
    tenant_id: str = Field(
        default="management", description="Management platform tenant ID"
    )

    # Multi-tenant management settings
    max_tenants: int = Field(
        default=1000, description="Maximum tenants that can be managed"
    )
    tenant_isolation_level: str = Field(
        default="strict", description="Tenant isolation level"
    )
    auto_tenant_provisioning: bool = Field(
        default=False, description="Enable automatic tenant provisioning"
    )

    # Billing and subscription management
    enable_billing: bool = Field(default=True, description="Enable billing management")
    billing_cycle: str = Field(default="monthly", description="Default billing cycle")
    trial_period_days: int = Field(
        default=30, description="Default trial period in days"
    )

    # Partner and reseller settings
    enable_reseller_network: bool = Field(
        default=True, description="Enable reseller network"
    )
    max_reseller_depth: int = Field(
        default=3, description="Maximum reseller hierarchy depth"
    )
    reseller_commission_rate: float = Field(
        default=0.10, description="Default reseller commission rate"
    )

    # Deployment and orchestration settings
    enable_kubernetes_orchestration: bool = Field(
        default=True, description="Enable Kubernetes orchestration"
    )
    default_deployment_strategy: str = Field(
        default="rolling", description="Default deployment strategy"
    )
    max_concurrent_deployments: int = Field(
        default=10, description="Maximum concurrent deployments"
    )

    # Monitoring and analytics
    enable_cost_management: bool = Field(
        default=True, description="Enable cost management features"
    )
    enable_saas_monitoring: bool = Field(
        default=True, description="Enable SaaS monitoring"
    )
    analytics_retention_days: int = Field(
        default=365, description="Analytics data retention period"
    )

    # Plugin licensing and management
    enable_plugin_licensing: bool = Field(
        default=True, description="Enable plugin licensing"
    )
    plugin_marketplace_url: str = Field(
        default="https://marketplace.dotmac.io", description="Plugin marketplace URL"
    )

    # Security and compliance
    enforce_ssl: bool = Field(default=True, description="Enforce SSL connections")
    audit_log_retention_days: int = Field(
        default=2555, description="Audit log retention (7 years)"
    )
    compliance_level: str = Field(default="enterprise", description="Compliance level")

    # API rate limiting (Management Platform specific)
    management_api_rate_limit: int = Field(
        default=1000, description="Management API rate limit per hour"
    )
    tenant_api_rate_limit: int = Field(
        default=10000, description="Per-tenant API rate limit per hour"
    )

    # Database settings (Management Platform specific)
    management_database_url: str = Field(
        default_factory=lambda: os.getenv(
            "MANAGEMENT_DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost/dotmac_management",
        ),
        description="Management Platform database connection URL",
    )

    # Message queue settings for tenant operations
    celery_broker_url: str = Field(
        default_factory=lambda: os.getenv(
            "CELERY_BROKER_URL", "redis://localhost:6379/1"
        ),
        description="Celery broker URL for background tasks",
    )
    celery_result_backend: str = Field(
        default_factory=lambda: os.getenv(
            "CELERY_RESULT_BACKEND", "redis://localhost:6379/2"
        ),
        description="Celery result backend URL",
    )

    @field_validator("tenant_isolation_level")
    def validate_isolation_level(cls, v):
        allowed = ["basic", "standard", "strict", "enterprise"]
        if v not in allowed:
            raise ValueError(f"Tenant isolation level must be one of {allowed}")
        return v

    @field_validator("billing_cycle")
    def validate_billing_cycle(cls, v):
        allowed = ["monthly", "quarterly", "yearly"]
        if v not in allowed:
            raise ValueError(f"Billing cycle must be one of {allowed}")
        return v

    @field_validator("default_deployment_strategy")
    def validate_deployment_strategy(cls, v):
        allowed = ["rolling", "blue_green", "canary", "recreate"]
        if v not in allowed:
            raise ValueError(f"Deployment strategy must be one of {allowed}")
        return v

    @field_validator("compliance_level")
    def validate_compliance_level(cls, v):
        allowed = ["basic", "standard", "enterprise", "government"]
        if v not in allowed:
            raise ValueError(f"Compliance level must be one of {allowed}")
        return v

    model_config = ConfigDict()
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> ManagementPlatformSettings:
    """Get cached Management Platform settings instance."""
    return ManagementPlatformSettings()
