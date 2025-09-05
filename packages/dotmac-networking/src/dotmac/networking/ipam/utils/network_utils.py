"""
Network utility functions for IPAM operations.
"""

import ipaddress
from typing import Any, Optional, Union


def validate_cidr(cidr: str, strict: bool = False) -> dict[str, Any]:
    """
    Validate CIDR notation and return network information.

    Args:
        cidr: CIDR string to validate (e.g., "192.168.1.0/24")
        strict: If True, require exact network address

    Returns:
        Dictionary with validation results and network info:
        {
            "valid": bool,
            "network": ipaddress.IPv4Network or ipaddress.IPv6Network or None,
            "network_address": str,
            "broadcast_address": str,
            "total_addresses": int,
            "usable_addresses": int,
            "prefix_length": int,
            "is_private": bool,
            "is_multicast": bool,
            "is_reserved": bool,
            "issues": list[str]
        }
    """
    result = {
        "valid": False,
        "network": None,
        "network_address": None,
        "broadcast_address": None,
        "total_addresses": 0,
        "usable_addresses": 0,
        "prefix_length": 0,
        "is_private": False,
        "is_multicast": False,
        "is_reserved": False,
        "issues": [],
    }

    try:
        network = ipaddress.ip_network(cidr, strict=strict)

        result.update(
            {
                "valid": True,
                "network": network,
                "network_address": str(network.network_address),
                "broadcast_address": str(network.broadcast_address),
                "total_addresses": network.num_addresses,
                "usable_addresses": calculate_usable_addresses(network),
                "prefix_length": network.prefixlen,
                "is_private": network.is_private,
                "is_multicast": network.is_multicast,
                "is_reserved": network.is_reserved,
            }
        )

        # Add warnings for unusual configurations
        if network.prefixlen > 30:
            result["issues"].append(
                f"Very small network (/{network.prefixlen}) with limited addresses"
            )
        elif network.prefixlen < 8:
            result["issues"].append(
                f"Very large network (/{network.prefixlen}) - consider subnetting"
            )

        if network.is_multicast:
            result["issues"].append("Multicast address range")

        if network.is_reserved:
            result["issues"].append("Reserved address range")

    except ValueError as e:
        result["issues"].append(f"Invalid CIDR format: {e}")

    return result


def calculate_usable_addresses(
    network: Union[ipaddress.IPv4Network, ipaddress.IPv6Network],
) -> int:
    """
    Calculate number of usable addresses in a network.

    Args:
        network: IPv4Network or IPv6Network object

    Returns:
        Number of usable addresses (excluding network and broadcast for IPv4, all addresses for IPv6)
    """
    if network.version == 4:
        if network.prefixlen >= 31:
            # /31 and /32 networks have special rules for IPv4
            return 2 if network.prefixlen == 31 else 1
        else:
            # Standard IPv4 networks exclude network and broadcast addresses
            return max(0, network.num_addresses - 2)
    else:
        # IPv6 networks - all addresses are usable (no broadcast concept)
        return network.num_addresses


def calculate_network_info(cidr: str) -> dict[str, Any]:
    """
    Calculate comprehensive network information.

    Args:
        cidr: Network CIDR string

    Returns:
        Dictionary with detailed network information
    """
    validation = validate_cidr(cidr)
    if not validation["valid"]:
        return validation

    network = validation["network"]

    # Calculate subnet information
    info = validation.copy()

    # IPv4/IPv6 specific calculations
    if network.version == 4:
        info.update(
            {
                "network_class": get_network_class(network),
                "subnet_mask": str(network.netmask),
                "wildcard_mask": str(network.hostmask),
                "first_usable": (
                    str(list(network.hosts())[0])
                    if network.num_addresses > 2
                    else str(network.network_address)
                ),
                "last_usable": (
                    str(list(network.hosts())[-1])
                    if network.num_addresses > 2
                    else str(network.broadcast_address)
                ),
                "total_subnets": (
                    2 ** (32 - network.prefixlen) if network.prefixlen < 32 else 1
                ),
                "addresses_per_subnet": network.num_addresses,
            }
        )
    else:
        # IPv6 specific info - avoid generating huge host lists
        info.update(
            {
                "network_class": get_network_class(network),
                "subnet_mask": str(network.netmask),
                "wildcard_mask": str(network.hostmask),
                "first_usable": (
                    str(network.network_address + 1)
                    if network.num_addresses > 1
                    else str(network.network_address)
                ),
                "last_usable": (
                    str(network.broadcast_address - 1)
                    if network.num_addresses > 1
                    else str(network.network_address)
                ),
                "total_subnets": (
                    min(2 ** (128 - network.prefixlen), 2**64)
                    if network.prefixlen < 128
                    else 1
                ),  # Cap at 2^64 for display
                "addresses_per_subnet": network.num_addresses,
            }
        )

    return info


