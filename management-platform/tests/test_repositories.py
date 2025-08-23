"""
Unit tests for repository classes.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.repositories.billing_additional import (
    SubscriptionRepository, InvoiceRepository, PaymentRepository
)
from app.models.tenant import Tenant
from app.models.user import User


@pytest.mark.unit
class TestBaseRepository:
    """Test base repository functionality."""
    
    @pytest.mark.asyncio
    async def test_create_record(self, db_session: AsyncSession):
        """Test creating a record."""
        tenant_repo = TenantRepository(db_session)
        
        tenant_data = {
            "name": "test-create",
            "display_name": "Test Create", 
            "description": "Test creating tenant",
            "slug": "test-create-tenant",
            "primary_contact_email": "test@example.com",
            "primary_contact_name": "Test User",
            "status": "active",
            "tier": "small"
        }
        
        tenant = await tenant_repo.create(tenant_data, "test-user")
        
        assert tenant.id is not None
        assert tenant.name == "test-create"
        assert tenant.display_name == "Test Create"
        assert tenant.created_by == "test-user"
        assert tenant.created_at is not None
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session: AsyncSession):
        """Test retrieving record by ID."""
        tenant_repo = TenantRepository(db_session)
        
        # Create tenant
        tenant_data = {
            "name": "test-get-by-id",
            "display_name": "Test Get By ID", 
            "description": "Test getting tenant by ID",
            "slug": "test-get-by-id-tenant",
            "primary_contact_email": "getbyid@example.com",
            "primary_contact_name": "Get By ID User",
            "status": "active",
            "tier": "small"
        }
        
        created_tenant = await tenant_repo.create(tenant_data, "test-user")
        
        # Retrieve tenant
        retrieved_tenant = await tenant_repo.get_by_id(created_tenant.id)
        
        assert retrieved_tenant is not None
        assert retrieved_tenant.id == created_tenant.id
        assert retrieved_tenant.name == "test-get-by-id"
    
    @pytest.mark.asyncio
    async def test_update_record(self, db_session: AsyncSession):
        """Test updating a record."""
        tenant_repo = TenantRepository(db_session)
        
        # Create tenant
        tenant_data = {
            "name": "test-update",
            "display_name": "Test Update",
            "description": "Test updating tenant",
            "slug": "test-update-tenant",
            "primary_contact_email": "update@example.com",
            "primary_contact_name": "Update User",
            "status": "pending",
            "tier": "small"
        }
        
        tenant = await tenant_repo.create(tenant_data, "test-user")
        original_updated_at = tenant.updated_at
        
        # Update tenant
        update_data = {
            "display_name": "Updated Display Name",
            "status": "active"
        }
        
        updated_tenant = await tenant_repo.update(tenant.id, update_data, "test-updater")
        
        assert updated_tenant.display_name == "Updated Display Name"
        assert updated_tenant.status == "active"
        assert updated_tenant.updated_by == "test-updater"
        assert updated_tenant.updated_at > original_updated_at
    
    @pytest.mark.asyncio
    async def test_soft_delete_record(self, db_session: AsyncSession):
        """Test soft deleting a record."""
        tenant_repo = TenantRepository(db_session)
        
        # Create tenant
        tenant_data = {
            "name": "test-delete",
            "display_name": "Test Delete",
            "description": "Test deleting tenant",
            "slug": "test-delete-tenant",
            "primary_contact_email": "delete@example.com",
            "primary_contact_name": "Delete User",
            "status": "active",
            "tier": "small"
        }
        
        tenant = await tenant_repo.create(tenant_data, "test-user")
        
        # Delete tenant
        await tenant_repo.delete(tenant.id)
        
        # Should not find deleted tenant in normal queries
        retrieved_tenant = await tenant_repo.get_by_id(tenant.id)
        assert retrieved_tenant is None
        
        # Should find in deleted records
        deleted_tenant = await tenant_repo.get_by_id(tenant.id, include_deleted=True)
        assert deleted_tenant is not None
        assert deleted_tenant.is_deleted is True
        assert deleted_tenant.deleted_at is not None
    
    @pytest.mark.asyncio
    async def test_list_with_filters(self, db_session: AsyncSession):
        """Test listing records with filters."""
        tenant_repo = TenantRepository(db_session)
        
        # Create test tenants
        tenant_data_list = [
            {
                "name": "active-1", 
                "display_name": "Active 1", 
                "description": "First active tenant",
                "slug": "active-1-tenant",
                "primary_contact_email": "active1@example.com",
                "primary_contact_name": "Active 1 User",
                "status": "active",
                "tier": "small"
            },
            {
                "name": "active-2", 
                "display_name": "Active 2", 
                "description": "Second active tenant",
                "slug": "active-2-tenant",
                "primary_contact_email": "active2@example.com",
                "primary_contact_name": "Active 2 User",
                "status": "active",
                "tier": "medium"
            }, 
            {
                "name": "pending-1", 
                "display_name": "Pending 1", 
                "description": "First pending tenant",
                "slug": "pending-1-tenant",
                "primary_contact_email": "pending1@example.com",
                "primary_contact_name": "Pending 1 User",
                "status": "pending",
                "tier": "small"
            }
        ]
        
        for data in tenant_data_list:
            await tenant_repo.create(data, "test-user")
        
        # Filter by status
        active_tenants = await tenant_repo.list(filters={"status": "active"})
        assert len(active_tenants) == 2
        
        pending_tenants = await tenant_repo.list(filters={"status": "pending"})
        assert len(pending_tenants) == 1
    
    @pytest.mark.asyncio
    async def test_pagination(self, db_session: AsyncSession):
        """Test pagination functionality."""
        tenant_repo = TenantRepository(db_session)
        
        # Create multiple tenants
        for i in range(15):
            tenant_data = {
                "name": f"tenant-{i:02d}",
                "display_name": f"Tenant {i:02d}",
                "description": f"Pagination test tenant {i:02d}",
                "slug": f"tenant-{i:02d}-slug",
                "primary_contact_email": f"tenant{i:02d}@example.com",
                "primary_contact_name": f"Tenant {i:02d} User",
                "status": "active",
                "tier": "small"
            }
            await tenant_repo.create(tenant_data, "test-user")
        
        # Test first page
        page_1 = await tenant_repo.list(skip=0, limit=5)
        assert len(page_1) == 5
        
        # Test second page
        page_2 = await tenant_repo.list(skip=5, limit=5)
        assert len(page_2) == 5
        
        # Test last page
        page_3 = await tenant_repo.list(skip=10, limit=5)
        assert len(page_3) == 5
        
        # Verify no overlap
        page_1_names = {t.name for t in page_1}
        page_2_names = {t.name for t in page_2}
        assert page_1_names.isdisjoint(page_2_names)


@pytest.mark.unit 
class TestTenantRepository:
    """Test tenant-specific repository methods."""
    
    async def test_get_by_name(self, db_session: AsyncSession):
        """Test getting tenant by name."""
        tenant_repo = TenantRepository(db_session)
        
        tenant_data = {
            "name": "unique-tenant",
            "display_name": "Unique Tenant",
            "status": "active"
        }
        
        created_tenant = await tenant_repo.create(tenant_data, "test-user")
        
        retrieved_tenant = await tenant_repo.get_by_name("unique-tenant")
        
        assert retrieved_tenant is not None
        assert retrieved_tenant.id == created_tenant.id
        assert retrieved_tenant.name == "unique-tenant"
    
    async def test_update_status(self, db_session: AsyncSession):
        """Test updating tenant status."""
        tenant_repo = TenantRepository(db_session)
        
        tenant_data = {
            "name": "status-test",
            "display_name": "Status Test",
            "status": "pending"
        }
        
        tenant = await tenant_repo.create(tenant_data, "test-user")
        
        updated_tenant = await tenant_repo.update_status(
            tenant.id, "active", "test-admin"
        )
        
        assert updated_tenant.status == "active"
        assert updated_tenant.updated_by == "test-admin"


@pytest.mark.unit
class TestUserRepository:
    """Test user-specific repository methods."""
    
    async def test_get_by_email(self, db_session: AsyncSession, test_tenant):
        """Test getting user by email."""
        user_repo = UserRepository(db_session)
        
        user_data = {
            "email": "unique@example.com",
            "hashed_password": "hashed_password_123",
            "first_name": "Unique",
            "last_name": "User",
            "role": "tenant_user",
            "tenant_id": test_tenant.id
        }
        
        created_user = await user_repo.create(user_data, "test-admin")
        
        retrieved_user = await user_repo.get_by_email("unique@example.com")
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == "unique@example.com"
    
    async def test_get_by_tenant(self, db_session: AsyncSession, test_tenant):
        """Test getting users by tenant."""
        user_repo = UserRepository(db_session)
        
        # Create users for the tenant
        for i in range(3):
            user_data = {
                "email": f"user{i}@tenant.com",
                "hashed_password": f"password_{i}",
                "first_name": f"User{i}",
                "last_name": "Tenant",
                "role": "tenant_user",
                "tenant_id": test_tenant.id
            }
            await user_repo.create(user_data, "test-admin")
        
        # Get users by tenant
        tenant_users = await user_repo.get_by_tenant(test_tenant.id)
        
        assert len(tenant_users) == 3
        for user in tenant_users:
            assert user.tenant_id == test_tenant.id
    
    async def test_update_last_login(self, db_session: AsyncSession, test_user):
        """Test updating user's last login."""
        user_repo = UserRepository(db_session)
        
        original_last_login = test_user.last_login_at
        
        updated_user = await user_repo.update_last_login(test_user.id)
        
        assert updated_user.last_login_at > original_last_login
        assert updated_user.login_count == (test_user.login_count or 0) + 1


