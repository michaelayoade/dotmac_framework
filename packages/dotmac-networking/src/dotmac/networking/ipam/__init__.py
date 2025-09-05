"""
DotMac IPAM - IP Address Management Package

This package provides comprehensive IP address management capabilities:
- Network/subnet management with CIDR validation
- Dynamic and static IP allocation
- IP reservation system with expiration
- Conflict detection and validation
- Network utilization statistics and analytics
- Multi-tenant support with isolation
- Database persistence with SQLAlchemy integration
- RESTful API schemas with Pydantic
"""
from typing import Optional

try:
    from .core.models import (
        AllocationStatus,
        IPAllocation,
        IPNetwork,
        IPReservation,
        NetworkType,
        ReservationStatus,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM core models not available: {e}")
    NetworkType = AllocationStatus = ReservationStatus = None
    IPNetwork = IPAllocation = IPReservation = None

try:
    from .core.schemas import (
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
    NetworkCreate = NetworkUpdate = NetworkResponse = None
    AllocationCreate = AllocationResponse = NetworkUtilization = None

try:
    from .services.ipam_service import IPAMService
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM service not available: {e}")
    IPAMService = None

# Enhanced service (placeholder for future implementation)
EnhancedIPAMService = None

try:
    from .sdk.ipam_sdk import IPAMSDK
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM SDK not available: {e}")
    IPAMSDK = None

try:
    from .repositories.ipam_repository import IPAMRepository
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM repository not available: {e}")
    IPAMRepository = None

# Utility imports
try:
    from .utils.network_utils import (
        calculate_network_info,
        check_ip_in_network,
        find_next_available_subnet,
        validate_cidr,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM network utilities not available: {e}")
    validate_cidr = calculate_network_info = None
    find_next_available_subnet = check_ip_in_network = None

# Enhanced components
try:
    from .middleware.rate_limiting import IPAMRateLimiter, IPAMRateLimitMiddleware
    from .planning.network_planner import IPPool, NetworkPlanner, SubnetRequirement
    from .tasks.cleanup_tasks import (
        audit_ip_conflicts,
        cleanup_expired_allocations,
        cleanup_expired_reservations,
        generate_utilization_report,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM enhanced components not available: {e}")
    IPAMRateLimiter = IPAMRateLimitMiddleware = None
    NetworkPlanner = SubnetRequirement = IPPool = None
    cleanup_expired_allocations = cleanup_expired_reservations = None
    generate_utilization_report = audit_ip_conflicts = None

# Platform adapters
try:
    from .adapters.database_adapter import DatabaseIPAMAdapter
except ImportError:
    DatabaseIPAMAdapter = None

try:
    from .adapters.dhcp_adapter import DHCPIPAMAdapter
except ImportError:
    DHCPIPAMAdapter = None

# Version and metadata
__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

# Main exports
__all__ = [
    # Core models
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
    # Services
    "IPAMService",
    "EnhancedIPAMService",
    "IPAMSDK",
    # Repository
    "IPAMRepository",
    # Utilities
    "validate_cidr",
    "calculate_network_info",
    "find_next_available_subnet",
    "check_ip_in_network",
    # Enhanced Components
    "IPAMRateLimiter",
    "IPAMRateLimitMiddleware",
    "NetworkPlanner",
    "SubnetRequirement",
    "IPPool",
    "cleanup_expired_allocations",
    "cleanup_expired_reservations",
    "generate_utilization_report",
    "audit_ip_conflicts",
    # Adapters
    "DatabaseIPAMAdapter",
    "DHCPIPAMAdapter",
    # Version
    "__version__",
]

# Configuration defaults
DEFAULT_CONFIG = {
    "allocation": {
        "default_lease_time": 86400,  # 24 hours
        "max_lease_time": 2592000,  # 30 days
        "auto_release_expired": True,
        "conflict_detection": True,
    },
    "reservation": {
        "default_reservation_time": 3600,  # 1 hour
        "max_reservation_time": 86400,  # 24 hours
        "auto_cleanup_expired": True,
    },
    "network": {
        "allow_overlapping_networks": False,
        "auto_create_gateway": True,
        "default_dhcp_enabled": False,
        "validate_network_boundaries": True,
    },
    "utilization": {
        "warning_threshold": 80,  # Percent
        "critical_threshold": 95,  # Percent
        "track_historical_usage": True,
    },
    "database": {
        "auto_create_tables": True,
        "connection_pool_size": 10,
        "query_timeout": 30,
    },
}


def get_version():
    """Get IPAM package version."""
    return __version__


def get_default_config():
    """Get default IPAM configuration."""
    return DEFAULT_CONFIG.copy()


# Quick setup functions for common use cases
def create_ipam_service(database_session=None, config: Optional[dict] = None) -> "IPAMService":
    """Create a configured IPAM service."""
    if not IPAMService:
        raise ImportError("IPAM service not available")

    config = config or get_default_config()
    return IPAMService(database_session, config)


def create_ipam_sdk(
    tenant_id: str, database_session=None, config: Optional[dict] = None
) -> "IPAMSDK":
    """Create a configured IPAM SDK."""
    if not IPAMSDK:
        raise ImportError("IPAM SDK not available")

    config = config or get_default_config()
    return IPAMSDK(tenant_id, database_session, config)


def create_simple_ipam(tenant_id: str = "default", config: Optional[dict] = None) -> "IPAMSDK":
    """Create a simple in-memory IPAM SDK for testing."""
    if not IPAMSDK:
        raise ImportError("IPAM SDK not available")

    # In-memory configuration for testing
    test_config = {
        "allocation": {"default_lease_time": 3600},
        "network": {"validate_network_boundaries": True},
    }
    test_config.update(config or {})

    return IPAMSDK(tenant_id, database_session=None, config=test_config)