def get_network_class(
    network: Union[ipaddress.IPv4Network, ipaddress.IPv6Network],
) -> str:
    """
    Determine network class for IPv4 or IPv6 type for IPv6.

    Args:
        network: IPv4Network or IPv6Network object

    Returns:
        Network class string ("A", "B", "C", "D", "E" for IPv4, "IPv6-Global", "IPv6-Link-Local", etc. for IPv6)
    """
    if network.version == 4:
        first_octet = int(network.network_address.packed[0])

        if 1 <= first_octet <= 126:
            return "A"
        elif 128 <= first_octet <= 191:
            return "B"
        elif 192 <= first_octet <= 223:
            return "C"
        elif 224 <= first_octet <= 239:
            return "D"  # Multicast
        elif 240 <= first_octet <= 255:
            return "E"  # Reserved
        else:
            return "Unknown"
    else:
        # IPv6 classification
        addr = network.network_address

        if addr.is_link_local:
            return "IPv6-Link-Local"
        elif addr.is_site_local:
            return "IPv6-Site-Local"
        elif addr.is_multicast:
            return "IPv6-Multicast"
        elif addr.is_private:
            return "IPv6-ULA"  # Unique Local Address
        elif addr.is_reserved:
            return "IPv6-Reserved"
        elif addr.is_loopback:
            return "IPv6-Loopback"
        else:
            return "IPv6-Global"


def find_next_available_subnet(
    parent_cidr: str, subnet_size: int, existing_subnets: list[str]
) -> Optional[str]:
    """
    Find next available subnet within a parent network.

    Args:
        parent_cidr: Parent network CIDR
        subnet_size: Desired subnet size (prefix length)
        existing_subnets: List of existing subnet CIDRs to avoid

    Returns:
        Next available subnet CIDR or None if no space available
    """
    try:
        parent_network = ipaddress.ip_network(parent_cidr)

        if subnet_size <= parent_network.prefixlen:
            return None  # Subnet cannot be larger than parent

        # Convert existing subnets to network objects
        existing_networks = []
        for subnet_cidr in existing_subnets:
            try:
                existing_networks.append(ipaddress.ip_network(subnet_cidr))
            except ValueError:
                continue  # Skip invalid CIDRs

        # Generate all possible subnets of the desired size
        for subnet in parent_network.subnets(new_prefix=subnet_size):
            # Check if this subnet overlaps with any existing subnet
            overlaps = False
            for existing in existing_networks:
                if subnet.overlaps(existing):
                    overlaps = True
                    break

            if not overlaps:
                return str(subnet)

        return None  # No available space

    except ValueError:
        return None


def check_ip_in_network(ip_address: str, cidr: str) -> bool:
    """
    Check if an IP address belongs to a network.

    Args:
        ip_address: IP address to check
        cidr: Network CIDR

    Returns:
        True if IP is in network, False otherwise
    """
    try:
        ip = ipaddress.ip_address(ip_address)
        network = ipaddress.ip_network(cidr, strict=False)
        return ip in network
    except ValueError:
        return False


def check_network_overlap(cidr1: str, cidr2: str) -> bool:
    """
    Check if two networks overlap.

    Args:
        cidr1: First network CIDR
        cidr2: Second network CIDR

    Returns:
        True if networks overlap, False otherwise
    """
    try:
        network1 = ipaddress.ip_network(cidr1, strict=False)
        network2 = ipaddress.ip_network(cidr2, strict=False)
        return network1.overlaps(network2)
    except ValueError:
        return False


def suggest_subnet_split(cidr: str, num_subnets: int) -> list[str]:
    """
    Suggest how to split a network into smaller subnets.

    Args:
        cidr: Parent network CIDR
        num_subnets: Desired number of subnets

    Returns:
        List of subnet CIDRs or empty list if not possible
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)

        # Calculate required prefix length
        import math

        prefix_increase = math.ceil(math.log2(num_subnets))
        new_prefix = network.prefixlen + prefix_increase

        if new_prefix > 32:
            return []  # Not possible to create that many subnets

        # Generate subnets
        subnets = list(network.subnets(new_prefix=new_prefix))
        return [str(subnet) for subnet in subnets[:num_subnets]]

    except ValueError:
        return []


def calculate_supernet(cidrs: list[str]) -> Optional[str]:
    """
    Calculate the smallest supernet that contains all given networks.

    Args:
        cidrs: List of network CIDRs

    Returns:
        Supernet CIDR string or None if not possible
    """
    if not cidrs:
        return None

    try:
        networks = [ipaddress.ip_network(cidr, strict=False) for cidr in cidrs]

        if len(networks) == 1:
            return str(networks[0])

        # Find the supernet that contains all networks
        supernet = networks[0]

        for network in networks[1:]:
            # Find common supernet
            while not (network.subnet_of(supernet) or network == supernet):
                if supernet.prefixlen == 0:
                    return None  # Can't go smaller
                supernet = supernet.supernet()

        return str(supernet)

    except ValueError:
        return None


def get_ip_version(address: str) -> Optional[int]:
    """
    Determine IP version (4 or 6) of an address.

    Args:
        address: IP address string

    Returns:
        4 for IPv4, 6 for IPv6, None for invalid
    """
    try:
        ip = ipaddress.ip_address(address)
        return ip.version
    except ValueError:
        return None


def is_valid_mac_address(mac: str) -> bool:
    """
    Validate MAC address format.

    Args:
        mac: MAC address string

    Returns:
        True if valid MAC address format
    """
    import re

    # Common MAC address formats
    patterns = [
        r"^[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}$",  # xx:xx:xx:xx:xx:xx
        r"^[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}$",  # xx-xx-xx-xx-xx-xx
        r"^[0-9A-Fa-f]{12}$",  # Review required: xxxxxxxxx
        r"^[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}$",  # Review required: x.xxxx.xxxx (Cisco format)
    ]

    return any(re.match(pattern, mac) for pattern in patterns)


def normalize_mac_address(mac: str) -> Optional[str]:
    """
    Normalize MAC address to standard colon-separated format.

    Args:
        mac: MAC address in any common format

    Returns:
        Normalized MAC address (xx:xx:xx:xx:xx:xx) or None if invalid
    """
    if not is_valid_mac_address(mac):
        return None

    # Remove separators and normalize to uppercase
    clean_mac = "".join(c.upper() for c in mac if c.isalnum())

    if len(clean_mac) != 12:
        return None

    # Insert colons every 2 characters
    return ":".join(clean_mac[i : i + 2] for i in range(0, 12, 2))


def get_network_address_range(cidr: str) -> Optional[tuple[str, str]]:
    """
    Get first and last IP addresses in a network range.

    Args:
        cidr: Network CIDR string

    Returns:
        Tuple of (first_ip, last_ip) or None if invalid
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        return (str(network.network_address), str(network.broadcast_address))
    except ValueError:
        return None


def get_usable_address_range(cidr: str) -> Optional[tuple[str, str]]:
    """
    Get first and last usable IP addresses in a network.

    Args:
        cidr: Network CIDR string

    Returns:
        Tuple of (first_usable, last_usable) or None if invalid
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)

        if network.prefixlen >= 31:
            # /31 and /32 networks
            return (str(network.network_address), str(network.broadcast_address))
        else:
            # Regular networks - exclude network and broadcast
            hosts = list(network.hosts())
            if hosts:
                return (str(hosts[0]), str(hosts[-1]))
            else:
                return None

    except ValueError:
        return None


def calculate_network_utilization(
    cidr: str, allocated_ips: list[str], reserved_ips: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Calculate network utilization statistics.

    Args:
        cidr: Network CIDR string
        allocated_ips: List of allocated IP addresses
        reserved_ips: Optional list of reserved IP addresses

    Returns:
        Dictionary with utilization statistics
    """
    reserved_ips = reserved_ips or []

    validation = validate_cidr(cidr)
    if not validation["valid"]:
        return {"error": "Invalid CIDR", "issues": validation["issues"]}

    validation["network"]
    usable_addresses = validation["usable_addresses"]

    # Count valid allocated and reserved IPs
    valid_allocated = [ip for ip in allocated_ips if check_ip_in_network(ip, cidr)]
    valid_reserved = [ip for ip in reserved_ips if check_ip_in_network(ip, cidr)]

    allocated_count = len(valid_allocated)
    reserved_count = len(valid_reserved)
    used_count = allocated_count + reserved_count
    available_count = usable_addresses - used_count

    utilization_percent = (
        (used_count / usable_addresses * 100) if usable_addresses > 0 else 0
    )

    return {
        "cidr": cidr,
        "total_addresses": validation["total_addresses"],
        "usable_addresses": usable_addresses,
        "allocated_count": allocated_count,
        "reserved_count": reserved_count,
        "used_count": used_count,
        "available_count": available_count,
        "utilization_percent": round(utilization_percent, 2),
        "is_full": available_count <= 0,
        "warning_threshold_80": utilization_percent >= 80,
        "critical_threshold_95": utilization_percent >= 95,
    }
