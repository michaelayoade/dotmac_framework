"""
Tests for IPAM database models.
"""

import ipaddress
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from dotmac.networking.ipam.core.models import (
    SQLALCHEMY_AVAILABLE,
    AllocationStatus,
    NetworkType,
    ReservationStatus,
)


# Test enums first since they don't require SQLAlchemy
class TestEnums:
    """Test IPAM enumeration classes."""

    def test_network_type_values(self):
        """Test NetworkType enum values."""
        assert NetworkType.CUSTOMER == "customer"
        assert NetworkType.INFRASTRUCTURE == "infrastructure"
        assert NetworkType.MANAGEMENT == "management"
        assert NetworkType.SERVICE == "service"
        assert NetworkType.TRANSIT == "transit"
        assert NetworkType.LOOPBACK == "loopback"
        assert NetworkType.POINT_TO_POINT == "point_to_point"

    def test_allocation_status_values(self):
        """Test AllocationStatus enum values."""
        assert AllocationStatus.ALLOCATED == "allocated"
        assert AllocationStatus.RELEASED == "released"
        assert AllocationStatus.EXPIRED == "expired"
        assert AllocationStatus.RESERVED == "reserved"

    def test_reservation_status_values(self):
        """Test ReservationStatus enum values."""
        assert ReservationStatus.RESERVED == "reserved"
        assert ReservationStatus.ALLOCATED == "allocated"
        assert ReservationStatus.EXPIRED == "expired"
        assert ReservationStatus.CANCELLED == "cancelled"


