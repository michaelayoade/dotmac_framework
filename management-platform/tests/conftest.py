"""
Test configuration and fixtures for the DotMac Management Platform.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import get_db
from app.models.base import BaseModel as Base
# Import all models to register them with SQLAlchemy metadata
from app.models.tenant import Tenant
from app.models.user import User
from app.models.billing import Subscription, Invoice, Payment, PricingPlan, UsageRecord


# Test database URL - use PostgreSQL for production parity
# Defaults can be overridden with environment variables
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_password@localhost:5432/test_dotmac_platform"
)

# Fallback to SQLite if PostgreSQL is not available (for CI/local dev)
SQLITE_TEST_URL = "sqlite+aiosqlite:///./test_platform.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine with PostgreSQL preference and SQLite fallback."""
    database_url = TEST_DATABASE_URL
    
    # Try PostgreSQL first, fall back to SQLite if connection fails
    try:
        engine = create_async_engine(
            database_url,
            poolclass=NullPool,
            echo=False,
            pool_pre_ping=True  # Verify connections before use
        )
        
        # Test connection
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        print(f"✅ Using PostgreSQL test database: {database_url}")
        
    except Exception as e:
        print(f"⚠️  PostgreSQL not available ({e}), falling back to SQLite")
        database_url = SQLITE_TEST_URL
        engine = create_async_engine(
            database_url,
            poolclass=NullPool,
            echo=False
        )
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield engine
        
    finally:
        # Clean up
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        except Exception as e:
            print(f"⚠️  Database cleanup error: {e}")
        
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Provide database session for tests."""
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def client(db_session):
    """Create test client with database override."""
    from unittest.mock import patch
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Create a test app without the problematic lifespan
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from app.api.portals import portals_router
    from app.api.v1 import api_router
    from app.core.exceptions import add_exception_handlers
    from app.core.middleware import (
        LoggingMiddleware,
        RateLimitMiddleware,
        RequestValidationMiddleware,
        SecurityHeadersMiddleware,
        TenantIsolationMiddleware,
    )
    from app.config import settings
    
    test_app = FastAPI(
        title="DotMac Management Platform API",
        description="Test version without database initialization",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Add middleware (same as main app)
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    trusted_hosts = (
        ["localhost", "127.0.0.1", "testserver", "*.dotmac.app"]
        if not settings.is_production
        else ["*.dotmac.app"]
    )
    test_app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=trusted_hosts,
    )

    test_app.add_middleware(LoggingMiddleware)
    test_app.add_middleware(RateLimitMiddleware, calls_per_minute=settings.rate_limit_per_minute)
    test_app.add_middleware(RequestValidationMiddleware)
    test_app.add_middleware(SecurityHeadersMiddleware)
    test_app.add_middleware(TenantIsolationMiddleware)
    
    # Add metrics endpoint for testing
    @test_app.get("/metrics")
    async def metrics_endpoint():
        """Prometheus-style metrics endpoint for testing."""
        from fastapi.responses import PlainTextResponse
        
        metrics_text = """# HELP app_info Application information
# TYPE app_info gauge
app_info{version="1.0.0",environment="test"} 1

# HELP app_requests_total Total number of requests
# TYPE app_requests_total counter
app_requests_total 100
"""
        return PlainTextResponse(content=metrics_text, media_type="text/plain; charset=utf-8")
    
    # Add routers
    test_app.include_router(api_router, prefix="/api/v1")
    test_app.include_router(portals_router, prefix="/portals")
    
    # Add exception handlers
    add_exception_handlers(test_app)
    
    # Override database dependency
    test_app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(test_app) as test_client:
        yield test_client
    
    # Clean up
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def master_admin_token(db_session, test_tenant):
    """Create master admin JWT token for testing with real user."""
    from app.core.security import create_access_token
    from app.repositories.user import UserRepository
    from app.core.security import get_password_hash
    
    # Create a master admin user in the database
    user_repo = UserRepository(db_session)
    admin_user_data = {
        "email": "master@example.com",
        "password_hash": get_password_hash("admin123"),
        "full_name": "Master Admin",
        "role": "master_admin",
        "tenant_id": None,  # Master admin has no tenant
        "is_active": True,
        "is_verified": True
    }
    
    admin_user = await user_repo.create(admin_user_data, "test-system")
    
    token_data = {
        "sub": str(admin_user.id),
        "email": admin_user.email,
        "role": admin_user.role,
        "tenant_id": None
    }
    return create_access_token(token_data)


@pytest_asyncio.fixture  
async def tenant_admin_token(db_session, test_tenant):
    """Create tenant admin JWT token for testing with real user."""
    from app.core.security import create_access_token
    from app.repositories.user import UserRepository
    from app.core.security import get_password_hash
    
    # Create a tenant admin in the database
    user_repo = UserRepository(db_session)
    tenant_admin_data = {
        "email": "tenantadmin@example.com",
        "password_hash": get_password_hash("admin123"),
        "full_name": "Tenant Admin",
        "role": "tenant_admin",
        "tenant_id": test_tenant.id,
        "is_active": True,
        "is_verified": True
    }
    
    tenant_admin = await user_repo.create(tenant_admin_data, "test-system")
    
    token_data = {
        "sub": str(tenant_admin.id),
        "email": tenant_admin.email,
        "role": tenant_admin.role,
        "tenant_id": str(test_tenant.id)
    }
    return create_access_token(token_data)


@pytest_asyncio.fixture
async def tenant_user_token(db_session, test_tenant):
    """Create tenant user JWT token for testing with real user."""
    from app.core.security import create_access_token
    from app.repositories.user import UserRepository
    from app.core.security import get_password_hash
    
    # Create a tenant user in the database
    user_repo = UserRepository(db_session)
    tenant_user_data = {
        "email": "tenantuser@example.com",
        "password_hash": get_password_hash("user123"),
        "full_name": "Tenant User",
        "role": "tenant_user",
        "tenant_id": test_tenant.id,
        "is_active": True,
        "is_verified": True
    }
    
    tenant_user = await user_repo.create(tenant_user_data, "test-system")
    
    token_data = {
        "sub": str(tenant_user.id),
        "email": tenant_user.email,
        "role": tenant_user.role,
        "tenant_id": str(test_tenant.id)
    }
    return create_access_token(token_data)


@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession):
    """Create a test tenant."""
    from app.repositories.tenant import TenantRepository
    from app.models.tenant import Tenant
    
    tenant_repo = TenantRepository(db_session)
    
    tenant_data = {
        "name": "test-tenant",
        "display_name": "Test Tenant",
        "description": "Test tenant for unit tests",
        "slug": "test-tenant-slug",
        "primary_contact_email": "test@example.com",
        "primary_contact_name": "Test Admin",
        "status": "active",
        "tier": "small"
    }
    
    tenant = await tenant_repo.create(tenant_data, "test-system")
    return tenant


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_tenant):
    """Create a test user."""
    from app.repositories.user import UserRepository
    from app.core.security import get_password_hash
    
    user_repo = UserRepository(db_session)
    
    user_data = {
        "email": "test@example.com",
        "password_hash": get_password_hash("testpassword123"),
        "full_name": "Test User",
        "role": "tenant_user",
        "tenant_id": test_tenant.id,
        "is_active": True,
        "is_verified": True
    }
    
    user = await user_repo.create(user_data, "test-system")
    return user


# Test markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )