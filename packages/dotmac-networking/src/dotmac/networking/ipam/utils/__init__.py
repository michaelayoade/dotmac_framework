"""IPAM utilities package."""
try:
    from .network_utils import (
        calculate_network_info,
        calculate_network_utilization,
        calculate_supernet,
        check_ip_in_network,
        check_network_overlap,
        find_next_available_subnet,
        get_ip_version,
        get_network_address_range,
        get_usable_address_range,
        is_valid_mac_address,
        normalize_mac_address,
        suggest_subnet_split,
        validate_cidr,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM network utilities not available: {e}")
    validate_cidr = calculate_network_info = None
    find_next_available_subnet = check_ip_in_network = None
    check_network_overlap = suggest_subnet_split = None
    calculate_supernet = get_ip_version = None
    is_valid_mac_address = normalize_mac_address = None
    get_network_address_range = get_usable_address_range = None
    calculate_network_utilization = None

__all__ = [
    "validate_cidr",
    "calculate_network_info",
    "find_next_available_subnet",
    "check_ip_in_network",
    "check_network_overlap",
    "suggest_subnet_split",
    "calculate_supernet",
    "get_ip_version",
    "is_valid_mac_address",
    "normalize_mac_address",
    "get_network_address_range",
    "get_usable_address_range",
    "calculate_network_utilization",
]
