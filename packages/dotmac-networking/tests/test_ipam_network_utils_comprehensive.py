"""
Comprehensive IPAM Network Utils tests for calculations and validation.
"""

import ipaddress
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestIPAMNetworkUtilsComprehensive:
    """Comprehensive tests for IPAM network utility functions."""

    def test_cidr_validation_comprehensive(self):
        """Test comprehensive CIDR validation scenarios."""
        try:
            from dotmac.networking.ipam.utils.network_utils import validate_cidr
        except ImportError:
            pytest.skip("IPAM network utils not available")

        # Valid IPv4 CIDRs
        valid_ipv4 = [
            "192.168.1.0/24",
            "10.0.0.0/8",
            "172.16.0.0/16",
            "192.168.1.1/32",  # Single host
            "10.0.0.0/31",     # Point-to-point
            "0.0.0.0/0"        # Default route
        ]

        for cidr in valid_ipv4:
            assert validate_cidr(cidr) == True, f"Valid CIDR {cidr} should pass"

        # Valid IPv6 CIDRs
        valid_ipv6 = [
            "2001:db8::/64",
            "::1/128",
            "::/0",
            "2001:db8:85a3::/48"
        ]

        for cidr in valid_ipv6:
            assert validate_cidr(cidr) == True, f"Valid IPv6 CIDR {cidr} should pass"

        # Invalid CIDRs
        invalid_cidrs = [
            "192.168.1.0/33",      # Invalid prefix length
            "192.168.256.0/24",    # Invalid IP
            "192.168.1.0",         # Missing prefix
            "not-an-ip/24",        # Invalid format
            "",                    # Empty string
            "192.168.1.0/-1",      # Negative prefix
            "2001:db8::/129"       # Invalid IPv6 prefix
        ]

        for cidr in invalid_cidrs:
            assert validate_cidr(cidr) == False, f"Invalid CIDR {cidr} should fail"

    def test_network_calculations(self):
        """Test network size and address calculations."""
        try:
            from dotmac.networking.ipam.utils.network_utils import (
                get_first_usable_ip,
                get_last_usable_ip,
                get_network_size,
                get_usable_host_count,
            )
        except ImportError:
            pytest.skip("IPAM network utils not available")

        # Test /24 network
        network = "192.168.1.0/24"
        assert get_network_size(network) == 256
        assert get_usable_host_count(network) == 254  # Excluding network/broadcast
        assert get_first_usable_ip(network) == "192.168.1.1"
        assert get_last_usable_ip(network) == "192.168.1.254"

        # Test /30 network (point-to-point)
        p2p_network = "10.0.0.0/30"
        assert get_network_size(p2p_network) == 4
        assert get_usable_host_count(p2p_network) == 2
        assert get_first_usable_ip(p2p_network) == "10.0.0.1"
        assert get_last_usable_ip(p2p_network) == "10.0.0.2"

        # Test /32 network (single host)
        host_network = "192.168.1.100/32"
        assert get_network_size(host_network) == 1
        assert get_usable_host_count(host_network) == 1
        assert get_first_usable_ip(host_network) == "192.168.1.100"
        assert get_last_usable_ip(host_network) == "192.168.1.100"

    def test_ip_range_generation(self):
        """Test IP address range generation."""
        try:
            from dotmac.networking.ipam.utils.network_utils import (
                generate_ip_range,
                get_all_host_addresses,
            )
        except ImportError:
            pytest.skip("IPAM network utils not available")

        # Test small network
        small_range = list(generate_ip_range("192.168.1.0", "192.168.1.5"))
        expected_small = [
            "192.168.1.0", "192.168.1.1", "192.168.1.2",
            "192.168.1.3", "192.168.1.4", "192.168.1.5"
        ]
        assert small_range == expected_small

        # Test /30 network all hosts
        p2p_hosts = list(get_all_host_addresses("10.0.0.0/30"))
        assert len(p2p_hosts) == 4
        assert "10.0.0.0" in p2p_hosts  # Network address
        assert "10.0.0.1" in p2p_hosts
        assert "10.0.0.2" in p2p_hosts
        assert "10.0.0.3" in p2p_hosts  # Broadcast address

        # Test usable hosts only
        usable_hosts = list(get_all_host_addresses("10.0.0.0/30", usable_only=True))
        assert len(usable_hosts) == 2
        assert usable_hosts == ["10.0.0.1", "10.0.0.2"]

    def test_subnet_planning(self):
        """Test subnet planning and allocation."""
        try:
            from dotmac.networking.ipam.utils.network_utils import (
                allocate_subnet,
                find_available_subnet,
                plan_subnets,
            )
        except ImportError:
            pytest.skip("IPAM network utils not available")

        # Test subnet planning for /24 network
        parent_network = "192.168.1.0/24"
        subnet_plan = plan_subnets(parent_network, subnet_size=26)  # /26 subnets

        assert len(subnet_plan) == 4  # /24 can contain 4 /26 subnets
        expected_subnets = [
            "192.168.1.0/26",   # 192.168.1.0-63
            "192.168.1.64/26",  # 192.168.1.64-127
            "192.168.1.128/26", # 192.168.1.128-191
            "192.168.1.192/26"  # 192.168.1.192-255
        ]
        assert subnet_plan == expected_subnets

        # Test subnet allocation
        used_subnets = ["192.168.1.0/26", "192.168.1.128/26"]
        available = find_available_subnet(parent_network, 26, used_subnets)
        assert available in ["192.168.1.64/26", "192.168.1.192/26"]

        # Test no available subnets
        all_used = ["192.168.1.0/26", "192.168.1.64/26", "192.168.1.128/26", "192.168.1.192/26"]
        no_available = find_available_subnet(parent_network, 26, all_used)
        assert no_available is None

    def test_address_math(self):
        """Test IP address arithmetic operations."""
        try:
            from dotmac.networking.ipam.utils.network_utils import (
                ip_add,
                ip_distance,
                ip_subtract,
                next_ip,
                previous_ip,
            )
        except ImportError:
            pytest.skip("IPAM network utils not available")

        # Test IP addition
        assert ip_add("192.168.1.10", 5) == "192.168.1.15"
        assert ip_add("192.168.1.250", 10) == "192.168.2.4"  # Cross octet boundary

        # Test IP subtraction
        assert ip_subtract("192.168.1.15", 5) == "192.168.1.10"
        assert ip_subtract("192.168.2.4", 10) == "192.168.1.250"  # Cross octet boundary

        # Test IP distance
        assert ip_distance("192.168.1.10", "192.168.1.20") == 10
        assert ip_distance("192.168.1.20", "192.168.1.10") == 10  # Absolute distance

        # Test next/previous IP
        assert next_ip("192.168.1.10") == "192.168.1.11"
        assert previous_ip("192.168.1.11") == "192.168.1.10"

        # Test edge cases
        assert next_ip("192.168.1.255") == "192.168.2.0"
        assert previous_ip("192.168.2.0") == "192.168.1.255"

    def test_network_overlap_detection(self):
        """Test network overlap detection algorithms."""
        try:
            from dotmac.networking.ipam.utils.network_utils import (
                find_network_conflicts,
                network_contains,
                networks_overlap,
            )
        except ImportError:
            pytest.skip("IPAM network utils not available")

        # Test exact overlap
        assert networks_overlap("192.168.1.0/24", "192.168.1.0/24") == True

        # Test subnet overlap
        assert networks_overlap("192.168.1.0/24", "192.168.1.0/25") == True
        assert networks_overlap("192.168.1.0/25", "192.168.1.0/24") == True

        # Test partial overlap
        assert networks_overlap("192.168.1.0/25", "192.168.1.128/25") == False

        # Test containment
        assert network_contains("10.0.0.0/16", "10.0.1.0/24") == True
        assert network_contains("10.0.1.0/24", "10.0.0.0/16") == False

        # Test conflict detection
        existing_networks = [
            "192.168.1.0/24",
            "10.0.0.0/16",
            "172.16.0.0/24"
        ]

        # Should find conflict
        conflicts = find_network_conflicts("192.168.1.128/25", existing_networks)
        assert len(conflicts) == 1
        assert "192.168.1.0/24" in conflicts

        # Should find no conflicts
        no_conflicts = find_network_conflicts("192.168.2.0/24", existing_networks)
        assert len(no_conflicts) == 0

    def test_ipv4_ipv6_utilities(self):
        """Test IPv4 and IPv6 utility functions."""
        try:
            from dotmac.networking.ipam.utils.network_utils import (
                convert_to_canonical,
                expand_ipv6,
                ip_version,
                is_ipv4,
                is_ipv6,
            )
        except ImportError:
            pytest.skip("IPAM network utils not available")

        # Test IPv4 detection
        assert is_ipv4("192.168.1.1") == True
        assert is_ipv4("2001:db8::1") == False

        # Test IPv6 detection
        assert is_ipv6("2001:db8::1") == True
        assert is_ipv6("192.168.1.1") == False

        # Test IP version detection
        assert ip_version("192.168.1.1") == 4
        assert ip_version("2001:db8::1") == 6

        # Test canonical conversion
        assert convert_to_canonical("192.168.001.001") == "192.168.1.1"

        # Test IPv6 expansion
        compressed = "2001:db8::1"
        expanded = expand_ipv6(compressed)
        assert expanded == "2001:0db8:0000:0000:0000:0000:0000:0001"

        # Test IPv6 compression
        full_addr = "2001:0db8:0000:0000:0000:0000:0000:0001"
        compressed_result = convert_to_canonical(full_addr)
        assert compressed_result == "2001:db8::1"

    def test_network_summarization(self):
        """Test network summarization and aggregation."""
        try:
            from dotmac.networking.ipam.utils.network_utils import (
                aggregate_routes,
                find_supernet,
                summarize_networks,
            )
        except ImportError:
            pytest.skip("IPAM network utils not available")

        # Test basic summarization
        networks = [
            "192.168.1.0/26",
            "192.168.1.64/26",
            "192.168.1.128/26",
            "192.168.1.192/26"
        ]

        summary = summarize_networks(networks)
        assert summary == ["192.168.1.0/24"]  # All /26s can be summarized to /24

        # Test partial summarization
        partial_networks = [
            "192.168.1.0/26",
            "192.168.1.64/26",
            "192.168.2.0/26"  # Different /24, can't be summarized
        ]

        partial_summary = summarize_networks(partial_networks)
        assert len(partial_summary) >= 2  # Should have at least 2 summary routes
        assert "192.168.1.0/25" in partial_summary  # First two can be summarized

        # Test supernet finding
        subnet_list = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
        supernet = find_supernet(subnet_list)
        # Supernet should be able to contain all subnets
        supernet_network = ipaddress.IPv4Network(supernet)
        for subnet in subnet_list:
            subnet_network = ipaddress.IPv4Network(subnet)
            assert subnet_network.subnet_of(supernet_network)

    def test_dhcp_range_calculations(self):
        """Test DHCP range calculation utilities."""
        try:
            from dotmac.networking.ipam.utils.network_utils import (
                calculate_dhcp_range,
                exclude_static_ranges,
                validate_dhcp_range,
            )
        except ImportError:
            pytest.skip("IPAM network utils not available")

        # Test automatic DHCP range calculation
        network = "192.168.1.0/24"
        dhcp_range = calculate_dhcp_range(network)

        # Should exclude first and last 10% for static assignments
        assert dhcp_range["start"] == "192.168.1.26"  # ~10% of 254 = 25 IPs reserved
        assert dhcp_range["end"] == "192.168.1.229"   # Last ~10% reserved

        # Test custom DHCP range validation
        valid_range = validate_dhcp_range(network, "192.168.1.100", "192.168.1.200")
        assert valid_range == True

        # Test invalid DHCP range
        invalid_range = validate_dhcp_range(network, "192.168.2.100", "192.168.2.200")
        assert invalid_range == False  # Outside network

        # Test static range exclusion
        full_range = ("192.168.1.10", "192.168.1.240")
        static_ranges = [
            ("192.168.1.50", "192.168.1.60"),   # Exclude servers
            ("192.168.1.200", "192.168.1.210")  # Exclude printers
        ]

        available_ranges = exclude_static_ranges(full_range, static_ranges)
        assert len(available_ranges) == 3  # Should split into 3 ranges
        assert ("192.168.1.10", "192.168.1.49") in available_ranges
        assert ("192.168.1.61", "192.168.1.199") in available_ranges
        assert ("192.168.1.211", "192.168.1.240") in available_ranges


