"""
Tests for core DotMac models - BaseModel, TenantContext, etc.
"""
import os
import sys

# Adjust path for core package imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../packages/dotmac-core/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../packages/dotmac-platform-services/src'))

import pytest
from pydantic import ValidationError

from dotmac.core import BaseModel, DotMacError
from dotmac.core import ValidationError as DotMacValidationError
from dotmac.models import TenantContext

# Restore path after imports
sys.path = sys.path[2:]


class TestBaseModel:
    """Test suite for BaseModel functionality."""

    def test_base_model_inheritance(self):
        """Test BaseModel can be inherited properly."""
        class TestModel(BaseModel):
            name: str
            value: int = 0

        model = TestModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42

    def test_base_model_validation_assignment(self):
        """Test BaseModel validates on assignment."""
        class TestModel(BaseModel):
            name: str
            count: int

        model = TestModel(name="test", count=1)

        # Valid assignment should work
        model.name = "updated"
        assert model.name == "updated"

        # Invalid assignment should raise error
        with pytest.raises(ValidationError):
            model.count = "not_an_integer"

    def test_base_model_from_attributes(self):
        """Test BaseModel can be created from object attributes."""
        class SourceObject:
            def __init__(self):
                self.name = "source"
                self.value = 123

        class TestModel(BaseModel):
            name: str
            value: int

        source = SourceObject()
        model = TestModel.model_validate(source)

        assert model.name == "source"
        assert model.value == 123

    def test_base_model_serialization(self):
        """Test BaseModel serialization methods."""
        class TestModel(BaseModel):
            name: str
            active: bool = True

        model = TestModel(name="serialize_test")

        # Test dict conversion
        model_dict = model.model_dump()
        assert model_dict == {"name": "serialize_test", "active": True}

        # Test JSON conversion
        json_str = model.model_dump_json()
        assert "serialize_test" in json_str
        assert "true" in json_str.lower()

    def test_base_model_with_complex_types(self):
        """Test BaseModel with complex field types."""
        class ComplexModel(BaseModel):
            name: str
            tags: list[str] = []
            metadata: dict[str, int] = {}
            is_active: bool = True

        model = ComplexModel(
            name="complex_test",
            tags=["tag1", "tag2"],
            metadata={"count": 5, "score": 95}
        )

        assert model.name == "complex_test"
        assert model.tags == ["tag1", "tag2"]
        assert model.metadata["count"] == 5
        assert model.metadata["score"] == 95
        assert model.is_active is True


class TestTenantContext:
    """Test suite for TenantContext model."""

    def test_tenant_context_creation(self):
        """Test TenantContext creation with required fields."""
        context = TenantContext(tenant_id="tenant-123")

        assert context.tenant_id == "tenant-123"
        assert context.tenant_name is None
        assert context.domain is None
        assert context.is_active is True
        assert context.metadata == {}

    def test_tenant_context_full_creation(self):
        """Test TenantContext creation with all fields."""
        context = TenantContext(
            tenant_id="tenant-456",
            tenant_name="Test ISP",
            domain="test-isp.com",
            is_active=True,
            metadata={"region": "us-west", "plan": "enterprise"}
        )

        assert context.tenant_id == "tenant-456"
        assert context.tenant_name == "Test ISP"
        assert context.domain == "test-isp.com"
        assert context.is_active is True
        assert context.metadata["region"] == "us-west"
        assert context.metadata["plan"] == "enterprise"

    def test_tenant_context_create_default(self):
        """Test TenantContext.create_default factory method."""
        context = TenantContext.create_default()

        assert context.tenant_id is not None
        assert context.tenant_name == "Test Tenant"
        assert context.domain == "test.example.com"
        assert context.is_active is True
        assert isinstance(context.metadata, dict)

    def test_tenant_context_validation(self):
        """Test TenantContext validation rules."""
        # Valid tenant_id should work
        context = TenantContext(tenant_id="valid-tenant")
        assert context.tenant_id == "valid-tenant"

        # Empty tenant_id is allowed by this model
        empty_context = TenantContext(tenant_id="")
        assert empty_context.tenant_id == ""

    def test_tenant_context_domain_validation(self):
        """Test domain validation patterns."""
        # Valid domain
        context = TenantContext(
            tenant_id="test",
            domain="valid.example.com"
        )
        assert context.domain == "valid.example.com"

        # None domain should be allowed
        context = TenantContext(tenant_id="test", domain=None)
        assert context.domain is None

    def test_tenant_context_metadata_manipulation(self):
        """Test tenant context metadata manipulation."""
        context = TenantContext(
            tenant_id="test",
            metadata={"initial": "value"}
        )

        # Metadata should be mutable
        context.metadata["new_key"] = "new_value"
        assert context.metadata["new_key"] == "new_value"
        assert context.metadata["initial"] == "value"

    def test_tenant_context_serialization(self):
        """Test TenantContext serialization."""
        context = TenantContext(
            tenant_id="serialize-test",
            tenant_name="Serialize Corp",
            domain="serialize.example.com",
            metadata={"test": True, "version": "1.0"}
        )

        # Test dict serialization
        context_dict = context.model_dump()
        assert context_dict["tenant_id"] == "serialize-test"
        assert context_dict["tenant_name"] == "Serialize Corp"
        assert context_dict["domain"] == "serialize.example.com"
        assert context_dict["is_active"] is True
        assert context_dict["metadata"]["test"] is True
        assert context_dict["metadata"]["version"] == "1.0"

        # Test JSON serialization
        json_str = context.model_dump_json()
        assert "serialize-test" in json_str
        assert "Serialize Corp" in json_str

    def test_tenant_context_equality(self):
        """Test TenantContext equality comparison."""
        context1 = TenantContext(
            tenant_id="same-id",
            tenant_name="Same Name"
        )

        context2 = TenantContext(
            tenant_id="same-id",
            tenant_name="Same Name"
        )

        # They should be equal based on content
        assert context1.model_dump() == context2.model_dump()

        # Different tenant_id should not be equal
        context3 = TenantContext(
            tenant_id="different-id",
            tenant_name="Same Name"
        )

        assert context1.model_dump() != context3.model_dump()

    def test_tenant_context_multiple_instances(self):
        """Test creating multiple TenantContext instances."""
        contexts = []
        for i in range(5):
            context = TenantContext(
                tenant_id=f"tenant-{i}",
                tenant_name=f"Tenant {i}",
                domain=f"tenant{i}.example.com"
            )
            contexts.append(context)

        # Each should have unique data
        assert len(contexts) == 5
        for i, context in enumerate(contexts):
            assert context.tenant_id == f"tenant-{i}"
            assert context.tenant_name == f"Tenant {i}"
            assert context.domain == f"tenant{i}.example.com"


