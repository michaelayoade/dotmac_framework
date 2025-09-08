"""
Tests for DotMac platform services core functionality.
"""
import os
import sys

# Temporarily adjust path to prioritize platform services
original_path = sys.path[:]
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../packages/dotmac-platform-services/src'))

from dotmac.core import (
    AuthorizationError,
    BaseModel,
    DotMacError,
    TenantContext,
    ValidationError,
)

# Restore original path after imports
sys.path = original_path


def test_base_model_creation():
    """Test BaseModel can be created and used."""
    class TestModel(BaseModel):
        name: str
        value: int = 0

    model = TestModel(name="test", value=42)
    assert model.name == "test"
    assert model.value == 42


def test_tenant_context_creation():
    """Test TenantContext creation and validation."""
    context = TenantContext(
        tenant_id="test_123",
        tenant_name="Test Tenant",
        domain="test.example.com"
    )

    assert context.tenant_id == "test_123"
    assert context.tenant_name == "Test Tenant"
    assert context.domain == "test.example.com"
    assert context.is_active is True


def test_tenant_context_create_default():
    """Test TenantContext create_default factory method."""
    context = TenantContext.create_default()

    assert context.tenant_id is not None
    assert context.tenant_name == "Test Tenant"
    assert context.domain == "test.example.com"
    assert context.is_active is True


def test_dotmac_exceptions():
    """Test DotMac exception hierarchy."""
    # Test base exception
    base_error = DotMacError("Base error message")
    assert str(base_error) == "Base error message"
    assert isinstance(base_error, Exception)

    # Test validation error
    validation_error = ValidationError("Validation failed")
    assert str(validation_error) == "Validation failed"
    assert isinstance(validation_error, DotMacError)

    # Test authorization error
    auth_error = AuthorizationError("Access denied")
    assert str(auth_error) == "Access denied"
    assert isinstance(auth_error, DotMacError)
