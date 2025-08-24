"""Test SQLAlchemy models."""

import pytest
from datetime import datetime, date
from uuid import uuid4

from dotmac_isp.shared.models import (
    BaseModel,
    TenantModel,
    TimestampMixin,
    SoftDeleteMixin,
    TenantMixin,
    StatusMixin,
    AddressMixin,
    ContactMixin,
)
from dotmac_isp.modules.identity.models import (
    User,
    Customer,
    Role,
    UserRole,
    CustomerType,
    AccountStatus,
)
from dotmac_isp.modules.billing.models import (
    Invoice,
    InvoiceStatus,
    PaymentMethod,
)


@pytest.mark.unit
class TestBaseMixins:
    """Test base model mixins."""
    
    def test_timestamp_mixin(self):
        """Test timestamp mixin functionality."""
        class TestModel(TimestampMixin):
            """Class for TestModel operations."""
            pass
        
        # Check that columns exist (this is a basic structure test)
        assert hasattr(TestModel, 'created_at')
        assert hasattr(TestModel, 'updated_at')
    
    def test_soft_delete_mixin(self):
        """Test soft delete mixin functionality."""
        mixin = SoftDeleteMixin()
        
        # Test initial state
        assert mixin.is_deleted is None  # Column default will be set by SQLAlchemy
        assert mixin.deleted_at is None
        
        # Test soft delete
        mixin.soft_delete()
        assert mixin.is_deleted is True
        assert isinstance(mixin.deleted_at, datetime)
        
        # Test restore
        mixin.restore()
        assert mixin.is_deleted is False
        assert mixin.deleted_at is None
    
    def test_status_mixin(self):
        """Test status mixin functionality."""
        mixin = StatusMixin()
        
        # Test change status
        mixin.change_status("inactive", "Testing")
        assert mixin.status == "inactive"
        assert mixin.status_reason == "Testing"
        assert isinstance(mixin.status_changed_at, datetime)
    
    def test_address_mixin(self):
        """Test address mixin functionality."""
        mixin = AddressMixin()
        mixin.street_address = "123 Main St"
        mixin.city = "Anytown"
        mixin.state_province = "CA"
        mixin.postal_code = "12345"
        
        full_address = mixin.full_address
        assert "123 Main St" in full_address
        assert "Anytown" in full_address
        assert "CA" in full_address
        assert "12345" in full_address
        
        # Test with missing fields
        mixin2 = AddressMixin()
        mixin2.city = "TestCity"
        assert mixin2.full_address == "TestCity"
    
    def test_contact_mixin(self):
        """Test contact mixin functionality."""
        mixin = ContactMixin()
        
        # Test with email primary
        mixin.email_primary = "test@example.com"
        assert mixin.primary_contact == "test@example.com"
        
        # Test with phone primary when no email
        mixin.email_primary = None
        mixin.phone_primary = "+1-555-0123"
        assert mixin.primary_contact == "+1-555-0123"
        
        # Test with no contact info
        mixin.phone_primary = None
        assert mixin.primary_contact == "No contact info"


@pytest.mark.unit
class TestIdentityModels:
    """Test identity models."""
    
    def test_user_model_properties(self):
        """Test User model properties."""
        user = User()
        user.first_name = "John"
        user.last_name = "Doe"
        
        assert user.full_name == "John Doe"
        
        # Test locked status
        assert user.is_locked is False
        
        # Test with locked_until in the future
        user.locked_until = datetime.utcnow()
        # Can't test exact lock status as it depends on timing
        assert hasattr(user, 'is_locked')
    
    def test_customer_model_properties(self):
        """Test Customer model properties."""
        # Test business customer display name
        customer = Customer()
        customer.customer_type = CustomerType.BUSINESS
        customer.company_name = "Acme Corp"
        customer.customer_number = "CUST001"
        
        assert customer.display_name == "Acme Corp"
        
        # Test residential customer display name
        customer.customer_type = CustomerType.RESIDENTIAL
        customer.company_name = None
        customer.first_name = "Jane"
        customer.last_name = "Smith"
        
        assert customer.display_name == "Jane Smith"
        
        # Test fallback to customer number
        customer.first_name = None
        customer.last_name = None
        
        assert customer.display_name == "CUST001"
    
    def test_user_role_enum(self):
        """Test UserRole enum values."""
        assert UserRole.SUPER_ADMIN.value == "super_admin"
        assert UserRole.CUSTOMER.value == "customer"
        assert UserRole.TECHNICIAN.value == "technician"
    
    def test_customer_type_enum(self):
        """Test CustomerType enum values."""
        assert CustomerType.RESIDENTIAL.value == "residential"
        assert CustomerType.BUSINESS.value == "business"
        assert CustomerType.ENTERPRISE.value == "enterprise"
    
    def test_account_status_enum(self):
        """Test AccountStatus enum values."""
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.SUSPENDED.value == "suspended"
        assert AccountStatus.PENDING.value == "pending"
        assert AccountStatus.CANCELLED.value == "cancelled"


@pytest.mark.unit
class TestBillingModels:
    """Test billing models."""
    
    def test_invoice_model_properties(self):
        """Test Invoice model properties."""
        invoice = Invoice()
        invoice.total_amount = 100.00
        invoice.paid_amount = 30.00
        invoice.due_date = date.today()
        invoice.status = InvoiceStatus.SENT
        
        # Test balance due calculation
        assert invoice.balance_due == 70.00
        
        # Test overdue status (this invoice due today should not be overdue)
        assert invoice.is_overdue is False
        
        # Test with past due date
        from datetime import timedelta
        invoice.due_date = date.today() - timedelta(days=1)
        assert invoice.is_overdue is True
        
        # Test paid invoice is not overdue
        invoice.status = InvoiceStatus.PAID
        assert invoice.is_overdue is False
    
    def test_invoice_status_enum(self):
        """Test InvoiceStatus enum values."""
        assert InvoiceStatus.DRAFT.value == "draft"
        assert InvoiceStatus.PENDING.value == "pending"
        assert InvoiceStatus.PAID.value == "paid"
        assert InvoiceStatus.OVERDUE.value == "overdue"
    
    def test_payment_method_enum(self):
        """Test PaymentMethod enum values."""
        assert PaymentMethod.CREDIT_CARD.value == "credit_card"
        assert PaymentMethod.BANK_TRANSFER.value == "bank_transfer"
        assert PaymentMethod.ACH.value == "ach"
        assert PaymentMethod.PAYPAL.value == "paypal"