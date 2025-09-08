"""
Production-Ready Test Utilities and Helpers

This module provides comprehensive testing utilities that support the walkthrough
methodology for validating UI flows and ensuring production readiness.
"""

import asyncio
import json
import uuid
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import httpx
import pytest
from faker import Faker

# Framework imports
try:
    from dotmac.auth.current_user import get_current_user
    from dotmac_isp.core.settings import get_settings
    from dotmac_shared.database.session import get_async_db
except ImportError:
    # Handle missing imports gracefully for testing
    def get_async_db():
        return None
    def get_current_user():
        return None
    def get_settings():
        return None


fake = Faker()


class TestDataFactory:
    """Factory class for generating realistic test data."""

    @staticmethod
    def create_test_customer(
        tenant_id: str = "test_tenant_001",
        reseller_id: Optional[str] = None,
        **overrides,
    ) -> dict[str, Any]:
        """Create a complete test customer with realistic data."""

        base_data = {
            "customer_id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "email": fake.email(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "phone": fake.phone_number(),
            "date_of_birth": fake.date_of_birth(
                minimum_age=18, maximum_age=80
            ).isoformat(),
            # Address information
            "service_address": {
                "street": fake.street_address(),
                "city": fake.city(),
                "state": fake.state_abbr(),
                "zip_code": fake.zipcode(),
                "country": "US",
            },
            # Customer status and metadata
            "status": "active",
            "customer_type": "residential",
            "created_at": datetime.utcnow().isoformat(),
            # Customer preferences
            "preferences": {
                "billing_notifications": True,
                "service_notifications": True,
                "marketing_emails": fake.boolean(chance_of_getting_true=60),
                "preferred_contact_method": fake.random_element(
                    elements=["email", "phone", "sms"]
                ),
            },
            # Reseller information (if applicable)
            "reseller_info": (
                {
                    "reseller_id": reseller_id,
                    "commission_eligible": True if reseller_id else False,
                }
                if reseller_id
                else None
            ),
        }

        # Apply any overrides
        base_data.update(overrides)
        return base_data

    @staticmethod
    def create_test_service_plan(
        plan_type: str = "residential", **overrides
    ) -> dict[str, Any]:
        """Create a test service plan with realistic pricing."""

        plans = {
            "residential": {
                "plan_id": "res_100mbps",
                "name": "Residential 100Mbps",
                "download_speed": 100,
                "upload_speed": 10,
                "monthly_price": Decimal("59.99"),
            },
            "business": {
                "plan_id": "biz_500mbps",
                "name": "Business 500Mbps",
                "download_speed": 500,
                "upload_speed": 100,
                "monthly_price": Decimal("149.99"),
            },
        }

        base_plan = plans.get(plan_type, plans["residential"]).copy()
        base_plan.update(
            {
                "plan_type": plan_type,
                "setup_fee": Decimal("99.00"),
                "contract_length": 12,
                "active": True,
            }
        )

        base_plan.update(overrides)
        return base_plan

    @staticmethod
    def create_test_reseller(**overrides) -> dict[str, Any]:
        """Create a test reseller with territory and commission structure."""

        base_data = {
            "reseller_id": str(uuid.uuid4()),
            "company_name": fake.company(),
            "contact_email": fake.company_email(),
            "contact_phone": fake.phone_number(),
            # Territory information
            "territory": {
                "zip_codes": [fake.zipcode() for _ in range(5)],
                "cities": [fake.city() for _ in range(3)],
                "exclusive": True,
            },
            # Commission structure
            "commission": {
                "acquisition_rate": 100,  # dollars per customer
                "recurring_rate": 0.05,  # 5% of monthly revenue
                "payment_frequency": "monthly",
            },
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
        }

        base_data.update(overrides)
        return base_data


