"""
Root conftest.py - Shared test fixtures and configuration.

Leverages existing DotMac infrastructure for clean testing.
Also ensures local monorepo packages are importable in tests.
"""

import asyncio
import glob
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Ensure local packages/*/src are importable (provides top-level `dotmac` pkg)
REPO_ROOT = Path(__file__).resolve().parents[1]  # noqa: B008
for pattern in [REPO_ROOT / "packages" / "*" / "src", REPO_ROOT / "packages" / "*" / "*" / "src"]:
    for path in glob.glob(str(pattern)):
        if path not in sys.path:
            sys.path.insert(0, path)

# Prevent accidental import of heavy E2E conftest inside src during unit test collection
import types

sys.modules.setdefault("dotmac_management.tests.e2e.conftest", types.ModuleType("conftest"))

import pytest

# Test environment setup
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32-chars-min")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def framework_root() -> Path:
    """Framework root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def src_path(framework_root) -> Path:
    """Source code path."""
    return framework_root / "src"


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Auto-setup test environment for all tests."""
    # Ensure test environment variables
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")  # Reduce noise in tests


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = False
    return redis_mock


@pytest.fixture
def mock_database():
    """Mock database session for testing."""
    db_mock = MagicMock()
    db_mock.query.return_value.filter.return_value.first.return_value = None
    db_mock.query.return_value.all.return_value = []
    db_mock.add.return_value = None
    db_mock.commit.return_value = None
    db_mock.refresh.return_value = None
    return db_mock


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "username": "testuser",
        "is_active": True,
        "tenant_id": "test-tenant-456",
    }


@pytest.fixture
def sample_tenant_data():
    """Sample tenant data for testing."""
    return {
        "id": "test-tenant-456",
        "name": "Test ISP",
        "domain": "test.example.com",
        "is_active": True,
        "plan": "professional",
    }


@pytest.fixture
async def async_mock_client():
    """Async mock client for testing."""
    client = AsyncMock()
    client.get.return_value.status_code = 200
    client.get.return_value.json.return_value = {"status": "ok"}
    client.post.return_value.status_code = 201
    client.post.return_value.json.return_value = {"id": "created"}
    return client


@pytest.fixture
def clean_environment():
    """Ensure clean environment for sensitive tests."""
    # Clean any global state that might interfere with tests
    import sys

    # Clear any cached modules that might have global state
    modules_to_clear = [
        name for name in sys.modules.keys() if name.startswith("dotmac_")
    ]
    for module_name in modules_to_clear:
        if hasattr(sys.modules[module_name], "_global_cache"):
            delattr(sys.modules[module_name], "_global_cache")

    yield

    # Cleanup after test
    pass


# Pytest configuration
def pytest_configure(config):
    """Pytest configuration."""
    import warnings

    # Suppress warnings during testing
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


def pytest_collection_modifyitems(config, items):
    """Modify collected test items."""
    # Auto-mark async tests
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
