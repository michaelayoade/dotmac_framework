"""
Comprehensive security tests to achieve 90% coverage.

Tests all security components with focus on:
- Sandbox security vulnerabilities
- JWT extraction and validation
- Signature verification
- Audit logging with redaction
- Tenant isolation
- Access control
"""

import base64
import hashlib
import hmac
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import security components to test
from dotmac.security.sandbox.sandbox import PluginSandbox, PluginExecutionError
from dotmac.security.sandbox.manager import SecurityScanner
from dotmac.security.tenant_isolation.enforcer import TenantSecurityEnforcer
from dotmac.security.audit.logger import init_audit_logger
from dotmac.security.audit.middleware import AuditMiddleware
from dotmac.security.access_control.manager import AccessControlManager


class TestSecureSandbox:
    """Test secure sandbox implementation."""
    
    def test_sandbox_initialization(self):
        """Test sandbox proper initialization without global cwd change."""
        plugin_id = "test-plugin-001"
        sandbox = PluginSandbox(plugin_id)
        
        # Should not change global cwd during init
        original_cwd = os.getcwd()
        assert sandbox.plugin_id == plugin_id
        assert os.getcwd() == original_cwd
    
    @pytest.mark.asyncio
    async def test_sandbox_context_manager(self):
        """Test sandbox context manager setup and cleanup."""
        plugin_id = "test-plugin-002"
        
        async with PluginSandbox(plugin_id) as sandbox:
            # Should create temp directory
            temp_dir = sandbox.get_temp_directory()
            assert temp_dir.exists()
            assert temp_dir.name.startswith("secure_plugin_")
            
            # Should have restrictive permissions
            stat_info = os.stat(temp_dir)
            permissions = oct(stat_info.st_mode)[-3:]
            assert permissions == "700"  # Owner only
        
        # Should clean up temp directory
        assert not temp_dir.exists()
    
    @pytest.mark.asyncio
    async def test_subprocess_execution(self):
        """Test secure subprocess execution."""
        plugin_id = "test-plugin-003"
        test_code = """
import os
print(f"Working directory: {os.getcwd()}")
print("Hello from secure sandbox!")
"""
        
        async with PluginSandbox(plugin_id) as sandbox:
            result = await sandbox.execute_in_subprocess(test_code)
            
            assert result["return_code"] == 0
            assert "Hello from secure sandbox!" in result["stdout"]
            assert "Working directory:" in result["stdout"]
            # Should be executed in sandbox temp dir, not global cwd
            assert str(sandbox.get_temp_directory()) in result["stdout"]
    
    @pytest.mark.asyncio
    async def test_subprocess_timeout(self):
        """Test subprocess timeout handling."""
        plugin_id = "test-plugin-004"
        slow_code = """
import time
time.sleep(10)  # Sleep longer than timeout
"""
        
        async with PluginSandbox(plugin_id) as sandbox:
            with pytest.raises(PluginExecutionError) as excinfo:
                await sandbox.execute_in_subprocess(slow_code, timeout=1)
            
            assert "timeout" in str(excinfo.value).lower()
    
    @pytest.mark.asyncio
    async def test_environment_isolation(self):
        """Test secure environment creation."""
        plugin_id = "test-plugin-005"
        test_code = """
import os
print("PATH:", os.environ.get("PATH", "NOT_SET"))
print("HOME:", os.environ.get("HOME", "NOT_SET"))
print("PYTHONPATH:", os.environ.get("PYTHONPATH", "NOT_SET"))
"""
        
        async with PluginSandbox(plugin_id) as sandbox:
            result = await sandbox.execute_in_subprocess(test_code)
            
            assert result["return_code"] == 0
            output = result["stdout"]
            
            # Should have minimal PATH
            assert "PATH: /usr/bin:/bin" in output
            # HOME should be sandbox temp dir
            assert f"HOME: {sandbox.get_temp_directory()}" in output
            # PYTHONPATH should be sandbox temp dir
            assert f"PYTHONPATH: {sandbox.get_temp_directory()}" in output
    
    def test_resource_limits_configuration(self):
        """Test resource limits configuration."""
        with patch('resource.setrlimit') as mock_setrlimit:
            # Mock subprocess execution to test limits setup
            sandbox = PluginSandbox("test-plugin-006")
            sandbox._setup_subprocess_limits()
            
            # Should have called setrlimit for various limits
            assert mock_setrlimit.call_count >= 3  # At least memory, CPU, file size


