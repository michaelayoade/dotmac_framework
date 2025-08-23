"""Simple isolated conftest for core model testing."""

import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# Create isolated base for testing to avoid registry conflicts
TestBase = declarative_base()

# Import ONLY the core models we need for basic testing
from dotmac_isp.modules.identity.models import Customer, User, Role
from dotmac_isp.modules.billing.models import Invoice, InvoiceLineItem, Payment  
from dotmac_isp.modules.services.models import ServiceInstance, ServicePlan
from dotmac_isp.modules.support.models import Ticket

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

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
async def setup_test_database():
    """Set up isolated test database with core models only."""
    # Manually create core tables to avoid registry conflicts
    async with test_engine.begin() as conn:
        # Create core identity tables
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            customer_number TEXT NOT NULL,
            display_name TEXT NOT NULL,
            customer_type TEXT NOT NULL,
            account_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            invoice_number TEXT UNIQUE NOT NULL,
            customer_id TEXT NOT NULL,
            invoice_date DATE NOT NULL,
            due_date DATE NOT NULL,
            subtotal DECIMAL(10,2) DEFAULT 0,
            tax_amount DECIMAL(10,2) DEFAULT 0,
            total_amount DECIMAL(10,2) DEFAULT 0,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """)
        
    yield
    
    # Cleanup
    async with test_engine.begin() as conn:
        await conn.execute("DROP TABLE IF EXISTS invoices")
        await conn.execute("DROP TABLE IF EXISTS customers") 
        await conn.execute("DROP TABLE IF EXISTS users")

@pytest.fixture
async def db_session(setup_test_database):
    """Create a database session for testing."""
    async with TestAsyncSessionLocal() as session:
        yield session
        await session.rollback()