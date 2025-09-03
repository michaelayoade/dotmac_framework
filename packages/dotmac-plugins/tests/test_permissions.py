"""
Test suite for plugin permissions and context functionality.

Tests plugin context creation, permission checking, wildcard permissions,
service registration, and tenant isolation.
"""

import pytest
import logging
from unittest.mock import Mock

from dotmac.plugins import (
    PluginContext,
    PluginPermissionError,
    PluginMetadata,
    PluginKind,
    Author,
)
from conftest import TestPlugin


class TestPluginContext:
    """Test PluginContext creation and basic functionality."""
    
    def test_context_creation_defaults(self):
        """Test context creation with default values."""
        context = PluginContext()
        
        assert context.tenant_id is None
        assert context.environment == "production"
        assert context.services == {}
        assert context.config == {}
        assert context.permissions == set()
        
    def test_context_creation_with_values(self):
        """Test context creation with explicit values."""
        services = {"logger": logging.getLogger("test")}
        config = {"api_key": "test_key"}
        permissions = {"read", "write"}
        
        context = PluginContext(
            tenant_id="test_tenant",
            environment="development",
            services=services,
            config=config,
            permissions=permissions
        )
        
        assert context.tenant_id == "test_tenant"
        assert context.environment == "development"
        assert context.services == services
        assert context.config == config
        assert context.permissions == permissions
        
    def test_context_services_registration(self):
        """Test service registration in context."""
        context = PluginContext()
        
        # Register a service
        logger = logging.getLogger("test")
        context.services["logger"] = logger
        
        assert "logger" in context.services
        assert context.services["logger"] is logger
        
    def test_context_config_updates(self):
        """Test configuration updates in context."""
        context = PluginContext(config={"key1": "value1"})
        
        # Update config
        context.config["key2"] = "value2"
        context.config["key1"] = "updated_value1"
        
        assert context.config["key1"] == "updated_value1"
        assert context.config["key2"] == "value2"


class TestPermissionChecking:
    """Test permission validation and checking."""
    
    def test_has_permission_exact_match(self):
        """Test exact permission matching."""
        context = PluginContext(permissions={"read:users", "write:posts"})
        
        assert context.has_permission("read:users") is True
        assert context.has_permission("write:posts") is True
        assert context.has_permission("delete:users") is False
        
    def test_has_permission_wildcard_matching(self):
        """Test wildcard permission matching."""
        context = PluginContext(permissions={"read:*", "admin:*"})
        
        # Wildcard should match specific permissions
        assert context.has_permission("read:users") is True
        assert context.has_permission("read:posts") is True
        assert context.has_permission("admin:settings") is True
        assert context.has_permission("admin:users") is True
        
        # Should not match different prefixes
        assert context.has_permission("write:users") is False
        assert context.has_permission("delete:posts") is False
        
    def test_has_permission_mixed_permissions(self):
        """Test mixed exact and wildcard permissions."""
        context = PluginContext(permissions={"read:*", "write:users", "admin:settings"})
        
        # Wildcard permissions
        assert context.has_permission("read:anything") is True
        assert context.has_permission("read:users") is True
        
        # Exact permissions
        assert context.has_permission("write:users") is True
        assert context.has_permission("admin:settings") is True
        
        # Non-matching permissions
        assert context.has_permission("write:posts") is False
        assert context.has_permission("admin:users") is False
        
    def test_check_permission_success(self):
        """Test check_permission with valid permission."""
        context = PluginContext(permissions={"test:permission"})
        
        # Should not raise exception
        context.check_permission("test:permission")
        
    def test_check_permission_failure(self):
        """Test check_permission raises error for invalid permission."""
        context = PluginContext(permissions={"other:permission"})
        
        with pytest.raises(PluginPermissionError, match="Permission denied: missing:permission"):
            context.check_permission("missing:permission")
            
    def test_check_permission_wildcard(self):
        """Test check_permission with wildcard permissions."""
        context = PluginContext(permissions={"test:*"})
        
        # Should succeed for wildcard matches
        context.check_permission("test:read")
        context.check_permission("test:write")
        
        # Should fail for non-matches
        with pytest.raises(PluginPermissionError):
            context.check_permission("admin:read")
            
    def test_check_multiple_permissions(self):
        """Test checking multiple permissions at once."""
        context = PluginContext(permissions={"read:*", "write:users"})
        
        # All valid permissions
        context.check_permission("read:users", "read:posts", "write:users")
        
        # One invalid permission should raise error
        with pytest.raises(PluginPermissionError):
            context.check_permission("read:users", "write:posts")  # write:posts not allowed


