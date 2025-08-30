"""
Plugin Service - Business Logic Layer

Implements plugin management business logic following DRY patterns.
Integrates with existing repository, licensing, and security systems.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.auth.core.permissions import PluginPermissions
from dotmac_shared.monitoring import get_monitoring
from dotmac_shared.plugins.core.exceptions import PluginError, PluginNotFoundError
from dotmac_shared.plugins.core.manager import PluginManager

from ..core.exceptions import BusinessLogicError, ValidationError
from ..core.logging import get_logger
from ..dependencies import get_db_session
from ..models.plugin import (
    LicenseStatus,
    LicenseTier,
    Plugin,
    PluginLicense,
    PluginUsage,
)
from ..repositories.plugin import PluginLicenseRepository, PluginRepository
from ..repositories.plugin_additional import PluginUsageRepository
from ..schemas.plugin import PluginUsageResponse

logger = get_logger(__name__)


class PluginService:
    """
    Plugin management service following DRY service patterns.

    Handles plugin lifecycle, licensing, and integration with the plugin system.
    """

    def __init__(
        self, db: AsyncSession, plugin_manager: PluginManager, monitoring_service=None
    ):
        self.db = db
        self.plugin_manager = plugin_manager
        self.monitoring = monitoring_service or get_monitoring()

        # Repository instances following DRY dependency injection
        self.plugin_repo = PluginRepository(db)
        self.license_repo = PluginLicenseRepository(db)
        self.usage_repo = PluginUsageRepository(db)

    # ============================================================================
    # Plugin Catalog Management
    # ============================================================================

    async def get_catalog(
        self,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        featured_only: bool = False,
        free_only: bool = False,
        tenant_id: Optional[UUID] = None,
    ) -> List[Plugin]:
        """
        Get plugin catalog with filtering.
        Uses DRY repository patterns and caching.
        """
        logger.info(
            f"Fetching plugin catalog with filters: category={category}, search={search_query}"
        )

        try:
            # Build filter conditions using DRY query patterns
            filters = {}

            if category:
                filters["category__slug"] = category

            if featured_only:
                filters["is_featured"] = True

            if free_only:
                filters["free_tier_available"] = True

            # Get plugins from repository
            plugins = await self.plugin_repo.find_all(**filters)

            # Apply search filtering if needed
            if search_query:
                plugins = [
                    plugin
                    for plugin in plugins
                    if (
                        search_query.lower() in plugin.name.lower()
                        or search_query.lower() in plugin.short_description.lower()
                    )
                ]

            # Filter by tenant accessibility if specified
            if tenant_id:
                plugins = await self._filter_plugins_for_tenant(plugins, tenant_id)

            logger.info(f"Retrieved {len(plugins)} plugins from catalog")
            return plugins

        except Exception as e:
            logger.error(f"Error fetching plugin catalog: {e}")
            raise BusinessLogicError(f"Failed to fetch plugin catalog: {str(e)}") from e

    async def get_plugin(self, plugin_id: UUID) -> Optional[Plugin]:
        """
        Get plugin by ID using DRY repository patterns.
        """
        try:
            plugin = await self.plugin_repo.get_by_id(plugin_id)
            return plugin

        except Exception as e:
            logger.error(f"Error fetching plugin {plugin_id}: {e}")
            raise BusinessLogicError(f"Failed to fetch plugin: {str(e)}") from e

    # ============================================================================
    # Plugin Installation Management
    # ============================================================================

    async def install_plugin(
        self,
        tenant_id: UUID,
        plugin_id: UUID,
        license_tier: LicenseTier,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> PluginLicense:
        """
        Install plugin for tenant following DRY transaction patterns.
        """
        logger.info(f"Installing plugin {plugin_id} for tenant {tenant_id}")

        try:
            # Begin transaction following DRY patterns
            async with self.db.begin():
                # Validate plugin exists
                plugin = await self.get_plugin(plugin_id)
                if not plugin:
                    raise ValidationError(f"Plugin {plugin_id} not found")

                # Validate license tier is available
                if not self._is_license_tier_available(plugin, license_tier):
                    raise ValidationError(
                        f"License tier {license_tier} not available for plugin"
                    )

                # Check for existing installation
                existing_license = await self.get_tenant_plugin_license(
                    tenant_id, plugin_id
                )
                if existing_license and existing_license.is_active:
                    raise ValidationError("Plugin is already installed for this tenant")

                # Validate dependencies
                await self._validate_plugin_dependencies(plugin, tenant_id)

                # Create plugin license
                license_data = {
                    "tenant_id": tenant_id,
                    "plugin_id": plugin_id,
                    "license_tier": license_tier,
                    "status": LicenseStatus.TRIAL,
                    "configuration": configuration or {},
                    "activated_at": datetime.now(timezone.utc),
                }

                # Set trial and expiry dates based on tier
                if license_tier == LicenseTier.FREE:
                    license_data["status"] = LicenseStatus.ACTIVE
                else:
                    from datetime import timedelta

                    license_data["trial_ends_at"] = datetime.now(
                        timezone.utc
                    ) + timedelta(days=plugin.trial_days)

                plugin_license = await self.license_repo.create(license_data)

                # Record installation event
                await self._record_plugin_event(
                    tenant_id=tenant_id,
                    plugin_id=plugin_id,
                    event_type="plugin_installed",
                    metadata={"license_tier": license_tier.value},
                )

                # Update plugin installation count
                plugin.active_installations += 1
                await self.plugin_repo.update(
                    plugin.id, {"active_installations": plugin.active_installations}
                )

                logger.info(f"Plugin installed: license_id={plugin_license.id}")
                return plugin_license

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Plugin installation failed: {e}")
            raise BusinessLogicError(f"Plugin installation failed: {str(e)}") from e

    async def update_plugin_installation(
        self,
        installation_id: UUID,
        version: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        license_tier: Optional[LicenseTier] = None,
    ) -> PluginLicense:
        """
        Update plugin installation following DRY update patterns.
        """
        logger.info(f"Updating plugin installation {installation_id}")

        try:
            async with self.db.begin():
                # Get existing installation
                installation = await self.license_repo.get_by_id(installation_id)
                if not installation:
                    raise ValidationError(
                        f"Plugin installation {installation_id} not found"
                    )

                # Prepare update data
                update_data = {}

                if configuration is not None:
                    update_data["configuration"] = configuration

                if license_tier and license_tier != installation.license_tier:
                    # Validate tier change is allowed
                    plugin = await self.get_plugin(installation.plugin_id)
                    if not self._is_license_tier_available(plugin, license_tier):
                        raise ValidationError(
                            f"License tier {license_tier} not available"
                        )

                    update_data["license_tier"] = license_tier

                if version:
                    # Version updates would require additional validation
                    update_data["version"] = version

                # Update installation
                updated_installation = await self.license_repo.update(
                    installation_id, update_data
                )

                # Record update event
                await self._record_plugin_event(
                    tenant_id=installation.tenant_id,
                    plugin_id=installation.plugin_id,
                    event_type="plugin_updated",
                    metadata=update_data,
                )

                logger.info(f"Plugin installation updated: {installation_id}")
                return updated_installation

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Plugin update failed: {e}")
            raise BusinessLogicError(f"Plugin update failed: {str(e)}") from e

    async def uninstall_plugin(self, installation_id: UUID) -> bool:
        """
        Uninstall plugin following DRY cleanup patterns.
        """
        logger.info(f"Uninstalling plugin installation {installation_id}")

        try:
            async with self.db.begin():
                # Get installation
                installation = await self.license_repo.get_by_id(installation_id)
                if not installation:
                    raise ValidationError(
                        f"Plugin installation {installation_id} not found"
                    )

                # Mark license as cancelled
                await self.license_repo.update(
                    installation_id,
                    {
                        "status": LicenseStatus.CANCELLED,
                        "expires_at": datetime.now(timezone.utc),
                    },
                )

                # Update plugin installation count
                plugin = await self.get_plugin(installation.plugin_id)
                if plugin and plugin.active_installations > 0:
                    plugin.active_installations -= 1
                    await self.plugin_repo.update(
                        plugin.id, {"active_installations": plugin.active_installations}
                    )

                # Record uninstall event
                await self._record_plugin_event(
                    tenant_id=installation.tenant_id,
                    plugin_id=installation.plugin_id,
                    event_type="plugin_uninstalled",
                    metadata={"installation_id": str(installation_id)},
                )

                logger.info(f"Plugin uninstalled: {installation_id}")
                return True

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Plugin uninstall failed: {e}")
            raise BusinessLogicError(f"Plugin uninstall failed: {str(e)}") from e

    # ============================================================================
    # License and Installation Management
    # ============================================================================

    async def get_tenant_plugin_license(
        self, tenant_id: UUID, plugin_id: UUID
    ) -> Optional[PluginLicense]:
        """
        Get plugin license for tenant using DRY query patterns.
        """
        try:
            licenses = await self.license_repo.find_all(
                tenant_id=tenant_id, plugin_id=plugin_id
            )

            # Return active license if exists
            active_licenses = [l for l in licenses if l.is_active]
            return active_licenses[0] if active_licenses else None

        except Exception as e:
            logger.error(f"Error fetching tenant plugin license: {e}")
            return None

    async def get_plugin_installation(
        self, installation_id: UUID, tenant_id: Optional[UUID] = None
    ) -> Optional[PluginLicense]:
        """
        Get plugin installation with optional tenant validation.
        """
        try:
            installation = await self.license_repo.get_by_id(installation_id)

            if installation and tenant_id and installation.tenant_id != tenant_id:
                return None  # Installation doesn't belong to tenant

            return installation

        except Exception as e:
            logger.error(f"Error fetching plugin installation: {e}")
            return None

    async def get_tenant_plugins(
        self, tenant_id: UUID, status: Optional[LicenseStatus] = None
    ) -> List[PluginLicense]:
        """
        Get all plugins installed for tenant.
        """
        try:
            filters = {"tenant_id": tenant_id}
            if status:
                filters["status"] = status

            installations = await self.license_repo.find_all(**filters)
            return installations

        except Exception as e:
            logger.error(f"Error fetching tenant plugins: {e}")
            return []

    async def get_dependent_plugins(
        self, plugin_id: UUID, tenant_id: UUID
    ) -> List[PluginLicense]:
        """
        Get plugins that depend on the specified plugin.
        """
        try:
            # Get all tenant plugins
            tenant_plugins = await self.get_tenant_plugins(tenant_id)

            # Find dependencies
            dependent_plugins = []
            target_plugin = await self.get_plugin(plugin_id)

            if not target_plugin:
                return []

            for installation in tenant_plugins:
                if installation.plugin and installation.is_active:
                    plugin_deps = installation.plugin.dependencies or []
                    if any(
                        dep.get("plugin_id") == str(plugin_id) for dep in plugin_deps
                    ):
                        dependent_plugins.append(installation)

            return dependent_plugins

        except Exception as e:
            logger.error(f"Error finding dependent plugins: {e}")
            return []

    # ============================================================================
    # Usage Analytics
    # ============================================================================

    async def get_plugin_usage_stats(
        self,
        installation_id: UUID,
        tenant_id: UUID,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[PluginUsageResponse]:
        """
        Get plugin usage statistics following DRY analytics patterns.
        """
        try:
            # Validate installation exists and belongs to tenant
            installation = await self.get_plugin_installation(
                installation_id, tenant_id
            )
            if not installation:
                return None

            # Get usage records
            usage_records = await self.usage_repo.get_usage_stats(
                license_id=installation_id, start_date=start_date, end_date=end_date
            )

            # Calculate aggregated stats
            total_calls = sum(record.quantity for record in usage_records)
            total_cost = sum(record.total_cost for record in usage_records)

            # Build response
            return PluginUsageResponse(
                installation_id=installation_id,
                plugin_name=installation.plugin.name,
                period_start=start_date,
                period_end=end_date,
                total_api_calls=total_calls,
                total_cost_cents=int(total_cost * 100),
                current_usage=installation.current_usage,
                usage_limit=installation.usage_limit,
                usage_percentage=installation.usage_percentage,
                daily_usage=[],  # Would implement daily breakdown
                feature_usage={},  # Would implement feature breakdown
            )

        except Exception as e:
            logger.error(f"Error fetching plugin usage: {e}")
            return None

    async def record_plugin_usage(
        self,
        license_id: UUID,
        usage_type: str,
        quantity: int = 1,
        feature_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record plugin usage following DRY audit patterns.
        """
        try:
            # Get license to validate
            license = await self.license_repo.get_by_id(license_id)
            if not license or not license.is_active:
                return False

            # Check usage limits
            if not license.record_usage(quantity):
                logger.warning(f"Usage limit exceeded for license {license_id}")
                return False

            # Create usage record
            usage_data = {
                "license_id": license_id,
                "plugin_id": license.plugin_id,
                "usage_type": usage_type,
                "quantity": quantity,
                "feature_name": feature_name,
                "usage_date": datetime.now(timezone.utc),
            }

            if metadata:
                usage_data.update(metadata)

            await self.usage_repo.create(usage_data)

            # Update license usage counter
            await self.license_repo.update(
                license_id, {"current_usage": license.current_usage}
            )

            return True

        except Exception as e:
            logger.error(f"Error recording plugin usage: {e}")
            return False

    # ============================================================================
    # Helper Methods
    # ============================================================================

    def _is_license_tier_available(self, plugin: Plugin, tier: LicenseTier) -> bool:
        """
        Check if license tier is available for plugin.
        """
        tier_availability = {
            LicenseTier.FREE: plugin.free_tier_available,
            LicenseTier.BASIC: plugin.basic_price_cents > 0
            or plugin.free_tier_available,
            LicenseTier.PREMIUM: plugin.premium_price_cents > 0,
            LicenseTier.ENTERPRISE: plugin.enterprise_price_cents > 0,
        }

        return tier_availability.get(tier, False)

    async def _validate_plugin_dependencies(
        self, plugin: Plugin, tenant_id: UUID
    ) -> None:
        """
        Validate plugin dependencies are satisfied.
        """
        if not plugin.dependencies:
            return

        # Get tenant's installed plugins
        tenant_plugins = await self.get_tenant_plugins(
            tenant_id, status=LicenseStatus.ACTIVE
        )
        installed_plugin_ids = {str(p.plugin_id) for p in tenant_plugins}

        # Check required dependencies
        missing_deps = []
        for dep in plugin.dependencies:
            dep_plugin_id = dep.get("plugin_id")
            if dep_plugin_id and dep_plugin_id not in installed_plugin_ids:
                missing_deps.append(dep.get("name", dep_plugin_id))

        if missing_deps:
            raise ValidationError(
                f"Missing required dependencies: {', '.join(missing_deps)}"
            )

    async def _filter_plugins_for_tenant(
        self, plugins: List[Plugin], tenant_id: UUID
    ) -> List[Plugin]:
        """
        Filter plugins based on tenant accessibility and permissions.
        """
        # Implementation would check tenant permissions, subscription level, etc.
        return plugins

    async def _record_plugin_event(
        self,
        tenant_id: UUID,
        plugin_id: UUID,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record plugin lifecycle events for audit trail.
        """
        try:
            if self.monitoring:
                self.monitoring.record_metric(
                    name="plugin_event",
                    value=1,
                    tags={
                        "tenant_id": str(tenant_id),
                        "plugin_id": str(plugin_id),
                        "event_type": event_type,
                    },
                )

            logger.info(f"Plugin event recorded: {event_type} for plugin {plugin_id}")

        except Exception as e:
            logger.error(f"Failed to record plugin event: {e}")
            # Don't fail the main operation if event recording fails


# Dependency injection helper following DRY patterns
def get_plugin_service(
    db: AsyncSession = None, plugin_manager: PluginManager = None
) -> PluginService:
    """
    Create plugin service instance with dependency injection.
    """
    if not db:
        db = get_db_session()

    if not plugin_manager:
        # Would get from dependency injection container
        from ..dependencies import get_plugin_manager

        plugin_manager = get_plugin_manager()

    return PluginService(db, plugin_manager)


__all__ = ["PluginService", "get_plugin_service"]
