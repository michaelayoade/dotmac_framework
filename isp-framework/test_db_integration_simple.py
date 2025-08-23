"""Simple database integration test to validate our approach."""

import pytest
import asyncio
from uuid import uuid4
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database():
    """Set up simple test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        # Create minimal test tables  
        await conn.execute("""
        CREATE TABLE customers (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            customer_number TEXT NOT NULL,
            display_name TEXT NOT NULL,
            customer_type TEXT NOT NULL,
            account_status TEXT DEFAULT 'pending'
        )
        """)
        
        await conn.execute("""
        CREATE TABLE invoices (
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
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """)
    
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession)
    yield session_factory
    
    await engine.dispose()


@pytest.fixture
async def db_session(setup_database):
    """Create database session."""
    session_factory = await setup_database
    async with session_factory() as session:
        yield session


async def test_database_connection(db_session: AsyncSession):
    """Test basic database connectivity."""
    result = await db_session.execute("SELECT 1 as test")
    assert result.scalar() == 1


async def test_customer_creation(db_session: AsyncSession):
    """Test creating customer record."""
    customer_id = str(uuid4())
    tenant_id = str(uuid4())
    
    await db_session.execute("""
        INSERT INTO customers (id, tenant_id, customer_number, display_name, customer_type)
        VALUES (?, ?, ?, ?, ?)
    """, (customer_id, tenant_id, "CUST001", "John Doe", "residential"))
    
    await db_session.commit()
    
    result = await db_session.execute("SELECT display_name FROM customers WHERE id = ?", (customer_id,))
    assert result.scalar() == "John Doe"


async def test_invoice_creation_with_customer(db_session: AsyncSession):
    """Test creating invoice with customer relationship."""
    # First create customer
    customer_id = str(uuid4())
    tenant_id = str(uuid4())
    
    await db_session.execute("""
        INSERT INTO customers (id, tenant_id, customer_number, display_name, customer_type)
        VALUES (?, ?, ?, ?, ?)
    """, (customer_id, tenant_id, "CUST002", "Jane Smith", "business"))
    
    # Then create invoice
    invoice_id = str(uuid4())
    await db_session.execute("""
        INSERT INTO invoices (id, tenant_id, invoice_number, customer_id, invoice_date, due_date, total_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (invoice_id, tenant_id, "INV001", customer_id, date.today(), date.today() + timedelta(days=30), Decimal('150.00')))
    
    await db_session.commit()
    
    # Verify the relationship works
    result = await db_session.execute("""
        SELECT c.display_name, i.total_amount 
        FROM invoices i
        JOIN customers c ON i.customer_id = c.id
        WHERE i.id = ?
    """, (invoice_id,))
    
    row = result.fetchone()
    assert row[0] == "Jane Smith"  # customer name
    assert row[1] == Decimal('150.00')  # invoice amount


if __name__ == "__main__":
    pytest.main([__file__, "-v"])