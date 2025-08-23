"""
Reseller Portal SDK - support reseller access.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from ..core.exceptions import PortalError
from ..models.portals import AccessLevel, BindingStatus, ResellerPortalAccess
from ..utils.datetime_compat import utcnow


class ResellerPortalService:
    """In-memory service for reseller portal operations."""

    def __init__(self):
        self._accesses: Dict[UUID, ResellerPortalAccess] = {}
        self._portal_accesses: Dict[UUID, List[UUID]] = {}
        self._reseller_accesses: Dict[UUID, List[UUID]] = {}

    async def create_access(self, **kwargs) -> ResellerPortalAccess:
        """Create reseller portal access."""
        access = ResellerPortalAccess(**kwargs)

        self._accesses[access.id] = access

        # Index by portal
        if access.portal_id not in self._portal_accesses:
            self._portal_accesses[access.portal_id] = []
        self._portal_accesses[access.portal_id].append(access.id)

        # Index by reseller organization
        if access.reseller_organization_id not in self._reseller_accesses:
            self._reseller_accesses[access.reseller_organization_id] = []
        self._reseller_accesses[access.reseller_organization_id].append(access.id)

        return access

    async def get_access(self, access_id: UUID) -> Optional[ResellerPortalAccess]:
        """Get access by ID."""
        return self._accesses.get(access_id)

    async def update_access(self, access_id: UUID, **updates) -> ResellerPortalAccess:
        """Update access."""
        access = self._accesses.get(access_id)
        if not access:
            raise PortalError(f"Access not found: {access_id}")

        for key, value in updates.items():
            if hasattr(access, key):
                setattr(access, key, value)

        access.updated_at = access.updated_at.__class__.utcnow()
        return access


class ResellerPortalSDK:
    """Small, composable SDK for reseller portal access management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = ResellerPortalService()

    async def grant_reseller_access(
        self,
        portal_id: str,
        reseller_organization_id: str,
        reseller_contact_id: Optional[str] = None,
        reseller_account_id: Optional[str] = None,
        access_level: str = "read_write",
        permissions: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Grant reseller access to portal."""
        access = await self._service.create_access(
            portal_id=UUID(portal_id),
            tenant_id=self.tenant_id,
            reseller_organization_id=UUID(reseller_organization_id),
            reseller_contact_id=(
                UUID(reseller_contact_id) if reseller_contact_id else None
            ),
            reseller_account_id=(
                UUID(reseller_account_id) if reseller_account_id else None
            ),
            access_level=AccessLevel(access_level),
            permissions=permissions or [],
            **kwargs,
        )

        return {
            "access_id": str(access.id),
            "portal_id": portal_id,
            "reseller_organization_id": str(access.reseller_organization_id),
            "reseller_contact_id": (
                str(access.reseller_contact_id) if access.reseller_contact_id else None
            ),
            "access_level": access.access_level.value,
            "permissions": access.permissions,
            "status": access.status.value,
            "created_at": access.created_at.isoformat(),
        }

    async def get_reseller_access(self, access_id: str) -> Optional[Dict[str, Any]]:
        """Get reseller portal access."""
        access = await self._service.get_access(UUID(access_id))
        if not access or access.tenant_id != self.tenant_id:
            return None

        return {
            "access_id": str(access.id),
            "portal_id": str(access.portal_id),
            "reseller_organization_id": str(access.reseller_organization_id),
            "reseller_contact_id": (
                str(access.reseller_contact_id) if access.reseller_contact_id else None
            ),
            "reseller_account_id": (
                str(access.reseller_account_id) if access.reseller_account_id else None
            ),
            "status": access.status.value,
            "access_level": access.access_level.value,
            "permissions": access.permissions,
            "accessible_customers": [str(cid) for cid in access.accessible_customers],
            "accessible_organizations": [
                str(oid) for oid in access.accessible_organizations
            ],
            "ip_restrictions": access.ip_restrictions,
            "time_restrictions": access.time_restrictions,
            "commission_rate": access.commission_rate,
            "territory": access.territory,
            "last_access_at": (
                access.last_access_at.isoformat() if access.last_access_at else None
            ),
            "created_at": access.created_at.isoformat(),
            "updated_at": access.updated_at.isoformat(),
        }

    async def set_customer_access_scope(
        self, access_id: str, accessible_customers: List[str]
    ) -> Dict[str, Any]:
        """Set which customers reseller can access."""
        access = await self._service.update_access(
            UUID(access_id),
            accessible_customers=[UUID(cid) for cid in accessible_customers],
        )

        if access.tenant_id != self.tenant_id:
            raise PortalError("Access not found in tenant")

        return await self.get_reseller_access(access_id)

    async def set_organization_access_scope(
        self, access_id: str, accessible_organizations: List[str]
    ) -> Dict[str, Any]:
        """Set which organizations reseller can access."""
        access = await self._service.update_access(
            UUID(access_id),
            accessible_organizations=[UUID(oid) for oid in accessible_organizations],
        )

        if access.tenant_id != self.tenant_id:
            raise PortalError("Access not found in tenant")

        return await self.get_reseller_access(access_id)

    async def set_ip_restrictions(
        self, access_id: str, ip_restrictions: List[str]
    ) -> Dict[str, Any]:
        """Set IP address restrictions for reseller access."""
        access = await self._service.update_access(
            UUID(access_id), ip_restrictions=ip_restrictions
        )

        if access.tenant_id != self.tenant_id:
            raise PortalError("Access not found in tenant")

        return await self.get_reseller_access(access_id)

    async def set_commission_rate(
        self, access_id: str, commission_rate: float
    ) -> Dict[str, Any]:
        """Set commission rate for reseller."""
        access = await self._service.update_access(
            UUID(access_id), commission_rate=commission_rate
        )

        if access.tenant_id != self.tenant_id:
            raise PortalError("Access not found in tenant")

        return await self.get_reseller_access(access_id)

    async def activate_reseller_access(self, access_id: str) -> Dict[str, Any]:
        """Activate reseller portal access."""
        access = await self._service.update_access(
            UUID(access_id), status=BindingStatus.ACTIVE
        )

        if access.tenant_id != self.tenant_id:
            raise PortalError("Access not found in tenant")

        return await self.get_reseller_access(access_id)

    async def suspend_reseller_access(self, access_id: str) -> Dict[str, Any]:
        """Suspend reseller portal access."""
        access = await self._service.update_access(
            UUID(access_id), status=BindingStatus.SUSPENDED
        )

        if access.tenant_id != self.tenant_id:
            raise PortalError("Access not found in tenant")

        return await self.get_reseller_access(access_id)
