"""
Tests for WebSocket authentication.
"""

import time
import pytest
from unittest.mock import Mock, AsyncMock, patch

from dotmac.websockets.auth.manager import AuthManager
from dotmac.websockets.auth.types import AuthResult, UserInfo
from dotmac.websockets.auth.middleware import AuthMiddleware
from dotmac.websockets.core.config import AuthConfig


class MockSession:
    """Mock session for testing."""
    
    def __init__(self, session_id="test-session"):
        self.session_id = session_id
        self.metadata = Mock()
        self.metadata.custom_data = {}
        self._user_id = None
        self._tenant_id = None
        self._authenticated = False
        self.messages_sent = []
    
    @property
    def user_id(self):
        return self._user_id
    
    @property
    def tenant_id(self):
        return self._tenant_id
    
    @property
    def is_authenticated(self):
        return self._authenticated
    
    def set_user_info(self, user_id, tenant_id=None):
        self._user_id = user_id
        self._tenant_id = tenant_id
        self._authenticated = True
    
    async def send_message(self, message_type, data):
        self.messages_sent.append({"type": message_type, "data": data})


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.path = "/ws"
        self.request_headers = Mock()
        self.request_headers.raw = []
        self.request_headers.get = Mock(return_value=None)


class TestAuthManager:
    """Test authentication manager."""
    
    @pytest.fixture
    def auth_config(self):
        """Create test auth configuration."""
        return AuthConfig(
            enabled=True,
            jwt_secret_key="test_secret_key_123",
            jwt_algorithm="HS256",
            require_token=True
        )
    
    @pytest.fixture
    def auth_manager(self, auth_config):
        """Create auth manager."""
        return AuthManager(auth_config)
    
    @pytest.mark.asyncio
    async def test_jwt_authentication_success(self, auth_manager):
        """Test successful JWT authentication."""
        # Mock JWT to avoid dependency issues
        with patch('dotmac.websockets.auth.manager.jwt') as mock_jwt:
            mock_jwt.decode.return_value = {
                "sub": "user123",
                "username": "testuser",
                "email": "test@example.com",
                "tenant_id": "tenant456",
                "roles": ["user", "admin"],
                "permissions": ["read", "write"],
                "exp": time.time() + 3600  # 1 hour from now
            }
            
            result = await auth_manager.authenticate_token("valid_token")
            
            assert result.success
            assert result.user_info.user_id == "user123"
            assert result.user_info.username == "testuser"
            assert result.user_info.email == "test@example.com"
            assert result.user_info.tenant_id == "tenant456"
            assert "user" in result.user_info.roles
            assert "admin" in result.user_info.roles
            assert "read" in result.user_info.permissions
            assert "write" in result.user_info.permissions
    
    @pytest.mark.asyncio
    async def test_jwt_authentication_expired(self, auth_manager):
        """Test JWT authentication with expired token."""
        with patch('dotmac.websockets.auth.manager.jwt') as mock_jwt:
            from jwt import ExpiredSignatureError
            mock_jwt.decode.side_effect = ExpiredSignatureError("Token expired")
            mock_jwt.ExpiredSignatureError = ExpiredSignatureError
            
            result = await auth_manager.authenticate_token("expired_token")
            
            assert not result.success
            assert "expired" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_jwt_authentication_invalid(self, auth_manager):
        """Test JWT authentication with invalid token."""
        with patch('dotmac.websockets.auth.manager.jwt') as mock_jwt:
            from jwt import InvalidTokenError
            mock_jwt.decode.side_effect = InvalidTokenError("Invalid token")
            mock_jwt.InvalidTokenError = InvalidTokenError
            
            result = await auth_manager.authenticate_token("invalid_token")
            
            assert not result.success
            assert "invalid" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_jwt_authentication_missing_user_id(self, auth_manager):
        """Test JWT authentication with missing user ID."""
        with patch('dotmac.websockets.auth.manager.jwt') as mock_jwt:
            mock_jwt.decode.return_value = {
                "username": "testuser",
                # Missing 'sub' or 'user_id'
            }
            
            result = await auth_manager.authenticate_token("token_without_user_id")
            
            assert not result.success
            assert "user id" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_authentication_disabled(self):
        """Test authentication when disabled."""
        config = AuthConfig(enabled=False)
        auth_manager = AuthManager(config)
        
        result = await auth_manager.authenticate_token("any_token")
        
        assert result.success
        assert result.user_info.user_id == "anonymous"
    
    @pytest.mark.asyncio
    async def test_required_permissions_check(self, auth_manager):
        """Test required permissions validation."""
        auth_manager.config.require_permissions = ["admin", "write"]
        
        with patch('dotmac.websockets.auth.manager.jwt') as mock_jwt:
            # User without required permissions
            mock_jwt.decode.return_value = {
                "sub": "user123",
                "permissions": ["read"]  # Missing "admin" and "write"
            }
            
            result = await auth_manager.authenticate_token("token")
            
            assert not result.success
            assert "permissions" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_token_caching(self, auth_manager):
        """Test token result caching."""
        with patch('dotmac.websockets.auth.manager.jwt') as mock_jwt:
            mock_jwt.decode.return_value = {
                "sub": "user123",
                "exp": time.time() + 3600
            }
            
            # First call
            result1 = await auth_manager.authenticate_token("cached_token")
            assert result1.success
            assert mock_jwt.decode.call_count == 1
            
            # Second call - should use cache
            result2 = await auth_manager.authenticate_token("cached_token")
            assert result2.success
            assert mock_jwt.decode.call_count == 1  # Not called again
    
    @pytest.mark.asyncio
    async def test_user_resolution(self, auth_manager):
        """Test user information resolution."""
        # Mock external user resolver
        auth_manager.config.user_resolver_url = "http://localhost/users"
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "user_id": "user123",
                "username": "testuser",
                "email": "test@example.com",
                "tenant_id": "tenant456",
                "roles": ["user"],
                "permissions": ["read"]
            })
            mock_get.return_value.__aenter__.return_value = mock_response
            
            user_info = await auth_manager.resolve_user("user123")
            
            assert user_info is not None
            assert user_info.user_id == "user123"
            assert user_info.username == "testuser"
            assert user_info.tenant_id == "tenant456"
    
    @pytest.mark.asyncio
    async def test_websocket_auth_validation(self, auth_manager):
        """Test WebSocket authentication validation."""
        websocket = MockWebSocket()
        websocket.request_headers.raw = [("Authorization", "Bearer valid_token")]
        
        with patch.object(auth_manager, 'authenticate_token') as mock_auth:
            mock_auth.return_value = AuthResult.success_result(
                UserInfo(user_id="user123", tenant_id="tenant456")
            )
            
            result = await auth_manager.validate_websocket_auth(websocket, "/ws")
            
            assert result.success
            assert result.user_info.user_id == "user123"
            assert mock_auth.called
    
    def test_token_extraction_from_headers(self, auth_manager):
        """Test token extraction from headers."""
        # Bearer token
        headers = {"Authorization": "Bearer abc123"}
        token = auth_manager.extract_token_from_headers(headers)
        assert token == "abc123"
        
        # Token prefix
        headers = {"Authorization": "Token xyz789"}
        token = auth_manager.extract_token_from_headers(headers)
        assert token == "xyz789"
        
        # Raw token
        headers = {"Authorization": "raw_token"}
        token = auth_manager.extract_token_from_headers(headers)
        assert token == "raw_token"
        
        # No token
        headers = {}
        token = auth_manager.extract_token_from_headers(headers)
        assert token is None
    
    def test_token_extraction_from_query(self, auth_manager):
        """Test token extraction from query parameters."""
        # With token
        query_params = {"token": "query_token_123"}
        token = auth_manager.extract_token_from_query(query_params)
        assert token == "query_token_123"
        
        # No token
        query_params = {"other_param": "value"}
        token = auth_manager.extract_token_from_query(query_params)
        assert token is None
    
    def test_cache_cleanup(self, auth_manager):
        """Test cache cleanup functionality."""
        # Add expired entries to cache
        expired_time = time.time() - 1000
        auth_manager._token_cache["expired_token"] = (Mock(), expired_time)
        auth_manager._user_cache["expired_user"] = (Mock(), expired_time)
        
        # Add valid entries
        valid_time = time.time() + 1000
        auth_manager._token_cache["valid_token"] = (Mock(), valid_time)
        auth_manager._user_cache["valid_user"] = (Mock(), valid_time)
        
        # Run cleanup
        auth_manager.cleanup_cache()
        
        # Expired entries should be removed
        assert "expired_token" not in auth_manager._token_cache
        assert "expired_user" not in auth_manager._user_cache
        
        # Valid entries should remain
        assert "valid_token" in auth_manager._token_cache
        assert "valid_user" in auth_manager._user_cache
    
    def test_statistics(self, auth_manager):
        """Test statistics collection."""
        stats = auth_manager.get_stats()
        
        assert "enabled" in stats
        assert "require_token" in stats
        assert "cached_tokens" in stats
        assert "cached_users" in stats
        assert "jwt_available" in stats
        assert "user_resolver_configured" in stats


