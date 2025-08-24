"""Pytest configuration and fixtures for DotMac ISP Framework."""

import asyncio
import pytest
import sys
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fastapi.testclient import TestClient

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from dotmac_isp.main import app
from dotmac_isp.core.database import Base, get_async_db
from dotmac_isp.core.settings import get_settings

settings = get_settings()


def import_all_models():
    """Import all models to ensure they're registered with SQLAlchemy."""
    try:
        # Import all module models to register them with SQLAlchemy
        # This matches the pattern from core/database.py init_database()
        from dotmac_isp.modules.identity import models as identity_models  # noqa: F401
        from dotmac_isp.modules.billing import models as billing_models  # noqa: F401
        from dotmac_isp.modules.services import models as services_models  # noqa: F401
        from dotmac_isp.modules.support import models as support_models  # noqa: F401
        from dotmac_isp.modules.projects import models as projects_models  # noqa: F401
        from dotmac_isp.modules.field_ops import models as field_ops_models  # noqa: F401
        from dotmac_isp.modules.network_integration import models as network_integration_models  # noqa: F401
        from dotmac_isp.modules.network_monitoring import models as network_monitoring_models  # noqa: F401
        from dotmac_isp.modules.network_visualization import models as network_visualization_models  # noqa: F401
        from dotmac_isp.modules.analytics import models as analytics_models  # noqa: F401
        from dotmac_isp.modules.inventory import models as inventory_models  # noqa: F401
        from dotmac_isp.modules.compliance import models as compliance_models  # noqa: F401
        from dotmac_isp.modules.licensing import models as licensing_models  # noqa: F401
        from dotmac_isp.modules.notifications import models as notifications_models  # noqa: F401
        from dotmac_isp.modules.omnichannel import models as omnichannel_models  # noqa: F401
        from dotmac_isp.modules.portal_management import models as portal_management_models  # noqa: F401
        from dotmac_isp.modules.resellers import models as resellers_models  # noqa: F401
        from dotmac_isp.modules.sales import models as sales_models  # noqa: F401
        from dotmac_isp.modules.gis import models as gis_models  # noqa: F401
    except ImportError:
        pass  # Some models may not exist yet

# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database():
    """Set up test database."""
    # Import all models first to register them with SQLAlchemy
    import_all_models()
    
    # Configure cross-module relationships after all models are imported
    try:
        from dotmac_isp.shared.database.relationship_registry import relationship_registry
        relationship_registry.configure_all_relationships()
    except ImportError:
        pass  # Relationship registry not available
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    async with TestAsyncSessionLocal() as session:
        yield session


@pytest.fixture
def client(db_session: AsyncSession):
    """Create a test client with database session override."""
    
    async def get_test_db():
        """Get Test Db operation."""
        yield db_session
    
    app.dependency_overrides[get_async_db] = get_test_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "testpassword123"
    }


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    return {
        "customer_number": "CUST001",
        "first_name": "John",
        "last_name": "Doe",
        "email_primary": "john.doe@example.com",
        "phone_primary": "+1-555-0123",
        "customer_type": "residential"
    }