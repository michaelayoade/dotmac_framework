"""Enhanced pytest configuration and fixtures for DotMac ISP Framework.

This module provides comprehensive test fixtures for:
- Database testing with multi-tenant isolation
- API client with authentication 
- Test data factories
- Business logic testing scenarios
- Performance and security testing setup
"""

import asyncio
import pytest
import sys
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator, Dict, Any
from unittest.mock import MagicMock

# Third-party imports
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from faker import Faker
import httpx

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Local imports
from dotmac_isp.main import app
from dotmac_isp.core.database import Base, get_async_db
from dotmac_isp.core.settings import get_settings

# Initialize faker for test data
fake = Faker()

# Test settings
settings = get_settings()

# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine with connection pooling
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

# Import all models before creating tables
def import_all_models():
    """Import all models to ensure they're registered with SQLAlchemy."""
    try:
        # Import models that exist to ensure metadata is populated
        from dotmac_isp.shared.database.base import Base, TenantModel, BaseModel
        
        # Import all module models to register them with SQLAlchemy
        # This matches the pattern from core/database.py init_database()
        try:
            from dotmac_isp.modules.identity import models as identity_models  # noqa: F401
        except ImportError:
            # Create minimal models for testing if they don't exist
            from sqlalchemy import Column, String
            from sqlalchemy.dialects.postgresql import UUID
            
            class Customer(TenantModel):
                __tablename__ = "customers"
                customer_number = Column(String(50), unique=True)
                first_name = Column(String(100))
                last_name = Column(String(100))
                email_primary = Column(String(255))
            
            class User(TenantModel):
                __tablename__ = "users"
                username = Column(String(100), unique=True)
                email = Column(String(255))
            
        try:
            from dotmac_isp.modules.billing import models as billing_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.services import models as services_models  # noqa: F401
        except ImportError:
            # Create minimal ServiceInstance for billing relationships
            from sqlalchemy import Column, String, Numeric
            
            class ServiceInstance(TenantModel):
                __tablename__ = "service_instances"
                service_name = Column(String(255))
                monthly_price = Column(Numeric(10, 2))
                
        try:
            from dotmac_isp.modules.support import models as support_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.projects import models as projects_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.field_ops import models as field_ops_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.network_integration import models as network_integration_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.network_monitoring import models as network_monitoring_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.network_visualization import models as network_visualization_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.analytics import models as analytics_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.inventory import models as inventory_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.compliance import models as compliance_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.licensing import models as licensing_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.notifications import models as notifications_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.omnichannel import models as omnichannel_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.portal_management import models as portal_management_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.resellers import models as resellers_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.sales import models as sales_models  # noqa: F401
        except ImportError:
            pass
            
        try:
            from dotmac_isp.modules.gis import models as gis_models  # noqa: F401
        except ImportError:
            pass
            
    except Exception as e:
        print(f"Warning: Model import issue: {e}")
        # Continue with testing even if some models fail to import

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =============================================================================
# CORE FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_test_database() -> AsyncGenerator[None, None]:
    """Set up test database schema."""
    # Import models first
    import_all_models()
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(setup_test_database) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing with automatic cleanup."""
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
def client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """Create a test client with database session override."""
    
    async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    
    app.dependency_overrides[get_async_db] = get_test_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async HTTP client for testing."""
    
    async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    
    app.dependency_overrides[get_async_db] = get_test_db
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


# =============================================================================
# AUTHENTICATION & AUTHORIZATION FIXTURES
# =============================================================================