class TestAuthMiddleware:
    """Test authentication middleware."""
    
    @pytest.fixture
    def auth_config(self):
        """Create test auth configuration."""
        return AuthConfig(enabled=True, jwt_secret_key="test_key")
    
    @pytest.fixture
    def auth_manager(self, auth_config):
        """Create auth manager."""
        return AuthManager(auth_config)
    
    @pytest.fixture
    def auth_middleware(self, auth_manager):
        """Create auth middleware."""
        return AuthMiddleware(auth_manager)
    
    @pytest.mark.asyncio
    async def test_connection_authentication(self, auth_middleware):
        """Test connection authentication."""
        websocket = MockWebSocket()
        
        with patch.object(auth_middleware.auth_manager, 'validate_websocket_auth') as mock_auth:
            mock_auth.return_value = AuthResult.success_result(
                UserInfo(user_id="user123", tenant_id="tenant456")
            )
            
            result = await auth_middleware.authenticate_connection(websocket, "/ws")
            
            assert result.success
            assert result.user_info.user_id == "user123"
    
    @pytest.mark.asyncio
    async def test_message_permission_check(self, auth_middleware):
        """Test message permission checking."""
        session = MockSession()
        
        # Anonymous session - should allow ping
        allowed = await auth_middleware.check_message_permission(session, "ping")
        assert allowed
        
        # Anonymous session - should not allow protected message
        allowed = await auth_middleware.check_message_permission(session, "admin_action")
        assert not allowed
        
        # Authenticated session
        session.set_user_info("user123", "tenant456")
        allowed = await auth_middleware.check_message_permission(session, "admin_action")
        assert allowed  # No specific permission required
    
    @pytest.mark.asyncio
    async def test_channel_access_check(self, auth_middleware):
        """Test channel access checking."""
        session = MockSession()
        
        # Public channel - should allow anonymous access
        allowed = await auth_middleware.check_channel_access(session, "public:announcements")
        assert allowed
        
        # Private channel - should not allow anonymous access
        allowed = await auth_middleware.check_channel_access(session, "private:admin")
        assert not allowed
        
        # Authenticated session
        session.set_user_info("user123", "tenant456")
        session.metadata.custom_data["user_info"] = Mock()
        session.metadata.custom_data["user_info"].user_id = "user123"
        session.metadata.custom_data["user_info"].tenant_id = "tenant456"
        
        # User-specific channel
        allowed = await auth_middleware.check_channel_access(session, "user:user123:notifications")
        assert allowed
        
        # Different user's channel
        allowed = await auth_middleware.check_channel_access(session, "user:other_user:notifications")
        assert not allowed
    
    def test_auth_required_decorator(self, auth_middleware):
        """Test auth required decorator."""
        decorator = auth_middleware.create_auth_required_decorator()
        
        handler_called = False
        original_data = {"test": "data"}
        
        @decorator
        async def test_handler(session, data):
            nonlocal handler_called
            handler_called = True
            assert data == original_data
        
        # Test with authenticated session
        session = MockSession()
        session.set_user_info("user123")
        
        # Should call handler
        import asyncio
        asyncio.run(test_handler(session, original_data))
        assert handler_called
    
    def test_permission_required_decorator(self, auth_middleware):
        """Test permission required decorator."""
        decorator = auth_middleware.create_permission_required_decorator("admin")
        
        @decorator
        async def test_handler(session, data):
            return "success"
        
        # Test with session lacking permission
        session = MockSession()
        session.set_user_info("user123")
        
        import asyncio
        asyncio.run(test_handler(session, {}))
        
        # Should have sent permission denied message
        assert len(session.messages_sent) > 0
        assert any(msg["type"] == "permission_denied" for msg in session.messages_sent)
    
    def test_role_required_decorator(self, auth_middleware):
        """Test role required decorator."""
        decorator = auth_middleware.create_role_required_decorator(["admin", "moderator"])
        
        @decorator
        async def test_handler(session, data):
            return "success"
        
        # Test with unauthenticated session
        session = MockSession()
        
        import asyncio
        asyncio.run(test_handler(session, {}))
        
        # Should have sent auth required message
        assert len(session.messages_sent) > 0
        assert any(msg["type"] == "auth_required" for msg in session.messages_sent)
    
    def test_statistics(self, auth_middleware):
        """Test middleware statistics."""
        stats = auth_middleware.get_stats()
        
        assert "auth_success_handlers" in stats
        assert "auth_failure_handlers" in stats
        assert "auth_manager_stats" in stats


