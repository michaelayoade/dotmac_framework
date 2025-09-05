"""
Service protocols for the DotMac Billing Package.

These protocols define the interfaces that billing services must implement,
allowing for platform-specific customization while maintaining consistency.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Generic, Optional, Protocol, TypeVar
from uuid import UUID

from ..core.models import (
    BillingPeriod,
    BillingPlan,
    Customer,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentStatus,
    Subscription,
    UsageRecord,
)
from ..schemas.billing_schemas import (
    BillingPlanCreate,
    BillingPlanUpdate,
    CustomerCreate,
    CustomerUpdate,
    InvoiceCreate,
    PaymentCreate,
    SubscriptionCreate,
    SubscriptionUpdate,
    UsageRecordCreate,
)

# Generic types for repository operations
T = TypeVar("T")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class DatabaseSessionProtocol(Protocol):
    """Protocol for database session objects."""

    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        ...

    async def refresh(self, instance: Any) -> None:
        """Refresh an instance from the database."""
        ...


class BaseRepositoryProtocol(Protocol, Generic[T, CreateSchemaType, UpdateSchemaType]):
    """Base protocol for repository operations."""

    async def create(self, obj_in: CreateSchemaType, **kwargs) -> T:
        """Create a new record."""
        ...

    async def get(self, id: UUID) -> Optional[T]:
        """Get a record by ID."""
        ...

    async def get_multi(self, *, skip: int = 0, limit: int = 100, **filters) -> list[T]:
        """Get multiple records with pagination and filters."""
        ...

    async def update(self, db_obj: T, obj_in: UpdateSchemaType) -> T:
        """Update a record."""
        ...

    async def delete(self, id: UUID) -> bool:
        """Delete a record by ID."""
        ...

    async def count(self, **filters) -> int:
        """Count records with optional filters."""
        ...


class CustomerRepositoryProtocol(
    BaseRepositoryProtocol[Customer, CustomerCreate, CustomerUpdate], Protocol
):
    """Protocol for customer repository operations."""

    async def get_by_email(
        self, email: str, tenant_id: Optional[UUID] = None
    ) -> Optional[Customer]:
        """Get customer by email address."""
        ...

    async def get_by_customer_code(
        self, customer_code: str, tenant_id: Optional[UUID] = None
    ) -> Optional[Customer]:
        """Get customer by customer code."""
        ...

    async def get_active_customers(
        self, tenant_id: Optional[UUID] = None
    ) -> list[Customer]:
        """Get all active customers."""
        ...


class BillingPlanRepositoryProtocol(
    BaseRepositoryProtocol[BillingPlan, BillingPlanCreate, BillingPlanUpdate], Protocol
):
    """Protocol for billing plan repository operations."""

    async def get_by_plan_code(
        self, plan_code: str, tenant_id: Optional[UUID] = None
    ) -> Optional[BillingPlan]:
        """Get billing plan by plan code."""
        ...

    async def get_active_plans(
        self, tenant_id: Optional[UUID] = None
    ) -> list[BillingPlan]:
        """Get all active billing plans."""
        ...

    async def get_public_plans(
        self, tenant_id: Optional[UUID] = None
    ) -> list[BillingPlan]:
        """Get all public billing plans."""
        ...


class SubscriptionRepositoryProtocol(
    BaseRepositoryProtocol[Subscription, SubscriptionCreate, SubscriptionUpdate],
    Protocol,
):
    """Protocol for subscription repository operations."""

    async def get_by_customer(self, customer_id: UUID) -> list[Subscription]:
        """Get all subscriptions for a customer."""
        ...

    async def get_active_subscriptions(
        self, tenant_id: Optional[UUID] = None
    ) -> list[Subscription]:
        """Get all active subscriptions."""
        ...

    async def get_due_for_billing(self, date: Optional[date] = None) -> list[Subscription]:
        """Get subscriptions due for billing on a specific date."""
        ...

    async def get_by_subscription_number(
        self, subscription_number: str, tenant_id: Optional[UUID] = None
    ) -> Optional[Subscription]:
        """Get subscription by subscription number."""
        ...


class InvoiceRepositoryProtocol(
    BaseRepositoryProtocol[Invoice, InvoiceCreate, Any], Protocol
):
    """Protocol for invoice repository operations."""

    async def get_by_customer(self, customer_id: UUID) -> list[Invoice]:
        """Get all invoices for a customer."""
        ...

    async def get_by_subscription(self, subscription_id: UUID) -> list[Invoice]:
        """Get all invoices for a subscription."""
        ...

    async def get_by_status(
        self, status: InvoiceStatus, tenant_id: Optional[UUID] = None
    ) -> list[Invoice]:
        """Get invoices by status."""
        ...

    async def get_overdue_invoices(
        self, tenant_id: Optional[UUID] = None
    ) -> list[Invoice]:
        """Get all overdue invoices."""
        ...

    async def get_by_invoice_number(
        self, invoice_number: str, tenant_id: Optional[UUID] = None
    ) -> Optional[Invoice]:
        """Get invoice by invoice number."""
        ...


class PaymentRepositoryProtocol(
    BaseRepositoryProtocol[Payment, PaymentCreate, Any], Protocol
):
    """Protocol for payment repository operations."""

    async def get_by_customer(self, customer_id: UUID) -> list[Payment]:
        """Get all payments for a customer."""
        ...

    async def get_by_invoice(self, invoice_id: UUID) -> list[Payment]:
        """Get all payments for an invoice."""
        ...

    async def get_by_status(
        self, status: PaymentStatus, tenant_id: Optional[UUID] = None
    ) -> list[Payment]:
        """Get payments by status."""
        ...


class UsageRepositoryProtocol(
    BaseRepositoryProtocol[UsageRecord, UsageRecordCreate, Any], Protocol
):
    """Protocol for usage record repository operations."""

    async def get_by_subscription(
        self,
        subscription_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[UsageRecord]:
        """Get usage records for a subscription within date range."""
        ...

    async def get_unprocessed_usage(
        self, tenant_id: Optional[UUID] = None
    ) -> list[UsageRecord]:
        """Get unprocessed usage records."""
        ...


class PaymentGatewayProtocol(Protocol):
    """Protocol for payment gateway integrations."""

    async def process_payment(
        self,
        amount: Decimal,
        currency: str,
        payment_method_id: str,
        customer_id: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Process a payment through the gateway."""
        ...

    async def refund_payment(
        self, transaction_id: str, amount: Optional[Decimal] = None
    ) -> dict[str, Any]:
        """Refund a payment."""
        ...

    async def get_payment_status(self, transaction_id: str) -> dict[str, Any]:
        """Get payment status from the gateway."""
        ...


