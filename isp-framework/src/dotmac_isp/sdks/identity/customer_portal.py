"""
Customer Portal SDK - binds customer/contact to portal account, login policies, ISP credentials.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime, timezone

from ..core.exceptions import PortalError
from ..models.portals import AccessLevel, BindingStatus, CustomerPortalBinding
from ..utils.datetime_compat import utcnow


class CustomerPortalService:
    """In-memory service for customer portal operations."""

    def __init__(self):
        """  Init   operation."""
        self._bindings: Dict[UUID, CustomerPortalBinding] = {}
        self._portal_bindings: Dict[UUID, List[UUID]] = {}
        self._customer_bindings: Dict[UUID, List[UUID]] = {}
        self._username_index: Dict[str, UUID] = {}

    async def create_binding(self, **kwargs) -> CustomerPortalBinding:
        """Create customer portal binding."""
        binding = CustomerPortalBinding(**kwargs)

        self._bindings[binding.id] = binding

        # Index by portal
        if binding.portal_id not in self._portal_bindings:
            self._portal_bindings[binding.portal_id] = []
        self._portal_bindings[binding.portal_id].append(binding.id)

        # Index by customer
        if binding.customer_id:
            if binding.customer_id not in self._customer_bindings:
                self._customer_bindings[binding.customer_id] = []
            self._customer_bindings[binding.customer_id].append(binding.id)

        # Index by username
        self._username_index[binding.portal_username] = binding.id

        return binding

    async def get_binding(self, binding_id: UUID) -> Optional[CustomerPortalBinding]:
        """Get binding by ID."""
        return self._bindings.get(binding_id)

    async def get_binding_by_username(
        self, portal_username: str
    ) -> Optional[CustomerPortalBinding]:
        """Get binding by portal username."""
        binding_id = self._username_index.get(portal_username)
        if binding_id:
            return self._bindings.get(binding_id)
        return None

    async def update_binding(
        self, binding_id: UUID, **updates
    ) -> CustomerPortalBinding:
        """Update binding."""
        binding = self._bindings.get(binding_id)
        if not binding:
            raise PortalError(f"Binding not found: {binding_id}")

        for key, value in updates.items():
            if hasattr(binding, key):
                setattr(binding, key, value)

        binding.updated_at = datetime.now(timezone.utc)
        return binding

    async def list_bindings_by_portal(
        self, portal_id: UUID
    ) -> List[CustomerPortalBinding]:
        """List bindings for portal."""
        binding_ids = self._portal_bindings.get(portal_id, [])
        return [self._bindings[bid] for bid in binding_ids if bid in self._bindings]


class CustomerPortalSDK:
    """Small, composable SDK for customer portal binding and login policies."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = CustomerPortalService()

    async def bind_customer_to_portal(
        self,
        portal_id: str,
        customer_id: str,
        portal_username: str,
        portal_email: str,
        contact_id: Optional[str] = None,
        account_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Bind a customer/contact to a portal account."""
        binding = await self._service.create_binding(
            portal_id=UUID(portal_id),
            tenant_id=self.tenant_id,
            customer_id=UUID(customer_id),
            contact_id=UUID(contact_id) if contact_id else None,
            account_id=UUID(account_id) if account_id else None,
            portal_username=portal_username,
            portal_email=portal_email,
            **kwargs,
        )

        return {
            "binding_id": str(binding.id),
            "portal_id": portal_id,
            "customer_id": str(binding.customer_id),
            "contact_id": str(binding.contact_id) if binding.contact_id else None,
            "portal_username": binding.portal_username,
            "portal_email": binding.portal_email,
            "status": binding.status.value,
            "access_level": binding.access_level.value,
            "created_at": binding.created_at.isoformat(),
        }

    async def get_customer_portal_binding(
        self, binding_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get customer portal binding."""
        binding = await self._service.get_binding(UUID(binding_id))
        if not binding or binding.tenant_id != self.tenant_id:
            return None

        return {
            "binding_id": str(binding.id),
            "portal_id": str(binding.portal_id),
            "customer_id": str(binding.customer_id) if binding.customer_id else None,
            "contact_id": str(binding.contact_id) if binding.contact_id else None,
            "account_id": str(binding.account_id) if binding.account_id else None,
            "portal_username": binding.portal_username,
            "portal_email": binding.portal_email,
            "status": binding.status.value,
            "access_level": binding.access_level.value,
            "permissions": binding.permissions,
            "login_policies": binding.login_policies,
            "published_credentials": binding.published_credentials,
            "published_attributes": binding.published_attributes,
            "last_login_at": (
                binding.last_login_at.isoformat() if binding.last_login_at else None
            ),
            "created_at": binding.created_at.isoformat(),
            "updated_at": binding.updated_at.isoformat(),
        }

    async def get_binding_by_username(
        self, portal_username: str
    ) -> Optional[Dict[str, Any]]:
        """Get binding by portal username."""
        binding = await self._service.get_binding_by_username(portal_username)
        if not binding or binding.tenant_id != self.tenant_id:
            return None

        return await self.get_customer_portal_binding(str(binding.id))

    async def update_login_policies(
        self, binding_id: str, login_policies: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update login policies for customer portal binding."""
        binding = await self._service.update_binding(
            UUID(binding_id), login_policies=login_policies
        )

        if binding.tenant_id != self.tenant_id:
            raise PortalError("Binding not found in tenant")

        return await self.get_customer_portal_binding(binding_id)

    async def publish_credentials_for_networking(
        self, binding_id: str, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish credentials/attributes for ISP Networking consumption."""
        binding = await self._service.update_binding(
            UUID(binding_id), published_credentials=credentials
        )

        if binding.tenant_id != self.tenant_id:
            raise PortalError("Binding not found in tenant")

        return await self.get_customer_portal_binding(binding_id)

    async def publish_attributes_for_networking(
        self, binding_id: str, attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish attributes for ISP Networking consumption."""
        binding = await self._service.update_binding(
            UUID(binding_id), published_attributes=attributes
        )

        if binding.tenant_id != self.tenant_id:
            raise PortalError("Binding not found in tenant")

        return await self.get_customer_portal_binding(binding_id)

    async def set_access_level(
        self, binding_id: str, access_level: str
    ) -> Dict[str, Any]:
        """Set access level for customer portal binding."""
        binding = await self._service.update_binding(
            UUID(binding_id), access_level=AccessLevel(access_level)
        )

        if binding.tenant_id != self.tenant_id:
            raise PortalError("Binding not found in tenant")

        return await self.get_customer_portal_binding(binding_id)

    async def activate_binding(self, binding_id: str) -> Dict[str, Any]:
        """Activate customer portal binding."""
        binding = await self._service.update_binding(
            UUID(binding_id), status=BindingStatus.ACTIVE
        )

        if binding.tenant_id != self.tenant_id:
            raise PortalError("Binding not found in tenant")

        return await self.get_customer_portal_binding(binding_id)

    async def suspend_binding(self, binding_id: str) -> Dict[str, Any]:
        """Suspend customer portal binding."""
        binding = await self._service.update_binding(
            UUID(binding_id), status=BindingStatus.SUSPENDED
        )

        if binding.tenant_id != self.tenant_id:
            raise PortalError("Binding not found in tenant")

        return await self.get_customer_portal_binding(binding_id)
