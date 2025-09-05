from pydantic import BaseModel, ConfigDict, Field

"""IPAM API schemas for requests and responses."""

import ipaddress
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

try:
    from pydantic import field_validator, model_validator

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

    # Create minimal stubs when Pydantic is not available
    class BaseModel:
        """BaseModel implementation."""

        pass

    Field = validator = ConfigDict = None

# Create independent schema base class
try:
    from dotmac.core.schemas import TenantModelSchema

    SHARED_SCHEMAS_AVAILABLE = True
except ImportError:
    SHARED_SCHEMAS_AVAILABLE = False

if not SHARED_SCHEMAS_AVAILABLE:
    # Fallback when shared schemas aren't available
    if PYDANTIC_AVAILABLE:

        class TenantModelSchema(BaseModel):
            """TenantModelSchema implementation."""

            model_config = ConfigDict(from_attributes=True, extra="allow")
            id: Optional[UUID] = None
            tenant_id: str
            created_at: datetime
            updated_at: datetime

    else:
        TenantModelSchema = BaseModel

from .models import AllocationStatus, NetworkType, ReservationStatus

if PYDANTIC_AVAILABLE:
    # Network Schemas
    class NetworkBase(BaseModel):
        """Base network schema."""

        network_name: Optional[str] = Field(None, max_length=200)
        description: Optional[str] = None
        cidr: str = Field(..., description="Network CIDR (e.g., 192.168.1.0/24)")
        network_type: NetworkType
        gateway: Optional[str] = Field(None, description="Gateway IP address")
        dns_servers: Optional[list[str]] = Field(
            default=[], description="List of DNS server IPs"
        )
        dhcp_enabled: bool = Field(default=False)
        site_id: Optional[str] = Field(None, max_length=100)
        vlan_id: Optional[int] = Field(None, ge=1, le=4094)
        location: Optional[str] = Field(None, max_length=200)
        tags: Optional[dict[str, Any]] = Field(default={})

        @field_validator("cidr")
        @classmethod
        def validate_cidr(cls, v):
            """Validate CIDR format."""
            try:
                ipaddress.ip_network(v, strict=False)
                return v
            except ValueError as e:
                raise ValueError(f"Invalid CIDR format: {e}") from e

        @field_validator("gateway")
        @classmethod
        def validate_gateway(cls, v):
            """Validate gateway IP address."""
            if v:
                try:
                    ipaddress.ip_address(v)
                    return v
                except ValueError as e:
                    raise ValueError(f"Invalid gateway IP address: {e}") from e
            return v

        @field_validator("dns_servers")
        @classmethod
        def validate_dns_servers(cls, v):
            """Validate DNS server IP addresses."""
            if v:
                for dns_ip in v:
                    try:
                        ipaddress.ip_address(dns_ip)
                    except ValueError:
                        raise ValueError(f"Invalid DNS server IP address: {dns_ip}")
            return v or []

    class NetworkCreate(NetworkBase):
        """Schema for creating networks."""

        network_id: Optional[str] = Field(None, max_length=100)

    class NetworkUpdate(BaseModel):
        """Schema for updating networks."""

        network_name: Optional[str] = Field(None, max_length=200)
        description: Optional[str] = None
        gateway: Optional[str] = None
        dns_servers: Optional[list[str]] = None
        dhcp_enabled: Optional[bool] = None
        site_id: Optional[str] = Field(None, max_length=100)
        vlan_id: Optional[int] = Field(None, ge=1, le=4094)
        location: Optional[str] = Field(None, max_length=200)
        tags: Optional[dict[str, Any]] = None
        is_active: Optional[bool] = None

    class NetworkResponse(TenantModelSchema, NetworkBase):
        """Schema for network responses."""

        network_id: str
        total_addresses: int
        usable_addresses: int
        is_active: bool

    # Allocation Schemas
    class AllocationBase(BaseModel):
        """Base allocation schema."""

        ip_address: Optional[str] = Field(
            None, description="Specific IP to allocate (optional)"
        )
        allocation_type: str = Field(
            default="dynamic", description="dynamic, static, dhcp"
        )
        assigned_to: Optional[str] = Field(None, max_length=200)
        assigned_resource_id: Optional[str] = Field(None, max_length=100)
        assigned_resource_type: Optional[str] = Field(None, max_length=50)
        lease_time: int = Field(
            default=86400, ge=300, le=31536000, description="Lease time in seconds"
        )
        hostname: Optional[str] = Field(None, max_length=255)
        mac_address: Optional[str] = Field(
            None,
            pattern=r"^[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}$",
        )
        description: Optional[str] = None
        tags: Optional[dict[str, Any]] = Field(default={})

        @field_validator("ip_address")
        @classmethod
        def validate_ip_address(cls, v):
            """Validate IP address format."""
            if v:
                try:
                    ipaddress.ip_address(v)
                    return v
                except ValueError as e:
                    raise ValueError(f"Invalid IP address: {e}") from e
            return v

    class AllocationCreate(AllocationBase):
        """Schema for creating allocations."""

        network_id: str = Field(..., description="Network ID to allocate from")

    class AllocationUpdate(BaseModel):
        """Schema for updating allocations."""

        assigned_to: Optional[str] = Field(None, max_length=200)
        assigned_resource_id: Optional[str] = Field(None, max_length=100)
        assigned_resource_type: Optional[str] = Field(None, max_length=50)
        lease_time: Optional[int] = Field(None, ge=300, le=31536000)
        hostname: Optional[str] = Field(None, max_length=255)
        mac_address: Optional[str] = None
        description: Optional[str] = None
        tags: Optional[dict[str, Any]] = None

    class AllocationResponse(TenantModelSchema, AllocationBase):
        """Schema for allocation responses."""

        allocation_id: str
        network_id: str
        ip_address: str
        allocation_status: AllocationStatus
        allocated_at: datetime
        expires_at: Optional[datetime] = None
        renewed_at: Optional[datetime] = None
        released_at: Optional[datetime] = None
        last_seen: Optional[datetime] = None
        is_expired: bool
        is_active: bool
        days_until_expiry: Optional[int] = None

    # Reservation Schemas
    class ReservationBase(BaseModel):
        """Base reservation schema."""

        ip_address: str = Field(..., description="IP address to reserve")
        reserved_for: Optional[str] = Field(None, max_length=200)
        reserved_resource_id: Optional[str] = Field(None, max_length=100)
        reserved_resource_type: Optional[str] = Field(None, max_length=50)
        reservation_time: int = Field(
            default=3600, ge=60, le=86400, description="Reservation time in seconds"
        )
        priority: int = Field(
            default=0, ge=0, le=100, description="Reservation priority"
        )
        description: Optional[str] = None
        tags: Optional[dict[str, Any]] = Field(default={})

        @field_validator("ip_address")
        @classmethod
        def validate_ip_address(cls, v):
            """Validate IP address format."""
            try:
                ipaddress.ip_address(v)
                return v
            except ValueError as e:
                raise ValueError(f"Invalid IP address: {e}") from e

    class ReservationCreate(ReservationBase):
        """Schema for creating reservations."""

        network_id: str = Field(..., description="Network ID to reserve from")

    class ReservationResponse(TenantModelSchema, ReservationBase):
        """Schema for reservation responses."""

        reservation_id: str
        network_id: str
        reservation_status: ReservationStatus
        reserved_at: datetime
        expires_at: datetime
        allocated_at: Optional[datetime] = None
        cancelled_at: Optional[datetime] = None
        is_expired: bool
        is_active: bool
        minutes_until_expiry: Optional[int] = None

    # Analytics and Reporting Schemas
    class NetworkUtilization(BaseModel):
        """Network utilization statistics."""

        network_id: str
        network_name: Optional[str] = None
        cidr: str
        network_type: NetworkType
        total_addresses: int
        usable_addresses: int
        allocated_addresses: int
        reserved_addresses: int
        available_addresses: int
        utilization_percent: float = Field(ge=0, le=100)
        allocation_breakdown: dict[str, int] = Field(
            default_factory=dict
        )  # By allocation type
        recent_allocations: int = 0  # Last 24 hours
        expiring_soon: int = 0  # Expiring in next 7 days

    class IPAvailability(BaseModel):
        """IP address availability check."""

        network_id: str
        ip_address: str
        available: bool
        reason: str
        conflicting_allocation_id: Optional[str] = None
        conflicting_reservation_id: Optional[str] = None
        suggested_alternatives: Optional[list[str]] = Field(default=[], max_length=5)

    class AllocationSummary(BaseModel):
        """Allocation summary statistics."""

        total_allocations: int
        active_allocations: int
        expired_allocations: int
        expiring_soon: int  # Next 7 days
        by_type: dict[str, int] = Field(default_factory=dict)
        by_status: dict[str, int] = Field(default_factory=dict)
        top_assignees: list[dict[str, Any]] = Field(default_factory=list)

    class ReservationSummary(BaseModel):
        """Reservation summary statistics."""

        total_reservations: int
        active_reservations: int
        expired_reservations: int
        expiring_soon: int  # Next hour
        by_status: dict[str, int] = Field(default_factory=dict)
        by_priority: dict[str, int] = Field(default_factory=dict)

    # List Response Schemas
    class NetworkListResponse(BaseModel):
        """Network list response."""

        networks: list[NetworkResponse]
        total_count: int
        utilization_summary: dict[str, float] = Field(default_factory=dict)

    class AllocationListResponse(BaseModel):
        """Allocation list response."""

        allocations: list[AllocationResponse]
        total_count: int
        summary: AllocationSummary

    class ReservationListResponse(BaseModel):
        """Reservation list response."""

        reservations: list[ReservationResponse]
        total_count: int
        summary: ReservationSummary

    # Filter Schemas
    class NetworkFilters(BaseModel):
        """Network filtering options."""

        network_type: Optional[NetworkType] = None
        site_id: Optional[str] = None
        vlan_id: Optional[int] = None
        dhcp_enabled: Optional[bool] = None
        is_active: Optional[bool] = None
        utilization_min: Optional[float] = Field(None, ge=0, le=100)
        utilization_max: Optional[float] = Field(None, ge=0, le=100)
        has_available_ips: Optional[bool] = None

    class AllocationFilters(BaseModel):
        """Allocation filtering options."""

        network_id: Optional[str] = None
        allocation_type: Optional[str] = None
        allocation_status: Optional[AllocationStatus] = None
        assigned_to: Optional[str] = None
        assigned_resource_type: Optional[str] = None
        expired_only: bool = False
        expiring_soon: bool = False  # Next 7 days
        has_hostname: Optional[bool] = None
        has_mac_address: Optional[bool] = None

    class ReservationFilters(BaseModel):
        """Reservation filtering options."""

        network_id: Optional[str] = None
        reservation_status: Optional[ReservationStatus] = None
        reserved_for: Optional[str] = None
        reserved_resource_type: Optional[str] = None
        priority_min: Optional[int] = Field(None, ge=0, le=100)
        expired_only: bool = False
        expiring_soon: bool = False  # Next hour

else:
    # Create stub classes when Pydantic is not available
    NetworkBase = NetworkCreate = NetworkUpdate = NetworkResponse = None
    AllocationBase = AllocationCreate = AllocationResponse = None
    ReservationBase = ReservationCreate = ReservationResponse = None
    NetworkUtilization = IPAvailability = None
    NetworkListResponse = AllocationListResponse = ReservationListResponse = None
    NetworkFilters = AllocationFilters = ReservationFilters = None
