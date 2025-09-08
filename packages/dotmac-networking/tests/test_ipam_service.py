"""
Tests for IPAM Service - Core business logic for IP address management.
"""

import ipaddress
from unittest.mock import Mock, patch
from uuid import UUID

import pytest

from dotmac.networking.ipam.core.exceptions import (
    AllocationNotFoundError,
    IPAddressConflictError,
    IPAMError,
    NetworkNotFoundError,
    NetworkOverlapError,
)
from dotmac.networking.ipam.services.ipam_service import IPAMService


class TestIPAMServiceInitialization:
    """Test IPAM service initialization and configuration."""

    def test_init_default_config(self):
        """Test initialization with default configuration."""
        service = IPAMService()

        assert service.db is None
        assert service.config == {}
        assert service.default_lease_time == 86400
        assert service.max_lease_time == 2592000
        assert service.default_reservation_time == 3600
        assert service.auto_release_expired is True
        assert service.conflict_detection is True

    def test_init_custom_config(self):
        """Test initialization with custom configuration."""
        config = {
            "allocation": {
                "default_lease_time": 7200,
                "max_lease_time": 604800,
                "auto_release_expired": False,
                "conflict_detection": False,
            },
            "reservation": {
                "default_reservation_time": 1800,
            },
        }

        service = IPAMService(config=config)

        assert service.default_lease_time == 7200
        assert service.max_lease_time == 604800
        assert service.default_reservation_time == 1800
        assert service.auto_release_expired is False
        assert service.conflict_detection is False

    def test_use_database_with_session(self):
        """Test _use_database returns True when session provided."""
        mock_session = Mock()
        service = IPAMService(database_session=mock_session)

        # Mock the required modules as available
        with patch('dotmac.networking.ipam.services.ipam_service.SQLALCHEMY_AVAILABLE', True):
            with patch('dotmac.networking.ipam.services.ipam_service.MODELS_AVAILABLE', True):
                assert service._use_database() is True

    def test_use_database_without_session(self):
        """Test _use_database returns False without session."""
        service = IPAMService()
        assert service._use_database() is False


