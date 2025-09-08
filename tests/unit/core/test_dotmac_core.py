"""
Tests for DotMac core functionality - Base models and exceptions.
"""
from dotmac.core import (
    AuthorizationError,
    BaseModel,
    DotMacError,
    TenantContext,
    ValidationError,
)


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


def test_tenant_context_defaults():
    """Test TenantContext default values."""
    context = TenantContext(tenant_id="test_123")

    assert context.tenant_id == "test_123"
    assert context.tenant_name is None
    assert context.domain is None
    assert context.is_active is True
    assert context.metadata == {}


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
    assert isinstance(validation_error, Exception)

    # Test authorization error
    auth_error = AuthorizationError("Access denied")
    assert str(auth_error) == "Access denied"
    assert isinstance(auth_error, DotMacError)
    assert isinstance(auth_error, Exception)


def test_database_compatibility_functions():
    """Test database compatibility functions."""
    from dotmac.core import (
        DatabaseManager,
        check_database_health,
        get_db,
        get_db_session,
    )

    # These are stubs, but should not raise errors
    db_result = get_db()
    assert db_result is None

    session_result = get_db_session()
    assert session_result is None

    health_result = check_database_health()
    assert health_result["status"] == "ok"

    # Test DatabaseManager
    db_manager = DatabaseManager()
    assert db_manager.config is None

    session = db_manager.get_session()
    assert session is None

    health = db_manager.check_health()
    assert health["status"] == "ok"