class TestWildcardPermissions:
    """Test advanced wildcard permission scenarios."""
    
    def test_wildcard_permission_patterns(self):
        """Test various wildcard permission patterns."""
        test_cases = [
            # (permissions, test_permission, expected)
            ({"*"}, "anything", True),  # Global wildcard
            ({"read:*"}, "read:users", True),  # Namespace wildcard
            ({"read:*"}, "write:users", False),  # Different namespace
            ({"admin:*:read"}, "admin:users:read", True),  # Multi-level wildcard
            ({"admin:*:read"}, "admin:users:write", False),  # Partial match
        ]
        
        for permissions, test_perm, expected in test_cases:
            context = PluginContext(permissions=permissions)
            assert context.has_permission(test_perm) == expected
            
    def test_nested_wildcard_permissions(self):
        """Test nested wildcard permission structures."""
        context = PluginContext(permissions={"api:*:read", "api:users:*"})
        
        # Should match first wildcard
        assert context.has_permission("api:posts:read") is True
        assert context.has_permission("api:comments:read") is True
        
        # Should match second wildcard
        assert context.has_permission("api:users:create") is True
        assert context.has_permission("api:users:delete") is True
        
        # Should not match
        assert context.has_permission("api:posts:write") is False
        assert context.has_permission("web:users:read") is False
        
    def test_permission_precedence(self):
        """Test permission precedence and overlapping patterns."""
        context = PluginContext(permissions={"read:*", "read:users:admin"})
        
        # Both patterns should work
        assert context.has_permission("read:posts") is True
        assert context.has_permission("read:users:admin") is True
        assert context.has_permission("read:users:basic") is True
        
    def test_case_sensitive_permissions(self):
        """Test that permissions are case-sensitive."""
        context = PluginContext(permissions={"Read:Users", "ADMIN:*"})
        
        # Exact case should match
        assert context.has_permission("Read:Users") is True
        assert context.has_permission("ADMIN:Settings") is True
        
        # Different case should not match
        assert context.has_permission("read:Users") is False
        assert context.has_permission("admin:Settings") is False


class TestPluginPermissionIntegration:
    """Test permission integration with plugin operations."""
    
    def test_plugin_with_required_permissions(self, plugin_context):
        """Test plugin that requires specific permissions."""
        plugin = TestPlugin("perm_plugin")
        plugin._metadata.permissions_required = ["read:data", "write:files"]
        
        # Context with sufficient permissions
        plugin_context.permissions.update({"read:data", "write:files", "admin:settings"})
        
        # Should succeed
        for perm in plugin._metadata.permissions_required:
            plugin_context.check_permission(perm)
            
    def test_plugin_missing_required_permissions(self, plugin_context):
        """Test plugin validation fails with missing permissions."""
        plugin = TestPlugin("perm_plugin")
        plugin._metadata.permissions_required = ["admin:users", "admin:settings"]
        
        # Context with insufficient permissions
        plugin_context.permissions.update({"read:users", "write:posts"})
        
        # Should fail for missing permissions
        for perm in plugin._metadata.permissions_required:
            if not plugin_context.has_permission(perm):
                with pytest.raises(PluginPermissionError):
                    plugin_context.check_permission(perm)
                    
    def test_plugin_wildcard_permission_satisfaction(self, plugin_context):
        """Test plugin requirements satisfied by wildcard permissions."""
        plugin = TestPlugin("wildcard_plugin")
        plugin._metadata.permissions_required = [
            "api:users:read",
            "api:posts:read",
            "api:comments:read"
        ]
        
        # Context with wildcard permission
        plugin_context.permissions.add("api:*:read")
        
        # Should satisfy all specific requirements
        for perm in plugin._metadata.permissions_required:
            plugin_context.check_permission(perm)
            
    def test_multiple_plugins_different_permissions(self):
        """Test multiple plugins with different permission requirements."""
        # Create plugins with different permission needs
        export_plugin = TestPlugin("export")
        export_plugin._metadata.permissions_required = ["export:csv", "export:xlsx"]
        
        admin_plugin = TestPlugin("admin")
        admin_plugin._metadata.permissions_required = ["admin:users", "admin:settings"]
        
        # Context for export plugin
        export_context = PluginContext(permissions={"export:*"})
        for perm in export_plugin._metadata.permissions_required:
            export_context.check_permission(perm)  # Should succeed
            
        # Same context should fail for admin plugin
        for perm in admin_plugin._metadata.permissions_required:
            with pytest.raises(PluginPermissionError):
                export_context.check_permission(perm)


