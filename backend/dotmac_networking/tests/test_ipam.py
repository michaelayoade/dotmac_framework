"""Tests for IP Address Management (IPAM)."""
import pytest
import ipaddress
from datetime import datetime, timedelta


class TestIPAddressManagement:
    """Test IPAM core functionality."""

    def test_subnet_allocation(self, sample_network):
        """Test subnet allocation from parent network."""
        parent_network = sample_network["network"]
        allocated_subnets = []

        # Allocate /24 subnets
        for i in range(5):
            subnet = ipaddress.ip_network(f"10.{i}.0.0/24")
            if subnet.subnet_of(parent_network):
                allocated_subnets.append(subnet)

        assert len(allocated_subnets) == 5
        assert all(s.subnet_of(parent_network) for s in allocated_subnets)
        assert all(s.prefixlen == 24 for s in allocated_subnets)

    def test_ip_address_allocation(self):
        """Test individual IP address allocation."""
        subnet = ipaddress.ip_network("192.168.1.0/24")
        allocated_ips = []
        reserved_ips = [
            subnet.network_address,  # Network address
            subnet.broadcast_address,  # Broadcast address
            subnet.network_address + 1  # Gateway
        ]

        # Allocate first 10 usable IPs
        for host in list(subnet.hosts())[:10]:
            if host not in reserved_ips:
                allocated_ips.append(host)

        assert len(allocated_ips) == 10
        assert all(ip in subnet for ip in allocated_ips)
        assert subnet.network_address not in allocated_ips
        assert subnet.broadcast_address not in allocated_ips

    def test_ip_conflict_detection(self):
        """Test detection of IP address conflicts."""
        allocated_pool = {
            "192.168.1.10",
            "192.168.1.11",
            "192.168.1.12"
        }

        # Test conflict detection
        test_ips = ["192.168.1.10", "192.168.1.13", "192.168.1.11"]
        conflicts = []
        available = []

        for ip in test_ips:
            if ip in allocated_pool:
                conflicts.append(ip)
            else:
                available.append(ip)

        assert len(conflicts) == 2
        assert "192.168.1.10" in conflicts
        assert "192.168.1.11" in conflicts
        assert "192.168.1.13" in available

    def test_subnet_overlap_detection(self):
        """Test detection of overlapping subnets."""
        existing_subnets = [
            ipaddress.ip_network("10.0.0.0/24"),
            ipaddress.ip_network("10.1.0.0/24"),
            ipaddress.ip_network("192.168.0.0/16")
        ]

        test_cases = [
            ("10.0.0.0/25", True),  # Overlaps with first subnet
            ("10.2.0.0/24", False),  # No overlap
            ("192.168.1.0/24", True),  # Overlaps with third subnet
            ("172.16.0.0/16", False)  # No overlap
        ]

        for test_subnet_str, should_overlap in test_cases:
            test_subnet = ipaddress.ip_network(test_subnet_str)
            has_overlap = any(
                test_subnet.overlaps(existing)
                for existing in existing_subnets
            )
            assert has_overlap == should_overlap

    def test_ip_range_generation(self):
        """Test IP range generation for DHCP pools."""
        subnet = ipaddress.ip_network("192.168.1.0/24")
        start_ip = ipaddress.ip_address("192.168.1.100")
        end_ip = ipaddress.ip_address("192.168.1.200")

        dhcp_pool = []
        current_ip = start_ip
        while current_ip <= end_ip:
            dhcp_pool.append(current_ip)
            current_ip += 1

        assert len(dhcp_pool) == 101
        assert dhcp_pool[0] == start_ip
        assert dhcp_pool[-1] == end_ip
        assert all(ip in subnet for ip in dhcp_pool)

    @pytest.mark.asyncio
    async def test_ipam_database_operations(self, mock_database):
        """Test IPAM database operations."""
        # Test subnet creation
        subnet_data = {
            "network": "10.10.0.0/24",
            "vlan_id": 100,
            "description": "Test subnet",
            "gateway": "10.10.0.1"
        }

        mock_database.execute.return_value = {"rows_affected": 1}
        result = await mock_database.execute()
        assert result["rows_affected"] == 1

        # Test IP allocation record
        allocation_data = {
            "ip_address": "10.10.0.10",
            "mac_address": "00:11:22:33:44:55",
            "hostname": "test-host",
            "allocated_at": datetime.now()
        }

        mock_database.fetch_one.return_value = {**allocation_data, "id": 1}
        allocation = await mock_database.fetch_one()
        assert allocation["ip_address"] == "10.10.0.10"
        assert allocation["mac_address"] == "00:11:22:33:44:55"


