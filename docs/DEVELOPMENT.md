# DotMac Framework Development Guide

This guide provides comprehensive information for developers working on the DotMac ISP Framework, including setup instructions, development workflows, coding standards, and best practices.

## 🚀 Quick Start

### Prerequisites

Ensure you have the following installed:

- **Python 3.9+** (recommended: 3.11)
- **PostgreSQL 12+** 
- **Redis 6+**
- **Git 2.30+**
- **Docker & Docker Compose** (optional, for containerized development)

### Initial Setup

1. **Clone and setup the repository**
   ```bash
   git clone https://github.com/your-org/dotmac-framework.git
   cd dotmac-framework
   
   # Install development environment
   make install-dev
   ```

2. **Configure your environment**
   ```bash
   # Copy and customize environment configuration
   cp .env.example .env
   
   # Edit .env with your local settings
   nano .env
   ```

3. **Start local services**
   ```bash
   # Option 1: Using Docker Compose (recommended)
   docker-compose up -d postgres redis
   
   # Option 2: Install locally (macOS with Homebrew)
   brew install postgresql redis
   brew services start postgresql
   brew services start redis
   ```

4. **Initialize the database**
   ```bash
   # Create test databases
   createdb dotmac_dev
   createdb dotmac_test
   
   # Run migrations
   cd dotmac_identity && alembic upgrade head && cd ..
   cd dotmac_billing && alembic upgrade head && cd ..
   # Repeat for other services with databases
   ```

5. **Verify installation**
   ```bash
   # Run tests to ensure everything works
   make test
   
   # Check code quality
   make check
   ```

## 🛠️ Development Environment

### IDE Configuration

#### VS Code (Recommended)
Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["-v"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/node_modules": true
    },
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

#### PyCharm
1. Import project as existing source
2. Set Python interpreter to `./venv/bin/python`
3. Configure code style to use Black
4. Enable pytest as test runner
5. Configure Ruff as external tool

### Environment Variables

Key environment variables for development:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dotmac_dev
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/dotmac_test

# Redis
REDIS_URL=redis://localhost:6379/0

# Development flags
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# External services (use test/mock values)
STRIPE_SECRET_KEY=sk_test_...
TWILIO_AUTH_TOKEN=test_token
MOCK_EXTERNAL_SERVICES=true
```

## 📁 Project Structure

### Monorepo Layout
```
dotmac_framework/
├── .github/                    # GitHub Actions and templates
├── docs/                       # Documentation
├── scripts/                    # Utility scripts
├── tests/                      # Global test configuration
├── dotmac_core_events/         # Event system
├── dotmac_core_ops/           # Operational utilities
├── dotmac_identity/           # Authentication & authorization
├── dotmac_billing/            # Billing & payments
├── dotmac_services/           # Service management
├── dotmac_networking/         # Network infrastructure
├── dotmac_analytics/          # Business intelligence
├── dotmac_api_gateway/        # API gateway
├── dotmac_platform/           # Platform orchestration
├── dotmac_devtools/           # Development tools
└── templates/                 # Service templates
```

### Service Structure
Each service follows a consistent structure:
```
dotmac_service_name/
├── dotmac_service_name/
│   ├── __init__.py
│   ├── api/                   # FastAPI routes
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── dependencies.py
│   ├── models/               # Data models
│   │   ├── __init__.py
│   │   ├── entities.py       # SQLAlchemy models
│   │   └── schemas.py        # Pydantic schemas
│   ├── services/             # Business logic
│   │   ├── __init__.py
│   │   └── service.py
│   ├── repositories/         # Data access
│   │   ├── __init__.py
│   │   └── repository.py
│   └── utils/               # Utilities
│       ├── __init__.py
│       └── helpers.py
├── tests/                   # Tests
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_services.py
│   └── test_models.py
├── migrations/              # Database migrations
├── pyproject.toml          # Package configuration
└── README.md               # Service documentation
```

## 🔧 Development Workflow

### Feature Development Process

1. **Create feature branch**
   ```bash
   git checkout -b feature/customer-self-service
   ```

2. **Make changes following TDD**
   ```bash
   # Write failing test first
   # Implement feature
   # Make test pass
   # Refactor if needed
   ```

3. **Run quality checks frequently**
   ```bash
   # Quick checks during development
   make test-unit
   make lint
   
   # Full checks before committing
   make check
   ```

4. **Commit with conventional format**
   ```bash
   git add .
   git commit -m "feat(billing): add automated invoice generation"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/customer-self-service
   # Create PR via GitHub UI
   ```

### Daily Development Commands

```bash
# Start development day
make install-dev              # Update dependencies if needed
make test                     # Ensure everything works