class TestSignatureVerification:
    """Test secure signature verification."""
    
    def test_signature_verifier_initialization(self):
        """Test signature verifier initialization."""
        scanner = SecurityScanner()
        
        assert hasattr(scanner, 'trusted_signatures')
        assert hasattr(scanner, 'trusted_hashes')
        assert hasattr(scanner, 'hmac_keys')
    
    def test_trusted_signature_verification(self):
        """Test trusted signature verification."""
        scanner = SecurityScanner()
        
        # Add a trusted signature
        test_signature = "trusted_signature_123"
        scanner.trusted_signatures.add(test_signature)
        
        code = "print('Hello World')"
        
        # Should pass with trusted signature
        assert scanner._verify_trusted_signature(code, test_signature, {})
        
        # Should fail with untrusted signature
        assert not scanner._verify_trusted_signature(code, "untrusted_sig", {})
    
    def test_hash_signature_verification(self):
        """Test hash-based signature verification."""
        scanner = SecurityScanner()
        
        # Setup hash verification
        plugin_name = "test_plugin"
        code = "print('Hello World')"
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        
        scanner.trusted_hashes[plugin_name] = code_hash
        metadata = {"name": plugin_name}
        
        # Should pass with correct hash
        assert scanner._verify_hash_signature(code, code_hash, metadata)
        
        # Should fail with wrong hash
        assert not scanner._verify_hash_signature(code, "wrong_hash", metadata)
    
    def test_hmac_signature_verification(self):
        """Test HMAC signature verification."""
        scanner = SecurityScanner()
        
        # Setup HMAC verification
        plugin_name = "test_plugin"
        code = "print('Hello World')"
        hmac_key = b"secret_key_for_testing"
        
        scanner.hmac_keys[plugin_name] = hmac_key
        metadata = {"name": plugin_name}
        
        # Generate correct HMAC
        expected_hmac = hmac.new(hmac_key, code.encode(), hashlib.sha256).hexdigest()
        
        # Should pass with correct HMAC
        assert scanner._verify_hmac_signature(code, expected_hmac, metadata)
        
        # Should fail with wrong HMAC
        assert not scanner._verify_hmac_signature(code, "wrong_hmac", metadata)
    
    @pytest.mark.asyncio
    async def test_code_validation_with_signature(self):
        """Test complete code validation with signature."""
        scanner = SecurityScanner()
        
        # Add trusted signature
        trusted_sig = "test_signature_456"
        scanner.trusted_signatures.add(trusted_sig)
        
        code = "print('Safe code')"
        metadata = {"name": "test_plugin", "signature": trusted_sig}
        
        # Should pass validation
        result = await scanner.validate_plugin_code(code, metadata)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_code_validation_without_signature(self):
        """Test code validation without signature (should warn)."""
        scanner = SecurityScanner()
        
        code = "print('Code without signature')"
        metadata = {"name": "test_plugin"}  # No signature
        
        with patch('structlog.get_logger') as mock_logger:
            logger_instance = MagicMock()
            mock_logger.return_value = logger_instance
            
            result = await scanner.validate_plugin_code(code, metadata)
            assert result is True
            # Should have warned about missing signature
            logger_instance.warning.assert_called()


