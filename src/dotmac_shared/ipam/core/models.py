"""IPAM database models for network management."""

import ipaddress
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from sqlalchemy import JSON, Boolean, Column, Date, DateTime
    from sqlalchemy import Enum as SQLEnum
    from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
    from sqlalchemy.dialects.postgresql import INET, UUID
    from sqlalchemy.ext.hybrid import hybrid_property
    from sqlalchemy.orm import declarative_base, relationship

        Base = declarative_base()

        class TenantModel(Base):
            """TenantModel implementation."""

            __abstract__ = True
            id = Column(UUID(as_uuid=True), primary_key=True)
            tenant_id = Column(String(100), nullable=False, index=True)

        class StatusMixin:
            """StatusMixin implementation."""

            __abstract__ = True
            is_active = Column(Boolean, default=True, nullable=False)

        class AuditMixin:
            """AuditMixin implementation."""

            __abstract__ = True
            created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
            updated_at = Column(
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
                nullable=False,
            )
            created_by = Column(
                String(100), nullable=True, index=True
            )  # User ID who created
            updated_by = Column(
                String(100), nullable=True, index=True
            )  # User ID who last updated

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    # Create minimal stubs for when SQLAlchemy is not available
    Column = String = Text = Boolean = DateTime = Date = None
    Integer = Numeric = JSON = ForeignKey = Index = None
    UUID = INET = relationship = hybrid_property = SQLEnum = None
    TenantModel = StatusMixin = AuditMixin = None


class NetworkType(str, Enum):
    """Network type enumeration."""

    CUSTOMER = "customer"
    INFRASTRUCTURE = "infrastructure"
    MANAGEMENT = "management"
    SERVICE = "service"
    TRANSIT = "transit"
    LOOPBACK = "loopback"
    POINT_TO_POINT = "point_to_point"


class AllocationStatus(str, Enum):
    """IP allocation status."""

    ALLOCATED = "allocated"
    RELEASED = "released"
    EXPIRED = "expired"
    RESERVED = "reserved"


