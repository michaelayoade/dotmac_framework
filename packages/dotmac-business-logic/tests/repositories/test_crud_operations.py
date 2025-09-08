"""
Database Repository CRUD Operations Testing - Phase 2
Comprehensive testing of repository patterns, CRUD operations, transactions, and error handling.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

import pytest


class EntityStatus(Enum):
    """Entity status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


@dataclass
class User:
    """User entity for testing"""
    id: str
    email: str
    name: str
    status: EntityStatus
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "status": self.status.value,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata or {}
        }


@dataclass
class Subscription:
    """Subscription entity for testing"""
    id: str
    user_id: str
    plan_id: str
    status: str
    amount: float
    currency: str
    billing_cycle: str
    created_at: datetime
    next_billing_date: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "amount": self.amount,
            "currency": self.currency,
            "billing_cycle": self.billing_cycle,
            "created_at": self.created_at.isoformat(),
            "next_billing_date": self.next_billing_date.isoformat()
        }


class MockDatabase:
    """Mock database connection for testing"""

    def __init__(self):
        self.users = {}
        self.subscriptions = {}
        self.transaction_active = False
        self.transaction_data = {}
        self.query_count = 0
        self.connection_pool_size = 5
        self.active_connections = 0

    async def connect(self):
        """Simulate database connection"""
        if self.active_connections >= self.connection_pool_size:
            raise Exception("Connection pool exhausted")
        self.active_connections += 1

    async def disconnect(self):
        """Simulate database disconnection"""
        self.active_connections = max(0, self.active_connections - 1)

    async def begin_transaction(self):
        """Begin database transaction"""
        if self.transaction_active:
            raise Exception("Transaction already active")
        self.transaction_active = True
        self.transaction_data = {
            "users": self.users.copy(),
            "subscriptions": self.subscriptions.copy()
        }

    async def commit_transaction(self):
        """Commit database transaction"""
        if not self.transaction_active:
            raise Exception("No active transaction")
        self.transaction_active = False
        self.transaction_data = {}

    async def rollback_transaction(self):
        """Rollback database transaction"""
        if not self.transaction_active:
            raise Exception("No active transaction")

        # Restore data from transaction start
        self.users = self.transaction_data["users"]
        self.subscriptions = self.transaction_data["subscriptions"]
        self.transaction_active = False
        self.transaction_data = {}

    async def execute_query(self, query: str, params: dict = None):
        """Execute database query"""
        self.query_count += 1

        # Simulate network latency
        await asyncio.sleep(0.001)

        # Mock query execution
        return {"affected_rows": 1, "query": query, "params": params}


