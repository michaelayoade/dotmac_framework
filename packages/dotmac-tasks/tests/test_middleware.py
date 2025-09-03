"""
Tests for HTTP middleware functionality.
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from dotmac.tasks import (
    BackgroundOperationsManager,
    BackgroundOperationsMiddleware,
    MemoryStorage,
    OperationStatus,
    add_background_operations_middleware,
    get_idempotency_key,
    is_idempotent_request,
    set_operation_result,
)


class TestMiddleware:
    """Test middleware functionality."""

    @pytest.fixture
    async def manager(self):
        """Create manager with memory storage."""
        storage = MemoryStorage()
        manager = BackgroundOperationsManager(storage=storage)
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.fixture
    def app_with_middleware(self, manager):
        """Create FastAPI app with middleware."""
        app = FastAPI()
        
        # Add middleware
        app.add_middleware(
            BackgroundOperationsMiddleware,
            manager=manager
        )
        
        # Test route that uses idempotency
        @app.post("/api/send-email")
        async def send_email(request: Request):
            # Check if request is idempotent
            if is_idempotent_request(request):
                idempotency_key = get_idempotency_key(request)
                
                # Simulate work
                result = {
                    "message_id": "123",
                    "status": "sent",
                    "idempotency_key": idempotency_key
                }
                
                # Set result for caching
                set_operation_result(request, result)
                
                return result
            else:
                # Non-idempotent request
                return {"message_id": "456", "status": "sent"}
        
        # Non-exempt route
        @app.get("/api/data")
        async def get_data():
            return {"data": "test"}
        
        # Exempt route
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        return app

    def test_middleware_exempt_paths(self, app_with_middleware):
        """Test that exempt paths are not processed."""
        client = TestClient(app_with_middleware)
        
        # Exempt paths should work without idempotency
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Idempotency-Key" not in response.headers
        
        response = client.get("/docs")
        # FastAPI returns 404 for /docs if not configured, but middleware shouldn't process
        assert "X-Idempotency-Key" not in response.headers

    def test_middleware_no_idempotency_header(self, app_with_middleware):
        """Test request without idempotency header passes through."""
        client = TestClient(app_with_middleware)
        
        response = client.post("/api/send-email")
        assert response.status_code == 200
        assert "X-Idempotency-Key" not in response.headers
        
        data = response.json()
        assert data["message_id"] == "456"  # Non-idempotent path

    def test_middleware_new_idempotency_key(self, app_with_middleware):
        """Test request with new idempotency key."""
        client = TestClient(app_with_middleware)
        
        headers = {"Idempotency-Key": "test-key-123"}
        response = client.post("/api/send-email", headers=headers)
        
        assert response.status_code == 200
        assert response.headers["X-Idempotency-Key"] == "test-key-123"
        
        data = response.json()
        assert data["message_id"] == "123"
        assert data["idempotency_key"] == "test-key-123"

    async def test_middleware_completed_operation_cached_result(self, manager, app_with_middleware):
        """Test that completed operations return cached results."""
        client = TestClient(app_with_middleware)
        
        # Create completed idempotency key
        key_obj = await manager.create_idempotency_key(
            tenant_id="default",
            user_id=None,
            operation_type="POST_/api/send-email",
            key="completed-key-123"
        )
        
        cached_result = {"cached": True, "message_id": "cached-123"}
        await manager.complete_idempotent_operation(
            "completed-key-123", cached_result
        )
        
        # Request with completed key should return cached result
        headers = {"Idempotency-Key": "completed-key-123"}
        response = client.post("/api/send-email", headers=headers)
        
        assert response.status_code == 200
        assert response.headers["X-Cache-Hit"] == "true"
        assert response.headers["X-Idempotency-Key"] == "completed-key-123"
        
        data = response.json()
        assert data == cached_result

    async def test_middleware_failed_operation_error_result(self, manager, app_with_middleware):
        """Test that failed operations return error results.""" 
        client = TestClient(app_with_middleware)
        
        # Create failed idempotency key
        key_obj = await manager.create_idempotency_key(
            tenant_id="default",
            user_id=None,
            operation_type="POST_/api/send-email",
            key="failed-key-123"
        )
        
        await manager.complete_idempotent_operation(
            "failed-key-123", {}, error="SMTP connection failed"
        )
        
        # Request with failed key should return error
        headers = {"Idempotency-Key": "failed-key-123"}
        response = client.post("/api/send-email", headers=headers)
        
        assert response.status_code == 400
        assert response.headers["X-Cache-Hit"] == "true"
        assert response.headers["X-Idempotency-Key"] == "failed-key-123"
        
        data = response.json()
        assert data["status"] == "failed"
        assert "SMTP connection failed" in data["error"]

    async def test_middleware_in_progress_operation(self, manager, app_with_middleware):
        """Test in-progress operations return 202."""
        client = TestClient(app_with_middleware)
        
        # Create in-progress idempotency key
        key_obj = await manager.create_idempotency_key(
            tenant_id="default", 
            user_id=None,
            operation_type="POST_/api/send-email",
            key="in-progress-key-123"
        )
        
        # Mark as in progress
        current_data = await manager.storage.get_idempotency("in-progress-key-123")
        current_data["status"] = OperationStatus.IN_PROGRESS.value
        await manager.storage.set_idempotency("in-progress-key-123", current_data, 3600)
        
        # Request with in-progress key should return 202
        headers = {"Idempotency-Key": "in-progress-key-123"}
        response = client.post("/api/send-email", headers=headers)
        
        assert response.status_code == 202
        assert response.headers["X-Idempotency-Key"] == "in-progress-key-123"
        
        data = response.json()
        assert data["status"] == "in_progress"
        assert "being processed" in data["message"]

    def test_add_background_operations_middleware_helper(self):
        """Test the middleware helper function."""
        app = FastAPI()
        
        # Add middleware using helper
        manager = add_background_operations_middleware(app)
        
        assert isinstance(manager, BackgroundOperationsManager)
        
        # Check middleware was added
        middleware_types = [type(middleware).__name__ for middleware in app.middleware_stack]
        assert "BackgroundOperationsMiddleware" in str(middleware_types)

    def test_custom_middleware_configuration(self, manager):
        """Test middleware with custom configuration."""
        app = FastAPI()
        
        custom_exempt_paths = {"/custom-health", "/custom-metrics"}
        custom_headers = {
            "idempotency_header": "Custom-Idempotency-Key",
            "cache_hit_header": "Custom-Cache-Hit",
            "idempotency_response_header": "Custom-Idempotency-Response",
        }
        
        app.add_middleware(
            BackgroundOperationsMiddleware,
            manager=manager,
            exempt_paths=custom_exempt_paths,
            **custom_headers
        )
        
        @app.post("/api/test")
        async def test_endpoint(request: Request):
            if is_idempotent_request(request):
                key = get_idempotency_key(request)
                result = {"key": key, "processed": True}
                set_operation_result(request, result)
                return result
            return {"processed": False}
        
        client = TestClient(app)
        
        # Test custom headers
        headers = {"Custom-Idempotency-Key": "custom-key-123"}
        response = client.post("/api/test", headers=headers)
        
        assert response.status_code == 200
        assert response.headers["Custom-Idempotency-Response"] == "custom-key-123"
        
        data = response.json()
        assert data["key"] == "custom-key-123"
        assert data["processed"] is True

    def test_middleware_handles_exceptions_gracefully(self, manager):
        """Test middleware handles exceptions without breaking request flow."""
        app = FastAPI()
        
        # Create middleware with storage that will fail
        class FailingStorage:
            async def get_idempotency(self, key):
                raise RuntimeError("Storage connection failed")
            
            async def set_idempotency(self, key, mapping, ttl):
                raise RuntimeError("Storage connection failed")
        
        # Replace storage temporarily to cause failures
        original_storage = manager.storage
        manager.storage = FailingStorage()
        
        app.add_middleware(
            BackgroundOperationsMiddleware,
            manager=manager
        )
        
        @app.post("/api/test")
        async def test_endpoint(request: Request):
            return {"status": "ok"}
        
        try:
            client = TestClient(app)
            
            # Request should still work despite storage failure
            headers = {"Idempotency-Key": "failing-key-123"}
            response = client.post("/api/test", headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
        
        finally:
            # Restore original storage
            manager.storage = original_storage

    def test_tenant_id_extraction(self, manager):
        """Test tenant ID extraction from requests."""
        app = FastAPI()
        
        app.add_middleware(
            BackgroundOperationsMiddleware,
            manager=manager
        )
        
        @app.post("/api/tenant/{tenant_id}/action")
        async def tenant_action(tenant_id: str, request: Request):
            # The middleware should extract tenant_id from path
            return {"tenant_id": tenant_id, "processed": True}
        
        @app.post("/api/action")
        async def global_action(request: Request):
            # Should use default tenant
            return {"processed": True}
        
        client = TestClient(app)
        
        # Test with tenant in path
        headers = {"Idempotency-Key": "tenant-key-123"}
        response = client.post("/api/tenant/tenant123/action", headers=headers)
        
        assert response.status_code == 200
        assert response.headers["X-Idempotency-Key"] == "tenant-key-123"

    def test_user_id_extraction(self, manager):
        """Test user ID extraction from requests."""
        app = FastAPI()
        
        app.add_middleware(
            BackgroundOperationsMiddleware,
            manager=manager
        )
        
        @app.post("/api/user-action")
        async def user_action(request: Request):
            return {"processed": True}
        
        client = TestClient(app)
        
        # Test with user ID in headers
        headers = {
            "Idempotency-Key": "user-key-123",
            "X-User-ID": "user456"
        }
        response = client.post("/api/user-action", headers=headers)
        
        assert response.status_code == 200
        assert response.headers["X-Idempotency-Key"] == "user-key-123"

    def test_concurrent_requests_same_key(self, app_with_middleware):
        """Test concurrent requests with same idempotency key.""" 
        import threading
        import time
        
        client = TestClient(app_with_middleware)
        results = []
        
        def make_request():
            headers = {"Idempotency-Key": "concurrent-key-123"}
            response = client.post("/api/send-email", headers=headers)
            results.append({
                "status_code": response.status_code,
                "data": response.json(),
                "headers": dict(response.headers)
            })
        
        # Start multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all requests to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(results) == 5
        for result in results:
            assert result["status_code"] in [200, 202]  # Either processed or in-progress
            assert result["headers"]["x-idempotency-key"] == "concurrent-key-123"