class TestDotMacExceptions:
    """Test suite for DotMac exception models."""

    def test_dotmac_error_creation(self):
        """Test DotMacError exception creation."""
        error = DotMacError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_validation_error_inheritance(self):
        """Test ValidationError inherits from DotMacError."""
        error = DotMacValidationError("Validation failed")

        assert str(error) == "Validation failed"
        assert isinstance(error, DotMacError)
        assert isinstance(error, Exception)

    def test_exception_in_validation_context(self):
        """Test exceptions can be raised in validation contexts."""
        with pytest.raises(DotMacError):
            raise DotMacError("Test context")

        with pytest.raises(DotMacValidationError):
            raise DotMacValidationError("Validation context")

    def test_exception_with_different_messages(self):
        """Test exceptions with various message types."""
        # String message
        error1 = DotMacError("String message")
        assert str(error1) == "String message"

        # Empty message
        error2 = DotMacError("")
        assert str(error2) == ""

        # Complex message
        complex_msg = "Complex error in tenant 'tenant-123' for user 'user-456'"
        error3 = DotMacError(complex_msg)
        assert str(error3) == complex_msg


class TestModelInteractions:
    """Test interactions between different models."""

    def test_tenant_context_in_business_logic(self):
        """Test TenantContext usage in business logic scenarios."""
        active_context = TenantContext(
            tenant_id="active-tenant",
            tenant_name="Active Tenant",
            is_active=True
        )

        inactive_context = TenantContext(
            tenant_id="inactive-tenant",
            tenant_name="Inactive Tenant",
            is_active=False
        )

        # Simulate business logic that checks tenant status
        def is_tenant_active(tenant_context: TenantContext) -> bool:
            return tenant_context.is_active and tenant_context.tenant_id is not None

        assert is_tenant_active(active_context) is True
        assert is_tenant_active(inactive_context) is False

    def test_model_composition(self):
        """Test composing models together."""
        class ServiceModel(BaseModel):
            name: str
            tenant_context: TenantContext
            is_enabled: bool = True

        tenant = TenantContext(
            tenant_id="service-tenant",
            tenant_name="Service Tenant"
        )

        service = ServiceModel(
            name="Test Service",
            tenant_context=tenant
        )

        assert service.name == "Test Service"
        assert service.tenant_context.tenant_id == "service-tenant"
        assert service.tenant_context.tenant_name == "Service Tenant"
        assert service.is_enabled is True

    def test_model_validation_with_nested_structures(self):
        """Test model validation with nested data structures."""
        class ConfigModel(BaseModel):
            tenant: TenantContext
            settings: dict[str, str | int | bool]
            features: list[str]

        tenant = TenantContext(
            tenant_id="config-tenant",
            metadata={"env": "test"}
        )

        config = ConfigModel(
            tenant=tenant,
            settings={
                "timeout": 30,
                "debug": True,
                "api_version": "v1"
            },
            features=["auth", "billing", "monitoring"]
        )

        assert config.tenant.tenant_id == "config-tenant"
        assert config.settings["timeout"] == 30
        assert config.settings["debug"] is True
        assert "auth" in config.features
        assert len(config.features) == 3
