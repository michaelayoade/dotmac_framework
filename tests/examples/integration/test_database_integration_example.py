"""
Example integration tests for database operations.

This demonstrates best practices for testing:
- Database connections and transactions
- Repository pattern testing  
- Data persistence and retrieval
- Database migrations and schema
- Multi-tenant data isolation
"""

import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import uuid4

import pytest
import pytest_asyncio
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Skip tests if no database URL provided
DATABASE_URL = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not provided for integration tests"
)


# Example repository implementation
class DatabaseCustomerRepository:
    """PostgreSQL implementation of customer repository."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create(self, customer_data: Dict) -> Dict:
        """Create a new customer."""
        query = """
            INSERT INTO customers (id, tenant_id, email, first_name, last_name, 
                                 phone, status, balance, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
        """
        
        now = datetime.now(timezone.utc)
        customer_id = customer_data.get('id', str(uuid4())
        
        row = await self.db.fetchrow(
            query,
            customer_id,
            customer_data['tenant_id'],
            customer_data['email'],
            customer_data['first_name'],
            customer_data['last_name'],
            customer_data.get('phone'),
            customer_data.get('status', 'active'),
            Decimal(str(customer_data.get('balance', '0.00'),
            customer_data.get('created_at', now),
            now
        )
        
        return dict(row) if row else None
    
    async def get_by_id(self, customer_id: str, tenant_id: str) -> Optional[Dict]:
        """Get customer by ID with tenant isolation."""
        query = "SELECT * FROM customers WHERE id = $1 AND tenant_id = $2"
        row = await self.db.fetchrow(query, customer_id, tenant_id)
        return dict(row) if row else None
    
    async def get_by_email(self, email: str, tenant_id: str) -> Optional[Dict]:
        """Get customer by email with tenant isolation."""
        query = "SELECT * FROM customers WHERE email = $1 AND tenant_id = $2"
        row = await self.db.fetchrow(query, email, tenant_id)
        return dict(row) if row else None
    
    async def update(self, customer_id: str, tenant_id: str, update_data: Dict) -> Optional[Dict]:
        """Update customer with tenant isolation."""
        set_clauses = []
        values = []
        param_count = 1
        
        for field, value in update_data.items():
            if field not in ['id', 'tenant_id', 'created_at']:
                set_clauses.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
        
        # Always update the updated_at field
        set_clauses.append(f"updated_at = ${param_count}")
        values.append(datetime.now(timezone.utc)
        param_count += 1
        
        # Add WHERE clause parameters
        values.extend([customer_id, tenant_id])
        
        query = f"""
            UPDATE customers 
            SET {', '.join(set_clauses)}
            WHERE id = ${param_count} AND tenant_id = ${param_count + 1}
            RETURNING *
        """
        
        row = await self.db.fetchrow(query, *values)
        return dict(row) if row else None
    
    async def delete(self, customer_id: str, tenant_id: str) -> bool:
        """Delete customer with tenant isolation."""
        query = "DELETE FROM customers WHERE id = $1 AND tenant_id = $2"
        result = await self.db.execute(query, customer_id, tenant_id)
        return result.split()[-1] == '1'  # Check if one row was affected
    
    async def list_by_tenant(self, tenant_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """List customers for a tenant with pagination."""
        query = """
            SELECT * FROM customers 
            WHERE tenant_id = $1 
            ORDER BY created_at DESC 
            LIMIT $2 OFFSET $3
        """
        rows = await self.db.fetch(query, tenant_id, limit, offset)
        return [dict(row) for row in rows]
    
    async def count_by_tenant(self, tenant_id: str) -> int:
        """Count customers for a tenant."""
        query = "SELECT COUNT(*) FROM customers WHERE tenant_id = $1"
        result = await self.db.fetchval(query, tenant_id)
        return result


# Test fixtures
@pytest_asyncio.fixture(scope="session")
async def database_engine():
    """Create async database engine for testing."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_connection(database_engine):
    """Create database connection for tests."""
    async with database_engine.connect() as connection:
        yield connection


@pytest_asyncio.fixture
async def db_transaction(db_connection):
    """Create transaction that rolls back after each test."""
    transaction = await db_connection.begin()
    try:
        yield db_connection
    finally:
        await transaction.rollback()


@pytest_asyncio.fixture
async def setup_test_schema(db_transaction):
    """Set up test schema and tables."""
    # Create customers table if it doesn't exist
    await db_transaction.execute(text("""
        CREATE TABLE IF NOT EXISTS customers (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20),
            status VARCHAR(20) DEFAULT 'active',
            balance DECIMAL(10,2) DEFAULT 0.00,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(email, tenant_id)
        )
    """)
    
    # Create indexes
    await db_transaction.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_customers_tenant_id ON customers(tenant_id)
    """)
    await db_transaction.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_customers_email_tenant ON customers(email, tenant_id)
    """)
    
    await db_transaction.commit()
    yield
    
    # Cleanup - truncate table
    await db_transaction.execute(text("TRUNCATE TABLE customers")
    await db_transaction.commit()


@pytest_asyncio.fixture
async def repository(db_transaction, setup_test_schema):
    """Create customer repository with database connection."""
    return DatabaseCustomerRepository(db_transaction)


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    return {
        'tenant_id': 'test-tenant-1',
        'email': 'test@example.com',
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '1234567890',
        'status': 'active',
        'balance': '100.00'
    }


@pytest.fixture
def another_tenant_customer_data():
    """Customer data for a different tenant."""
    return {
        'tenant_id': 'test-tenant-2',
        'email': 'test@example.com',  # Same email, different tenant
        'first_name': 'Jane',
        'last_name': 'Smith',
        'phone': '0987654321',
        'status': 'active',
        'balance': '200.00'
    }


# Integration tests
@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
class TestCustomerRepositoryBasicOperations:
    """Test basic CRUD operations."""
    
    async def test_create_customer(self, repository, sample_customer_data):
        """Test creating a customer."""
        customer = await repository.create(sample_customer_data)
        
        assert customer is not None
        assert customer['email'] == sample_customer_data['email']
        assert customer['first_name'] == sample_customer_data['first_name']
        assert customer['tenant_id'] == sample_customer_data['tenant_id']
        assert customer['id'] is not None
        assert isinstance(customer['created_at'], datetime)
        assert isinstance(customer['updated_at'], datetime)
    
    async def test_get_customer_by_id(self, repository, sample_customer_data):
        """Test retrieving a customer by ID."""
        # Create customer first
        created_customer = await repository.create(sample_customer_data)
        customer_id = created_customer['id']
        
        # Retrieve customer
        retrieved_customer = await repository.get_by_id(customer_id, sample_customer_data['tenant_id'])
        
        assert retrieved_customer is not None
        assert retrieved_customer['id'] == customer_id
        assert retrieved_customer['email'] == sample_customer_data['email']
    
    async def test_get_customer_by_email(self, repository, sample_customer_data):
        """Test retrieving a customer by email."""
        # Create customer first
        await repository.create(sample_customer_data)
        
        # Retrieve by email
        customer = await repository.get_by_email(
            sample_customer_data['email'], 
            sample_customer_data['tenant_id']
        )
        
        assert customer is not None
        assert customer['email'] == sample_customer_data['email']
        assert customer['tenant_id'] == sample_customer_data['tenant_id']
    
    async def test_update_customer(self, repository, sample_customer_data):
        """Test updating a customer."""
        # Create customer first
        created_customer = await repository.create(sample_customer_data)
        customer_id = created_customer['id']
        
        # Update customer
        update_data = {
            'first_name': 'Updated John',
            'status': 'suspended',
            'balance': Decimal('150.50')
        }
        
        updated_customer = await repository.update(
            customer_id, 
            sample_customer_data['tenant_id'], 
            update_data
        )
        
        assert updated_customer is not None
        assert updated_customer['first_name'] == 'Updated John'
        assert updated_customer['status'] == 'suspended'
        assert updated_customer['balance'] == Decimal('150.50')
        assert updated_customer['updated_at'] > updated_customer['created_at']
    
    async def test_delete_customer(self, repository, sample_customer_data):
        """Test deleting a customer."""
        # Create customer first
        created_customer = await repository.create(sample_customer_data)
        customer_id = created_customer['id']
        
        # Delete customer
        deleted = await repository.delete(customer_id, sample_customer_data['tenant_id'])
        assert deleted is True
        
        # Verify customer is deleted
        customer = await repository.get_by_id(customer_id, sample_customer_data['tenant_id'])
        assert customer is None


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
class TestCustomerRepositoryTenantIsolation:
    """Test multi-tenant data isolation."""
    
    async def test_tenant_isolation_get_by_id(self, repository, sample_customer_data, another_tenant_customer_data):
        """Test that customers are isolated by tenant ID."""
        # Create customer for tenant 1
        customer1 = await repository.create(sample_customer_data)
        customer1_id = customer1['id']
        
        # Try to access customer1 from tenant 2 - should fail
        customer_cross_tenant = await repository.get_by_id(customer1_id, 'test-tenant-2')
        assert customer_cross_tenant is None
        
        # Access from correct tenant should work
        customer_same_tenant = await repository.get_by_id(customer1_id, 'test-tenant-1')
        assert customer_same_tenant is not None
    
    async def test_tenant_isolation_same_email(self, repository, sample_customer_data, another_tenant_customer_data):
        """Test that same email can exist in different tenants."""
        # Create customers with same email in different tenants
        customer1 = await repository.create(sample_customer_data)
        customer2 = await repository.create(another_tenant_customer_data)
        
        assert customer1 is not None
        assert customer2 is not None
        assert customer1['email'] == customer2['email']
        assert customer1['tenant_id'] != customer2['tenant_id']
    
    async def test_tenant_isolation_update(self, repository, sample_customer_data):
        """Test that updates are tenant-isolated."""
        # Create customer
        customer = await repository.create(sample_customer_data)
        customer_id = customer['id']
        
        # Try to update from wrong tenant - should fail
        update_result = await repository.update(
            customer_id, 
            'wrong-tenant', 
            {'first_name': 'Hacker'}
        )
        assert update_result is None
        
        # Verify original customer unchanged
        original_customer = await repository.get_by_id(customer_id, sample_customer_data['tenant_id'])
        assert original_customer['first_name'] == sample_customer_data['first_name']
    
    async def test_tenant_isolation_delete(self, repository, sample_customer_data):
        """Test that deletes are tenant-isolated."""
        # Create customer
        customer = await repository.create(sample_customer_data)
        customer_id = customer['id']
        
        # Try to delete from wrong tenant - should fail
        delete_result = await repository.delete(customer_id, 'wrong-tenant')
        assert delete_result is False
        
        # Verify customer still exists
        customer_check = await repository.get_by_id(customer_id, sample_customer_data['tenant_id'])
        assert customer_check is not None


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
class TestCustomerRepositoryListOperations:
    """Test list and pagination operations."""
    
    async def test_list_customers_empty(self, repository):
        """Test listing customers when none exist."""
        customers = await repository.list_by_tenant('empty-tenant')
        assert customers == []
    
    async def test_list_customers_single(self, repository, sample_customer_data):
        """Test listing customers with single record."""
        # Create one customer
        await repository.create(sample_customer_data)
        
        customers = await repository.list_by_tenant(sample_customer_data['tenant_id'])
        assert len(customers) == 1
        assert customers[0]['email'] == sample_customer_data['email']
    
    async def test_list_customers_multiple(self, repository):
        """Test listing multiple customers."""
        tenant_id = 'multi-customer-tenant'
        
        # Create multiple customers
        customers_data = [
            {
                'tenant_id': tenant_id,
                'email': f'user{i}@example.com',
                'first_name': f'User{i}',
                'last_name': 'Test',
                'status': 'active'
            }
            for i in range(5)
        ]
        
        for customer_data in customers_data:
            await repository.create(customer_data)
        
        # List customers
        customers = await repository.list_by_tenant(tenant_id)
        assert len(customers) == 5
        
        # Verify ordering (newest first)
        emails = [c['email'] for c in customers]
        expected_emails = [f'user{i}@example.com' for i in reversed(range(5)]
        assert emails == expected_emails
    
    async def test_list_customers_pagination(self, repository):
        """Test customer list pagination."""
        tenant_id = 'pagination-tenant'
        
        # Create 10 customers
        for i in range(10):
            await repository.create({
                'tenant_id': tenant_id,
                'email': f'page_user{i:02d}@example.com',
                'first_name': f'PageUser{i:02d}',
                'last_name': 'Test'
            })
        
        # Test first page
        page1 = await repository.list_by_tenant(tenant_id, limit=3, offset=0)
        assert len(page1) == 3
        
        # Test second page
        page2 = await repository.list_by_tenant(tenant_id, limit=3, offset=3)
        assert len(page2) == 3
        
        # Verify no overlap
        page1_emails = {c['email'] for c in page1}
        page2_emails = {c['email'] for c in page2}
        assert page1_emails.isdisjoint(page2_emails)
    
    async def test_count_customers(self, repository):
        """Test customer count functionality."""
        tenant_id = 'count-tenant'
        
        # Initially empty
        count = await repository.count_by_tenant(tenant_id)
        assert count == 0
        
        # Add some customers
        for i in range(7):
            await repository.create({
                'tenant_id': tenant_id,
                'email': f'count_user{i}@example.com',
                'first_name': f'CountUser{i}',
                'last_name': 'Test'
            })
        
        # Check count
        count = await repository.count_by_tenant(tenant_id)
        assert count == 7


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
class TestDatabaseConstraints:
    """Test database constraints and data integrity."""
    
    async def test_unique_email_per_tenant(self, repository, sample_customer_data):
        """Test unique email constraint within tenant."""
        # Create first customer
        await repository.create(sample_customer_data)
        
        # Try to create another customer with same email in same tenant
        duplicate_data = sample_customer_data.copy()
        duplicate_data['first_name'] = 'Different Name'
        
        with pytest.raises(Exception):  # Should raise constraint violation
            await repository.create(duplicate_data)
    
    async def test_required_fields(self, repository):
        """Test that required fields are enforced."""
        incomplete_data = {
            'tenant_id': 'test-tenant',
            'email': 'incomplete@example.com'
            # Missing first_name and last_name
        }
        
        with pytest.raises(Exception):  # Should raise NOT NULL constraint violation
            await repository.create(incomplete_data)
    
    async def test_decimal_precision(self, repository, sample_customer_data):
        """Test decimal field precision."""
        # Test with high precision balance
        sample_customer_data['balance'] = '12345.99'
        customer = await repository.create(sample_customer_data)
        
        assert customer['balance'] == Decimal('12345.99')
        
        # Test precision is maintained
        retrieved = await repository.get_by_id(customer['id'], sample_customer_data['tenant_id'])
        assert retrieved['balance'] == Decimal('12345.99')


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
@pytest.mark.slow
class TestDatabasePerformance:
    """Test database operation performance."""
    
    async def test_bulk_insert_performance(self, repository, benchmark):
        """Test performance of bulk inserts."""
        tenant_id = 'perf-tenant'
        
        def create_customers():
            return asyncio.run(self._bulk_create_customers(repository, tenant_id, 100)
        
        result = benchmark(create_customers)
        assert result == 100  # Number of customers created
    
    async def _bulk_create_customers(self, repository, tenant_id: str, count: int) -> int:
        """Helper method for bulk customer creation."""
        tasks = []
        for i in range(count):
            customer_data = {
                'tenant_id': tenant_id,
                'email': f'perf_user{i:04d}@example.com',
                'first_name': f'PerfUser{i:04d}',
                'last_name': 'Test',
                'balance': str(i * 10.50)
            }
            tasks.append(repository.create(customer_data)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if not isinstance(r, Exception)
        return success_count
    
    async def test_query_performance_with_index(self, repository):
        """Test query performance with proper indexing."""
        tenant_id = 'index-perf-tenant'
        
        # Create many customers
        for i in range(1000):
            await repository.create({
                'tenant_id': tenant_id,
                'email': f'index_user{i:04d}@example.com',
                'first_name': f'IndexUser{i:04d}',
                'last_name': 'Test'
            })
        
        # Query should be fast with index
        import time
        start_time = time.time()
        customers = await repository.list_by_tenant(tenant_id, limit=10)
        query_time = time.time() - start_time
        
        assert len(customers) == 10
        assert query_time < 1.0  # Should complete in under 1 second


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
class TestTransactionHandling:
    """Test transaction handling and rollback scenarios."""
    
    async def test_transaction_rollback_on_error(self, db_connection, setup_test_schema):
        """Test that failed transactions are properly rolled back."""
        # Start transaction
        transaction = await db_connection.begin()
        
        try:
            # Create a customer
            await db_connection.execute(text("""
                INSERT INTO customers (id, tenant_id, email, first_name, last_name)
                VALUES ('test-tx-1', 'tx-tenant', 'tx1@example.com', 'TX', 'User1')
            """)
            
            # This should fail due to unique constraint (same email)
            await db_connection.execute(text("""
                INSERT INTO customers (id, tenant_id, email, first_name, last_name)
                VALUES ('test-tx-2', 'tx-tenant', 'tx1@example.com', 'TX', 'User2')
            """)
            
            await transaction.commit()
        except Exception:
            await transaction.rollback()
        
        # Verify no customers were created (rollback successful)
        result = await db_connection.execute(text("""
            SELECT COUNT(*) FROM customers WHERE tenant_id = 'tx-tenant'
        """)
        count = result.scalar()
        assert count == 0


# Test cleanup fixture
@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data(db_connection):
    """Cleanup test data after each test."""
    yield
    
    # Clean up any test data
    try:
        await db_connection.execute(text("DELETE FROM customers WHERE tenant_id LIKE 'test-%'")
        await db_connection.execute(text("DELETE FROM customers WHERE tenant_id LIKE '%-tenant%'")
        await db_connection.commit()
    except Exception:
        # Ignore cleanup errors
        pass