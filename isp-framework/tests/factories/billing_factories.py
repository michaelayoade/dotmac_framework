"""Factories for billing-related test data."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
import factory
from faker import Faker

from .base import (
    BaseFactory, 
    TenantMixin, 
    TimestampMixin,
    random_decimal,
    invoice_number_generator,
    payment_number_generator,
)

fake = Faker()


class InvoiceFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for Invoice test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None  # Will be set during testing
    
    # Invoice identification
    invoice_number = factory.LazyFunction(invoice_number_generator)
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Invoice dates
    invoice_date = factory.LazyFunction(lambda: date.today())
    due_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    
    # Financial information
    subtotal = factory.LazyFunction(lambda: random_decimal(50.0, 500.0))
    tax_amount = factory.LazyAttribute(lambda obj: obj.subtotal * Decimal('0.085'))
    discount_amount = Decimal('0.00')
    total_amount = factory.LazyAttribute(
        lambda obj: obj.subtotal + obj.tax_amount - obj.discount_amount
    )
    
    # Status and metadata
    status = "draft"
    currency = "USD"
    notes = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=200))
    
    # Payment tracking
    paid_amount = Decimal('0.00')
    paid_date = None
    
    # External references
    external_invoice_id = None
    
    @classmethod
    def create_paid(cls, **kwargs):
        """Create a paid invoice."""
        invoice_data = kwargs.copy()
        invoice_data.update({
            'status': 'paid',
            'paid_date': date.today(),
        })
        invoice = cls.create(**invoice_data)
        invoice.paid_amount = invoice.total_amount
        return invoice
    
    @classmethod
    def create_overdue(cls, **kwargs):
        """Create an overdue invoice."""
        invoice_data = kwargs.copy()
        invoice_data.update({
            'status': 'overdue',
            'due_date': date.today() - timedelta(days=15),
            'invoice_date': date.today() - timedelta(days=45),
        })
        return cls.create(**invoice_data)


class InvoiceLineItemFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for InvoiceLineItem test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    invoice_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Item details
    description = factory.LazyAttribute(lambda obj: fake.catch_phrase())
    quantity = Decimal('1.00')
    unit_price = factory.LazyFunction(lambda: random_decimal(10.0, 200.0))
    line_total = factory.LazyAttribute(lambda obj: obj.quantity * obj.unit_price)
    
    # Tax information
    tax_rate = Decimal('0.0850')  # 8.5%
    tax_amount = factory.LazyAttribute(lambda obj: obj.line_total * obj.tax_rate)
    
    # Service reference
    service_instance_id = factory.LazyFunction(lambda: str(uuid4()))


class PaymentFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for Payment test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    # Payment identification
    payment_number = factory.LazyFunction(payment_number_generator)
    invoice_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Payment details
    amount = factory.LazyFunction(lambda: random_decimal(50.0, 500.0))
    payment_date = factory.LazyFunction(lambda: date.today())
    payment_method = "credit_card"
    status = "completed"
    
    # Payment processing
    transaction_id = factory.LazyAttribute(lambda obj: f"TXN_{fake.bothify('??##??##')}")
    reference_number = factory.LazyAttribute(lambda obj: f"REF_{fake.bothify('###???###')}")
    notes = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=100))
    
    # Failure information
    failure_reason = None
    
    @classmethod
    def create_failed(cls, **kwargs):
        """Create a failed payment."""
        payment_data = kwargs.copy()
        payment_data.update({
            'status': 'failed',
            'failure_reason': fake.sentence(),
            'transaction_id': None,
        })
        return cls.create(**payment_data)
    
    @classmethod
    def create_pending(cls, **kwargs):
        """Create a pending payment."""
        payment_data = kwargs.copy()
        payment_data.update({
            'status': 'pending',
            'transaction_id': None,
        })
        return cls.create(**payment_data)


class SubscriptionFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for Subscription test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    service_instance_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Subscription details
    billing_cycle = "monthly"
    amount = factory.LazyFunction(lambda: random_decimal(25.0, 200.0))
    currency = "USD"
    
    # Dates
    start_date = factory.LazyFunction(lambda: date.today())
    end_date = None  # Ongoing subscription
    next_billing_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    
    # Status
    is_active = True
    auto_renew = True
    
    @classmethod
    def create_quarterly(cls, **kwargs):
        """Create quarterly subscription."""
        subscription_data = kwargs.copy()
        subscription_data.update({
            'billing_cycle': 'quarterly',
            'next_billing_date': date.today() + timedelta(days=90),
        })
        return cls.create(**subscription_data)
    
    @classmethod
    def create_annual(cls, **kwargs):
        """Create annual subscription."""
        subscription_data = kwargs.copy()
        subscription_data.update({
            'billing_cycle': 'annually',
            'next_billing_date': date.today() + timedelta(days=365),
        })
        return cls.create(**subscription_data)


class BillingAccountFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for BillingAccount test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Account details
    account_name = factory.LazyAttribute(lambda obj: fake.catch_phrase())
    is_primary = True
    
    # Payment method details
    payment_method = "credit_card"
    card_last_four = factory.LazyFunction(lambda: str(fake.random_int(1000, 9999)))
    card_expiry = factory.LazyFunction(lambda: f"{fake.random_int(1, 12):02d}/{fake.random_int(2025, 2030)}")
    bank_name = factory.LazyAttribute(lambda obj: fake.company())
    account_number_masked = factory.LazyFunction(lambda: f"****{fake.random_int(1000, 9999)}")
    
    # External payment processor references
    stripe_payment_method_id = factory.LazyAttribute(lambda obj: f"pm_{fake.bothify('??????????????????????')}")
    stripe_customer_id = factory.LazyAttribute(lambda obj: f"cus_{fake.bothify('??????????????')}")
    
    # Status
    is_verified = True
    is_active = True


class TaxRateFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for TaxRate test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    name = factory.LazyAttribute(lambda obj: f"{fake.state()} Sales Tax")
    rate = Decimal('0.0850')  # 8.5%
    tax_type = "sales_tax"
    
    # Geographic applicability
    country_code = "US"
    state_province = factory.LazyAttribute(lambda obj: fake.state_abbr())
    city = factory.LazyAttribute(lambda obj: fake.city())
    postal_code = None
    
    # Effective dates
    effective_from = factory.LazyFunction(lambda: date.today() - timedelta(days=365))
    effective_to = None
    
    is_active = True


class CreditNoteFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for CreditNote test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    # Credit note identification
    credit_note_number = factory.LazyFunction(lambda: f"CN-{fake.bothify('####')}")
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    invoice_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Credit note details
    amount = factory.LazyFunction(lambda: random_decimal(10.0, 100.0))
    reason = factory.LazyAttribute(lambda obj: fake.sentence())
    credit_date = factory.LazyFunction(lambda: date.today())
    
    # Status
    is_applied = False
    applied_date = None


class ReceiptFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for Receipt test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    # Receipt identification
    receipt_number = factory.LazyFunction(lambda: f"RCP-{fake.bothify('######')}")
    payment_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Receipt details
    issued_at = factory.LazyFunction(datetime.utcnow)
    amount = factory.LazyFunction(lambda: random_decimal(50.0, 500.0))
    payment_method = "credit_card"
    
    # Customer and invoice information (denormalized)
    customer_name = factory.LazyAttribute(lambda obj: fake.name())
    invoice_number = factory.LazyFunction(invoice_number_generator)


class LateFeeFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for LateFee test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    # Late fee identification
    invoice_id = factory.LazyFunction(lambda: str(uuid4()))
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Fee details
    fee_amount = factory.LazyFunction(lambda: random_decimal(15.0, 50.0))
    fee_date = factory.LazyFunction(lambda: date.today())
    days_overdue = factory.LazyFunction(lambda: str(fake.random_int(15, 90)))
    
    # Status
    is_waived = False
    waived_date = None
    waived_reason = None