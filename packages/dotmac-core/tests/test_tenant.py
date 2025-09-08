"""
Test cases for DotMac Core tenant management.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from dotmac.core.exceptions import TenantNotFoundError
from dotmac.core.tenant import (
    HeaderTenantResolver,
    SubdomainTenantResolver,
    TenantContext,
    TenantManager,
    TenantMetadata,
    clear_current_tenant,
    get_current_tenant,
    require_current_tenant,
    set_current_tenant,
    tenant_manager,
)


class TestTenantMetadata:
    """Test TenantMetadata model."""

    def test_metadata_defaults(self):
        """Test TenantMetadata with defaults."""
        metadata = TenantMetadata()
        assert metadata.database_url is None
        assert metadata.database_schema is None
        assert metadata.database_isolation_level == "read_committed"
        assert metadata.features == {}
        assert metadata.allowed_domains == []
        assert metadata.rate_limits == {}
        assert metadata.settings == {}

    def test_metadata_with_values(self):
        """Test TenantMetadata with custom values."""
        metadata = TenantMetadata(
            database_url="postgresql://localhost/test",
            database_schema="tenant_123",
            features={"feature_a": True, "feature_b": False},
            allowed_domains=["example.com"],
            rate_limits={"api": 1000},
            settings={"theme": "dark"},
        )

        assert metadata.database_url == "postgresql://localhost/test"
        assert metadata.database_schema == "tenant_123"
        assert metadata.features == {"feature_a": True, "feature_b": False}
        assert metadata.allowed_domains == ["example.com"]
        assert metadata.rate_limits == {"api": 1000}
        assert metadata.settings == {"theme": "dark"}

    def test_metadata_extra_fields(self):
        """Test TenantMetadata allows extra fields."""
        metadata = TenantMetadata(custom_field="custom_value")
        assert metadata.custom_field == "custom_value"


class TestTenantContext:
    """Test TenantContext model."""

    @pytest.fixture
    def tenant_context(self):
        """Create a test tenant context."""
        return TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_slug="test-tenant",
            display_name="Test Tenant",
            resolution_method="subdomain",
            resolved_from="test-tenant",
        )

    def test_tenant_context_creation(self, tenant_context):
        """Test TenantContext creation."""
        assert isinstance(tenant_context.tenant_id, uuid.UUID)
        assert tenant_context.tenant_slug == "test-tenant"
        assert tenant_context.display_name == "Test Tenant"
        assert tenant_context.resolution_method == "subdomain"
        assert tenant_context.resolved_from == "test-tenant"
        assert tenant_context.metadata is None
        assert tenant_context.request_id is None
        assert tenant_context.user_id is None
        assert tenant_context.security_level == "standard"
        assert tenant_context.permissions == []
        assert tenant_context.features == {}

    def test_is_active_property(self, tenant_context):
        """Test is_active property."""
        assert tenant_context.is_active is True

        tenant_context.security_level = "suspended"
        assert tenant_context.is_active is False

    def test_has_feature_method(self, tenant_context):
        """Test has_feature method."""
        assert tenant_context.has_feature("feature_a") is False

        tenant_context.features = {"feature_a": True, "feature_b": False}
        assert tenant_context.has_feature("feature_a") is True
        assert tenant_context.has_feature("feature_b") is False
        assert tenant_context.has_feature("feature_c") is False

    def test_has_permission_method(self, tenant_context):
        """Test has_permission method."""
        assert tenant_context.has_permission("read") is False

        tenant_context.permissions = ["read", "write"]
        assert tenant_context.has_permission("read") is True
        assert tenant_context.has_permission("write") is True
        assert tenant_context.has_permission("delete") is False

    def test_tenant_context_with_metadata(self):
        """Test TenantContext with metadata."""
        metadata = TenantMetadata(
            database_url="postgresql://localhost/test", features={"feature_a": True}
        )

        context = TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_slug="test",
            display_name="Test",
            resolution_method="header",
            resolved_from="test-id",
            metadata=metadata,
        )

        assert context.metadata == metadata
        assert context.metadata.database_url == "postgresql://localhost/test"

    def test_tenant_context_with_user(self):
        """Test TenantContext with user information."""
        user_id = uuid.uuid4()
        context = TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_slug="test",
            display_name="Test",
            resolution_method="header",
            resolved_from="test",
            request_id="req-123",
            user_id=user_id,
            permissions=["read", "write"],
        )

        assert context.request_id == "req-123"
        assert context.user_id == user_id
        assert context.permissions == ["read", "write"]


class TestSubdomainTenantResolver:
    """Test SubdomainTenantResolver."""

    @pytest.fixture
    def resolver(self):
        """Create a subdomain resolver."""
        return SubdomainTenantResolver()

    @pytest.mark.asyncio
    async def test_resolve_from_subdomain(self, resolver):
        """Test resolving tenant from subdomain."""
        request_data = {"host": "acme-corp.example.com"}

        tenant_context = await resolver.resolve_tenant(request_data)

        assert tenant_context is not None
        assert tenant_context.tenant_slug == "acme-corp"
        assert tenant_context.display_name == "Acme Corp"
        assert tenant_context.resolution_method == "subdomain"
        assert tenant_context.resolved_from == "acme-corp"
        assert isinstance(tenant_context.tenant_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_resolve_with_dashes(self, resolver):
        """Test resolving tenant with dashes in subdomain."""
        request_data = {"host": "my-test-tenant.example.com"}

        tenant_context = await resolver.resolve_tenant(request_data)

        assert tenant_context is not None
        assert tenant_context.tenant_slug == "my-test-tenant"
        assert tenant_context.display_name == "My Test Tenant"

    @pytest.mark.asyncio
    async def test_resolve_no_host(self, resolver):
        """Test resolving with no host."""
        request_data = {}

        tenant_context = await resolver.resolve_tenant(request_data)

        assert tenant_context is None

    @pytest.mark.asyncio
    async def test_resolve_no_subdomain(self, resolver):
        """Test resolving with no subdomain."""
        request_data = {"host": "example.com"}

        tenant_context = await resolver.resolve_tenant(request_data)

        assert tenant_context is None

    @pytest.mark.asyncio
    async def test_custom_domain_pattern(self):
        """Test custom domain pattern."""
        resolver = SubdomainTenantResolver(domain_pattern=r"^tenant-([a-zA-Z0-9\-]+)\.")
        request_data = {"host": "tenant-123.example.com"}

        tenant_context = await resolver.resolve_tenant(request_data)

        assert tenant_context is not None
        assert tenant_context.tenant_slug == "123"


class TestHeaderTenantResolver:
    """Test HeaderTenantResolver."""

    @pytest.fixture
    def resolver(self):
        """Create a header resolver."""
        return HeaderTenantResolver()

    @pytest.mark.asyncio
    async def test_resolve_from_uuid_header(self, resolver):
        """Test resolving tenant from UUID header."""
        tenant_id = str(uuid.uuid4())
        request_data = {"headers": {"x-tenant-id": tenant_id}}

        tenant_context = await resolver.resolve_tenant(request_data)

        assert tenant_context is not None
        assert str(tenant_context.tenant_id) == tenant_id
        assert tenant_context.tenant_slug == tenant_id
        assert tenant_context.resolution_method == "header"
        assert tenant_context.resolved_from == tenant_id

    @pytest.mark.asyncio
    async def test_resolve_from_slug_header(self, resolver):
        """Test resolving tenant from slug header."""
        request_data = {"headers": {"x-tenant-id": "test-tenant"}}

        tenant_context = await resolver.resolve_tenant(request_data)

        assert tenant_context is not None
        assert tenant_context.tenant_slug == "test-tenant"
        assert tenant_context.display_name == "Test-Tenant"
        assert tenant_context.resolution_method == "header"
        assert tenant_context.resolved_from == "test-tenant"

    @pytest.mark.asyncio
    async def test_resolve_no_headers(self, resolver):
        """Test resolving with no headers."""
        request_data = {}

        tenant_context = await resolver.resolve_tenant(request_data)

        assert tenant_context is None

    @pytest.mark.asyncio
    async def test_resolve_no_tenant_header(self, resolver):
        """Test resolving with no tenant header."""
        request_data = {"headers": {"x-other-header": "value"}}

        tenant_context = await resolver.resolve_tenant(request_data)

        assert tenant_context is None

    @pytest.mark.asyncio
    async def test_custom_header_name(self):
        """Test custom header name."""
        resolver = HeaderTenantResolver(header_name="X-Custom-Tenant")
        request_data = {"headers": {"x-custom-tenant": "custom-tenant"}}

        tenant_context = await resolver.resolve_tenant(request_data)

        assert tenant_context is not None
        assert tenant_context.tenant_slug == "custom-tenant"


class TestTenantManager:
    """Test TenantManager."""

    @pytest.fixture
    def manager(self):
        """Create a tenant manager."""
        return TenantManager()

    @pytest.fixture
    def tenant_context(self):
        """Create a test tenant context."""
        return TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_slug="test",
            display_name="Test",
            resolution_method="test",
            resolved_from="test",
        )

    @pytest.mark.asyncio
    async def test_resolve_tenant_success(self, manager):
        """Test successful tenant resolution."""
        request_data = {"host": "test.example.com"}

        tenant_context = await manager.resolve_tenant(request_data)

        assert tenant_context is not None
        assert tenant_context.tenant_slug == "test"

    @pytest.mark.asyncio
    async def test_resolve_tenant_failure(self, manager):
        """Test failed tenant resolution."""
        request_data = {"host": "example.com"}  # No subdomain

        tenant_context = await manager.resolve_tenant(request_data)

        assert tenant_context is None

    @pytest.mark.asyncio
    async def test_resolve_tenant_with_exception(self, manager):
        """Test tenant resolution with exception."""
        # Mock a resolver that raises an exception
        mock_resolver = AsyncMock()
        mock_resolver.resolve_tenant.side_effect = Exception("Test error")
        manager.resolvers = [mock_resolver]

        tenant_context = await manager.resolve_tenant({})

        assert tenant_context is None

    def test_set_and_get_tenant_context(self, manager, tenant_context):
        """Test setting and getting tenant context."""
        # Initially no context
        assert manager.get_tenant_context() is None

        # Set context
        manager.set_tenant_context(tenant_context)

        # Get context
        result = manager.get_tenant_context()
        assert result == tenant_context

    def test_require_tenant_context_success(self, manager, tenant_context):
        """Test requiring tenant context when available."""
        manager.set_tenant_context(tenant_context)

        result = manager.require_tenant_context()
        assert result == tenant_context

    def test_require_tenant_context_failure(self, manager):
        """Test requiring tenant context when not available."""
        with pytest.raises(TenantNotFoundError) as exc_info:
            manager.require_tenant_context()

        assert "No tenant context available" in str(exc_info.value)
        assert exc_info.value.error_code == "TENANT_CONTEXT_REQUIRED"

    def test_clear_tenant_context(self, manager, tenant_context):
        """Test clearing tenant context."""
        # Set context first
        manager.set_tenant_context(tenant_context)
        assert manager.get_tenant_context() == tenant_context

        # Clear context
        manager.clear_tenant_context()
        assert manager.get_tenant_context() is None


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.fixture
    def tenant_context(self):
        """Create a test tenant context."""
        return TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_slug="test",
            display_name="Test",
            resolution_method="test",
            resolved_from="test",
        )

    def test_get_current_tenant(self, tenant_context):
        """Test get_current_tenant function."""
        # Clear any existing context
        clear_current_tenant()
        assert get_current_tenant() is None

        # Set context
        set_current_tenant(tenant_context)
        result = get_current_tenant()
        assert result == tenant_context

    def test_require_current_tenant_success(self, tenant_context):
        """Test require_current_tenant when context is available."""
        set_current_tenant(tenant_context)

        result = require_current_tenant()
        assert result == tenant_context

    def test_require_current_tenant_failure(self):
        """Test require_current_tenant when context is not available."""
        clear_current_tenant()

        with pytest.raises(TenantNotFoundError):
            require_current_tenant()

    def test_set_current_tenant(self, tenant_context):
        """Test set_current_tenant function."""
        set_current_tenant(tenant_context)

        result = get_current_tenant()
        assert result == tenant_context

    def test_clear_current_tenant(self, tenant_context):
        """Test clear_current_tenant function."""
        # Set context first
        set_current_tenant(tenant_context)
        assert get_current_tenant() == tenant_context

        # Clear context
        clear_current_tenant()
        assert get_current_tenant() is None

    def test_set_none_tenant(self):
        """Test setting None as tenant context."""
        set_current_tenant(None)
        assert get_current_tenant() is None


class TestTenantManagerSingleton:
    """Test global tenant manager instance."""

    def test_tenant_manager_is_singleton(self):
        """Test that tenant_manager is accessible."""
        assert tenant_manager is not None
        assert isinstance(tenant_manager, TenantManager)

    def test_convenience_functions_use_global_manager(self, monkeypatch):
        """Test that convenience functions use the global manager."""
        mock_manager = AsyncMock()
        mock_context = TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_slug="test",
            display_name="Test",
            resolution_method="test",
            resolved_from="test",
        )

        # Mock the global manager
        monkeypatch.setattr("dotmac.core.tenant.tenant_manager", mock_manager)

        # Test functions call the global manager
        mock_manager.get_tenant_context.return_value = mock_context
        from dotmac.core.tenant import get_current_tenant

        result = get_current_tenant()
        mock_manager.get_tenant_context.assert_called_once()

    def teardown_method(self):
        """Clean up after each test."""
        clear_current_tenant()
