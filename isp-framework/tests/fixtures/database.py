"""Database fixtures for testing - isolated from model conflicts."""

import pytest
import asyncio
from typing import AsyncGenerator
from uuid import uuid4
from decimal import Decimal
from datetime import date, timedelta, datetime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create all necessary tables without model conflicts
    async with engine.begin() as conn:
        # Core identity tables
        await conn.execute(text('''
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            is_verified BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''))
        
        await conn.execute(text('''
        CREATE TABLE customers (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            customer_number TEXT NOT NULL,
            display_name TEXT NOT NULL,
            customer_type TEXT NOT NULL,
            account_status TEXT DEFAULT 'pending',
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            credit_limit DECIMAL(10,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''))
        
        # Billing tables  
        await conn.execute(text('''
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
            currency TEXT DEFAULT 'USD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        '''))
        
        await conn.execute(text('''
        CREATE TABLE invoice_line_items (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            invoice_id TEXT NOT NULL,
            description TEXT NOT NULL,
            quantity DECIMAL(10,2) DEFAULT 1,
            unit_price DECIMAL(10,2) NOT NULL,
            line_total DECIMAL(10,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        )
        '''))
        
        await conn.execute(text('''
        CREATE TABLE payments (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            payment_number TEXT UNIQUE NOT NULL,
            invoice_id TEXT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            payment_date DATE NOT NULL,
            payment_method TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        )
        '''))
        
        # Support tables
        await conn.execute(text('''
        CREATE TABLE tickets (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            ticket_number TEXT UNIQUE NOT NULL,
            customer_id TEXT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        '''))
        
        # Service tables
        await conn.execute(text('''
        CREATE TABLE service_plans (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            plan_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            monthly_price DECIMAL(10,2) NOT NULL,
            service_type TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''))
        
        await conn.execute(text('''
        CREATE TABLE service_instances (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            service_number TEXT UNIQUE NOT NULL,
            customer_id TEXT NOT NULL,
            service_plan_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            monthly_price DECIMAL(10,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (service_plan_id) REFERENCES service_plans(id)
        )
        '''))
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for testing."""
    SessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession)
    
    async with SessionLocal() as session:
        # Start a transaction
        yield session
        # Rollback after each test to ensure isolation
        await session.rollback()


class DatabaseTestFactory:
    """Factory for creating test database records."""
    
    @staticmethod
    async def create_user(session: AsyncSession, **kwargs) -> str:
        """Create a test user."""
        user_id = str(uuid4())
        tenant_id = kwargs.get('tenant_id', str(uuid4()))
        
        await session.execute(text('''
            INSERT INTO users (id, tenant_id, username, email, password_hash, first_name, last_name)
            VALUES (:id, :tenant_id, :username, :email, :password_hash, :first_name, :last_name)
        '''), {
            'id': user_id,
            'tenant_id': tenant_id,
            'username': kwargs.get('username', f'user_{user_id[:8]}'),
            'email': kwargs.get('email', f'user_{user_id[:8]}@example.com'),
            'password_hash': kwargs.get('password_hash', 'hashed_password'),
            'first_name': kwargs.get('first_name', 'Test'),
            'last_name': kwargs.get('last_name', 'User')
        })
        
        await session.commit()
        return user_id
    
    @staticmethod
    async def create_customer(session: AsyncSession, **kwargs) -> str:
        """Create a test customer."""
        customer_id = str(uuid4())
        tenant_id = kwargs.get('tenant_id', str(uuid4()))
        
        await session.execute(text('''
            INSERT INTO customers (id, tenant_id, customer_number, display_name, customer_type, first_name, last_name, email)
            VALUES (:id, :tenant_id, :customer_number, :display_name, :customer_type, :first_name, :last_name, :email)
        '''), {
            'id': customer_id,
            'tenant_id': tenant_id,
            'customer_number': kwargs.get('customer_number', f'CUST{customer_id[:8]}'),
            'display_name': kwargs.get('display_name', f'Customer {customer_id[:8]}'),
            'customer_type': kwargs.get('customer_type', 'residential'),
            'first_name': kwargs.get('first_name', 'John'),
            'last_name': kwargs.get('last_name', 'Doe'),
            'email': kwargs.get('email', f'customer_{customer_id[:8]}@example.com')
        })
        
        await session.commit()
        return customer_id
    
    @staticmethod
    async def create_invoice(session: AsyncSession, customer_id: str, **kwargs) -> str:
        """Create a test invoice."""
        invoice_id = str(uuid4())
        tenant_id = kwargs.get('tenant_id', str(uuid4()))
        
        await session.execute(text('''
            INSERT INTO invoices (id, tenant_id, invoice_number, customer_id, invoice_date, due_date, total_amount, status)
            VALUES (:id, :tenant_id, :invoice_number, :customer_id, :invoice_date, :due_date, :total_amount, :status)
        '''), {
            'id': invoice_id,
            'tenant_id': tenant_id,
            'invoice_number': kwargs.get('invoice_number', f'INV{invoice_id[:8]}'),
            'customer_id': customer_id,
            'invoice_date': kwargs.get('invoice_date', date.today().isoformat()),
            'due_date': kwargs.get('due_date', (date.today() + timedelta(days=30)).isoformat()),
            'total_amount': kwargs.get('total_amount', Decimal('100.00')),
            'status': kwargs.get('status', 'draft')
        })
        
        await session.commit()
        return invoice_id
    
    @staticmethod
    async def create_service_plan(session: AsyncSession, **kwargs) -> str:
        """Create a test service plan."""
        plan_id = str(uuid4())
        tenant_id = kwargs.get('tenant_id', str(uuid4()))
        
        await session.execute(text('''
            INSERT INTO service_plans (id, tenant_id, plan_code, name, monthly_price, service_type)
            VALUES (:id, :tenant_id, :plan_code, :name, :monthly_price, :service_type)
        '''), {
            'id': plan_id,
            'tenant_id': tenant_id,
            'plan_code': kwargs.get('plan_code', f'PLAN{plan_id[:8]}'),
            'name': kwargs.get('name', f'Test Plan {plan_id[:8]}'),
            'monthly_price': kwargs.get('monthly_price', Decimal('50.00')),
            'service_type': kwargs.get('service_type', 'internet')
        })
        
        await session.commit()
        return plan_id


@pytest.fixture
def db_factory():
    """Provide database test factory."""
    return DatabaseTestFactory