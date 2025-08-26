"""
Portal Management SDK - creates and manages portal_id and portal settings per tenant.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime, timezone

from ..core.exceptions import PortalError, PortalNotFoundError
from ..models.portals import Portal, PortalSettings, PortalStatus, PortalType
from ..utils.datetime_compat import utcnow


class PortalManagementService:
    """In-memory service for portal management operations."""

    def __init__(self):
        """  Init   operation."""
        self._portals: Dict[UUID, Portal] = {}
        self._portal_settings: Dict[UUID, PortalSettings] = {}
        self._portal_id_index: Dict[str, UUID] = {}
        self._tenant_portals: Dict[str, List[UUID]] = {}

    async def create_portal(self, tenant_id: str, portal_id: str, **kwargs) -> Portal:
        """Create a new portal."""
        if portal_id in self._portal_id_index:
            raise PortalError(f"Portal ID already exists: {portal_id}")

        portal = Portal(tenant_id=tenant_id, portal_id=portal_id, **kwargs)

        self._portals[portal.id] = portal
        self._portal_id_index[portal_id] = portal.id

        if tenant_id not in self._tenant_portals:
            self._tenant_portals[tenant_id] = []
        self._tenant_portals[tenant_id].append(portal.id)

        return portal

    async def get_portal(self, portal_uuid: UUID) -> Optional[Portal]:
        """Get portal by UUID."""
        return self._portals.get(portal_uuid)

    async def get_portal_by_id(self, portal_id: str) -> Optional[Portal]:
        """Get portal by portal_id string."""
        portal_uuid = self._portal_id_index.get(portal_id)
        if portal_uuid:
            return self._portals.get(portal_uuid)
        return None

    async def update_portal(self, portal_uuid: UUID, **updates) -> Portal:
        """Update portal."""
        portal = self._portals.get(portal_uuid)
        if not portal:
            raise PortalNotFoundError(str(portal_uuid))

        for key, value in updates.items():
            if hasattr(portal, key):
                setattr(portal, key, value)

        portal.updated_at = datetime.now(timezone.utc)
        return portal

    async def create_portal_settings(
        self, portal_uuid: UUID, **kwargs
    ) -> PortalSettings:
        """Create portal settings."""
        portal = self._portals.get(portal_uuid)
        if not portal:
            raise PortalNotFoundError(str(portal_uuid))

        settings = PortalSettings(
            portal_id=portal_uuid, tenant_id=portal.tenant_id, **kwargs
        )

        self._portal_settings[portal_uuid] = settings
        return settings

    async def get_portal_settings(self, portal_uuid: UUID) -> Optional[PortalSettings]:
        """Get portal settings."""
        return self._portal_settings.get(portal_uuid)

    async def list_portals(self, tenant_id: str) -> List[Portal]:
        """List portals for tenant."""
        portal_uuids = self._tenant_portals.get(tenant_id, [])
        return [self._portals[uuid] for uuid in portal_uuids if uuid in self._portals]


class PortalManagementSDK:
    """Small, composable SDK for portal management."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = PortalManagementService()

    async def create_portal(
        self,
        portal_id: str,
        name: str,
        display_name: str,
        portal_type: str = "customer",
        **kwargs,
    ) -> Dict[str, Any]:
        """Create and manage portal_id per tenant."""
        portal = await self._service.create_portal(
            tenant_id=self.tenant_id,
            portal_id=portal_id,
            name=name,
            display_name=display_name,
            portal_type=PortalType(portal_type),
            **kwargs,
        )

        return {
            "portal_uuid": str(portal.id),
            "portal_id": portal.portal_id,
            "name": portal.name,
            "display_name": portal.display_name,
            "portal_type": portal.portal_type.value,
            "status": portal.status.value,
            "created_at": portal.created_at.isoformat(),
        }

    async def get_portal(self, portal_id: str) -> Optional[Dict[str, Any]]:
        """Get portal by portal_id."""
        portal = await self._service.get_portal_by_id(portal_id)
        if not portal or portal.tenant_id != self.tenant_id:
            return None

        return {
            "portal_uuid": str(portal.id),
            "portal_id": portal.portal_id,
            "name": portal.name,
            "display_name": portal.display_name,
            "description": portal.description,
            "portal_type": portal.portal_type.value,
            "status": portal.status.value,
            "base_url": portal.base_url,
            "custom_domain": portal.custom_domain,
            "logo_url": portal.logo_url,
            "theme_config": portal.theme_config,
            "created_at": portal.created_at.isoformat(),
            "updated_at": portal.updated_at.isoformat(),
        }

    async def update_portal(self, portal_id: str, **updates) -> Dict[str, Any]:
        """Update portal."""
        portal = await self._service.get_portal_by_id(portal_id)
        if not portal or portal.tenant_id != self.tenant_id:
            raise PortalError("Portal not found in tenant")

        portal = await self._service.update_portal(portal.id, **updates)
        return await self.get_portal(portal_id)

    async def configure_portal_settings(
        self,
        portal_id: str,
        session_timeout: int = 3600,
        max_login_attempts: int = 5,
        require_mfa: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Configure portal settings per tenant."""
        portal = await self._service.get_portal_by_id(portal_id)
        if not portal or portal.tenant_id != self.tenant_id:
            raise PortalError("Portal not found in tenant")

        settings = await self._service.create_portal_settings(
            portal.id,
            session_timeout=session_timeout,
            max_login_attempts=max_login_attempts,
            require_mfa=require_mfa,
            **kwargs,
        )

        return {
            "portal_id": portal_id,
            "session_timeout": settings.session_timeout,
            "max_login_attempts": settings.max_login_attempts,
            "require_mfa": settings.require_mfa,
            "password_min_length": settings.password_min_length,
            "enabled_features": settings.enabled_features,
            "created_at": settings.created_at.isoformat(),
        }

    async def get_portal_settings(self, portal_id: str) -> Optional[Dict[str, Any]]:
        """Get portal settings."""
        portal = await self._service.get_portal_by_id(portal_id)
        if not portal or portal.tenant_id != self.tenant_id:
            return None

        settings = await self._service.get_portal_settings(portal.id)
        if not settings:
            return None

        return {
            "portal_id": portal_id,
            "session_timeout": settings.session_timeout,
            "max_login_attempts": settings.max_login_attempts,
            "lockout_duration": settings.lockout_duration,
            "require_mfa": settings.require_mfa,
            "password_min_length": settings.password_min_length,
            "password_require_uppercase": settings.password_require_uppercase,
            "password_require_lowercase": settings.password_require_lowercase,
            "password_require_numbers": settings.password_require_numbers,
            "password_require_symbols": settings.password_require_symbols,
            "enabled_features": settings.enabled_features,
            "disabled_features": settings.disabled_features,
            "custom_css": settings.custom_css,
            "settings": settings.settings,
        }

    async def list_portals(self) -> List[Dict[str, Any]]:
        """List all portals for tenant."""
        portals = await self._service.list_portals(self.tenant_id)

        return [
            {
                "portal_uuid": str(portal.id),
                "portal_id": portal.portal_id,
                "name": portal.name,
                "display_name": portal.display_name,
                "portal_type": portal.portal_type.value,
                "status": portal.status.value,
                "created_at": portal.created_at.isoformat(),
            }
            for portal in portals
        ]

    async def activate_portal(self, portal_id: str) -> Dict[str, Any]:
        """Activate portal."""
        return await self.update_portal(portal_id, status=PortalStatus.ACTIVE)

    async def deactivate_portal(self, portal_id: str) -> Dict[str, Any]:
        """Deactivate portal."""
        return await self.update_portal(portal_id, status=PortalStatus.INACTIVE)
