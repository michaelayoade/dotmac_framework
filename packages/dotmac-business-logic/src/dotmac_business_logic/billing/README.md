# DotMac Billing Package

A comprehensive, reusable billing system for ISP and service provider applications. Designed for multi-tenant, scalable deployments with pluggable integrations.

## Features

- **Multi-tenant billing** with tenant isolation
- **Flexible pricing models** (flat rate, usage-based, tiered)
- **Subscription and one-time billing** support
- **Payment processing integration** with multiple gateways
- **Invoice generation and management**
- **Usage tracking and billing**
- **Revenue recognition and reporting**
- **Plugin architecture** for custom billing rules
- **Audit trail and compliance** features

## Quick Start

### Installation

```bash
pip install dotmac-billing
```

Or install from source:

```bash
cd /path/to/dotmac_shared/billing
pip install -e .
```

### Basic Usage

```python
from dotmac_shared.billing import BillingServiceFactory, create_basic_billing_service
from sqlalchemy.ext.asyncio import AsyncSession

# Create a basic billing service
async def setup_billing(db: AsyncSession):
    billing_service = create_basic_billing_service(db)

    # Create a customer
    customer_data = CustomerCreate(
        customer_code="CUST001",
        email="john@example.com",
        name="John Doe"
    )
    customer = await billing_service.customer_repo.create(customer_data)

    # Create a billing plan
    plan_data = BillingPlanCreate(
        plan_code="BASIC",
        name="Basic Plan",
        pricing_model=PricingModel.FLAT_RATE,
        base_price=29.99,
        billing_cycle=BillingCycle.MONTHLY
    )
    plan = await billing_service.plan_repo.create(plan_data)

    # Create a subscription
    subscription = await billing_service.create_subscription(
        customer_id=customer.id,
        plan_id=plan.id
    )

    return billing_service
```

### With Payment Gateway Integration

```python
from dotmac_shared.billing import create_stripe_billing_service

# Create billing service with Stripe integration
billing_service = create_stripe_billing_service(
    db=db_session,
    stripe_secret_key="sk_test_...",
    tenant_id=tenant_id
)

# Process payment for an invoice
payment = await billing_service.process_payment(
    invoice_id=invoice.id,
    payment_method_id="pm_1234567890",
    amount=invoice.amount_due
)
```

## Architecture

### Core Components

1. **Models** (`core/models.py`):
   - Customer, BillingPlan, Subscription, Invoice, Payment
   - UsageRecord, BillingPeriod, PricingTier
   - Multi-tenant support with `tenant_id` field

2. **Repositories** (`repositories/`):
   - Data access layer with async SQLAlchemy
   - Protocol-based interfaces for platform flexibility
   - Built-in filtering, pagination, and relationships

3. **Services** (`services/`):
   - Business logic implementation
   - Protocol-based architecture for extensibility
   - External service integrations (payment, notifications, etc.)

4. **Schemas** (`schemas/`):
   - Pydantic models for API requests/responses
   - Input validation and serialization
   - Type-safe data transfer objects

5. **Adapters** (`adapters/`):
   - Platform-specific integration helpers
   - Service factory for dependency injection
   - Configuration-driven service creation

### Protocol-Based Design

The package uses Python protocols to define interfaces, allowing for:

- **Platform Independence**: Works with any FastAPI/SQLAlchemy application
- **Testability**: Easy to mock dependencies for testing
- **Extensibility**: Plugin architecture for custom implementations
- **Type Safety**: Full type hints and protocol compliance checking

## Configuration

### Service Factory Configuration

```python
config = {
    "payment_gateway": {
        "type": "stripe",
        "options": {
            "secret_key": "sk_test_...",
            "webhook_secret": "whsec_..."
        }
    },
    "notifications": {
        "type": "email",
        "options": {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "username": "billing@example.com",
            "password": "password"
        }
    },
    "tax_calculation": {
        "type": "avalara",
        "options": {
            "account_id": "123456789",
            "license_key": "your-license-key"
        }
    },
    "pdf_generation": {
        "type": "reportlab",
        "options": {
            "template_dir": "/path/to/templates"
        }
    }
}

billing_service = billing_service_factory.create_billing_service(db, config, tenant_id)
```