@pytest.mark.unit
class TestBillingRepositories:
    """Test billing-specific repositories."""
    
    async def test_subscription_repository(self, db_session: AsyncSession, test_tenant):
        """Test subscription repository methods."""
        subscription_repo = SubscriptionRepository(db_session)
        
        subscription_data = {
            "tenant_id": test_tenant.id,
            "plan_name": "standard",
            "status": "active",
            "billing_cycle": "monthly",
            "price": 99.99,
            "currency": "USD"
        }
        
        subscription = await subscription_repo.create(subscription_data, "test-admin")
        
        # Test get_by_tenant
        tenant_subscriptions = await subscription_repo.get_by_tenant(test_tenant.id)
        assert len(tenant_subscriptions) == 1
        assert tenant_subscriptions[0].id == subscription.id
        
        # Test get_active_subscription
        active_subscription = await subscription_repo.get_active_subscription(test_tenant.id)
        assert active_subscription is not None
        assert active_subscription.id == subscription.id
        assert active_subscription.status == "active"
    
    async def test_invoice_repository(self, db_session: AsyncSession, test_tenant):
        """Test invoice repository methods."""
        # First create a subscription
        subscription_repo = SubscriptionRepository(db_session)
        subscription_data = {
            "tenant_id": test_tenant.id,
            "plan_name": "standard",
            "status": "active",
            "billing_cycle": "monthly",
            "price": 99.99
        }
        subscription = await subscription_repo.create(subscription_data, "test-admin")
        
        # Create invoice
        invoice_repo = InvoiceRepository(db_session)
        invoice_data = {
            "tenant_id": test_tenant.id,
            "subscription_id": subscription.id,
            "amount": 99.99,
            "currency": "USD",
            "status": "pending",
            "due_date": datetime.utcnow()
        }
        
        invoice = await invoice_repo.create(invoice_data, "test-admin")
        
        # Test get_by_tenant
        tenant_invoices = await invoice_repo.get_by_tenant(test_tenant.id)
        assert len(tenant_invoices) == 1
        assert tenant_invoices[0].id == invoice.id
        
        # Test update_status
        updated_invoice = await invoice_repo.update_status(
            invoice.id, "paid", "test-admin"
        )
        assert updated_invoice.status == "paid"
    
    async def test_payment_repository(self, db_session: AsyncSession, test_tenant):
        """Test payment repository methods."""
        payment_repo = PaymentRepository(db_session)
        
        payment_data = {
            "tenant_id": test_tenant.id,
            "amount": 99.99,
            "currency": "USD",
            "status": "completed",
            "payment_method": "credit_card",
            "provider": "stripe",
            "provider_payment_id": "pi_test_123"
        }
        
        payment = await payment_repo.create(payment_data, "test-system")
        
        # Test get_by_tenant
        tenant_payments = await payment_repo.get_by_tenant(test_tenant.id)
        assert len(tenant_payments) == 1
        assert tenant_payments[0].id == payment.id
        
        # Test get_successful_payments
        successful_payments = await payment_repo.get_successful_payments(test_tenant.id)
        assert len(successful_payments) == 1
        assert successful_payments[0].status == "completed"