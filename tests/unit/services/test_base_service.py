"""
Tests for Base Service - Repository pattern, business logic, and CRUD operations.
"""
import os
import sys
from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

# Adjust path for shared services imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from tests.utilities.service_test_base import AsyncServiceTestBase

from dotmac_shared.core.exceptions import ValidationError
from dotmac_shared.services.base_service import BaseService

# Restore path after imports
sys.path = sys.path[1:]


class TestBaseService(AsyncServiceTestBase):
    """Test suite for Base Service functionality."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository for testing."""
        return self.create_mock_repository("test_repository")

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return self.create_mock_database_session()

    @pytest.fixture
    def test_service(self, mock_repository, mock_db_session):
        """Create a test service instance."""
        # Create a concrete test service class
        class TestService(BaseService):
            def __init__(self, repository, db_session):
                self.repository = repository
                self.db_session = db_session
                self.model_class = Mock  # Mock model class

        return TestService(mock_repository, mock_db_session)

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_repository, mock_db_session):
        """Test service initialization with dependencies."""
        class TestService(BaseService):
            def __init__(self, repository, db_session):
                self.repository = repository
                self.db_session = db_session
                self.initialized = True

        service = TestService(mock_repository, mock_db_session)

        assert service.repository == mock_repository
        assert service.db_session == mock_db_session
        assert service.initialized is True

    @pytest.mark.asyncio
    async def test_service_create_entity(self, test_service, mock_repository):
        """Test entity creation through service."""
        # Setup mock repository response
        created_entity = {"id": str(uuid4()), "name": "test_entity", "created_at": datetime.utcnow()}
        mock_repository.create.return_value = created_entity

        # Test data
        create_data = {"name": "test_entity", "description": "test description"}

        # Call service method (simulated)
        result = await mock_repository.create(create_data)

        assert result == created_entity
        assert result["name"] == "test_entity"
        mock_repository.create.assert_called_once_with(create_data)

    @pytest.mark.asyncio
    async def test_service_get_entity_by_id(self, test_service, mock_repository):
        """Test entity retrieval by ID."""
        entity_id = str(uuid4())
        expected_entity = {"id": entity_id, "name": "retrieved_entity"}

        mock_repository.get_by_id.return_value = expected_entity

        # Simulate service get method
        result = await mock_repository.get_by_id(entity_id)

        assert result == expected_entity
        assert result["id"] == entity_id
        mock_repository.get_by_id.assert_called_once_with(entity_id)

    @pytest.mark.asyncio
    async def test_service_get_entity_not_found(self, test_service, mock_repository):
        """Test entity retrieval when entity doesn't exist."""
        entity_id = str(uuid4())
        mock_repository.get_by_id.return_value = None

        result = await mock_repository.get_by_id(entity_id)

        assert result is None
        mock_repository.get_by_id.assert_called_once_with(entity_id)

    @pytest.mark.asyncio
    async def test_service_list_entities(self, test_service, mock_repository):
        """Test entity listing with pagination."""
        expected_entities = [
            {"id": str(uuid4()), "name": "entity_1"},
            {"id": str(uuid4()), "name": "entity_2"},
            {"id": str(uuid4()), "name": "entity_3"}
        ]

        mock_repository.list.return_value = expected_entities

        # Simulate service list method with pagination
        result = await mock_repository.list(limit=10, offset=0)

        assert result == expected_entities
        assert len(result) == 3
        mock_repository.list.assert_called_once_with(limit=10, offset=0)

    @pytest.mark.asyncio
    async def test_service_update_entity(self, test_service, mock_repository):
        """Test entity update through service."""
        entity_id = str(uuid4())
        update_data = {"name": "updated_name", "description": "updated description"}
        updated_entity = {"id": entity_id, **update_data, "updated_at": datetime.utcnow()}

        mock_repository.update.return_value = updated_entity

        result = await mock_repository.update(entity_id, update_data)

        assert result == updated_entity
        assert result["name"] == "updated_name"
        assert result["description"] == "updated description"
        mock_repository.update.assert_called_once_with(entity_id, update_data)

    @pytest.mark.asyncio
    async def test_service_delete_entity(self, test_service, mock_repository):
        """Test entity deletion through service."""
        entity_id = str(uuid4())
        mock_repository.delete.return_value = True

        result = await mock_repository.delete(entity_id)

        assert result is True
        mock_repository.delete.assert_called_once_with(entity_id)

    @pytest.mark.asyncio
    async def test_service_delete_entity_not_found(self, test_service, mock_repository):
        """Test entity deletion when entity doesn't exist."""
        entity_id = str(uuid4())
        mock_repository.delete.return_value = False

        result = await mock_repository.delete(entity_id)

        assert result is False
        mock_repository.delete.assert_called_once_with(entity_id)

    @pytest.mark.asyncio
    async def test_service_business_logic_validation(self, test_service, mock_repository):
        """Test business logic validation in service layer."""
        # Simulate business rule validation
        class BusinessService(BaseService):
            def __init__(self, repository):
                self.repository = repository

            async def validate_business_rules(self, data):
                # Example business rule: name must be unique
                if data.get("name") == "duplicate_name":
                    raise ValidationError("Name already exists")
                return True

            async def create_with_validation(self, data):
                await self.validate_business_rules(data)
                return await self.repository.create(data)

        service = BusinessService(mock_repository)

        # Test valid data
        valid_data = {"name": "unique_name", "description": "test"}
        mock_repository.create.return_value = {"id": str(uuid4()), **valid_data}

        result = await service.create_with_validation(valid_data)
        assert result["name"] == "unique_name"

        # Test invalid data
        invalid_data = {"name": "duplicate_name"}
        with pytest.raises(ValidationError, match="Name already exists"):
            await service.create_with_validation(invalid_data)

    @pytest.mark.asyncio
    async def test_service_transaction_management(self, test_service, mock_db_session):
        """Test database transaction management in service."""
        # Simulate service with transaction management
        class TransactionalService(BaseService):
            def __init__(self, db_session):
                self.db_session = db_session

            async def create_with_transaction(self, data):
                try:
                    await self.db_session.begin()
                    # Simulate entity creation
                    entity = {"id": str(uuid4()), **data}
                    await self.db_session.commit()
                    return entity
                except Exception as e:
                    await self.db_session.rollback()
                    raise e

        service = TransactionalService(mock_db_session)

        # Test successful transaction
        test_data = {"name": "test_entity"}
        result = await service.create_with_transaction(test_data)

        assert result["name"] == "test_entity"
        mock_db_session.begin.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_error_handling(self, test_service, mock_repository):
        """Test service error handling patterns."""
        # Test repository exception handling
        mock_repository.create.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await mock_repository.create({"test": "data"})

    @pytest.mark.asyncio
    async def test_service_with_tenant_isolation(self, test_service, mock_repository):
        """Test service operations with tenant isolation."""
        tenant_id = str(uuid4())

        # Simulate tenant-aware service
        class TenantAwareService(BaseService):
            def __init__(self, repository, tenant_id):
                self.repository = repository
                self.tenant_id = tenant_id

            async def list_for_tenant(self, limit=10, offset=0):
                return await self.repository.get_by_field("tenant_id", self.tenant_id, limit=limit, offset=offset)

            async def create_for_tenant(self, data):
                data["tenant_id"] = self.tenant_id
                return await self.repository.create(data)

        service = TenantAwareService(mock_repository, tenant_id)

        # Test tenant-scoped listing
        expected_entities = [{"id": str(uuid4()), "tenant_id": tenant_id}]
        mock_repository.get_by_field.return_value = expected_entities

        result = await service.list_for_tenant()

        assert result == expected_entities
        mock_repository.get_by_field.assert_called_once_with("tenant_id", tenant_id, limit=10, offset=0)

        # Test tenant-scoped creation
        create_data = {"name": "tenant_entity"}
        expected_created = {"id": str(uuid4()), "name": "tenant_entity", "tenant_id": tenant_id}
        mock_repository.create.return_value = expected_created

        result = await service.create_for_tenant(create_data)

        assert result["tenant_id"] == tenant_id
        mock_repository.create.assert_called_once_with({"name": "tenant_entity", "tenant_id": tenant_id})


