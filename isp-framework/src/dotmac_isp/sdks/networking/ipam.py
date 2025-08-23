"""
IPAM SDK - IP Address Management with allocation, reservation, and conflict detection
"""

import ipaddress
from datetime import datetime, timedelta
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import IPAddressConflictError, IPAMError


class IPAMService:
    """In-memory service for IPAM operations."""

    def __init__(self):
        self._networks: Dict[str, Dict[str, Any]] = {}
        self._allocations: Dict[str, Dict[str, Any]] = {}
        self._reservations: Dict[str, Dict[str, Any]] = {}
        self._ip_index: Dict[str, str] = {}  # ip_address -> allocation_id

    async def create_network(self, **kwargs) -> Dict[str, Any]:
        """Create IP network/subnet."""
        network_id = kwargs.get("network_id") or str(uuid4())
        cidr = kwargs["cidr"]

        # Validate CIDR
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError as e:
            raise IPAMError(f"Invalid CIDR: {cidr} - {e}")

        if network_id in self._networks:
            raise IPAMError(f"Network already exists: {network_id}")

        net_data = {
            "network_id": network_id,
            "cidr": str(network),
            "network_type": kwargs.get("network_type", "customer"),
            "vlan_id": kwargs.get("vlan_id"),
            "site_id": kwargs.get("site_id"),
            "description": kwargs.get("description", ""),
            "gateway": kwargs.get("gateway"),
            "dns_servers": kwargs.get("dns_servers", []),
            "dhcp_enabled": kwargs.get("dhcp_enabled", False),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._networks[network_id] = net_data
        return net_data

    async def allocate_ip(self, **kwargs) -> Dict[str, Any]:
        """Allocate IP address from network."""
        network_id = kwargs["network_id"]

        if network_id not in self._networks:
            raise IPAMError(f"Network not found: {network_id}")

        network_data = self._networks[network_id]
        network = ipaddress.ip_network(network_data["cidr"])

        # Check for specific IP request
        requested_ip = kwargs.get("ip_address")
        if requested_ip:
            ip_addr = ipaddress.ip_address(requested_ip)
            if ip_addr not in network:
                raise IPAMError(
                    f"IP {requested_ip} not in network {network_data['cidr']}"
                )

            if str(ip_addr) in self._ip_index:
                raise IPAddressConflictError(str(ip_addr))
        else:
            # Find next available IP
            for ip in network.hosts():
                if str(ip) not in self._ip_index:
                    ip_addr = ip
                    break
            else:
                raise IPAMError(f"No available IPs in network {network_data['cidr']}")

        allocation_id = str(uuid4())
        allocation = {
            "allocation_id": allocation_id,
            "network_id": network_id,
            "ip_address": str(ip_addr),
            "allocation_type": kwargs.get("allocation_type", "dynamic"),
            "assigned_to": kwargs.get("assigned_to", ""),
            "description": kwargs.get("description", ""),
            "lease_time": kwargs.get("lease_time", 86400),
            "status": "allocated",
            "created_at": utc_now().isoformat(),
            "expires_at": (
                utc_now() + timedelta(seconds=kwargs.get("lease_time", 86400))
            ).isoformat(),
        }

        self._allocations[allocation_id] = allocation
        self._ip_index[str(ip_addr)] = allocation_id

        return allocation

    async def reserve_ip(self, **kwargs) -> Dict[str, Any]:
        """Reserve IP address for future allocation."""
        network_id = kwargs["network_id"]
        ip_address = kwargs["ip_address"]

        if network_id not in self._networks:
            raise IPAMError(f"Network not found: {network_id}")

        network_data = self._networks[network_id]
        network = ipaddress.ip_network(network_data["cidr"])
        ip_addr = ipaddress.ip_address(ip_address)

        if ip_addr not in network:
            raise IPAMError(f"IP {ip_address} not in network {network_data['cidr']}")

        if str(ip_addr) in self._ip_index:
            raise IPAddressConflictError(str(ip_addr))

        reservation_id = str(uuid4())
        reservation = {
            "reservation_id": reservation_id,
            "network_id": network_id,
            "ip_address": str(ip_addr),
            "reserved_for": kwargs.get("reserved_for", ""),
            "description": kwargs.get("description", ""),
            "reservation_time": kwargs.get("reservation_time", 3600),
            "status": "reserved",
            "created_at": utc_now().isoformat(),
            "expires_at": (
                utc_now() + timedelta(seconds=kwargs.get("reservation_time", 3600))
            ).isoformat(),
        }

        self._reservations[reservation_id] = reservation
        self._ip_index[str(ip_addr)] = f"reserved:{reservation_id}"

        return reservation


class IPAMSDK:
    """Minimal, reusable SDK for IP Address Management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = IPAMService()

    async def create_network(
        self,
        cidr: str,
        network_type: str = "customer",
        vlan_id: Optional[int] = None,
        site_id: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create IP network/subnet."""
        network = await self._service.create_network(
            cidr=cidr,
            network_type=network_type,
            vlan_id=vlan_id,
            site_id=site_id,
            description=description,
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "network_id": network["network_id"],
            "cidr": network["cidr"],
            "network_type": network["network_type"],
            "vlan_id": network["vlan_id"],
            "site_id": network["site_id"],
            "description": network["description"],
            "gateway": network["gateway"],
            "dns_servers": network["dns_servers"],
            "dhcp_enabled": network["dhcp_enabled"],
            "status": network["status"],
            "created_at": network["created_at"],
        }

    async def allocate_ip(
        self,
        network_id: str,
        allocation_type: str = "dynamic",
        assigned_to: Optional[str] = None,
        ip_address: Optional[str] = None,
        lease_time: int = 86400,
        **kwargs,
    ) -> Dict[str, Any]:
        """Allocate IP address from network."""
        allocation = await self._service.allocate_ip(
            network_id=network_id,
            allocation_type=allocation_type,
            assigned_to=assigned_to,
            ip_address=ip_address,
            lease_time=lease_time,
            **kwargs,
        )

        return {
            "allocation_id": allocation["allocation_id"],
            "network_id": allocation["network_id"],
            "ip_address": allocation["ip_address"],
            "allocation_type": allocation["allocation_type"],
            "assigned_to": allocation["assigned_to"],
            "lease_time": allocation["lease_time"],
            "status": allocation["status"],
            "created_at": allocation["created_at"],
            "expires_at": allocation["expires_at"],
        }

    async def reserve_ip(
        self,
        network_id: str,
        ip_address: str,
        reserved_for: Optional[str] = None,
        reservation_time: int = 3600,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reserve IP address for future allocation."""
        reservation = await self._service.reserve_ip(
            network_id=network_id,
            ip_address=ip_address,
            reserved_for=reserved_for,
            reservation_time=reservation_time,
            description=description,
        )

        return {
            "reservation_id": reservation["reservation_id"],
            "network_id": reservation["network_id"],
            "ip_address": reservation["ip_address"],
            "reserved_for": reservation["reserved_for"],
            "reservation_time": reservation["reservation_time"],
            "status": reservation["status"],
            "created_at": reservation["created_at"],
            "expires_at": reservation["expires_at"],
        }

    async def release_ip(self, allocation_id: str) -> Dict[str, Any]:
        """Release allocated IP address."""
        if allocation_id not in self._service._allocations:
            raise IPAMError(f"Allocation not found: {allocation_id}")

        allocation = self._service._allocations[allocation_id]
        ip_address = allocation["ip_address"]

        # Remove from index and allocations
        del self._service._ip_index[ip_address]
        del self._service._allocations[allocation_id]

        return {
            "allocation_id": allocation_id,
            "ip_address": ip_address,
            "status": "released",
            "released_at": utc_now().isoformat(),
        }

    async def get_network_utilization(self, network_id: str) -> Dict[str, Any]:
        """Get network utilization statistics."""
        if network_id not in self._service._networks:
            raise IPAMError(f"Network not found: {network_id}")

        network_data = self._service._networks[network_id]
        network = ipaddress.ip_network(network_data["cidr"])

        total_ips = network.num_addresses - 2  # Exclude network and broadcast
        allocated_ips = sum(
            1
            for alloc in self._service._allocations.values()
            if alloc["network_id"] == network_id and alloc["status"] == "allocated"
        )
        reserved_ips = sum(
            1
            for res in self._service._reservations.values()
            if res["network_id"] == network_id and res["status"] == "reserved"
        )

        available_ips = total_ips - allocated_ips - reserved_ips
        utilization_percent = (
            ((allocated_ips + reserved_ips) / total_ips) * 100 if total_ips > 0 else 0
        )

        return {
            "network_id": network_id,
            "cidr": network_data["cidr"],
            "total_ips": total_ips,
            "allocated_ips": allocated_ips,
            "reserved_ips": reserved_ips,
            "available_ips": available_ips,
            "utilization_percent": round(utilization_percent, 2),
        }

    async def get_allocations_by_network(self, network_id: str) -> List[Dict[str, Any]]:
        """Get all allocations for a network."""
        allocations = [
            alloc
            for alloc in self._service._allocations.values()
            if alloc["network_id"] == network_id
        ]

        return [
            {
                "allocation_id": alloc["allocation_id"],
                "ip_address": alloc["ip_address"],
                "allocation_type": alloc["allocation_type"],
                "assigned_to": alloc["assigned_to"],
                "status": alloc["status"],
                "created_at": alloc["created_at"],
                "expires_at": alloc["expires_at"],
            }
            for alloc in allocations
        ]

    async def check_ip_availability(
        self, network_id: str, ip_address: str
    ) -> Dict[str, Any]:
        """Check if IP address is available for allocation."""
        if network_id not in self._service._networks:
            raise IPAMError(f"Network not found: {network_id}")

        network_data = self._service._networks[network_id]
        network = ipaddress.ip_network(network_data["cidr"])

        try:
            ip_addr = ipaddress.ip_address(ip_address)
        except ValueError:
            raise IPAMError(f"Invalid IP address: {ip_address}")

        if ip_addr not in network:
            return {
                "ip_address": ip_address,
                "available": False,
                "reason": f"IP not in network {network_data['cidr']}",
            }

        if str(ip_addr) in self._service._ip_index:
            allocation_ref = self._service._ip_index[str(ip_addr)]
            if allocation_ref.startswith("reserved:"):
                return {
                    "ip_address": ip_address,
                    "available": False,
                    "reason": "IP is reserved",
                }
            else:
                return {
                    "ip_address": ip_address,
                    "available": False,
                    "reason": "IP is allocated",
                }

        return {
            "ip_address": ip_address,
            "available": True,
            "reason": "IP is available for allocation",
        }
