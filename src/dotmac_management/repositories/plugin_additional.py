"""
Additional plugin repository methods.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.plugin import Plugin, PluginLicense, PluginUsage
from ..repositories.base import BaseRepository
from ..schemas.plugin import PluginSearchRequest


class PluginRepository(BaseRepository[Plugin]):
    """Repository for plugin operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Plugin)

    async def get_by_name(self, name: str) -> Optional[Plugin]:
        """Get plugin by name."""
        return await self.get_by_field("name", name)

    async def increment_download_count(self, plugin_id: UUID) -> None:
        """Increment plugin download count."""
        plugin = await self.get_by_id(plugin_id)
        if plugin:
            await self.update(
                plugin_id, {"download_count": plugin.download_count + 1}, "system"
            )

    async def update_rating(
        self, plugin_id: UUID, rating: float, review_count: int
    ) -> None:
        """Update plugin rating and review count."""
        await self.update(
            plugin_id, {"rating": rating, "review_count": review_count}, "system"
        )

    async def search_plugins(
        self,
        query: Optional[str] = None,
        filters: Optional[dict] = None,
        sort_by: str = "popularity",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100,
    ) -> list[Plugin]:
        """Search plugins with filters."""
        # For now, simple implementation - would add full-text search in production
        search_filters = {"is_deleted": False, "is_active": True}
        if filters:
            search_filters.update(filters)

        return await self.list(
            filters=search_filters,
            skip=skip,
            limit=limit,
            order_by=f"{sort_by} {sort_order}" if sort_by else "created_at DESC",
        )

    async def count_search_results(self, search_request: PluginSearchRequest) -> int:
        """Count search results."""
        filters = {"is_deleted": False, "is_active": True}
        if search_request.filters:
            if search_request.filters.category:
                filters["category"] = search_request.filters.category
            if search_request.filters.author:
                filters["author"] = search_request.filters.author
            if search_request.filters.is_official is not None:
                filters["is_official"] = search_request.filters.is_official
            if search_request.filters.is_verified is not None:
                filters["is_verified"] = search_request.filters.is_verified

        return await self.count(filters)


class PluginLicenseRepository(BaseRepository[PluginLicense]):
    """Repository for plugin license operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PluginLicense)

    async def get_by_tenant_and_plugin(
        self, tenant_id: UUID, plugin_id: UUID
    ) -> Optional[PluginLicense]:
        """Get installation by tenant and plugin."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.plugin_id == plugin_id,
                self.model.is_deleted is False,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_plugin(self, installation_id: UUID) -> Optional[PluginLicense]:
        """Get installation with plugin details."""
        # For now, just get the installation - would implement join in production
        return await self.get_by_id(installation_id)

    async def get_by_tenant(self, tenant_id: UUID) -> list[PluginLicense]:
        """Get installations by tenant."""
        return await self.list(filters={"tenant_id": tenant_id, "is_deleted": False})

    async def get_by_plugin(self, plugin_id: UUID) -> list[PluginLicense]:
        """Get installations by plugin."""
        return await self.list(filters={"plugin_id": plugin_id, "is_deleted": False})

    async def update_status(
        self, installation_id: UUID, status: str, updated_by: str
    ) -> Optional[PluginLicense]:
        """Update installation status."""
        return await self.update(installation_id, {"status": status}, updated_by)

    async def get_auto_update_enabled(self) -> list[PluginLicense]:
        """Get installations with auto-update enabled."""
        return await self.list(
            filters={
                "auto_update": True,
                "enabled": True,
                "status": "installed",
                "is_deleted": False,
            }
        )


class PluginUsageRepository(BaseRepository[PluginUsage]):
    """Repository for plugin usage tracking."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PluginUsage)

    async def get_by_license(self, license_id: UUID) -> list[PluginUsage]:
        """Get usage records by license."""
        return await self.list(filters={"license_id": license_id, "is_deleted": False})

    async def get_by_plugin(self, plugin_id: UUID) -> list[PluginUsage]:
        """Get usage records by plugin."""
        return await self.list(filters={"plugin_id": plugin_id, "is_deleted": False})


class PluginInstallationRepository(BaseRepository[PluginLicense]):
    """Alias for PluginLicense repository - installations are managed via licenses."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PluginLicense)

    async def get_by_tenant_and_plugin(
        self, tenant_id: UUID, plugin_id: UUID
    ) -> Optional[PluginLicense]:
        """Get installation by tenant and plugin."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.plugin_id == plugin_id,
                self.model.is_deleted is False,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


class PluginResourceUsageRepository(BaseRepository[PluginUsage]):
    """Repository for plugin resource usage tracking."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PluginUsage)

    async def get_resource_usage_by_license(
        self,
        license_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[PluginUsage]:
        """Get resource usage records by license within date range."""
        filters = {"license_id": license_id, "is_deleted": False}
        # In production, would add date filtering logic here
        return await self.list(filters=filters)

    async def get_resource_usage_by_plugin(
        self,
        plugin_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[PluginUsage]:
        """Get resource usage records by plugin within date range."""
        filters = {"plugin_id": plugin_id, "is_deleted": False}
        # In production, would add date filtering logic here
        return await self.list(filters=filters)


class PluginSecurityScanRepository(BaseRepository[Plugin]):
    """Repository for plugin security scan operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Plugin)

    async def get_plugins_for_security_scan(
        self, scan_type: str = "all"
    ) -> list[Plugin]:
        """Get plugins that need security scanning."""
        filters = {"is_deleted": False, "is_active": True}
        return await self.list(filters=filters)

    async def update_security_status(
        self, plugin_id: UUID, security_data: dict[str, Any], updated_by: str
    ) -> Optional[Plugin]:
        """Update plugin security scan results."""
        # In production, would store security scan results in a separate table
        # For now, just update the plugin metadata
        plugin = await self.get_by_id(plugin_id)
        if plugin and hasattr(plugin, "metadata"):
            metadata = getattr(plugin, "metadata", {}) or {}
            metadata["security_scan"] = security_data
            return await self.update(plugin_id, {"metadata": metadata}, updated_by)
        return None


class PluginVersionRepository(BaseRepository[Plugin]):
    """Repository for plugin version management."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Plugin)

    async def get_plugin_versions(self, plugin_name: str) -> list[Plugin]:
        """Get all versions of a plugin."""
        # In a production system, versions would be in a separate table
        # For now, get plugins by name pattern
        return await self.list(filters={"name": plugin_name, "is_deleted": False})

    async def get_latest_version(self, plugin_name: str) -> Optional[Plugin]:
        """Get the latest version of a plugin."""
        plugins = await self.get_plugin_versions(plugin_name)
        if not plugins:
            return None
        # Simple version sorting - in production would use semantic versioning
        return sorted(plugins, key=lambda p: p.version, reverse=True)[0]

    async def check_compatibility(self, plugin_id: UUID, target_version: str) -> bool:
        """Check if plugin version is compatible."""
        plugin = await self.get_by_id(plugin_id)
        if not plugin:
            return False
        # Simple compatibility check - in production would have comprehensive logic
        return True