class APITestHelper:
    """Helper class for API testing operations."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def authenticate_user(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate a user and return auth token."""
        response = await self.client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError(f"Authentication failed: {response.text}")

    async def create_test_customer_via_api(
        self, customer_data: dict[str, Any], auth_token: str
    ) -> dict[str, Any]:
        """Create a customer via API."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await self.client.post(
            "/api/v1/customers", json=customer_data, headers=headers
        )
        if response.status_code == 201:
            return response.json()
        else:
            raise ValueError(f"Customer creation failed: {response.text}")

    async def generate_customer_activation_token(self, email: str) -> str:
        """Generate activation token for customer."""
        return f"activation_token_{email}_{uuid.uuid4()}"

    async def complete_customer_installation(self, email: str) -> dict[str, Any]:
        """Mark customer installation as complete."""
        return {"status": "completed", "email": email}

    async def trigger_billing_cycle(self, email: str) -> dict[str, Any]:
        """Trigger billing cycle for testing."""
        return {"status": "processed", "email": email}

    async def resolve_ticket(
        self, ticket_number: str, resolution: str
    ) -> dict[str, Any]:
        """Resolve a support ticket."""
        return {
            "ticket_number": ticket_number,
            "status": "resolved",
            "resolution": resolution,
        }

    async def simulate_payment_failure(self, email: str) -> dict[str, Any]:
        """Simulate payment failure for testing."""
        return {"status": "failed", "email": email, "reason": "insufficient_funds"}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


def create_mock_settings(**overrides) -> MagicMock:
    """Create mock settings with DotMac defaults."""
    mock_settings = MagicMock()

    # Default settings that match DotMac structure
    defaults = {
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://localhost:6379/15",
        "secret_key": "test-secret-key",
        "environment": "testing",
        "debug": False,
        "log_level": "WARNING",
    }

    # Apply overrides
    for key, value in overrides.items():
        defaults[key] = value

    # Set attributes on mock
    for key, value in defaults.items():
        setattr(mock_settings, key, value)

    return mock_settings


async def create_unified_test_client():
    """Create FastAPI test client using the unified factory."""
    from fastapi.testclient import TestClient

    from dotmac_shared.application.factory import create_isp_framework_app

    # Create app using the unified factory in development mode
    app = await create_isp_framework_app(tenant_config=None)  # None = development mode

    return TestClient(app)


def create_test_client():
    """
    DEPRECATED: Use create_unified_test_client() instead.

    This function creates a minimal FastAPI app for basic testing,
    but does not use the unified factory and misses middleware/health checks.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    # Create minimal FastAPI app for testing (DEPRECATED)
    app = FastAPI(title="DotMac Test App (Deprecated)")

    @app.get("/health")
    def health_check():
        return {"status": "healthy", "note": "deprecated test client"}

    return TestClient(app)


class MockRedisManager:
    """Mock Redis manager that behaves like the real one."""

    def __init__(self):
        self._data = {}
        self._connected = True

    def get(self, key: str) -> Optional[str]:
        return self._data.get(key)

    def set(self, key: str, value: str, ttl: int = None) -> bool:
        self._data[key] = value
        return True

    def delete(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    def ping(self) -> bool:
        return self._connected

    def clear(self):
        self._data.clear()


class MockDatabaseSession:
    """Mock database session for testing."""

    def __init__(self):
        self._objects = []
        self._committed = False

    def add(self, obj):
        self._objects.append(obj)

    def commit(self):
        self._committed = True

    def rollback(self):
        self._objects.clear()
        self._committed = False

    def query(self, model):
        return MockQuery()

    def close(self):
        pass


class MockQuery:
    """Mock database query for testing."""

    def __init__(self):
        self._results = []

    def filter(self, *args):
        return self

    def first(self):
        return self._results[0] if self._results else None

    def all(self):
        return self._results

    def count(self):
        return len(self._results)


def assert_valid_response(
    response, expected_status: int = 200, expected_keys: list = None
):
    """Assert response is valid with expected structure."""
    assert (
        response.status_code == expected_status
    ), f"Expected {expected_status}, got {response.status_code}: {response.text}"

    if expected_keys:
        response_data = response.json()
        for key in expected_keys:
            assert key in response_data, f"Expected key '{key}' not found in response"


def load_test_data(filename: str) -> dict[str, Any]:
    """Load test data from JSON file."""
    test_data_dir = Path(__file__).parent / "data"  # noqa: B008
    file_path = test_data_dir / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Test data file not found: {file_path}")

    with open(file_path) as f:
        return json.load(f)


async def wait_for_condition(
    condition: Callable[[], bool], timeout: float = 5.0
) -> bool:
    """Wait for a condition to become true, with timeout."""
    import time

    start_time = time.time()

    while time.time() - start_time < timeout:
        if condition():
            return True
        await asyncio.sleep(0.1)

    return False


def patch_dotmac_module(module_path: str, **patches):
    """Context manager to patch DotMac modules safely."""
    return patch.multiple(module_path, **patches)


def generate_test_auth_headers(user_id: str, roles: list[str] = None) -> dict[str, str]:
    """Generate test authentication headers."""
    if roles is None:
        roles = ["user"]

    # This would normally generate a proper JWT token
    token = f"test_token_{user_id}"
    return {"Authorization": f"Bearer {token}"}


def assert_decimal_equal(actual: Decimal, expected: Decimal, places: int = 2):
    """Assert that two decimal values are equal to specified precision."""
    actual_rounded = actual.quantize(Decimal("0.01"))
    expected_rounded = expected.quantize(Decimal("0.01"))
    assert (
        actual_rounded == expected_rounded
    ), f"Expected {expected_rounded}, got {actual_rounded}"


# Test Fixtures
@pytest.fixture
def test_data_factory():
    """Create a test data factory instance."""
    return TestDataFactory()


@pytest.fixture
async def api_helper():
    """Create an API test helper instance."""
    helper = APITestHelper()
    yield helper
    await helper.close()


# Export commonly used functions and classes
__all__ = [
    "TestDataFactory",
    "APITestHelper",
    "create_mock_settings",
    "create_test_client",
    "MockRedisManager",
    "MockDatabaseSession",
    "assert_valid_response",
    "wait_for_condition",
    "assert_decimal_equal",
    "generate_test_auth_headers",
]
