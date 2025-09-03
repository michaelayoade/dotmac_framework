"""
Unit tests for tenant identity resolution.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from dotmac.tenant.identity import (
    TenantContext,
    TenantIdentityResolver,
    get_current_tenant,
    set_tenant_context,
    clear_tenant_context,
    require_tenant,
    tenant_required,
)
from dotmac.tenant.config import TenantResolutionStrategy
from dotmac.tenant.exceptions import (
    TenantNotFoundError,
    TenantResolutionError,
    TenantContextError,
)


class TestTenantContext:
    """Test TenantContext model."""
    
    def test_tenant_context_creation(self):
        """Test basic tenant context creation."""
        context = TenantContext(
            tenant_id="test-tenant",
            resolution_method="test",
            resolved_from="unit-test"
        )
        
        assert context.tenant_id == "test-tenant"
        assert context.resolution_method == "test"
        assert context.resolved_from == "unit-test"
        assert context.display_name is None
        assert context.security_level == "standard"
        assert context.permissions == []
    
    def test_tenant_context_with_metadata(self):
        """Test tenant context with additional metadata."""
        context = TenantContext(
            tenant_id="tenant1",
            display_name="Tenant One",
            resolution_method="host",
            resolved_from="tenant1.example.com",
            request_id="req-123",
            user_id="user-456",
            security_level="high",
            permissions=["read", "write", "admin"],
            context_data={"custom": "data"}
        )
        
        assert context.tenant_id == "tenant1"
        assert context.display_name == "Tenant One"
        assert context.request_id == "req-123"
        assert context.user_id == "user-456"
        assert context.security_level == "high"
        assert context.permissions == ["read", "write", "admin"]
        assert context.context_data == {"custom": "data"}


class TestTenantIdentityResolver:
    """Test tenant identity resolution."""
    
    @pytest.mark.asyncio
    async def test_host_based_resolution(self, tenant_config, tenant_resolver, mock_request):
        """Test host-based tenant resolution."""
        mock_request.headers = {"host": "tenant1.example.com"}
        
        context = await tenant_resolver.resolve_tenant(mock_request)
        
        assert context.tenant_id == "tenant1"
        assert context.resolution_method == "host_mapping"
        assert context.resolved_from == "tenant1.example.com"
    
    @pytest.mark.asyncio
    async def test_host_pattern_resolution(self, tenant_config, tenant_resolver, mock_request):
        """Test host pattern-based resolution."""
        mock_request.headers = {"host": "newclient.example.com"}
        
        context = await tenant_resolver.resolve_tenant(mock_request)
        
        assert context.tenant_id == "newclient"
        assert context.resolution_method == "host_pattern"
        assert context.resolved_from == "newclient.example.com"
    
    @pytest.mark.asyncio
    async def test_subdomain_resolution(self, subdomain_config, mock_request):
        """Test subdomain-based resolution."""
        resolver = TenantIdentityResolver(subdomain_config)
        mock_request.headers = {"host": "tenant1.api.example.com"}
        
        context = await resolver.resolve_tenant(mock_request)
        
        assert context.tenant_id == "tenant1"
        assert context.resolution_method == "subdomain"
        assert context.resolved_from == "tenant1.api.example.com"
    
    @pytest.mark.asyncio
    async def test_header_based_resolution(self, header_config, mock_request):
        """Test header-based tenant resolution."""
        resolver = TenantIdentityResolver(header_config)
        mock_request.headers = {"X-Tenant-ID": "header-tenant"}
        
        context = await resolver.resolve_tenant(mock_request)
        
        assert context.tenant_id == "header-tenant"
        assert context.resolution_method == "header_tenant_id"
        assert context.resolved_from == "header-tenant"
    
    @pytest.mark.asyncio
    async def test_fallback_tenant_resolution(self, tenant_config, tenant_resolver, mock_request):
        """Test fallback to default tenant."""
        mock_request.headers = {"host": "unknown.example.com"}
        
        context = await tenant_resolver.resolve_tenant(mock_request)
        
        assert context.tenant_id == "test-tenant"  # fallback_tenant_id
        assert context.resolution_method == "fallback"
        assert context.resolved_from == "config"
    
    @pytest.mark.asyncio
    async def test_tenant_not_found_error(self, tenant_config, mock_request):
        """Test tenant not found error when no fallback."""
        config = tenant_config.copy()
        config.fallback_tenant_id = None
        resolver = TenantIdentityResolver(config)
        
        mock_request.headers = {"host": "unknown.example.com"}
        
        with pytest.raises(TenantNotFoundError) as exc_info:
            await resolver.resolve_tenant(mock_request)
        
        assert "unknown.example.com" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_composite_resolution_success(self, composite_config, mock_request):
        """Test successful composite resolution."""
        resolver = TenantIdentityResolver(composite_config)
        mock_request.headers = {
            "X-Tenant-ID": "header-tenant",
            "host": "some.example.com"
        }
        
        context = await resolver.resolve_tenant(mock_request)
        
        # Should resolve using header first
        assert context.tenant_id == "header-tenant"
        assert context.resolution_method == "header_tenant_id"
    
    @pytest.mark.asyncio
    async def test_composite_resolution_fallback(self, composite_config, mock_request):
        """Test composite resolution fallback to default."""
        resolver = TenantIdentityResolver(composite_config)
        mock_request.headers = {"host": "unknown.example.com"}
        
        context = await resolver.resolve_tenant(mock_request)
        
        # Should fallback to default tenant
        assert context.tenant_id == "default"
        assert context.resolution_method == "fallback"
    
    @pytest.mark.asyncio
    async def test_resolution_error_handling(self, tenant_config, mock_request):
        """Test resolution error handling."""
        resolver = TenantIdentityResolver(tenant_config)
        mock_request.headers = {}  # No host header
        
        with pytest.raises(TenantResolutionError) as exc_info:
            await resolver.resolve_tenant(mock_request)
        
        assert "No host header found" in str(exc_info.value)


class TestTenantContextManagement:
    """Test tenant context management functions."""
    
    def test_get_set_clear_tenant_context(self, sample_tenant_context):
        """Test getting, setting, and clearing tenant context."""
        # Initially no context
        assert get_current_tenant() is None
        
        # Set context
        set_tenant_context(sample_tenant_context)
        current = get_current_tenant()
        
        assert current is not None
        assert current.tenant_id == "test-tenant"
        assert current.display_name == "Test Tenant"
        
        # Clear context
        clear_tenant_context()
        assert get_current_tenant() is None
    
    def test_require_tenant_success(self, sample_tenant_context):
        """Test require_tenant with valid context."""
        set_tenant_context(sample_tenant_context)
        
        context = require_tenant()
        assert context.tenant_id == "test-tenant"
        
        clear_tenant_context()
    
    def test_require_tenant_failure(self):
        """Test require_tenant without context."""
        clear_tenant_context()
        
        with pytest.raises(Exception):  # HTTPException in actual FastAPI
            require_tenant()
    
    def test_tenant_required_decorator_success(self, sample_tenant_context):
        """Test tenant_required decorator with valid context."""
        set_tenant_context(sample_tenant_context)
        
        @tenant_required
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
        
        clear_tenant_context()
    
    def test_tenant_required_decorator_failure(self):
        """Test tenant_required decorator without context."""
        clear_tenant_context()
        
        @tenant_required
        def test_function():
            return "should not reach here"
        
        with pytest.raises(TenantContextError):
            test_function()


class TestPatternMatching:
    """Test tenant pattern matching functionality."""
    
    def test_extract_tenant_from_pattern_success(self, tenant_resolver):
        """Test successful tenant extraction from pattern."""
        pattern = "{tenant}.example.com"
        host = "client1.example.com"
        
        tenant_id = tenant_resolver._extract_tenant_from_pattern(host, pattern)
        assert tenant_id == "client1"
    
    def test_extract_tenant_from_pattern_failure(self, tenant_resolver):
        """Test failed tenant extraction from pattern."""
        pattern = "{tenant}.example.com"
        host = "client1.different.com"
        
        tenant_id = tenant_resolver._extract_tenant_from_pattern(host, pattern)
        assert tenant_id is None
    
    def test_extract_tenant_complex_pattern(self, tenant_resolver):
        """Test tenant extraction from complex pattern."""
        pattern = "app-{tenant}.prod.example.com"
        host = "app-client123.prod.example.com"
        
        tenant_id = tenant_resolver._extract_tenant_from_pattern(host, pattern)
        assert tenant_id == "client123"


class TestCaching:
    """Test tenant resolution caching."""
    
    @pytest.mark.asyncio
    async def test_tenant_caching_enabled(self, tenant_config, mock_request):
        """Test tenant resolution caching."""
        tenant_config.enable_tenant_caching = True
        resolver = TenantIdentityResolver(tenant_config)
        
        mock_request.headers = {"host": "tenant1.example.com"}
        
        # First resolution
        context1 = await resolver.resolve_tenant(mock_request)
        
        # Check cache was populated
        cache_key = "host_mapping:tenant1.example.com"
        assert cache_key in resolver._tenant_cache
        
        # Second resolution should use cache
        context2 = await resolver.resolve_tenant(mock_request)
        
        assert context1.tenant_id == context2.tenant_id
    
    @pytest.mark.asyncio
    async def test_tenant_caching_disabled(self, tenant_config, mock_request):
        """Test tenant resolution without caching."""
        tenant_config.enable_tenant_caching = False
        resolver = TenantIdentityResolver(tenant_config)
        
        mock_request.headers = {"host": "tenant1.example.com"}
        
        await resolver.resolve_tenant(mock_request)
        
        # Cache should be empty
        assert len(resolver._tenant_cache) == 0