class UserRepository:
    """User repository with CRUD operations"""

    def __init__(self, db: MockDatabase):
        self.db = db

    async def create(self, user_data: dict[str, Any]) -> User:
        """Create new user"""
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        user = User(
            id=user_id,
            email=user_data["email"],
            name=user_data["name"],
            status=EntityStatus(user_data.get("status", "active")),
            tenant_id=user_data["tenant_id"],
            created_at=now,
            updated_at=now,
            metadata=user_data.get("metadata", {})
        )

        # Simulate database insert
        await self.db.execute_query(
            "INSERT INTO users (id, email, name, status, tenant_id, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            {"id": user.id, "email": user.email, "name": user.name}
        )

        self.db.users[user_id] = user
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        await self.db.execute_query("SELECT * FROM users WHERE id = %s", {"id": user_id})
        return self.db.users.get(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        await self.db.execute_query("SELECT * FROM users WHERE email = %s", {"email": email})

        for user in self.db.users.values():
            if user.email == email:
                return user
        return None

    async def update(self, user_id: str, update_data: dict[str, Any]) -> Optional[User]:
        """Update user"""
        user = self.db.users.get(user_id)
        if not user:
            return None

        # Update fields
        for field, value in update_data.items():
            if hasattr(user, field) and field != "id":
                if field == "status":
                    setattr(user, field, EntityStatus(value))
                else:
                    setattr(user, field, value)

        user.updated_at = datetime.now(timezone.utc)

        await self.db.execute_query(
            "UPDATE users SET updated_at = %s WHERE id = %s",
            {"updated_at": user.updated_at, "id": user_id}
        )

        return user

    async def delete(self, user_id: str) -> bool:
        """Delete user (soft delete)"""
        user = self.db.users.get(user_id)
        if not user:
            return False

        user.status = EntityStatus.DELETED
        user.updated_at = datetime.now(timezone.utc)

        await self.db.execute_query("UPDATE users SET status = 'deleted' WHERE id = %s", {"id": user_id})
        return True

    async def list_by_tenant(self, tenant_id: str, limit: int = 100, offset: int = 0) -> list[User]:
        """List users by tenant with pagination"""
        await self.db.execute_query(
            "SELECT * FROM users WHERE tenant_id = %s AND status != 'deleted' LIMIT %s OFFSET %s",
            {"tenant_id": tenant_id, "limit": limit, "offset": offset}
        )

        users = [
            user for user in self.db.users.values()
            if user.tenant_id == tenant_id and user.status != EntityStatus.DELETED
        ]

        return users[offset:offset + limit]

    async def search(self, query: str, tenant_id: str = None) -> list[User]:
        """Search users by name or email"""
        await self.db.execute_query(
            "SELECT * FROM users WHERE (name ILIKE %s OR email ILIKE %s) AND tenant_id = %s",
            {"query": f"%{query}%", "tenant_id": tenant_id}
        )

        results = []
        for user in self.db.users.values():
            if user.status == EntityStatus.DELETED:
                continue

            if tenant_id and user.tenant_id != tenant_id:
                continue

            if query.lower() in user.name.lower() or query.lower() in user.email.lower():
                results.append(user)

        return results


class SubscriptionRepository:
    """Subscription repository with CRUD operations"""

    def __init__(self, db: MockDatabase):
        self.db = db

    async def create(self, subscription_data: dict[str, Any]) -> Subscription:
        """Create new subscription"""
        subscription_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        subscription = Subscription(
            id=subscription_id,
            user_id=subscription_data["user_id"],
            plan_id=subscription_data["plan_id"],
            status=subscription_data.get("status", "active"),
            amount=subscription_data["amount"],
            currency=subscription_data.get("currency", "USD"),
            billing_cycle=subscription_data.get("billing_cycle", "monthly"),
            created_at=now,
            next_billing_date=now + timedelta(days=30)
        )

        await self.db.execute_query(
            "INSERT INTO subscriptions (id, user_id, plan_id, status, amount) VALUES (%s, %s, %s, %s, %s)",
            subscription.to_dict()
        )

        self.db.subscriptions[subscription_id] = subscription
        return subscription

    async def get_by_user_id(self, user_id: str) -> list[Subscription]:
        """Get subscriptions by user ID"""
        await self.db.execute_query("SELECT * FROM subscriptions WHERE user_id = %s", {"user_id": user_id})

        return [
            sub for sub in self.db.subscriptions.values()
            if sub.user_id == user_id
        ]

    async def update_status(self, subscription_id: str, status: str) -> Optional[Subscription]:
        """Update subscription status"""
        subscription = self.db.subscriptions.get(subscription_id)
        if not subscription:
            return None

        subscription.status = status

        await self.db.execute_query(
            "UPDATE subscriptions SET status = %s WHERE id = %s",
            {"status": status, "id": subscription_id}
        )

        return subscription


class TestCRUDOperations:
    """Database CRUD operations tests for Phase 2 coverage"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        return MockDatabase()

    @pytest.fixture
    def user_repo(self, mock_db):
        """Create user repository"""
        return UserRepository(mock_db)

    @pytest.fixture
    def subscription_repo(self, mock_db):
        """Create subscription repository"""
        return SubscriptionRepository(mock_db)

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing"""
        return {
            "email": "test@example.com",
            "name": "Test User",
            "tenant_id": "tenant_123",
            "status": "active",
            "metadata": {"source": "test"}
        }

    # User Repository CRUD Tests

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_repo, sample_user_data):
        """Test successful user creation"""
        user = await user_repo.create(sample_user_data)

        assert user.email == sample_user_data["email"]
        assert user.name == sample_user_data["name"]
        assert user.tenant_id == sample_user_data["tenant_id"]
        assert user.status == EntityStatus.ACTIVE
        assert user.id is not None
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.metadata == sample_user_data["metadata"]

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, user_repo, sample_user_data):
        """Test successful user retrieval by ID"""
        created_user = await user_repo.create(sample_user_data)
        retrieved_user = await user_repo.get_by_id(created_user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email
        assert retrieved_user.name == created_user.name

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_repo):
        """Test user retrieval by ID when user doesn't exist"""
        result = await user_repo.get_by_id("nonexistent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, user_repo, sample_user_data):
        """Test successful user retrieval by email"""
        created_user = await user_repo.create(sample_user_data)
        retrieved_user = await user_repo.get_by_email(sample_user_data["email"])

        assert retrieved_user is not None
        assert retrieved_user.email == sample_user_data["email"]
        assert retrieved_user.id == created_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_repo):
        """Test user retrieval by email when user doesn't exist"""
        result = await user_repo.get_by_email("nonexistent@example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_success(self, user_repo, sample_user_data):
        """Test successful user update"""
        created_user = await user_repo.create(sample_user_data)

        update_data = {
            "name": "Updated Name",
            "status": "inactive"
        }

        updated_user = await user_repo.update(created_user.id, update_data)

        assert updated_user is not None
        assert updated_user.name == "Updated Name"
        assert updated_user.status == EntityStatus.INACTIVE
        assert updated_user.email == sample_user_data["email"]  # Unchanged
        assert updated_user.updated_at > updated_user.created_at

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_repo):
        """Test user update when user doesn't exist"""
        result = await user_repo.update("nonexistent_id", {"name": "New Name"})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_repo, sample_user_data):
        """Test successful user deletion (soft delete)"""
        created_user = await user_repo.create(sample_user_data)

        deleted = await user_repo.delete(created_user.id)
        assert deleted is True

        # Verify user is marked as deleted
        updated_user = await user_repo.get_by_id(created_user.id)
        assert updated_user.status == EntityStatus.DELETED

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_repo):
        """Test user deletion when user doesn't exist"""
        result = await user_repo.delete("nonexistent_id")
        assert result is False

    # Query and Filtering Tests

    @pytest.mark.asyncio
    async def test_list_users_by_tenant(self, user_repo):
        """Test listing users by tenant"""
        tenant_id = "tenant_123"

        # Create multiple users for the tenant
        for i in range(5):
            user_data = {
                "email": f"user{i}@example.com",
                "name": f"User {i}",
                "tenant_id": tenant_id
            }
            await user_repo.create(user_data)

        # Create user for different tenant
        await user_repo.create({
            "email": "other@example.com",
            "name": "Other User",
            "tenant_id": "other_tenant"
        })

        users = await user_repo.list_by_tenant(tenant_id)

        assert len(users) == 5
        assert all(user.tenant_id == tenant_id for user in users)

    @pytest.mark.asyncio
    async def test_list_users_pagination(self, user_repo):
        """Test user listing with pagination"""
        tenant_id = "tenant_123"

        # Create 10 users
        for i in range(10):
            user_data = {
                "email": f"user{i}@example.com",
                "name": f"User {i}",
                "tenant_id": tenant_id
            }
            await user_repo.create(user_data)

        # Test first page
        page1 = await user_repo.list_by_tenant(tenant_id, limit=3, offset=0)
        assert len(page1) == 3

        # Test second page
        page2 = await user_repo.list_by_tenant(tenant_id, limit=3, offset=3)
        assert len(page2) == 3

        # Verify different users in each page
        page1_ids = {user.id for user in page1}
        page2_ids = {user.id for user in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_search_users(self, user_repo):
        """Test user search functionality"""
        tenant_id = "tenant_123"

        # Create test users
        users_data = [
            {"email": "john.doe@example.com", "name": "John Doe", "tenant_id": tenant_id},
            {"email": "jane.smith@example.com", "name": "Jane Smith", "tenant_id": tenant_id},
            {"email": "bob.johnson@example.com", "name": "Bob Johnson", "tenant_id": tenant_id}
        ]

        for user_data in users_data:
            await user_repo.create(user_data)

        # Search by name
        john_results = await user_repo.search("John", tenant_id)
        assert len(john_results) == 1
        assert john_results[0].name == "John Doe"

        # Search by email
        smith_results = await user_repo.search("smith", tenant_id)
        assert len(smith_results) == 1
        assert smith_results[0].email == "jane.smith@example.com"

        # Search with no results
        no_results = await user_repo.search("nonexistent", tenant_id)
        assert len(no_results) == 0

    # Subscription Repository Tests

    @pytest.mark.asyncio
    async def test_create_subscription_success(self, subscription_repo, user_repo, sample_user_data):
        """Test successful subscription creation"""
        # Create user first
        user = await user_repo.create(sample_user_data)

        subscription_data = {
            "user_id": user.id,
            "plan_id": "plan_basic",
            "amount": 29.99,
            "currency": "USD",
            "billing_cycle": "monthly"
        }

        subscription = await subscription_repo.create(subscription_data)

        assert subscription.user_id == user.id
        assert subscription.plan_id == "plan_basic"
        assert subscription.amount == 29.99
        assert subscription.currency == "USD"
        assert subscription.billing_cycle == "monthly"
        assert subscription.status == "active"
        assert subscription.id is not None

    @pytest.mark.asyncio
    async def test_get_subscriptions_by_user(self, subscription_repo, user_repo, sample_user_data):
        """Test retrieving subscriptions by user ID"""
        # Create user
        user = await user_repo.create(sample_user_data)

        # Create multiple subscriptions
        for i in range(3):
            subscription_data = {
                "user_id": user.id,
                "plan_id": f"plan_{i}",
                "amount": 10.0 + i * 10
            }
            await subscription_repo.create(subscription_data)

        subscriptions = await subscription_repo.get_by_user_id(user.id)

        assert len(subscriptions) == 3
        assert all(sub.user_id == user.id for sub in subscriptions)

    @pytest.mark.asyncio
    async def test_update_subscription_status(self, subscription_repo, user_repo, sample_user_data):
        """Test subscription status update"""
        # Create user and subscription
        user = await user_repo.create(sample_user_data)
        subscription_data = {
            "user_id": user.id,
            "plan_id": "plan_basic",
            "amount": 29.99
        }
        subscription = await subscription_repo.create(subscription_data)

        # Update status
        updated = await subscription_repo.update_status(subscription.id, "cancelled")

        assert updated is not None
        assert updated.status == "cancelled"
        assert updated.id == subscription.id

    # Transaction Tests

    @pytest.mark.asyncio
    async def test_transaction_commit(self, mock_db, user_repo, sample_user_data):
        """Test successful transaction commit"""
        await mock_db.begin_transaction()

        # Create user within transaction
        user = await user_repo.create(sample_user_data)
        assert user.id in mock_db.users

        # Commit transaction
        await mock_db.commit_transaction()

        # Verify user still exists
        assert user.id in mock_db.users

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, mock_db, user_repo, sample_user_data):
        """Test transaction rollback"""
        # Create initial user outside transaction
        initial_user = await user_repo.create(sample_user_data)
        initial_count = len(mock_db.users)

        await mock_db.begin_transaction()

        # Create user within transaction
        transaction_user_data = {
            **sample_user_data,
            "email": "transaction@example.com"
        }
        transaction_user = await user_repo.create(transaction_user_data)

        # Verify user exists in transaction
        assert len(mock_db.users) == initial_count + 1

        # Rollback transaction
        await mock_db.rollback_transaction()

        # Verify transaction user is removed
        assert len(mock_db.users) == initial_count
        assert initial_user.id in mock_db.users
        assert transaction_user.id not in mock_db.users

    # Concurrent Access Tests

    @pytest.mark.asyncio
    async def test_concurrent_user_creation(self, user_repo):
        """Test concurrent user creation"""
        tasks = []

        for i in range(10):
            user_data = {
                "email": f"concurrent{i}@example.com",
                "name": f"Concurrent User {i}",
                "tenant_id": "tenant_concurrent"
            }
            tasks.append(user_repo.create(user_data))

        users = await asyncio.gather(*tasks)

        # Verify all users were created
        assert len(users) == 10
        assert len({user.id for user in users}) == 10  # All unique IDs
        assert all(user.tenant_id == "tenant_concurrent" for user in users)

    @pytest.mark.asyncio
    async def test_database_connection_pool(self, mock_db):
        """Test database connection pool limits"""
        # Connect up to pool limit
        for _i in range(mock_db.connection_pool_size):
            await mock_db.connect()

        assert mock_db.active_connections == mock_db.connection_pool_size

        # Try to exceed pool limit
        with pytest.raises(Exception, match="Connection pool exhausted"):
            await mock_db.connect()

        # Disconnect and verify
        await mock_db.disconnect()
        assert mock_db.active_connections == mock_db.connection_pool_size - 1

    # Performance and Optimization Tests

    @pytest.mark.asyncio
    async def test_query_performance_monitoring(self, user_repo, sample_user_data):
        """Test query performance monitoring"""
        initial_query_count = user_repo.db.query_count

        # Perform multiple operations
        user = await user_repo.create(sample_user_data)
        await user_repo.get_by_id(user.id)
        await user_repo.get_by_email(user.email)
        await user_repo.update(user.id, {"name": "Updated"})

        # Verify queries were tracked
        final_query_count = user_repo.db.query_count
        assert final_query_count > initial_query_count
        assert final_query_count - initial_query_count == 4  # 4 operations = 4 queries