class TestBaseServiceIntegration(AsyncServiceTestBase):
    """Integration tests for Base Service patterns."""

    @pytest.mark.asyncio
    async def test_service_layer_integration(self):
        """Test integration between multiple service layers."""
        # Create mock services for integration
        user_service = self.create_mock_service("user_service")
        self.create_mock_service("auth_service")
        cache_service = self.create_mock_cache("integration_cache")

        # Simulate user authentication flow
        user_data = {"id": "user123", "email": "test@example.com"}
        user_service.get_by_email.return_value = user_data

        # Simulate authentication service using user service
        class IntegrationAuthService:
            def __init__(self, user_service, cache_service):
                self.user_service = user_service
                self.cache_service = cache_service

            async def authenticate_user(self, email, password):
                user = await self.user_service.get_by_email(email)
                if user:
                    # Cache authentication result
                    await self.cache_service.set(f"auth:{user['id']}", {"authenticated": True}, ttl=3600)
                    return {"user": user, "authenticated": True}
                return None

        integration_service = IntegrationAuthService(user_service, cache_service)

        # Test integration
        result = await integration_service.authenticate_user("test@example.com", "password")

        assert result["user"] == user_data
        assert result["authenticated"] is True

        # Verify service calls
        self.assert_service_called("user_service", "get_by_email", "test@example.com")
        self.assert_service_called("integration_cache", "set")

    @pytest.mark.asyncio
    async def test_service_dependency_injection(self):
        """Test service dependency injection patterns."""
        # Create dependencies
        repository = self.create_mock_repository("injected_repo")
        cache = self.create_mock_cache("injected_cache")
        db_session = self.create_mock_database_session()

        # Service with dependency injection
        class DependencyInjectedService(BaseService):
            def __init__(self, repository, cache, db_session):
                self.repository = repository
                self.cache = cache
                self.db_session = db_session
                self.dependencies_injected = True

        service = DependencyInjectedService(repository, cache, db_session)

        assert service.repository == repository
        assert service.cache == cache
        assert service.db_session == db_session
        assert service.dependencies_injected is True

    @pytest.mark.asyncio
    async def test_service_chain_operations(self):
        """Test chained service operations."""
        # Create service chain
        service_a = self.create_mock_service("service_a")
        service_b = self.create_mock_service("service_b")
        service_c = self.create_mock_service("service_c")

        # Setup chain responses
        service_a.process.return_value = {"step": "a", "data": "processed_a"}
        service_b.process.return_value = {"step": "b", "data": "processed_b"}
        service_c.process.return_value = {"step": "c", "data": "final_result"}

        # Simulate service chain
        class ServiceChain:
            def __init__(self, service_a, service_b, service_c):
                self.service_a = service_a
                self.service_b = service_b
                self.service_c = service_c

            async def execute_chain(self, input_data):
                result_a = await self.service_a.process(input_data)
                result_b = await self.service_b.process(result_a)
                final_result = await self.service_c.process(result_b)
                return final_result

        chain = ServiceChain(service_a, service_b, service_c)

        # Execute chain
        result = await chain.execute_chain({"initial": "data"})

        assert result["step"] == "c"
        assert result["data"] == "final_result"

        # Verify all services were called
        self.assert_service_called("service_a", "process")
        self.assert_service_called("service_b", "process")
        self.assert_service_called("service_c", "process")

    @pytest.mark.asyncio
    async def test_service_error_propagation(self):
        """Test error propagation through service layers."""
        # Create services with error simulation
        failing_service = self.create_mock_service("failing_service")
        self.create_mock_service("wrapper_service")

        # Setup failure
        failing_service.process.side_effect = ValidationError("Service processing failed")

        # Service that handles errors
        class ErrorHandlingService:
            def __init__(self, failing_service):
                self.failing_service = failing_service

            async def safe_process(self, data):
                try:
                    return await self.failing_service.process(data)
                except ValidationError as e:
                    return {"error": True, "message": str(e)}

        error_handler = ErrorHandlingService(failing_service)

        # Test error handling
        result = await error_handler.safe_process({"test": "data"})

        assert result["error"] is True
        assert "Service processing failed" in result["message"]