# During development
make test-unit                # Quick feedback
make lint                     # Check style issues
make format                   # Auto-fix formatting

# Before committing
make check                    # Full quality check
make security                 # Security scan

# End of day cleanup
make clean                    # Remove build artifacts
```

## 🧪 Testing Strategy

### Test Categories

1. **Unit Tests** - Fast, isolated tests
2. **Integration Tests** - Cross-component testing
3. **Contract Tests** - API compatibility
4. **End-to-End Tests** - Full workflow testing

### Writing Tests

#### Unit Test Example
```python
# tests/test_services/test_billing_service.py
import pytest
from decimal import Decimal
from dotmac_billing.services.billing_service import BillingService
from dotmac_billing.models.schemas import InvoiceCreate

class TestBillingService:
    
    @pytest.fixture
    def billing_service(self, mock_repository):
        return BillingService(repository=mock_repository)
    
    def test_calculate_monthly_charges(self, billing_service, sample_customer):
        # Given
        services = [
            {"type": "broadband", "monthly_price": Decimal("79.99")},
            {"type": "phone", "monthly_price": Decimal("29.99")}
        ]
        
        # When
        total = billing_service.calculate_monthly_charges(
            customer_id=sample_customer.id,
            services=services
        )
        
        # Then
        assert total == Decimal("109.98")
    
    async def test_generate_invoice(self, billing_service, sample_customer):
        # Given
        invoice_data = InvoiceCreate(
            customer_id=sample_customer.id,
            amount=Decimal("79.99"),
            due_date="2024-02-15"
        )
        
        # When
        invoice = await billing_service.generate_invoice(invoice_data)
        
        # Then
        assert invoice.customer_id == sample_customer.id
        assert invoice.amount == Decimal("79.99")
        assert invoice.status == "draft"
```

#### Integration Test Example
```python
# tests/test_integration/test_customer_billing_flow.py
import pytest
from httpx import AsyncClient

@pytest.mark.integration
class TestCustomerBillingFlow:
    
    async def test_customer_service_to_billing_flow(
        self, 
        async_client: AsyncClient,
        auth_headers: dict,
        sample_customer_data: dict
    ):
        # Create customer via Identity service
        customer_response = await async_client.post(
            "/api/v1/customers",
            json=sample_customer_data,
            headers=auth_headers
        )
        assert customer_response.status_code == 201
        customer = customer_response.json()
        
        # Add service via Services service
        service_data = {
            "customer_id": customer["id"],
            "service_type": "broadband",
            "plan": "fiber_100",
            "monthly_price": 79.99
        }
        
        service_response = await async_client.post(
            "/api/v1/services",
            json=service_data,
            headers=auth_headers
        )
        assert service_response.status_code == 201
        
        # Generate invoice via Billing service
        invoice_response = await async_client.post(
            f"/api/v1/customers/{customer['id']}/invoices",
            headers=auth_headers
        )
        assert invoice_response.status_code == 201
        invoice = invoice_response.json()
        assert invoice["amount"] == 79.99
```

### Test Utilities

#### Test Data Factory
```python
# tests/factories.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from dotmac_identity.models.entities import Customer

class CustomerFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Customer
        sqlalchemy_session = None  # Set in conftest.py
    
    id = factory.Faker('uuid4')
    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    tenant_id = factory.Faker('uuid4')

# Usage in tests
def test_customer_creation(db_session):
    CustomerFactory._meta.sqlalchemy_session = db_session
    customer = CustomerFactory()
    assert customer.email is not None
```

#### Mock Services
```python
# tests/mocks.py
from unittest.mock import AsyncMock, Mock
import pytest

@pytest.fixture
def mock_stripe_service():
    mock = AsyncMock()
    mock.create_payment_intent.return_value = {
        "id": "pi_test123",
        "status": "succeeded",
        "amount": 7999
    }
    return mock

@pytest.fixture
def mock_email_service():
    mock = AsyncMock()
    mock.send_invoice_email.return_value = {"message_id": "msg_123"}
    return mock