class TestJWTExtraction:
    """Test secure JWT extraction and validation."""
    
    def setup_method(self):
        """Setup JWT test environment."""
        self.secret_key = "test_secret_key_123"
        self.enforcer = TenantSecurityEnforcer(jwt_secret_key=self.secret_key)
    
    def create_test_jwt(self, payload: dict) -> str:
        """Create a test JWT token."""
        header = {"alg": "HS256", "typ": "JWT"}
        
        # Encode header and payload
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip('=')
        
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip('=')
        
        # Create signature
        message = f"{header_b64}.{payload_b64}"
        signature = base64.urlsafe_b64encode(
            hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
        ).decode().rstrip('=')
        
        return f"{message}.{signature}"
    
    def test_jwt_decode_and_validate(self):
        """Test JWT decoding and validation."""
        payload = {
            "tenant_id": "tenant-123",
            "user_id": "user-456",
            "exp": int(time.time()) + 3600  # Expires in 1 hour
        }
        
        token = self.create_test_jwt(payload)
        decoded = self.enforcer._decode_and_validate_jwt(token)
        
        assert decoded["tenant_id"] == "tenant-123"
        assert decoded["user_id"] == "user-456"
    
    def test_jwt_expired_token(self):
        """Test expired JWT token handling."""
        payload = {
            "tenant_id": "tenant-123",
            "exp": int(time.time()) - 3600  # Expired 1 hour ago
        }
        
        token = self.create_test_jwt(payload)
        
        with pytest.raises(ValueError) as excinfo:
            self.enforcer._decode_and_validate_jwt(token)
        
        assert "expired" in str(excinfo.value).lower()
    
    def test_jwt_invalid_signature(self):
        """Test JWT with invalid signature."""
        payload = {"tenant_id": "tenant-123"}
        token = self.create_test_jwt(payload)
        
        # Corrupt the signature
        parts = token.split('.')
        corrupted_token = f"{parts[0]}.{parts[1]}.invalid_signature"
        
        with pytest.raises(ValueError) as excinfo:
            self.enforcer._decode_and_validate_jwt(token)
    
    def test_jwt_malformed_token(self):
        """Test malformed JWT token."""
        malformed_tokens = [
            "invalid",
            "invalid.token",
            "invalid.token.format.extra"
        ]
        
        for token in malformed_tokens:
            with pytest.raises(ValueError):
                self.enforcer._decode_and_validate_jwt(token)
    
    @pytest.mark.asyncio
    async def test_extract_tenant_from_jwt(self):
        """Test tenant extraction from JWT."""
        # Create mock request
        payload = {"tenant_id": "tenant-789"}
        token = self.create_test_jwt(payload)
        
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        
        tenant_id = await self.enforcer._extract_from_jwt(mock_request)
        assert tenant_id == "tenant-789"
    
    @pytest.mark.asyncio
    async def test_extract_tenant_no_auth_header(self):
        """Test tenant extraction without authorization header."""
        mock_request = MagicMock()
        mock_request.headers = {}
        
        tenant_id = await self.enforcer._extract_from_jwt(mock_request)
        assert tenant_id is None