class TestTenantIsolation:
    """Test tenant-based isolation and context separation."""
    
    def test_different_tenant_contexts(self):
        """Test different tenant contexts are isolated."""
        tenant_a_context = PluginContext(
            tenant_id="tenant_a",
            permissions={"read:users"},
            config={"api_endpoint": "https://a.api.com"}
        )
        
        tenant_b_context = PluginContext(
            tenant_id="tenant_b", 
            permissions={"write:users"},
            config={"api_endpoint": "https://b.api.com"}
        )
        
        # Contexts should be independent
        assert tenant_a_context.tenant_id != tenant_b_context.tenant_id
        assert tenant_a_context.permissions != tenant_b_context.permissions
        assert tenant_a_context.config != tenant_b_context.config
        
    def test_tenant_specific_permissions(self):
        """Test tenant-specific permission patterns."""
        context = PluginContext(
            tenant_id="acme_corp",
            permissions={"tenant:acme_corp:*", "global:read"}
        )
        
        # Should have access to tenant-specific resources
        assert context.has_permission("tenant:acme_corp:users") is True
        assert context.has_permission("tenant:acme_corp:billing") is True
        
        # Should have global read access
        assert context.has_permission("global:read") is True
        
        # Should not have access to other tenants
        assert context.has_permission("tenant:other_corp:users") is False
        
    def test_multi_tenant_plugin_context(self):
        """Test plugin operating in multi-tenant context."""
        plugin = TestPlugin("multi_tenant")
        plugin._metadata.permissions_required = ["tenant:*:read"]
        
        # Context for tenant A
        tenant_a = PluginContext(
            tenant_id="tenant_a",
            permissions={"tenant:tenant_a:read", "tenant:tenant_a:write"}
        )
        
        # Should satisfy permission requirement
        assert tenant_a.has_permission("tenant:tenant_a:read") is True


class TestContextServices:
    """Test context service management."""
    
    def test_service_registration_and_retrieval(self):
        """Test registering and retrieving services."""
        context = PluginContext()
        
        # Register services
        logger = logging.getLogger("test")
        db_connection = Mock()
        
        context.services["logger"] = logger
        context.services["database"] = db_connection
        
        # Retrieve services
        assert context.services["logger"] is logger
        assert context.services["database"] is db_connection
        
    def test_service_overwriting(self):
        """Test overwriting existing services."""
        context = PluginContext()
        
        old_service = Mock()
        new_service = Mock()
        
        context.services["test_service"] = old_service
        assert context.services["test_service"] is old_service
        
        context.services["test_service"] = new_service
        assert context.services["test_service"] is new_service
        assert context.services["test_service"] is not old_service
        
    def test_service_availability_check(self):
        """Test checking service availability."""
        context = PluginContext()
        
        # Service not available
        assert "logger" not in context.services
        
        # Register service
        context.services["logger"] = logging.getLogger("test")
        
        # Service now available
        assert "logger" in context.services
        
    def test_context_with_predefined_services(self):
        """Test context creation with predefined services."""
        logger = logging.getLogger("test")
        cache = Mock()
        
        services = {
            "logger": logger,
            "cache": cache
        }
        
        context = PluginContext(services=services)
        
        assert context.services["logger"] is logger
        assert context.services["cache"] is cache
        assert len(context.services) == 2


class TestContextConfiguration:
    """Test context configuration management."""
    
    def test_config_access_and_modification(self):
        """Test configuration access and modification."""
        config = {"debug": True, "timeout": 30}
        context = PluginContext(config=config)
        
        # Access existing config
        assert context.config["debug"] is True
        assert context.config["timeout"] == 30
        
        # Modify config
        context.config["debug"] = False
        context.config["retries"] = 3
        
        assert context.config["debug"] is False
        assert context.config["retries"] == 3
        
    def test_config_nested_access(self):
        """Test nested configuration access."""
        config = {
            "database": {
                "host": "localhost",
                "port": 5432
            },
            "redis": {
                "host": "localhost",
                "port": 6379
            }
        }
        
        context = PluginContext(config=config)
        
        assert context.config["database"]["host"] == "localhost"
        assert context.config["redis"]["port"] == 6379
        
    def test_empty_config_handling(self):
        """Test handling of empty or None config."""
        # Empty config
        context1 = PluginContext(config={})
        assert context1.config == {}
        
        # None config defaults to empty dict
        context2 = PluginContext()
        assert context2.config == {}
        
    def test_config_isolation(self):
        """Test configuration isolation between contexts."""
        base_config = {"shared": "value"}
        
        context1 = PluginContext(config=base_config.copy())
        context2 = PluginContext(config=base_config.copy())
        
        # Modify one context
        context1.config["unique1"] = "value1"
        context2.config["unique2"] = "value2"
        
        # Should be isolated
        assert "unique1" in context1.config
        assert "unique1" not in context2.config
        assert "unique2" in context2.config
        assert "unique2" not in context1.config