"""
MAC Registry SDK - MAC address management and tracking
"""

import re
from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional

from ..core.exceptions import NetworkingError


class MacRegistryService:
    """In-memory service for MAC address registry operations."""

    def __init__(self):
        """  Init   operation."""
        self._mac_entries: Dict[str, Dict[str, Any]] = {}
        self._device_macs: Dict[str, List[str]] = {}
        self._vendor_oui: Dict[str, str] = {}  # OUI -> Vendor mapping

    def _normalize_mac(self, mac_address: str) -> str:
        """Normalize MAC address format."""
        # Remove separators and convert to lowercase
        mac = re.sub(r"[:-]", "", mac_address.lower())

        # Validate MAC format
        if not re.match(r"^[0-9a-f]{12}$", mac):
            raise NetworkingError(f"Invalid MAC address format: {mac_address}")

        # Return in standard format (xx:xx:xx:xx:xx:xx)
        return ":".join([mac[i : i + 2] for i in range(0, 12, 2)])

    def _get_oui(self, mac_address: str) -> str:
        """Extract OUI (first 3 octets) from MAC address."""
        normalized = self._normalize_mac(mac_address)
        return normalized[:8]  # First 3 octets (xx:xx:xx)

    async def register_mac(self, **kwargs) -> Dict[str, Any]:
        """Register MAC address."""
        mac_address = self._normalize_mac(kwargs["mac_address"])

        if mac_address in self._mac_entries:
            raise NetworkingError(f"MAC address already registered: {mac_address}")

        oui = self._get_oui(mac_address)
        vendor = self._vendor_oui.get(oui, "Unknown")

        entry = {
            "mac_address": mac_address,
            "device_id": kwargs.get("device_id"),
            "interface_name": kwargs.get("interface_name"),
            "port_id": kwargs.get("port_id"),
            "vendor": vendor,
            "oui": oui,
            "device_type": kwargs.get("device_type", "unknown"),
            "description": kwargs.get("description", ""),
            "first_seen": utc_now().isoformat(),
            "last_seen": utc_now().isoformat(),
            "status": kwargs.get("status", "active"),
            "metadata": kwargs.get("metadata", {}),
        }

        self._mac_entries[mac_address] = entry

        # Index by device
        device_id = entry.get("device_id")
        if device_id:
            if device_id not in self._device_macs:
                self._device_macs[device_id] = []
            self._device_macs[device_id].append(mac_address)

        return entry

    async def update_mac_seen(self, mac_address: str) -> Dict[str, Any]:
        """Update last seen timestamp for MAC address."""
        normalized_mac = self._normalize_mac(mac_address)

        if normalized_mac not in self._mac_entries:
            raise NetworkingError(f"MAC address not found: {mac_address}")

        self._mac_entries[normalized_mac]["last_seen"] = utc_now().isoformat()
        return self._mac_entries[normalized_mac]


class MacRegistrySDK:
    """Minimal, reusable SDK for MAC address registry."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = MacRegistryService()

    async def register_mac(
        self,
        mac_address: str,
        device_id: Optional[str] = None,
        interface_name: Optional[str] = None,
        port_id: Optional[str] = None,
        device_type: str = "unknown",
        description: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Register MAC address in registry."""
        entry = await self._service.register_mac(
            mac_address=mac_address,
            device_id=device_id,
            interface_name=interface_name,
            port_id=port_id,
            device_type=device_type,
            description=description,
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "mac_address": entry["mac_address"],
            "device_id": entry["device_id"],
            "interface_name": entry["interface_name"],
            "port_id": entry["port_id"],
            "vendor": entry["vendor"],
            "oui": entry["oui"],
            "device_type": entry["device_type"],
            "description": entry["description"],
            "first_seen": entry["first_seen"],
            "last_seen": entry["last_seen"],
            "status": entry["status"],
        }

    async def lookup_mac(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Lookup MAC address in registry."""
        try:
            normalized_mac = self._service._normalize_mac(mac_address)
        except NetworkingError:
            return None

        entry = self._service._mac_entries.get(normalized_mac)
        if not entry:
            return None

        return {
            "mac_address": entry["mac_address"],
            "device_id": entry["device_id"],
            "interface_name": entry["interface_name"],
            "port_id": entry["port_id"],
            "vendor": entry["vendor"],
            "oui": entry["oui"],
            "device_type": entry["device_type"],
            "description": entry["description"],
            "first_seen": entry["first_seen"],
            "last_seen": entry["last_seen"],
            "status": entry["status"],
            "metadata": entry["metadata"],
        }

    async def update_mac_seen(self, mac_address: str) -> Dict[str, Any]:
        """Update last seen timestamp for MAC address."""
        entry = await self._service.update_mac_seen(mac_address)

        return {
            "mac_address": entry["mac_address"],
            "last_seen": entry["last_seen"],
            "status": "updated",
        }

    async def get_device_macs(self, device_id: str) -> List[Dict[str, Any]]:
        """Get all MAC addresses for a device."""
        mac_addresses = self._service._device_macs.get(device_id, [])

        return [
            {
                "mac_address": mac,
                "interface_name": self._service._mac_entries[mac]["interface_name"],
                "port_id": self._service._mac_entries[mac]["port_id"],
                "vendor": self._service._mac_entries[mac]["vendor"],
                "device_type": self._service._mac_entries[mac]["device_type"],
                "last_seen": self._service._mac_entries[mac]["last_seen"],
                "status": self._service._mac_entries[mac]["status"],
            }
            for mac in mac_addresses
            if mac in self._service._mac_entries
        ]

    async def search_macs_by_vendor(self, vendor: str) -> List[Dict[str, Any]]:
        """Search MAC addresses by vendor."""
        matching_entries = [
            entry
            for entry in self._service._mac_entries.values()
            if vendor.lower() in entry["vendor"].lower()
        ]

        return [
            {
                "mac_address": entry["mac_address"],
                "device_id": entry["device_id"],
                "vendor": entry["vendor"],
                "device_type": entry["device_type"],
                "last_seen": entry["last_seen"],
                "status": entry["status"],
            }
            for entry in matching_entries
        ]

    async def get_mac_statistics(self) -> Dict[str, Any]:
        """Get MAC registry statistics."""
        total_macs = len(self._service._mac_entries)
        active_macs = sum(
            1
            for entry in self._service._mac_entries.values()
            if entry["status"] == "active"
        )

        vendor_counts = {}
        for entry in self._service._mac_entries.values():
            vendor = entry["vendor"]
            vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1

        return {
            "total_macs": total_macs,
            "active_macs": active_macs,
            "inactive_macs": total_macs - active_macs,
            "vendor_distribution": vendor_counts,
            "unique_vendors": len(vendor_counts),
        }