class TestUserInfo:
    """Test UserInfo class."""
    
    def test_user_info_creation(self):
        """Test UserInfo creation."""
        user_info = UserInfo(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            tenant_id="tenant456",
            roles=["user", "admin"],
            permissions=["read", "write", "delete"]
        )
        
        assert user_info.user_id == "user123"
        assert user_info.username == "testuser"
        assert user_info.email == "test@example.com"
        assert user_info.tenant_id == "tenant456"
        assert "user" in user_info.roles
        assert "admin" in user_info.roles
        assert "read" in user_info.permissions
    
    def test_permission_checking(self):
        """Test permission checking methods."""
        user_info = UserInfo(
            user_id="user123",
            roles=["user", "admin"],
            permissions=["read", "write"]
        )
        
        # Has permission
        assert user_info.has_permission("read")
        assert user_info.has_permission("write")
        
        # Doesn't have permission
        assert not user_info.has_permission("delete")
        
        # Has role
        assert user_info.has_role("user")
        assert user_info.has_role("admin")
        
        # Doesn't have role
        assert not user_info.has_role("moderator")
        
        # Has any role
        assert user_info.has_any_role(["user", "moderator"])
        assert user_info.has_any_role(["admin"])
        assert not user_info.has_any_role(["moderator", "guest"])


class TestAuthResult:
    """Test AuthResult class."""
    
    def test_success_result_creation(self):
        """Test successful auth result creation."""
        user_info = UserInfo(user_id="user123")
        result = AuthResult.success_result(user_info, "jwt", time.time() + 3600)
        
        assert result.success
        assert result.user_info == user_info
        assert result.token_type == "jwt"
        assert result.error is None
    
    def test_failure_result_creation(self):
        """Test failed auth result creation."""
        result = AuthResult.failure_result("Invalid token", "jwt")
        
        assert not result.success
        assert result.error == "Invalid token"
        assert result.auth_method == "jwt"
        assert result.user_info is None


if __name__ == "__main__":
    pytest.main([__file__])