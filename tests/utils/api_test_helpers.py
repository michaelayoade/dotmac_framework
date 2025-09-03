"""
Test utilities and helpers for DotMac Framework API testing.
Provides common fixtures, mock factories, and testing utilities.
"""

import asyncio
import json
import jwt
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


class MockAuthService:
    """Mock authentication service for testing."""
    
    def __init__(self, tenant_id: str = "test-tenant-123"):
        self.tenant_id = tenant_id
        self.users = {}
        self.sessions = {}
        self.failed_attempts = {}
    
    async def authenticate_user(self, username: str, password: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Mock user authentication."""
        if username == "testuser" and password == "password":
            user_id = f"user-{username}"
            return {
                "access_token": self.create_test_token(user_id, username),
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": f"{username}@example.com",
                    "tenant_id": self.tenant_id
                }
            }
        return None
    
    async def logout_user(self, session_id: str, user_id: str) -> bool:
        """Mock user logout."""
        if session_id in self.sessions:
            del self.sessions[session_id]
        return True
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Mock token refresh."""
        return {
            "access_token": "refreshed_access_token",
            "expires_in": 3600
        }
    
    def create_test_token(self, user_id: str, username: str) -> str:
        """Create a test JWT token."""
        payload = {
            "sub": user_id,
            "username": username,
            "tenant_id": self.tenant_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        return jwt.encode(payload, "test-secret", algorithm="HS256")


class MockCustomerService:
    """Mock customer service for testing."""
    
    def __init__(self, tenant_id: str = "test-tenant-123"):
        self.tenant_id = tenant_id
        self.customers = {}
        self._init_test_data()
    
    def _init_test_data(self):
        """Initialize test customer data."""
        test_customers = [
            {
                "id": "customer-123",
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1234567890",
                "company_name": "Doe Industries",
                "status": "active",
                "tenant_id": self.tenant_id,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "customer-456",
                "email": "jane.smith@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "phone": "+0987654321",
                "status": "active",
                "tenant_id": self.tenant_id,
                "created_at": "2024-01-02T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z"
            }
        ]
        
        for customer in test_customers:
            self.customers[customer["id"]] = customer
    
    async def create_customer(self, customer_data: Dict[str, Any], created_by: str = None) -> Dict[str, Any]:
        """Mock customer creation."""
        customer_id = f"customer-{uuid4()}"
        customer = {
            "id": customer_id,
            "tenant_id": self.tenant_id,
            "created_at": datetime.now(timezone.utc).isoformat() + "Z",
            "updated_at": datetime.now(timezone.utc).isoformat() + "Z",
            **customer_data
        }
        self.customers[customer_id] = customer
        return customer
    
    async def get_customer_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Mock customer retrieval by ID."""
        return self.customers.get(customer_id)
    
    async def get_customers_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Mock customer retrieval by status."""
        return [c for c in self.customers.values() if c.get("status") == status]
    
    async def search_customers(self, search_term: str) -> List[Dict[str, Any]]:
        """Mock customer search."""
        results = []
        for customer in self.customers.values():
            if (search_term.lower() in customer.get("first_name", "").lower() or
                search_term.lower() in customer.get("last_name", "").lower() or
                search_term.lower() in customer.get("email", "").lower()):
                results.append(customer)
        return results


class MockServicesService:
    """Mock services service for testing."""
    
    def __init__(self, tenant_id: str = "test-tenant-123"):
        self.tenant_id = tenant_id
        self.service_plans = {}
        self.service_instances = {}
        self.usage_data = {}
        self._init_test_data()
    
    def _init_test_data(self):
        """Initialize test service data."""
        test_plans = [
            {
                "id": "plan-123",
                "name": "Premium Internet",
                "description": "High-speed internet with unlimited data",
                "service_type": "internet",
                "speed_down": 1000,
                "speed_up": 100,
                "data_limit": None,
                "price": 99.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "is_active": True,
                "is_public": True,
                "tenant_id": self.tenant_id,
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "plan-456",
                "name": "Basic Internet",
                "description": "Standard internet service",
                "service_type": "internet",
                "speed_down": 100,
                "speed_up": 10,
                "price": 29.99,
                "currency": "USD",
                "is_active": True,
                "is_public": True,
                "tenant_id": self.tenant_id,
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
        
        for plan in test_plans:
            self.service_plans[plan["id"]] = plan
    
    async def create_service_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock service plan creation."""
        plan_id = f"plan-{uuid4()}"
        plan = {
            "id": plan_id,
            "tenant_id": self.tenant_id,
            "created_at": datetime.now(timezone.utc).isoformat() + "Z",
            **plan_data
        }
        self.service_plans[plan_id] = plan
        return plan
    
    async def get_service_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Mock service plan retrieval."""
        return self.service_plans.get(plan_id)
    
    async def list_service_plans(self, filters: Dict[str, Any] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Mock service plan listing."""
        plans = list(self.service_plans.values())
        
        if filters:
            for key, value in filters.items():
                plans = [p for p in plans if p.get(key) == value]
        
        return plans[offset:offset + limit]
    
    async def activate_service(self, activation_request: Dict[str, Any]) -> Dict[str, Any]:
        """Mock service activation."""
        service_id = f"service-{uuid4()}"
        service_instance = {
            "id": service_id,
            "service_number": f"SVC-{str(uuid4())[:8].upper()}",
            "customer_id": activation_request["customer_id"],
            "service_plan_id": activation_request["service_plan_id"],
            "status": "pending_installation",
            "tenant_id": self.tenant_id,
            "created_at": datetime.now(timezone.utc).isoformat() + "Z"
        }
        
        self.service_instances[service_id] = service_instance
        
        return {
            "service_instance": service_instance,
            "activation_id": f"activation-{uuid4()}",
            "status": "pending_installation"
        }
    
    async def get_service_instance(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Mock service instance retrieval."""
        return self.service_instances.get(service_id)


class TestDataFactory:
    """Factory for creating test data objects."""
    
    @staticmethod
    def create_customer_data(**overrides) -> Dict[str, Any]:
        """Create test customer data."""
        default_data = {
            "email": f"test.{uuid4()}@example.com",
            "first_name": "Test",
            "last_name": "Customer",
            "phone": "+1234567890",
            "company_name": "Test Company",
            "billing_address": {
                "street": "123 Test St",
                "city": "Test City",
                "state": "CA",
                "zip_code": "90210",
                "country": "USA"
            }
        }
        default_data.update(overrides)
        return default_data
    
    @staticmethod
    def create_service_plan_data(**overrides) -> Dict[str, Any]:
        """Create test service plan data."""
        default_data = {
            "name": f"Test Plan {uuid4()}",
            "description": "Test service plan",
            "service_type": "internet",
            "speed_down": 100,
            "speed_up": 10,
            "price": 49.99,
            "currency": "USD",
            "billing_cycle": "monthly",
            "is_active": True,
            "is_public": True
        }
        default_data.update(overrides)
        return default_data
    
    @staticmethod
    def create_user_data(**overrides) -> Dict[str, Any]:
        """Create test user data."""
        username = f"testuser{uuid4()}"
        default_data = {
            "username": username,
            "email": f"{username}@example.com",
            "first_name": "Test",
            "last_name": "User",
            "portal_type": "admin",
            "password_hash": "hashed_password",
            "is_active": True
        }
        default_data.update(overrides)
        return default_data
    
    @staticmethod
    def create_jwt_token(user_id: str = None, tenant_id: str = None, expired: bool = False) -> str:
        """Create test JWT token."""
        user_id = user_id or f"user-{uuid4()}"
        tenant_id = tenant_id or f"tenant-{uuid4()}"
        
        exp_time = datetime.now(timezone.utc)
        if expired:
            exp_time -= timedelta(hours=1)
        else:
            exp_time += timedelta(hours=1)
        
        payload = {
            "sub": user_id,
            "username": "testuser",
            "tenant_id": tenant_id,
            "exp": exp_time,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        
        return jwt.encode(payload, "test-secret", algorithm="HS256")


class APITestClient:
    """Enhanced test client with authentication helpers."""
    
    def __init__(self, client: TestClient, tenant_id: str = "test-tenant-123"):
        self.client = client
        self.tenant_id = tenant_id
        self._auth_token = None
    
    def authenticate(self, username: str = "testuser", password: str = "password") -> str:
        """Authenticate and return token."""
        login_data = {
            "username": username,
            "password": password,
            "portal_type": "admin"
        }
        
        response = self.client.post("/identity/auth/login", json=login_data)
        if response.status_code == 200:
            self._auth_token = response.json()["access_token"]
            return self._auth_token
        
        raise Exception(f"Authentication failed: {response.status_code}")
    
    def get_auth_headers(self, token: str = None) -> Dict[str, str]:
        """Get authentication headers."""
        token = token or self._auth_token
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": self.tenant_id
        }
        return headers
    
    def authenticated_get(self, url: str, **kwargs) -> Any:
        """Make authenticated GET request."""
        headers = kwargs.pop("headers", {})
        headers.update(self.get_auth_headers())
        return self.client.get(url, headers=headers, **kwargs)
    
    def authenticated_post(self, url: str, **kwargs) -> Any:
        """Make authenticated POST request."""
        headers = kwargs.pop("headers", {})
        headers.update(self.get_auth_headers())
        return self.client.post(url, headers=headers, **kwargs)
    
    def authenticated_put(self, url: str, **kwargs) -> Any:
        """Make authenticated PUT request."""
        headers = kwargs.pop("headers", {})
        headers.update(self.get_auth_headers())
        return self.client.put(url, headers=headers, **kwargs)
    
    def authenticated_patch(self, url: str, **kwargs) -> Any:
        """Make authenticated PATCH request."""
        headers = kwargs.pop("headers", {})
        headers.update(self.get_auth_headers())
        return self.client.patch(url, headers=headers, **kwargs)
    
    def authenticated_delete(self, url: str, **kwargs) -> Any:
        """Make authenticated DELETE request."""
        headers = kwargs.pop("headers", {})
        headers.update(self.get_auth_headers())
        return self.client.delete(url, headers=headers, **kwargs)


class DatabaseTestHelper:
    """Helper for database testing operations."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_test_tenant(self, tenant_id: str = None) -> str:
        """Create test tenant."""
        tenant_id = tenant_id or f"tenant-{uuid4()}"
        # In real implementation, would create tenant record
        return tenant_id
    
    def create_test_user(self, tenant_id: str, **overrides) -> Dict[str, Any]:
        """Create test user in database."""
        user_data = TestDataFactory.create_user_data(**overrides)
        user_data["tenant_id"] = tenant_id
        # In real implementation, would create user record
        return user_data
    
    def create_test_customer(self, tenant_id: str, **overrides) -> Dict[str, Any]:
        """Create test customer in database."""
        customer_data = TestDataFactory.create_customer_data(**overrides)
        customer_data["tenant_id"] = tenant_id
        # In real implementation, would create customer record
        return customer_data
    
    def cleanup_test_data(self, tenant_id: str):
        """Clean up test data for tenant."""
        # In real implementation, would delete test records
        pass


def assert_error_response(response: Any, expected_status: int, expected_message: str = None):
    """Assert that response is an error with expected details."""
    assert response.status_code == expected_status
    
    error_data = response.json()
    assert "detail" in error_data
    
    if expected_message:
        assert expected_message in error_data["detail"]


def assert_successful_response(response: Any, expected_fields: List[str] = None):
    """Assert that response is successful and contains expected fields."""
    assert 200 <= response.status_code < 300
    
    if expected_fields:
        data = response.json()
        for field in expected_fields:
            assert field in data


def create_mock_dependency(return_value: Any = None, side_effect: Any = None):
    """Create a mock dependency for FastAPI dependency injection."""
    mock = MagicMock()
    if return_value is not None:
        mock.return_value = return_value
    if side_effect is not None:
        mock.side_effect = side_effect
    return mock


# Export commonly used utilities
__all__ = [
    "MockAuthService",
    "MockCustomerService", 
    "MockServicesService",
    "TestDataFactory",
    "APITestClient",
    "DatabaseTestHelper",
    "assert_error_response",
    "assert_successful_response",
    "create_mock_dependency"
]