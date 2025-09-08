"""
Comprehensive IPAM test fixtures and factories.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock

import pytest


# Test data factories
class IPAMTestDataFactory:
    """Factory for generating IPAM test data."""

    @staticmethod
    def create_network_data(
        tenant_id: str = "test-tenant",
        network_id: str = "test-network",
        cidr: str = "192.168.1.0/24",
        network_type: str = "customer",
        **kwargs
    ) -> Dict[str, Any]:
        """Create network test data."""
        base_data = {
            "tenant_id": tenant_id,
            "network_id": network_id,
            "cidr": cidr,
            "network_name": f"Test Network {network_id}",
            "network_type": network_type,
            "description": f"Test network for {tenant_id}",
            "vlan_id": 100,
            "is_active": True,
            "enable_dhcp": True,
            "dhcp_range_start": None,
            "dhcp_range_end": None,
            "dns_servers": ["8.8.8.8", "8.8.4.4"],
            "domain_name": "test.local",
            "lease_time": 86400,
            "gateway_ip": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        base_data.update(kwargs)
        return base_data

    @staticmethod
    def create_allocation_data(
        tenant_id: str = "test-tenant",
        network_id: str = "test-network",
        ip_address: str = "192.168.1.10",
        **kwargs
    ) -> Dict[str, Any]:
        """Create allocation test data."""
        base_data = {
            "allocation_id": f"alloc-{ip_address.replace('.', '-')}",
            "tenant_id": tenant_id,
            "network_id": network_id,
            "ip_address": ip_address,
            "mac_address": "00:11:22:33:44:55",
            "hostname": f"device-{ip_address.split('.')[-1]}",
            "assigned_to": "test-device",
            "allocation_status": "allocated",
            "lease_start": datetime.now(timezone.utc),
            "lease_end": datetime.now(timezone.utc) + timedelta(hours=24),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        base_data.update(kwargs)
        return base_data

    @staticmethod
    def create_reservation_data(
        tenant_id: str = "test-tenant",
        network_id: str = "test-network",
        ip_address: str = "192.168.1.20",
        **kwargs
    ) -> Dict[str, Any]:
        """Create reservation test data."""
        base_data = {
            "reservation_id": f"res-{ip_address.replace('.', '-')}",
            "tenant_id": tenant_id,
            "network_id": network_id,
            "ip_address": ip_address,
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "description": f"Reserved IP {ip_address}",
            "reserved_by": "test-admin",
            "reservation_status": "reserved",
            "reserved_until": datetime.now(timezone.utc) + timedelta(days=30),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        base_data.update(kwargs)
        return base_data

@pytest.fixture
def ipam_test_factory():
    """Provide IPAM test data factory."""
    return IPAMTestDataFactory()

@pytest.fixture
def mock_database_session():
    """Mock database session with common methods."""
    session = Mock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = Mock()
    session.close = Mock()
    session.query = Mock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    return session

@pytest.fixture
def sample_networks(ipam_test_factory):
    """Sample network data for testing."""
    return [
        ipam_test_factory.create_network_data(
            network_id="net-1",
            cidr="192.168.1.0/24",
            network_type="customer"
        ),
        ipam_test_factory.create_network_data(
            network_id="net-2",
            cidr="10.0.0.0/16",
            network_type="infrastructure"
        ),
        ipam_test_factory.create_network_data(
            network_id="net-3",
            cidr="172.16.0.0/24",
            network_type="management"
        )
    ]

@pytest.fixture
def sample_allocations(ipam_test_factory):
    """Sample allocation data for testing."""
    return [
        ipam_test_factory.create_allocation_data(
            ip_address="192.168.1.10",
            assigned_to="server-1"
        ),
        ipam_test_factory.create_allocation_data(
            ip_address="192.168.1.11",
            assigned_to="workstation-1"
        ),
        ipam_test_factory.create_allocation_data(
            ip_address="192.168.1.12",
            assigned_to="printer-1",
            allocation_status="expired"
        )
    ]

@pytest.fixture
def sample_reservations(ipam_test_factory):
    """Sample reservation data for testing."""
    return [
        ipam_test_factory.create_reservation_data(
            ip_address="192.168.1.20",
            reserved_by="admin-1"
        ),
        ipam_test_factory.create_reservation_data(
            ip_address="192.168.1.21",
            reserved_by="admin-2",
            reservation_status="expired"
        )
    ]

@pytest.fixture
def ipv6_test_data(ipam_test_factory):
    """IPv6 test data for comprehensive testing."""
    return [
        ipam_test_factory.create_network_data(
            network_id="ipv6-net-1",
            cidr="2001:db8::/64",
            network_type="customer"
        ),
        ipam_test_factory.create_allocation_data(
            network_id="ipv6-net-1",
            ip_address="2001:db8::10",
            assigned_to="ipv6-device"
        )
    ]

@pytest.fixture
async def ipam_service_with_data(mock_database_session, sample_networks):
    """IPAM service with test data loaded."""
    try:
        from dotmac.networking.ipam.services.ipam_service import IPAMService

        service = IPAMService(database_session=mock_database_session)

        # Pre-load test networks into in-memory storage
        for network_data in sample_networks:
            service._in_memory_networks[network_data["network_id"]] = network_data

        return service
    except ImportError:
        pytest.skip("IPAMService not available")

# Error scenario fixtures
@pytest.fixture
def database_error_scenarios():
    """Database error scenarios for testing."""
    return {
        "connection_timeout": Exception("Database connection timeout"),
        "constraint_violation": Exception("UNIQUE constraint failed"),
        "foreign_key_error": Exception("Foreign key constraint violation"),
        "deadlock": Exception("Database deadlock detected"),
        "disk_full": Exception("Database disk full")
    }

@pytest.fixture
def network_conflict_scenarios():
    """Network conflict scenarios for testing."""
    return [
        {
            "existing_cidr": "192.168.1.0/24",
            "new_cidr": "192.168.1.0/25",  # Subnet overlap
            "conflict_type": "subnet_overlap"
        },
        {
            "existing_cidr": "10.0.0.0/16",
            "new_cidr": "10.0.1.0/24",     # Contains existing
            "conflict_type": "contains_existing"
        },
        {
            "existing_cidr": "172.16.0.0/24",
            "new_cidr": "172.16.0.0/24",   # Exact duplicate
            "conflict_type": "exact_duplicate"
        }
    ]

# Async test utilities
class AsyncTestHelper:
    """Helper utilities for async testing."""

    @staticmethod
    async def run_with_timeout(coro, timeout=5.0):
        """Run coroutine with timeout."""
        return await asyncio.wait_for(coro, timeout=timeout)

    @staticmethod
    def create_async_mock_with_result(result):
        """Create async mock that returns specific result."""
        mock = AsyncMock()
        mock.return_value = result
        return mock

@pytest.fixture
def async_test_helper():
    """Provide async test helper utilities."""
    return AsyncTestHelper()