@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Create authentication headers for API testing."""
    # This would normally generate a proper JWT token
    # For testing, we'll use a mock token
    return {"Authorization": "Bearer test_jwt_token"}


@pytest.fixture
def admin_user_data() -> Dict[str, Any]:
    """Sample admin user data for testing."""
    return {
        "id": "admin_001",
        "username": "admin_user",
        "email": "admin@dotmac.com",
        "first_name": "Admin",
        "last_name": "User", 
        "role": "admin",
        "tenant_id": "tenant_001",
        "portal_id": "ADMIN_PORTAL_001",
        "is_active": True,
        "is_superuser": True,
    }


@pytest.fixture 
def customer_user_data() -> Dict[str, Any]:
    """Sample customer user data for testing."""
    return {
        "id": "cust_001", 
        "username": "customer_user",
        "email": "customer@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "customer",
        "tenant_id": "tenant_001",
        "portal_id": "CUST_PORTAL_001",
        "is_active": True,
        "is_superuser": False,
    }


@pytest.fixture
def reseller_user_data() -> Dict[str, Any]:
    """Sample reseller user data for testing.""" 
    return {
        "id": "reseller_001",
        "username": "reseller_user", 
        "email": "reseller@partner.com",
        "first_name": "Partner",
        "last_name": "Reseller",
        "role": "reseller",
        "tenant_id": "tenant_002", 
        "portal_id": "RESELLER_PORTAL_001",
        "is_active": True,
        "is_superuser": False,
    }


# =============================================================================
# BUSINESS LOGIC TEST DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_customer_data() -> Dict[str, Any]:
    """Comprehensive customer data for business logic testing."""
    return {
        "customer_number": fake.bothify("CUST###"),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email_primary": fake.email(),
        "email_secondary": fake.email(),
        "phone_primary": fake.phone_number(),
        "phone_secondary": fake.phone_number(),
        "customer_type": "residential",
        "status": "active",
        "billing_address": {
            "street": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.zipcode(),
            "country": "US",
        },
        "service_address": {
            "street": fake.street_address(), 
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.zipcode(),
            "country": "US",
        },
        "tenant_id": "tenant_001",
        "created_by": "system",
    }


@pytest.fixture
def sample_service_data() -> Dict[str, Any]:
    """Sample service provisioning data."""
    return {
        "service_id": fake.bothify("SVC###"),
        "service_type": "internet",
        "plan_name": "Premium Internet 100/20",
        "bandwidth_down": 100,
        "bandwidth_up": 20,
        "monthly_price": 79.99,
        "installation_fee": 99.99,
        "status": "active",
        "activation_date": fake.date_this_year(),
        "tenant_id": "tenant_001",
    }


@pytest.fixture
def sample_billing_data() -> Dict[str, Any]:
    """Sample billing and invoice data."""
    return {
        "invoice_number": fake.bothify("INV-####"),
        "customer_id": "cust_001",
        "billing_period_start": fake.date_this_month(),
        "billing_period_end": fake.date_this_month(),
        "subtotal": 79.99,
        "tax_amount": 7.99,
        "total_amount": 87.98,
        "status": "pending",
        "due_date": fake.future_date(),
        "tenant_id": "tenant_001",
    }


@pytest.fixture
def sample_network_device_data() -> Dict[str, Any]:
    """Sample network device data for monitoring."""
    return {
        "device_id": fake.bothify("DEV###"),
        "device_name": f"Router-{fake.city()}",
        "device_type": "router", 
        "ip_address": fake.ipv4(),
        "mac_address": fake.mac_address(),
        "snmp_community": "public",
        "location": fake.address(),
        "status": "online",
        "last_seen": fake.date_time_this_month(),
        "tenant_id": "tenant_001",
    }


@pytest.fixture
def sample_support_ticket_data() -> Dict[str, Any]:
    """Sample support ticket data."""
    return {
        "ticket_number": fake.bothify("TICKET-#####"),
        "customer_id": "cust_001",
        "subject": "Internet connectivity issues",
        "description": fake.text(),
        "priority": "medium",
        "status": "open",
        "category": "technical",
        "assigned_to": "tech_001",
        "created_by": "cust_001",
        "tenant_id": "tenant_001",
    }


# =============================================================================
# MULTI-TENANT TESTING FIXTURES  
# =============================================================================

@pytest.fixture
def tenant_data() -> Dict[str, Dict[str, Any]]:
    """Multi-tenant test data for isolation testing."""
    return {
        "tenant_001": {
            "tenant_id": "tenant_001", 
            "name": "ISP Alpha",
            "domain": "ispalpha.com",
            "settings": {"billing_cycle": "monthly"},
        },
        "tenant_002": {
            "tenant_id": "tenant_002",
            "name": "ISP Beta", 
            "domain": "ispbeta.com",
            "settings": {"billing_cycle": "quarterly"},
        },
    }


@pytest.fixture
def isolated_tenant_session(tenant_data) -> str:
    """Fixture to ensure tenant isolation in tests."""
    return "tenant_001"  # Default tenant for isolated tests


# =============================================================================
# PERFORMANCE TESTING FIXTURES
# =============================================================================

@pytest.fixture
def performance_test_data() -> Dict[str, Any]:
    """Generate large dataset for performance testing."""
    return {
        "customers": [
            {
                "customer_number": fake.bothify("PERF###"),
                "name": fake.name(), 
                "email": fake.email(),
                "phone": fake.phone_number(),
                "tenant_id": "tenant_001",
            }
            for _ in range(1000)  # 1000 test customers
        ],
        "services": [
            {
                "service_id": fake.bothify("PERF_SVC###"),
                "customer_id": fake.bothify("PERF###"),
                "service_type": fake.random_element(["internet", "voip", "tv"]),
                "monthly_price": fake.pyfloat(2, 2, positive=True, max_value=200),
                "tenant_id": "tenant_001",
            }
            for _ in range(5000)  # 5000 test services
        ]
    }


# =============================================================================
# SECURITY TESTING FIXTURES
# =============================================================================

@pytest.fixture
def security_test_payloads() -> Dict[str, Any]:
    """Malicious payloads for security testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE customers; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM users",
        ],
        "xss_payloads": [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",  
            "<img src=x onerror=alert('XSS')>",
        ],
        "command_injection": [
            "; cat /etc/passwd",
            "| ls -la",
            "&& rm -rf /",
        ],
    }