```

## 🎨 Code Style Guide

### Python Style

We follow PEP 8 with Black formatting:

```python
# ✅ Good
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class InvoiceService:
    """Service for managing customer invoices."""
    
    def __init__(self, repository: InvoiceRepository) -> None:
        self.repository = repository
    
    async def generate_monthly_invoice(
        self, 
        customer_id: str, 
        billing_date: datetime
    ) -> Invoice:
        """Generate monthly invoice for customer.
        
        Args:
            customer_id: Unique customer identifier
            billing_date: Date for billing period
            
        Returns:
            Generated invoice
            
        Raises:
            CustomerNotFoundError: If customer doesn't exist
        """
        # Implementation here
        pass

# ❌ Bad
def generateInvoice(customerId,billingDate):
    # No type hints, poor naming, no docstring
    pass
```

### Naming Conventions

- **Classes**: PascalCase (`CustomerService`, `InvoiceRepository`)
- **Functions/Variables**: snake_case (`calculate_total`, `customer_id`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`)
- **Private methods**: Leading underscore (`_validate_input`)

### Type Hints

Always use type hints for better code clarity:

```python
from typing import List, Dict, Optional, Union
from uuid import UUID
from datetime import datetime

# Function signatures
async def get_customer_invoices(
    customer_id: UUID,
    start_date: Optional[datetime] = None,
    limit: int = 100
) -> List[Invoice]:
    pass

# Class attributes
class Customer:
    id: UUID
    email: str
    created_at: datetime
    metadata: Dict[str, str]
    services: List[Service]
```

### Error Handling

Use custom exceptions for domain errors:

```python
# Define domain exceptions
class DomainError(Exception):
    """Base class for domain errors."""
    pass

class CustomerNotFoundError(DomainError):
    """Raised when customer cannot be found."""
    
    def __init__(self, customer_id: UUID):
        self.customer_id = customer_id
        super().__init__(f"Customer {customer_id} not found")

class InsufficientFundsError(DomainError):
    """Raised when customer has insufficient funds."""
    
    def __init__(self, customer_id: UUID, required: Decimal, available: Decimal):
        self.customer_id = customer_id
        self.required = required
        self.available = available
        super().__init__(
            f"Customer {customer_id} has insufficient funds: "
            f"required ${required}, available ${available}"
        )

# Use in services
async def process_payment(customer_id: UUID, amount: Decimal) -> Payment:
    customer = await customer_repo.get_by_id(customer_id)
    if not customer:
        raise CustomerNotFoundError(customer_id)
    
    if customer.balance < amount:
        raise InsufficientFundsError(customer_id, amount, customer.balance)
    
    # Process payment
    return payment
```

## 🗄️ Database Development

### Migration Management

Each service manages its own database schema:

```bash
# Create new migration
cd dotmac_billing
alembic revision --autogenerate -m "Add payment_methods table"

# Review generated migration
# Edit if necessary for data migration

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Model Development

```python
# models/entities.py
from sqlalchemy import Column, String, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from dotmac_core_ops.database import Base
import uuid

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    due_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    line_items = relationship("InvoiceLineItem", back_populates="invoice")
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, amount={self.amount}, status={self.status})>"
```

### Repository Pattern

```python
# repositories/invoice_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotmac_billing.models.entities import Invoice

class InvoiceRepository(ABC):
    @abstractmethod
    async def get_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        pass
    
    @abstractmethod
    async def get_by_customer(self, customer_id: UUID) -> List[Invoice]:
        pass
    
    @abstractmethod
    async def create(self, invoice: Invoice) -> Invoice:
        pass

class SqlAlchemyInvoiceRepository(InvoiceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        result = await self.session.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_customer(self, customer_id: UUID) -> List[Invoice]:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.customer_id == customer_id)
            .order_by(Invoice.created_at.desc())
        )
        return result.scalars().all()
    
    async def create(self, invoice: Invoice) -> Invoice:
        self.session.add(invoice)
        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice
```

## 🌐 API Development

### FastAPI Route Development

```python
# api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List
from dotmac_billing.models.schemas import InvoiceResponse, InvoiceCreate
from dotmac_billing.services.invoice_service import InvoiceService
from dotmac_billing.api.dependencies import get_invoice_service, get_current_user

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.post(
    "/",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new invoice",
    description="Generate a new invoice for a customer"
)
async def create_invoice(
    invoice_data: InvoiceCreate,
    service: InvoiceService = Depends(get_invoice_service),
    current_user = Depends(get_current_user)
):
    """Create a new invoice."""
    try:
        invoice = await service.create_invoice(invoice_data)
        return InvoiceResponse.from_orm(invoice)
    except CustomerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {e.customer_id} not found"
        )

