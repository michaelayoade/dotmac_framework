"""IPAM-specific exceptions."""

from typing import Optional


class IPAMError(Exception):
    """Base IPAM exception."""

    pass


class IPAddressConflictError(IPAMError):
    """IP address already allocated or reserved."""

    def __init__(self, ip_address: str, message: Optional[str] = None):
        self.ip_address = ip_address
        if message is None:
            message = f"IP address {ip_address} is already allocated or reserved"
        super().__init__(message)


class NetworkNotFoundError(IPAMError):
    """Network not found in IPAM database."""

    def __init__(self, network_id: str, message: Optional[str] = None):
        self.network_id = network_id
        if message is None:
            message = f"Network {network_id} not found"
        super().__init__(message)


class InvalidNetworkError(IPAMError):
    """Invalid network configuration or CIDR."""

    def __init__(self, cidr: str, reason: Optional[str] = None):
        self.cidr = cidr
        if reason:
            message = f"Invalid network {cidr}: {reason}"
        else:
            message = f"Invalid network {cidr}"
        super().__init__(message)


class AllocationNotFoundError(IPAMError):
    """IP allocation not found."""

    def __init__(self, allocation_id: str, message: Optional[str] = None):
        self.allocation_id = allocation_id
        if message is None:
            message = f"Allocation {allocation_id} not found"
        super().__init__(message)


class ReservationNotFoundError(IPAMError):
    """IP reservation not found."""

    def __init__(self, reservation_id: str, message: Optional[str] = None):
        self.reservation_id = reservation_id
        if message is None:
            message = f"Reservation {reservation_id} not found"
        super().__init__(message)


class InsufficientAddressSpaceError(IPAMError):
    """No available IP addresses in network."""

    def __init__(self, network_id: str, message: Optional[str] = None):
        self.network_id = network_id
        if message is None:
            message = f"No available IP addresses in network {network_id}"
        super().__init__(message)


class NetworkOverlapError(IPAMError):
    """Network overlaps with existing network."""

    def __init__(self, cidr: str, existing_cidr: str, message: Optional[str] = None):
        self.cidr = cidr
        self.existing_cidr = existing_cidr
        if message is None:
            message = f"Network {cidr} overlaps with existing network {existing_cidr}"
        super().__init__(message)


class ExpiredAllocationError(IPAMError):
    """IP allocation has expired."""

    def __init__(
        self, allocation_id: str, expired_at: str, message: Optional[str] = None
    ):
        self.allocation_id = allocation_id
        self.expired_at = expired_at
        if message is None:
            message = f"Allocation {allocation_id} expired at {expired_at}"
        super().__init__(message)


class TenantIsolationError(IPAMError):
    """Tenant isolation violation."""

    def __init__(self, tenant_id: str, resource_id: str, message: Optional[str] = None):
        self.tenant_id = tenant_id
        self.resource_id = resource_id
        if message is None:
            message = f"Tenant {tenant_id} cannot access resource {resource_id}"
        super().__init__(message)