# =============================================================================
# EXTERNAL SERVICE MOCKS
# =============================================================================

@pytest.fixture
def mock_stripe() -> MagicMock:
    """Mock Stripe payment processing."""
    mock = MagicMock()
    mock.Charge.create.return_value = {
        "id": "ch_test_123",
        "amount": 8799,  # $87.99 in cents
        "currency": "usd", 
        "status": "succeeded",
    }
    return mock


@pytest.fixture 
def mock_twilio() -> MagicMock:
    """Mock Twilio SMS/voice services."""
    mock = MagicMock()
    mock.messages.create.return_value = MagicMock(sid="SM_test_123")
    return mock


@pytest.fixture
def mock_snmp_client() -> MagicMock:
    """Mock SNMP client for network monitoring."""
    mock = MagicMock()
    mock.get.return_value = "test_response"
    mock.walk.return_value = [("oid", "value")]
    return mock


@pytest.fixture
def mock_ansible_runner() -> MagicMock:
    """Mock Ansible automation runner."""
    mock = MagicMock() 
    mock.run.return_value = MagicMock(
        status="successful",
        stdout="Task completed",
        rc=0,
    )
    return mock


# =============================================================================
# CLEANUP AND UTILITIES
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Automatically clean up test files after each test."""
    temp_files = []
    
    def create_temp_file(suffix: str = ".tmp") -> str:
        """Helper to create tracked temporary files."""
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        temp_files.append(path)
        return path
    
    yield create_temp_file
    
    # Cleanup
    for file_path in temp_files:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except OSError:
            pass  # File already cleaned up


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Test configuration settings."""
    return {
        "DATABASE_URL": TEST_DATABASE_URL,
        "REDIS_URL": "redis://localhost:6379/15",  # Test Redis DB
        "TESTING": True,
        "SECRET_KEY": "test_secret_key",
        "JWT_SECRET_KEY": "test_jwt_secret", 
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "DEBUG",
    }


@pytest.fixture(scope="session")
def test_reports_dir() -> Path:
    """Create test reports directory."""
    reports_dir = Path("test-reports")
    reports_dir.mkdir(exist_ok=True)
    return reports_dir


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

@pytest.fixture
def sample_user_data():
    """Sample user data for testing - legacy compatibility."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "testpassword123"
    }