@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get invoice by ID"
)
async def get_invoice(
    invoice_id: UUID,
    service: InvoiceService = Depends(get_invoice_service),
    current_user = Depends(get_current_user)
):
    """Retrieve a specific invoice."""
    invoice = await service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return InvoiceResponse.from_orm(invoice)
```

### Pydantic Schemas

```python
# models/schemas.py
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from typing import List, Optional

class InvoiceBase(BaseModel):
    customer_id: UUID = Field(..., description="Customer identifier")
    amount: Decimal = Field(..., gt=0, description="Invoice amount")
    due_date: date = Field(..., description="Payment due date")

class InvoiceCreate(InvoiceBase):
    line_items: List[LineItemCreate] = Field(default_factory=list)
    
    @validator('due_date')
    def due_date_must_be_future(cls, v):
        if v <= date.today():
            raise ValueError('Due date must be in the future')
        return v

class InvoiceResponse(InvoiceBase):
    id: UUID
    status: str
    created_at: datetime
    line_items: List[LineItemResponse]
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "customer_id": "123e4567-e89b-12d3-a456-426614174001",
                "amount": 79.99,
                "status": "pending",
                "due_date": "2024-02-15",
                "created_at": "2024-01-15T10:30:00Z",
                "line_items": []
            }
        }
```

### Dependency Injection

```python
# api/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dotmac_core_ops.database import get_db_session
from dotmac_billing.repositories.invoice_repository import SqlAlchemyInvoiceRepository
from dotmac_billing.services.invoice_service import InvoiceService

async def get_invoice_repository(
    session: AsyncSession = Depends(get_db_session)
) -> SqlAlchemyInvoiceRepository:
    return SqlAlchemyInvoiceRepository(session)

async def get_invoice_service(
    repository: SqlAlchemyInvoiceRepository = Depends(get_invoice_repository)
) -> InvoiceService:
    return InvoiceService(repository)
