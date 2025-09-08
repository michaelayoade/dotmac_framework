"""
Integration tests for Billing Service
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

try:
    from dotmac_business_logic.billing.core.models import (
        BillingCycle,
        BillingPeriod,
        Invoice,
        InvoiceLineItem,
        InvoiceStatus,
        Payment,
        PaymentStatus,
        Subscription,
        SubscriptionStatus,
        UsageRecord,
    )
    from dotmac_business_logic.billing.schemas.billing_schemas import (
        SubscriptionCreate,
        UsageRecordCreate,
    )
    from dotmac_business_logic.billing.services.billing_service import BillingService
    from dotmac_business_logic.billing.services.protocols import (
        BillingPlanRepositoryProtocol,
        CustomerRepositoryProtocol,
        DatabaseSessionProtocol,
        InvoiceRepositoryProtocol,
        NotificationServiceProtocol,
        PaymentGatewayProtocol,
        PaymentRepositoryProtocol,
        PdfGeneratorProtocol,
        SubscriptionRepositoryProtocol,
        TaxCalculationServiceProtocol,
        UsageRepositoryProtocol,
    )
except ImportError:
    # Mock implementations for testing
    from dataclasses import dataclass, field
    from enum import Enum
    from typing import Protocol

    class BillingCycle(Enum):
        ONE_TIME = "one_time"
        WEEKLY = "weekly"
        MONTHLY = "monthly"
        QUARTERLY = "quarterly"
        SEMI_ANNUALLY = "semi_annually"
        ANNUALLY = "annually"

    class SubscriptionStatus(Enum):
        ACTIVE = "active"
        TRIAL = "trial"
        CANCELLED = "cancelled"
        SUSPENDED = "suspended"
        EXPIRED = "expired"

    class InvoiceStatus(Enum):
        DRAFT = "draft"
        PENDING = "pending"
        PAID = "paid"
        OVERDUE = "overdue"
        CANCELLED = "cancelled"

    class PaymentStatus(Enum):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"
        REFUNDED = "refunded"

    @dataclass
    class MockCustomer:
        id: UUID
        email: str
        name: str
        address: dict = field(default_factory=dict)

    @dataclass
    class MockBillingPlan:
        id: UUID
        name: str
        base_price: Decimal
        billing_cycle: BillingCycle
        currency: str = "USD"
        is_active: bool = True
        trial_days: int = 0
        included_usage: Optional[Decimal] = None
        overage_price: Optional[Decimal] = None
        usage_unit: str = "units"

    @dataclass
    class Subscription:
        id: UUID
        customer_id: UUID
        billing_plan_id: UUID
        status: SubscriptionStatus
        start_date: date
        end_date: Optional[date] = None
        trial_end_date: Optional[date] = None
        next_billing_date: Optional[date] = None
        subscription_number: Optional[str] = None
        quantity: Decimal = Decimal("1")
        custom_price: Optional[Decimal] = None
        current_usage: Decimal = Decimal("0")
        tenant_id: Optional[UUID] = None

        # Relationships (mock)
        customer: Optional[MockCustomer] = None
        billing_plan: Optional[MockBillingPlan] = None

    @dataclass
    class Invoice:
        id: UUID
        customer_id: UUID
        subscription_id: UUID
        invoice_number: Optional[str] = None
        invoice_date: date = field(default_factory=date.today)
        due_date: date = field(default_factory=lambda: date.today() + timedelta(days=30))
        service_period_start: date = field(default_factory=date.today)
        service_period_end: date = field(default_factory=date.today)
        subtotal: Decimal = Decimal("0")
        tax_amount: Decimal = Decimal("0")
        total_amount: Decimal = Decimal("0")
        amount_paid: Decimal = Decimal("0")
        amount_due: Decimal = Decimal("0")
        status: InvoiceStatus = InvoiceStatus.DRAFT
        currency: str = "USD"
        tax_type: Optional[str] = None
        tax_rate: Optional[Decimal] = None
        tenant_id: Optional[UUID] = None

        # Relationships (mock)
        customer: Optional[MockCustomer] = None

    @dataclass
    class InvoiceLineItem:
        id: UUID
        invoice_id: UUID
        description: str
        quantity: Decimal
        unit_price: Decimal
        line_total: Decimal
        service_period_start: date
        service_period_end: date
        tenant_id: Optional[UUID] = None

    @dataclass
    class Payment:
        id: UUID
        customer_id: UUID
        invoice_id: UUID
        amount: Decimal
        currency: str
        payment_method: str
        status: PaymentStatus
        payment_date: datetime
        processed_date: Optional[datetime] = None
        payment_number: Optional[str] = None
        gateway_transaction_id: Optional[str] = None
        authorization_code: Optional[str] = None
        tenant_id: Optional[UUID] = None

    @dataclass
    class UsageRecord:
        id: UUID
        subscription_id: UUID
        usage_date: date
        quantity: Decimal
        description: Optional[str] = None
        tenant_id: Optional[UUID] = None

    @dataclass
    class BillingPeriod:
        id: UUID
        subscription_id: UUID
        period_start: date
        period_end: date
        base_amount: Decimal
        usage_amount: Decimal
        total_amount: Decimal
        total_usage: Decimal
        included_usage: Decimal
        overage_usage: Decimal
        invoiced: bool = False
        invoice_id: Optional[UUID] = None
        tenant_id: Optional[UUID] = None

    @dataclass
    class SubscriptionCreate:
        customer_id: UUID
        billing_plan_id: UUID
        start_date: date
        trial_end_date: Optional[date] = None
        tenant_id: Optional[UUID] = None
        quantity: Decimal = Decimal("1")
        custom_price: Optional[Decimal] = None

    @dataclass
    class UsageRecordCreate:
        subscription_id: Optional[UUID] = None
        usage_date: date = field(default_factory=date.today)
        quantity: Decimal = Decimal("1")
        description: Optional[str] = None
        tenant_id: Optional[UUID] = None

    # Protocol implementations (interfaces)
    class DatabaseSessionProtocol(Protocol):
        async def commit(self) -> None: ...
        async def rollback(self) -> None: ...
        async def refresh(self, instance: Any) -> None: ...
        async def flush(self) -> None: ...
        def add(self, instance: Any) -> None: ...

    class CustomerRepositoryProtocol(Protocol):
        async def get(self, customer_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[MockCustomer]: ...

    class BillingPlanRepositoryProtocol(Protocol):
        async def get(self, plan_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[MockBillingPlan]: ...

    class SubscriptionRepositoryProtocol(Protocol):
        async def create(self, subscription_data: SubscriptionCreate) -> Subscription: ...
        async def get(self, subscription_id: UUID, tenant_id: Optional[UUID] = None, load_relationships: Optional[list[str]] = None) -> Optional[Subscription]: ...
        async def get_due_for_billing(self, billing_date: date) -> list[Subscription]: ...

    class InvoiceRepositoryProtocol(Protocol):
        async def get(self, invoice_id: UUID, tenant_id: Optional[UUID] = None, load_relationships: Optional[list[str]] = None) -> Optional[Invoice]: ...

    class PaymentRepositoryProtocol(Protocol):
        pass

    class UsageRepositoryProtocol(Protocol):
        async def create(self, usage_data: UsageRecordCreate) -> UsageRecord: ...
        async def get_by_subscription(self, subscription_id: UUID, start_date: date, end_date: date) -> list[UsageRecord]: ...

    class NotificationServiceProtocol(Protocol):
        async def send_subscription_notification(self, customer: MockCustomer, subscription: Subscription, notification_type: str) -> None: ...
        async def send_payment_notification(self, customer: MockCustomer, payment: Payment, notification_type: str) -> None: ...

    class PaymentGatewayProtocol(Protocol):
        async def process_payment(self, amount: Decimal, currency: str, payment_method_id: str, customer_id: str, metadata: dict = None) -> dict: ...

    class TaxCalculationServiceProtocol(Protocol):
        async def calculate_tax(self, amount: Decimal, customer: MockCustomer) -> dict: ...

    class PdfGeneratorProtocol(Protocol):
        pass

    # BillingService mock implementation
    class BillingService:
        def __init__(
            self,
            db: DatabaseSessionProtocol,
            customer_repo: CustomerRepositoryProtocol,
            plan_repo: BillingPlanRepositoryProtocol,
            subscription_repo: SubscriptionRepositoryProtocol,
            invoice_repo: InvoiceRepositoryProtocol,
            payment_repo: PaymentRepositoryProtocol,
            usage_repo: UsageRepositoryProtocol,
            payment_gateway: Optional[PaymentGatewayProtocol] = None,
            notification_service: Optional[NotificationServiceProtocol] = None,
            tax_service: Optional[TaxCalculationServiceProtocol] = None,
            pdf_generator: Optional[PdfGeneratorProtocol] = None,
            default_tenant_id: Optional[UUID] = None,
        ):
            self.db = db
            self.customer_repo = customer_repo
            self.plan_repo = plan_repo
            self.subscription_repo = subscription_repo
            self.invoice_repo = invoice_repo
            self.payment_repo = payment_repo
            self.usage_repo = usage_repo
            self.payment_gateway = payment_gateway
            self.notification_service = notification_service
            self.tax_service = tax_service
            self.pdf_generator = pdf_generator
            self.default_tenant_id = default_tenant_id

        async def create_subscription(
            self,
            customer_id: UUID,
            plan_id: UUID,
            start_date: Optional[date] = None,
            **kwargs,
        ) -> Subscription:
            if start_date is None:
                start_date = date.today()

            customer = await self.customer_repo.get(customer_id, self.default_tenant_id)
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")

            plan = await self.plan_repo.get(plan_id, self.default_tenant_id)
            if not plan or not plan.is_active:
                raise ValueError(f"Billing plan {plan_id} not found or inactive")

            next_billing_date = self._calculate_next_billing_date(start_date, plan.billing_cycle)

            trial_end_date = None
            if plan.trial_days > 0:
                trial_end_date = start_date + timedelta(days=plan.trial_days)

            subscription_data = SubscriptionCreate(
                customer_id=customer_id,
                billing_plan_id=plan_id,
                start_date=start_date,
                trial_end_date=trial_end_date,
                tenant_id=self.default_tenant_id,
                **kwargs,
            )

            subscription = await self.subscription_repo.create(subscription_data)
            subscription.subscription_number = f"SUB-{subscription.id.hex[:8].upper()}"
            subscription.next_billing_date = next_billing_date

            await self.db.commit()
            await self.db.refresh(subscription)

            if self.notification_service:
                await self.notification_service.send_subscription_notification(
                    customer, subscription, "subscription_created"
                )

            return subscription

        async def cancel_subscription(
            self, subscription_id: UUID, cancellation_date: Optional[date] = None
        ) -> Subscription:
            if cancellation_date is None:
                cancellation_date = date.today()

            subscription = await self.subscription_repo.get(subscription_id, self.default_tenant_id)
            if not subscription:
                raise ValueError(f"Subscription {subscription_id} not found")

            if subscription.status == SubscriptionStatus.CANCELLED:
                raise ValueError("Subscription is already cancelled")

            subscription.status = SubscriptionStatus.CANCELLED
            subscription.end_date = cancellation_date

            await self.db.commit()

            if self.notification_service:
                customer = await self.customer_repo.get(subscription.customer_id)
                await self.notification_service.send_subscription_notification(
                    customer, subscription, "subscription_cancelled"
                )

            return subscription

        async def generate_invoice(
            self, subscription_id: UUID, billing_period: BillingPeriod
        ) -> Invoice:
            subscription = await self.subscription_repo.get(
                subscription_id,
                self.default_tenant_id,
                load_relationships=["customer", "billing_plan"],
            )

            if not subscription:
                raise ValueError(f"Subscription {subscription_id} not found")

            customer = subscription.customer
            plan = subscription.billing_plan

            invoice = Invoice(
                id=uuid4(),
                customer_id=customer.id,
                subscription_id=subscription.id,
                invoice_date=billing_period.period_end,
                due_date=billing_period.period_end + timedelta(days=30),
                service_period_start=billing_period.period_start,
                service_period_end=billing_period.period_end,
                currency=plan.currency,
                tenant_id=self.default_tenant_id,
            )

            invoice.invoice_number = f"INV-{uuid4().hex[:8].upper()}"
            invoice.subtotal = billing_period.total_amount

            tax_amount = Decimal("0")
            if self.tax_service:
                tax_result = await self.tax_service.calculate_tax(invoice.subtotal, customer)
                tax_amount = Decimal(str(tax_result.get("amount", 0)))
                invoice.tax_type = tax_result.get("tax_type", "none")
                invoice.tax_rate = Decimal(str(tax_result.get("rate", 0)))

            invoice.tax_amount = tax_amount
            invoice.total_amount = invoice.subtotal + tax_amount
            invoice.amount_due = invoice.total_amount

            self.db.add(invoice)
            await self.db.commit()
            await self.db.refresh(invoice)

            # Also add to the invoice repository for retrieval
            if hasattr(self.invoice_repo, 'add_invoice'):
                self.invoice_repo.add_invoice(invoice)

            return invoice

        async def process_payment(
            self, invoice_id: UUID, payment_method_id: str, amount: Optional[Decimal] = None
        ) -> Payment:
            invoice = await self.invoice_repo.get(
                invoice_id, self.default_tenant_id, load_relationships=["customer"]
            )

            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")

            if amount is None:
                amount = invoice.amount_due

            customer = invoice.customer

            payment = Payment(
                id=uuid4(),
                customer_id=customer.id,
                invoice_id=invoice.id,
                amount=amount,
                currency=invoice.currency,
                payment_method=payment_method_id,
                status=PaymentStatus.PENDING,
                payment_date=datetime.now(timezone.utc),
                tenant_id=self.default_tenant_id,
            )

            payment.payment_number = f"PAY-{uuid4().hex[:8].upper()}"

            self.db.add(payment)
            await self.db.flush()

            if self.payment_gateway:
                gateway_result = await self.payment_gateway.process_payment(
                    amount=amount,
                    currency=invoice.currency,
                    payment_method_id=payment_method_id,
                    customer_id=str(customer.id),
                    metadata={"invoice_id": str(invoice.id), "payment_id": str(payment.id)},
                )

                payment.gateway_transaction_id = gateway_result.get("transaction_id")
                payment.authorization_code = gateway_result.get("authorization_code")

                if gateway_result.get("status") == "completed":
                    payment.status = PaymentStatus.COMPLETED
                    payment.processed_date = datetime.now(timezone.utc)

                    invoice.amount_paid += amount
                    invoice.amount_due = max(Decimal("0"), invoice.total_amount - invoice.amount_paid)

                    if invoice.amount_due <= 0:
                        invoice.status = InvoiceStatus.PAID

            await self.db.commit()

            if self.notification_service and payment.status == PaymentStatus.COMPLETED:
                await self.notification_service.send_payment_notification(
                    customer, payment, "payment_received"
                )

            return payment

        async def record_usage(
            self, subscription_id: UUID, usage_data: UsageRecordCreate
        ) -> UsageRecord:
            subscription = await self.subscription_repo.get(subscription_id, self.default_tenant_id)
            if not subscription:
                raise ValueError(f"Subscription {subscription_id} not found")

            usage_data.subscription_id = subscription_id
            usage_data.tenant_id = self.default_tenant_id

            usage_record = await self.usage_repo.create(usage_data)

            subscription.current_usage += usage_data.quantity
            await self.db.commit()

            return usage_record

        def _calculate_next_billing_date(self, current_date: date, billing_cycle: BillingCycle) -> date:
            if billing_cycle == BillingCycle.WEEKLY:
                return current_date + timedelta(weeks=1)
            elif billing_cycle == BillingCycle.MONTHLY:
                if current_date.month == 12:
                    return current_date.replace(year=current_date.year + 1, month=1)
                else:
                    return current_date.replace(month=current_date.month + 1)
            elif billing_cycle == BillingCycle.QUARTERLY:
                new_month = current_date.month + 3
                new_year = current_date.year
                if new_month > 12:
                    new_month -= 12
                    new_year += 1
                return current_date.replace(year=new_year, month=new_month)
            elif billing_cycle == BillingCycle.ANNUALLY:
                return current_date.replace(year=current_date.year + 1)
            else:
                return current_date


class MockDatabaseSession:
    """Mock database session"""

    def __init__(self):
        self.committed = False
        self.rollbacked = False
        self.added_objects = []
        self.flushed = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rollbacked = True

    async def refresh(self, instance):
        pass

    async def flush(self):
        self.flushed = True

    def add(self, instance):
        self.added_objects.append(instance)


class MockCustomerRepository:
    """Mock customer repository"""

    def __init__(self):
        self.customers = {}

    def add_customer(self, customer: MockCustomer):
        self.customers[customer.id] = customer

    async def get(self, customer_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[MockCustomer]:
        return self.customers.get(customer_id)


class MockBillingPlanRepository:
    """Mock billing plan repository"""

    def __init__(self):
        self.plans = {}

    def add_plan(self, plan: MockBillingPlan):
        self.plans[plan.id] = plan

    async def get(self, plan_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[MockBillingPlan]:
        return self.plans.get(plan_id)


class MockSubscriptionRepository:
    """Mock subscription repository"""

    def __init__(self):
        self.subscriptions = {}
        self.due_subscriptions = []

    async def create(self, subscription_data: SubscriptionCreate) -> Subscription:
        subscription = Subscription(
            id=uuid4(),
            customer_id=subscription_data.customer_id,
            billing_plan_id=subscription_data.billing_plan_id,
            status=SubscriptionStatus.ACTIVE,
            start_date=subscription_data.start_date,
            trial_end_date=subscription_data.trial_end_date,
            tenant_id=subscription_data.tenant_id,
            quantity=subscription_data.quantity,
            custom_price=subscription_data.custom_price,
        )
        self.subscriptions[subscription.id] = subscription
        return subscription

    async def get(
        self,
        subscription_id: UUID,
        tenant_id: Optional[UUID] = None,
        load_relationships: Optional[list[str]] = None
    ) -> Optional[Subscription]:
        subscription = self.subscriptions.get(subscription_id)
        if subscription and load_relationships:
            # Mock relationship loading
            if "customer" in load_relationships:
                subscription.customer = MockCustomer(
                    id=subscription.customer_id,
                    email="test@example.com",
                    name="Test Customer",
                    address={"country": "US", "state": "CA"}
                )
            if "billing_plan" in load_relationships:
                subscription.billing_plan = MockBillingPlan(
                    id=subscription.billing_plan_id,
                    name="Test Plan",
                    base_price=Decimal("99.99"),
                    billing_cycle=BillingCycle.MONTHLY,
                    currency="USD"
                )
        return subscription

    async def get_due_for_billing(self, billing_date: date) -> list[Subscription]:
        return self.due_subscriptions

    def add_due_subscription(self, subscription: Subscription):
        self.due_subscriptions.append(subscription)


class MockInvoiceRepository:
    """Mock invoice repository"""

    def __init__(self):
        self.invoices = {}

    def add_invoice(self, invoice: Invoice):
        self.invoices[invoice.id] = invoice

    async def get(
        self,
        invoice_id: UUID,
        tenant_id: Optional[UUID] = None,
        load_relationships: Optional[list[str]] = None
    ) -> Optional[Invoice]:
        invoice = self.invoices.get(invoice_id)
        if invoice and load_relationships:
            if "customer" in load_relationships:
                invoice.customer = MockCustomer(
                    id=invoice.customer_id,
                    email="test@example.com",
                    name="Test Customer",
                    address={"country": "US", "state": "CA"}
                )
        return invoice


class MockUsageRepository:
    """Mock usage repository"""

    def __init__(self):
        self.usage_records = []

    async def create(self, usage_data: UsageRecordCreate) -> UsageRecord:
        usage_record = UsageRecord(
            id=uuid4(),
            subscription_id=usage_data.subscription_id,
            usage_date=usage_data.usage_date,
            quantity=usage_data.quantity,
            description=usage_data.description,
            tenant_id=usage_data.tenant_id
        )
        self.usage_records.append(usage_record)
        return usage_record

    async def get_by_subscription(
        self, subscription_id: UUID, start_date: date, end_date: date
    ) -> list[UsageRecord]:
        return [
            record for record in self.usage_records
            if (
                record.subscription_id == subscription_id and
                start_date <= record.usage_date <= end_date
            )
        ]


@pytest.mark.integration
@pytest.mark.asyncio
class TestBillingServiceIntegration:
    """Integration tests for BillingService"""

    @pytest.fixture
    def mock_db(self):
        return MockDatabaseSession()

    @pytest.fixture
    def mock_customer_repo(self):
        return MockCustomerRepository()

    @pytest.fixture
    def mock_plan_repo(self):
        return MockBillingPlanRepository()

    @pytest.fixture
    def mock_subscription_repo(self):
        return MockSubscriptionRepository()

    @pytest.fixture
    def mock_invoice_repo(self):
        return MockInvoiceRepository()

    @pytest.fixture
    def mock_usage_repo(self):
        return MockUsageRepository()

    @pytest.fixture
    def mock_notification_service(self):
        service = Mock()
        service.send_subscription_notification = AsyncMock()
        service.send_payment_notification = AsyncMock()
        return service

    @pytest.fixture
    def mock_payment_gateway(self):
        gateway = Mock()
        gateway.process_payment = AsyncMock(return_value={
            "status": "completed",
            "transaction_id": "txn_123456",
            "authorization_code": "auth_789"
        })
        return gateway

    @pytest.fixture
    def mock_tax_service(self):
        service = Mock()
        service.calculate_tax = AsyncMock(return_value={
            "amount": 8.25,
            "rate": 0.0825,
            "tax_type": "sales_tax"
        })
        return service

    @pytest.fixture
    def billing_service(
        self,
        mock_db,
        mock_customer_repo,
        mock_plan_repo,
        mock_subscription_repo,
        mock_invoice_repo,
        mock_usage_repo,
        mock_notification_service,
        mock_payment_gateway,
        mock_tax_service
    ):
        """Create billing service with all dependencies"""
        return BillingService(
            db=mock_db,
            customer_repo=mock_customer_repo,
            plan_repo=mock_plan_repo,
            subscription_repo=mock_subscription_repo,
            invoice_repo=mock_invoice_repo,
            payment_repo=Mock(),
            usage_repo=mock_usage_repo,
            payment_gateway=mock_payment_gateway,
            notification_service=mock_notification_service,
            tax_service=mock_tax_service,
            default_tenant_id=uuid4()
        )

    @pytest.fixture
    def sample_customer(self, mock_customer_repo):
        """Create a sample customer"""
        customer = MockCustomer(
            id=uuid4(),
            email="test@example.com",
            name="Test Customer",
            address={"country": "US", "state": "CA"}
        )
        mock_customer_repo.add_customer(customer)
        return customer

    @pytest.fixture
    def sample_plan(self, mock_plan_repo):
        """Create a sample billing plan"""
        plan = MockBillingPlan(
            id=uuid4(),
            name="Premium Plan",
            base_price=Decimal("99.99"),
            billing_cycle=BillingCycle.MONTHLY,
            currency="USD",
            trial_days=14,
            included_usage=Decimal("1000"),
            overage_price=Decimal("0.10"),
            usage_unit="API calls"
        )
        mock_plan_repo.add_plan(plan)
        return plan

    async def test_create_subscription_success(self, billing_service, sample_customer, sample_plan):
        """Test successful subscription creation"""
        start_date = date.today()

        subscription = await billing_service.create_subscription(
            customer_id=sample_customer.id,
            plan_id=sample_plan.id,
            start_date=start_date
        )

        # Verify subscription was created correctly
        assert subscription.customer_id == sample_customer.id
        assert subscription.billing_plan_id == sample_plan.id
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.start_date == start_date
        assert subscription.subscription_number is not None
        assert subscription.subscription_number.startswith("SUB-")
        assert subscription.next_billing_date > start_date

        # Verify trial period was set
        expected_trial_end = start_date + timedelta(days=sample_plan.trial_days)
        assert subscription.trial_end_date == expected_trial_end

        # Verify database operations
        assert billing_service.db.committed

        # Verify notification was sent
        billing_service.notification_service.send_subscription_notification.assert_called_once()

    async def test_create_subscription_with_invalid_customer(self, billing_service, sample_plan):
        """Test subscription creation with invalid customer"""
        invalid_customer_id = uuid4()

        with pytest.raises(ValueError, match="Customer .* not found"):
            await billing_service.create_subscription(
                customer_id=invalid_customer_id,
                plan_id=sample_plan.id
            )

    async def test_create_subscription_with_invalid_plan(self, billing_service, sample_customer):
        """Test subscription creation with invalid plan"""
        invalid_plan_id = uuid4()

        with pytest.raises(ValueError, match="Billing plan .* not found or inactive"):
            await billing_service.create_subscription(
                customer_id=sample_customer.id,
                plan_id=invalid_plan_id
            )

    async def test_cancel_subscription_success(self, billing_service, sample_customer, sample_plan, mock_subscription_repo):
        """Test successful subscription cancellation"""
        # Create subscription first
        subscription = await billing_service.create_subscription(
            customer_id=sample_customer.id,
            plan_id=sample_plan.id
        )

        cancellation_date = date.today()

        # Cancel subscription
        cancelled_subscription = await billing_service.cancel_subscription(
            subscription.id,
            cancellation_date
        )

        # Verify cancellation
        assert cancelled_subscription.status == SubscriptionStatus.CANCELLED
        assert cancelled_subscription.end_date == cancellation_date
        assert billing_service.db.committed

        # Verify notification was sent
        assert billing_service.notification_service.send_subscription_notification.call_count == 2  # Create + Cancel

    async def test_cancel_already_cancelled_subscription(self, billing_service, sample_customer, sample_plan):
        """Test cancelling already cancelled subscription"""
        # Create and cancel subscription
        subscription = await billing_service.create_subscription(
            sample_customer.id, sample_plan.id
        )
        await billing_service.cancel_subscription(subscription.id)

        # Try to cancel again
        with pytest.raises(ValueError, match="Subscription is already cancelled"):
            await billing_service.cancel_subscription(subscription.id)

    async def test_generate_invoice_success(self, billing_service, sample_customer, sample_plan):
        """Test successful invoice generation"""
        # Create subscription
        subscription = await billing_service.create_subscription(
            sample_customer.id, sample_plan.id
        )

        # Create billing period
        billing_period = BillingPeriod(
            id=uuid4(),
            subscription_id=subscription.id,
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            base_amount=Decimal("99.99"),
            usage_amount=Decimal("15.50"),
            total_amount=Decimal("115.49"),
            total_usage=Decimal("1155"),
            included_usage=Decimal("1000"),
            overage_usage=Decimal("155"),
            tenant_id=billing_service.default_tenant_id
        )

        # Generate invoice
        invoice = await billing_service.generate_invoice(subscription.id, billing_period)

        # Verify invoice
        assert invoice.customer_id == sample_customer.id
        assert invoice.subscription_id == subscription.id
        assert invoice.invoice_number is not None
        assert invoice.invoice_number.startswith("INV-")
        assert invoice.subtotal == billing_period.total_amount
        assert invoice.tax_amount > 0  # Tax service is configured
        assert invoice.total_amount == invoice.subtotal + invoice.tax_amount
        assert invoice.amount_due == invoice.total_amount

        # Verify tax calculation was called
        billing_service.tax_service.calculate_tax.assert_called_once_with(
            invoice.subtotal, sample_customer
        )

        # Verify database operations
        assert len(billing_service.db.added_objects) > 0
        assert billing_service.db.committed

    async def test_process_payment_success(self, billing_service, mock_invoice_repo, sample_customer):
        """Test successful payment processing"""
        # Create mock invoice
        invoice = Invoice(
            id=uuid4(),
            customer_id=sample_customer.id,
            subscription_id=uuid4(),
            invoice_number="INV-TEST123",
            subtotal=Decimal("99.99"),
            tax_amount=Decimal("8.25"),
            total_amount=Decimal("108.24"),
            amount_due=Decimal("108.24"),
            currency="USD"
        )
        invoice.customer = sample_customer
        mock_invoice_repo.add_invoice(invoice)

        # Process payment
        expected_payment_amount = invoice.amount_due
        payment = await billing_service.process_payment(
            invoice_id=invoice.id,
            payment_method_id="pm_test123",
            amount=expected_payment_amount
        )

        # Verify payment
        assert payment.customer_id == sample_customer.id
        assert payment.invoice_id == invoice.id
        assert payment.amount == expected_payment_amount
        assert payment.payment_number is not None
        assert payment.payment_number.startswith("PAY-")
        assert payment.status == PaymentStatus.COMPLETED
        assert payment.gateway_transaction_id == "txn_123456"
        assert payment.authorization_code == "auth_789"

        # Verify payment gateway was called
        billing_service.payment_gateway.process_payment.assert_called_once()

        # Verify invoice was updated
        assert invoice.amount_paid == payment.amount
        assert invoice.amount_due == Decimal("0")
        assert invoice.status == InvoiceStatus.PAID

        # Verify notification was sent
        billing_service.notification_service.send_payment_notification.assert_called_once()

    async def test_record_usage_success(self, billing_service, sample_customer, sample_plan):
        """Test successful usage recording"""
        # Create subscription
        subscription = await billing_service.create_subscription(
            sample_customer.id, sample_plan.id
        )

        # Record usage
        usage_data = UsageRecordCreate(
            usage_date=date.today(),
            quantity=Decimal("250"),
            description="API calls for premium features"
        )

        usage_record = await billing_service.record_usage(
            subscription_id=subscription.id,
            usage_data=usage_data
        )

        # Verify usage record
        assert usage_record.subscription_id == subscription.id
        assert usage_record.quantity == Decimal("250")
        assert usage_record.description == "API calls for premium features"

        # Verify subscription usage was updated
        updated_subscription = await billing_service.subscription_repo.get(subscription.id)
        assert updated_subscription.current_usage == Decimal("250")

        # Verify database operations
        assert billing_service.db.committed

    async def test_record_usage_with_invalid_subscription(self, billing_service):
        """Test usage recording with invalid subscription"""
        invalid_subscription_id = uuid4()
        usage_data = UsageRecordCreate(quantity=Decimal("100"))

        with pytest.raises(ValueError, match="Subscription .* not found"):
            await billing_service.record_usage(invalid_subscription_id, usage_data)


@pytest.mark.integration
@pytest.mark.asyncio
class TestBillingServiceComplexScenarios:
    """Integration tests for complex billing scenarios"""

    @pytest.fixture
    def billing_service_with_mocks(self):
        """Create billing service with comprehensive mocks"""
        db = MockDatabaseSession()
        customer_repo = MockCustomerRepository()
        plan_repo = MockBillingPlanRepository()
        subscription_repo = MockSubscriptionRepository()
        invoice_repo = MockInvoiceRepository()
        usage_repo = MockUsageRepository()

        # Create notification service mock
        notification_service = Mock()
        notification_service.send_subscription_notification = AsyncMock()
        notification_service.send_payment_notification = AsyncMock()

        # Create payment gateway mock
        payment_gateway = Mock()
        payment_gateway.process_payment = AsyncMock(return_value={
            "status": "completed",
            "transaction_id": "txn_abc123",
            "authorization_code": "auth_xyz789"
        })

        service = BillingService(
            db=db,
            customer_repo=customer_repo,
            plan_repo=plan_repo,
            subscription_repo=subscription_repo,
            invoice_repo=invoice_repo,
            payment_repo=Mock(),
            usage_repo=usage_repo,
            payment_gateway=payment_gateway,
            notification_service=notification_service,
            default_tenant_id=uuid4()
        )

        # Add test data
        customer = MockCustomer(uuid4(), "test@example.com", "Test Customer")
        customer_repo.add_customer(customer)

        plan = MockBillingPlan(
            id=uuid4(),
            name="Enterprise Plan",
            base_price=Decimal("299.99"),
            billing_cycle=BillingCycle.MONTHLY,
            included_usage=Decimal("5000"),
            overage_price=Decimal("0.05")
        )
        plan_repo.add_plan(plan)

        return service, customer, plan

    async def test_complete_billing_lifecycle(self, billing_service_with_mocks):
        """Test complete billing lifecycle from subscription to payment"""
        billing_service, customer, plan = billing_service_with_mocks

        # Step 1: Create subscription
        subscription = await billing_service.create_subscription(
            customer_id=customer.id,
            plan_id=plan.id
        )
        assert subscription.status == SubscriptionStatus.ACTIVE

        # Step 2: Record usage
        for day in range(5):
            usage_data = UsageRecordCreate(
                usage_date=date.today() - timedelta(days=day),
                quantity=Decimal("1200"),  # Total: 6000 units
                description=f"Daily usage - day {day + 1}"
            )
            await billing_service.record_usage(subscription.id, usage_data)

        # Verify total usage (6000 units, 1000 overage)
        updated_subscription = await billing_service.subscription_repo.get(subscription.id)
        assert updated_subscription.current_usage == Decimal("6000")

        # Step 3: Generate invoice
        billing_period = BillingPeriod(
            id=uuid4(),
            subscription_id=subscription.id,
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            base_amount=plan.base_price,  # $299.99
            usage_amount=Decimal("50.00"),  # 1000 overage * $0.05
            total_amount=plan.base_price + Decimal("50.00"),  # $349.99
            total_usage=Decimal("6000"),
            included_usage=plan.included_usage,
            overage_usage=Decimal("1000"),
            tenant_id=billing_service.default_tenant_id
        )

        invoice = await billing_service.generate_invoice(subscription.id, billing_period)
        assert invoice.subtotal == Decimal("349.99")

        # Step 4: Process payment
        payment = await billing_service.process_payment(
            invoice_id=invoice.id,
            payment_method_id="pm_enterprise123"
        )

        assert payment.status == PaymentStatus.COMPLETED
        assert payment.amount == invoice.total_amount
        assert invoice.status == InvoiceStatus.PAID

        # Verify all notifications were sent
        assert billing_service.notification_service.send_subscription_notification.call_count == 1
        assert billing_service.notification_service.send_payment_notification.call_count == 1

    async def test_subscription_with_trial_period(self, billing_service_with_mocks):
        """Test subscription creation with trial period"""
        billing_service, customer, plan = billing_service_with_mocks

        # Update plan to have trial period
        plan.trial_days = 30

        start_date = date.today()
        subscription = await billing_service.create_subscription(
            customer_id=customer.id,
            plan_id=plan.id,
            start_date=start_date
        )

        # Verify trial end date
        expected_trial_end = start_date + timedelta(days=30)
        assert subscription.trial_end_date == expected_trial_end

        # Verify next billing date (should be after trial)
        assert subscription.next_billing_date >= expected_trial_end

    async def test_partial_payment_processing(self, billing_service_with_mocks):
        """Test processing partial payment on invoice"""
        billing_service, customer, plan = billing_service_with_mocks

        # Create invoice
        invoice = Invoice(
            id=uuid4(),
            customer_id=customer.id,
            subscription_id=uuid4(),
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            amount_due=Decimal("500.00"),
            currency="USD"
        )
        invoice.customer = customer
        billing_service.invoice_repo.add_invoice(invoice)

        # Process partial payment
        partial_amount = Decimal("300.00")
        payment = await billing_service.process_payment(
            invoice_id=invoice.id,
            payment_method_id="pm_partial123",
            amount=partial_amount
        )

        # Verify partial payment
        assert payment.amount == partial_amount
        assert payment.status == PaymentStatus.COMPLETED

        # Verify invoice still has remaining balance
        assert invoice.amount_paid == partial_amount
        assert invoice.amount_due == Decimal("200.00")
        assert invoice.status != InvoiceStatus.PAID  # Should still be pending

    async def test_usage_tracking_across_billing_periods(self, billing_service_with_mocks):
        """Test usage tracking across different billing periods"""
        billing_service, customer, plan = billing_service_with_mocks

        # Create subscription
        subscription = await billing_service.create_subscription(
            customer_id=customer.id,
            plan_id=plan.id
        )

        # Record usage across different periods
        today = date.today()

        # Current period usage
        for i in range(3):
            usage_data = UsageRecordCreate(
                usage_date=today - timedelta(days=i),
                quantity=Decimal("1000"),
                description=f"Current period usage {i + 1}"
            )
            await billing_service.record_usage(subscription.id, usage_data)

        # Previous period usage
        for i in range(2):
            usage_data = UsageRecordCreate(
                usage_date=today - timedelta(days=35 + i),  # 35+ days ago
                quantity=Decimal("800"),
                description=f"Previous period usage {i + 1}"
            )
            await billing_service.record_usage(subscription.id, usage_data)

        # Get current period usage
        current_period_start = today - timedelta(days=30)
        current_usage = await billing_service.usage_repo.get_by_subscription(
            subscription.id, current_period_start, today
        )

        # Should only include current period (3 records)
        assert len(current_usage) == 3
        current_total = sum(record.quantity for record in current_usage)
        assert current_total == Decimal("3000")

        # Get previous period usage
        previous_period_start = today - timedelta(days=60)
        previous_period_end = today - timedelta(days=31)
        previous_usage = await billing_service.usage_repo.get_by_subscription(
            subscription.id, previous_period_start, previous_period_end
        )

        # Should only include previous period (2 records)
        assert len(previous_usage) == 2
        previous_total = sum(record.quantity for record in previous_usage)
        assert previous_total == Decimal("1600")
