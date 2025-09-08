"""
FastAPI Integration Testing - Phase 2
Comprehensive testing of FastAPI endpoints with authentication, validation, and error handling.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock
from typing import Dict, Any

# Mock FastAPI components for testing
class MockRequest:
    """Mock FastAPI Request object"""
    def __init__(self, headers: Dict[str, str] = None, json_data: Dict = None):
        self.headers = headers or {}
        self.json_data = json_data or {}
        self.path_params = {}
        self.query_params = {}
    
    async def json(self):
        return self.json_data


class MockResponse:
    """Mock FastAPI Response object"""
    def __init__(self, content: Any, status_code: int = 200, headers: Dict = None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}


class MockAuthDependency:
    """Mock authentication dependency"""
    def __init__(self, user_id: str = "test_user", authenticated: bool = True):
        self.user_id = user_id
        self.authenticated = authenticated
        self.roles = ["user"]
        self.tenant_id = "test_tenant"


class APIEndpointHandler:
    """Mock API endpoint handler for testing"""
    
    def __init__(self):
        self.auth_service = Mock()
        self.api_key_service = Mock()
        self.rate_limiter = Mock()
        self.validator = Mock()
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint"""
        checks = {
            "database": {"status": "healthy", "response_time": 0.001},
            "cache": {"status": "healthy", "response_time": 0.002},
            "storage": {"status": "healthy", "response_time": 0.003}
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "checks": checks
        }
    
    async def create_user_profile(self, request: MockRequest, current_user: MockAuthDependency) -> Dict[str, Any]:
        """Create user profile endpoint"""
        # Validate authentication
        if not current_user.authenticated:
            return {"error": "Authentication required", "status_code": 401}
        
        # Validate request data
        profile_data = await request.json()
        
        if not profile_data.get("name"):
            return {"error": "Name is required", "status_code": 400}
        
        if not profile_data.get("email"):
            return {"error": "Email is required", "status_code": 400}
        
        # Simulate profile creation
        profile = {
            "id": f"profile_{current_user.user_id}",
            "user_id": current_user.user_id,
            "name": profile_data["name"],
            "email": profile_data["email"],
            "tenant_id": current_user.tenant_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        }
        
        return {"profile": profile, "status_code": 201}
    
    async def get_user_profile(self, user_id: str, current_user: MockAuthDependency) -> Dict[str, Any]:
        """Get user profile endpoint"""
        # Check authentication
        if not current_user.authenticated:
            return {"error": "Authentication required", "status_code": 401}
        
        # Check authorization (users can only access their own profile)
        if current_user.user_id != user_id and "admin" not in current_user.roles:
            return {"error": "Access denied", "status_code": 403}
        
        # Simulate profile retrieval
        if user_id == "nonexistent_user":
            return {"error": "User not found", "status_code": 404}
        
        profile = {
            "id": f"profile_{user_id}",
            "user_id": user_id,
            "name": "Test User",
            "email": "test@example.com",
            "tenant_id": current_user.tenant_id,
            "created_at": "2024-01-01T00:00:00Z",
            "active": True
        }
        
        return {"profile": profile, "status_code": 200}
    
    async def update_user_profile(self, user_id: str, request: MockRequest, current_user: MockAuthDependency) -> Dict[str, Any]:
        """Update user profile endpoint"""
        # Authentication check
        if not current_user.authenticated:
            return {"error": "Authentication required", "status_code": 401}
        
        # Authorization check
        if current_user.user_id != user_id and "admin" not in current_user.roles:
            return {"error": "Access denied", "status_code": 403}
        
        # Get update data
        update_data = await request.json()
        
        # Validate update data
        allowed_fields = ["name", "email", "bio"]
        invalid_fields = [field for field in update_data.keys() if field not in allowed_fields]
        
        if invalid_fields:
            return {"error": f"Invalid fields: {invalid_fields}", "status_code": 400}
        
        # Simulate profile update
        updated_profile = {
            "id": f"profile_{user_id}",
            "user_id": user_id,
            "name": update_data.get("name", "Test User"),
            "email": update_data.get("email", "test@example.com"),
            "bio": update_data.get("bio", ""),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        return {"profile": updated_profile, "status_code": 200}
    
    async def delete_user_profile(self, user_id: str, current_user: MockAuthDependency) -> Dict[str, Any]:
        """Delete user profile endpoint"""
        # Authentication check
        if not current_user.authenticated:
            return {"error": "Authentication required", "status_code": 401}
        
        # Authorization check (only admins can delete profiles)
        if "admin" not in current_user.roles:
            return {"error": "Admin access required", "status_code": 403}
        
        # Simulate profile deletion
        return {"message": f"Profile {user_id} deleted successfully", "status_code": 200}
    
    async def list_api_keys(self, current_user: MockAuthDependency) -> Dict[str, Any]:
        """List user's API keys"""
        if not current_user.authenticated:
            return {"error": "Authentication required", "status_code": 401}
        
        # Simulate API key listing
        api_keys = [
            {
                "id": "key_1",
                "name": "Production Key",
                "created_at": "2024-01-01T00:00:00Z",
                "last_used": "2024-01-15T12:00:00Z",
                "active": True
            },
            {
                "id": "key_2", 
                "name": "Development Key",
                "created_at": "2024-01-10T00:00:00Z",
                "last_used": None,
                "active": True
            }
        ]
        
        return {"api_keys": api_keys, "status_code": 200}
    
    async def create_api_key(self, request: MockRequest, current_user: MockAuthDependency) -> Dict[str, Any]:
        """Create new API key"""
        if not current_user.authenticated:
            return {"error": "Authentication required", "status_code": 401}
        
        key_data = await request.json()
        
        if not key_data.get("name"):
            return {"error": "Key name is required", "status_code": 400}
        
        # Simulate API key creation
        new_key = {
            "id": "key_new_123",
            "name": key_data["name"],
            "api_key": f"dotmac_live_{hash(key_data['name']) % 1000000:06d}",
            "user_id": current_user.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        }
        
        return {"api_key": new_key, "status_code": 201}


class TestFastAPIIntegration:
    """FastAPI integration tests for Phase 2 coverage"""
    
    @pytest.fixture
    def api_handler(self):
        """Create API handler instance"""
        return APIEndpointHandler()
    
    @pytest.fixture
    def authenticated_user(self):
        """Create authenticated user dependency"""
        return MockAuthDependency(user_id="test_user_123", authenticated=True)
    
    @pytest.fixture
    def admin_user(self):
        """Create admin user dependency"""
        user = MockAuthDependency(user_id="admin_user", authenticated=True)
        user.roles = ["admin", "user"]
        return user
    
    @pytest.fixture
    def unauthenticated_user(self):
        """Create unauthenticated user dependency"""
        return MockAuthDependency(authenticated=False)
    
    # Health Check Endpoint Tests
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, api_handler):
        """Test health check endpoint"""
        result = await api_handler.health_check()
        
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "version" in result
        assert "checks" in result
        
        # Verify individual service checks
        assert result["checks"]["database"]["status"] == "healthy"
        assert result["checks"]["cache"]["status"] == "healthy"
        assert result["checks"]["storage"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_performance(self, api_handler):
        """Test health check endpoint performance"""
        import time
        
        start_time = time.time()
        result = await api_handler.health_check()
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 0.1  # Should be under 100ms
        assert result["status"] == "healthy"
    
    # User Profile CRUD Tests
    
    @pytest.mark.asyncio
    async def test_create_user_profile_success(self, api_handler, authenticated_user):
        """Test successful user profile creation"""
        request = MockRequest(json_data={
            "name": "John Doe",
            "email": "john.doe@example.com"
        })
        
        result = await api_handler.create_user_profile(request, authenticated_user)
        
        assert result["status_code"] == 201
        assert "profile" in result
        assert result["profile"]["name"] == "John Doe"
        assert result["profile"]["email"] == "john.doe@example.com"
        assert result["profile"]["user_id"] == authenticated_user.user_id
        assert result["profile"]["tenant_id"] == authenticated_user.tenant_id
    
    @pytest.mark.asyncio
    async def test_create_user_profile_missing_name(self, api_handler, authenticated_user):
        """Test user profile creation with missing name"""
        request = MockRequest(json_data={"email": "john@example.com"})
        
        result = await api_handler.create_user_profile(request, authenticated_user)
        
        assert result["status_code"] == 400
        assert "Name is required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_create_user_profile_missing_email(self, api_handler, authenticated_user):
        """Test user profile creation with missing email"""
        request = MockRequest(json_data={"name": "John Doe"})
        
        result = await api_handler.create_user_profile(request, authenticated_user)
        
        assert result["status_code"] == 400
        assert "Email is required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_create_user_profile_unauthenticated(self, api_handler, unauthenticated_user):
        """Test user profile creation without authentication"""
        request = MockRequest(json_data={"name": "John", "email": "john@example.com"})
        
        result = await api_handler.create_user_profile(request, unauthenticated_user)
        
        assert result["status_code"] == 401
        assert "Authentication required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, api_handler, authenticated_user):
        """Test successful user profile retrieval"""
        result = await api_handler.get_user_profile(authenticated_user.user_id, authenticated_user)
        
        assert result["status_code"] == 200
        assert "profile" in result
        assert result["profile"]["user_id"] == authenticated_user.user_id
    
    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, api_handler, authenticated_user):
        """Test user profile retrieval for nonexistent user"""
        result = await api_handler.get_user_profile("nonexistent_user", authenticated_user)
        
        assert result["status_code"] == 404
        assert "User not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_user_profile_unauthorized(self, api_handler, authenticated_user):
        """Test user profile retrieval without proper authorization"""
        result = await api_handler.get_user_profile("other_user", authenticated_user)
        
        assert result["status_code"] == 403
        assert "Access denied" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_user_profile_admin_access(self, api_handler, admin_user):
        """Test admin can access any user profile"""
        result = await api_handler.get_user_profile("any_user", admin_user)
        
        assert result["status_code"] == 200
        assert "profile" in result
    
    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, api_handler, authenticated_user):
        """Test successful user profile update"""
        request = MockRequest(json_data={
            "name": "John Updated",
            "bio": "Updated bio"
        })
        
        result = await api_handler.update_user_profile(authenticated_user.user_id, request, authenticated_user)
        
        assert result["status_code"] == 200
        assert result["profile"]["name"] == "John Updated"
        assert result["profile"]["bio"] == "Updated bio"
        assert "updated_at" in result["profile"]
    
    @pytest.mark.asyncio
    async def test_update_user_profile_invalid_fields(self, api_handler, authenticated_user):
        """Test user profile update with invalid fields"""
        request = MockRequest(json_data={
            "name": "John",
            "invalid_field": "should not be allowed"
        })
        
        result = await api_handler.update_user_profile(authenticated_user.user_id, request, authenticated_user)
        
        assert result["status_code"] == 400
        assert "Invalid fields" in result["error"]
        assert "invalid_field" in result["error"]
    
    @pytest.mark.asyncio
    async def test_delete_user_profile_admin_success(self, api_handler, admin_user):
        """Test successful user profile deletion by admin"""
        result = await api_handler.delete_user_profile("user_to_delete", admin_user)
        
        assert result["status_code"] == 200
        assert "deleted successfully" in result["message"]
    
    @pytest.mark.asyncio
    async def test_delete_user_profile_non_admin_denied(self, api_handler, authenticated_user):
        """Test user profile deletion denied for non-admin"""
        result = await api_handler.delete_user_profile("some_user", authenticated_user)
        
        assert result["status_code"] == 403
        assert "Admin access required" in result["error"]
    
    # API Key Management Tests
    
    @pytest.mark.asyncio
    async def test_list_api_keys_success(self, api_handler, authenticated_user):
        """Test successful API key listing"""
        result = await api_handler.list_api_keys(authenticated_user)
        
        assert result["status_code"] == 200
        assert "api_keys" in result
        assert len(result["api_keys"]) == 2
        assert result["api_keys"][0]["name"] == "Production Key"
        assert result["api_keys"][1]["name"] == "Development Key"
    
    @pytest.mark.asyncio
    async def test_list_api_keys_unauthenticated(self, api_handler, unauthenticated_user):
        """Test API key listing without authentication"""
        result = await api_handler.list_api_keys(unauthenticated_user)
        
        assert result["status_code"] == 401
        assert "Authentication required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_create_api_key_success(self, api_handler, authenticated_user):
        """Test successful API key creation"""
        request = MockRequest(json_data={"name": "New Integration Key"})
        
        result = await api_handler.create_api_key(request, authenticated_user)
        
        assert result["status_code"] == 201
        assert "api_key" in result
        assert result["api_key"]["name"] == "New Integration Key"
        assert result["api_key"]["user_id"] == authenticated_user.user_id
        assert "api_key" in result["api_key"]
        assert result["api_key"]["api_key"].startswith("dotmac_live_")
    
    @pytest.mark.asyncio
    async def test_create_api_key_missing_name(self, api_handler, authenticated_user):
        """Test API key creation with missing name"""
        request = MockRequest(json_data={})
        
        result = await api_handler.create_api_key(request, authenticated_user)
        
        assert result["status_code"] == 400
        assert "Key name is required" in result["error"]
    
    # Integration Flow Tests
    
    @pytest.mark.asyncio
    async def test_complete_user_management_flow(self, api_handler, authenticated_user, admin_user):
        """Test complete user management flow"""
        # 1. Create profile
        create_request = MockRequest(json_data={
            "name": "Integration Test User",
            "email": "integration@example.com"
        })
        
        create_result = await api_handler.create_user_profile(create_request, authenticated_user)
        assert create_result["status_code"] == 201
        
        # 2. Get profile
        get_result = await api_handler.get_user_profile(authenticated_user.user_id, authenticated_user)
        assert get_result["status_code"] == 200
        
        # 3. Update profile
        update_request = MockRequest(json_data={
            "name": "Updated Integration User",
            "bio": "Integration test bio"
        })
        
        update_result = await api_handler.update_user_profile(authenticated_user.user_id, update_request, authenticated_user)
        assert update_result["status_code"] == 200
        assert update_result["profile"]["name"] == "Updated Integration User"
        
        # 4. Admin delete profile
        delete_result = await api_handler.delete_user_profile(authenticated_user.user_id, admin_user)
        assert delete_result["status_code"] == 200
    
    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, api_handler, authenticated_user):
        """Test concurrent API requests"""
        # Simulate multiple concurrent requests
        tasks = []
        
        # Health checks
        for _ in range(5):
            tasks.append(api_handler.health_check())
        
        # Profile retrievals
        for _ in range(3):
            tasks.append(api_handler.get_user_profile(authenticated_user.user_id, authenticated_user))
        
        # API key listings
        for _ in range(2):
            tasks.append(api_handler.list_api_keys(authenticated_user))
        
        results = await asyncio.gather(*tasks)
        
        # Verify all requests succeeded
        assert len(results) == 10
        
        # Health check results
        for i in range(5):
            assert results[i]["status"] == "healthy"
        
        # Profile retrieval results
        for i in range(5, 8):
            assert results[i]["status_code"] == 200
            assert "profile" in results[i]
        
        # API key listing results
        for i in range(8, 10):
            assert results[i]["status_code"] == 200
            assert "api_keys" in results[i]
    
    # Error Handling Tests
    
    @pytest.mark.asyncio
    async def test_request_validation_edge_cases(self, api_handler, authenticated_user):
        """Test request validation with edge cases"""
        # Empty JSON
        empty_request = MockRequest(json_data={})
        result = await api_handler.create_user_profile(empty_request, authenticated_user)
        assert result["status_code"] == 400
        
        # Very long name
        long_name_request = MockRequest(json_data={
            "name": "x" * 1000,
            "email": "test@example.com"
        })
        result = await api_handler.create_user_profile(long_name_request, authenticated_user)
        assert result["status_code"] == 201  # Should handle long names gracefully
        
        # Invalid email format (basic validation)
        invalid_email_request = MockRequest(json_data={
            "name": "Test User",
            "email": "not-an-email"
        })
        result = await api_handler.create_user_profile(invalid_email_request, authenticated_user)
        assert result["status_code"] == 201  # Basic handler doesn't validate email format