# Mock implementations for network utilities if module doesn't exist
try:
    from dotmac.networking.ipam.utils.network_utils import validate_cidr
except ImportError:
    # Create mock implementations for testing

    # Mock network_utils module
    class MockNetworkUtils:
        @staticmethod
        def validate_cidr(cidr: str) -> bool:
            """Mock CIDR validation."""
            try:
                network = ipaddress.ip_network(cidr, strict=False)
                return True
            except ValueError:
                return False

        @staticmethod
        def get_network_size(cidr: str) -> int:
            """Mock network size calculation."""
            return int(ipaddress.ip_network(cidr).num_addresses)

        @staticmethod
        def get_usable_host_count(cidr: str) -> int:
            """Mock usable host count."""
            network = ipaddress.ip_network(cidr)
            if network.prefixlen == 32:  # /32 network
                return 1
            elif network.prefixlen == 31:  # /31 network (point-to-point)
                return 2
            else:
                return int(network.num_addresses - 2)  # Exclude network/broadcast

        @staticmethod
        def get_first_usable_ip(cidr: str) -> str:
            """Mock first usable IP."""
            network = ipaddress.ip_network(cidr)
            if network.prefixlen >= 31:
                return str(network.network_address)
            return str(network.network_address + 1)

        @staticmethod
        def get_last_usable_ip(cidr: str) -> str:
            """Mock last usable IP."""
            network = ipaddress.ip_network(cidr)
            if network.prefixlen == 32:
                return str(network.network_address)
            elif network.prefixlen == 31:
                return str(network.broadcast_address)
            return str(network.broadcast_address - 1)

        @staticmethod
        def generate_ip_range(start_ip: str, end_ip: str):
            """Mock IP range generation."""
            start = ipaddress.ip_address(start_ip)
            end = ipaddress.ip_address(end_ip)
            current = start
            while current <= end:
                yield str(current)
                current += 1

        @staticmethod
        def get_all_host_addresses(cidr: str, usable_only: bool = False):
            """Mock host address generation."""
            network = ipaddress.ip_network(cidr)
            if usable_only and network.prefixlen < 31:
                # Skip network and broadcast addresses
                for host in list(network.hosts()):
                    yield str(host)
            else:
                # Include all addresses
                for addr in network:
                    yield str(addr)

        @staticmethod
        def plan_subnets(parent_cidr: str, subnet_size: int):
            """Mock subnet planning."""
            parent = ipaddress.ip_network(parent_cidr)
            return [str(subnet) for subnet in parent.subnets(new_prefix=subnet_size)]

        @staticmethod
        def find_available_subnet(parent_cidr: str, subnet_size: int, used_subnets: list):
            """Mock available subnet finding."""
            all_subnets = MockNetworkUtils.plan_subnets(parent_cidr, subnet_size)
            for subnet in all_subnets:
                if subnet not in used_subnets:
                    return subnet
            return None

        @staticmethod
        def ip_add(ip: str, count: int) -> str:
            """Mock IP addition."""
            return str(ipaddress.ip_address(ip) + count)

        @staticmethod
        def ip_subtract(ip: str, count: int) -> str:
            """Mock IP subtraction."""
            return str(ipaddress.ip_address(ip) - count)

        @staticmethod
        def ip_distance(ip1: str, ip2: str) -> int:
            """Mock IP distance calculation."""
            return abs(int(ipaddress.ip_address(ip2)) - int(ipaddress.ip_address(ip1)))

        @staticmethod
        def next_ip(ip: str) -> str:
            """Mock next IP."""
            return str(ipaddress.ip_address(ip) + 1)

        @staticmethod
        def previous_ip(ip: str) -> str:
            """Mock previous IP."""
            return str(ipaddress.ip_address(ip) - 1)

        @staticmethod
        def networks_overlap(cidr1: str, cidr2: str) -> bool:
            """Mock network overlap detection."""
            net1 = ipaddress.ip_network(cidr1)
            net2 = ipaddress.ip_network(cidr2)
            return net1.overlaps(net2)

        @staticmethod
        def network_contains(parent_cidr: str, child_cidr: str) -> bool:
            """Mock network containment check."""
            parent = ipaddress.ip_network(parent_cidr)
            child = ipaddress.ip_network(child_cidr)
            return child.subnet_of(parent)

        @staticmethod
        def find_network_conflicts(new_cidr: str, existing_cidrs: list) -> list:
            """Mock network conflict detection."""
            conflicts = []
            new_net = ipaddress.ip_network(new_cidr)
            for existing in existing_cidrs:
                existing_net = ipaddress.ip_network(existing)
                if new_net.overlaps(existing_net):
                    conflicts.append(existing)
            return conflicts

        @staticmethod
        def is_ipv4(ip: str) -> bool:
            """Mock IPv4 detection."""
            try:
                ipaddress.IPv4Address(ip)
                return True
            except ValueError:
                return False

        @staticmethod
        def is_ipv6(ip: str) -> bool:
            """Mock IPv6 detection."""
            try:
                ipaddress.IPv6Address(ip)
                return True
            except ValueError:
                return False

        @staticmethod
        def ip_version(ip: str) -> int:
            """Mock IP version detection."""
            try:
                addr = ipaddress.ip_address(ip)
                return addr.version
            except ValueError:
                return None

        @staticmethod
        def convert_to_canonical(ip: str) -> str:
            """Mock canonical conversion."""
            return str(ipaddress.ip_address(ip))

        @staticmethod
        def expand_ipv6(ip: str) -> str:
            """Mock IPv6 expansion."""
            return str(ipaddress.IPv6Address(ip).exploded)

        @staticmethod
        def summarize_networks(cidrs: list) -> list:
            """Mock network summarization."""
            networks = [ipaddress.ip_network(cidr) for cidr in cidrs]
            summarized = list(ipaddress.collapse_addresses(networks))
            return [str(net) for net in summarized]

        @staticmethod
        def find_supernet(cidrs: list) -> str:
            """Mock supernet finding."""
            networks = [ipaddress.ip_network(cidr) for cidr in cidrs]
            return str(ipaddress.ip_network(f"{min(net.network_address for net in networks)}/{min(net.prefixlen for net in networks) - 1}"))

        @staticmethod
        def calculate_dhcp_range(cidr: str) -> dict:
            """Mock DHCP range calculation."""
            network = ipaddress.ip_network(cidr)
            hosts = list(network.hosts())
            if len(hosts) < 20:  # Small network
                return {"start": str(hosts[0]), "end": str(hosts[-1])}

            # Reserve first and last 10% for static
            reserve_count = max(1, len(hosts) // 10)
            return {
                "start": str(hosts[reserve_count]),
                "end": str(hosts[-(reserve_count + 1)])
            }

        @staticmethod
        def validate_dhcp_range(cidr: str, start_ip: str, end_ip: str) -> bool:
            """Mock DHCP range validation."""
            network = ipaddress.ip_network(cidr)
            start = ipaddress.ip_address(start_ip)
            end = ipaddress.ip_address(end_ip)
            return start in network and end in network

        @staticmethod
        def exclude_static_ranges(full_range: tuple, static_ranges: list) -> list:
            """Mock static range exclusion."""
            start_ip = ipaddress.ip_address(full_range[0])
            end_ip = ipaddress.ip_address(full_range[1])

            # Sort static ranges by start IP
            static_sorted = sorted([(ipaddress.ip_address(s), ipaddress.ip_address(e)) for s, e in static_ranges])

            available = []
            current = start_ip

            for static_start, static_end in static_sorted:
                if current < static_start:
                    available.append((str(current), str(static_start - 1)))
                current = max(current, static_end + 1)

            if current <= end_ip:
                available.append((str(current), str(end_ip)))

            return available

    # Inject mock functions into the namespace
    mock_utils = MockNetworkUtils()
    for attr_name in dir(mock_utils):
        if not attr_name.startswith('_'):
            globals()[attr_name] = getattr(mock_utils, attr_name)
