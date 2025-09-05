"""
Platform Adapters for Device Management.

Provides adapters to integrate device management with different DotMac platform modules.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..exceptions import DeviceManagementError
from ..services.device_service import DeviceService


class BaseDeviceAdapter(ABC):
    """Base adapter for platform integration."""

    def __init__(self, session: Session, tenant_id: str):
        """Initialize base adapter."""
        self.session = session
        self.tenant_id = tenant_id
        self.device_service = DeviceService(session, tenant_id)

    @abstractmethod
    async def adapt_device_data(self, platform_data: dict[str, Any]) -> dict[str, Any]:
        """Adapt platform-specific device data to standard format."""
        pass

    @abstractmethod
    async def export_device_data(self, device_data: dict[str, Any]) -> dict[str, Any]:
        """Export device data to platform-specific format."""
        pass

    async def create_device_from_platform(
        self, platform_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create device from platform-specific data."""
        try:
            # Adapt platform data to standard format
            adapted_data = await self.adapt_device_data(platform_data)

            # Create device using standard service
            result = await self.device_service.create_device(**adapted_data)

            return result
        except Exception as e:
            raise DeviceManagementError(
                f"Failed to create device from platform data: {str(e)}"
            ) from e

    async def sync_device_to_platform(
        self, device_id: str, platform_config: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Sync device data to platform."""
        try:
            # Get device overview
            device_data = await self.device_service.get_device_overview(device_id)

            if "error" in device_data:
                raise DeviceManagementError(device_data["error"])

            # Export to platform format
            platform_data = await self.export_device_data(device_data)

            return {
                "device_id": device_id,
                "sync_status": "completed",
                "platform_data": platform_data,
            }
        except Exception as e:
            raise DeviceManagementError(
                f"Failed to sync device to platform: {str(e)}"
            ) from e


class ISPDeviceAdapter(BaseDeviceAdapter):
    """Adapter for ISP Framework integration."""

    async def adapt_device_data(self, platform_data: dict[str, Any]) -> dict[str, Any]:
        """Adapt ISP platform device data to standard format."""
        # Map ISP framework fields to device management fields
        adapted_data = {
            "device_id": platform_data.get("device_id"),
            "hostname": platform_data.get("hostname") or platform_data.get("name"),
            "device_type": self._map_isp_device_type(
                platform_data.get("device_type", "unknown")
            ),
            "vendor": platform_data.get("vendor"),
            "model": platform_data.get("model"),
            "serial_number": platform_data.get("serial_number"),
            "firmware_version": platform_data.get("firmware_version"),
            "management_ip": platform_data.get("management_ip"),
            "site_id": platform_data.get("site_id"),
            "status": self._map_isp_status(platform_data.get("status", "unknown")),
            "metadata": {
                "source": "isp_framework",
                "customer_id": platform_data.get("customer_id"),
                "service_tier": platform_data.get("service_tier"),
                "original_data": platform_data,
            },
        }

        # Add ISP-specific properties
        if platform_data.get("subscriber_count"):
            adapted_data["properties"] = {
                "subscriber_count": platform_data["subscriber_count"],
                "bandwidth_capacity": platform_data.get("bandwidth_capacity"),
                "service_areas": platform_data.get("service_areas", []),
            }

        # Handle network interfaces for ISP devices
        if platform_data.get("interfaces"):
            adapted_data["interfaces"] = [
                {
                    "name": iface.get("name"),
                    "type": self._map_interface_type(iface.get("type", "ethernet")),
                    "speed": iface.get("speed"),
                    "description": iface.get("description"),
                    "vlan_id": iface.get("vlan_id"),
                    "ip_address": iface.get("ip_address"),
                    "subnet_mask": iface.get("subnet_mask"),
                }
                for iface in platform_data["interfaces"]
            ]

        return adapted_data

    async def export_device_data(self, device_data: dict[str, Any]) -> dict[str, Any]:
        """Export device data to ISP framework format."""
        device_info = device_data.get("device_info", {})
        health_status = device_data.get("health_status", {})
        connectivity = device_data.get("connectivity", {})

        # Map to ISP framework structure
        exported_data = {
            "device_id": device_info.get("device_id"),
            "hostname": device_info.get("hostname"),
            "device_type": self._map_to_isp_device_type(device_info.get("device_type")),
            "vendor": device_info.get("vendor"),
            "model": device_info.get("model"),
            "status": self._map_to_isp_status(device_info.get("status")),
            "management_ip": device_info.get("management_ip"),
            "site_id": device_info.get("site_id"),
            # ISP-specific fields
            "health_score": health_status.get("health_score", 0),
            "operational_status": health_status.get("health_status", "unknown"),
            "last_health_check": health_status.get("last_check"),
            "connection_count": len(connectivity.get("links", [])),
            "monitoring_enabled": health_status.get("active_monitors", 0) > 0,
            # Network information
            "interfaces": [
                {
                    "interface_id": iface.get("interface_id"),
                    "name": iface.get("name"),
                    "type": iface.get("type"),
                    "operational_status": iface.get("status"),
                    "speed": iface.get("speed"),
                }
                for iface in device_data.get("interfaces", [])
            ],
            # MAC addresses for network tracking
            "mac_addresses": [
                {
                    "mac": mac.get("mac_address"),
                    "interface": mac.get("interface"),
                    "vendor": mac.get("vendor"),
                }
                for mac in device_data.get("mac_addresses", [])
            ],
        }

        return exported_data

    def _map_isp_device_type(self, isp_type: str) -> str:
        """Map ISP device type to standard device type."""
        mapping = {
            "ont": "ont",
            "olt": "olt",
            "switch": "switch",
            "router": "router",
            "cpe": "cable_modem",
            "modem": "cable_modem",
            "gateway": "router",
            "access_point": "access_point",
            "unknown": "unknown",
        }
        return mapping.get(isp_type.lower(), "unknown")

    def _map_to_isp_device_type(self, device_type: str) -> str:
        """Map standard device type to ISP device type."""
        mapping = {
            "ont": "ont",
            "olt": "olt",
            "switch": "switch",
            "router": "router",
            "cable_modem": "cpe",
            "access_point": "access_point",
            "unknown": "unknown",
        }
        return mapping.get(device_type, "unknown")

    def _map_isp_status(self, isp_status: str) -> str:
        """Map ISP status to standard device status."""
        mapping = {
            "online": "active",
            "offline": "inactive",
            "provisioning": "provisioning",
            "maintenance": "maintenance",
            "failed": "failed",
            "decommissioned": "decommissioned",
            "unknown": "inactive",
        }
        return mapping.get(isp_status.lower(), "inactive")

    def _map_to_isp_status(self, device_status: str) -> str:
        """Map standard device status to ISP status."""
        mapping = {
            "active": "online",
            "inactive": "offline",
            "provisioning": "provisioning",
            "maintenance": "maintenance",
            "failed": "failed",
            "decommissioned": "decommissioned",
        }
        return mapping.get(device_status, "offline")

    def _map_interface_type(self, isp_interface_type: str) -> str:
        """Map ISP interface type to standard interface type."""
        mapping = {
            "ethernet": "ethernet",
            "fiber": "fiber",
            "wireless": "wireless",
            "gpon": "fiber",
            "docsis": "ethernet",
            "dsl": "ethernet",
            "serial": "serial",
        }
        return mapping.get(isp_interface_type.lower(), "ethernet")


class ManagementDeviceAdapter(BaseDeviceAdapter):
    """Adapter for Management Platform integration."""

    async def adapt_device_data(self, platform_data: dict[str, Any]) -> dict[str, Any]:
        """Adapt Management platform device data to standard format."""
        adapted_data = {
            "device_id": platform_data.get("device_id")
            or platform_data.get("asset_id"),
            "hostname": platform_data.get("hostname")
            or platform_data.get("asset_name"),
            "device_type": self._map_management_device_type(
                platform_data.get("asset_type", "unknown")
            ),
            "vendor": platform_data.get("vendor") or platform_data.get("manufacturer"),
            "model": platform_data.get("model"),
            "serial_number": platform_data.get("serial_number"),
            "site_id": platform_data.get("location_id") or platform_data.get("site_id"),
            "rack_id": platform_data.get("rack_id"),
            "rack_unit": platform_data.get("rack_unit"),
            "status": self._map_management_status(
                platform_data.get("status", "unknown")
            ),
            "install_date": platform_data.get("install_date"),
            "warranty_end": platform_data.get("warranty_expiry"),
            "metadata": {
                "source": "management_platform",
                "asset_tag": platform_data.get("asset_tag"),
                "cost_center": platform_data.get("cost_center"),
                "owner": platform_data.get("owner"),
                "criticality": platform_data.get("criticality"),
                "original_data": platform_data,
            },
        }

        # Add management-specific properties
        if platform_data.get("power_consumption"):
            adapted_data["properties"] = {
                "power_consumption_watts": platform_data["power_consumption"],
                "power_redundancy": platform_data.get("power_redundancy", False),
                "cooling_requirements": platform_data.get("cooling_requirements"),
                "space_units": platform_data.get("space_units", 1),
            }

        return adapted_data

    async def export_device_data(self, device_data: dict[str, Any]) -> dict[str, Any]:
        """Export device data to Management platform format."""
        device_info = device_data.get("device_info", {})
        health_status = device_data.get("health_status", {})

        # Map to Management platform structure
        exported_data = {
            "asset_id": device_info.get("device_id"),
            "asset_name": device_info.get("hostname"),
            "asset_type": self._map_to_management_device_type(
                device_info.get("device_type")
            ),
            "manufacturer": device_info.get("vendor"),
            "model": device_info.get("model"),
            "serial_number": device_info.get("serial_number"),
            "status": self._map_to_management_status(device_info.get("status")),
            "location_id": device_info.get("site_id"),
            "install_date": device_info.get("install_date"),
            # Management platform specific
            "operational_status": health_status.get("health_status", "unknown"),
            "health_score": health_status.get("health_score", 0),
            "last_monitored": health_status.get("last_check"),
            "alert_count": len(health_status.get("issues", [])),
            "monitoring_enabled": health_status.get("active_monitors", 0) > 0,
            # Asset management fields
            "asset_category": "network_infrastructure",
            "criticality": "medium",  # Default, could be derived from device type
            "lifecycle_stage": self._derive_lifecycle_stage(device_info.get("status")),
            # Component information
            "components": {
                "interfaces": len(device_data.get("interfaces", [])),
                "modules": len(device_data.get("modules", [])),
                "mac_addresses": len(device_data.get("mac_addresses", [])),
            },
        }

        return exported_data

    def _map_management_device_type(self, mgmt_type: str) -> str:
        """Map Management platform asset type to standard device type."""
        mapping = {
            "network_switch": "switch",
            "network_router": "router",
            "firewall": "firewall",
            "wireless_ap": "access_point",
            "server": "server",
            "storage": "server",
            "optical_equipment": "optical",
            "telecom_equipment": "unknown",
            "infrastructure": "unknown",
        }
        return mapping.get(mgmt_type.lower(), "unknown")

    def _map_to_management_device_type(self, device_type: str) -> str:
        """Map standard device type to Management platform asset type."""
        mapping = {
            "switch": "network_switch",
            "router": "network_router",
            "firewall": "firewall",
            "access_point": "wireless_ap",
            "server": "server",
            "optical": "optical_equipment",
            "ont": "telecom_equipment",
            "olt": "telecom_equipment",
            "cable_modem": "telecom_equipment",
            "unknown": "infrastructure",
        }
        return mapping.get(device_type, "infrastructure")

    def _map_management_status(self, mgmt_status: str) -> str:
        """Map Management platform status to standard device status."""
        mapping = {
            "in_service": "active",
            "out_of_service": "inactive",
            "under_maintenance": "maintenance",
            "being_repaired": "maintenance",
            "decommissioned": "decommissioned",
            "disposed": "decommissioned",
            "planning": "provisioning",
            "ordered": "provisioning",
        }
        return mapping.get(mgmt_status.lower(), "inactive")

    def _map_to_management_status(self, device_status: str) -> str:
        """Map standard device status to Management platform status."""
        mapping = {
            "active": "in_service",
            "inactive": "out_of_service",
            "maintenance": "under_maintenance",
            "provisioning": "planning",
            "failed": "out_of_service",
            "decommissioned": "decommissioned",
        }
        return mapping.get(device_status, "out_of_service")

    def _derive_lifecycle_stage(self, device_status: str) -> str:
        """Derive lifecycle stage from device status."""
        mapping = {
            "provisioning": "deployment",
            "active": "production",
            "maintenance": "maintenance",
            "inactive": "maintenance",
            "failed": "maintenance",
            "decommissioned": "retirement",
        }
        return mapping.get(device_status, "production")