class ReservationStatus(str, Enum):
    """IP reservation status."""

    RESERVED = "reserved"
    ALLOCATED = "allocated"  # Reserved IP was allocated
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# SQLAlchemy models (only available if SQLAlchemy is installed)
if SQLALCHEMY_AVAILABLE:

    class IPNetwork(TenantModel, StatusMixin, AuditMixin):
        """IP network/subnet definition."""

        __tablename__ = "ipam_networks"

        # Network identification
        network_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
        network_name = Column(String(200), nullable=True)
        description = Column(Text, nullable=True)

        # Network configuration
        cidr = Column(INET, nullable=False, index=True)
        network_type = Column(SQLEnum(NetworkType), nullable=False, index=True)

        # Network properties
        gateway = Column(INET, nullable=True)
        dns_servers = Column(JSON, nullable=True)  # List of DNS server IPs
        dhcp_enabled = Column(Boolean, default=False, nullable=False)

        # Organizational
        site_id = Column(String(100), nullable=True, index=True)
        vlan_id = Column(Integer, nullable=True, index=True)
        location = Column(String(200), nullable=True)

        # Metadata
        tags = Column(JSON, nullable=True)  # Flexible tagging system
        custom_fields = Column(JSON, nullable=True)

        # Relationships
        allocations = relationship(
            "IPAllocation", back_populates="network", cascade="all, delete-orphan"
        )
        reservations = relationship(
            "IPReservation", back_populates="network", cascade="all, delete-orphan"
        )

        __table_args__ = (
            Index("ix_networks_tenant_cidr", "tenant_id", "cidr"),
            Index("ix_networks_type_site", "network_type", "site_id"),
            Index("ix_networks_vlan", "vlan_id"),
        )

        @hybrid_property
        def network_address(self):
            """Get network address as ipaddress object."""
            try:
                return ipaddress.ip_network(self.cidr, strict=False)
            except ValueError:
                return None

        @hybrid_property
        def total_addresses(self):
            """Calculate total number of addresses in network."""
            network = self.network_address
            return network.num_addresses if network else 0

        @hybrid_property
        def usable_addresses(self):
            """Calculate usable addresses (excluding network and broadcast)."""
            network = self.network_address
            if network:
                # Point-to-point networks have 2 usable addresses
                if network.prefixlen >= 30:  # /30 or smaller
                    return 2 if network.prefixlen == 30 else 1
                # Regular networks exclude network and broadcast
                return max(0, network.num_addresses - 2)
            return 0

        def __repr__(self):
            return f"<IPNetwork(id='{self.network_id}', cidr='{self.cidr}', type='{self.network_type}')>"

    class IPAllocation(TenantModel, AuditMixin):
        """IP address allocations."""

        __tablename__ = "ipam_allocations"

        # Allocation identification
        allocation_id = Column(
            UUID(as_uuid=True), nullable=False, unique=True, index=True
        )

        # Network reference
        network_id = Column(
            UUID(as_uuid=True),
            ForeignKey("ipam_networks.id"),
            nullable=False,
            index=True,
        )

        # IP allocation details
        ip_address = Column(INET, nullable=False, index=True)
        allocation_type = Column(
            String(50), default="dynamic", nullable=False
        )  # dynamic, static, dhcp
        allocation_status = Column(
            SQLEnum(AllocationStatus),
            default=AllocationStatus.ALLOCATED,
            nullable=False,
            index=True,
        )

        # Assignment details
        assigned_to = Column(
            String(200), nullable=True, index=True
        )  # Device, user, service, etc.
        assigned_resource_id = Column(
            String(100), nullable=True, index=True
        )  # Device ID, customer ID, etc.
        assigned_resource_type = Column(
            String(50), nullable=True
        )  # device, customer, service, etc.

        # Lease management
        lease_time = Column(Integer, default=86400, nullable=False)  # Seconds
        allocated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        expires_at = Column(DateTime, nullable=True, index=True)
        renewed_at = Column(DateTime, nullable=True)
        released_at = Column(DateTime, nullable=True)

        # Usage tracking
        hostname = Column(String(255), nullable=True)
        mac_address = Column(
            String(17), nullable=True, index=True
        )  # For DHCP tracking, normalized format
        last_seen = Column(DateTime, nullable=True)

        @hybrid_property
        def normalized_mac_address(self):
            """Get normalized MAC address (lowercase, colon-separated)."""
            if not self.mac_address:
                return None
            # Remove all separators and normalize to lowercase
            clean_mac = "".join(c.lower() for c in self.mac_address if c.isalnum())
            if len(clean_mac) == 12:
                return ":".join(clean_mac[i : i + 2] for i in range(0, 12, 2))
            return self.mac_address

        # Additional information
        description = Column(Text, nullable=True)
        tags = Column(JSON, nullable=True)
        custom_fields = Column(JSON, nullable=True)

        # Relationships
        network = relationship("IPNetwork", back_populates="allocations")

        __table_args__ = (
            Index("ix_allocations_tenant_ip", "tenant_id", "ip_address", unique=True),
            Index("ix_allocations_network_status", "network_id", "allocation_status"),
            Index("ix_allocations_assigned", "assigned_to", "assigned_resource_id"),
            Index("ix_allocations_expires", "expires_at"),
            Index("ix_allocations_mac", "mac_address"),
        )

        @hybrid_property
        def is_expired(self):
            """Check if allocation has expired."""
            return self.expires_at and datetime.now(timezone.utc) > self.expires_at

        @hybrid_property
        def is_active(self):
            """Check if allocation is currently active."""
            return (
                self.allocation_status == AllocationStatus.ALLOCATED
                and not self.is_expired
            )

        @hybrid_property
        def days_until_expiry(self):
            """Calculate days until expiry."""
            if self.expires_at:
                delta = self.expires_at - datetime.now(timezone.utc)
                return max(0, delta.days)
            return None

        def __repr__(self):
            return f"<IPAllocation(id='{self.allocation_id}', ip='{self.ip_address}', status='{self.allocation_status}')>"

    class IPReservation(TenantModel, AuditMixin):
        """IP address reservations for future allocation."""

        __tablename__ = "ipam_reservations"

        # Reservation identification
        reservation_id = Column(
            UUID(as_uuid=True), nullable=False, unique=True, index=True
        )

        # Network reference
        network_id = Column(
            UUID(as_uuid=True),
            ForeignKey("ipam_networks.id"),
            nullable=False,
            index=True,
        )

        # Reservation details
        ip_address = Column(INET, nullable=False, index=True)
        reservation_status = Column(
            SQLEnum(ReservationStatus),
            default=ReservationStatus.RESERVED,
            nullable=False,
            index=True,
        )

        # Reservation purpose
        reserved_for = Column(
            String(200), nullable=True, index=True
        )  # Who/what this is reserved for
        reserved_resource_id = Column(String(100), nullable=True, index=True)
        reserved_resource_type = Column(String(50), nullable=True)

        # Time management
        reservation_time = Column(Integer, default=3600, nullable=False)  # Seconds
        reserved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        expires_at = Column(DateTime, nullable=False, index=True)
        allocated_at = Column(DateTime, nullable=True)  # When reservation was fulfilled
        cancelled_at = Column(DateTime, nullable=True)

        # Additional information
        description = Column(Text, nullable=True)
        priority = Column(
            Integer, default=0, nullable=False
        )  # Higher number = higher priority
        tags = Column(JSON, nullable=True)
        custom_fields = Column(JSON, nullable=True)

        # Relationships
        network = relationship("IPNetwork", back_populates="reservations")

        __table_args__ = (
            Index("ix_reservations_tenant_ip", "tenant_id", "ip_address", unique=True),
            Index("ix_reservations_network_status", "network_id", "reservation_status"),
            Index(
                "ix_reservations_reserved_for", "reserved_for", "reserved_resource_id"
            ),
            Index("ix_reservations_expires", "expires_at"),
            Index("ix_reservations_priority", "priority"),
        )

        @hybrid_property
        def is_expired(self):
            """Check if reservation has expired."""
            return datetime.now(timezone.utc) > self.expires_at

        @hybrid_property
        def is_active(self):
            """Check if reservation is currently active."""
            return (
                self.reservation_status == ReservationStatus.RESERVED
                and not self.is_expired
            )

        @hybrid_property
        def minutes_until_expiry(self):
            """Calculate minutes until expiry."""
            if self.expires_at:
                delta = self.expires_at - datetime.now(timezone.utc)
                return max(0, int(delta.total_seconds() / 60))
            return None

        def __repr__(self):
            return f"<IPReservation(id='{self.reservation_id}', ip='{self.ip_address}', status='{self.reservation_status}')>"

else:
    # Create stub classes when SQLAlchemy is not available
    class IPNetwork:
        """IPNetwork model stub."""

        pass

    class IPAllocation:
        """IPAllocation model stub."""

        pass

    class IPReservation:
        """IPReservation model stub."""

        pass
