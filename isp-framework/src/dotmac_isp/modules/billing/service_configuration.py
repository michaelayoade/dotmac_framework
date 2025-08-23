"""Service configuration and registration for billing domain."""

from uuid import UUID
from sqlalchemy.orm import Session

from dotmac_isp.core.service_registry import get_service_registry, ServiceBoundary
from .domain.interfaces import (
    IInvoiceService,
    IPaymentService,
    IBillingCalculationService,
    ICreditNoteService,
    ISubscriptionService,
    IBillingNotificationService,
    IBillingReportService,
    IRecurringBillingService,
)
from .domain.invoice_service import InvoiceService
from .domain.payment_service import PaymentService
from .domain.calculation_service import BillingCalculationService
from .repository import (
    InvoiceRepository,
    InvoiceLineItemRepository,
    PaymentRepository,
    SubscriptionRepository,
    CreditNoteRepository,
)


def create_billing_calculation_service(
    db: Session, tenant_id: UUID
) -> IBillingCalculationService:
    """Factory for billing calculation service."""
    return BillingCalculationService()


def create_invoice_service(db: Session, tenant_id: UUID) -> IInvoiceService:
    """Factory for invoice service."""
    invoice_repo = InvoiceRepository(db, tenant_id)
    line_item_repo = InvoiceLineItemRepository(db, tenant_id)
    calculation_service = get_service_registry().get(
        IBillingCalculationService, db, tenant_id
    )

    return InvoiceService(
        invoice_repo=invoice_repo,
        line_item_repo=line_item_repo,
        calculation_service=calculation_service,
        tenant_id=tenant_id,
    )


def create_payment_service(db: Session, tenant_id: UUID) -> IPaymentService:
    """Factory for payment service."""
    payment_repo = PaymentRepository(db, tenant_id)
    invoice_repo = InvoiceRepository(db, tenant_id)

    return PaymentService(
        payment_repo=payment_repo, invoice_repo=invoice_repo, tenant_id=tenant_id
    )


def register_billing_services():
    """Register all billing domain services."""
    registry = get_service_registry()

    # Register core services
    registry.register(
        IBillingCalculationService, create_billing_calculation_service, singleton=True
    )

    registry.register(IInvoiceService, create_invoice_service)

    registry.register(IPaymentService, create_payment_service)


def configure_billing_service_boundaries():
    """Configure service boundaries for billing domain."""
    boundary = ServiceBoundary(get_service_registry())

    # Invoice service dependencies
    boundary.add_dependency(IInvoiceService, IBillingCalculationService)

    # Payment service dependencies
    boundary.add_dependency(IPaymentService, IInvoiceService)

    # Subscription service dependencies
    boundary.add_dependency(ISubscriptionService, IBillingCalculationService)
    boundary.add_dependency(ISubscriptionService, IInvoiceService)

    # Recurring billing service dependencies
    boundary.add_dependency(IRecurringBillingService, ISubscriptionService)
    boundary.add_dependency(IRecurringBillingService, IInvoiceService)

    # Report service dependencies
    boundary.add_dependency(IBillingReportService, IInvoiceService)
    boundary.add_dependency(IBillingReportService, IPaymentService)

    # Credit note service dependencies
    boundary.add_dependency(ICreditNoteService, IInvoiceService)

    return boundary


# Initialize billing services
def initialize_billing_services():
    """Initialize billing domain services and boundaries."""
    register_billing_services()
    return configure_billing_service_boundaries()