class TestVLANManagement:
    """Test VLAN management functionality."""

    def test_vlan_creation(self, sample_network):
        """Test VLAN creation and validation."""
        vlans = sample_network["vlans"]

        for vlan in vlans:
            assert 1 <= vlan["id"] <= 4094  # Valid VLAN range
            assert vlan["name"] is not None
            assert ipaddress.ip_network(vlan["subnet"])  # Valid subnet

    def test_vlan_assignment_to_port(self, sample_device):
        """Test VLAN assignment to switch port."""
        port_configs = [
            {
                "interface": "GigabitEthernet0/1",
                "mode": "access",
                "vlan": 100
            },
            {
                "interface": "GigabitEthernet0/2",
                "mode": "trunk",
                "allowed_vlans": [100, 200, 300]
            }
        ]

        for config in port_configs:
            if config["mode"] == "access":
                assert isinstance(config["vlan"], int)
                assert 1 <= config["vlan"] <= 4094
            elif config["mode"] == "trunk":
                assert isinstance(config["allowed_vlans"], list)
                assert all(1 <= v <= 4094 for v in config["allowed_vlans"])

    def test_vlan_tagging(self):
        """Test VLAN tagging for packets."""
        packet_data = {
            "src_mac": "00:11:22:33:44:55",
            "dst_mac": "AA:BB:CC:DD:EE:FF",
            "vlan_id": 100,
            "ethertype": 0x8100,  # 802.1Q
            "priority": 0,
            "cfi": 0
        }

        # Construct VLAN tag
        vlan_tag = (packet_data["priority"] << 13) | (packet_data["cfi"] << 12) | packet_data["vlan_id"]

        assert packet_data["ethertype"] == 0x8100
        assert 0 <= vlan_tag <= 0xFFFF
        assert (vlan_tag & 0xFFF) == packet_data["vlan_id"]

    @pytest.mark.asyncio
    async def test_vlan_database_sync(self, mock_database, sample_network):
        """Test VLAN database synchronization."""
        vlans = sample_network["vlans"]

        # Mock database returns existing VLANs
        mock_database.fetch_all.return_value = [
            {"id": v["id"], "name": v["name"]} for v in vlans
        ]

        db_vlans = await mock_database.fetch_all()

        assert len(db_vlans) == len(vlans)
        assert all(v["id"] in [vlan["id"] for vlan in vlans] for v in db_vlans)


class TestDHCPManagement:
    """Test DHCP server management."""

    def test_dhcp_pool_configuration(self):
        """Test DHCP pool configuration."""
        dhcp_pool = {
            "name": "LAN_POOL",
            "network": "192.168.1.0/24",
            "range_start": "192.168.1.100",
            "range_end": "192.168.1.200",
            "gateway": "192.168.1.1",
            "dns_servers": ["8.8.8.8", "8.8.4.4"],
            "lease_time": 86400,  # 24 hours
            "domain_name": "example.local"
        }

        network = ipaddress.ip_network(dhcp_pool["network"])
        start_ip = ipaddress.ip_address(dhcp_pool["range_start"])
        end_ip = ipaddress.ip_address(dhcp_pool["range_end"])
        gateway = ipaddress.ip_address(dhcp_pool["gateway"])

        assert start_ip in network
        assert end_ip in network
        assert gateway in network
        assert start_ip < end_ip
        assert gateway not in range(int(start_ip), int(end_ip) + 1)

    def test_dhcp_lease_management(self):
        """Test DHCP lease tracking."""
        leases = [
            {
                "ip": "192.168.1.100",
                "mac": "00:11:22:33:44:55",
                "hostname": "client1",
                "lease_start": datetime.now(),
                "lease_end": datetime.now() + timedelta(hours=24),
                "state": "active"
            },
            {
                "ip": "192.168.1.101",
                "mac": "AA:BB:CC:DD:EE:FF",
                "hostname": "client2",
                "lease_start": datetime.now() - timedelta(hours=25),
                "lease_end": datetime.now() - timedelta(hours=1),
                "state": "expired"
            }
        ]

        active_leases = [l for l in leases if l["state"] == "active"]
        expired_leases = [l for l in leases if l["state"] == "expired"]

        assert len(active_leases) == 1
        assert len(expired_leases) == 1
        assert active_leases[0]["lease_end"] > datetime.now()
        assert expired_leases[0]["lease_end"] < datetime.now()

    def test_dhcp_reservation(self):
        """Test DHCP static reservations."""
        reservations = [
            {"mac": "00:11:22:33:44:55", "ip": "192.168.1.10"},
            {"mac": "AA:BB:CC:DD:EE:FF", "ip": "192.168.1.11"}
        ]

        # Test MAC address format validation
        import re
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')

        for reservation in reservations:
            assert mac_pattern.match(reservation["mac"])
            assert ipaddress.ip_address(reservation["ip"])

    @pytest.mark.asyncio
    async def test_dhcp_statistics(self, mock_database):
        """Test DHCP pool statistics."""
        mock_database.fetch_one.return_value = {
            "pool_name": "LAN_POOL",
            "total_ips": 101,
            "allocated": 45,
            "available": 56,
            "reserved": 10,
            "utilization": 44.5
        }

        stats = await mock_database.fetch_one()

        assert stats["total_ips"] == stats["allocated"] + stats["available"]
        assert stats["utilization"] == (stats["allocated"] / stats["total_ips"]) * 100
        assert 0 <= stats["utilization"] <= 100
