"""
Tests for RouterFactory with comprehensive coverage.
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import Any

from dotmac.application.api.router_factory import RouterFactory, ServiceProtocol
from dotmac.application.dependencies.dependencies import StandardDependencies, PaginatedDependencies


# Test schemas
class TestCreateSchema(BaseModel):
    name: str
    description: str | None = None


class TestUpdateSchema(BaseModel):
    name: str | None = None
    description: str | None = None


class TestResponseSchema(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_at: str | None = None


# Mock service implementation
class MockService:
    """Mock service implementing ServiceProtocol."""
    
    def __init__(self, db, tenant_id):
        self.db = db
        self.tenant_id = tenant_id
    
    async def create(self, data: TestCreateSchema, user_id: Any) -> TestResponseSchema:
        return TestResponseSchema(
            id=str(uuid4()),
            name=data.name,
            description=data.description,
            created_at="2023-01-01T00:00:00Z"
        )
    
    async def list(self, skip: int, limit: int, user_id: Any) -> list[TestResponseSchema]:
        return [
            TestResponseSchema(
                id=str(uuid4()),
                name=f"Item {i}",
                description=f"Description {i}",
                created_at="2023-01-01T00:00:00Z"
            )
            for i in range(skip, skip + limit)
        ]
    
    async def count(self, user_id: Any) -> int:
        return 100
    
    async def get_by_id(self, entity_id: str, user_id: Any) -> TestResponseSchema:
        return TestResponseSchema(
            id=entity_id,
            name="Test Item",
            description="Test Description",
            created_at="2023-01-01T00:00:00Z"
        )
    
    async def update(self, entity_id: str, data: TestUpdateSchema, user_id: Any) -> TestResponseSchema:
        return TestResponseSchema(
            id=entity_id,
            name=data.name or "Updated Item",
            description=data.description,
            created_at="2023-01-01T00:00:00Z"
        )
    
    async def delete(self, entity_id: str, user_id: Any, soft_delete: bool = True) -> None:
        pass
    
    async def bulk_create(self, data: list[TestCreateSchema], user_id: Any) -> list[TestResponseSchema]:
        return [
            TestResponseSchema(
                id=str(uuid4()),
                name=item.name,
                description=item.description,
                created_at="2023-01-01T00:00:00Z"
            )
            for item in data
        ]
    
    async def bulk_update(self, updates: dict[str, TestUpdateSchema], user_id: Any) -> None:
        pass
    
    async def bulk_delete(self, entity_ids: list[str], user_id: Any, soft_delete: bool = True) -> None:
        pass


@pytest.fixture
def mock_dependencies():
    """Mock dependencies for testing."""
    mock_user = {
        "user_id": 1,
        "email": "test@example.com",
        "is_active": True,
        "is_admin": False
    }
    
    mock_db = Mock()
    mock_tenant_id = "test_tenant"
    
    return StandardDependencies(mock_user, mock_db, mock_tenant_id)


@pytest.fixture
def mock_paginated_dependencies():
    """Mock paginated dependencies for testing."""
    from dotmac.application.dependencies.dependencies import PaginationParams
    
    mock_user = {
        "user_id": 1,
        "email": "test@example.com",
        "is_active": True,
        "is_admin": False
    }
    
    mock_db = Mock()
    mock_tenant_id = "test_tenant"
    mock_pagination = PaginationParams(page=1, size=20)
    
    return PaginatedDependencies(mock_user, mock_db, mock_pagination, mock_tenant_id)


class TestRouterFactory:
    """Test RouterFactory functionality."""
    
    def test_create_crud_router(self, mock_dependencies, mock_paginated_dependencies):
        """Test CRUD router creation."""
        router = RouterFactory.create_crud_router(
            service_class=MockService,
            create_schema=TestCreateSchema,
            update_schema=TestUpdateSchema,
            response_schema=TestResponseSchema,
            prefix="/test",
            tags=["test"],
        )
        
        assert router.prefix == "/test"
        assert router.tags == ["test"]
        
        # Check that routes were created
        route_paths = [route.path for route in router.routes]
        expected_paths = [
            "/test/",  # POST create
            "/test/",  # GET list
            "/test/{entity_id}",  # GET single
            "/test/{entity_id}",  # PUT update
            "/test/{entity_id}",  # DELETE
        ]
        
        for expected_path in expected_paths:
            assert expected_path in route_paths
    
    def test_create_crud_router_with_bulk_operations(self):
        """Test CRUD router with bulk operations enabled."""
        router = RouterFactory.create_crud_router(
            service_class=MockService,
            create_schema=TestCreateSchema,
            update_schema=TestUpdateSchema,
            response_schema=TestResponseSchema,
            prefix="/test",
            enable_bulk_operations=True,
        )
        
        route_paths = [route.path for route in router.routes]
        bulk_paths = [
            "/test/bulk",  # POST bulk create
            "/test/bulk",  # PUT bulk update
            "/test/bulk",  # DELETE bulk delete
        ]
        
        for bulk_path in bulk_paths:
            assert bulk_path in route_paths
    
    def test_create_readonly_router(self):
        """Test read-only router creation."""
        router = RouterFactory.create_readonly_router(
            service_class=MockService,
            response_schema=TestResponseSchema,
            prefix="/readonly",
            tags=["readonly"],
        )
        
        assert router.prefix == "/readonly"
        assert router.tags == ["readonly"]
        
        route_paths = [route.path for route in router.routes]
        expected_paths = [
            "/readonly/",  # GET list
            "/readonly/{entity_id}",  # GET single
        ]
        
        for expected_path in expected_paths:
            assert expected_path in route_paths
        
        # Should not have write operations
        write_paths = [
            "/readonly/",  # POST
            "/readonly/{entity_id}",  # PUT/DELETE would be separate routes
        ]
        route_methods = [(route.path, route.methods) for route in router.routes]
        
        # Check that only GET methods exist
        for path, methods in route_methods:
            if path == "/readonly/":
                assert "GET" in methods
                assert "POST" not in methods
    
    def test_create_standard_router(self):
        """Test standard router creation."""
        router = RouterFactory.create_standard_router(
            prefix="/custom",
            tags=["custom"]
        )
        
        assert router.prefix == "/custom"
        assert router.tags == ["custom"]
        assert len(router.routes) == 0  # No predefined routes


class TestServiceProtocol:
    """Test ServiceProtocol compliance."""
    
    def test_mock_service_implements_protocol(self):
        """Test that MockService implements ServiceProtocol."""
        # This is a type check that would be validated by mypy
        service = MockService(Mock(), "tenant")
        assert isinstance(service, ServiceProtocol)
    
    @pytest.mark.asyncio
    async def test_service_protocol_methods(self):
        """Test all ServiceProtocol methods."""
        service = MockService(Mock(), "test_tenant")
        
        # Test create
        create_data = TestCreateSchema(name="Test", description="Test Desc")
        result = await service.create(create_data, "user1")
        assert result.name == "Test"
        
        # Test list
        items = await service.list(0, 10, "user1")
        assert len(items) == 10
        
        # Test count
        count = await service.count("user1")
        assert count == 100
        
        # Test get_by_id
        entity_id = str(uuid4())
        item = await service.get_by_id(entity_id, "user1")
        assert item.id == entity_id
        
        # Test update
        update_data = TestUpdateSchema(name="Updated")
        updated = await service.update(entity_id, update_data, "user1")
        assert updated.name == "Updated"
        
        # Test delete (should not raise)
        await service.delete(entity_id, "user1")
        
        # Test bulk operations
        bulk_data = [TestCreateSchema(name=f"Bulk {i}") for i in range(3)]
        bulk_results = await service.bulk_create(bulk_data, "user1")
        assert len(bulk_results) == 3
        
        updates = {str(uuid4()): TestUpdateSchema(name="Bulk Updated")}
        await service.bulk_update(updates, "user1")
        
        entity_ids = [str(uuid4()) for _ in range(3)]
        await service.bulk_delete(entity_ids, "user1")


class TestIntegrationWithFastAPI:
    """Test integration with FastAPI application."""
    
    def test_router_integration(self, mock_dependencies, monkeypatch):
        """Test router integration with FastAPI."""
        # Mock the dependency functions
        async def mock_get_standard_deps():
            return mock_dependencies
        
        async def mock_get_paginated_deps():
            from dotmac.application.dependencies.dependencies import PaginationParams
            return PaginatedDependencies(
                mock_dependencies.current_user,
                mock_dependencies.db,
                PaginationParams(page=1, size=20),
                mock_dependencies.tenant_id
            )
        
        # Patch the dependency functions
        monkeypatch.setattr(
            "dotmac.application.dependencies.dependencies.get_standard_deps",
            mock_get_standard_deps
        )
        monkeypatch.setattr(
            "dotmac.application.dependencies.dependencies.get_paginated_deps", 
            mock_get_paginated_deps
        )
        
        # Create router
        router = RouterFactory.create_crud_router(
            service_class=MockService,
            create_schema=TestCreateSchema,
            update_schema=TestUpdateSchema,
            response_schema=TestResponseSchema,
            prefix="/api/test",
            tags=["test"],
        )
        
        # Create FastAPI app and include router
        app = FastAPI()
        app.include_router(router)
        
        # Test with client
        client = TestClient(app)
        
        # Test create endpoint
        response = client.post("/api/test/", json={
            "name": "Test Item",
            "description": "Test Description"
        })
        assert response.status_code == 201
        assert response.json()["name"] == "Test Item"
        
        # Test list endpoint
        response = client.get("/api/test/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data


if __name__ == "__main__":
    pytest.main([__file__])