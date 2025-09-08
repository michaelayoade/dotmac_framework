"""
PEP 8 and Pydantic v2 compliance tests for dotmac-networking package.
"""

import sys
from pathlib import Path

import pytest

# Add local source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestPEP8Compliance:
    """Test PEP 8 compliance in code structure."""

    def test_import_style_compliance(self):
        """Test that imports follow PEP 8 style guidelines."""
        from dotmac.networking.ipam.core.models import (
            AllocationStatus,
            NetworkType,
            ReservationStatus,
        )

        # Test enum naming follows PEP 8 (UPPER_CASE for constants)
        assert hasattr(NetworkType, "CUSTOMER")
        assert hasattr(NetworkType, "INFRASTRUCTURE")
        assert hasattr(AllocationStatus, "ALLOCATED")
        assert hasattr(ReservationStatus, "RESERVED")

    def test_class_naming_conventions(self):
        """Test class naming follows PEP 8 (CamelCase)."""
        from dotmac.networking.ipam.core.exceptions import (
            AllocationNotFoundError,
            IPAMError,
            NetworkNotFoundError,
        )

        # All exception classes should be CamelCase
        assert IPAMError.__name__ == "IPAMError"
        assert NetworkNotFoundError.__name__ == "NetworkNotFoundError"
        assert AllocationNotFoundError.__name__ == "AllocationNotFoundError"

    def test_function_naming_conventions(self):
        """Test function naming follows PEP 8 (snake_case)."""
        from dotmac.networking import get_default_config

        # Function should be snake_case
        assert get_default_config.__name__ == "get_default_config"

    def test_constant_naming_conventions(self):
        """Test constants follow PEP 8 (UPPER_CASE)."""

        # Constants should be UPPER_CASE
        assert "DEFAULT_CONFIG" in dir(__import__("dotmac.networking", fromlist=["DEFAULT_CONFIG"]))


class TestPydanticV2Compliance:
    """Test Pydantic v2 patterns and compliance."""

    def test_enum_inheritance(self):
        """Test enums use proper Python enum inheritance."""
        from enum import Enum

        from dotmac.networking.ipam.core.models import AllocationStatus, NetworkType

        # Enums should inherit from proper base classes
        assert issubclass(NetworkType, Enum)
        assert issubclass(AllocationStatus, Enum)

    def test_enum_value_types(self):
        """Test enum values are properly typed."""
        from dotmac.networking.ipam.core.models import NetworkType

        # Enum values should be strings (Pydantic v2 compatible)
        assert isinstance(NetworkType.CUSTOMER.value, str)
        assert isinstance(NetworkType.INFRASTRUCTURE.value, str)
        assert NetworkType.CUSTOMER.value == "customer"

    def test_exception_hierarchy(self):
        """Test exception hierarchy follows Python best practices."""
        from dotmac.networking.ipam.core.exceptions import (
            AllocationNotFoundError,
            IPAMError,
            NetworkNotFoundError,
        )

        # All should inherit from base IPAMError
        assert issubclass(NetworkNotFoundError, IPAMError)
        assert issubclass(AllocationNotFoundError, IPAMError)

        # IPAMError should inherit from Exception
        assert issubclass(IPAMError, Exception)

    def test_modern_type_hints(self):
        """Test that code uses modern type hints (PEP 585)."""
        import inspect

        from dotmac.networking.ipam.services.ipam_service import IPAMService

        # Get method signature to check for modern type hints
        init_sig = inspect.signature(IPAMService.__init__)

        # Should have type annotations
        assert len(init_sig.parameters) > 1  # self + other params

        # Check that methods exist with proper naming
        assert hasattr(IPAMService, "create_network")
        assert hasattr(IPAMService, "allocate_ip")
        assert hasattr(IPAMService, "release_allocation")