```

## 🔒 Security Development

### Authentication Middleware

```python
# api/middleware/auth.py
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from dotmac_identity.services.auth_service import AuthService

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Extract and validate current user from JWT token."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            auth_service.secret_key,
            algorithms=[auth_service.algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        user = await auth_service.get_user(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
```

### Authorization Decorators

```python
# utils/auth.py
from functools import wraps
from fastapi import HTTPException, status

def require_permission(permission: str):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not current_user.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@router.delete("/{invoice_id}")
@require_permission("invoices:delete")
async def delete_invoice(
    invoice_id: UUID,
    current_user = Depends(get_current_user)
):
    pass
```

## 🔄 Event-Driven Development

### Publishing Events

```python
# services/invoice_service.py
from dotmac_core_events.publisher import EventPublisher
from dotmac_billing.events import InvoiceCreatedEvent

class InvoiceService:
    def __init__(
        self, 
        repository: InvoiceRepository,
        event_publisher: EventPublisher
    ):
        self.repository = repository
        self.event_publisher = event_publisher
    
    async def create_invoice(self, invoice_data: InvoiceCreate) -> Invoice:
        # Create invoice
        invoice = Invoice(**invoice_data.dict())
        invoice = await self.repository.create(invoice)
        
        # Publish event
        event = InvoiceCreatedEvent(
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            amount=invoice.amount,
            due_date=invoice.due_date,
            timestamp=datetime.now(timezone.utc)
        )
        await self.event_publisher.publish("billing.invoice_created", event)
        
        return invoice
```

### Consuming Events

```python
# event_handlers/billing_handlers.py
from dotmac_core_events.consumer import EventConsumer
from dotmac_billing.services.notification_service import NotificationService

@EventConsumer.handle("billing.invoice_created")
async def handle_invoice_created(event: InvoiceCreatedEvent):
    """Send email notification when invoice is created."""
    notification_service = get_notification_service()
    
    await notification_service.send_invoice_notification(
        customer_id=event.customer_id,
        invoice_id=event.invoice_id,
        amount=event.amount
    )
```

## 📊 Monitoring & Debugging

### Logging

```python
# Use structured logging
import structlog
from dotmac_core_ops.logging import get_logger

logger = get_logger(__name__)

async def process_payment(payment_data: PaymentCreate) -> Payment:
    logger.info(
        "Payment processing started",
        customer_id=payment_data.customer_id,
        amount=float(payment_data.amount),
        payment_method=payment_data.method
    )
    
    try:
        payment = await payment_processor.charge(payment_data)
        
        logger.info(
            "Payment processed successfully",
            payment_id=payment.id,
            customer_id=payment_data.customer_id,
            amount=float(payment_data.amount),
            status=payment.status
        )
        
        return payment
        
    except PaymentError as e:
        logger.error(
            "Payment processing failed",
            customer_id=payment_data.customer_id,
            amount=float(payment_data.amount),
            error=str(e),
            error_code=e.code
        )
        raise
```

### Metrics Collection

```python
# utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps

# Define metrics
invoice_created_total = Counter(
    'invoices_created_total',
    'Total number of invoices created',
    ['status']
)

payment_processing_duration = Histogram(
    'payment_processing_duration_seconds',
    'Time spent processing payments',
    ['payment_method']
)

def track_duration(metric: Histogram, labels: dict = None):
    """Decorator to track function duration."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        return wrapper
    return decorator

# Usage
@track_duration(payment_processing_duration, {"payment_method": "stripe"})
async def process_stripe_payment(payment_data):
    # Implementation
    pass
```

## 🚀 Performance Optimization

### Database Query Optimization

```python
# ✅ Good - Eager loading to avoid N+1 queries
from sqlalchemy.orm import joinedload

async def get_customers_with_services(self) -> List[Customer]:
    result = await self.session.execute(
        select(Customer)
        .options(joinedload(Customer.services))
        .where(Customer.is_active == True)
    )
    return result.unique().scalars().all()

# ✅ Good - Use pagination for large datasets
async def get_invoices_paginated(
    self, 
    offset: int = 0, 
    limit: int = 100
) -> List[Invoice]:
    result = await self.session.execute(
        select(Invoice)
        .offset(offset)
        .limit(limit)
        .order_by(Invoice.created_at.desc())
    )
    return result.scalars().all()
```

### Caching Strategies

```python
# services/customer_service.py
from dotmac_core_ops.cache import cache_result

class CustomerService:
    
    @cache_result(ttl=300)  # Cache for 5 minutes
    async def get_customer_profile(self, customer_id: UUID) -> CustomerProfile:
        """Get customer profile with caching."""
        customer = await self.repository.get_by_id(customer_id)
        return CustomerProfile.from_customer(customer)
    
    async def update_customer(self, customer_id: UUID, data: CustomerUpdate):
        """Update customer and invalidate cache."""
        customer = await self.repository.update(customer_id, data)
        
        # Invalidate cache
        cache_key = f"customer_profile:{customer_id}"
        await self.cache.delete(cache_key)
        
        return customer
```

## 🐛 Debugging Tips

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check database connection
   psql $DATABASE_URL -c "SELECT 1"
   
   # Check connection pool
   SELECT * FROM pg_stat_activity WHERE datname = 'dotmac_dev';
   ```

2. **Event System Issues**
   ```bash
   # Check Redis connection
   redis-cli ping
   
   # Monitor Redis activity
   redis-cli monitor
   
   # Check event queues
   redis-cli KEYS "*event*"
   ```

3. **Test Failures**
   ```bash
   # Run specific test with verbose output
   pytest tests/test_billing.py::test_invoice_creation -v -s
   
   # Debug with pdb
   pytest tests/test_billing.py::test_invoice_creation --pdb
   
   # Run with coverage
   pytest tests/test_billing.py --cov=dotmac_billing --cov-report=html
   ```

### Development Tools

```bash
# Code quality tools
make lint                    # Check code style
make format                  # Fix formatting
make type-check             # Check types
make complexity-report      # Analyze complexity

# Testing tools
make test-unit              # Fast unit tests
make test-integration       # Integration tests
make test-package PACKAGE=dotmac_billing  # Test specific package

# Security tools
make security               # Security scan
make deps-check            # Check vulnerabilities

# Performance tools
py-spy top --pid $(pgrep -f uvicorn)  # Profile running app
```

This development guide provides the foundation for productive development on the DotMac Framework. For specific questions or issues, refer to the project documentation or create an issue in the repository.