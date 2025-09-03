"""
Device Inventory Management for DotMac Device Management Framework.

Provides comprehensive device inventory tracking with modules, interfaces,
and hardware lifecycle management.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..exceptions import DeviceInventoryError
from .models import (
    Device,
    DeviceInterface,
    DeviceModule,
    DeviceStatus,
    DeviceType,
    InterfaceStatus,
    InterfaceType,
)


class DeviceInventoryManager:
    """Device inventory manager for database operations."""

    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def create_device(
        self,
        device_id: str,
        hostname: str,
        device_type: str = DeviceType.UNKNOWN,
        vendor: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> Device:
        """Create new device in inventory."""
        # Check if device already exists
        existing = (
            self.session.query(Device)
            .filter(
                and_(Device.device_id == device_id, Device.tenant_id == self.tenant_id)
            )
            .first()
        )

        if existing:
            raise DeviceInventoryError(f"Device already exists: {device_id}")

        device = Device(
            tenant_id=self.tenant_id,
            device_id=device_id,
            hostname=hostname,
            device_type=device_type,
            vendor=vendor,
            model=model,
            serial_number=kwargs.get("serial_number"),
            firmware_version=kwargs.get("firmware_version"),
            management_ip=kwargs.get("management_ip"),
            mac_address=kwargs.get("mac_address"),
            site_id=kwargs.get("site_id"),
            rack_id=kwargs.get("rack_id"),
            rack_unit=kwargs.get("rack_unit"),
            location_description=kwargs.get("location_description"),
            status=kwargs.get("status", DeviceStatus.ACTIVE),
            install_date=kwargs.get("install_date"),
            warranty_end=kwargs.get("warranty_end"),
            device_device_metadata=kwargs.get("metadata", {}),
            properties=kwargs.get("properties", {}),
            created_by=kwargs.get("created_by"),
            updated_by=kwargs.get("updated_by"),
        )

        self.session.add(device)
        self.session.commit()
        return device

    async def get_device(self, device_id: str) -> Optional[Device]:
        """Get device by ID."""
        return (
            self.session.query(Device)
            .filter(
                and_(Device.device_id == device_id, Device.tenant_id == self.tenant_id)
            )
            .first()
        )

    async def update_device(
        self, device_id: str, updates: Dict[str, Any]
    ) -> Optional[Device]:
        """Update device information."""
        device = await self.get_device(device_id)
        if not device:
            return None

        for key, value in updates.items():
            if hasattr(device, key) and key not in [
                "id",
                "tenant_id",
                "device_id",
                "created_at",
            ]:
                setattr(device, key, value)

        device.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        return device

    async def delete_device(self, device_id: str) -> bool:
        """Delete device from inventory."""
        device = await self.get_device(device_id)
        if not device:
            return False

        self.session.delete(device)
        self.session.commit()
        return True

    async def list_devices(
        self,
        site_id: Optional[str] = None,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        vendor: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Device]:
        """List devices with filtering."""
        query = self.session.query(Device).filter(Device.tenant_id == self.tenant_id)

        if site_id:
            query = query.filter(Device.site_id == site_id)
        if device_type:
            query = query.filter(Device.device_type == device_type)
        if status:
            query = query.filter(Device.status == status)
        if vendor:
            query = query.filter(Device.vendor == vendor)

        return query.offset(offset).limit(limit).all()

    async def add_device_module(
        self,
        device_id: str,
        module_id: str,
        slot: str,
        module_type: Optional[str] = None,
        **kwargs,
    ) -> DeviceModule:
        """Add module to device."""
        device = await self.get_device(device_id)
        if not device:
            raise DeviceInventoryError(f"Device not found: {device_id}")

        # Check if module already exists
        existing = (
            self.session.query(DeviceModule)
            .filter(
                and_(
                    DeviceModule.module_id == module_id,
                    DeviceModule.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

        if existing:
            raise DeviceInventoryError(f"Module already exists: {module_id}")

        module = DeviceModule(
            tenant_id=self.tenant_id,
            module_id=module_id,
            device_id=device_id,
            slot=slot,
            module_type=module_type,
            part_number=kwargs.get("part_number"),
            serial_number=kwargs.get("serial_number"),
            firmware_version=kwargs.get("firmware_version"),
            status=kwargs.get("status", "active"),
            device_device_metadata=kwargs.get("metadata", {}),
        )

        self.session.add(module)
        self.session.commit()
        return module

    async def add_device_interface(
        self,
        device_id: str,
        interface_id: str,
        interface_name: str,
        interface_type: str = InterfaceType.ETHERNET,
        **kwargs,
    ) -> DeviceInterface:
        """Add interface to device."""
        device = await self.get_device(device_id)
        if not device:
            raise DeviceInventoryError(f"Device not found: {device_id}")

        # Generate stable port ID
        port_id = f"{device_id}:{interface_name}"

        # Check if interface already exists
        existing = (
            self.session.query(DeviceInterface)
            .filter(
                and_(
                    DeviceInterface.interface_id == interface_id,
                    DeviceInterface.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

        if existing:
            raise DeviceInventoryError(f"Interface already exists: {interface_id}")

        interface = DeviceInterface(
            tenant_id=self.tenant_id,
            interface_id=interface_id,
            device_id=device_id,
            port_id=port_id,
            interface_name=interface_name,
            interface_type=interface_type,
            speed=kwargs.get("speed"),
            duplex=kwargs.get("duplex", "full"),
            mtu=kwargs.get("mtu", 1500),
            admin_status=kwargs.get("admin_status", InterfaceStatus.UP),
            oper_status=kwargs.get("oper_status", InterfaceStatus.DOWN),
            description=kwargs.get("description"),
            vlan_id=kwargs.get("vlan_id"),
            ip_address=kwargs.get("ip_address"),
            subnet_mask=kwargs.get("subnet_mask"),
            mac_address=kwargs.get("mac_address"),
            last_input=kwargs.get("last_input"),
            last_output=kwargs.get("last_output"),
            input_rate=kwargs.get("input_rate", 0.0),
            output_rate=kwargs.get("output_rate", 0.0),
            device_device_metadata=kwargs.get("metadata", {}),
        )

        self.session.add(interface)
        self.session.commit()
        return interface

    async def get_device_interfaces(self, device_id: str) -> List[DeviceInterface]:
        """Get all interfaces for a device."""
        return (
            self.session.query(DeviceInterface)
            .filter(
                and_(
                    DeviceInterface.device_id == device_id,
                    DeviceInterface.tenant_id == self.tenant_id,
                )
            )
            .all()
        )

    async def get_device_modules(self, device_id: str) -> List[DeviceModule]:
        """Get all modules for a device."""
        return (
            self.session.query(DeviceModule)
            .filter(
                and_(
                    DeviceModule.device_id == device_id,
                    DeviceModule.tenant_id == self.tenant_id,
                )
            )
            .all()
        )

    async def update_interface_status(
        self,
        interface_id: str,
        admin_status: Optional[str] = None,
        oper_status: Optional[str] = None,
        input_rate: Optional[float] = None,
        output_rate: Optional[float] = None,
    ) -> Optional[DeviceInterface]:
        """Update interface status and statistics."""
        interface = (
            self.session.query(DeviceInterface)
            .filter(
                and_(
                    DeviceInterface.interface_id == interface_id,
                    DeviceInterface.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

        if not interface:
            return None

        if admin_status:
            interface.admin_status = admin_status
        if oper_status:
            interface.oper_status = oper_status
        if input_rate is not None:
            interface.input_rate = input_rate
            interface.last_input = datetime.now(timezone.utc)
        if output_rate is not None:
            interface.output_rate = output_rate
            interface.last_output = datetime.now(timezone.utc)

        interface.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        return interface

    async def search_devices(self, query: str) -> List[Device]:
        """Search devices by hostname, IP, or serial number."""
        search_filter = or_(
            Device.hostname.ilike(f"%{query}%"),
            Device.management_ip.ilike(f"%{query}%"),
            Device.serial_number.ilike(f"%{query}%"),
            Device.device_id.ilike(f"%{query}%"),
        )

        return (
            self.session.query(Device)
            .filter(and_(Device.tenant_id == self.tenant_id, search_filter))
            .all()
        )

    async def get_device_count_by_type(self) -> Dict[str, int]:
        """Get device count grouped by type."""
        from sqlalchemy import func

        results = (
            self.session.query(Device.device_type, func.count(Device.id))
            .filter(Device.tenant_id == self.tenant_id)
            .group_by(Device.device_type)
            .all()
        )

        return {device_type: count for device_type, count in results}

    async def get_devices_by_site(self, site_id: str) -> List[Device]:
        """Get all devices for a specific site."""
        return (
            self.session.query(Device)
            .filter(and_(Device.site_id == site_id, Device.tenant_id == self.tenant_id))
            .all()
        )


class DeviceInventoryService:
    """High-level service for device inventory operations."""

    def __init__(self, session: Session, tenant_id: str):
        self.manager = DeviceInventoryManager(session, tenant_id)
        self.tenant_id = tenant_id

    async def provision_device(
        self, device_id: str, hostname: str, device_type: str, site_id: str, **kwargs
    ) -> Dict[str, Any]:
        """Provision a new device with full setup."""
        # Create device
        device = await self.manager.create_device(
            device_id=device_id,
            hostname=hostname,
            device_type=device_type,
            site_id=site_id,
            status=DeviceStatus.PROVISIONING,
            **kwargs,
        )

        # If interfaces are provided, add them
        interfaces_data = kwargs.get("interfaces", [])
        interfaces = []
        for iface_data in interfaces_data:
            interface = await self.manager.add_device_interface(
                device_id=device_id,
                interface_id=f"{device_id}_{iface_data['name']}",
                interface_name=iface_data["name"],
                interface_type=iface_data.get("type", InterfaceType.ETHERNET),
                **iface_data,
            )
            interfaces.append(interface)

        # If modules are provided, add them
        modules_data = kwargs.get("modules", [])
        modules = []
        for module_data in modules_data:
            module = await self.manager.add_device_module(
                device_id=device_id,
                module_id=f"{device_id}_{module_data['slot']}",
                slot=module_data["slot"],
                module_type=module_data.get("type"),
                **module_data,
            )
            modules.append(module)

        return {
            "device_id": device.device_id,
            "hostname": device.hostname,
            "device_type": device.device_type,
            "status": device.status,
            "site_id": device.site_id,
            "interfaces_count": len(interfaces),
            "modules_count": len(modules),
            "provisioned_at": device.created_at.isoformat(),
        }

    async def decommission_device(self, device_id: str) -> Dict[str, Any]:
        """Decommission a device."""
        device = await self.manager.get_device(device_id)
        if not device:
            raise DeviceInventoryError(f"Device not found: {device_id}")

        # Update status to decommissioned
        await self.manager.update_device(
            device_id, {"status": DeviceStatus.DECOMMISSIONED}
        )

        return {
            "device_id": device_id,
            "status": "decommissioned",
            "decommissioned_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_device_health_summary(self, device_id: str) -> Dict[str, Any]:
        """Get comprehensive device health summary."""
        device = await self.manager.get_device(device_id)
        if not device:
            return {"error": "Device not found"}

        interfaces = await self.manager.get_device_interfaces(device_id)
        modules = await self.manager.get_device_modules(device_id)

        # Calculate interface status summary
        interface_summary = {
            "total": len(interfaces),
            "up": len([i for i in interfaces if i.oper_status == InterfaceStatus.UP]),
            "down": len(
                [i for i in interfaces if i.oper_status == InterfaceStatus.DOWN]
            ),
            "admin_down": len(
                [i for i in interfaces if i.admin_status == InterfaceStatus.ADMIN_DOWN]
            ),
        }

        # Calculate module status summary
        module_summary = {
            "total": len(modules),
            "active": len([m for m in modules if m.status == "active"]),
            "inactive": len([m for m in modules if m.status != "active"]),
        }

        return {
            "device_id": device_id,
            "hostname": device.hostname,
            "device_type": device.device_type,
            "status": device.status,
            "site_id": device.site_id,
            "interfaces": interface_summary,
            "modules": module_summary,
            "last_updated": device.updated_at.isoformat(),
            "uptime_days": (
                (datetime.now(timezone.utc) - device.created_at).days
                if device.install_date
                else None
            ),
        }
