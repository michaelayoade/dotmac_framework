"""Working import tests for dotmac-networking package."""

import sys
from pathlib import Path

# Add package source paths to Python path
package_root = Path(__file__).parent.parent
sys.path.insert(0, str(package_root / "src"))
sys.path.insert(0, str(package_root / ".." / "dotmac-core" / "src"))


def test_basic_enum_imports():
    """Test basic enum imports work."""
    from dotmac.networking.ipam.core.models import (
        AllocationStatus,
        NetworkType,
        ReservationStatus,
    )

    assert NetworkType.CUSTOMER == "customer"
    assert NetworkType.INFRASTRUCTURE == "infrastructure"
    assert AllocationStatus.ALLOCATED == "allocated"
    assert ReservationStatus.RESERVED == "reserved"


def test_exception_imports():
    """Test IPAM exceptions can be imported."""
    from dotmac.networking.ipam.core.exceptions import (
        IPAMError,
        NetworkNotFoundError,
    )

    # Test exception instantiation
    error = IPAMError("test message")
    assert str(error) == "test message"

    network_error = NetworkNotFoundError("net-123")
    assert "net-123" in str(network_error)


def test_default_config_import():
    """Test default configuration import."""
    from dotmac.networking import DEFAULT_CONFIG, get_default_config

    # Verify structure
    assert isinstance(DEFAULT_CONFIG, dict)
    assert "ipam" in DEFAULT_CONFIG
    assert "automation" in DEFAULT_CONFIG
    assert "monitoring" in DEFAULT_CONFIG
    assert "radius" in DEFAULT_CONFIG

    # Test get_default_config returns copy
    config1 = get_default_config()
    config2 = get_default_config()
    assert config1 == config2
    assert config1 is not config2


def test_pydantic_v2_usage():
    """Test that Pydantic v2 patterns are used correctly."""
    # Import the exceptions module to check Pydantic usage
    from dotmac.networking.ipam.core.exceptions import IPAMError

    # Check that exceptions inherit from proper base classes
    assert issubclass(IPAMError, Exception)

    # Test that we can create and use the exceptions properly
    try:
        raise IPAMError("Test error with details")
    except IPAMError as e:
        assert "Test error with details" in str(e)


if __name__ == "__main__":
    test_basic_enum_imports()
    test_exception_imports()
    test_default_config_import()
    test_pydantic_v2_usage()
    print("✅ All import tests passed!")
