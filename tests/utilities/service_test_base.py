"""
Service Testing Base Classes and Utilities.

Provides common patterns for testing services with mocking, fixtures, and async support.
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Optional
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

# Adjust path for platform services imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/dotmac-platform-services/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/dotmac-core/src'))

# Restore path after imports
sys.path = sys.path[2:]


class ServiceTestBase:
    """Base class for service testing with common utilities and mocks."""

    @pytest.fixture(autouse=True)
    def setup_service_test(self):
        """Setup that runs before each service test."""
        self.service_mocks = {}
        self.repository_mocks = {}
        self.external_mocks = {}

    def create_mock_repository(self, name: str) -> AsyncMock:
        """Create a mock repository with standard CRUD operations."""
        mock_repo = AsyncMock()

        # Standard CRUD operations
        mock_repo.create = AsyncMock(return_value={"id": f"mock_{name}_id", "created": True})
        mock_repo.get_by_id = AsyncMock(return_value={"id": f"mock_{name}_id", "name": f"mock_{name}"})
        mock_repo.get_by_field = AsyncMock(return_value=[])
        mock_repo.list = AsyncMock(return_value=[])
        mock_repo.update = AsyncMock(return_value={"id": f"mock_{name}_id", "updated": True})
        mock_repo.delete = AsyncMock(return_value=True)
        mock_repo.count = AsyncMock(return_value=0)
        mock_repo.exists = AsyncMock(return_value=False)

        # Database transaction operations
        mock_repo.begin_transaction = AsyncMock()
        mock_repo.commit_transaction = AsyncMock()
        mock_repo.rollback_transaction = AsyncMock()

        self.repository_mocks[name] = mock_repo
        return mock_repo

    def create_mock_service(self, name: str, service_class: Optional[type] = None) -> AsyncMock:
        """Create a mock service with common business operations."""
        mock_service = AsyncMock()

        # Standard business operations
        mock_service.create = AsyncMock(return_value={"id": f"mock_{name}_service_id", "created": True})
        mock_service.get = AsyncMock(return_value={"id": f"mock_{name}_service_id", "name": f"mock_{name}"})
        mock_service.list = AsyncMock(return_value=[])
        mock_service.update = AsyncMock(return_value={"id": f"mock_{name}_service_id", "updated": True})
        mock_service.delete = AsyncMock(return_value=True)
        mock_service.validate = AsyncMock(return_value=True)

        # Service-specific operations
        mock_service.process = AsyncMock(return_value={"processed": True})
        mock_service.execute = AsyncMock(return_value={"executed": True})
        mock_service.calculate = AsyncMock(return_value={"result": 0})

        if service_class:
            mock_service.spec = service_class

        self.service_mocks[name] = mock_service
        return mock_service

    def create_mock_cache(self, name: str = "cache") -> AsyncMock:
        """Create a mock cache service."""
        mock_cache = AsyncMock()

        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        mock_cache.delete = AsyncMock(return_value=True)
        mock_cache.exists = AsyncMock(return_value=False)
        mock_cache.clear = AsyncMock(return_value=True)
        mock_cache.initialize = AsyncMock(return_value=None)

        # Cache-specific operations
        mock_cache.get_or_set = AsyncMock(return_value={"cached": True})
        mock_cache.invalidate_pattern = AsyncMock(return_value=True)
        mock_cache.get_ttl = AsyncMock(return_value=300)

        self.external_mocks[name] = mock_cache
        return mock_cache

    def create_mock_database_session(self) -> AsyncMock:
        """Create a mock database session."""
        mock_session = AsyncMock()

        # Session operations
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.begin = AsyncMock()

        # Query operations
        mock_session.query = Mock(return_value=Mock())
        mock_session.add = Mock()
        mock_session.merge = AsyncMock()
        mock_session.delete = AsyncMock()
        mock_session.refresh = AsyncMock()

        self.external_mocks["db_session"] = mock_session
        return mock_session

    def create_mock_jwt_service(self) -> AsyncMock:
        """Create a mock JWT service for authentication testing."""
        mock_jwt = AsyncMock()

        # Token generation
        mock_jwt.create_access_token = AsyncMock(return_value="mock.access.token")
        mock_jwt.create_refresh_token = AsyncMock(return_value="mock.refresh.token")
        mock_jwt.create_token_pair = AsyncMock(return_value={
            "access_token": "mock.access.token",
            "refresh_token": "mock.refresh.token",
            "token_type": "bearer"
        })

        # Token validation
        mock_jwt.verify_token = AsyncMock(return_value={
            "sub": "user123",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "valid": True
        })
        mock_jwt.decode_token = AsyncMock(return_value={
            "sub": "user123",
            "aud": "dotmac",
            "iss": "dotmac-auth"
        })

        # Token refresh
        mock_jwt.refresh_access_token = AsyncMock(return_value="new.access.token")
        mock_jwt.revoke_token = AsyncMock(return_value=True)

        self.external_mocks["jwt_service"] = mock_jwt
        return mock_jwt

    def create_service_fixture(self, service_class: type, **dependencies) -> Any:
        """Create a service instance with mocked dependencies."""
        # Create mocks for any dependencies not provided
        default_deps = {
            "repository": self.create_mock_repository("default"),
            "cache": self.create_mock_cache(),
            "db_session": self.create_mock_database_session()
        }

        # Merge provided dependencies with defaults
        all_deps = {**default_deps, **dependencies}

        # Filter dependencies to match service constructor
        try:
            return service_class(**all_deps)
        except TypeError:
            # If constructor doesn't accept all deps, try with just the provided ones
            return service_class(**dependencies)

    def assert_repository_called(self, repo_name: str, method: str, *args, **kwargs):
        """Assert that a repository method was called with specific arguments."""
        if repo_name not in self.repository_mocks:
            pytest.fail(f"Repository '{repo_name}' was not mocked")

        repo = self.repository_mocks[repo_name]
        method_mock = getattr(repo, method)

        if args or kwargs:
            method_mock.assert_called_with(*args, **kwargs)
        else:
            method_mock.assert_called()

    def assert_service_called(self, service_name: str, method: str, *args, **kwargs):
        """Assert that a service method was called with specific arguments."""
        if service_name not in self.service_mocks:
            pytest.fail(f"Service '{service_name}' was not mocked")

        service = self.service_mocks[service_name]
        method_mock = getattr(service, method)

        if args or kwargs:
            method_mock.assert_called_with(*args, **kwargs)
        else:
            method_mock.assert_called()

    def create_test_data(self, data_type: str, **overrides) -> dict[str, Any]:
        """Create common test data structures."""
        test_data = {
            "user": {
                "id": str(uuid4()),
                "email": "test@example.com",
                "username": "testuser",
                "is_active": True,
                "created_at": datetime.utcnow(),
                **overrides
            },
            "tenant": {
                "tenant_id": str(uuid4()),
                "tenant_name": "Test Tenant",
                "domain": "test.example.com",
                "is_active": True,
                **overrides
            },
            "auth_token": {
                "token": "mock.jwt.token",
                "token_type": "bearer",
                "expires_in": 3600,
                "refresh_token": "mock.refresh.token",
                **overrides
            },
            "cache_entry": {
                "key": "test_key",
                "value": {"data": "test_value"},
                "ttl": 300,
                **overrides
            }
        }

        return test_data.get(data_type, overrides)


class AsyncServiceTestBase(ServiceTestBase):
    """Extended base class for async service testing."""

    @pytest.fixture
    def event_loop(self):
        """Provide event loop for async tests."""
        import asyncio
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    async def setup_async_service_test(self):
        """Async setup for service tests."""
        # Initialize any async mocks
        for mock in self.external_mocks.values():
            if hasattr(mock, 'initialize'):
                await mock.initialize()

    async def teardown_async_service_test(self):
        """Async teardown for service tests."""
        # Clean up async resources
        for mock in self.external_mocks.values():
            if hasattr(mock, 'close'):
                await mock.close()


class ServiceIntegrationTestBase(AsyncServiceTestBase):
    """Base class for service integration testing."""

    def create_integration_environment(self) -> dict[str, Any]:
        """Create a controlled integration test environment."""
        return {
            "database": self.create_mock_database_session(),
            "cache": self.create_mock_cache("integration_cache"),
            "message_queue": self.create_mock_message_queue(),
            "external_api": self.create_mock_external_api()
        }

    def create_mock_message_queue(self) -> AsyncMock:
        """Create a mock message queue for integration testing."""
        mock_mq = AsyncMock()

        mock_mq.publish = AsyncMock(return_value=True)
        mock_mq.subscribe = AsyncMock()
        mock_mq.consume = AsyncMock(return_value=[])
        mock_mq.acknowledge = AsyncMock(return_value=True)
        mock_mq.reject = AsyncMock(return_value=True)

        self.external_mocks["message_queue"] = mock_mq
        return mock_mq

    def create_mock_external_api(self) -> AsyncMock:
        """Create a mock external API client."""
        mock_api = AsyncMock()

        mock_api.get = AsyncMock(return_value={"status": "success", "data": {}})
        mock_api.post = AsyncMock(return_value={"status": "created", "id": str(uuid4())})
        mock_api.put = AsyncMock(return_value={"status": "updated"})
        mock_api.delete = AsyncMock(return_value={"status": "deleted"})

        self.external_mocks["external_api"] = mock_api
        return mock_api
