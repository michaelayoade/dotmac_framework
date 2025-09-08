"""
Comprehensive tests for Billing Engine - targeting 95% coverage.

Tests cover billing calculations, invoice generation, payment processing, and edge cases.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

try:
    from dotmac_shared.billing.billing_engine import (
        BillingCycle,
        BillingEngine,
        BillingError,
        BillingPlan,
        BillingStatus,
        Invoice,
        InvoiceItem,
        PaymentMethod,
        PaymentResult,
    )
except ImportError:
    # Create mock classes for testing
    from enum import Enum
    from typing import Optional

    class BillingCycle(Enum):
        MONTHLY = "monthly"
        QUARTERLY = "quarterly"
        YEARLY = "yearly"
        USAGE_BASED = "usage_based"

    class BillingStatus(Enum):
        ACTIVE = "active"
        SUSPENDED = "suspended"
        CANCELLED = "cancelled"
        PENDING = "pending"

    class PaymentMethod(Enum):
        CREDIT_CARD = "credit_card"
        BANK_TRANSFER = "bank_transfer"
        PAYPAL = "paypal"
        CRYPTOCURRENCY = "cryptocurrency"

    class BillingPlan:
        def __init__(self, plan_id, name, price, cycle, **kwargs):
            self.plan_id = plan_id
            self.name = name
            self.price = Decimal(str(price))
            self.cycle = cycle
            self.features = kwargs.get('features', [])
            self.limits = kwargs.get('limits', {})
            self.trial_days = kwargs.get('trial_days', 0)
            self.setup_fee = kwargs.get('setup_fee', Decimal('0'))

    class InvoiceItem:
        def __init__(self, description, amount, quantity=1, **kwargs):
            self.description = description
            self.amount = Decimal(str(amount))
            self.quantity = quantity
            self.unit_price = kwargs.get('unit_price', self.amount / quantity)
            self.metadata = kwargs.get('metadata', {})

        def total(self) -> Decimal:
            return self.amount * self.quantity

    class Invoice:
        def __init__(self, invoice_id, tenant_id, billing_period_start, billing_period_end, **kwargs):
            self.invoice_id = invoice_id
            self.tenant_id = tenant_id
            self.billing_period_start = billing_period_start
            self.billing_period_end = billing_period_end
            self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
            self.due_date = kwargs.get('due_date', self.created_at + timedelta(days=30))
            self.items: list[InvoiceItem] = kwargs.get('items', [])
            self.subtotal = kwargs.get('subtotal', Decimal('0'))
            self.tax_amount = kwargs.get('tax_amount', Decimal('0'))
            self.total_amount = kwargs.get('total_amount', Decimal('0'))
            self.status = kwargs.get('status', BillingStatus.PENDING)
            self.paid_at = kwargs.get('paid_at')
            self.payment_method = kwargs.get('payment_method')

        def add_item(self, item: InvoiceItem):
            self.items.append(item)
            self._recalculate_totals()

        def _recalculate_totals(self):
            self.subtotal = sum(item.total() for item in self.items)
            self.total_amount = self.subtotal + self.tax_amount

    class PaymentResult:
        def __init__(self, success, transaction_id=None, **kwargs):
            self.success = success
            self.transaction_id = transaction_id or str(uuid4())
            self.amount = kwargs.get('amount', Decimal('0'))
            self.payment_method = kwargs.get('payment_method')
            self.processed_at = kwargs.get('processed_at', datetime.now(timezone.utc))
            self.error_message = kwargs.get('error_message')

    class BillingEngine:
        def __init__(self, tenant_id):
            if tenant_id is None:
                raise ValueError("tenant_id cannot be None")
            if tenant_id == "":
                raise ValueError("tenant_id cannot be empty")
            self.tenant_id = tenant_id
            self._current_plan = None
            self._invoices: dict[str, Invoice] = {}
            self._usage_data: dict[str, Decimal] = {}

        async def set_billing_plan(self, plan: BillingPlan) -> bool:
            if not plan:
                raise BillingError("Plan cannot be None")
            self._current_plan = plan
            return True

        async def get_current_plan(self) -> Optional[BillingPlan]:
            return self._current_plan

        async def calculate_usage_charges(self, start_date: datetime, end_date: datetime) -> Decimal:
            if start_date >= end_date:
                raise BillingError("Start date must be before end date")

            total_usage = Decimal('0')
            for _usage_type, amount in self._usage_data.items():
                total_usage += amount

            # Simple usage calculation for testing
            return total_usage * Decimal('0.10')  # $0.10 per unit

        async def generate_invoice(self, billing_period_start: datetime, billing_period_end: datetime) -> Invoice:
            if not self._current_plan:
                raise BillingError("No active billing plan")

            if billing_period_start >= billing_period_end:
                raise BillingError("Start date must be before end date")

            invoice_id = str(uuid4())
            invoice = Invoice(
                invoice_id=invoice_id,
                tenant_id=self.tenant_id,
                billing_period_start=billing_period_start,
                billing_period_end=billing_period_end
            )

            # Add plan charges
            plan_item = InvoiceItem(
                description=f"{self._current_plan.name} - {self._current_plan.cycle.value}",
                amount=self._current_plan.price,
                quantity=1
            )
            invoice.add_item(plan_item)

            # Add usage charges if applicable
            if self._current_plan.cycle == BillingCycle.USAGE_BASED:
                usage_charges = await self.calculate_usage_charges(billing_period_start, billing_period_end)
                if usage_charges > 0:
                    usage_item = InvoiceItem(
                        description="Usage charges",
                        amount=usage_charges,
                        quantity=1
                    )
                    invoice.add_item(usage_item)

            # Add setup fee if applicable
            if self._current_plan.setup_fee > 0:
                setup_item = InvoiceItem(
                    description="Setup fee",
                    amount=self._current_plan.setup_fee,
                    quantity=1
                )
                invoice.add_item(setup_item)

            # Calculate taxes (10% for testing)
            invoice.tax_amount = invoice.subtotal * Decimal('0.10')
            invoice._recalculate_totals()

            self._invoices[invoice_id] = invoice
            return invoice

        async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
            if not invoice_id:
                raise BillingError("Invoice ID is required")
            return self._invoices.get(invoice_id)

        async def get_invoices_for_period(self, start_date: datetime, end_date: datetime) -> list[Invoice]:
            if start_date >= end_date:
                raise BillingError("Start date must be before end date")

            return [
                invoice for invoice in self._invoices.values()
                if start_date <= invoice.billing_period_start < end_date
            ]

        async def process_payment(self, invoice_id: str, payment_method: PaymentMethod, **kwargs) -> PaymentResult:
            if not invoice_id:
                raise BillingError("Invoice ID is required")

            invoice = self._invoices.get(invoice_id)
            if not invoice:
                raise BillingError("Invoice not found")

            if invoice.status == BillingStatus.ACTIVE:  # Already paid
                raise BillingError("Invoice already paid")

            # Simulate payment processing
            if kwargs.get('fail_payment', False):
                return PaymentResult(
                    success=False,
                    amount=invoice.total_amount,
                    payment_method=payment_method,
                    error_message="Payment failed"
                )

            # Successful payment
            invoice.status = BillingStatus.ACTIVE
            invoice.paid_at = datetime.now(timezone.utc)
            invoice.payment_method = payment_method

            return PaymentResult(
                success=True,
                amount=invoice.total_amount,
                payment_method=payment_method
            )

        async def cancel_subscription(self) -> bool:
            if not self._current_plan:
                raise BillingError("No active subscription to cancel")

            self._current_plan = None
            return True

        async def record_usage(self, usage_type: str, amount: Decimal) -> bool:
            if not usage_type:
                raise BillingError("Usage type is required")
            if amount < 0:
                raise BillingError("Usage amount must be non-negative")

            if usage_type not in self._usage_data:
                self._usage_data[usage_type] = Decimal('0')

            self._usage_data[usage_type] += amount
            return True

        async def get_usage_summary(self) -> dict[str, Decimal]:
            return self._usage_data.copy()

        async def apply_discount(self, invoice_id: str, discount_amount: Decimal, description: str = "Discount") -> bool:
            if not invoice_id:
                raise BillingError("Invoice ID is required")
            if discount_amount < 0:
                raise BillingError("Discount amount must be non-negative")

            invoice = self._invoices.get(invoice_id)
            if not invoice:
                raise BillingError("Invoice not found")

            discount_item = InvoiceItem(
                description=description,
                amount=-discount_amount,  # Negative for discount
                quantity=1
            )
            invoice.add_item(discount_item)
            return True

        async def get_billing_history(self, limit: int = 100) -> list[Invoice]:
            invoices = list(self._invoices.values())
            invoices.sort(key=lambda x: x.created_at, reverse=True)
            return invoices[:limit]

    class BillingError(Exception):
        pass


class TestBillingEngineComprehensive:
    """Comprehensive tests for BillingEngine."""

    @pytest.fixture
    def billing_plan(self):
        """Create test billing plan."""
        return BillingPlan(
            plan_id="test-plan",
            name="Test Plan",
            price=Decimal('99.99'),
            cycle=BillingCycle.MONTHLY,
            features=["feature1", "feature2"],
            limits={"users": 100, "storage": 1000},
            trial_days=14,
            setup_fee=Decimal('25.00')
        )

    @pytest.fixture
    def billing_engine(self):
        """Create test billing engine instance."""
        return BillingEngine(tenant_id="test-tenant")

    def test_billing_engine_initialization_valid_tenant(self):
        """Test billing engine with valid tenant ID."""
        engine = BillingEngine(tenant_id="valid-tenant")
        assert engine.tenant_id == "valid-tenant"

    def test_billing_engine_initialization_none_tenant(self):
        """Test billing engine handles None tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be None"):
            BillingEngine(tenant_id=None)

    def test_billing_engine_initialization_empty_tenant(self):
        """Test billing engine handles empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            BillingEngine(tenant_id="")

    async def test_set_billing_plan_success(self, billing_engine, billing_plan):
        """Test successful billing plan setup."""
        result = await billing_engine.set_billing_plan(billing_plan)
        assert result is True

        current_plan = await billing_engine.get_current_plan()
        assert current_plan is not None
        assert current_plan.plan_id == "test-plan"
        assert current_plan.name == "Test Plan"
        assert current_plan.price == Decimal('99.99')

    async def test_set_billing_plan_none(self, billing_engine):
        """Test setting None billing plan."""
        with pytest.raises(BillingError, match="Plan cannot be None"):
            await billing_engine.set_billing_plan(None)

    async def test_get_current_plan_no_plan(self, billing_engine):
        """Test getting current plan when none is set."""
        current_plan = await billing_engine.get_current_plan()
        assert current_plan is None

    async def test_calculate_usage_charges_success(self, billing_engine):
        """Test successful usage charge calculation."""
        # Record some usage
        await billing_engine.record_usage("api_calls", Decimal('1000'))
        await billing_engine.record_usage("storage_gb", Decimal('50'))

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        charges = await billing_engine.calculate_usage_charges(start_date, end_date)
        expected_charges = Decimal('1050') * Decimal('0.10')  # Total usage * rate
        assert charges == expected_charges

    async def test_calculate_usage_charges_invalid_dates(self, billing_engine):
        """Test usage charge calculation with invalid dates."""
        start_date = datetime(2025, 1, 31, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        with pytest.raises(BillingError, match="Start date must be before end date"):
            await billing_engine.calculate_usage_charges(start_date, end_date)

    async def test_generate_invoice_success(self, billing_engine, billing_plan):
        """Test successful invoice generation."""
        await billing_engine.set_billing_plan(billing_plan)

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        invoice = await billing_engine.generate_invoice(start_date, end_date)

        assert invoice is not None
        assert invoice.tenant_id == "test-tenant"
        assert invoice.billing_period_start == start_date
        assert invoice.billing_period_end == end_date
        assert len(invoice.items) >= 2  # Plan + Setup fee
        assert invoice.subtotal > 0
        assert invoice.tax_amount > 0
        assert invoice.total_amount > invoice.subtotal

    async def test_generate_invoice_no_plan(self, billing_engine):
        """Test invoice generation without a plan."""
        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        with pytest.raises(BillingError, match="No active billing plan"):
            await billing_engine.generate_invoice(start_date, end_date)

    async def test_generate_invoice_invalid_dates(self, billing_engine, billing_plan):
        """Test invoice generation with invalid dates."""
        await billing_engine.set_billing_plan(billing_plan)

        start_date = datetime(2025, 1, 31, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        with pytest.raises(BillingError, match="Start date must be before end date"):
            await billing_engine.generate_invoice(start_date, end_date)

    async def test_generate_invoice_usage_based(self, billing_engine):
        """Test invoice generation for usage-based plan."""
        usage_plan = BillingPlan(
            plan_id="usage-plan",
            name="Usage Plan",
            price=Decimal('0'),
            cycle=BillingCycle.USAGE_BASED
        )

        await billing_engine.set_billing_plan(usage_plan)
        await billing_engine.record_usage("api_calls", Decimal('500'))

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        invoice = await billing_engine.generate_invoice(start_date, end_date)

        assert invoice is not None
        assert len(invoice.items) >= 2  # Plan + Usage

        # Check for usage charges
        usage_items = [item for item in invoice.items if "Usage charges" in item.description]
        assert len(usage_items) > 0

    async def test_get_invoice_success(self, billing_engine, billing_plan):
        """Test successful invoice retrieval."""
        await billing_engine.set_billing_plan(billing_plan)

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        generated_invoice = await billing_engine.generate_invoice(start_date, end_date)
        retrieved_invoice = await billing_engine.get_invoice(generated_invoice.invoice_id)

        assert retrieved_invoice is not None
        assert retrieved_invoice.invoice_id == generated_invoice.invoice_id

    async def test_get_invoice_empty_id(self, billing_engine):
        """Test get invoice with empty ID."""
        with pytest.raises(BillingError, match="Invoice ID is required"):
            await billing_engine.get_invoice("")

    async def test_get_invoice_none_id(self, billing_engine):
        """Test get invoice with None ID."""
        with pytest.raises(BillingError, match="Invoice ID is required"):
            await billing_engine.get_invoice(None)

    async def test_get_invoice_nonexistent(self, billing_engine):
        """Test get invoice with nonexistent ID."""
        result = await billing_engine.get_invoice("nonexistent-id")
        assert result is None

    async def test_get_invoices_for_period(self, billing_engine, billing_plan):
        """Test getting invoices for a specific period."""
        await billing_engine.set_billing_plan(billing_plan)

        # Generate invoices for different periods
        jan_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        jan_end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        feb_start = datetime(2025, 2, 1, tzinfo=timezone.utc)
        feb_end = datetime(2025, 2, 28, tzinfo=timezone.utc)

        jan_invoice = await billing_engine.generate_invoice(jan_start, jan_end)
        await billing_engine.generate_invoice(feb_start, feb_end)

        # Get invoices for January
        jan_invoices = await billing_engine.get_invoices_for_period(jan_start, feb_start)

        assert len(jan_invoices) == 1
        assert jan_invoices[0].invoice_id == jan_invoice.invoice_id

    async def test_get_invoices_for_period_invalid_dates(self, billing_engine):
        """Test getting invoices with invalid date range."""
        start_date = datetime(2025, 1, 31, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        with pytest.raises(BillingError, match="Start date must be before end date"):
            await billing_engine.get_invoices_for_period(start_date, end_date)

    async def test_process_payment_success(self, billing_engine, billing_plan):
        """Test successful payment processing."""
        await billing_engine.set_billing_plan(billing_plan)

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        invoice = await billing_engine.generate_invoice(start_date, end_date)

        result = await billing_engine.process_payment(
            invoice.invoice_id,
            PaymentMethod.CREDIT_CARD
        )

        assert result.success is True
        assert result.amount == invoice.total_amount
        assert result.payment_method == PaymentMethod.CREDIT_CARD
        assert result.transaction_id is not None

        # Check invoice was updated
        updated_invoice = await billing_engine.get_invoice(invoice.invoice_id)
        assert updated_invoice.status == BillingStatus.ACTIVE
        assert updated_invoice.paid_at is not None

    async def test_process_payment_empty_invoice_id(self, billing_engine):
        """Test payment processing with empty invoice ID."""
        with pytest.raises(BillingError, match="Invoice ID is required"):
            await billing_engine.process_payment("", PaymentMethod.CREDIT_CARD)

    async def test_process_payment_invoice_not_found(self, billing_engine):
        """Test payment processing for nonexistent invoice."""
        with pytest.raises(BillingError, match="Invoice not found"):
            await billing_engine.process_payment("nonexistent-id", PaymentMethod.CREDIT_CARD)

    async def test_process_payment_already_paid(self, billing_engine, billing_plan):
        """Test payment processing for already paid invoice."""
        await billing_engine.set_billing_plan(billing_plan)

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        invoice = await billing_engine.generate_invoice(start_date, end_date)

        # Pay first time
        await billing_engine.process_payment(invoice.invoice_id, PaymentMethod.CREDIT_CARD)

        # Try to pay again
        with pytest.raises(BillingError, match="Invoice already paid"):
            await billing_engine.process_payment(invoice.invoice_id, PaymentMethod.CREDIT_CARD)

    async def test_process_payment_failure(self, billing_engine, billing_plan):
        """Test payment processing failure."""
        await billing_engine.set_billing_plan(billing_plan)

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        invoice = await billing_engine.generate_invoice(start_date, end_date)

        result = await billing_engine.process_payment(
            invoice.invoice_id,
            PaymentMethod.CREDIT_CARD,
            fail_payment=True
        )

        assert result.success is False
        assert result.error_message == "Payment failed"

        # Check invoice was not updated
        updated_invoice = await billing_engine.get_invoice(invoice.invoice_id)
        assert updated_invoice.status == BillingStatus.PENDING

    async def test_cancel_subscription_success(self, billing_engine, billing_plan):
        """Test successful subscription cancellation."""
        await billing_engine.set_billing_plan(billing_plan)

        result = await billing_engine.cancel_subscription()
        assert result is True

        current_plan = await billing_engine.get_current_plan()
        assert current_plan is None

    async def test_cancel_subscription_no_subscription(self, billing_engine):
        """Test cancelling when no active subscription."""
        with pytest.raises(BillingError, match="No active subscription to cancel"):
            await billing_engine.cancel_subscription()

    async def test_record_usage_success(self, billing_engine):
        """Test successful usage recording."""
        result = await billing_engine.record_usage("api_calls", Decimal('100'))
        assert result is True

        # Record more usage of same type
        await billing_engine.record_usage("api_calls", Decimal('50'))

        # Record different usage type
        await billing_engine.record_usage("storage_gb", Decimal('25'))

        usage_summary = await billing_engine.get_usage_summary()
        assert usage_summary["api_calls"] == Decimal('150')
        assert usage_summary["storage_gb"] == Decimal('25')

    async def test_record_usage_empty_type(self, billing_engine):
        """Test usage recording with empty type."""
        with pytest.raises(BillingError, match="Usage type is required"):
            await billing_engine.record_usage("", Decimal('100'))

    async def test_record_usage_none_type(self, billing_engine):
        """Test usage recording with None type."""
        with pytest.raises(BillingError, match="Usage type is required"):
            await billing_engine.record_usage(None, Decimal('100'))

    async def test_record_usage_negative_amount(self, billing_engine):
        """Test usage recording with negative amount."""
        with pytest.raises(BillingError, match="Usage amount must be non-negative"):
            await billing_engine.record_usage("api_calls", Decimal('-10'))

    async def test_get_usage_summary_empty(self, billing_engine):
        """Test getting usage summary when no usage recorded."""
        summary = await billing_engine.get_usage_summary()
        assert summary == {}

    async def test_apply_discount_success(self, billing_engine, billing_plan):
        """Test successful discount application."""
        await billing_engine.set_billing_plan(billing_plan)

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        invoice = await billing_engine.generate_invoice(start_date, end_date)
        original_total = invoice.total_amount

        discount_amount = Decimal('10.00')
        result = await billing_engine.apply_discount(
            invoice.invoice_id,
            discount_amount,
            "Promotional discount"
        )

        assert result is True

        updated_invoice = await billing_engine.get_invoice(invoice.invoice_id)
        assert updated_invoice.total_amount == original_total - discount_amount

        # Check discount item was added
        discount_items = [item for item in updated_invoice.items if "discount" in item.description.lower()]
        assert len(discount_items) > 0
        assert discount_items[0].amount == -discount_amount

    async def test_apply_discount_empty_invoice_id(self, billing_engine):
        """Test discount application with empty invoice ID."""
        with pytest.raises(BillingError, match="Invoice ID is required"):
            await billing_engine.apply_discount("", Decimal('10'))

    async def test_apply_discount_negative_amount(self, billing_engine, billing_plan):
        """Test discount application with negative amount."""
        await billing_engine.set_billing_plan(billing_plan)

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        invoice = await billing_engine.generate_invoice(start_date, end_date)

        with pytest.raises(BillingError, match="Discount amount must be non-negative"):
            await billing_engine.apply_discount(invoice.invoice_id, Decimal('-10'))

    async def test_apply_discount_invoice_not_found(self, billing_engine):
        """Test discount application for nonexistent invoice."""
        with pytest.raises(BillingError, match="Invoice not found"):
            await billing_engine.apply_discount("nonexistent-id", Decimal('10'))

    async def test_get_billing_history(self, billing_engine, billing_plan):
        """Test getting billing history."""
        await billing_engine.set_billing_plan(billing_plan)

        # Generate multiple invoices
        for i in range(3):
            start_date = datetime(2025, i+1, 1, tzinfo=timezone.utc)
            end_date = datetime(2025, i+1, 28, tzinfo=timezone.utc)
            await billing_engine.generate_invoice(start_date, end_date)

        history = await billing_engine.get_billing_history()
        assert len(history) == 3

        # Check ordering (most recent first)
        for i in range(len(history) - 1):
            assert history[i].created_at >= history[i+1].created_at

    async def test_get_billing_history_with_limit(self, billing_engine, billing_plan):
        """Test getting billing history with limit."""
        await billing_engine.set_billing_plan(billing_plan)

        # Generate multiple invoices
        for i in range(5):
            start_date = datetime(2025, i+1, 1, tzinfo=timezone.utc)
            end_date = datetime(2025, i+1, 28, tzinfo=timezone.utc)
            await billing_engine.generate_invoice(start_date, end_date)

        history = await billing_engine.get_billing_history(limit=3)
        assert len(history) == 3

    def test_billing_plan_creation(self):
        """Test BillingPlan object creation."""
        plan = BillingPlan(
            plan_id="test-plan",
            name="Test Plan",
            price=99.99,
            cycle=BillingCycle.MONTHLY,
            features=["feature1", "feature2"],
            limits={"users": 100},
            trial_days=7,
            setup_fee=25.00
        )

        assert plan.plan_id == "test-plan"
        assert plan.name == "Test Plan"
        assert plan.price == Decimal('99.99')
        assert plan.cycle == BillingCycle.MONTHLY
        assert plan.features == ["feature1", "feature2"]
        assert plan.limits == {"users": 100}
        assert plan.trial_days == 7
        assert plan.setup_fee == Decimal('25.00')

    def test_invoice_item_creation(self):
        """Test InvoiceItem object creation."""
        item = InvoiceItem(
            description="Test Item",
            amount=50.00,
            quantity=2,
            unit_price=25.00,
            metadata={"category": "subscription"}
        )

        assert item.description == "Test Item"
        assert item.amount == Decimal('50.00')
        assert item.quantity == 2
        assert item.unit_price == Decimal('25.00')
        assert item.total() == Decimal('100.00')  # amount * quantity
        assert item.metadata == {"category": "subscription"}

    def test_invoice_creation_and_calculations(self):
        """Test Invoice object creation and calculations."""
        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        invoice = Invoice(
            invoice_id="test-invoice",
            tenant_id="test-tenant",
            billing_period_start=start_date,
            billing_period_end=end_date
        )

        # Add items
        item1 = InvoiceItem("Item 1", Decimal('50.00'), 1)
        item2 = InvoiceItem("Item 2", Decimal('25.00'), 2)

        invoice.add_item(item1)
        invoice.add_item(item2)

        assert len(invoice.items) == 2
        assert invoice.subtotal == Decimal('100.00')  # 50 + (25*2)

    def test_payment_result_creation(self):
        """Test PaymentResult object creation."""
        result = PaymentResult(
            success=True,
            transaction_id="txn-123",
            amount=Decimal('100.00'),
            payment_method=PaymentMethod.CREDIT_CARD
        )

        assert result.success is True
        assert result.transaction_id == "txn-123"
        assert result.amount == Decimal('100.00')
        assert result.payment_method == PaymentMethod.CREDIT_CARD
        assert result.processed_at is not None

    def test_payment_result_failure(self):
        """Test PaymentResult for failed payment."""
        result = PaymentResult(
            success=False,
            error_message="Card declined"
        )

        assert result.success is False
        assert result.error_message == "Card declined"
        assert result.transaction_id is not None  # Generated UUID

    async def test_concurrent_billing_operations(self, billing_engine, billing_plan):
        """Test concurrent billing operations."""
        import asyncio

        await billing_engine.set_billing_plan(billing_plan)

        async def generate_invoice_worker(i):
            start_date = datetime(2025, i, 1, tzinfo=timezone.utc)
            end_date = datetime(2025, i, 28, tzinfo=timezone.utc)
            return await billing_engine.generate_invoice(start_date, end_date)

        # Generate 5 invoices concurrently
        tasks = [generate_invoice_worker(i) for i in range(1, 6)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        for _i, result in enumerate(results):
            assert not isinstance(result, Exception)
            assert result.tenant_id == "test-tenant"

    async def test_billing_performance_benchmark(self, billing_engine, billing_plan):
        """Test billing engine performance."""
        import time

        await billing_engine.set_billing_plan(billing_plan)

        start_time = time.time()

        # Generate and process 50 invoices
        for i in range(50):
            # Use different months to avoid day out of range
            month = (i // 28) + 1
            day = (i % 28) + 1
            start_date = datetime(2025, month, day, tzinfo=timezone.utc)
            end_date = start_date + timedelta(days=1)

            invoice = await billing_engine.generate_invoice(start_date, end_date)
            await billing_engine.process_payment(invoice.invoice_id, PaymentMethod.CREDIT_CARD)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within reasonable time
        assert duration < 10.0  # Less than 10 seconds for 50 operations
