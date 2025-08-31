"""
Global pytest configuration for DotMac Platform
Provides unified test fixtures and configuration across all modules
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path for proper imports
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Set environment variables for testing
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def test_environment():
    """Test environment configuration"""
    return {
        "environment": "test",
        "database_url": "sqlite:///test.db",
        "redis_url": "redis://localhost:6379/1",
        "api_base_url": "http://localhost:8000",
        "frontend_base_url": "http://localhost:3000"
    }


@pytest.fixture
def mock_database():
    """Mock database connection for testing"""
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.fetch_all = AsyncMock(return_value=[])
    mock_db.fetch_one = AsyncMock(return_value=None)
    return mock_db


@pytest.fixture  
def mock_redis():
    """Mock Redis connection for testing"""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=True)
    return mock_redis


@pytest.fixture
def mock_secrets_manager():
    """Mock secrets manager for testing"""
    mock = MagicMock()
    mock.get_secret = AsyncMock(return_value="test-secret-value")
    mock.set_secret = AsyncMock(return_value=True)
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    return mock


# Async test fixtures
@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Common test data
@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID for testing"""
    return "test-tenant-123"


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing"""
    return "test-user-456"


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing"""
    return {
        "id": "customer-789",
        "name": "Test Customer",
        "email": "customer@test.com",
        "status": "active",
        "tenant_id": "test-tenant-123"
    }