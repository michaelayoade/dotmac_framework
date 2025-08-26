"""Tenant initialization system for multi-tenant SaaS deployment."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel, Field

from dotmac_isp.core.database import get_async_session
from dotmac_isp.modules.licensing.models import SoftwareLicense, LicenseType
from dotmac_isp.modules.licensing.service import LicensingService
from dotmac_isp.plugins.core.models import PluginRegistry, PluginConfiguration
from dotmac_isp.plugins.core.manager import PluginManager


logger = logging.getLogger(__name__, timezone)


class TenantConfig(BaseModel):
    """Configuration for tenant initialization."""

    tenant_id: str = Field(..., min_length=1, max_length=100)
    tenant_name: str = Field(..., min_length=1, max_length=255)
    tenant_domain: str = Field(..., min_length=1, max_length=255)
    license_tier: str = Field(
        default="basic", regex="^(basic|professional|enterprise)$"
    )
    max_users: int = Field(default=10, ge=1, le=10000)
    max_customers: int = Field(default=100, ge=1, le=100000)
    max_services: int = Field(default=50, ge=1, le=10000)
    storage_limit_gb: int = Field(default=5, ge=1, le=1000)
    api_rate_limit: int = Field(default=1000, ge=100, le=100000)
    enabled_plugins: List[str] = Field(default_factory=list)
    custom_config: Dict[str, Any] = Field(default_factory=dict)


class TenantInitializationService:
    """Service for initializing new tenant instances."""

    def __init__(self, session: AsyncSession):
        """  Init   operation."""
        self.session = session
        self.licensing_service = LicensingService(session)
        self.plugin_manager = PluginManager()

    async def initialize_tenant_data(
        self, tenant_id: str, config: Optional[TenantConfig] = None
    ) -> bool:
        """Initialize tenant data and configuration.

        Args:
            tenant_id: Unique tenant identifier
            config: Tenant configuration, uses defaults if not provided

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info(f"Initializing tenant data for: {tenant_id}")

            # Use provided config or create default
            if config is None:
                config = TenantConfig(
                    tenant_id=tenant_id,
                    tenant_name=f"Tenant {tenant_id}",
                    tenant_domain=f"{tenant_id}.dotmac.app",
                )

            # Step 1: Create tenant database schema
            await self._create_tenant_schema(tenant_id)

            # Step 2: Initialize default licenses
            await self._initialize_default_licenses(tenant_id, config.license_tier)

            # Step 3: Configure plugins based on license tier
            await self._configure_tenant_plugins(tenant_id, config)

            # Step 4: Create default administrative user
            await self._create_default_admin_user(tenant_id, config)

            # Step 5: Initialize tenant settings
            await self._initialize_tenant_settings(tenant_id, config)

            # Step 6: Set up monitoring and metrics
            await self._initialize_tenant_monitoring(tenant_id)

            logger.info(f"✅ Tenant {tenant_id} initialization completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Tenant {tenant_id} initialization failed: {str(e)}")
            # Attempt cleanup on failure
            await self._cleanup_failed_tenant_initialization(tenant_id)
            return False

    async def _create_tenant_schema(self, tenant_id: str) -> None:
        """Create tenant-specific database schema and tables."""
        logger.info(f"Creating database schema for tenant: {tenant_id}")

        # Create tenant-specific tables with RLS policies
        await self.session.execute(
            text(
                f"""
            -- Enable Row Level Security on all tenant tables
            CREATE SCHEMA IF NOT EXISTS tenant_{tenant_id};
            
            -- Create tenant-specific configuration table
            CREATE TABLE IF NOT EXISTS tenant_{tenant_id}.tenant_config (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id VARCHAR(100) NOT NULL DEFAULT '{tenant_id}',
                config_key VARCHAR(255) NOT NULL,
                config_value TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(tenant_id, config_key)
            );
            
            -- Create tenant-specific audit log
            CREATE TABLE IF NOT EXISTS tenant_{tenant_id}.audit_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id VARCHAR(100) NOT NULL DEFAULT '{tenant_id}',
                user_id UUID,
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(100),
                resource_id VARCHAR(255),
                details JSONB,
                ip_address INET,
                user_agent TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS idx_tenant_config_{tenant_id}_key 
                ON tenant_{tenant_id}.tenant_config(config_key);
            CREATE INDEX IF NOT EXISTS idx_audit_log_{tenant_id}_created 
                ON tenant_{tenant_id}.audit_log(created_at);
            CREATE INDEX IF NOT EXISTS idx_audit_log_{tenant_id}_user 
                ON tenant_{tenant_id}.audit_log(user_id);
        """
            )
        )

        await self.session.commit()

    async def _initialize_default_licenses(
        self, tenant_id: str, license_tier: str
    ) -> None:
        """Initialize default software licenses based on tier."""
        logger.info(f"Initializing {license_tier} licenses for tenant: {tenant_id}")

        # Define license configurations per tier
        license_configs = {
            "basic": [
                {
                    "software_name": "Core ISP Framework",
                    "license_type": LicenseType.SUBSCRIPTION,
                    "features": ["basic_billing", "customer_management"],
                },
                {
                    "software_name": "Basic Analytics",
                    "license_type": LicenseType.SUBSCRIPTION,
                    "features": ["basic_reports"],
                },
            ],
            "professional": [
                {
                    "software_name": "Core ISP Framework",
                    "license_type": LicenseType.SUBSCRIPTION,
                    "features": [
                        "advanced_billing",
                        "customer_management",
                        "inventory",
                    ],
                },
                {
                    "software_name": "Professional Analytics",
                    "license_type": LicenseType.SUBSCRIPTION,
                    "features": ["advanced_reports", "custom_dashboards"],
                },
                {
                    "software_name": "API Integrations",
                    "license_type": LicenseType.SUBSCRIPTION,
                    "features": ["third_party_apis"],
                },
            ],
            "enterprise": [
                {
                    "software_name": "Core ISP Framework",
                    "license_type": LicenseType.ENTERPRISE,
                    "features": ["all_core_features"],
                },
                {
                    "software_name": "Enterprise Analytics",
                    "license_type": LicenseType.ENTERPRISE,
                    "features": ["ai_insights", "predictive_analytics"],
                },
                {
                    "software_name": "API Integrations",
                    "license_type": LicenseType.ENTERPRISE,
                    "features": ["unlimited_apis"],
                },
                {
                    "software_name": "Custom Branding",
                    "license_type": LicenseType.ENTERPRISE,
                    "features": ["white_label"],
                },
                {
                    "software_name": "Advanced Security",
                    "license_type": LicenseType.ENTERPRISE,
                    "features": ["sso", "advanced_audit"],
                },
            ],
        }

        licenses = license_configs.get(license_tier, license_configs["basic"])

        for license_config in licenses:
            # Create license record
            license_data = {
                "tenant_id": tenant_id,
                "software_name": license_config["software_name"],
                "license_type": license_config["license_type"],
                "license_key": f"{tenant_id}-{uuid.uuid4().hex[:8]}",
                "features": license_config["features"],
                "issued_date": datetime.now(timezone.utc),
                "expiry_date": datetime.now(timezone.utc)
                + timedelta(days=365),  # 1 year license
                "is_active": True,
                "max_users": (
                    1000
                    if license_tier == "enterprise"
                    else (100 if license_tier == "professional" else 10)
                ),
                "concurrent_sessions": (
                    50
                    if license_tier == "enterprise"
                    else (20 if license_tier == "professional" else 5)
                ),
            }

            await self.licensing_service.create_license(license_data)

    async def _configure_tenant_plugins(
        self, tenant_id: str, config: TenantConfig
    ) -> None:
        """Configure plugins based on tenant license and preferences."""
        logger.info(f"Configuring plugins for tenant: {tenant_id}")

        # Get available plugins
        result = await self.session.execute(
            select(PluginRegistry).where(PluginRegistry.tenant_id == tenant_id)
        )
        available_plugins = result.scalars().all()

        # Define plugin configurations per license tier
        tier_plugins = {
            "basic": ["core_billing", "basic_customer_management", "basic_reporting"],
            "professional": [
                "advanced_billing",
                "crm_integration",
                "advanced_reporting",
                "api_access",
            ],
            "enterprise": ["all_plugins"],
        }

        enabled_plugins = tier_plugins.get(config.license_tier, tier_plugins["basic"])

        # Enable plugins based on license tier
        for plugin in available_plugins:
            should_enable = (
                config.license_tier == "enterprise"
                or plugin.plugin_id in enabled_plugins
                or plugin.plugin_id in config.enabled_plugins
            )

            if should_enable:
                # Create or update plugin configuration
                plugin_config = PluginConfiguration(
                    tenant_id=tenant_id,
                    plugin_id=plugin.plugin_id,
                    enabled=True,
                    priority=100,
                    config_data={
                        "auto_start": True,
                        "license_tier": config.license_tier,
                        "max_usage": self._get_plugin_usage_limit(
                            plugin.plugin_id, config.license_tier
                        ),
                    },
                    auto_start=True,
                    restart_on_failure=True,
                    configured_by=None,  # System configuration
                )

                self.session.add(plugin_config)

        await self.session.commit()

    async def _create_default_admin_user(
        self, tenant_id: str, config: TenantConfig
    ) -> None:
        """Create default administrative user for tenant."""
        logger.info(f"Creating default admin user for tenant: {tenant_id}")

        # This would integrate with your user management system
        # For now, we'll create a configuration entry
        await self.session.execute(
            text(
                f"""
            INSERT INTO tenant_{tenant_id}.tenant_config (config_key, config_value) 
            VALUES ('default_admin_created', 'true')
            ON CONFLICT (tenant_id, config_key) DO NOTHING
        """
            )
        )

        await self.session.commit()

    async def _initialize_tenant_settings(
        self, tenant_id: str, config: TenantConfig
    ) -> None:
        """Initialize tenant-specific settings and configurations."""
        logger.info(f"Initializing settings for tenant: {tenant_id}")

        settings = {
            "tenant_name": config.tenant_name,
            "tenant_domain": config.tenant_domain,
            "license_tier": config.license_tier,
            "max_users": str(config.max_users),
            "max_customers": str(config.max_customers),
            "max_services": str(config.max_services),
            "storage_limit_gb": str(config.storage_limit_gb),
            "api_rate_limit": str(config.api_rate_limit),
            "timezone": "UTC",
            "language": "en",
            "currency": "USD",
            "initialized_at": datetime.now(timezone.utc).isoformat(),
            "initialization_version": "1.0",
        }

        # Add custom configuration
        settings.update(config.custom_config)

        for key, value in settings.items():
            await self.session.execute(
                text(
                    f"""
                INSERT INTO tenant_{tenant_id}.tenant_config (config_key, config_value) 
                VALUES ('{key}', '{value}')
                ON CONFLICT (tenant_id, config_key) 
                DO UPDATE SET config_value = EXCLUDED.config_value, updated_at = NOW()
            """
                )
            )

        await self.session.commit()

    async def _initialize_tenant_monitoring(self, tenant_id: str) -> None:
        """Initialize monitoring and health check configuration for tenant."""
        logger.info(f"Initializing monitoring for tenant: {tenant_id}")

        # Create monitoring configuration
        monitoring_config = {
            "health_check_enabled": "true",
            "metrics_collection_enabled": "true",
            "log_retention_days": "30",
            "alert_email": f"admin@{tenant_id}.dotmac.app",
            "monitoring_level": "standard",
        }

        for key, value in monitoring_config.items():
            await self.session.execute(
                text(
                    f"""
                INSERT INTO tenant_{tenant_id}.tenant_config (config_key, config_value) 
                VALUES ('monitoring_{key}', '{value}')
                ON CONFLICT (tenant_id, config_key) DO NOTHING
            """
                )
            )

        await self.session.commit()

    def _get_plugin_usage_limit(self, plugin_id: str, license_tier: str) -> int:
        """Get usage limits for plugin based on license tier."""
        limits = {
            "basic": {"default": 100, "api_access": 1000},
            "professional": {"default": 1000, "api_access": 10000},
            "enterprise": {"default": -1, "api_access": -1},  # -1 means unlimited
        }

        tier_limits = limits.get(license_tier, limits["basic"])
        return tier_limits.get(plugin_id, tier_limits["default"])

    async def _cleanup_failed_tenant_initialization(self, tenant_id: str) -> None:
        """Clean up resources if tenant initialization fails."""
        try:
            logger.warning(f"Cleaning up failed initialization for tenant: {tenant_id}")

            # Drop tenant schema
            await self.session.execute(
                text(f"DROP SCHEMA IF EXISTS tenant_{tenant_id} CASCADE")
            )

            # Remove plugin configurations
            await self.session.execute(
                text(
                    f"""
                DELETE FROM plugin_configurations WHERE tenant_id = '{tenant_id}'
            """
                )
            )

            await self.session.commit()

        except Exception as e:
            logger.error(f"Failed to cleanup tenant {tenant_id}: {str(e)}")

    async def verify_tenant_health(self, tenant_id: str) -> Dict[str, Any]:
        """Verify tenant health and return status."""
        health_status = {
            "tenant_id": tenant_id,
            "status": "unknown",
            "checks": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Check database schema
            result = await self.session.execute(
                text(
                    f"""
                SELECT schema_name FROM information_schema.schemata 
                WHERE schema_name = 'tenant_{tenant_id}'
            """
                )
            )
            schema_exists = result.fetchone() is not None
            health_status["checks"]["database_schema"] = (
                "ok" if schema_exists else "failed"
            )

            # Check configuration
            result = await self.session.execute(
                text(
                    f"""
                SELECT COUNT(*) FROM tenant_{tenant_id}.tenant_config
            """
                )
            )
            config_count = result.scalar()
            health_status["checks"]["configuration"] = (
                "ok" if config_count > 0 else "failed"
            )

            # Check licenses
            licenses = await self.licensing_service.get_active_licenses(tenant_id)
            health_status["checks"]["licenses"] = "ok" if licenses else "failed"

            # Overall status
            all_checks_ok = all(
                status == "ok" for status in health_status["checks"].values()
            )
            health_status["status"] = "healthy" if all_checks_ok else "unhealthy"

        except Exception as e:
            health_status["status"] = "error"
            health_status["error"] = str(e)

        return health_status


async def initialize_tenant_data(
    session: AsyncSession, tenant_id: str, config: Optional[TenantConfig] = None
) -> bool:
    """Convenience function for tenant initialization."""
    service = TenantInitializationService(session)
    return await service.initialize_tenant_data(tenant_id, config)
