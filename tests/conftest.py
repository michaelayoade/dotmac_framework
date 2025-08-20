"""
Global test configuration for DotMac Framework.
Provides shared fixtures and utilities for all packages.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock

import pytest


# Test Database Configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/dotmac_test"
)
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_database():
    """Create test database for the session."""
    # Parse database URL to get connection params
    import urllib.parse

    import asyncpg
    parsed = urllib.parse.urlparse(TEST_DATABASE_URL)

    # Connect to postgres database to create test database
    conn = await asyncpg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database="postgres"
    )

    # Create test database
    test_db_name = parsed.path[1:]  # Remove leading slash
    await conn.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')
    await conn.execute(f'CREATE DATABASE "{test_db_name}"')
    await conn.close()

    yield TEST_DATABASE_URL

    # Cleanup: Drop test database
    conn = await asyncpg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database="postgres"
    )
    await conn.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')
    await conn.close()


@pytest.fixture
async def db_session(test_database):
    """Create database session for individual tests."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(test_database, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest.fixture
async def redis_client():
    """Create Redis client for testing."""
    import redis.asyncio as redis

    client = redis.from_url(TEST_REDIS_URL)

    # Clear test database
    await client.flushdb()

    yield client

    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config():
    """Create mock configuration for testing."""
    from dotmac_devtools.core.config import DevToolsConfig

    config = Mock(spec=DevToolsConfig)
    config.workspace_path = "/tmp/test_workspace"
    config.templates.custom_path = Path("/tmp/test_templates")
    config.defaults.author = "Test Author"
    config.defaults.license = "MIT"
    config.defaults.python_version = "3.11"
    config.defaults.docker_registry = "test.registry.com"
    config.generator.git_init = False
    config.generator.create_venv = False
    config.generator.install_deps = False
    config.generator.auto_format = False
    config.generator.run_tests = False

    return config


@pytest.fixture
def mock_event_bus():
    """Create mock event bus for testing."""
    event_bus = AsyncMock()
    event_bus.emit = AsyncMock()
    event_bus.on = Mock()
    return event_bus


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    return {
        "id": "cust_123",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "address": {
            "line1": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "zip": "62701"
        },
        "status": "active",
        "created_at": "2024-01-15T10:30:00Z"
    }


@pytest.fixture
def sample_service_data():
    """Sample service data for testing."""
    return {
        "id": "svc_456",
        "customer_id": "cust_123",
        "service_type": "broadband",
        "plan": "fiber_100",
        "status": "active",
        "monthly_price": 79.99,
        "installation_date": "2024-01-20",
        "equipment": ["modem_789", "router_101"]
    }


@pytest.fixture
def sample_invoice_data():
    """Sample invoice data for testing."""
    return {
        "id": "inv_789",
        "customer_id": "cust_123",
        "amount": 79.99,
        "due_date": "2024-02-15",
        "status": "pending",
        "line_items": [
            {
                "description": "Fiber Internet 100 Mbps",
                "amount": 79.99,
                "quantity": 1
            }
        ]
    }


@pytest.fixture
def http_client():
    """Create HTTP client for API testing."""
    import httpx

    with httpx.Client() as client:
        yield client


@pytest.fixture
async def async_http_client():
    """Create async HTTP client for API testing."""
    import httpx

    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def api_headers():
    """Standard API headers for testing."""
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer test_token_123",
        "X-Tenant-ID": "tenant_test"
    }


