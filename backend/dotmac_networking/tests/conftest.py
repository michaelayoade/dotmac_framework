"""Pytest configuration for networking tests."""
import pytest
import ipaddress
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_snmp_client():
    """Mock SNMP client."""
    client = Mock()
    client.get = Mock(return_value={"oid": "1.3.6.1.2.1.1.1.0", "value": "Cisco IOS"})
    client.walk = Mock(return_value=[
        {"oid": "1.3.6.1.2.1.2.2.1.1.1", "value": "1"},
        {"oid": "1.3.6.1.2.1.2.2.1.1.2", "value": "2"}
    ])
    client.set = Mock(return_value={"success": True})
    client.get_bulk = Mock(return_value=[{"oid": "1.3.6.1", "value": "test"}])
    return client


@pytest.fixture
def mock_ssh_client():
    """Mock SSH client for device management."""
    client = Mock()
    client.connect = Mock(return_value=True)
    client.send_command = Mock(return_value="Command output\\nSuccess")
    client.send_config_set = Mock(return_value="Configuration applied")
    client.disconnect = Mock(return_value=True)
    client.is_alive = Mock(return_value=True)
    return client


@pytest.fixture
def mock_radius_server():
    """Mock RADIUS server."""
    server = Mock()
    server.authenticate = Mock(return_value={
        "code": "Access-Accept",
        "attributes": {
            "Framed-IP-Address": "192.168.1.100",
            "Session-Timeout": 3600
        }
    })
    server.account = Mock(return_value={"status": "recorded"})
    server.coa = Mock(return_value={"code": "CoA-ACK"})
    return server


@pytest.fixture
def mock_netflow_collector():
    """Mock NetFlow collector."""
    collector = AsyncMock()
    collector.start = AsyncMock(return_value=True)
    collector.stop = AsyncMock(return_value=True)
    collector.get_flows = AsyncMock(return_value=[
        {
            "src_ip": "192.168.1.10",
            "dst_ip": "8.8.8.8",
            "protocol": 6,
            "src_port": 45678,
            "dst_port": 443,
            "bytes": 1024,
            "packets": 10
        }
    ])
    return collector


@pytest.fixture
def sample_network():
    """Sample network for testing."""
    return {
        "network": ipaddress.ip_network("10.0.0.0/8"),
        "subnets": [
            ipaddress.ip_network("10.1.0.0/16"),
            ipaddress.ip_network("10.2.0.0/16"),
            ipaddress.ip_network("10.3.0.0/16")
        ],
        "vlans": [
            {"id": 100, "name": "Management", "subnet": "10.1.0.0/24"},
            {"id": 200, "name": "Users", "subnet": "10.2.0.0/24"},
            {"id": 300, "name": "Servers", "subnet": "10.3.0.0/24"}
        ]
    }


@pytest.fixture
def sample_device():
    """Sample network device."""
    return {
        "id": "DEV-001",
        "hostname": "core-switch-01",
        "ip_address": "10.0.0.1",
        "device_type": "cisco_ios",
        "model": "Catalyst 9300",
        "serial_number": "FCW2140L0NK",
        "location": "DC-1-Rack-42-U20",
        "credentials": {
            "username": "admin",
            "password": "encrypted_password",
            "enable_password": "encrypted_enable"
        },
        "snmp": {
            "version": "v3",
            "community": "encrypted_community",
            "port": 161
        },
        "interfaces": [
            {"name": "GigabitEthernet0/0", "status": "up", "speed": "1000"},
            {"name": "GigabitEthernet0/1", "status": "up", "speed": "1000"}
        ]
    }


@pytest.fixture
def sample_radius_session():
    """Sample RADIUS session."""
    return {
        "session_id": "SES-123456789",
        "username": "user@example.com",
        "nas_ip": "10.0.0.1",
        "nas_port": 1,
        "framed_ip": "192.168.1.100",
        "start_time": datetime.now(),
        "session_timeout": 3600,
        "idle_timeout": 600,
        "service_type": "Framed-User",
        "acct_session_id": "ACC-123456789",
        "calling_station_id": "00:11:22:33:44:55",
        "called_station_id": "AA:BB:CC:DD:EE:FF"
    }


@pytest.fixture
def sample_flow_data():
    """Sample NetFlow/IPFIX data."""
    return {
        "version": 9,
        "source_id": 1,
        "flows": [
            {
                "timestamp": datetime.now(),
                "duration": 60,
                "src_addr": "192.168.1.10",
                "dst_addr": "8.8.8.8",
                "src_port": 54321,
                "dst_port": 53,
                "protocol": 17,  # UDP
                "packets": 2,
                "bytes": 120,
                "tcp_flags": 0,
                "input_iface": 1,
                "output_iface": 2
            },
            {
                "timestamp": datetime.now(),
                "duration": 300,
                "src_addr": "192.168.1.20",
                "dst_addr": "1.1.1.1",
                "src_port": 443,
                "dst_port": 443,
                "protocol": 6,  # TCP
                "packets": 1000,
                "bytes": 500000,
                "tcp_flags": 27,  # SYN, ACK, PSH, FIN
                "input_iface": 1,
                "output_iface": 2
            }
        ]
    }


@pytest.fixture
def mock_database():
    """Mock database for network data."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value={"rows_affected": 1})
    db.fetch_one = AsyncMock(return_value={"id": 1})
    db.fetch_all = AsyncMock(return_value=[{"id": 1}, {"id": 2}])
    return db
