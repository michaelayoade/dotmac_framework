"""
Test configuration and fixtures for dotmac-networking tests.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.query = Mock()
    return session


@pytest.fixture
def sample_network_data():
    """Sample network data for testing."""
    return {
        "network_id": "net-123",
        "tenant_id": "tenant-456",
        "network_name": "Test Network",
        "description": "Test network for unit tests",
        "cidr": "192.168.1.0/24",
        "network_type": "customer",
        "gateway": "192.168.1.1",
        "dns_servers": ["8.8.8.8", "8.8.4.4"],
        "dhcp_enabled": True,
        "site_id": "site-789",
        "vlan_id": 100,
        "location": "Test Location",
        "tags": {"environment": "test"},
        "is_active": True,
    }


@pytest.fixture
def sample_allocation_data():
    """Sample IP allocation data for testing."""
    return {
        "allocation_id": "alloc-123",
        "tenant_id": "tenant-456",
        "network_id": "net-123",
        "ip_address": "192.168.1.10",
        "allocation_type": "dynamic",
        "allocation_status": "allocated",
        "assigned_to": "test-device",
        "assigned_resource_id": "device-123",
        "assigned_resource_type": "device",
        "lease_time": 86400,
        "hostname": "test-host",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "description": "Test allocation",
        "tags": {"type": "test"},
        "allocated_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
    }


@pytest.fixture
def sample_reservation_data():
    """Sample IP reservation data for testing."""
    return {
        "reservation_id": "res-123",
        "tenant_id": "tenant-456",
        "network_id": "net-123",
        "ip_address": "192.168.1.20",
        "reservation_status": "reserved",
        "reserved_for": "test-service",
        "reserved_resource_id": "service-123",
        "reserved_resource_type": "service",
        "reservation_time": 3600,
        "priority": 1,
        "description": "Test reservation",
        "tags": {"type": "test"},
        "reserved_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
    }


@pytest.fixture
def mock_snmp_response():
    """Mock SNMP response data."""
    return {
        "system_info": {
            "name": "test-router",
            "description": "Test Router v1.0",
            "uptime": 864000,
            "contact": "admin@test.com",
            "location": "Test Lab",
        },
        "interfaces": [
            {
                "index": 1,
                "name": "GigabitEthernet0/0",
                "type": "ethernetCsmacd",
                "speed": 1000000000,
                "admin_status": "up",
                "oper_status": "up",
                "in_octets": 1000000,
                "out_octets": 2000000,
                "in_errors": 0,
                "out_errors": 0,
                "utilization": 25.5,
            }
        ],
        "cpu_utilization": 45.2,
        "memory_utilization": 67.8,
    }


@pytest.fixture
def mock_radius_packet():
    """Mock RADIUS packet for testing."""
    packet = Mock()
    packet.code = 1  # Access-Request
    packet.identifier = 123
    packet.authenticator = b"test_authenticator"
    packet.attributes = {
        "User-Name": ["testuser"],
        "User-Password": ["testpass"],
        "NAS-IP-Address": ["192.168.1.1"],
    }
    return packet


@pytest.fixture
def mock_radius_client():
    """Mock RADIUS client for testing."""
    client = Mock()
    client.address = "192.168.1.100"
    client.secret = "shared_secret"
    client.shortname = "test-nas"
    return client


@pytest.fixture
def mock_radius_user():
    """Mock RADIUS user for testing."""
    from dotmac.networking.automation.radius.types import RADIUSUser

    return RADIUSUser(
        username="testuser",
        password="testpass",
        is_active=True,
        attributes={
            "Service-Type": "Framed-User",
            "Framed-IP-Address": "192.168.1.100",
        }
    )


@pytest.fixture
def mock_ssh_connection():
    """Mock SSH connection for testing."""
    conn = AsyncMock()
    conn.run = AsyncMock(return_value=Mock(stdout="Command executed successfully"))
    conn.close = AsyncMock()
    return conn


@pytest.fixture
def sample_device_config():
    """Sample device configuration for testing."""
    return {
        "hostname": "test-router",
        "interfaces": [
            {
                "name": "GigabitEthernet0/0",
                "ip_address": "192.168.1.1",
                "netmask": "255.255.255.0",
                "description": "WAN Interface",
            }
        ],
        "routing": {
            "static_routes": [
                {"network": "0.0.0.0/0", "next_hop": "192.168.1.254"}
            ]
        },
        "access_control": {
            "acls": [
                {
                    "name": "ALLOW_HTTP",
                    "rules": ["permit tcp any any eq 80", "permit tcp any any eq 443"],
                }
            ]
        },
    }


@pytest.fixture
def networking_service_config():
    """Configuration for NetworkingService."""
    return {
        "ipam": {
            "default_subnet_size": 24,
            "dhcp_lease_time": 86400,
            "dns_ttl": 300,
            "enable_ptr_records": True,
            "conflict_detection": True,
        },
        "automation": {
            "ssh_timeout": 30,
            "config_backup_enabled": True,
            "rollback_on_failure": True,
            "concurrent_operations": 5,
            "retry_attempts": 3,
        },
        "monitoring": {
            "snmp_timeout": 10,
            "collection_interval": 60,
            "alert_thresholds": {
                "cpu_utilization": 80,
                "memory_utilization": 85,
                "interface_utilization": 90,
            },
            "community": "public",
        },
        "radius": {
            "auth_port": 1812,
            "acct_port": 1813,
            "coa_port": 3799,
            "session_timeout": 3600,
            "enable_accounting": True,
        },
    }


class MockNetworkModel:
    """Mock network model for testing without SQLAlchemy."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockAllocationModel:
    """Mock allocation model for testing without SQLAlchemy."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockReservationModel:
    """Mock reservation model for testing without SQLAlchemy."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
