"""
Site POP SDK - sites/racks/rooms management
"""

from datetime import datetime
from dotmac_networking.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import NetworkingError


class SitePopService:
    """In-memory service for site/POP operations."""

    def __init__(self):
        self._sites: Dict[str, Dict[str, Any]] = {}
        self._racks: Dict[str, List[Dict[str, Any]]] = {}
        self._rooms: Dict[str, List[Dict[str, Any]]] = {}

    async def create_site(self, **kwargs) -> Dict[str, Any]:
        """Create site/POP."""
        site_id = kwargs.get("site_id") or str(uuid4())

        if site_id in self._sites:
            raise NetworkingError(f"Site already exists: {site_id}")

        site = {
            "site_id": site_id,
            "site_name": kwargs.get("site_name", ""),
            "site_type": kwargs.get("site_type", "pop"),  # pop, datacenter, office
            "address": kwargs.get("address", ""),
            "city": kwargs.get("city", ""),
            "state": kwargs.get("state", ""),
            "country": kwargs.get("country", ""),
            "postal_code": kwargs.get("postal_code", ""),
            "latitude": kwargs.get("latitude"),
            "longitude": kwargs.get("longitude"),
            "contact_name": kwargs.get("contact_name", ""),
            "contact_phone": kwargs.get("contact_phone", ""),
            "contact_email": kwargs.get("contact_email", ""),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
            "metadata": kwargs.get("metadata", {}),
        }

        self._sites[site_id] = site
        self._racks[site_id] = []
        self._rooms[site_id] = []

        return site

    async def get_site(self, site_id: str) -> Optional[Dict[str, Any]]:
        """Get site by ID."""
        return self._sites.get(site_id)

    async def add_room(self, site_id: str, **kwargs) -> Dict[str, Any]:
        """Add room to site."""
        if site_id not in self._sites:
            raise NetworkingError(f"Site not found: {site_id}")

        room = {
            "room_id": kwargs.get("room_id") or str(uuid4()),
            "site_id": site_id,
            "room_name": kwargs.get("room_name", ""),
            "room_type": kwargs.get("room_type", "equipment"),  # equipment, office, storage
            "floor": kwargs.get("floor", ""),
            "dimensions": kwargs.get("dimensions", {}),
            "power_capacity": kwargs.get("power_capacity"),
            "cooling_capacity": kwargs.get("cooling_capacity"),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
        }

        self._rooms[site_id].append(room)
        return room

    async def add_rack(self, site_id: str, **kwargs) -> Dict[str, Any]:
        """Add rack to site."""
        if site_id not in self._sites:
            raise NetworkingError(f"Site not found: {site_id}")

        rack = {
            "rack_id": kwargs.get("rack_id") or str(uuid4()),
            "site_id": site_id,
            "room_id": kwargs.get("room_id"),
            "rack_name": kwargs.get("rack_name", ""),
            "rack_units": kwargs.get("rack_units", 42),
            "power_capacity": kwargs.get("power_capacity"),
            "weight_capacity": kwargs.get("weight_capacity"),
            "position_x": kwargs.get("position_x"),
            "position_y": kwargs.get("position_y"),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
        }

        self._racks[site_id].append(rack)
        return rack


class SitePopSDK:
    """Minimal, reusable SDK for site/POP management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = SitePopService()

    async def create_site(
        self,
        site_id: str,
        site_name: str,
        site_type: str = "pop",
        address: Optional[str] = None,
        city: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create site/POP."""
        site = await self._service.create_site(
            site_id=site_id,
            site_name=site_name,
            site_type=site_type,
            address=address,
            city=city,
            tenant_id=self.tenant_id,
            **kwargs
        )

        return {
            "site_id": site["site_id"],
            "site_name": site["site_name"],
            "site_type": site["site_type"],
            "address": site["address"],
            "city": site["city"],
            "state": site["state"],
            "country": site["country"],
            "status": site["status"],
            "created_at": site["created_at"],
        }

    async def get_site(self, site_id: str) -> Optional[Dict[str, Any]]:
        """Get site by ID."""
        site = await self._service.get_site(site_id)
        if not site:
            return None

        return {
            "site_id": site["site_id"],
            "site_name": site["site_name"],
            "site_type": site["site_type"],
            "address": site["address"],
            "city": site["city"],
            "state": site["state"],
            "country": site["country"],
            "postal_code": site["postal_code"],
            "latitude": site["latitude"],
            "longitude": site["longitude"],
            "contact_name": site["contact_name"],
            "contact_phone": site["contact_phone"],
            "contact_email": site["contact_email"],
            "status": site["status"],
            "created_at": site["created_at"],
            "updated_at": site["updated_at"],
            "metadata": site["metadata"],
        }

    async def add_room(
        self,
        site_id: str,
        room_name: str,
        room_type: str = "equipment",
        floor: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Add room to site."""
        room = await self._service.add_room(
            site_id=site_id,
            room_name=room_name,
            room_type=room_type,
            floor=floor,
            **kwargs
        )

        return {
            "room_id": room["room_id"],
            "site_id": room["site_id"],
            "room_name": room["room_name"],
            "room_type": room["room_type"],
            "floor": room["floor"],
            "power_capacity": room["power_capacity"],
            "cooling_capacity": room["cooling_capacity"],
            "status": room["status"],
            "created_at": room["created_at"],
        }

    async def add_rack(
        self,
        site_id: str,
        rack_name: str,
        room_id: Optional[str] = None,
        rack_units: int = 42,
        **kwargs
    ) -> Dict[str, Any]:
        """Add rack to site."""
        rack = await self._service.add_rack(
            site_id=site_id,
            room_id=room_id,
            rack_name=rack_name,
            rack_units=rack_units,
            **kwargs
        )

        return {
            "rack_id": rack["rack_id"],
            "site_id": rack["site_id"],
            "room_id": rack["room_id"],
            "rack_name": rack["rack_name"],
            "rack_units": rack["rack_units"],
            "power_capacity": rack["power_capacity"],
            "weight_capacity": rack["weight_capacity"],
            "status": rack["status"],
            "created_at": rack["created_at"],
        }

    async def get_site_rooms(self, site_id: str) -> List[Dict[str, Any]]:
        """Get all rooms for a site."""
        rooms = self._service._rooms.get(site_id, [])

        return [
            {
                "room_id": room["room_id"],
                "room_name": room["room_name"],
                "room_type": room["room_type"],
                "floor": room["floor"],
                "power_capacity": room["power_capacity"],
                "cooling_capacity": room["cooling_capacity"],
                "status": room["status"],
            }
            for room in rooms
        ]

    async def get_site_racks(self, site_id: str) -> List[Dict[str, Any]]:
        """Get all racks for a site."""
        racks = self._service._racks.get(site_id, [])

        return [
            {
                "rack_id": rack["rack_id"],
                "room_id": rack["room_id"],
                "rack_name": rack["rack_name"],
                "rack_units": rack["rack_units"],
                "power_capacity": rack["power_capacity"],
                "weight_capacity": rack["weight_capacity"],
                "status": rack["status"],
            }
            for rack in racks
        ]
