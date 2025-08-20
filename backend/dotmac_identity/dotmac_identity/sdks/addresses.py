"""
Addresses SDK - postal/geo addresses.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from ..models.addresses import Address, AddressType


class AddressService:
    """In-memory service for address operations."""

    def __init__(self):
        self._addresses: Dict[UUID, Address] = {}
        self._contact_addresses: Dict[UUID, List[UUID]] = {}
        self._organization_addresses: Dict[UUID, List[UUID]] = {}
        self._customer_addresses: Dict[UUID, List[UUID]] = {}

    async def create_address(self, **kwargs) -> Address:
        """Create address."""
        address = Address(**kwargs)
        self._addresses[address.id] = address

        # Index by linked entities
        if address.contact_id:
            if address.contact_id not in self._contact_addresses:
                self._contact_addresses[address.contact_id] = []
            self._contact_addresses[address.contact_id].append(address.id)

        if address.organization_id:
            if address.organization_id not in self._organization_addresses:
                self._organization_addresses[address.organization_id] = []
            self._organization_addresses[address.organization_id].append(address.id)

        if address.customer_id:
            if address.customer_id not in self._customer_addresses:
                self._customer_addresses[address.customer_id] = []
            self._customer_addresses[address.customer_id].append(address.id)

        return address

    async def get_address(self, address_id: UUID) -> Optional[Address]:
        """Get address by ID."""
        return self._addresses.get(address_id)

    async def get_addresses_by_contact(self, contact_id: UUID) -> List[Address]:
        """Get addresses for contact."""
        address_ids = self._contact_addresses.get(contact_id, [])
        return [self._addresses[aid] for aid in address_ids if aid in self._addresses]


class AddressesSDK:
    """Small, composable SDK for postal/geo address management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = AddressService()

    async def create_address(  # noqa: PLR0913
        self,
        line1: str,
        city: str,
        state_province: str,
        postal_code: str,
        country: str,
        address_type: str = "billing",
        contact_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create postal/geo address."""
        address = await self._service.create_address(
            tenant_id=self.tenant_id,
            line1=line1,
            city=city,
            state_province=state_province,
            postal_code=postal_code,
            country=country,
            address_type=AddressType(address_type),
            contact_id=UUID(contact_id) if contact_id else None,
            organization_id=UUID(organization_id) if organization_id else None,
            customer_id=UUID(customer_id) if customer_id else None,
            **kwargs
        )

        return {
            "address_id": str(address.id),
            "line1": address.line1,
            "line2": address.line2,
            "city": address.city,
            "state_province": address.state_province,
            "postal_code": address.postal_code,
            "country": address.country,
            "address_type": address.address_type.value,
            "formatted_address": address.get_formatted_address(),
            "created_at": address.created_at.isoformat(),
        }

    async def get_address(self, address_id: str) -> Optional[Dict[str, Any]]:
        """Get address by ID."""
        address = await self._service.get_address(UUID(address_id))
        if not address or address.tenant_id != self.tenant_id:
            return None

        return {
            "address_id": str(address.id),
            "line1": address.line1,
            "line2": address.line2,
            "line3": address.line3,
            "city": address.city,
            "state_province": address.state_province,
            "postal_code": address.postal_code,
            "country": address.country,
            "address_type": address.address_type.value,
            "status": address.status.value,
            "latitude": address.latitude,
            "longitude": address.longitude,
            "is_verified": address.is_verified,
            "is_deliverable": address.is_deliverable,
            "formatted_address": address.get_formatted_address(),
            "single_line_address": address.get_single_line_address(),
            "contact_id": str(address.contact_id) if address.contact_id else None,
            "organization_id": str(address.organization_id) if address.organization_id else None,
            "customer_id": str(address.customer_id) if address.customer_id else None,
            "notes": address.notes,
            "created_at": address.created_at.isoformat(),
            "updated_at": address.updated_at.isoformat(),
        }

    async def get_addresses_by_contact(self, contact_id: str) -> List[Dict[str, Any]]:
        """Get all addresses for contact."""
        addresses = await self._service.get_addresses_by_contact(UUID(contact_id))

        return [
            {
                "address_id": str(address.id),
                "line1": address.line1,
                "city": address.city,
                "state_province": address.state_province,
                "postal_code": address.postal_code,
                "country": address.country,
                "address_type": address.address_type.value,
                "formatted_address": address.get_formatted_address(),
                "is_verified": address.is_verified,
            }
            for address in addresses
            if address.tenant_id == self.tenant_id
        ]
