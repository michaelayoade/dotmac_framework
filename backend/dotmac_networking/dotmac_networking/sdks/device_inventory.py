"""
Device Inventory SDK - devices, modules, interfaces; stable portId = {deviceId}:{ifName}
"""

from datetime import datetime
from dotmac_networking.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import DeviceError, DeviceNotFoundError


class DeviceInventoryService:
    """In-memory service for device inventory operations."""

    def __init__(self):
        self._devices: Dict[str, Dict[str, Any]] = {}
        self._modules: Dict[str, List[Dict[str, Any]]] = {}
        self._interfaces: Dict[str, List[Dict[str, Any]]] = {}
        self._site_devices: Dict[str, List[str]] = {}

    async def create_device(self, **kwargs) -> Dict[str, Any]:
        """Create device in inventory."""
        device_id = kwargs.get("device_id") or str(uuid4())

        if device_id in self._devices:
            raise DeviceError(f"Device already exists: {device_id}")

        device = {
            "device_id": device_id,
            "hostname": kwargs.get("hostname", ""),
            "device_type": kwargs.get("device_type", "unknown"),
            "vendor": kwargs.get("vendor", ""),
            "model": kwargs.get("model", ""),
            "serial_number": kwargs.get("serial_number", ""),
            "firmware_version": kwargs.get("firmware_version", ""),
            "management_ip": kwargs.get("management_ip", ""),
            "site_id": kwargs.get("site_id", ""),
            "rack_id": kwargs.get("rack_id", ""),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
            "metadata": kwargs.get("metadata", {}),
        }

        self._devices[device_id] = device
        self._modules[device_id] = []
        self._interfaces[device_id] = []

        # Index by site
        site_id = device.get("site_id")
        if site_id:
            if site_id not in self._site_devices:
                self._site_devices[site_id] = []
            self._site_devices[site_id].append(device_id)

        return device

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device by ID."""
        return self._devices.get(device_id)

    async def add_module(self, device_id: str, **kwargs) -> Dict[str, Any]:
        """Add module to device."""
        if device_id not in self._devices:
            raise DeviceNotFoundError(device_id)

        module = {
            "module_id": kwargs.get("module_id") or str(uuid4()),
            "device_id": device_id,
            "slot": kwargs.get("slot", ""),
            "module_type": kwargs.get("module_type", ""),
            "part_number": kwargs.get("part_number", ""),
            "serial_number": kwargs.get("serial_number", ""),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
        }

        self._modules[device_id].append(module)
        return module

    async def add_interface(self, device_id: str, **kwargs) -> Dict[str, Any]:
        """Add interface to device."""
        if device_id not in self._devices:
            raise DeviceNotFoundError(device_id)

        interface_name = kwargs.get("interface_name", "")
        port_id = f"{device_id}:{interface_name}"  # Stable portId format

        interface = {
            "interface_id": kwargs.get("interface_id") or str(uuid4()),
            "device_id": device_id,
            "port_id": port_id,  # Stable identifier
            "interface_name": interface_name,
            "interface_type": kwargs.get("interface_type", "ethernet"),
            "speed": kwargs.get("speed", ""),
            "duplex": kwargs.get("duplex", "full"),
            "mtu": kwargs.get("mtu", 1500),
            "admin_status": kwargs.get("admin_status", "up"),
            "oper_status": kwargs.get("oper_status", "down"),
            "description": kwargs.get("description", ""),
            "vlan_id": kwargs.get("vlan_id"),
            "ip_address": kwargs.get("ip_address"),
            "mac_address": kwargs.get("mac_address", ""),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._interfaces[device_id].append(interface)
        return interface


class DeviceInventorySDK:
    """Minimal, reusable SDK for device inventory management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = DeviceInventoryService()

    async def create_device(
        self,
        device_id: str,
        hostname: str,
        device_type: str,
        vendor: str,
        model: str,
        management_ip: str,
        site_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create device in inventory."""
        device = await self._service.create_device(
            device_id=device_id,
            hostname=hostname,
            device_type=device_type,
            vendor=vendor,
            model=model,
            management_ip=management_ip,
            site_id=site_id,
            tenant_id=self.tenant_id,
            **kwargs
        )

        return {
            "device_id": device["device_id"],
            "hostname": device["hostname"],
            "device_type": device["device_type"],
            "vendor": device["vendor"],
            "model": device["model"],
            "management_ip": device["management_ip"],
            "site_id": device["site_id"],
            "status": device["status"],
            "created_at": device["created_at"],
        }

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device by ID."""
        device = await self._service.get_device(device_id)
        if not device:
            return None

        return {
            "device_id": device["device_id"],
            "hostname": device["hostname"],
            "device_type": device["device_type"],
            "vendor": device["vendor"],
            "model": device["model"],
            "serial_number": device["serial_number"],
            "firmware_version": device["firmware_version"],
            "management_ip": device["management_ip"],
            "site_id": device["site_id"],
            "rack_id": device["rack_id"],
            "status": device["status"],
            "created_at": device["created_at"],
            "updated_at": device["updated_at"],
            "metadata": device["metadata"],
        }

    async def add_module(
        self,
        device_id: str,
        slot: str,
        module_type: str,
        part_number: str,
        serial_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add module to device."""
        module = await self._service.add_module(
            device_id=device_id,
            slot=slot,
            module_type=module_type,
            part_number=part_number,
            serial_number=serial_number
        )

        return {
            "module_id": module["module_id"],
            "device_id": module["device_id"],
            "slot": module["slot"],
            "module_type": module["module_type"],
            "part_number": module["part_number"],
            "serial_number": module["serial_number"],
            "status": module["status"],
            "created_at": module["created_at"],
        }

    async def add_interface(
        self,
        device_id: str,
        interface_name: str,
        interface_type: str = "ethernet",
        speed: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Add interface to device with stable portId."""
        interface = await self._service.add_interface(
            device_id=device_id,
            interface_name=interface_name,
            interface_type=interface_type,
            speed=speed,
            description=description,
            **kwargs
        )

        return {
            "interface_id": interface["interface_id"],
            "device_id": interface["device_id"],
            "port_id": interface["port_id"],  # Stable {deviceId}:{ifName}
            "interface_name": interface["interface_name"],
            "interface_type": interface["interface_type"],
            "speed": interface["speed"],
            "admin_status": interface["admin_status"],
            "oper_status": interface["oper_status"],
            "description": interface["description"],
            "mac_address": interface["mac_address"],
            "created_at": interface["created_at"],
        }

    async def get_device_interfaces(self, device_id: str) -> List[Dict[str, Any]]:
        """Get all interfaces for a device."""
        interfaces = self._service._interfaces.get(device_id, [])

        return [
            {
                "interface_id": iface["interface_id"],
                "port_id": iface["port_id"],
                "interface_name": iface["interface_name"],
                "interface_type": iface["interface_type"],
                "speed": iface["speed"],
                "admin_status": iface["admin_status"],
                "oper_status": iface["oper_status"],
                "vlan_id": iface["vlan_id"],
                "ip_address": iface["ip_address"],
                "mac_address": iface["mac_address"],
            }
            for iface in interfaces
        ]

    async def get_device_modules(self, device_id: str) -> List[Dict[str, Any]]:
        """Get all modules for a device."""
        modules = self._service._modules.get(device_id, [])

        return [
            {
                "module_id": module["module_id"],
                "slot": module["slot"],
                "module_type": module["module_type"],
                "part_number": module["part_number"],
                "serial_number": module["serial_number"],
                "status": module["status"],
            }
            for module in modules
        ]

    async def update_interface_status(
        self,
        device_id: str,
        interface_name: str,
        admin_status: Optional[str] = None,
        oper_status: Optional[str] = None,
        vlan_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update interface status and configuration."""
        interfaces = self._service._interfaces.get(device_id, [])

        for interface in interfaces:
            if interface["interface_name"] == interface_name:
                if admin_status:
                    interface["admin_status"] = admin_status
                if oper_status:
                    interface["oper_status"] = oper_status
                if vlan_id is not None:
                    interface["vlan_id"] = vlan_id
                if ip_address:
                    interface["ip_address"] = ip_address
                interface["updated_at"] = utc_now().isoformat()

                return {
                    "port_id": interface["port_id"],
                    "admin_status": interface["admin_status"],
                    "oper_status": interface["oper_status"],
                    "vlan_id": interface["vlan_id"],
                    "ip_address": interface["ip_address"],
                    "updated_at": interface["updated_at"],
                }

        raise DeviceError(f"Interface not found: {interface_name} on device {device_id}")

    async def get_port_by_id(self, port_id: str) -> Optional[Dict[str, Any]]:
        """Get interface by stable port ID ({deviceId}:{ifName})."""
        try:
            device_id, interface_name = port_id.split(":", 1)
        except ValueError:
            raise DeviceError(f"Invalid port ID format: {port_id}")

        interfaces = self._service._interfaces.get(device_id, [])

        for interface in interfaces:
            if interface["interface_name"] == interface_name:
                return {
                    "port_id": interface["port_id"],
                    "device_id": interface["device_id"],
                    "interface_name": interface["interface_name"],
                    "interface_type": interface["interface_type"],
                    "admin_status": interface["admin_status"],
                    "oper_status": interface["oper_status"],
                    "vlan_id": interface["vlan_id"],
                    "ip_address": interface["ip_address"],
                    "mac_address": interface["mac_address"],
                }

        return None