# Contract Testing Fixtures
@pytest.fixture
def contract_schemas():
    """Load contract schemas for testing."""
    schemas = {}

    # Customer schema
    schemas["customer"] = {
        "type": "object",
        "required": ["id", "email", "status"],
        "properties": {
            "id": {"type": "string"},
            "email": {"type": "string", "format": "email"},
            "status": {"type": "string", "enum": ["active", "inactive", "suspended"]}
        }
    }

    # Service schema
    schemas["service"] = {
        "type": "object",
        "required": ["id", "customer_id", "service_type", "status"],
        "properties": {
            "id": {"type": "string"},
            "customer_id": {"type": "string"},
            "service_type": {"type": "string"},
            "status": {"type": "string"}
        }
    }

    # Event schema
    schemas["event"] = {
        "type": "object",
        "required": ["event_type", "data", "timestamp"],
        "properties": {
            "event_type": {"type": "string"},
            "data": {"type": "object"},
            "timestamp": {"type": "string", "format": "date-time"}
        }
    }

    return schemas


@pytest.fixture
def validate_contract():
    """Contract validation function."""
    import jsonschema

    def _validate(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        try:
            jsonschema.validate(data, schema)
            return True
        except jsonschema.ValidationError:
            return False

    return _validate


# Performance Testing Fixtures
@pytest.fixture
def performance_monitor():
    """Monitor for performance testing."""
    import time

    import psutil

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None

        def start(self):
            self.start_time = time.time()
            self.start_memory = psutil.Process().memory_info().rss

        def stop(self):
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss

            return {
                "duration_seconds": end_time - self.start_time,
                "memory_delta_mb": (end_memory - self.start_memory) / 1024 / 1024
            }

    return PerformanceMonitor()


# Mock External Services
@pytest.fixture
def mock_stripe():
    """Mock Stripe API for billing tests."""
    stripe_mock = Mock()
    stripe_mock.Customer.create = Mock(return_value={"id": "cus_test123"})
    stripe_mock.PaymentIntent.create = Mock(return_value={"id": "pi_test123", "status": "succeeded"})
    return stripe_mock


@pytest.fixture
def mock_twilio():
    """Mock Twilio API for SMS tests."""
    twilio_mock = Mock()
    twilio_mock.messages.create = Mock(return_value=Mock(sid="SM123"))
    return twilio_mock


@pytest.fixture
def mock_email_service():
    """Mock email service for notification tests."""
    email_mock = AsyncMock()
    email_mock.send_email = AsyncMock(return_value={"message_id": "msg_123"})
    return email_mock


# Pytest Configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "contract: marks tests as contract tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "external: marks tests that require external services")


def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their location/name."""
    for item in items:
        # Mark tests in test_contract_* as contract tests
        if "test_contract" in item.nodeid:
            item.add_marker(pytest.mark.contract)

        # Mark tests in test_performance_* as performance tests
        if "test_performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)

        # Mark tests that use external services
        if any(fixture in item.fixturenames for fixture in ["test_database", "redis_client"]):
            item.add_marker(pytest.mark.external)

        # Mark slow tests (integration, end-to-end)
        if any(marker in item.nodeid for marker in ["integration", "e2e", "end_to_end"]):
            item.add_marker(pytest.mark.slow)


# Async Test Utilities
@pytest.fixture
def run_async():
    """Helper to run async functions in sync tests."""
    def _run_async(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    return _run_async


# Test Data Factory
@pytest.fixture
def test_data_factory():
    """Factory for generating test data."""
    import uuid
    from datetime import datetime
from ..core.datetime_utils import utc_now

    class TestDataFactory:
        @staticmethod
        def customer(**overrides):
            data = {
                "id": f"cust_{uuid.uuid4().hex[:8]}",
                "email": f"test{uuid.uuid4().hex[:8]}@example.com",
                "first_name": "Test",
                "last_name": "Customer",
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            data.update(overrides)
            return data

        @staticmethod
        def service(**overrides):
            data = {
                "id": f"svc_{uuid.uuid4().hex[:8]}",
                "customer_id": f"cust_{uuid.uuid4().hex[:8]}",
                "service_type": "broadband",
                "status": "active",
                "monthly_price": 79.99
            }
            data.update(overrides)
            return data

        @staticmethod
        def event(**overrides):
            data = {
                "event_type": "test.event",
                "data": {"test": True},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "test"
            }
            data.update(overrides)
            return data

    return TestDataFactory()
