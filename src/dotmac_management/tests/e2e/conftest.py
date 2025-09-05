"""
E2E Test Configuration for DotMac Management Backend.

This file is disabled by default during standard test runs to avoid pulling
in heavy browser and infrastructure dependencies. Enable by setting
DOTMAC_E2E_ENABLE=1 in the environment.
"""

import os
import secrets
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from dotmac_management.models.tenant import CustomerTenant, TenantStatus
from dotmac_shared.core.logging import get_logger
from sqlalchemy.orm import Session, sessionmaker

logger = get_logger(__name__)

if os.getenv("DOTMAC_E2E_ENABLE") == "1":
    # Only import heavy dependencies when explicitly enabled
    import asyncio
    import secrets
    from datetime import datetime
    from pathlib import Path
    from unittest.mock import AsyncMock, patch

    import httpx
    import pytest
    from dotmac_management.models.tenant import CustomerTenant, TenantStatus
    from dotmac_management.services.tenant_provisioning import (
        TenantProvisioningService,
    )
    from dotmac_shared.core.logging import get_logger
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Page,
        async_playwright,
    )
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    logger = get_logger(__name__)

    # Test configuration
    TEST_BASE_URL = os.getenv("TEST_BASE_URL", "https://test.dotmac.local")
    TEST_MANAGEMENT_URL = f"{TEST_BASE_URL}:8001"
    TEST_ADMIN_URL = f"{TEST_BASE_URL}:8002"
    TEST_RESELLER_URL = f"{TEST_BASE_URL}:8003"
    TEST_CUSTOMER_URL = f"{TEST_BASE_URL}:8004"
    TEST_TECHNICIAN_URL = f"{TEST_BASE_URL}:8005"

    # Test database URLs
    TEST_MANAGEMENT_DB = os.getenv(
        "TEST_MANAGEMENT_DB",
        "postgresql://test_user:test_pass@localhost:5433/test_management",
    )
    TEST_TENANT_A_DB = os.getenv(
        "TEST_TENANT_A_DB",
        "postgresql://test_user:test_pass@localhost:5434/test_tenant_a",
    )
    TEST_TENANT_B_DB = os.getenv(
        "TEST_TENANT_B_DB",
        "postgresql://test_user:test_pass@localhost:5435/test_tenant_b",
    )

    @pytest.fixture(scope="session")
    def event_loop():
        """Event loop for async tests."""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    @pytest.fixture(scope="session")
    async def browser():
        """Browser instance for E2E tests."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--allow-running-insecure-content",
                ],
            )
            yield browser
            await browser.close()

    @pytest.fixture(scope="function")
    async def browser_context(browser: Browser):
        """Isolated browser context for each test."""
        context = await browser.new_context(viewport={"width": 1280, "height": 720}, ignore_https_errors=True)
        yield context
        await context.close()

    @pytest.fixture(scope="function")
    async def management_page(browser_context: BrowserContext):
        """Management admin page."""
        page = await browser_context.new_page()
        await page.goto(TEST_MANAGEMENT_URL)
        yield page
        await page.close()

    @pytest.fixture(scope="function")
    async def tenant_page_factory(browser_context: BrowserContext):
        """Factory for creating tenant-specific pages."""

        async def create_tenant_page(tenant_subdomain: str) -> Page:
            page = await browser_context.new_page()
            tenant_url = f"https://{tenant_subdomain}.{TEST_BASE_URL.replace('https://', '')}"
            await page.goto(tenant_url)
            return page

        yield create_tenant_page

    @pytest.fixture(scope="session")
    def test_db_engines():
        """Database engines for testing."""
        engines = {
            "management": create_engine(TEST_MANAGEMENT_DB),
            "tenant_a": create_engine(TEST_TENANT_A_DB),
            "tenant_b": create_engine(TEST_TENANT_B_DB),
        }

        yield engines

        # Cleanup
        for engine in engines.values():
            engine.dispose()

    @pytest.fixture(scope="function")
    def management_db_session(test_db_engines):
        """Management database session."""
        SessionLocal = sessionmaker(bind=test_db_engines["management"])
        session = SessionLocal()
        try:
            yield session
        finally:
            session.rollback()
            session.close()


@pytest.fixture(scope="function")
def tenant_db_sessions(test_db_engines):
    """Tenant database sessions for isolation testing."""
    sessions = {}

    for tenant_name, engine in test_db_engines.items():
        if tenant_name != "management":
            SessionLocal = sessionmaker(bind=engine)
            sessions[tenant_name] = SessionLocal()

    try:
        yield sessions
    finally:
        for session in sessions.values():
            session.rollback()
            session.close()


@pytest.fixture(scope="function")
async def mock_coolify_client():
    """Mock Coolify client for testing without actual deployments."""
    mock_client = AsyncMock()

    # Mock successful responses
    mock_client.create_application.return_value = {
        "id": f"app_{secrets.token_hex(8)}",
        "name": "test-tenant-app",
        "status": "created",
    }

    mock_client.create_database_service.return_value = {
        "id": f"db_{secrets.token_hex(8)}",
        "name": "test-postgres",
        "status": "created",
    }

    mock_client.create_redis_service.return_value = {
        "id": f"redis_{secrets.token_hex(8)}",
        "name": "test-redis",
        "status": "created",
    }

    mock_client.get_application_status.return_value = {"id": "test-app", "status": "running", "health": "healthy"}

    mock_client.get_deployment_logs.return_value = [
        "Starting deployment...",
        "Database connected",
        "Running migrations...",
        "migration_complete",
        "Application started successfully",
    ]

    return mock_client


@pytest.fixture(scope="function")
def sample_tenant_data():
    """Sample tenant data for testing."""
    tenant_id = f"tenant_{secrets.token_hex(6)}"

    return {
        "tenant_id": tenant_id,
        "subdomain": f"test{secrets.token_hex(4)}",
        "company_name": "Test ISP Company",
        "admin_name": "Test Admin",
        "admin_email": "admin@test-isp.com",
        "plan": "professional",
        "region": "us-east-1",
        "status": TenantStatus.PENDING,
        "settings": {},
    }


@pytest.fixture(scope="function")
def tenant_factory(management_db_session: Session):
    """Factory for creating test tenants."""
    created_tenants = []

    def create_tenant(**overrides) -> CustomerTenant:
        base_data = {
            "tenant_id": f"tenant_{secrets.token_hex(6)}",
            "subdomain": f"test{secrets.token_hex(4)}",
            "company_name": "Test ISP Company",
            "admin_name": "Test Admin",
            "admin_email": f"admin{secrets.token_hex(4)}@test.com",
            "plan": "professional",
            "region": "us-east-1",
            "status": TenantStatus.PENDING,
            "created_at": datetime.now(timezone.utc),
            "settings": {},
        }

        # Apply any overrides
        base_data.update(overrides)

        # Create tenant in database
        tenant = CustomerTenant(**base_data)
        management_db_session.add(tenant)
        management_db_session.commit()
        management_db_session.refresh(tenant)

        created_tenants.append(tenant)
        return tenant

    yield create_tenant

    # Cleanup
    for tenant in created_tenants:
        try:
            management_db_session.delete(tenant)
            management_db_session.commit()
        except Exception as e:
            logger.warning(f"Failed to cleanup tenant {tenant.tenant_id}: {e}")


@pytest.fixture(scope="function")
async def mock_tenant_provisioning_service(mock_coolify_client):
    """Mocked tenant provisioning service."""
    with patch("dotmac_management.services.tenant_provisioning.CoolifyClient", return_value=mock_coolify_client):
        service = TenantProvisioningService()
        yield service


@pytest.fixture(scope="function")
async def http_client():
    """HTTP client for API testing."""
    async with httpx.AsyncClient(
        timeout=30.0,
        verify=False,  # Ignore SSL for test environments
    ) as client:
        yield client


@pytest.fixture(scope="function")
def test_file_cleanup():
    """Cleanup test files and directories."""
    temp_dirs = []
    temp_files = []

    def register_temp_dir(path: Path):
        temp_dirs.append(path)

    def register_temp_file(path: Path):
        temp_files.append(path)

    yield {"dir": register_temp_dir, "file": register_temp_file}

    # Cleanup
    for temp_file in temp_files:
        try:
            if temp_file.exists():
                temp_file.unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")

    for temp_dir in temp_dirs:
        try:
            if temp_dir.exists():
                import shutil

                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")


@pytest.fixture(scope="function")
async def isolation_test_data():
    """Test data for multi-tenant isolation tests."""
    return {
        "tenant_a": {
            "tenant_id": "tenant_isolation_a",
            "subdomain": "isola",
            "company_name": "Isolation Test ISP A",
            "admin_email": "admin_a@isolation-test.com",
            "test_customer_email": "customer_a@test.com",
            "test_customer_data": {"name": "Customer A", "phone": "+1234567890", "address": "123 Test St, City A"},
        },
        "tenant_b": {
            "tenant_id": "tenant_isolation_b",
            "subdomain": "isolb",
            "company_name": "Isolation Test ISP B",
            "admin_email": "admin_b@isolation-test.com",
            "test_customer_email": "customer_b@test.com",
            "test_customer_data": {"name": "Customer B", "phone": "+0987654321", "address": "456 Test Ave, City B"},
        },
    }


@pytest.fixture(scope="function")
async def container_lifecycle_test_setup():
    """Setup for container lifecycle tests."""
    test_containers = []

    def register_container(container_id: str, tenant_id: str):
        test_containers.append({"id": container_id, "tenant_id": tenant_id})

    yield {"register": register_container, "containers": test_containers}

    # Cleanup would happen here in real implementation
    logger.info(f"Container lifecycle test cleanup: {len(test_containers)} containers")


# Test markers for different test types
pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


def pytest_configure(config):
    """Configure test markers."""
    config.addinivalue_line("markers", "tenant_provisioning: marks tests as tenant provisioning tests")
    config.addinivalue_line("markers", "container_lifecycle: marks tests as container lifecycle tests")
    config.addinivalue_line("markers", "tenant_isolation: marks tests as multi-tenant isolation tests")
    config.addinivalue_line("markers", "slow: marks tests as slow-running")


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Auto-setup test environment for E2E tests."""
    monkeypatch.setenv("ENVIRONMENT", "e2e_testing")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("DISABLE_REAL_DEPLOYMENTS", "true")