# Only test SQLAlchemy models if available
@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="SQLAlchemy not available")
class TestIPNetworkModel:
    """Test IPNetwork model functionality."""

    def test_network_address_property(self):
        """Test network_address hybrid property."""
        from dotmac.networking.ipam.core.models import IPNetwork

        network = IPNetwork()
        network.cidr = "192.168.1.0/24"

        network_addr = network.network_address
        assert isinstance(network_addr, ipaddress.IPv4Network)
        assert str(network_addr) == "192.168.1.0/24"

    def test_network_address_invalid_cidr(self):
        """Test network_address with invalid CIDR."""
        from dotmac.networking.ipam.core.models import IPNetwork

        network = IPNetwork()
        network.cidr = "invalid_cidr"

        assert network.network_address is None

    def test_total_addresses_property(self):
        """Test total_addresses calculation."""
        from dotmac.networking.ipam.core.models import IPNetwork

        network = IPNetwork()
        network.cidr = "192.168.1.0/24"

        assert network.total_addresses == 256

    def test_usable_addresses_regular_network(self):
        """Test usable_addresses for regular networks."""
        from dotmac.networking.ipam.core.models import IPNetwork

        network = IPNetwork()
        network.cidr = "192.168.1.0/24"

        # Should exclude network and broadcast addresses
        assert network.usable_addresses == 254

    def test_usable_addresses_point_to_point(self):
        """Test usable_addresses for point-to-point networks."""
        from dotmac.networking.ipam.core.models import IPNetwork

        network = IPNetwork()
        network.cidr = "192.168.1.0/30"

        # /30 networks have 2 usable addresses
        assert network.usable_addresses == 2

    def test_usable_addresses_host_route(self):
        """Test usable_addresses for host routes."""
        from dotmac.networking.ipam.core.models import IPNetwork

        network = IPNetwork()
        network.cidr = "192.168.1.1/32"

        # /32 networks have 1 usable address
        assert network.usable_addresses == 1

    def test_usable_addresses_invalid_network(self):
        """Test usable_addresses with invalid network."""
        from dotmac.networking.ipam.core.models import IPNetwork

        network = IPNetwork()
        network.cidr = "invalid"

        assert network.usable_addresses == 0


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="SQLAlchemy not available")
class TestIPAllocationModel:
    """Test IPAllocation model functionality."""

    def test_normalized_mac_address_valid(self):
        """Test MAC address normalization with valid address."""
        from dotmac.networking.ipam.core.models import IPAllocation

        allocation = IPAllocation()
        allocation.mac_address = "AA:BB:CC:DD:EE:FF"

        assert allocation.normalized_mac_address == "aa:bb:cc:dd:ee:ff"

    def test_normalized_mac_address_various_formats(self):
        """Test MAC address normalization with different formats."""
        from dotmac.networking.ipam.core.models import IPAllocation

        test_cases = [
            ("aa-bb-cc-dd-ee-ff", "aa:bb:cc:dd:ee:ff"),
            ("aabbccddeeff", "aa:bb:cc:dd:ee:ff"),
            ("aa.bb.cc.dd.ee.ff", "aa:bb:cc:dd:ee:ff"),
            ("AA:BB:CC:DD:EE:FF", "aa:bb:cc:dd:ee:ff"),
        ]

        for input_mac, expected in test_cases:
            allocation = IPAllocation()
            allocation.mac_address = input_mac
            assert allocation.normalized_mac_address == expected

    def test_normalized_mac_address_invalid(self):
        """Test MAC address normalization with invalid address."""
        from dotmac.networking.ipam.core.models import IPAllocation

        allocation = IPAllocation()
        allocation.mac_address = "invalid_mac"

        # Should return original value for invalid MAC
        assert allocation.normalized_mac_address == "invalid_mac"

    def test_normalized_mac_address_none(self):
        """Test MAC address normalization with None value."""
        from dotmac.networking.ipam.core.models import IPAllocation

        allocation = IPAllocation()
        allocation.mac_address = None

        assert allocation.normalized_mac_address is None

    def test_is_expired_property(self):
        """Test is_expired property."""
        from dotmac.networking.ipam.core.models import IPAllocation

        allocation = IPAllocation()

        # Test non-expired allocation
        allocation.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        assert not allocation.is_expired

        # Test expired allocation
        allocation.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert allocation.is_expired

        # Test allocation without expiry
        allocation.expires_at = None
        assert not allocation.is_expired

    def test_is_active_property(self):
        """Test is_active property."""
        from dotmac.networking.ipam.core.models import AllocationStatus, IPAllocation

        allocation = IPAllocation()
        allocation.allocation_status = AllocationStatus.ALLOCATED
        allocation.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        assert allocation.is_active

        # Test with expired allocation
        allocation.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert not allocation.is_active

        # Test with released allocation
        allocation.allocation_status = AllocationStatus.RELEASED
        allocation.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        assert not allocation.is_active

    def test_days_until_expiry(self):
        """Test days_until_expiry calculation."""
        from dotmac.networking.ipam.core.models import IPAllocation

        allocation = IPAllocation()

        # Test future expiry
        allocation.expires_at = datetime.now(timezone.utc) + timedelta(days=5)
        assert allocation.days_until_expiry >= 4  # Allow for slight timing differences

        # Test past expiry
        allocation.expires_at = datetime.now(timezone.utc) - timedelta(days=2)
        assert allocation.days_until_expiry == 0

        # Test no expiry
        allocation.expires_at = None
        assert allocation.days_until_expiry is None


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="SQLAlchemy not available")
class TestIPReservationModel:
    """Test IPReservation model functionality."""

    def test_is_expired_property(self):
        """Test is_expired property."""
        from dotmac.networking.ipam.core.models import IPReservation

        reservation = IPReservation()

        # Test non-expired reservation
        reservation.expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        assert not reservation.is_expired

        # Test expired reservation
        reservation.expires_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        assert reservation.is_expired

    def test_is_active_property(self):
        """Test is_active property."""
        from dotmac.networking.ipam.core.models import IPReservation, ReservationStatus

        reservation = IPReservation()
        reservation.reservation_status = ReservationStatus.RESERVED
        reservation.expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        assert reservation.is_active

        # Test with expired reservation
        reservation.expires_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        assert not reservation.is_active

        # Test with cancelled reservation
        reservation.reservation_status = ReservationStatus.CANCELLED
        reservation.expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        assert not reservation.is_active

    def test_minutes_until_expiry(self):
        """Test minutes_until_expiry calculation."""
        from dotmac.networking.ipam.core.models import IPReservation

        reservation = IPReservation()

        # Test future expiry
        reservation.expires_at = datetime.now(timezone.utc) + timedelta(minutes=45)
        minutes_left = reservation.minutes_until_expiry
        assert 44 <= minutes_left <= 45  # Allow for timing differences

        # Test past expiry
        reservation.expires_at = datetime.now(timezone.utc) - timedelta(minutes=15)
        assert reservation.minutes_until_expiry == 0

        # Test no expiry
        reservation.expires_at = None
        assert reservation.minutes_until_expiry is None


class TestModelStubs:
    """Test model stubs when SQLAlchemy is not available."""

    @patch('dotmac.networking.ipam.core.models.SQLALCHEMY_AVAILABLE', False)
    def test_model_stubs_exist(self):
        """Test that model stubs are created when SQLAlchemy is unavailable."""
        from dotmac.networking.ipam.core.models import (
            IPAllocation,
            IPNetwork,
            IPReservation,
        )

        # Should be able to instantiate stub classes
        network = IPNetwork()
        allocation = IPAllocation()
        reservation = IPReservation()

        assert network is not None
        assert allocation is not None
        assert reservation is not None
