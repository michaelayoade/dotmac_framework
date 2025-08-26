import logging

logger = logging.getLogger(__name__)

"""PostgreSQL-specific test configuration for production-like testing."""

import asyncio
import pytest
import sys
import os
from pathlib import Path
from typing import AsyncGenerator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path)

from dotmac_isp.main import app
from dotmac_isp.core.database import Base, get_async_db, get_db
from dotmac_isp.core.settings import get_settings

settings = get_settings()


def get_test_database_urls():
    """Get test database URLs from environment or defaults."""
    # Use environment variables or Docker defaults
    pg_host = os.getenv("POSTGRES_TEST_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_TEST_PORT", "5432")
    pg_user = os.getenv("POSTGRES_TEST_USER", "postgres")
    pg_password = os.getenv("POSTGRES_TEST_PASSWORD", "postgres")
    pg_database = os.getenv("POSTGRES_TEST_DB", "dotmac_isp_test")
    
    sync_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
    async_url = f"postgresql+asyncpg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
    
    return sync_url, async_url


# Test database URLs
TEST_DATABASE_URL_SYNC, TEST_DATABASE_URL_ASYNC = get_test_database_urls()

# Global test engines (will be created when needed)
test_engine_sync: Optional[object] = None
test_engine_async: Optional[object] = None
TestSessionLocal: Optional[object] = None
TestAsyncSessionLocal: Optional[object] = None