class TestIPAMServiceNetworkManagement:
    """Test network creation and management functionality."""

    @pytest.mark.asyncio
    async def test_create_network_success(self, sample_network_data):
        """Test successful network creation."""
        service = IPAMService()

        result = await service.create_network("tenant-123", **sample_network_data)

        assert result["network_id"] == sample_network_data["network_id"]
        assert result["tenant_id"] == "tenant-123"
        assert result["cidr"] == sample_network_data["cidr"]
        assert result["network_type"] == sample_network_data["network_type"]
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_network_with_auto_id(self, sample_network_data):
        """Test network creation with auto-generated ID."""
        service = IPAMService()
        data = sample_network_data.copy()
        del data["network_id"]

        result = await service.create_network("tenant-123", **data)

        assert "network_id" in result
        assert result["network_id"] != sample_network_data["network_id"]
        # Should be a valid UUID
        UUID(result["network_id"])

    @pytest.mark.asyncio
    async def test_create_network_invalid_cidr(self, sample_network_data):
        """Test network creation with invalid CIDR."""
        service = IPAMService()
        data = sample_network_data.copy()
        data["cidr"] = "invalid.cidr.format"

        with pytest.raises(ValueError):
            await service.create_network("tenant-123", **data)

    @pytest.mark.asyncio
    async def test_create_network_duplicate_id(self, sample_network_data):
        """Test network creation with duplicate ID."""
        service = IPAMService()

        # Create first network
        await service.create_network("tenant-123", **sample_network_data)

        # Try to create duplicate
        with pytest.raises(IPAMError, match="Network already exists"):
            await service.create_network("tenant-123", **sample_network_data)

    @pytest.mark.asyncio
    async def test_create_network_overlap_detection(self, sample_network_data):
        """Test network overlap detection."""
        config = {"network": {"allow_overlapping_networks": False}}
        service = IPAMService(config=config)

        # Create first network
        await service.create_network("tenant-123", **sample_network_data)

        # Try to create overlapping network
        overlap_data = sample_network_data.copy()
        overlap_data["network_id"] = "net-456"
        overlap_data["cidr"] = "192.168.1.128/25"  # Overlaps with /24

        with pytest.raises(NetworkOverlapError):
            await service.create_network("tenant-123", **overlap_data)

    @pytest.mark.asyncio
    async def test_get_network_utilization(self, sample_network_data):
        """Test network utilization calculation."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Get utilization for empty network
        util = await service.get_network_utilization("tenant-123", sample_network_data["network_id"])

        assert util["network_id"] == sample_network_data["network_id"]
        assert util["total_addresses"] == 256
        assert util["usable_addresses"] == 254
        assert util["allocated_addresses"] == 0
        assert util["reserved_addresses"] == 0
        assert util["available_addresses"] == 254
        assert util["utilization_percent"] == 0.0


class TestIPAMServiceIPAllocation:
    """Test IP address allocation functionality."""

    @pytest.mark.asyncio
    async def test_allocate_ip_success(self, sample_network_data):
        """Test successful IP allocation."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Allocate IP
        allocation = await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            assigned_to="test-device",
            hostname="test-host",
            mac_address="aa:bb:cc:dd:ee:ff"
        )

        assert "allocation_id" in allocation
        assert allocation["tenant_id"] == "tenant-123"
        assert allocation["network_id"] == sample_network_data["network_id"]
        assert allocation["allocation_status"] == "allocated"
        assert allocation["assigned_to"] == "test-device"
        assert allocation["hostname"] == "test-host"
        assert allocation["mac_address"] == "aa:bb:cc:dd:ee:ff"

        # IP should be in network range
        ip_addr = ipaddress.ip_address(allocation["ip_address"])
        network = ipaddress.ip_network(sample_network_data["cidr"])
        assert ip_addr in network

    @pytest.mark.asyncio
    async def test_allocate_specific_ip(self, sample_network_data):
        """Test allocation of specific IP address."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Allocate specific IP
        requested_ip = "192.168.1.100"
        allocation = await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            ip_address=requested_ip,
            assigned_to="test-device"
        )

        assert allocation["ip_address"] == requested_ip

    @pytest.mark.asyncio
    async def test_allocate_ip_outside_network(self, sample_network_data):
        """Test allocation of IP outside network range."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Try to allocate IP outside network
        with pytest.raises(IPAMError, match="not in network"):
            await service.allocate_ip(
                "tenant-123",
                network_id=sample_network_data["network_id"],
                ip_address="10.0.0.1"  # Outside 192.168.1.0/24
            )

    @pytest.mark.asyncio
    async def test_allocate_ip_conflict_detection(self, sample_network_data):
        """Test IP conflict detection."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Allocate IP first time
        ip_address = "192.168.1.100"
        await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            ip_address=ip_address
        )

        # Try to allocate same IP again
        with pytest.raises(IPAddressConflictError):
            await service.allocate_ip(
                "tenant-123",
                network_id=sample_network_data["network_id"],
                ip_address=ip_address
            )

    @pytest.mark.asyncio
    async def test_allocate_ip_network_not_found(self):
        """Test allocation with non-existent network."""
        service = IPAMService()

        with pytest.raises(NetworkNotFoundError):
            await service.allocate_ip(
                "tenant-123",
                network_id="non-existent-network"
            )

    @pytest.mark.asyncio
    async def test_allocate_ip_custom_lease_time(self, sample_network_data):
        """Test allocation with custom lease time."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Allocate with custom lease time
        custom_lease = 7200  # 2 hours
        allocation = await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            lease_time=custom_lease
        )

        assert allocation["lease_time"] == custom_lease

    @pytest.mark.asyncio
    async def test_allocate_ip_lease_time_limit(self, sample_network_data):
        """Test lease time is limited by max_lease_time."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Try to allocate with excessive lease time
        excessive_lease = service.max_lease_time + 1000
        allocation = await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            lease_time=excessive_lease
        )

        # Should be limited to max_lease_time
        assert allocation["lease_time"] == service.max_lease_time


class TestIPAMServiceIPReservation:
    """Test IP address reservation functionality."""

    @pytest.mark.asyncio
    async def test_reserve_ip_success(self, sample_network_data):
        """Test successful IP reservation."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Reserve IP
        ip_address = "192.168.1.50"
        reservation = await service.reserve_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            ip_address=ip_address,
            reserved_for="test-service",
            description="Test reservation"
        )

        assert "reservation_id" in reservation
        assert reservation["tenant_id"] == "tenant-123"
        assert reservation["network_id"] == sample_network_data["network_id"]
        assert reservation["ip_address"] == ip_address
        assert reservation["reservation_status"] == "reserved"
        assert reservation["reserved_for"] == "test-service"
        assert reservation["description"] == "Test reservation"

    @pytest.mark.asyncio
    async def test_reserve_ip_outside_network(self, sample_network_data):
        """Test reservation of IP outside network range."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Try to reserve IP outside network
        with pytest.raises(IPAMError, match="not in network"):
            await service.reserve_ip(
                "tenant-123",
                network_id=sample_network_data["network_id"],
                ip_address="10.0.0.1"  # Outside 192.168.1.0/24
            )

    @pytest.mark.asyncio
    async def test_reserve_ip_conflict_with_allocation(self, sample_network_data):
        """Test reservation conflict with existing allocation."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Allocate IP first
        ip_address = "192.168.1.75"
        await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            ip_address=ip_address
        )

        # Try to reserve same IP
        with pytest.raises(IPAddressConflictError):
            await service.reserve_ip(
                "tenant-123",
                network_id=sample_network_data["network_id"],
                ip_address=ip_address
            )

    @pytest.mark.asyncio
    async def test_reserve_ip_custom_reservation_time(self, sample_network_data):
        """Test reservation with custom reservation time."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Reserve with custom time
        custom_time = 1800  # 30 minutes
        reservation = await service.reserve_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            ip_address="192.168.1.200",
            reservation_time=custom_time
        )

        assert reservation["reservation_time"] == custom_time


class TestIPAMServiceReleaseAllocation:
    """Test allocation release functionality."""

    @pytest.mark.asyncio
    async def test_release_allocation_success(self, sample_network_data):
        """Test successful allocation release."""
        service = IPAMService()

        # Create network and allocate IP
        await service.create_network("tenant-123", **sample_network_data)
        allocation = await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"]
        )

        # Release allocation
        released = await service.release_allocation(
            "tenant-123",
            allocation["allocation_id"]
        )

        assert released["allocation_status"] == "released"
        assert "released_at" in released
        assert released["released_at"] is not None

    @pytest.mark.asyncio
    async def test_release_allocation_not_found(self):
        """Test release of non-existent allocation."""
        service = IPAMService()

        with pytest.raises(AllocationNotFoundError):
            await service.release_allocation(
                "tenant-123",
                "non-existent-allocation"
            )


class TestIPAMServiceHelperMethods:
    """Test internal helper methods."""

    @pytest.mark.asyncio
    async def test_check_network_overlap_no_overlap(self):
        """Test network overlap detection with no overlap."""
        service = IPAMService()

        # Create first network
        await service.create_network("tenant-123", cidr="192.168.1.0/24", network_id="net-1")

        # Check for overlap with non-overlapping network
        overlap = await service._check_network_overlap("tenant-123", "192.168.2.0/24")
        assert overlap is None

    @pytest.mark.asyncio
    async def test_check_network_overlap_with_overlap(self):
        """Test network overlap detection with overlap."""
        service = IPAMService()

        # Create first network
        await service.create_network("tenant-123", cidr="192.168.1.0/24", network_id="net-1")

        # Check for overlap with overlapping network
        overlap = await service._check_network_overlap("tenant-123", "192.168.1.128/25")
        assert overlap == "192.168.1.0/24"

    @pytest.mark.asyncio
    async def test_check_ip_conflict_no_conflict(self):
        """Test IP conflict detection with no conflict."""
        service = IPAMService()

        conflict = await service._check_ip_conflict("tenant-123", "192.168.1.100")
        assert conflict is False

    @pytest.mark.asyncio
    async def test_check_ip_conflict_with_allocation(self, sample_network_data):
        """Test IP conflict detection with existing allocation."""
        service = IPAMService()

        # Create network and allocate IP
        await service.create_network("tenant-123", **sample_network_data)
        await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            ip_address="192.168.1.100"
        )

        # Check for conflict
        conflict = await service._check_ip_conflict("tenant-123", "192.168.1.100")
        assert conflict is True

    @pytest.mark.asyncio
    async def test_find_next_available_ip(self, sample_network_data):
        """Test finding next available IP."""
        service = IPAMService()

        network = ipaddress.ip_network(sample_network_data["cidr"])
        next_ip = await service._find_next_available_ip("tenant-123", network)

        # Should be first host IP in range
        assert next_ip == ipaddress.ip_address("192.168.1.1")

    @pytest.mark.asyncio
    async def test_find_next_available_ip_with_allocations(self, sample_network_data):
        """Test finding next available IP with existing allocations."""
        service = IPAMService()

        # Create network and allocate first few IPs
        await service.create_network("tenant-123", **sample_network_data)
        await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            ip_address="192.168.1.1"
        )
        await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            ip_address="192.168.1.2"
        )

        network = ipaddress.ip_network(sample_network_data["cidr"])
        next_ip = await service._find_next_available_ip("tenant-123", network)

        # Should skip allocated IPs and return next available
        assert next_ip == ipaddress.ip_address("192.168.1.3")


class TestIPAMServiceUtilization:
    """Test network utilization calculation with allocations."""

    @pytest.mark.asyncio
    async def test_utilization_with_allocations_and_reservations(self, sample_network_data):
        """Test utilization calculation with allocations and reservations."""
        service = IPAMService()

        # Create network
        await service.create_network("tenant-123", **sample_network_data)

        # Make some allocations
        await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            ip_address="192.168.1.10"
        )
        await service.allocate_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            ip_address="192.168.1.11"
        )

        # Make a reservation
        await service.reserve_ip(
            "tenant-123",
            network_id=sample_network_data["network_id"],
            ip_address="192.168.1.20"
        )

        # Check utilization
        util = await service.get_network_utilization("tenant-123", sample_network_data["network_id"])

        assert util["allocated_addresses"] == 2
        assert util["reserved_addresses"] == 1
        assert util["available_addresses"] == 251  # 254 - 2 - 1
        assert util["utilization_percent"] == round((3 / 254) * 100, 2)
