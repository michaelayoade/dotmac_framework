"""
IPAM core components.
"""
try:
    from .models import (
        AllocationStatus,
        IPAllocation,
        IPNetwork,
        IPReservation,
        NetworkType,
        ReservationStatus,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM models not available: {e}")
    NetworkType = AllocationStatus = ReservationStatus = None
    IPNetwork = IPAllocation = IPReservation = None

try:
    from .schemas import (
        AllocationCreate,
        AllocationResponse,
        AllocationUpdate,
        IPAvailability,
        NetworkCreate,
        NetworkResponse,
        NetworkUpdate,
        NetworkUtilization,
        ReservationCreate,
        ReservationResponse,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM schemas not available: {e}")
    NetworkCreate = NetworkResponse = AllocationResponse = None

try:
    from .exceptions import (
        AllocationNotFoundError,
        InvalidNetworkError,
        IPAddressConflictError,
        IPAMError,
        NetworkNotFoundError,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM exceptions not available: {e}")
    IPAMError = IPAddressConflictError = NetworkNotFoundError = None

__all__ = [
    # Models
    "IPNetwork",
    "IPAllocation",
    "IPReservation",
    # Enums
    "NetworkType",
    "AllocationStatus",
    "ReservationStatus",
    # Schemas
    "NetworkCreate",
    "NetworkUpdate",
    "NetworkResponse",
    "AllocationCreate",
    "AllocationUpdate",
    "AllocationResponse",
    "ReservationCreate",
    "ReservationResponse",
    "NetworkUtilization",
    "IPAvailability",
    # Exceptions
    "IPAMError",
    "IPAddressConflictError",
    "NetworkNotFoundError",
    "InvalidNetworkError",
    "AllocationNotFoundError",
]
