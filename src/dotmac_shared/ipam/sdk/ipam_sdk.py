"""
IPAM SDK - Public interface for IP Address Management operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from ..core.exceptions import (
        IPAddressConflictError,
        IPAMError,
        NetworkNotFoundError,
    )
    from ..core.schemas import (
        AllocationCreate,
        AllocationResponse,
        IPAvailability,
        NetworkCreate,
        NetworkResponse,
        NetworkUpdate,
        NetworkUtilization,
        ReservationCreate,
        ReservationResponse,
    )
    from ..services.ipam_service import IPAMService

    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False
    IPAMService = None
    IPAMError = IPAddressConflictError = NetworkNotFoundError = Exception

try:
    from sqlalchemy.orm import Session

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Session = None


class IPAMSDK:
    """
    Public SDK interface for IPAM operations.

    Provides a clean, tenant-aware API for IP address management including:
    - Network/subnet management
    - Dynamic and static IP allocation
    - IP reservation system
    - Network utilization analytics
    - Conflict detection and validation
    """

    def __init__(
        self,
        tenant_id: str,
        database_session: Optional[Session] = None,
        config: Optional[Dict] = None,
    ):
        """
        Initialize IPAM SDK for a specific tenant.

        Args:
            tenant_id: Unique identifier for the tenant
            database_session: Optional SQLAlchemy session for database operations
            config: Optional configuration overrides
        """
        self.tenant_id = tenant_id
        self.db = database_session
        self.config = config or {}

        if not SERVICES_AVAILABLE:
            raise ImportError("IPAM services not available - missing dependencies")

        self._service = IPAMService(database_session, config)

    # Network Management

    async def create_network(
        self,
        cidr: str,
        network_name: Optional[str] = None,
        network_type: str = "customer",
        description: Optional[str] = None,
        gateway: Optional[str] = None,
        dns_servers: Optional[List[str]] = None,
        dhcp_enabled: bool = False,
        site_id: Optional[str] = None,
        vlan_id: Optional[int] = None,
        location: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a new IP network/subnet.

        Args:
            cidr: Network CIDR notation (e.g., "192.168.1.0/24")
            network_name: Optional descriptive name
            network_type: Type of network (customer, infrastructure, etc.)
            description: Optional description
            gateway: Gateway IP address
            dns_servers: List of DNS server IP addresses
            dhcp_enabled: Whether DHCP is enabled for this network
            site_id: Optional site identifier
            vlan_id: Optional VLAN ID (1-4094)
            location: Optional location description
            **kwargs: Additional network parameters

        Returns:
            Dictionary containing network details

        Raises:
            InvalidNetworkError: If CIDR is invalid
            NetworkOverlapError: If network overlaps with existing network
            IPAMError: For other network creation errors
        """
        return await self._service.create_network(
            tenant_id=self.tenant_id,
            cidr=cidr,
            network_name=network_name,
            network_type=network_type,
            description=description,
            gateway=gateway,
            dns_servers=dns_servers or [],
            dhcp_enabled=dhcp_enabled,
            site_id=site_id,
            vlan_id=vlan_id,
            location=location,
            **kwargs,
        )

    async def get_network(self, network_id: str) -> Optional[Dict[str, Any]]:
        """
        Get network by ID.

        Args:
            network_id: Network identifier

        Returns:
            Network details dictionary or None if not found
        """
        return await self._service._get_network(self.tenant_id, network_id)

    async def get_network_utilization(self, network_id: str) -> Dict[str, Any]:
        """
        Get network utilization statistics.

        Args:
            network_id: Network identifier

        Returns:
            Dictionary with utilization statistics including:
            - total_addresses: Total addresses in network
            - usable_addresses: Usable addresses (excluding network/broadcast)
            - allocated_addresses: Currently allocated addresses
            - reserved_addresses: Currently reserved addresses
            - available_addresses: Available for allocation
            - utilization_percent: Percentage of network utilized

        Raises:
            NetworkNotFoundError: If network doesn't exist
        """
        return await self._service.get_network_utilization(self.tenant_id, network_id)

    # IP Allocation Management

    async def allocate_ip(
        self,
        network_id: str,
        ip_address: Optional[str] = None,
        allocation_type: str = "dynamic",
        assigned_to: Optional[str] = None,
        assigned_resource_id: Optional[str] = None,
        assigned_resource_type: Optional[str] = None,
        lease_time: int = 86400,
        hostname: Optional[str] = None,
        mac_address: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Allocate IP address from network.

        Args:
            network_id: Network to allocate from
            ip_address: Specific IP to allocate (optional, will find next available if None)
            allocation_type: Type of allocation (dynamic, static, dhcp)
            assigned_to: Description of what IP is assigned to
            assigned_resource_id: ID of assigned resource
            assigned_resource_type: Type of assigned resource
            lease_time: Lease duration in seconds (default 24 hours)
            hostname: Optional hostname
            mac_address: Optional MAC address (for DHCP tracking)
            description: Optional description
            **kwargs: Additional allocation parameters

        Returns:
            Dictionary containing allocation details

        Raises:
            NetworkNotFoundError: If network doesn't exist
            IPAddressConflictError: If requested IP is already allocated
            InsufficientAddressSpaceError: If no IPs available
        """
        return await self._service.allocate_ip(
            tenant_id=self.tenant_id,
            network_id=network_id,
            ip_address=ip_address,
            allocation_type=allocation_type,
            assigned_to=assigned_to,
            assigned_resource_id=assigned_resource_id,
            assigned_resource_type=assigned_resource_type,
            lease_time=lease_time,
            hostname=hostname,
            mac_address=mac_address,
            description=description,
            **kwargs,
        )

    async def release_ip(self, allocation_id: str) -> Dict[str, Any]:
        """
        Release allocated IP address.

        Args:
            allocation_id: Allocation identifier to release

        Returns:
            Dictionary with release details

        Raises:
            AllocationNotFoundError: If allocation doesn't exist
        """
        return await self._service.release_allocation(self.tenant_id, allocation_id)

    async def renew_allocation(
        self, allocation_id: str, lease_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Renew IP allocation lease.

        Args:
            allocation_id: Allocation to renew
            lease_time: New lease duration (optional)

        Returns:
            Updated allocation details

        Raises:
            AllocationNotFoundError: If allocation doesn't exist
            ExpiredAllocationError: If allocation has expired
        """
        # Implementation would extend the service with renew functionality
        raise NotImplementedError("Allocation renewal not yet implemented")

    # IP Reservation Management

    async def reserve_ip(
        self,
        network_id: str,
        ip_address: str,
        reserved_for: Optional[str] = None,
        reserved_resource_id: Optional[str] = None,
        reserved_resource_type: Optional[str] = None,
        reservation_time: int = 3600,
        priority: int = 0,
        description: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Reserve IP address for future allocation.

        Args:
            network_id: Network containing the IP
            ip_address: Specific IP address to reserve
            reserved_for: Description of what IP is reserved for
            reserved_resource_id: ID of resource IP is reserved for
            reserved_resource_type: Type of reserved resource
            reservation_time: Reservation duration in seconds (default 1 hour)
            priority: Reservation priority (0-100, higher = more priority)
            description: Optional description
            **kwargs: Additional reservation parameters

        Returns:
            Dictionary containing reservation details

        Raises:
            NetworkNotFoundError: If network doesn't exist
            IPAddressConflictError: If IP is already allocated or reserved
        """
        return await self._service.reserve_ip(
            tenant_id=self.tenant_id,
            network_id=network_id,
            ip_address=ip_address,
            reserved_for=reserved_for,
            reserved_resource_id=reserved_resource_id,
            reserved_resource_type=reserved_resource_type,
            reservation_time=reservation_time,
            priority=priority,
            description=description,
            **kwargs,
        )

    async def cancel_reservation(self, reservation_id: str) -> Dict[str, Any]:
        """
        Cancel IP reservation.

        Args:
            reservation_id: Reservation to cancel

        Returns:
            Cancelled reservation details

        Raises:
            ReservationNotFoundError: If reservation doesn't exist
        """
        # Implementation would extend the service with cancel functionality
        raise NotImplementedError("Reservation cancellation not yet implemented")

    # Query and Analytics

    async def check_ip_availability(
        self, network_id: str, ip_address: str
    ) -> Dict[str, Any]:
        """
        Check if IP address is available for allocation.

        Args:
            network_id: Network to check
            ip_address: IP address to check

        Returns:
            Dictionary with availability status:
            - ip_address: The checked IP
            - network_id: Network ID
            - available: Boolean availability status
            - reason: Reason if not available
            - conflicting_allocation_id: ID of conflicting allocation (if any)
            - conflicting_reservation_id: ID of conflicting reservation (if any)

        Raises:
            NetworkNotFoundError: If network doesn't exist
        """
        # Check network exists
        network_data = await self._service._get_network(self.tenant_id, network_id)
        if not network_data:
            raise NetworkNotFoundError(network_id)

        # Check if IP is in network range
        import ipaddress

        network = ipaddress.ip_network(network_data["cidr"])
        try:
            ip_addr = ipaddress.ip_address(ip_address)
        except ValueError:
            return {
                "ip_address": ip_address,
                "network_id": network_id,
                "available": False,
                "reason": "Invalid IP address format",
            }

        if ip_addr not in network:
            return {
                "ip_address": ip_address,
                "network_id": network_id,
                "available": False,
                "reason": f"IP not in network {network_data['cidr']}",
            }

        # Check for conflicts
        conflict = await self._service._check_ip_conflict(self.tenant_id, ip_address)
        if conflict:
            return {
                "ip_address": ip_address,
                "network_id": network_id,
                "available": False,
                "reason": "IP is already allocated or reserved",
            }

        return {
            "ip_address": ip_address,
            "network_id": network_id,
            "available": True,
            "reason": "IP is available for allocation",
        }

    async def get_allocations_by_network(
        self, network_id: str, include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all allocations for a network.

        Args:
            network_id: Network identifier
            include_expired: Whether to include expired allocations

        Returns:
            List of allocation dictionaries

        Raises:
            NetworkNotFoundError: If network doesn't exist
        """
        # Implementation would extend the service with allocation queries
        raise NotImplementedError("Allocation queries not yet implemented")

    async def get_reservations_by_network(
        self, network_id: str, include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all reservations for a network.

        Args:
            network_id: Network identifier
            include_expired: Whether to include expired reservations

        Returns:
            List of reservation dictionaries

        Raises:
            NetworkNotFoundError: If network doesn't exist
        """
        # Implementation would extend the service with reservation queries
        raise NotImplementedError("Reservation queries not yet implemented")

    # Utility Methods

    def get_configuration(self) -> Dict[str, Any]:
        """
        Get current IPAM configuration.

        Returns:
            Configuration dictionary
        """
        return self.config.copy()

    def get_tenant_id(self) -> str:
        """
        Get tenant ID for this SDK instance.

        Returns:
            Tenant identifier string
        """
        return self.tenant_id

    async def validate_network_configuration(self, **network_params) -> Dict[str, Any]:
        """
        Validate network configuration without creating it.

        Args:
            **network_params: Network parameters to validate

        Returns:
            Validation results with any issues found
        """
        import ipaddress

        validation_result = {"valid": True, "issues": [], "warnings": []}

        # Validate CIDR
        cidr = network_params.get("cidr")
        if cidr:
            try:
                network = ipaddress.ip_network(cidr, strict=False)

                # Check for common issues
                if network.prefixlen > 30:
                    validation_result["warnings"].append(
                        f"Very small network (/{network.prefixlen}) - limited usable addresses"
                    )

                if network.is_private:
                    validation_result["warnings"].append("Using private IP range")

            except ValueError as e:
                validation_result["valid"] = False
                validation_result["issues"].append(f"Invalid CIDR: {e}")

        # Validate VLAN ID
        vlan_id = network_params.get("vlan_id")
        if vlan_id is not None:
            if not (1 <= vlan_id <= 4094):
                validation_result["valid"] = False
                validation_result["issues"].append("VLAN ID must be between 1 and 4094")

        # Validate gateway
        gateway = network_params.get("gateway")
        if gateway and cidr:
            try:
                gateway_ip = ipaddress.ip_address(gateway)
                if gateway_ip not in network:
                    validation_result["valid"] = False
                    validation_result["issues"].append(
                        "Gateway IP not in network range"
                    )
            except ValueError:
                validation_result["valid"] = False
                validation_result["issues"].append("Invalid gateway IP address")

        return validation_result

    async def cleanup_expired(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Clean up expired allocations and reservations.

        Args:
            dry_run: If True, only report what would be cleaned up

        Returns:
            Cleanup summary with counts of items processed
        """
        # Implementation would extend the service with cleanup functionality
        raise NotImplementedError("Cleanup functionality not yet implemented")
