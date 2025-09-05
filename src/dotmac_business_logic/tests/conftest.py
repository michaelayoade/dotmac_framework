"""
Test configuration and fixtures for DotMac Business Logic package.
"""

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest


# Test database setup
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    session = Mock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    return session


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=False)
    return redis


# Billing fixtures
@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    return {
        "id": uuid4(),
        "name": "Test Customer",
        "email": "test@example.com",
        "phone": "+1234567890",
        "billing_address": {
            "street": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "zip_code": "12345",
            "country": "US",
        },
        "tenant_id": uuid4(),
        "created_at": datetime.now(timezone.utc),
        "is_active": True,
    }


@pytest.fixture
def sample_invoice_data():
    """Sample invoice data for testing."""
    return {
        "id": uuid4(),
        "customer_id": uuid4(),
        "invoice_number": "INV-001",
        "issue_date": date.today(),
        "due_date": date.today(),
        "subtotal": Decimal("100.00"),
        "tax_amount": Decimal("10.00"),
        "total_amount": Decimal("110.00"),
        "amount_due": Decimal("110.00"),
        "status": "pending",
        "currency": "USD",
        "tenant_id": uuid4(),
    }


@pytest.fixture
def sample_payment_data():
    """Sample payment data for testing."""
    return {
        "id": uuid4(),
        "customer_id": uuid4(),
        "invoice_id": uuid4(),
        "payment_number": "PAY-001",
        "amount": Decimal("110.00"),
        "currency": "USD",
        "payment_method": "credit_card",
        "status": "completed",
        "payment_date": datetime.now(timezone.utc),
        "tenant_id": uuid4(),
    }


# Task fixtures
@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "id": str(uuid4()),
        "name": "test_task",
        "status": "pending",
        "priority": "normal",
        "created_at": datetime.now(timezone.utc),
        "tenant_id": str(uuid4()),
        "metadata": {"test": True},
    }


@pytest.fixture
def mock_task_queue():
    """Mock task queue for testing."""
    queue = AsyncMock()
    queue.enqueue = AsyncMock(return_value="task-123")
    queue.dequeue = AsyncMock()
    queue.get_status = AsyncMock(return_value="pending")
    queue.cancel = AsyncMock(return_value=True)
    return queue


# File fixtures
@pytest.fixture
def sample_template_data():
    """Sample template data for testing."""
    return {
        "name": "test_template",
        "content": "Hello {{ name }}!",
        "variables": {"name": "Test"},
        "expected_output": "Hello Test!",
    }


@pytest.fixture
def mock_file_storage():
    """Mock file storage for testing."""
    storage = AsyncMock()
    storage.upload = AsyncMock(return_value="file-123")
    storage.download = AsyncMock(return_value=b"test content")
    storage.delete = AsyncMock(return_value=True)
    storage.exists = AsyncMock(return_value=True)
    return storage


# Error handling fixtures
@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


# Performance fixtures
@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing."""

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = datetime.now(timezone.utc)

        def stop(self):
            self.end_time = datetime.now(timezone.utc)

        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time).total_seconds() * 1000
            return 0

    return Timer()


# Configuration fixtures
@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        "database": {"url": "sqlite:///:memory:", "echo": False},
        "redis": {"host": "localhost", "port": 6379, "db": 1},
        "billing": {"default_currency": "USD", "tax_rate": Decimal("0.10")},
        "tasks": {"max_retries": 3, "default_timeout": 300},
        "files": {
            "storage_backend": "memory",
            "max_file_size": 10485760,  # 10MB
        },
    }