class NotificationServiceProtocol(Protocol):
    """Protocol for notification services."""

    async def send_invoice_notification(
        self,
        customer: Customer,
        invoice: Invoice,
        notification_type: str = "invoice_created",
    ) -> bool:
        """Send invoice-related notification."""
        ...

    async def send_payment_notification(
        self,
        customer: Customer,
        payment: Payment,
        notification_type: str = "payment_received",
    ) -> bool:
        """Send payment-related notification."""
        ...

    async def send_subscription_notification(
        self,
        customer: Customer,
        subscription: Subscription,
        notification_type: str = "subscription_created",
    ) -> bool:
        """Send subscription-related notification."""
        ...


class TaxCalculationServiceProtocol(Protocol):
    """Protocol for tax calculation services."""

    async def calculate_tax(
        self,
        amount: Decimal,
        customer: Customer,
        product_codes: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Calculate tax for an amount and customer."""
        ...

    async def validate_tax_id(self, tax_id: str, country: str) -> bool:
        """Validate a tax ID for a specific country."""
        ...


class PdfGeneratorProtocol(Protocol):
    """Protocol for PDF generation services."""

    async def generate_invoice_pdf(
        self, invoice: Invoice, template_name: Optional[str] = None
    ) -> bytes:
        """Generate PDF for an invoice."""
        ...

    async def generate_statement_pdf(
        self, customer: Customer, start_date: date, end_date: date
    ) -> bytes:
        """Generate customer statement PDF."""
        ...


class BillingServiceProtocol(Protocol):
    """Main billing service protocol."""

    # Repository access
    customer_repo: CustomerRepositoryProtocol
    plan_repo: BillingPlanRepositoryProtocol
    subscription_repo: SubscriptionRepositoryProtocol
    invoice_repo: InvoiceRepositoryProtocol
    payment_repo: PaymentRepositoryProtocol
    usage_repo: UsageRepositoryProtocol

    # External services
    payment_gateway: Optional[PaymentGatewayProtocol]
    notification_service: Optional[NotificationServiceProtocol]
    tax_service: Optional[TaxCalculationServiceProtocol]
    pdf_generator: Optional[PdfGeneratorProtocol]

    # Core billing operations
    async def create_subscription(
        self,
        customer_id: UUID,
        plan_id: UUID,
        start_date: Optional[date] = None,
        **kwargs,
    ) -> Subscription:
        """Create a new subscription."""
        ...

    async def cancel_subscription(
        self, subscription_id: UUID, cancellation_date: Optional[date] = None
    ) -> Subscription:
        """Cancel a subscription."""
        ...

    async def generate_invoice(
        self, subscription_id: UUID, billing_period: BillingPeriod
    ) -> Invoice:
        """Generate invoice for a billing period."""
        ...

    async def process_payment(
        self, invoice_id: UUID, payment_method_id: str, amount: Optional[Decimal] = None
    ) -> Payment:
        """Process payment for an invoice."""
        ...

    async def record_usage(
        self, subscription_id: UUID, usage_data: UsageRecordCreate
    ) -> UsageRecord:
        """Record usage for a subscription."""
        ...

    async def run_billing_cycle(
        self, billing_date: Optional[date] = None, tenant_id: Optional[UUID] = None
    ) -> dict[str, Any]:
        """Run billing cycle for due subscriptions."""
        ...


class InvoiceServiceProtocol(Protocol):
    """Invoice-specific service protocol."""

    async def create_invoice(
        self, customer_id: UUID, line_items: list[dict[str, Any]], **kwargs
    ) -> Invoice:
        """Create a manual invoice."""
        ...

    async def finalize_invoice(self, invoice_id: UUID) -> Invoice:
        """Finalize a draft invoice."""
        ...

    async def send_invoice(self, invoice_id: UUID) -> bool:
        """Send invoice to customer."""
        ...

    async def void_invoice(self, invoice_id: UUID) -> Invoice:
        """Void an invoice."""
        ...


class PaymentServiceProtocol(Protocol):
    """Payment-specific service protocol."""

    async def create_payment(
        self, customer_id: UUID, amount: Decimal, payment_method: str, **kwargs
    ) -> Payment:
        """Create a payment record."""
        ...

    async def process_payment(self, payment_id: UUID) -> Payment:
        """Process a payment."""
        ...

    async def refund_payment(
        self, payment_id: UUID, amount: Optional[Decimal] = None
    ) -> Payment:
        """Refund a payment."""
        ...


class SubscriptionServiceProtocol(Protocol):
    """Subscription-specific service protocol."""

    async def create_subscription(
        self, customer_id: UUID, plan_id: UUID, **kwargs
    ) -> Subscription:
        """Create a subscription."""
        ...

    async def update_subscription(
        self, subscription_id: UUID, updates: dict[str, Any]
    ) -> Subscription:
        """Update subscription details."""
        ...

    async def change_plan(
        self,
        subscription_id: UUID,
        new_plan_id: UUID,
        change_date: Optional[date] = None,
    ) -> Subscription:
        """Change subscription plan."""
        ...


class BillingAnalyticsProtocol(Protocol):
    """Protocol for billing analytics and reporting."""

    async def get_revenue_metrics(
        self, start_date: date, end_date: date, tenant_id: Optional[UUID] = None
    ) -> dict[str, Any]:
        """Get revenue metrics for a period."""
        ...

    async def get_customer_metrics(
        self, tenant_id: Optional[UUID] = None
    ) -> dict[str, Any]:
        """Get customer analytics."""
        ...

    async def get_subscription_metrics(
        self, tenant_id: Optional[UUID] = None
    ) -> dict[str, Any]:
        """Get subscription analytics."""
        ...

    async def get_churn_analysis(
        self, start_date: date, end_date: date, tenant_id: Optional[UUID] = None
    ) -> dict[str, Any]:
        """Get customer churn analysis."""
        ...