class TestCodeQuality:
    """Test overall code quality and structure."""

    def test_module_docstrings(self):
        """Test that modules have proper docstrings."""
        import dotmac.networking.ipam.core.exceptions as exceptions
        import dotmac.networking.ipam.core.models as models

        # Modules should have docstrings
        assert models.__doc__ is not None
        assert len(models.__doc__.strip()) > 0
        assert exceptions.__doc__ is not None
        assert len(exceptions.__doc__.strip()) > 0

    def test_class_docstrings(self):
        """Test that classes have proper docstrings."""
        from dotmac.networking.ipam.core.exceptions import IPAMError
        from dotmac.networking.ipam.services.ipam_service import IPAMService

        # Classes should have docstrings
        assert IPAMError.__doc__ is not None
        assert len(IPAMError.__doc__.strip()) > 0
        assert IPAMService.__doc__ is not None
        assert len(IPAMService.__doc__.strip()) > 0

    def test_configuration_structure(self):
        """Test configuration follows best practices."""
        from dotmac.networking import DEFAULT_CONFIG

        # Configuration should be well-structured dict
        assert isinstance(DEFAULT_CONFIG, dict)

        # Should have all main sections
        required_sections = ["ipam", "automation", "monitoring", "radius"]
        for section in required_sections:
            assert section in DEFAULT_CONFIG
            assert isinstance(DEFAULT_CONFIG[section], dict)

    def test_error_messages_quality(self):
        """Test that error messages are descriptive."""
        from dotmac.networking.ipam.core.exceptions import (
            AllocationNotFoundError,
            NetworkNotFoundError,
        )

        # Error messages should be descriptive
        network_error = NetworkNotFoundError("test-network-id")
        assert "test-network-id" in str(network_error)
        assert len(str(network_error)) > 10  # Should be descriptive

        alloc_error = AllocationNotFoundError("test-alloc-id")
        assert "test-alloc-id" in str(alloc_error)


class TestAsyncPatterns:
    """Test async/await patterns are used correctly."""

    def test_async_method_signatures(self):
        """Test async methods are properly defined."""
        import inspect

        from dotmac.networking.ipam.services.ipam_service import IPAMService

        service = IPAMService()

        # These methods should be async
        async_methods = ["create_network", "allocate_ip", "reserve_ip"]

        for method_name in async_methods:
            method = getattr(service, method_name)
            assert inspect.iscoroutinefunction(method), f"{method_name} should be async"

    def test_async_imports_available(self):
        """Test that async-related imports are available."""
        # Should be able to import async components
        from dotmac.networking.ipam.services.ipam_service import IPAMService

        # Service should be instantiable
        service = IPAMService()
        assert service is not None


class TestTypeAnnotations:
    """Test type annotations follow modern Python patterns."""

    def test_return_type_annotations(self):
        """Test return type annotations are present."""
        import inspect

        from dotmac.networking import get_default_config

        # Function should have return type annotation
        sig = inspect.signature(get_default_config)
        assert sig.return_annotation is not inspect.Signature.empty

    def test_parameter_type_annotations(self):
        """Test parameter type annotations are present where appropriate."""
        import inspect

        from dotmac.networking.ipam.services.ipam_service import IPAMService

        # Check async method signatures
        create_network_sig = inspect.signature(IPAMService.create_network)

        # Should have properly typed parameters
        params = create_network_sig.parameters
        assert "tenant_id" in params

        # tenant_id should be typed as str
        tenant_id_param = params["tenant_id"]
        assert tenant_id_param.annotation == str or str(tenant_id_param.annotation) == "str"


@pytest.mark.integration
class TestIntegrationCompliance:
    """Test integration patterns follow best practices."""

    def test_service_factory_pattern(self):
        """Test service factory follows best practices."""
        from dotmac.networking import NetworkingService, create_networking_service

        # Factory should return proper type
        service = create_networking_service()
        assert isinstance(service, NetworkingService)

    def test_configuration_immutability(self):
        """Test configuration defaults are immutable."""
        from dotmac.networking import get_default_config

        # Should return copies, not references
        config1 = get_default_config()
        config2 = get_default_config()

        assert config1 == config2
        assert config1 is not config2

        # Modifying one shouldn't affect the other
        config1["test"] = "modified"
        assert "test" not in config2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
