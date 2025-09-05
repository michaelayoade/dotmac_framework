"""
MAC Address Registry Management for DotMac Device Management Framework.

Provides MAC address tracking, OUI vendor identification, and device association.
"""

import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..exceptions import MacRegistryError
from .models import Device, MacAddress


class MacRegistryManager:
    """MAC address registry manager for database operations."""

    def __init__(self, session: Session, tenant_id: str, timezone):
        self.session = session
        self.tenant_id = tenant_id
        # OUI vendor mappings (sample data - in production this would be from IEEE database)
        self.oui_vendors = {
            "00:50:56": "VMware",
            "00:0C:29": "VMware",
            "00:1B:21": "VMware",
            "08:00:27": "Oracle VirtualBox",
            "00:15:5D": "Microsoft Hyper-V",
            "00:1C:42": "Parallels",
            "00:03:FF": "Microsoft",
            "00:50:C2": "IEEE Registration Authority",
            "AC:DE:48": "Private",
            "00:00:5E": "IANA",
        }

    def _normalize_mac(self, mac_address: str) -> str:
        """Normalize MAC address to standard format (xx:xx:xx:xx:xx:xx)."""
        # Remove any separators and convert to lowercase
        mac = re.sub(r"[:-]", "", mac_address.lower())

        # Validate MAC address length
        if len(mac) != 12:
            raise MacRegistryError(f"Invalid MAC address format: {mac_address}")

        # Validate hex characters
        if not re.match(r"^[0-9a-f]{12}$", mac):
            raise MacRegistryError(f"Invalid MAC address characters: {mac_address}")

        # Format as xx:xx:xx:xx:xx:xx
        return ":".join([mac[i : i + 2] for i in range(0, 12, 2)])

    def _extract_oui(self, mac_address: str) -> str:
        """Extract OUI (first 3 octets) from MAC address."""
        normalized_mac = self._normalize_mac(mac_address)
        return normalized_mac[:8]  # First 3 octets (xx:xx:xx)

    def _get_vendor_from_oui(self, oui: str) -> Optional[str]:
        """Get vendor name from OUI."""
        return self.oui_vendors.get(oui.upper())

    async def register_mac_address(
        self,
        mac_address: str,
        device_id: Optional[str] = None,
        interface_name: Optional[str] = None,
        device_type: str = "unknown",
        **kwargs,
    ) -> MacAddress:
        """Register a new MAC address."""
        try:
            normalized_mac = self._normalize_mac(mac_address)
        except MacRegistryError:
            raise

        # Check if MAC already exists
        existing = (
            self.session.query(MacAddress)
            .filter(
                and_(
                    MacAddress.mac_address == normalized_mac,
                    MacAddress.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

        if existing:
            # Update existing record
            existing.last_seen = datetime.now(timezone.utc)
            existing.seen_count += 1

            # Update device association if provided
            if device_id:
                existing.device_id = device_id
                existing.interface_name = interface_name
                existing.port_id = f"{device_id}:{interface_name}" if interface_name else None
                existing.device_type = device_type

            if kwargs.get("description"):
                existing.description = kwargs["description"]

            existing.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            return existing

        # Extract OUI and get vendor
        oui = self._extract_oui(normalized_mac)
        vendor = self._get_vendor_from_oui(oui)

        # Create new MAC address record
        mac_record = MacAddress(
            tenant_id=self.tenant_id,
            mac_address=normalized_mac,
            oui=oui,
            vendor=vendor or "Unknown",
            device_id=device_id,
            interface_name=interface_name,
            port_id=(f"{device_id}:{interface_name}" if device_id and interface_name else None),
            device_type=device_type,
            description=kwargs.get("description", ""),
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            seen_count=1,
            status=kwargs.get("status", "active"),
            device_device_metadata=kwargs.get("metadata", {}),
        )

        self.session.add(mac_record)
        self.session.commit()
        return mac_record

    async def get_mac_address(self, mac_address: str) -> Optional[MacAddress]:
        """Get MAC address record."""
        try:
            normalized_mac = self._normalize_mac(mac_address)
        except MacRegistryError:
            return None

        return (
            self.session.query(MacAddress)
            .filter(
                and_(
                    MacAddress.mac_address == normalized_mac,
                    MacAddress.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    async def update_mac_address(self, mac_address: str, updates: dict[str, Any]) -> Optional[MacAddress]:
        """Update MAC address record."""
        mac_record = await self.get_mac_address(mac_address)
        if not mac_record:
            return None

        for key, value in updates.items():
            if hasattr(mac_record, key) and key not in [
                "id",
                "tenant_id",
                "mac_address",
                "oui",
                "created_at",
            ]:
                setattr(mac_record, key, value)

        mac_record.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        return mac_record

    async def delete_mac_address(self, mac_address: str) -> bool:
        """Delete MAC address record."""
        mac_record = await self.get_mac_address(mac_address)
        if not mac_record:
            return False

        self.session.delete(mac_record)
        self.session.commit()
        return True

    async def search_mac_addresses(
        self,
        query: str,
        device_id: Optional[str] = None,
        vendor: Optional[str] = None,
        limit: int = 100,
    ) -> list[MacAddress]:
        """Search MAC addresses."""
        search_query = self.session.query(MacAddress).filter(MacAddress.tenant_id == self.tenant_id)

        # Add search filters
        if query:
            search_filter = or_(
                MacAddress.mac_address.ilike(f"%{query}%"),
                MacAddress.vendor.ilike(f"%{query}%"),
                MacAddress.description.ilike(f"%{query}%"),
                MacAddress.device_id.ilike(f"%{query}%"),
            )
            search_query = search_query.filter(search_filter)

        if device_id:
            search_query = search_query.filter(MacAddress.device_id == device_id)

        if vendor:
            search_query = search_query.filter(MacAddress.vendor.ilike(f"%{vendor}%"))

        return search_query.limit(limit).all()

    async def get_device_mac_addresses(self, device_id: str) -> list[MacAddress]:
        """Get all MAC addresses associated with a device."""
        return (
            self.session.query(MacAddress)
            .filter(
                and_(
                    MacAddress.device_id == device_id,
                    MacAddress.tenant_id == self.tenant_id,
                )
            )
            .all()
        )

    async def get_vendor_statistics(self) -> dict[str, int]:
        """Get MAC address count by vendor."""
        results = (
            self.session.query(MacAddress.vendor, func.count(MacAddress.id))
            .filter(MacAddress.tenant_id == self.tenant_id)
            .group_by(MacAddress.vendor)
            .all()
        )

        return dict(results)

    async def get_recent_mac_addresses(self, hours: int = 24) -> list[MacAddress]:
        """Get recently seen MAC addresses."""
        since = datetime.now(timezone.utc) - datetime.timedelta(hours=hours)

        return (
            self.session.query(MacAddress)
            .filter(
                and_(
                    MacAddress.tenant_id == self.tenant_id,
                    MacAddress.last_seen >= since,
                )
            )
            .order_by(MacAddress.last_seen.desc())
            .all()
        )

    async def cleanup_stale_records(self, days_inactive: int = 90) -> int:
        """Clean up stale MAC address records."""
        cutoff_date = datetime.now(timezone.utc) - datetime.timedelta(days=days_inactive)

        deleted_count = (
            self.session.query(MacAddress)
            .filter(
                and_(
                    MacAddress.tenant_id == self.tenant_id,
                    MacAddress.last_seen < cutoff_date,
                    MacAddress.status != "static",  # Don't delete static entries
                )
            )
            .delete()
        )

        self.session.commit()
        return deleted_count


class MacRegistryService:
    """High-level service for MAC address registry operations."""

    def __init__(self, session: Session, tenant_id: str):
        self.manager = MacRegistryManager(session, tenant_id)
        self.tenant_id = tenant_id

    async def discover_device_macs(self, device_id: str, interface_macs: dict[str, str]) -> dict[str, Any]:
        """Discover and register MAC addresses for device interfaces."""
        registered_macs = []
        errors = []

        # Verify device exists
        device = (
            self.manager.session.query(Device)
            .filter(and_(Device.device_id == device_id, Device.tenant_id == self.tenant_id))
            .first()
        )

        if not device:
            raise MacRegistryError(f"Device not found: {device_id}")

        for interface_name, mac_address in interface_macs.items():
            try:
                mac_record = await self.manager.register_mac_address(
                    mac_address=mac_address,
                    device_id=device_id,
                    interface_name=interface_name,
                    device_type=device.device_type,
                    description=f"Interface {interface_name} on {device.hostname}",
                )
                registered_macs.append(
                    {
                        "interface": interface_name,
                        "mac_address": mac_record.mac_address,
                        "vendor": mac_record.vendor,
                        "status": "registered",
                    }
                )
            except Exception as e:
                errors.append(
                    {
                        "interface": interface_name,
                        "mac_address": mac_address,
                        "error": str(e),
                    }
                )

        return {
            "device_id": device_id,
            "registered_count": len(registered_macs),
            "error_count": len(errors),
            "registered_macs": registered_macs,
            "errors": errors,
        }

    async def track_mac_movement(self, mac_address: str, new_device_id: str, new_interface: str) -> dict[str, Any]:
        """Track MAC address movement between devices/interfaces."""
        mac_record = await self.manager.get_mac_address(mac_address)

        if not mac_record:
            return {
                "status": "not_found",
                "message": f"MAC address not found: {mac_address}",
            }

        # Record previous location
        previous_location = {
            "device_id": mac_record.device_id,
            "interface_name": mac_record.interface_name,
            "port_id": mac_record.port_id,
        }

        # Update to new location
        await self.manager.update_mac_address(
            mac_address,
            {
                "device_id": new_device_id,
                "interface_name": new_interface,
                "port_id": f"{new_device_id}:{new_interface}",
                "last_seen": datetime.now(timezone.utc),
            },
        )

        return {
            "status": "moved",
            "mac_address": mac_address,
            "previous_location": previous_location,
            "new_location": {
                "device_id": new_device_id,
                "interface_name": new_interface,
                "port_id": f"{new_device_id}:{new_interface}",
            },
            "moved_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_mac_address_details(self, mac_address: str) -> dict[str, Any]:
        """Get comprehensive MAC address details."""
        mac_record = await self.manager.get_mac_address(mac_address)

        if not mac_record:
            return {
                "status": "not_found",
                "message": f"MAC address not found: {mac_address}",
            }

        # Get associated device details if available
        device_info = None
        if mac_record.device_id:
            device = (
                self.manager.session.query(Device)
                .filter(
                    and_(
                        Device.device_id == mac_record.device_id,
                        Device.tenant_id == self.tenant_id,
                    )
                )
                .first()
            )

            if device:
                device_info = {
                    "device_id": device.device_id,
                    "hostname": device.hostname,
                    "device_type": device.device_type,
                    "site_id": device.site_id,
                    "status": device.status,
                }

        return {
            "mac_address": mac_record.mac_address,
            "oui": mac_record.oui,
            "vendor": mac_record.vendor,
            "device_info": device_info,
            "interface_name": mac_record.interface_name,
            "port_id": mac_record.port_id,
            "device_type": mac_record.device_type,
            "description": mac_record.description,
            "first_seen": mac_record.first_seen.isoformat(),
            "last_seen": mac_record.last_seen.isoformat(),
            "seen_count": mac_record.seen_count,
            "status": mac_record.status,
        }

    async def generate_mac_report(self, report_type: str = "summary") -> dict[str, Any]:
        """Generate MAC address registry report."""
        if report_type == "summary":
            total_macs = self.manager.session.query(MacAddress).filter(MacAddress.tenant_id == self.tenant_id).count()

            vendor_stats = await self.manager.get_vendor_statistics()
            recent_macs = await self.manager.get_recent_mac_addresses(hours=24)

            return {
                "report_type": "summary",
                "total_mac_addresses": total_macs,
                "vendor_breakdown": vendor_stats,
                "recent_activity": {
                    "last_24_hours": len(recent_macs),
                    "recent_macs": [
                        {
                            "mac_address": mac.mac_address,
                            "vendor": mac.vendor,
                            "device_id": mac.device_id,
                            "last_seen": mac.last_seen.isoformat(),
                        }
                        for mac in recent_macs[:10]  # Top 10 recent
                    ],
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        return {"error": f"Unknown report type: {report_type}"}

    async def bulk_register_macs(self, mac_entries: list[dict[str, Any]]) -> dict[str, Any]:
        """Bulk register multiple MAC addresses."""
        results = {"registered": [], "updated": [], "errors": []}

        for entry in mac_entries:
            try:
                mac_address = entry["mac_address"]
                existing = await self.manager.get_mac_address(mac_address)

                if existing:
                    # Update existing
                    await self.manager.update_mac_address(
                        mac_address,
                        {
                            "device_id": entry.get("device_id"),
                            "interface_name": entry.get("interface_name"),
                            "device_type": entry.get("device_type", "unknown"),
                            "description": entry.get("description", ""),
                            "last_seen": datetime.now(timezone.utc),
                        },
                    )
                    results["updated"].append(mac_address)
                else:
                    # Register new
                    await self.manager.register_mac_address(**entry)
                    results["registered"].append(mac_address)

            except Exception as e:
                results["errors"].append(
                    {
                        "mac_address": entry.get("mac_address", "unknown"),
                        "error": str(e),
                    }
                )

        return {
            "total_processed": len(mac_entries),
            "registered_count": len(results["registered"]),
            "updated_count": len(results["updated"]),
            "error_count": len(results["errors"]),
            "results": results,
        }
