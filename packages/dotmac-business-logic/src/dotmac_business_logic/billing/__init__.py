"""
DotMac Business Logic - Billing Package

Clean architecture billing system with dependency injection and
optional component support.

## Usage Examples

### Basic Setup with Dependency Injection

```python
from dotmac_business_logic.billing import BillingService
from dotmac_business_logic.billing.infra import SQLAlchemyBillingRepository
from dotmac_business_logic.billing.usage import BillingPeriodCalculator

# Create repository with your ORM models
repository = SQLAlchemyBillingRepository(
    session=db_session,
    customer_model=Customer,
    subscription_model=Subscription,
    invoice_model=Invoice,
    payment_model=Payment,
    usage_record_model=UsageRecord,
)

# Create service with injected dependencies
billing_service = BillingService(
    repository=repository,
    payment_gateway=stripe_gateway,
    tax_service=tax_calculator,
    usage_service=usage_aggregator,
)
```

### File Generation (Optional)

```python
from dotmac_business_logic.billing.files import (
    create_invoice_pdf,
    create_billing_report_excel,
    create_usage_report_csv,
)

# Generate PDF invoice (requires reportlab)
create_invoice_pdf(invoice_data, "invoice.pdf")

# Generate Excel report (requires openpyxl)
create_billing_report_excel(report_data, "report.xlsx")

# Generate CSV export (always available)
create_usage_report_csv(usage_data, "usage.csv")
```

### Currency Exchange (Optional)

```python
from dotmac_business_logic.billing.exchange import CurrencyConverter, ManualExchangeRateProvider

# Set up exchange rates
rate_provider = ManualExchangeRateProvider()
await rate_provider.set_rate("USD", "EUR", Decimal("0.85"))

# Convert currencies
converter = CurrencyConverter(rate_provider)
eur_amount = await converter.convert(Money(100, "USD"), "EUR")
```
"""

# Core domain exports
from .core import (  # Domain models and enums
    BillingCycle,
    BillingPeriod,
    BillingRepository,
    BillingService,
    InvoiceStatus,
    PaymentGateway,
    PaymentMethod,
    PaymentStatus,
    PricingModel,
    PricingTier,
    SubscriptionStatus,
    TaxService,
    TaxType,
    UsageService,
)

# Domain events
from .core.events import (
    InvoiceGenerated,
    PaymentFailed,
    PaymentProcessed,
    SubscriptionCancelled,
    SubscriptionCreated,
    SubscriptionRenewed,
    event_bus,
    publish_event,
)

# Infrastructure (for configuration)
from .infra import (
    BillingEntityMixin,
    SQLAlchemyBillingRepository,
)

# Usage and periods
from .usage import (
    BillingPeriodCalculator,
    TrialHandler,
    UsageAggregator,
    UsageRatingEngine,
)

# Optional components with graceful fallbacks
try:
    from .files import (
        create_billing_report_excel,
        create_invoice_pdf,
        create_usage_report_csv,
    )
    _FILES_AVAILABLE = True
except ImportError:
    _FILES_AVAILABLE = False

try:
    from .exchange import (
        CurrencyConverter,
        ManualExchangeRateProvider,
    )
    _EXCHANGE_AVAILABLE = True
except ImportError:
    _EXCHANGE_AVAILABLE = False

# Public API
__all__ = [
    # Core Services
    "BillingService",

    # Core Interfaces
    "BillingRepository",
    "PaymentGateway",
    "TaxService",
    "UsageService",

    # Domain Models
    "BillingCycle",
    "BillingPeriod",
    "InvoiceStatus",
    "PaymentMethod",
    "PaymentStatus",
    "PricingModel",
    "PricingTier",
    "SubscriptionStatus",
    "TaxType",

    # Domain Events
    "InvoiceGenerated",
    "PaymentProcessed",
    "PaymentFailed",
    "SubscriptionCreated",
    "SubscriptionCancelled",
    "SubscriptionRenewed",
    "publish_event",
    "event_bus",

    # Usage and Periods
    "BillingPeriodCalculator",
    "TrialHandler",
    "UsageAggregator",
    "UsageRatingEngine",

    # Infrastructure
    "BillingEntityMixin",
    "SQLAlchemyBillingRepository",
]

# Add optional exports if available
if _FILES_AVAILABLE:
    __all__.extend([
        "create_invoice_pdf",
        "create_billing_report_excel",
        "create_usage_report_csv",
    ])

if _EXCHANGE_AVAILABLE:
    __all__.extend([
        "CurrencyConverter",
        "ManualExchangeRateProvider",
    ])


# Module metadata
__version__ = "2.0.0-refactored"
__author__ = "DotMac Team"
__description__ = "Clean architecture billing system with dependency injection"