## Database Setup

### Alembic Migration

The package includes Alembic migrations for database setup:

```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "Add billing tables"

# Apply migration
alembic upgrade head
```

### Manual Table Creation

```python
from dotmac_shared.billing.core.models import Base
from sqlalchemy import create_engine

engine = create_engine("postgresql://user:pass@localhost/db")
Base.metadata.create_all(engine)
```

## Multi-Tenant Support

All models include a `tenant_id` field for multi-tenant deployments:

```python
# Create tenant-specific billing service
billing_service = create_basic_billing_service(db, tenant_id=tenant_uuid)

# All operations will be scoped to this tenant
customers = await billing_service.customer_repo.get_multi(tenant_id=tenant_uuid)
```

## Extending the Package

### Custom Payment Gateway

```python
from dotmac_shared.billing.services.protocols import PaymentGatewayProtocol

class CustomPaymentGateway:
    async def process_payment(self, amount, currency, payment_method_id, customer_id, metadata=None):
        # Your payment processing logic here
        return {
            "status": "completed",
            "transaction_id": "txn_123",
            "authorization_code": "auth_456"
        }

    # Implement other required methods...

# Register with factory
billing_service_factory.register_payment_gateway("custom", CustomPaymentGateway)
```

### Custom Notification Service

```python
from dotmac_shared.billing.services.protocols import NotificationServiceProtocol

class CustomNotificationService:
    async def send_invoice_notification(self, customer, invoice, notification_type="invoice_created"):
        # Your notification logic here
        return True

    # Implement other required methods...

# Register with factory
billing_service_factory.register_notification_service("custom", CustomNotificationService)
```

## API Integration

The package is designed to integrate seamlessly with FastAPI:

```python
from fastapi import APIRouter, Depends
from dotmac_shared.billing import BillingServiceFactory

router = APIRouter()

def get_billing_service(db: AsyncSession = Depends(get_db)):
    return create_basic_billing_service(db)

@router.post("/subscriptions")
async def create_subscription(
    subscription_data: SubscriptionCreate,
    billing_service: BillingService = Depends(get_billing_service)
):
    return await billing_service.create_subscription(
        customer_id=subscription_data.customer_id,
        plan_id=subscription_data.billing_plan_id
    )
```

## Testing

The package includes comprehensive test coverage:

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=dotmac_shared.billing tests/
```

### Test Fixtures

```python
import pytest
from dotmac_shared.billing.adapters import create_basic_billing_service

@pytest.fixture
async def billing_service(db_session):
    return create_basic_billing_service(db_session)

@pytest.mark.asyncio
async def test_create_subscription(billing_service):
    # Test your billing logic
    pass
```

## Performance Considerations

- **Database Indexes**: All foreign keys and commonly queried fields are indexed
- **Lazy Loading**: Relationships use lazy loading by default, explicit loading available
- **Pagination**: Built-in pagination support for large result sets
- **Connection Pooling**: Works with SQLAlchemy's connection pooling
- **Caching**: Repository layer supports caching extensions

## Security

- **Input Validation**: All inputs validated through Pydantic schemas
- **SQL Injection Protection**: Parameterized queries throughout
- **Tenant Isolation**: Strict tenant_id filtering on all operations
- **Audit Trail**: All models include created_at/updated_at timestamps
- **Sensitive Data**: Payment methods and gateway data properly isolated

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/billing

# Payment Gateway
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Multi-tenant
DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000000
```

## Monitoring and Observability

The package includes built-in metrics and logging:

```python
import logging
from dotmac_shared.billing import BillingService

# Enable debug logging
logging.getLogger('dotmac_shared.billing').setLevel(logging.DEBUG)

# Metrics are automatically collected for:
# - Invoice generation time
# - Payment processing success/failure rates
# - Subscription churn rates
# - Revenue metrics
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: <https://docs.dotmac.dev/billing>
- Issues: <https://github.com/dotmac-framework/billing/issues>
- Email: <support@dotmac.dev>