def create_test_engines():
    """Create test engines with proper configuration."""
    global test_engine_sync, test_engine_async, TestSessionLocal, TestAsyncSessionLocal
    
    if test_engine_sync is None:
        test_engine_sync = create_engine(
            TEST_DATABASE_URL_SYNC,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        
        TestSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=test_engine_sync,
        )
    
    if test_engine_async is None:
        test_engine_async = create_async_engine(
            TEST_DATABASE_URL_ASYNC,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        
        TestAsyncSessionLocal = async_sessionmaker(
            bind=test_engine_async,
            class_=AsyncSession,
            expire_on_commit=False,
        )


def import_all_models():
    """Import all models to ensure they're registered with SQLAlchemy."""
    try:
        # Import models that exist to ensure metadata is populated
        from dotmac_isp.shared.database.base import Base, TenantModel, BaseModel
        
        # Import all module models
        try:
            from dotmac_isp.modules.identity.models import Customer, User
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.billing.models import Invoice, Payment, Subscription
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.services.models import ServiceInstance
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.network_integration.models import NetworkDevice
        except ImportError:
            pass
            
        # Import other modules
        module_names = [
            "analytics", "field_ops", "inventory", "network_monitoring",
            "network_visualization", "support", "projects", "portal_management",
            "omnichannel", "resellers", "compliance", "gis", "licensing",
            "notifications"
        ]
        
        for module_name in module_names:
            try:
                __import__(f"dotmac_isp.modules.{module_name}.models")
            except ImportError:
                pass
                
    except Exception as e:
logger.warning(f"Warning: Model import issue: {e}")


async def create_test_database():
    """Create test database if it doesn't exist."""
    # Connect to default postgres database to create test database
    pg_host = os.getenv("POSTGRES_TEST_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_TEST_PORT", "5432")
    pg_user = os.getenv("POSTGRES_TEST_USER", "postgres")
    pg_password = os.getenv("POSTGRES_TEST_PASSWORD", "postgres")
    pg_database = os.getenv("POSTGRES_TEST_DB", "dotmac_isp_test")
    
    default_url = f"postgresql+asyncpg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/postgres"
    
    try:
        engine = create_async_engine(default_url, isolation_level="AUTOCOMMIT")
        async with engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database"),
                {"database": pg_database}
            )
            if not result.fetchone():
                # Create database
                await conn.execute(text(f'CREATE DATABASE "{pg_database}"')
logger.info(f"Created test database: {pg_database}")
        await engine.dispose()
    except Exception as e:
logger.warning(f"Warning: Could not create test database: {e}")


async def drop_test_database():
    """Drop test database after tests."""
    pg_host = os.getenv("POSTGRES_TEST_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_TEST_PORT", "5432")
    pg_user = os.getenv("POSTGRES_TEST_USER", "postgres")
    pg_password = os.getenv("POSTGRES_TEST_PASSWORD", "postgres")
    pg_database = os.getenv("POSTGRES_TEST_DB", "dotmac_isp_test")
    
    default_url = f"postgresql+asyncpg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/postgres"
    
    try:
        engine = create_async_engine(default_url, isolation_level="AUTOCOMMIT")
        async with engine.connect() as conn:
            # Terminate connections to the test database
            await conn.execute(
                text("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = :database AND pid != pg_backend_pid()
                """),
                {"database": pg_database}
            )
            # Drop database
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{pg_database}"')
logger.info(f"Dropped test database: {pg_database}")
        await engine.dispose()
    except Exception as e:
logger.warning(f"Warning: Could not drop test database: {e}")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_postgresql_database():
    """Set up PostgreSQL test database schema."""
    # Create test database
    await create_test_database()
    
    # Create engines
    create_test_engines()
    
    # Import all models
    import_all_models()
    
    # Create all tables
    async with test_engine_async.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Cleanup: Drop all tables
    try:
        async with test_engine_async.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception as e:
logger.warning(f"Warning during cleanup: {e}")
    
    # Dispose engines
    if test_engine_async:
        await test_engine_async.dispose()
    if test_engine_sync:
        test_engine_sync.dispose()


@pytest.fixture
def db_sync(setup_postgresql_database) -> Session:
    """Create a synchronous PostgreSQL database session for testing."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
async def db_session(setup_postgresql_database) -> AsyncGenerator[AsyncSession, None]:
    """Create an asynchronous PostgreSQL database session for testing."""
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
def client_postgresql(db_sync: Session):
    """Create a test client with PostgreSQL synchronous database session override."""
    
    def get_test_db_sync():
        yield db_sync
    
    app.dependency_overrides[get_db] = get_test_db_sync
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def client_postgresql_async(db_session: AsyncSession):
    """Create a test client with PostgreSQL asynchronous database session override."""
    
    async def get_test_db():
        yield db_session
    
    app.dependency_overrides[get_async_db] = get_test_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID for PostgreSQL testing."""
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def postgresql_test_config():
    """PostgreSQL-specific test configuration."""
    return {
        "DATABASE_URL": TEST_DATABASE_URL_SYNC,
        "ASYNC_DATABASE_URL": TEST_DATABASE_URL_ASYNC,
        "TESTING": True,
        "ENVIRONMENT": "testing",
        "USE_POSTGRESQL": True,
    }


# Connection validation
async def validate_postgresql_connection():
    """Validate PostgreSQL connection before running tests."""
    try:
        create_test_engines()
        async with test_engine_async.connect() as conn:
            result = await conn.execute(text("SELECT version()")
            version = result.fetchone()[0]
logger.info(f"PostgreSQL connection successful: {version}")
            return True
    except Exception as e:
logger.info(f"PostgreSQL connection failed: {e}")
        return False


@pytest.fixture(scope="session", autouse=True)
async def validate_database_connection():
    """Auto-validate database connection at test session start."""
    is_connected = await validate_postgresql_connection()
    if not is_connected:
        pytest.skip("PostgreSQL database not available")


# Performance monitoring fixtures
@pytest.fixture
def performance_monitor():
    """Monitor test performance with PostgreSQL."""
    import time
    start_time = time.time()
    
    yield
    
    end_time = time.time()
    duration = end_time - start_time
    if duration > 1.0:  # Warn if test takes more than 1 second
logger.warning(f"Warning: Test took {duration:.2f} seconds")


# Database seeding fixtures
@pytest.fixture
async def seeded_database(db_session: AsyncSession):
    """Provide a database seeded with realistic test data."""
    from tests.factories.identity_factories import CustomerFactory, UserFactory
    from tests.factories.billing_factories import InvoiceFactory, PaymentFactory
    from tests.factories.service_factories import ServiceInstanceFactory
    
    # Create test tenant data (this would normally be done via proper model creation)
    # For now, we'll just ensure factories work
    
    # This fixture can be extended to actually seed the database
    # when the model relationships are properly resolved
    yield db_session