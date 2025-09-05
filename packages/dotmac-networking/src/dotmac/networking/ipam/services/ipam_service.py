"""
IPAM Service - Core business logic for IP address management.
"""

import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
from uuid import uuid4

from ..core.exceptions import (
    AllocationNotFoundError,
    InsufficientAddressSpaceError,
    IPAddressConflictError,
    IPAMError,
    NetworkNotFoundError,
    NetworkOverlapError,
)
from ..core.models import (
    AllocationStatus,
    IPAllocation,
    IPNetwork,
    IPReservation,
    NetworkType,
    ReservationStatus,
)

MODELS_AVAILABLE = True

from sqlalchemy.orm import Session

SQLALCHEMY_AVAILABLE = True


class IPAMService:
    """Core IPAM service with database persistence."""

    def __init__(
        self, database_session: Optional[Session] = None, config: Optional[dict] = None
    ):
        """Initialize IPAM service with optional database session."""
        self.db = database_session
        self.config = config or {}
        self._in_memory_networks = {}
        self._in_memory_allocations = {}
        self._in_memory_reservations = {}
        self._in_memory_ip_index = {}

        # Configuration defaults
        self.default_lease_time = self.config.get("allocation", {}).get(
            "default_lease_time", 86400
        )
        self.max_lease_time = self.config.get("allocation", {}).get(
            "max_lease_time", 2592000
        )
        self.default_reservation_time = self.config.get("reservation", {}).get(
            "default_reservation_time", 3600
        )
        self.auto_release_expired = self.config.get("allocation", {}).get(
            "auto_release_expired", True
        )
        self.conflict_detection = self.config.get("allocation", {}).get(
            "conflict_detection", True
        )

    def _use_database(self) -> bool:
        """Check if database operations should be used."""
        return SQLALCHEMY_AVAILABLE and MODELS_AVAILABLE and self.db is not None

    def _utc_now(self) -> datetime:
        """Get current UTC datetime."""
        return datetime.now(timezone.utc)

    async def create_network(self, tenant_id: str, **kwargs) -> dict[str, Any]:
        """Create IP network/subnet."""
        network_id = kwargs.get("network_id") or str(uuid4())
        cidr = kwargs["cidr"]

        # Validate CIDR
        network = ipaddress.ip_network(cidr, strict=False)

        # Check for existing network
        if self._use_database():
            existing = (
                self.db.query(IPNetwork)
                .filter(
                    IPNetwork.tenant_id == tenant_id, IPNetwork.network_id == network_id
                )
                .first()
            )
            if existing:
                raise IPAMError(f"Network already exists: {network_id}")
        else:
            if network_id in self._in_memory_networks:
                raise IPAMError(f"Network already exists: {network_id}")

        # Check for network overlaps if configured
        if not self.config.get("network", {}).get("allow_overlapping_networks", False):
            overlapping = await self._check_network_overlap(tenant_id, str(network))
            if overlapping:
                raise NetworkOverlapError(str(network), overlapping)

        network_data = {
            "network_id": network_id,
            "tenant_id": tenant_id,
            "network_name": kwargs.get("network_name"),
            "description": kwargs.get("description"),
            "cidr": str(network),
            "network_type": kwargs.get(
                "network_type", NetworkType.CUSTOMER if MODELS_AVAILABLE else "customer"
            ),
            "gateway": kwargs.get("gateway"),
            "dns_servers": kwargs.get("dns_servers", []),
            "dhcp_enabled": kwargs.get(
                "dhcp_enabled",
                self.config.get("network", {}).get("default_dhcp_enabled", False),
            ),
            "site_id": kwargs.get("site_id"),
            "vlan_id": kwargs.get("vlan_id"),
            "location": kwargs.get("location"),
            "tags": kwargs.get("tags", {}),
            "is_active": True,
            "created_at": self._utc_now(),
            "updated_at": self._utc_now(),
        }

        if self._use_database():
            network_obj = IPNetwork(**network_data)
            self.db.add(network_obj)
            self.db.commit()
            self.db.refresh(network_obj)
            return self._network_to_dict(network_obj)
        else:
            self._in_memory_networks[network_id] = network_data
            return network_data

    async def allocate_ip(self, tenant_id: str, **kwargs) -> dict[str, Any]:
        """Allocate IP address from network."""
        network_id = kwargs["network_id"]

        # Get network
        network_data = await self._get_network(tenant_id, network_id)
        if not network_data:
            raise NetworkNotFoundError(network_id)

        network = ipaddress.ip_network(network_data["cidr"])

        # Check for specific IP request
        requested_ip = kwargs.get("ip_address")
        if requested_ip:
            ip_addr = ipaddress.ip_address(requested_ip)
            if ip_addr not in network:
                raise IPAMError(
                    f"IP {requested_ip} not in network {network_data['cidr']}"
                )

            if self.conflict_detection and await self._check_ip_conflict(
                tenant_id, str(ip_addr)
            ):
                raise IPAddressConflictError(str(ip_addr))
        else:
            # Find next available IP
            ip_addr = await self._find_next_available_ip(tenant_id, network)
            if not ip_addr:
                raise InsufficientAddressSpaceError(network_id)

        allocation_id = str(uuid4())
        lease_time = min(
            kwargs.get("lease_time", self.default_lease_time), self.max_lease_time
        )

        allocation_data = {
            "allocation_id": allocation_id,
            "tenant_id": tenant_id,
            "network_id": (
                network_data.get("id") if self._use_database() else network_id
            ),
            "ip_address": str(ip_addr),
            "allocation_type": kwargs.get("allocation_type", "dynamic"),
            "allocation_status": (
                AllocationStatus.ALLOCATED if MODELS_AVAILABLE else "allocated"
            ),
            "assigned_to": kwargs.get("assigned_to"),
            "assigned_resource_id": kwargs.get("assigned_resource_id"),
            "assigned_resource_type": kwargs.get("assigned_resource_type"),
            "lease_time": lease_time,
            "hostname": kwargs.get("hostname"),
            "mac_address": kwargs.get("mac_address"),
            "description": kwargs.get("description"),
            "tags": kwargs.get("tags", {}),
            "allocated_at": self._utc_now(),
            "expires_at": self._utc_now() + timedelta(seconds=lease_time),
            "created_at": self._utc_now(),
            "updated_at": self._utc_now(),
        }

        if self._use_database():
            allocation_obj = IPAllocation(**allocation_data)
            self.db.add(allocation_obj)
            self.db.commit()
            self.db.refresh(allocation_obj)
            return self._allocation_to_dict(allocation_obj)
        else:
            self._in_memory_allocations[allocation_id] = allocation_data
            self._in_memory_ip_index[str(ip_addr)] = allocation_id
            return allocation_data

    async def reserve_ip(self, tenant_id: str, **kwargs) -> dict[str, Any]:
        """Reserve IP address for future allocation."""
        network_id = kwargs["network_id"]
        ip_address = kwargs["ip_address"]

        # Get network
        network_data = await self._get_network(tenant_id, network_id)
        if not network_data:
            raise NetworkNotFoundError(network_id)

        network = ipaddress.ip_network(network_data["cidr"])
        ip_addr = ipaddress.ip_address(ip_address)

        if ip_addr not in network:
            raise IPAMError(f"IP {ip_address} not in network {network_data['cidr']}")

        if self.conflict_detection and await self._check_ip_conflict(
            tenant_id, str(ip_addr)
        ):
            raise IPAddressConflictError(str(ip_addr))

        reservation_id = str(uuid4())
        reservation_time = min(
            kwargs.get("reservation_time", self.default_reservation_time),
            self.config.get("reservation", {}).get("max_reservation_time", 86400),
        )

        reservation_data = {
            "reservation_id": reservation_id,
            "tenant_id": tenant_id,
            "network_id": (
                network_data.get("id") if self._use_database() else network_id
            ),
            "ip_address": str(ip_addr),
            "reservation_status": (
                ReservationStatus.RESERVED if MODELS_AVAILABLE else "reserved"
            ),
            "reserved_for": kwargs.get("reserved_for"),
            "reserved_resource_id": kwargs.get("reserved_resource_id"),
            "reserved_resource_type": kwargs.get("reserved_resource_type"),
            "reservation_time": reservation_time,
            "priority": kwargs.get("priority", 0),
            "description": kwargs.get("description"),
            "tags": kwargs.get("tags", {}),
            "reserved_at": self._utc_now(),
            "expires_at": self._utc_now() + timedelta(seconds=reservation_time),
            "created_at": self._utc_now(),
            "updated_at": self._utc_now(),
        }

        if self._use_database():
            reservation_obj = IPReservation(**reservation_data)
            self.db.add(reservation_obj)
            self.db.commit()
            self.db.refresh(reservation_obj)
            return self._reservation_to_dict(reservation_obj)
        else:
            self._in_memory_reservations[reservation_id] = reservation_data
            self._in_memory_ip_index[str(ip_addr)] = f"reserved:{reservation_id}"
            return reservation_data

    async def release_allocation(
        self, tenant_id: str, allocation_id: str
    ) -> dict[str, Any]:
        """Release allocated IP address."""
        if self._use_database():
            allocation = (
                self.db.query(IPAllocation)
                .filter(
                    IPAllocation.tenant_id == tenant_id,
                    IPAllocation.allocation_id == allocation_id,
                )
                .first()
            )
            if not allocation:
                raise AllocationNotFoundError(allocation_id)

            allocation.allocation_status = AllocationStatus.RELEASED
            allocation.released_at = self._utc_now()
            allocation.updated_at = self._utc_now()

            self.db.commit()
            return self._allocation_to_dict(allocation)
        else:
            if allocation_id not in self._in_memory_allocations:
                raise AllocationNotFoundError(allocation_id)

            allocation = self._in_memory_allocations[allocation_id]
            ip_address = allocation["ip_address"]

            # Remove from index and update status
            if ip_address in self._in_memory_ip_index:
                del self._in_memory_ip_index[ip_address]

            allocation["allocation_status"] = "released"
            allocation["released_at"] = self._utc_now()
            allocation["updated_at"] = self._utc_now()

            return allocation

    async def get_network_utilization(
        self, tenant_id: str, network_id: str
    ) -> dict[str, Any]:
        """Get network utilization statistics."""
        network_data = await self._get_network(tenant_id, network_id)
        if not network_data:
            raise NetworkNotFoundError(network_id)

        network = ipaddress.ip_network(network_data["cidr"])
        total_addresses = network.num_addresses
        usable_addresses = (
            max(0, network.num_addresses - 2)
            if network.prefixlen < 30
            else network.num_addresses
        )

        if self._use_database():
            allocated_count = (
                self.db.query(IPAllocation)
                .filter(
                    IPAllocation.tenant_id == tenant_id,
                    IPAllocation.network_id == network_data["id"],
                    IPAllocation.allocation_status == AllocationStatus.ALLOCATED,
                )
                .count()
            )

            reserved_count = (
                self.db.query(IPReservation)
                .filter(
                    IPReservation.tenant_id == tenant_id,
                    IPReservation.network_id == network_data["id"],
                    IPReservation.reservation_status == ReservationStatus.RESERVED,
                )
                .count()
            )
        else:
            allocated_count = sum(
                1
                for alloc in self._in_memory_allocations.values()
                if alloc["network_id"] == network_id
                and alloc["allocation_status"] == "allocated"
            )
            reserved_count = sum(
                1
                for res in self._in_memory_reservations.values()
                if res["network_id"] == network_id
                and res["reservation_status"] == "reserved"
            )

        available_addresses = usable_addresses - allocated_count - reserved_count
        utilization_percent = (
            ((allocated_count + reserved_count) / usable_addresses * 100)
            if usable_addresses > 0
            else 0
        )

        return {
            "network_id": network_id,
            "network_name": network_data.get("network_name"),
            "cidr": network_data["cidr"],
            "network_type": network_data["network_type"],
            "total_addresses": total_addresses,
            "usable_addresses": usable_addresses,
            "allocated_addresses": allocated_count,
            "reserved_addresses": reserved_count,
            "available_addresses": available_addresses,
            "utilization_percent": round(utilization_percent, 2),
        }

    # Helper methods

    async def _get_network(
        self, tenant_id: str, network_id: str
    ) -> Optional[dict[str, Any]]:
        """Get network by ID and tenant."""
        if self._use_database():
            network = (
                self.db.query(IPNetwork)
                .filter(
                    IPNetwork.tenant_id == tenant_id,
                    IPNetwork.network_id == network_id,
                    IPNetwork.is_active is True,
                )
                .first()
            )
            return self._network_to_dict(network) if network else None
        else:
            return self._in_memory_networks.get(network_id)

    async def _check_network_overlap(self, tenant_id: str, cidr: str) -> Optional[str]:
        """Check for overlapping networks."""
        new_network = ipaddress.ip_network(cidr)

        if self._use_database():
            networks = (
                self.db.query(IPNetwork)
                .filter(IPNetwork.tenant_id == tenant_id, IPNetwork.is_active is True)
                .all()
            )

            for network in networks:
                existing_network = ipaddress.ip_network(network.cidr)
                if new_network.overlaps(existing_network):
                    return network.cidr
        else:
            for network_data in self._in_memory_networks.values():
                if network_data.get("tenant_id") == tenant_id:
                    existing_network = ipaddress.ip_network(network_data["cidr"])
                    if new_network.overlaps(existing_network):
                        return network_data["cidr"]

        return None

    async def _check_ip_conflict(self, tenant_id: str, ip_address: str) -> bool:
        """Check if IP address is already allocated or reserved."""
        if self._use_database():
            # Check allocations
            allocation = (
                self.db.query(IPAllocation)
                .filter(
                    IPAllocation.tenant_id == tenant_id,
                    IPAllocation.ip_address == ip_address,
                    IPAllocation.allocation_status == AllocationStatus.ALLOCATED,
                )
                .first()
            )
            if allocation:
                return True

            # Check reservations
            reservation = (
                self.db.query(IPReservation)
                .filter(
                    IPReservation.tenant_id == tenant_id,
                    IPReservation.ip_address == ip_address,
                    IPReservation.reservation_status == ReservationStatus.RESERVED,
                )
                .first()
            )
            return reservation is not None
        else:
            return ip_address in self._in_memory_ip_index

    async def _find_next_available_ip(
        self,
        tenant_id: str,
        network: Union[ipaddress.IPv4Network, ipaddress.IPv6Network],
    ) -> Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        """Find next available IP in network using optimized batch scanning."""
        if self._use_database():
            return await self._find_next_available_ip_batch(tenant_id, network)
        else:
            return await self._find_next_available_ip_sequential(tenant_id, network)

    async def _find_next_available_ip_batch(
        self,
        tenant_id: str,
        network: Union[ipaddress.IPv4Network, ipaddress.IPv6Network],
    ) -> Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        """Optimized IP scanning using batch database queries."""
        # For large networks (>1024 addresses), use batch queries
        if network.num_addresses > 1024:
            return await self._find_next_available_ip_large_network(tenant_id, network)

        # For smaller networks, get all allocated/reserved IPs in one query
        network_data = await self._get_network(tenant_id, str(network))
        if not network_data:
            return None

        # Get all allocated IPs for this network
        allocated_ips = set()

        # Query allocations
        allocations = (
            self.db.query(IPAllocation.ip_address)
            .filter(
                IPAllocation.tenant_id == tenant_id,
                IPAllocation.network_id == network_data["id"],
                IPAllocation.allocation_status == AllocationStatus.ALLOCATED,
            )
            .all()
        )
        allocated_ips.update(str(alloc.ip_address) for alloc in allocations)

        # Query reservations
        reservations = (
            self.db.query(IPReservation.ip_address)
            .filter(
                IPReservation.tenant_id == tenant_id,
                IPReservation.network_id == network_data["id"],
                IPReservation.reservation_status == ReservationStatus.RESERVED,
            )
            .all()
        )
        allocated_ips.update(str(res.ip_address) for res in reservations)

        # Find first available IP
        for ip in network.hosts():
            if str(ip) not in allocated_ips:
                return ip

        return None

    async def _find_next_available_ip_large_network(
        self,
        tenant_id: str,
        network: Union[ipaddress.IPv4Network, ipaddress.IPv6Network],
    ) -> Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        """Handle large networks with range-based scanning."""
        # For very large networks, scan in chunks
        chunk_size = 1024
        network_hosts = list(network.hosts())

        for i in range(0, len(network_hosts), chunk_size):
            chunk = network_hosts[i : i + chunk_size]
            ip_strings = [str(ip) for ip in chunk]

            # Check if any IPs in this chunk are allocated
            network_data = await self._get_network(tenant_id, str(network))
            if not network_data:
                return None

            # Query allocations for this IP range
            allocated_ips_query = (
                self.db.query(IPAllocation.ip_address)
                .filter(
                    IPAllocation.tenant_id == tenant_id,
                    IPAllocation.network_id == network_data["id"],
                    IPAllocation.allocation_status == AllocationStatus.ALLOCATED,
                    IPAllocation.ip_address.in_(ip_strings),
                )
                .all()
            )

            # Query reservations for this IP range
            reserved_ips_query = (
                self.db.query(IPReservation.ip_address)
                .filter(
                    IPReservation.tenant_id == tenant_id,
                    IPReservation.network_id == network_data["id"],
                    IPReservation.reservation_status == ReservationStatus.RESERVED,
                    IPReservation.ip_address.in_(ip_strings),
                )
                .all()
            )

            # Collect used IPs in this chunk
            used_ips = set()
            used_ips.update(str(alloc.ip_address) for alloc in allocated_ips_query)
            used_ips.update(str(res.ip_address) for res in reserved_ips_query)

            # Find first available IP in chunk
            for ip in chunk:
                if str(ip) not in used_ips:
                    return ip

        return None

    async def _find_next_available_ip_sequential(
        self,
        tenant_id: str,
        network: Union[ipaddress.IPv4Network, ipaddress.IPv6Network],
    ) -> Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        """Fallback sequential scanning for in-memory mode."""
        for ip in network.hosts():
            if not await self._check_ip_conflict(tenant_id, str(ip)):
                return ip
        return None

    def _network_to_dict(self, network) -> dict[str, Any]:
        """Convert network object to dictionary."""
        if not network:
            return {}
        return {
            "id": network.id,
            "network_id": network.network_id,
            "tenant_id": network.tenant_id,
            "network_name": network.network_name,
            "description": network.description,
            "cidr": network.cidr,
            "network_type": network.network_type,
            "gateway": network.gateway,
            "dns_servers": network.dns_servers,
            "dhcp_enabled": network.dhcp_enabled,
            "site_id": network.site_id,
            "vlan_id": network.vlan_id,
            "location": network.location,
            "tags": network.tags,
            "is_active": network.is_active,
            "created_at": network.created_at,
            "updated_at": network.updated_at,
        }

    def _allocation_to_dict(self, allocation) -> dict[str, Any]:
        """Convert allocation object to dictionary."""
        if not allocation:
            return {}
        return {
            "id": allocation.id,
            "allocation_id": allocation.allocation_id,
            "tenant_id": allocation.tenant_id,
            "network_id": allocation.network_id,
            "ip_address": allocation.ip_address,
            "allocation_type": allocation.allocation_type,
            "allocation_status": allocation.allocation_status,
            "assigned_to": allocation.assigned_to,
            "assigned_resource_id": allocation.assigned_resource_id,
            "assigned_resource_type": allocation.assigned_resource_type,
            "lease_time": allocation.lease_time,
            "hostname": allocation.hostname,
            "mac_address": allocation.mac_address,
            "description": allocation.description,
            "tags": allocation.tags,
            "allocated_at": allocation.allocated_at,
            "expires_at": allocation.expires_at,
            "renewed_at": allocation.renewed_at,
            "released_at": allocation.released_at,
            "last_seen": allocation.last_seen,
            "created_at": allocation.created_at,
            "updated_at": allocation.updated_at,
        }

    def _reservation_to_dict(self, reservation) -> dict[str, Any]:
        """Convert reservation object to dictionary."""
        if not reservation:
            return {}
        return {
            "id": reservation.id,
            "reservation_id": reservation.reservation_id,
            "tenant_id": reservation.tenant_id,
            "network_id": reservation.network_id,
            "ip_address": reservation.ip_address,
            "reservation_status": reservation.reservation_status,
            "reserved_for": reservation.reserved_for,
            "reserved_resource_id": reservation.reserved_resource_id,
            "reserved_resource_type": reservation.reserved_resource_type,
            "reservation_time": reservation.reservation_time,
            "priority": reservation.priority,
            "description": reservation.description,
            "tags": reservation.tags,
            "reserved_at": reservation.reserved_at,
            "expires_at": reservation.expires_at,
            "allocated_at": reservation.allocated_at,
            "cancelled_at": reservation.cancelled_at,
            "created_at": reservation.created_at,
            "updated_at": reservation.updated_at,
        }