class TestAuditLogging:
    """Test secure audit logging with redaction."""
    
    def setup_method(self):
        """Setup audit logging test environment."""
        # Initialize audit logger for testing
        self.audit_logger = init_audit_logger("test-service", "test-tenant")
    
    def test_audit_logger_initialization(self):
        """Test audit logger proper initialization."""
        logger = init_audit_logger("test-service", "test-tenant")
        assert logger.service_name == "test-service"
        assert logger.tenant_id == "test-tenant"
    
    def test_audit_logger_not_initialized_error(self):
        """Test error when audit logger not initialized."""
        # Clear global logger
        import dotmac.security.audit.logger as audit_module
        audit_module._global_audit_logger = None
        
        with pytest.raises(RuntimeError) as excinfo:
            from dotmac.security.audit.logger import get_audit_logger
            get_audit_logger()
        
        assert "not initialized" in str(excinfo.value)
    
    def test_audit_middleware_redaction(self):
        """Test audit middleware data redaction."""
        app = MagicMock()
        middleware = AuditMiddleware(app, enable_redaction=True)
        
        # Test sensitive data redaction
        sensitive_data = {
            "username": "john_doe",
            "password": "secret123",
            "token": "bearer_token_xyz",
            "normal_field": "normal_value"
        }
        
        redacted = middleware._redact_sensitive_data(sensitive_data)
        
        assert redacted["username"] == "john_doe"  # Not sensitive
        assert redacted["password"] == "[REDACTED]"  # Sensitive
        assert redacted["token"] == "[REDACTED]"  # Sensitive
        assert redacted["normal_field"] == "normal_value"  # Normal
    
    def test_audit_middleware_string_patterns(self):
        """Test string pattern redaction."""
        app = MagicMock()
        middleware = AuditMiddleware(app, enable_redaction=True)
        
        # Test various sensitive patterns
        test_strings = [
            "Bearer abc123xyz789token",
            "Credit card: 4532-1234-5678-9012",
            "Here is my token: verylongtokenstring123456789"
        ]
        
        for test_string in test_strings:
            redacted = middleware._redact_string(test_string)
            assert redacted != test_string  # Should be modified
            assert "REDACTED" in redacted or "TOKEN_REDACTED" in redacted
    
    def test_audit_attributes_preparation(self):
        """Test audit attributes preparation with redaction."""
        app = MagicMock()
        middleware = AuditMiddleware(app, enable_redaction=True)
        
        # Mock request with sensitive data
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/auth/login"
        mock_request.query_params = {"username": "john", "password": "secret"}
        mock_request.headers = {
            "Authorization": "Bearer token123",
            "User-Agent": "Mozilla/5.0",
            "X-API-Key": "secret_key_123"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        attributes = middleware._prepare_audit_attributes(mock_request, mock_response)
        
        # Should redact sensitive query params
        assert attributes["query_params"]["password"] == "[REDACTED]"
        assert attributes["query_params"]["username"] == "john"
        
        # Should redact sensitive headers
        assert attributes["headers"]["Authorization"] == "[REDACTED]"
        assert attributes["headers"]["X-API-Key"] == "[REDACTED]"
        assert attributes["headers"]["User-Agent"] == "Mozilla/5.0"  # Safe header


class TestTenantIsolation:
    """Test tenant isolation and boundary enforcement."""
    
    def setup_method(self):
        """Setup tenant isolation test environment."""
        self.enforcer = TenantSecurityEnforcer()
    
    def test_tenant_id_validation(self):
        """Test tenant ID format validation."""
        # Valid UUID format
        assert self.enforcer._is_valid_tenant_id("550e8400-e29b-41d4-a716-446655440000")
        
        # Valid slug format
        assert self.enforcer._is_valid_tenant_id("tenant-123")
        assert self.enforcer._is_valid_tenant_id("company_name")
        
        # Invalid formats
        assert not self.enforcer._is_valid_tenant_id("")
        assert not self.enforcer._is_valid_tenant_id("ab")  # Too short
        assert not self.enforcer._is_valid_tenant_id("tenant with spaces")
    
    def test_exempt_path_checking(self):
        """Test exempt path checking."""
        # Exempt paths should not require tenant enforcement
        exempt_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
        
        for path in exempt_paths:
            assert self.enforcer._is_exempt_path(path)
        
        # Non-exempt paths should require enforcement
        assert not self.enforcer._is_exempt_path("/api/users")
        assert not self.enforcer._is_exempt_path("/dashboard")
    
    @pytest.mark.asyncio
    async def test_tenant_context_extraction(self):
        """Test tenant context extraction from multiple sources."""
        mock_request = MagicMock()
        mock_request.headers = {
            "X-Tenant-ID": "tenant-from-gateway",
            "X-Container-Tenant": "tenant-from-container",
            "Host": "tenant-subdomain.example.com"
        }
        
        contexts = await self.enforcer._extract_tenant_contexts(mock_request)
        
        # Should extract from multiple sources
        sources = [ctx.source for ctx in contexts]
        assert "gateway_header" in sources
        assert "container_context" in sources
        assert "subdomain" in sources
    
    @pytest.mark.asyncio
    async def test_context_consistency_validation(self):
        """Test tenant context consistency validation."""
        from dotmac.security.tenant_isolation.models import TenantContext
        
        # Consistent contexts should pass
        consistent_contexts = [
            TenantContext(tenant_id="tenant-123", source="gateway_header"),
            TenantContext(tenant_id="tenant-123", source="container_context")
        ]
        
        result = await self.enforcer._validate_context_consistency(consistent_contexts)
        assert result.tenant_id == "tenant-123"
        assert result.source == "gateway_header"  # Highest priority
    
    @pytest.mark.asyncio
    async def test_context_mismatch_error(self):
        """Test tenant context mismatch handling."""
        from dotmac.security.tenant_isolation.models import TenantContext
        from fastapi import HTTPException
        
        # Mismatched contexts should raise error
        mismatched_contexts = [
            TenantContext(tenant_id="tenant-123", source="gateway_header"),
            TenantContext(tenant_id="tenant-456", source="container_context")
        ]
        
        with pytest.raises(HTTPException) as excinfo:
            await self.enforcer._validate_context_consistency(mismatched_contexts)
        
        assert excinfo.value.status_code == 403
        assert "mismatch" in excinfo.value.detail.lower()


class TestAccessControl:
    """Test access control and RBAC functionality."""
    
    def setup_method(self):
        """Setup access control test environment."""
        self.access_manager = AccessControlManager()
    
    def test_permission_caching(self):
        """Test permission result caching."""
        user_id = "user-123"
        resource = "users"
        action = "read"
        
        # First call should compute permission
        with patch.object(self.access_manager, '_compute_permission', return_value=True) as mock_compute:
            result1 = self.access_manager.check_permission(user_id, resource, action)
            assert result1 is True
            assert mock_compute.call_count == 1
        
        # Second call should use cache
        with patch.object(self.access_manager, '_compute_permission', return_value=True) as mock_compute:
            result2 = self.access_manager.check_permission(user_id, resource, action)
            assert result2 is True
            assert mock_compute.call_count == 0  # Should not be called due to cache
    
    def test_role_hierarchy(self):
        """Test role hierarchy handling."""
        # Mock role hierarchy: admin > manager > user
        self.access_manager.role_hierarchy = {
            "admin": ["manager", "user"],
            "manager": ["user"],
            "user": []
        }
        
        # Admin should inherit manager and user permissions
        admin_roles = self.access_manager._get_effective_roles(["admin"])
        assert "admin" in admin_roles
        assert "manager" in admin_roles
        assert "user" in admin_roles
        
        # Manager should inherit user permissions
        manager_roles = self.access_manager._get_effective_roles(["manager"])
        assert "manager" in manager_roles
        assert "user" in manager_roles
        assert "admin" not in manager_roles


class TestSecurityIntegration:
    """Integration tests for security components."""
    
    @pytest.mark.asyncio
    async def test_full_security_pipeline(self):
        """Test full security pipeline integration."""
        # Initialize all components
        audit_logger = init_audit_logger("integration-test", "test-tenant")
        enforcer = TenantSecurityEnforcer()
        scanner = SecurityScanner()
        
        # Test plugin validation and execution
        plugin_code = "print('Secure plugin execution')"
        plugin_metadata = {"name": "test_integration_plugin"}
        
        # Validate plugin code
        is_valid = await scanner.validate_plugin_code(plugin_code, plugin_metadata)
        assert is_valid is True
        
        # Execute in secure sandbox
        async with PluginSandbox("integration-test-plugin") as sandbox:
            result = await sandbox.execute_in_subprocess(plugin_code)
            assert result["return_code"] == 0
            assert "Secure plugin execution" in result["stdout"]
    
    def test_error_handling_chain(self):
        """Test proper error handling throughout security chain."""
        from dotmac.security.audit.logger import get_audit_logger
        
        # Test proper error propagation
        with pytest.raises(RuntimeError):
            # Should raise clear error when not initialized
            get_audit_logger()


# Test configuration
@pytest.fixture
def temp_directory():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_logger():
    """Mock structlog logger."""
    return MagicMock()


if __name__ == "__main__":
    # Run comprehensive security tests
    pytest.main([__file__, "-v", "--tb=short", "--cov=dotmac.security", "--cov-report=term-missing"])