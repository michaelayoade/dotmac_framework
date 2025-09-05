"""
Integration tests for the DotMac Security package.
"""

import asyncio
from uuid import uuid4

import pytest
from dotmac.security import (
    AccessControlManager,
    AccessRequest,
    ActionType,
    AuditEventType,
    AuditLogger,
    AuditSeverity,
    Permission,
    PermissionType,
    PluginPermissions,
    PluginSandbox,
    ResourceLimits,
    ResourceType,
    Role,
    SecurityValidator,
    TenantSecurityManager,
)


class TestSecurityIntegration:
    """Integration tests for security package components."""

    @pytest.fixture
    def access_control_manager(self):
        """Create access control manager instance."""
        return AccessControlManager()

    @pytest.fixture
    def audit_logger(self):
        """Create audit logger instance."""
        return AuditLogger(service_name="test-security")

    @pytest.fixture
    def tenant_manager(self):
        """Create tenant security manager instance."""
        return TenantSecurityManager()

    @pytest.fixture
    def security_validator(self):
        """Create security validator instance."""
        return SecurityValidator()

    @pytest.mark.asyncio
    async def test_access_control_flow(self, access_control_manager):
        """Test complete access control flow."""
        # Create permission
        permission = Permission(
            permission_id="test_read",
            name="Test Read",
            description="Read test resources",
            resource_type=ResourceType.API,
            action=ActionType.READ,
            permission_type=PermissionType.ALLOW
        )
        
        perm_id = await access_control_manager.create_permission(permission)
        assert perm_id == "test_read"

        # Create role
        role = Role(
            role_id="test_user",
            name="Test User",
            description="Test user role",
            permissions=["test_read"]
        )
        
        role_id = await access_control_manager.create_role(role)
        assert role_id == "test_user"

        # Grant permission
        ace_id = await access_control_manager.grant_permission(
            subject_type="user",
            subject_id="user123",
            resource_type=ResourceType.API,
            resource_id="test_api",
            permissions=[],
            roles=["test_user"],
            granted_by="admin"
        )
        
        assert ace_id is not None

        # Check permission
        request = AccessRequest(
            subject_type="user",
            subject_id="user123",
            resource_type=ResourceType.API,
            resource_id="test_api",
            action=ActionType.READ
        )
        
        decision = await access_control_manager.check_permission(request)
        assert decision.decision == "allow"

    @pytest.mark.asyncio
    async def test_audit_logging_flow(self, audit_logger):
        """Test audit logging functionality."""
        # Log authentication event
        auth_event = await audit_logger.log_auth_event(
            event_type=AuditEventType.AUTH_LOGIN,
            actor_id="user123",
            outcome="success",
            message="User login successful",
            client_ip="192.168.1.1"
        )
        
        assert auth_event.event_type == AuditEventType.AUTH_LOGIN
        assert auth_event.message == "User login successful"

        # Log data access event
        data_event = await audit_logger.log_data_access(
            operation="read",
            resource_type="customer",
            resource_id="cust123",
            actor_id="user123"
        )
        
        assert data_event.event_type == AuditEventType.DATA_READ
        assert "customer" in data_event.message

        # Query events
        events = await audit_logger.query_events(limit=10)
        assert len(events) >= 2

        # Get stats
        stats = await audit_logger.get_event_stats()
        assert stats["total_events"] >= 2

    @pytest.mark.asyncio
    async def test_tenant_security_flow(self, tenant_manager):
        """Test tenant security management."""
        tenant_id = str(uuid4())
        
        # Validate tenant
        is_valid = await tenant_manager.validate_tenant(tenant_id)
        assert is_valid

        # Get tenant info
        tenant_info = await tenant_manager.get_tenant_info(tenant_id)
        assert tenant_info is not None
        assert tenant_info.tenant_id == tenant_id

        # Check access
        has_access = await tenant_manager.check_tenant_access(tenant_id, "api")
        assert has_access

    @pytest.mark.asyncio
    async def test_plugin_sandbox_flow(self):
        """Test plugin sandbox functionality."""
        plugin_id = "test_plugin"
        tenant_id = uuid4()
        
        permissions = PluginPermissions.create_default()
        limits = ResourceLimits(max_memory_mb=128, max_execution_time_seconds=30)
        
        async with PluginSandbox(
            plugin_id=plugin_id,
            tenant_id=tenant_id,
            permissions=permissions,
            resource_limits=limits
        ) as sandbox:
            
            # Check permissions
            assert sandbox.check_permission("filesystem", "read_temp")
            assert not sandbox.check_permission("system", "process")
            
            # Get temp directory
            temp_dir = sandbox.get_temp_directory()
            assert temp_dir.exists()
            
            # Test execution with timeout
            async def test_function():
                await asyncio.sleep(0.1)
                return "success"
            
            result = await sandbox.execute_with_timeout(test_function, timeout=5.0)
            assert result == "success"

    def test_security_validation_flow(self, security_validator):
        """Test security validation functionality."""
        # Test SQL injection detection
        malicious_input = "'; DROP TABLE users; --"
        assert security_validator.check_sql_injection(malicious_input)
        
        safe_input = "john.doe@example.com"
        assert not security_validator.check_sql_injection(safe_input)

        # Test XSS detection
        xss_input = "<script>alert('xss')</script>"
        assert security_validator.check_xss(xss_input)
        
        safe_html = "<p>Hello World</p>"
        assert not security_validator.check_xss(safe_html)

        # Test data sanitization
        dirty_data = "<script>alert('hack')</script>Hello"
        clean_data = security_validator.sanitize_data(dirty_data)
        assert "script" not in clean_data
        assert "Hello" in clean_data

        # Test input validation with rules
        validation_result = security_validator.validate_input(
            data=malicious_input,
            rules={
                "check_sql_injection": True,
                "check_xss": True,
                "max_length": 100,
                "sanitize": True
            }
        )
        
        assert not validation_result["valid"]
        assert len(validation_result["errors"]) > 0
        assert validation_result["sanitized_data"] != malicious_input

    @pytest.mark.asyncio
    async def test_cross_component_integration(self, access_control_manager, audit_logger):
        """Test integration between access control and audit logging."""
        # Setup access control
        permission = Permission(
            permission_id="integrated_test",
            name="Integrated Test",
            resource_type=ResourceType.DATA,
            action=ActionType.READ,
            permission_type=PermissionType.ALLOW
        )
        
        await access_control_manager.create_permission(permission)
        
        ace_id = await access_control_manager.grant_permission(
            subject_type="user",
            subject_id="integration_user",
            resource_type=ResourceType.DATA,
            resource_id="sensitive_data",
            permissions=["integrated_test"],
            granted_by="admin"
        )
        
        # Test access and audit
        request = AccessRequest(
            subject_type="user",
            subject_id="integration_user",
            resource_type=ResourceType.DATA,
            resource_id="sensitive_data",
            action=ActionType.READ
        )
        
        decision = await access_control_manager.check_permission(request)
        
        # Log the access decision
        await audit_logger.log_event(
            event_type=AuditEventType.AUTHZ_PERMISSION_GRANTED if decision.decision == "allow" else AuditEventType.AUTHZ_PERMISSION_DENIED,
            message=f"Access decision: {decision.decision} - {decision.reason}",
            severity=AuditSeverity.MEDIUM,
            custom_attributes={
                "access_request_id": request.request_id,
                "decision": decision.decision,
                "evaluation_time_ms": decision.evaluation_time_ms
            }
        )
        
        # Verify integration
        assert decision.decision == "allow"
        
        events = await audit_logger.query_events(limit=5)
        access_events = [e for e in events if "Access decision" in e.message]
        assert len(access_events) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])