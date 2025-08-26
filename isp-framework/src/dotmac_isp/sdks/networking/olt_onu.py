"""
OLT/ONU SDK - Optical Line Terminal and Optical Network Unit management
"""

from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import NetworkingError


class OltOnuService:
    """In-memory service for OLT/ONU operations."""

    def __init__(self):
        """  Init   operation."""
        self._olts: Dict[str, Dict[str, Any]] = {}
        self._onus: Dict[str, Dict[str, Any]] = {}
        self._pon_ports: Dict[str, List[Dict[str, Any]]] = {}
        self._olt_onus: Dict[str, List[str]] = {}  # olt_id -> onu_ids

    async def register_olt(self, **kwargs) -> Dict[str, Any]:
        """Register OLT device."""
        olt_id = kwargs.get("olt_id") or str(uuid4())

        if olt_id in self._olts:
            raise NetworkingError(f"OLT already registered: {olt_id}")

        olt = {
            "olt_id": olt_id,
            "olt_name": kwargs.get("olt_name", ""),
            "ip_address": kwargs["ip_address"],
            "vendor": kwargs.get("vendor", ""),
            "model": kwargs.get("model", ""),
            "software_version": kwargs.get("software_version", ""),
            "pon_ports": kwargs.get("pon_ports", 16),
            "max_onus_per_port": kwargs.get("max_onus_per_port", 128),
            "snmp_community": kwargs.get("snmp_community", "public"),
            "management_vlan": kwargs.get("management_vlan"),
            "site_id": kwargs.get("site_id"),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._olts[olt_id] = olt
        self._pon_ports[olt_id] = []
        self._olt_onus[olt_id] = []

        # Initialize PON ports
        for port_num in range(1, olt["pon_ports"] + 1):
            pon_port = {
                "port_id": f"{olt_id}:pon{port_num}",
                "port_number": port_num,
                "port_type": "PON",
                "admin_status": "up",
                "oper_status": "up",
                "max_onus": olt["max_onus_per_port"],
                "current_onus": 0,
                "optical_power": kwargs.get("optical_power", -10.0),
                "created_at": utc_now().isoformat(),
            }
            self._pon_ports[olt_id].append(pon_port)

        return olt

    async def register_onu(self, **kwargs) -> Dict[str, Any]:
        """Register ONU device."""
        onu_id = kwargs.get("onu_id") or str(uuid4())
        olt_id = kwargs["olt_id"]

        if olt_id not in self._olts:
            raise NetworkingError(f"OLT not found: {olt_id}")

        if onu_id in self._onus:
            raise NetworkingError(f"ONU already registered: {onu_id}")

        onu = {
            "onu_id": onu_id,
            "olt_id": olt_id,
            "pon_port": kwargs.get("pon_port", 1),
            "onu_index": kwargs.get("onu_index", 1),
            "serial_number": kwargs.get("serial_number", ""),
            "mac_address": kwargs.get("mac_address", ""),
            "vendor": kwargs.get("vendor", ""),
            "model": kwargs.get("model", ""),
            "software_version": kwargs.get("software_version", ""),
            "customer_id": kwargs.get("customer_id", ""),
            "service_profile": kwargs.get("service_profile", ""),
            "vlan_id": kwargs.get("vlan_id"),
            "ip_address": kwargs.get("ip_address", ""),
            "optical_power_rx": kwargs.get("optical_power_rx", -20.0),
            "optical_power_tx": kwargs.get("optical_power_tx", 2.0),
            "distance": kwargs.get("distance", 0),
            "admin_status": kwargs.get("admin_status", "up"),
            "oper_status": kwargs.get("oper_status", "up"),
            "registration_status": kwargs.get("registration_status", "registered"),
            "last_seen": utc_now().isoformat(),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._onus[onu_id] = onu
        self._olt_onus[olt_id].append(onu_id)

        # Update PON port ONU count
        pon_port_idx = onu["pon_port"] - 1
        if pon_port_idx < len(self._pon_ports[olt_id]):
            self._pon_ports[olt_id][pon_port_idx]["current_onus"] += 1

        return onu

    async def provision_onu(self, onu_id: str, **kwargs) -> Dict[str, Any]:
        """Provision ONU with service configuration."""
        if onu_id not in self._onus:
            raise NetworkingError(f"ONU not found: {onu_id}")

        onu = self._onus[onu_id]

        # Update ONU configuration
        onu.update(
            {
                "service_profile": kwargs.get(
                    "service_profile", onu["service_profile"]
                ),
                "vlan_id": kwargs.get("vlan_id", onu["vlan_id"]),
                "ip_address": kwargs.get("ip_address", onu["ip_address"]),
                "bandwidth_profile": kwargs.get("bandwidth_profile", {}),
                "qos_profile": kwargs.get("qos_profile", {}),
                "provisioning_status": "provisioned",
                "updated_at": utc_now().isoformat(),
            }
        )

        return onu


class OltOnuSDK:
    """Minimal, reusable SDK for OLT/ONU management."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = OltOnuService()

    async def register_olt(
        self,
        olt_name: str,
        ip_address: str,
        vendor: str,
        model: str,
        pon_ports: int = 16,
        site_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Register OLT device."""
        olt = await self._service.register_olt(
            olt_name=olt_name,
            ip_address=ip_address,
            vendor=vendor,
            model=model,
            pon_ports=pon_ports,
            site_id=site_id,
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "olt_id": olt["olt_id"],
            "olt_name": olt["olt_name"],
            "ip_address": olt["ip_address"],
            "vendor": olt["vendor"],
            "model": olt["model"],
            "software_version": olt["software_version"],
            "pon_ports": olt["pon_ports"],
            "max_onus_per_port": olt["max_onus_per_port"],
            "site_id": olt["site_id"],
            "status": olt["status"],
            "created_at": olt["created_at"],
        }

    async def register_onu(
        self,
        olt_id: str,
        pon_port: int,
        serial_number: str,
        customer_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Register ONU device."""
        onu = await self._service.register_onu(
            olt_id=olt_id,
            pon_port=pon_port,
            serial_number=serial_number,
            customer_id=customer_id,
            **kwargs,
        )

        return {
            "onu_id": onu["onu_id"],
            "olt_id": onu["olt_id"],
            "pon_port": onu["pon_port"],
            "onu_index": onu["onu_index"],
            "serial_number": onu["serial_number"],
            "mac_address": onu["mac_address"],
            "vendor": onu["vendor"],
            "model": onu["model"],
            "customer_id": onu["customer_id"],
            "vlan_id": onu["vlan_id"],
            "admin_status": onu["admin_status"],
            "oper_status": onu["oper_status"],
            "registration_status": onu["registration_status"],
            "created_at": onu["created_at"],
        }

    async def provision_onu_service(
        self,
        onu_id: str,
        service_profile: str,
        vlan_id: int,
        bandwidth_profile: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Provision ONU with service configuration."""
        onu = await self._service.provision_onu(
            onu_id=onu_id,
            service_profile=service_profile,
            vlan_id=vlan_id,
            bandwidth_profile=bandwidth_profile or {},
            **kwargs,
        )

        return {
            "onu_id": onu["onu_id"],
            "service_profile": onu["service_profile"],
            "vlan_id": onu["vlan_id"],
            "ip_address": onu["ip_address"],
            "bandwidth_profile": onu["bandwidth_profile"],
            "qos_profile": onu["qos_profile"],
            "provisioning_status": onu["provisioning_status"],
            "updated_at": onu["updated_at"],
        }

    async def get_olt(self, olt_id: str) -> Optional[Dict[str, Any]]:
        """Get OLT device by ID."""
        olt = self._service._olts.get(olt_id)
        if not olt:
            return None

        return {
            "olt_id": olt["olt_id"],
            "olt_name": olt["olt_name"],
            "ip_address": olt["ip_address"],
            "vendor": olt["vendor"],
            "model": olt["model"],
            "software_version": olt["software_version"],
            "pon_ports": olt["pon_ports"],
            "max_onus_per_port": olt["max_onus_per_port"],
            "snmp_community": olt["snmp_community"],
            "management_vlan": olt["management_vlan"],
            "site_id": olt["site_id"],
            "status": olt["status"],
            "created_at": olt["created_at"],
            "updated_at": olt["updated_at"],
        }

    async def get_olt_pon_ports(self, olt_id: str) -> List[Dict[str, Any]]:
        """Get PON ports for OLT."""
        pon_ports = self._service._pon_ports.get(olt_id, [])

        return [
            {
                "port_id": port["port_id"],
                "port_number": port["port_number"],
                "port_type": port["port_type"],
                "admin_status": port["admin_status"],
                "oper_status": port["oper_status"],
                "max_onus": port["max_onus"],
                "current_onus": port["current_onus"],
                "optical_power": port["optical_power"],
            }
            for port in pon_ports
        ]

    async def get_olt_onus(self, olt_id: str) -> List[Dict[str, Any]]:
        """Get all ONUs for an OLT."""
        onu_ids = self._service._olt_onus.get(olt_id, [])

        return [
            {
                "onu_id": self._service._onus[onu_id]["onu_id"],
                "pon_port": self._service._onus[onu_id]["pon_port"],
                "onu_index": self._service._onus[onu_id]["onu_index"],
                "serial_number": self._service._onus[onu_id]["serial_number"],
                "customer_id": self._service._onus[onu_id]["customer_id"],
                "service_profile": self._service._onus[onu_id]["service_profile"],
                "vlan_id": self._service._onus[onu_id]["vlan_id"],
                "admin_status": self._service._onus[onu_id]["admin_status"],
                "oper_status": self._service._onus[onu_id]["oper_status"],
                "registration_status": self._service._onus[onu_id][
                    "registration_status"
                ],
                "optical_power_rx": self._service._onus[onu_id]["optical_power_rx"],
                "optical_power_tx": self._service._onus[onu_id]["optical_power_tx"],
                "distance": self._service._onus[onu_id]["distance"],
                "last_seen": self._service._onus[onu_id]["last_seen"],
            }
            for onu_id in onu_ids
            if onu_id in self._service._onus
        ]

    async def get_onu(self, onu_id: str) -> Optional[Dict[str, Any]]:
        """Get ONU by ID."""
        onu = self._service._onus.get(onu_id)
        if not onu:
            return None

        return {
            "onu_id": onu["onu_id"],
            "olt_id": onu["olt_id"],
            "pon_port": onu["pon_port"],
            "onu_index": onu["onu_index"],
            "serial_number": onu["serial_number"],
            "mac_address": onu["mac_address"],
            "vendor": onu["vendor"],
            "model": onu["model"],
            "customer_id": onu["customer_id"],
            "service_profile": onu["service_profile"],
            "vlan_id": onu["vlan_id"],
            "ip_address": onu["ip_address"],
            "optical_power_rx": onu["optical_power_rx"],
            "optical_power_tx": onu["optical_power_tx"],
            "distance": onu["distance"],
            "admin_status": onu["admin_status"],
            "oper_status": onu["oper_status"],
            "registration_status": onu["registration_status"],
            "bandwidth_profile": onu.get("bandwidth_profile", {}),
            "qos_profile": onu.get("qos_profile", {}),
            "last_seen": onu["last_seen"],
            "created_at": onu["created_at"],
            "updated_at": onu["updated_at"],
        }

    async def update_onu_status(
        self,
        onu_id: str,
        admin_status: Optional[str] = None,
        oper_status: Optional[str] = None,
        optical_power_rx: Optional[float] = None,
        optical_power_tx: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Update ONU status and optical parameters."""
        if onu_id not in self._service._onus:
            raise NetworkingError(f"ONU not found: {onu_id}")

        onu = self._service._onus[onu_id]

        if admin_status:
            onu["admin_status"] = admin_status
        if oper_status:
            onu["oper_status"] = oper_status
        if optical_power_rx is not None:
            onu["optical_power_rx"] = optical_power_rx
        if optical_power_tx is not None:
            onu["optical_power_tx"] = optical_power_tx

        onu["last_seen"] = utc_now().isoformat()
        onu["updated_at"] = utc_now().isoformat()

        return {
            "onu_id": onu_id,
            "admin_status": onu["admin_status"],
            "oper_status": onu["oper_status"],
            "optical_power_rx": onu["optical_power_rx"],
            "optical_power_tx": onu["optical_power_tx"],
            "last_seen": onu["last_seen"],
            "updated_at": onu["updated_at"],
        }


class OLTONUSDK:
    """SDK wrapper for OLT/ONU operations."""

    def __init__(self, tenant_id: str):
        """Initialize the SDK."""
        self.tenant_id = tenant_id
        self.service = OltOnuService()

    async def register_olt(self, **kwargs) -> Dict[str, Any]:
        """Register OLT device."""
        return await self.service.register_olt(**kwargs)

    async def register_onu(self, **kwargs) -> Dict[str, Any]:
        """Register ONU device."""
        return await self.service.register_onu(**kwargs)

    async def get_olt_info(self, olt_id: str) -> Dict[str, Any]:
        """Get OLT information."""
        return await self.service.get_olt_info(olt_id)

    async def get_onu_info(self, onu_id: str) -> Dict[str, Any]:
        """Get ONU information."""
        return await self.service.get_onu_info(onu_id)

    async def list_olts(self) -> List[Dict[str, Any]]:
        """List all OLT devices."""
        return await self.service.list_olts()

    async def list_onus_for_olt(self, olt_id: str) -> List[Dict[str, Any]]:
        """List ONUs for specific OLT."""
        return await self.service.list_onus_for_olt(olt_id)

    async def update_onu_status(
        self,
        onu_id: str,
        admin_status: Optional[str] = None,
        oper_status: Optional[str] = None,
        optical_power_rx: Optional[float] = None,
        optical_power_tx: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Update ONU status."""
        return await self.service.update_onu_status(
            onu_id, admin_status, oper_status, optical_power_rx, optical_power_tx
        )
