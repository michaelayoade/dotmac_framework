# DotMac ISP Framework - Developer Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Project Structure](#project-structure)
4. [Coding Standards](#coding-standards)
5. [Database Development](#database-development)
6. [API Development](#api-development)
7. [Testing Guidelines](#testing-guidelines)
8. [Security Best Practices](#security-best-practices)
9. [Performance Guidelines](#performance-guidelines)
10. [Deployment Process](#deployment-process)
11. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

Before you begin development, ensure you have the following installed:

- **Python 3.11+**: Latest stable Python version
- **Poetry**: Dependency management and packaging
- **PostgreSQL 12+**: Primary database
- **Redis 6+**: Caching and session storage
- **Docker & Docker Compose**: Containerized development
- **Git**: Version control

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/dotmac-isp-framework.git
cd dotmac-isp-framework/dotmac_isp_framework

# Install dependencies
poetry install

# Copy environment configuration
cp .env.example .env
# Edit .env with your local settings

# Start development services
docker-compose up -d postgres redis

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn dotmac_isp.main:app --reload --host 0.0.0.0 --port 8000
```

### First Steps

1. **Explore the API**: Visit http://localhost:8000/docs for interactive API documentation
2. **Check Health**: Verify system health at http://localhost:8000/health
3. **Review Examples**: Examine the test files for usage examples
4. **Read Architecture**: Understanding the [ARCHITECTURE.md](ARCHITECTURE.md) document

## Development Environment

### Local Development Setup

#### 1. Poetry Configuration
```bash
# Configure Poetry to create virtual environments in project directory
poetry config virtualenvs.in-project true

# Install all dependencies including dev tools
poetry install --with dev,test

# Activate virtual environment
poetry shell
```

#### 2. Environment Configuration
```env
# .env file for local development
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/dotmac_isp
ASYNC_DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/dotmac_isp

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Security Configuration
SECRET_KEY=your-development-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Portal ID Configuration
PORTAL_ID_LENGTH=8
PORTAL_SESSION_DEFAULT_TIMEOUT=30
```

#### 3. IDE Configuration

**VS Code Settings (.vscode/settings.json)**:
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["-v", "--tb=short"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        ".coverage": true,
        "htmlcov": true
    }
}
```

### Docker Development

For consistent development environments across team members:

```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - /app/.venv  # Anonymous volume for dependencies
    environment:
      - DEBUG=true
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/dotmac_isp
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    command: uvicorn dotmac_isp.main:app --reload --host 0.0.0.0 --port 8000

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=dotmac_isp
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_dev_data:
```

### Development Tools

#### Code Quality Tools
```bash
# Format code
poetry run black .
poetry run isort .

# Lint code
poetry run flake8 .
poetry run mypy .

# Security scan
poetry run bandit -r src/

# Run all quality checks
poetry run pre-commit run --all-files
```

#### Database Tools
```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Add new feature"

# Upgrade database
poetry run alembic upgrade head

# Downgrade one revision
poetry run alembic downgrade -1

# Check current revision
poetry run alembic current
```

## Project Structure

### Directory Layout
```
dotmac_isp_framework/
├── src/
│   └── dotmac_isp/
│       ├── __init__.py
│       ├── main.py                 # FastAPI application entry point
│       ├── core/                   # Core application components
│       │   ├── __init__.py
│       │   ├── database.py         # Database configuration
│       │   └── settings.py         # Application settings
│       ├── modules/                # Business modules
│       │   ├── identity/           # User and customer identity
│       │   ├── portal_management/  # Portal ID system
│       │   ├── billing/            # Billing and payments
│       │   ├── services/           # Service management
│       │   ├── networking/         # Network operations
│       │   ├── support/            # Customer support
│       │   ├── analytics/          # Business intelligence
│       │   ├── sales/              # Sales and CRM
│       │   ├── resellers/          # Partner management
│       │   ├── inventory/          # Equipment management
│       │   ├── field_ops/          # Field operations
│       │   ├── compliance/         # Regulatory compliance
│       │   ├── notifications/      # Communication system
│       │   └── licensing/          # Feature licensing
│       ├── portals/                # Portal interfaces
│       │   ├── admin/              # Admin portal
│       │   ├── customer/           # Customer portal
│       │   ├── reseller/           # Reseller portal
│       │   └── technician/         # Technician portal
│       ├── shared/                 # Shared components
│       │   ├── __init__.py
│       │   ├── models.py           # Base models and mixins
│       │   ├── schemas.py          # Shared Pydantic models
│       │   └── utils.py            # Utility functions
│       └── plugins/                # Plugin system
│           └── core/               # Core plugin functionality
├── tests/                          # Test suite
│   ├── conftest.py                 # Test configuration
│   ├── unit/                       # Unit tests
│   ├── integration/                # Integration tests
│   └── e2e/                        # End-to-end tests
├── alembic/                        # Database migrations
│   ├── versions/                   # Migration files
│   └── env.py                      # Alembic configuration
├── docs/                           # Documentation
├── docker-compose.yml              # Docker development setup
├── Dockerfile                      # Production Docker image
├── pyproject.toml                  # Project configuration
└── README.md                       # Project readme
```

### Module Structure

Each business module follows a consistent structure:

```
modules/example_module/
├── __init__.py
├── models.py          # SQLAlchemy models
├── schemas.py         # Pydantic schemas
├── router.py          # FastAPI routes
├── services.py        # Business logic (optional)
├── dependencies.py    # Dependency injection (optional)
└── exceptions.py      # Module-specific exceptions (optional)
```

### Naming Conventions

- **Files**: snake_case (`user_service.py`)
- **Classes**: PascalCase (`UserService`)
- **Functions**: snake_case (`create_user`)
- **Variables**: snake_case (`user_id`)
- **Constants**: UPPER_SNAKE_CASE (`DEFAULT_TIMEOUT`)
- **Database Tables**: snake_case (`portal_accounts`)
- **Database Columns**: snake_case (`created_at`)

## Coding Standards

### Python Code Style

The project follows PEP 8 with Black formatting and additional conventions:

#### Import Organization
```python
# Standard library imports
import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

# Third-party imports
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, validator
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import Session

# Local imports
from dotmac_isp.core.database import get_db
from dotmac_isp.shared.models import TenantModel
from .models import PortalAccount
from .schemas import PortalAccountCreate, PortalAccountResponse
```

#### Function Documentation
```python
async def create_portal_account(
    tenant_id: UUID,
    account_data: PortalAccountCreate,
    db: Session = Depends(get_db)
) -> PortalAccount:
    """
    Create a new Portal ID account for customer authentication.
    
    Args:
        tenant_id: Tenant identifier for multi-tenant isolation
        account_data: Portal account creation data
        db: Database session dependency
        
    Returns:
        Created portal account with generated Portal ID
        
    Raises:
        HTTPException: If portal ID generation fails or validation errors occur
        
    Example:
        >>> account = await create_portal_account(
        ...     tenant_id=uuid4(),
        ...     account_data=PortalAccountCreate(
        ...         customer_id=uuid4(),
        ...         account_type=PortalAccountType.CUSTOMER
        ...     )
        ... )
        >>> print(account.portal_id)  # Output: "ABC12345"
    """
    # Implementation here...
```

#### Error Handling
```python
# Define custom exceptions
class PortalAccountNotFoundError(Exception):
    """Raised when Portal ID account is not found."""
    def __init__(self, portal_id: str):
        self.portal_id = portal_id
        super().__init__(f"Portal account '{portal_id}' not found")

# Use specific exception handling
async def get_portal_account(portal_id: str) -> PortalAccount:
    try:
        account = await db.query(PortalAccount).filter(
            PortalAccount.portal_id == portal_id
        ).one()
        return account
    except NoResultFound:
        raise PortalAccountNotFoundError(portal_id)
    except Exception as e:
        logger.error(f"Unexpected error retrieving portal account {portal_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

#### Async/Await Best Practices
```python
# Good: Use async/await consistently
async def process_payment(payment_data: PaymentCreate) -> Payment:
    async with db.begin():
        payment = await create_payment_record(payment_data)
        result = await payment_gateway.charge(payment_data.amount)
        payment.gateway_transaction_id = result.transaction_id
        await db.commit()
        return payment

# Good: Handle concurrent operations
async def send_notifications(customers: List[Customer]) -> None:
    tasks = [
        send_email_notification(customer.email, "Welcome!")
        for customer in customers
    ]
    await asyncio.gather(*tasks)

# Bad: Mixing sync and async
def bad_function():
    # Don't mix sync database calls with async code
    user = db.query(User).first()  # Blocking call in async context
    return user
```

### Type Hints

Use comprehensive type hints throughout the codebase:

```python
from typing import Optional, List, Dict, Union, TypeVar, Generic
from uuid import UUID
from datetime import datetime

# Function type hints
async def get_customers(
    tenant_id: UUID,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 20,
    offset: int = 0
) -> List[Customer]:
    """Get customers with optional filtering."""
    pass

# Class type hints
class CustomerService:
    def __init__(self, db: AsyncSession, cache: Redis) -> None:
        self.db = db
        self.cache = cache
    
    async def create_customer(
        self,
        customer_data: CustomerCreate
    ) -> Customer:
        """Create new customer."""
        pass

# Generic types
T = TypeVar('T')

class Repository(Generic[T]):
    def __init__(self, model: type[T]) -> None:
        self.model = model
    
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Get entity by ID."""
        pass
```

## Database Development

### Model Design

#### Base Models
```python
# shared/models.py
class BaseModel(Base):
    """Base model with common fields."""
    __abstract__ = True
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

class TenantModel(BaseModel):
    """Base model with tenant isolation."""
    __abstract__ = True
    
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        nullable=False, 
        index=True
    )
```

#### Model Relationships
```python
class Customer(TenantModel):
    """Customer model with proper relationships."""
    __tablename__ = "customers"
    
    customer_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    
    # One-to-one relationship with Portal Account
    portal_account: Mapped[Optional["PortalAccount"]] = relationship(
        "PortalAccount",
        back_populates="customer",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # One-to-many relationship with Services
    services: Mapped[List["ServiceInstance"]] = relationship(
        "ServiceInstance",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin"  # Optimize N+1 queries
    )
    
    # One-to-many relationship with Invoices
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="customer",
        order_by="Invoice.created_at.desc()"
    )

class PortalAccount(TenantModel):
    """Portal account with back-reference."""
    __tablename__ = "portal_accounts"
    
    portal_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    customer_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("customers.id"))
    
    # Relationship back to customer
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="portal_account"
    )
```

### Query Patterns

#### Efficient Queries
```python
# Good: Use selectin loading to avoid N+1
async def get_customers_with_services(tenant_id: UUID) -> List[Customer]:
    result = await db.execute(
        select(Customer)
        .options(selectinload(Customer.services))
        .where(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.is_deleted == False
            )
        )
    )
    return result.scalars().all()

# Good: Use joins for filtered queries
async def get_customers_with_active_services(tenant_id: UUID) -> List[Customer]:
    result = await db.execute(
        select(Customer)
        .join(ServiceInstance)
        .where(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.is_deleted == False,
                ServiceInstance.status == ServiceStatus.ACTIVE
            )
        )
        .distinct()
    )
    return result.scalars().all()

# Good: Use subqueries for complex filtering
async def get_customers_without_portal_accounts(tenant_id: UUID) -> List[Customer]:
    portal_subquery = select(PortalAccount.customer_id).where(
        PortalAccount.tenant_id == tenant_id
    )
    
    result = await db.execute(
        select(Customer)
        .where(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.is_deleted == False,
                Customer.id.notin_(portal_subquery)
            )
        )
    )
    return result.scalars().all()
```

#### Pagination
```python
async def paginate_customers(
    tenant_id: UUID,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Paginate customers with search."""
    
    base_query = select(Customer).where(
        and_(
            Customer.tenant_id == tenant_id,
            Customer.is_deleted == False
        )
    )
    
    # Add search filter
    if search:
        search_filter = or_(
            Customer.first_name.ilike(f"%{search}%"),
            Customer.last_name.ilike(f"%{search}%"),
            Customer.email.ilike(f"%{search}%"),
            Customer.customer_number.ilike(f"%{search}%")
        )
        base_query = base_query.where(search_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    customers_query = base_query.order_by(Customer.created_at.desc()).offset(offset).limit(limit)
    customers_result = await db.execute(customers_query)
    customers = customers_result.scalars().all()
    
    return {
        "items": customers,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total
    }
```

### Migration Best Practices

#### Migration Structure
```python
"""Add Portal ID system tables

Revision ID: 001_portal_id_system
Revises: 000_initial_schema
Create Date: 2024-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_portal_id_system'
down_revision = '000_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Apply migration."""
    # Create enum types
    portal_account_status = postgresql.ENUM(
        'active', 'suspended', 'locked', 'pending_activation', 'deactivated',
        name='portal_account_status'
    )
    portal_account_status.create(op.get_bind())
    
    # Create tables
    op.create_table(
        'portal_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('portal_id', sa.String(20), nullable=False, unique=True),
        sa.Column('status', portal_account_status, nullable=False, server_default='pending_activation'),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean, server_default=sa.false()),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
    )
    
    # Create indexes
    op.create_index('idx_portal_accounts_portal_id', 'portal_accounts', ['portal_id'])
    op.create_index('idx_portal_accounts_tenant', 'portal_accounts', ['tenant_id'])
    
def downgrade() -> None:
    """Reverse migration."""
    op.drop_table('portal_accounts')
    op.execute('DROP TYPE portal_account_status')
```

## API Development

### Route Organization

#### Module Router Structure
```python
# modules/identity/router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.dependencies import get_current_user
from .models import Customer
from .schemas import CustomerCreate, CustomerResponse, CustomerUpdate
from .services import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])

@router.get("", response_model=List[CustomerResponse])
async def list_customers(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, min_length=2),
    customer_type: Optional[CustomerType] = Query(None),
    current_user: User = Depends(get_current_user),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """List customers with filtering and pagination."""
    
    customers = await customer_service.list_customers(
        tenant_id=current_user.tenant_id,
        limit=limit,
        offset=offset,
        search=search,
        customer_type=customer_type
    )
    
    return [CustomerResponse.from_orm(customer) for customer in customers]

@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    customer_data: CustomerCreate,
    current_user: User = Depends(get_current_user),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """Create new customer with Portal ID account."""
    
    customer = await customer_service.create_customer_with_portal(
        tenant_id=current_user.tenant_id,
        customer_data=customer_data,
        created_by=current_user.id
    )
    
    return CustomerResponse.from_orm(customer)

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user),
    customer_service: CustomerService = Depends(get_customer_service)
):
    """Get customer by ID."""
    
    customer = await customer_service.get_customer(
        tenant_id=current_user.tenant_id,
        customer_id=customer_id
    )
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return CustomerResponse.from_orm(customer)
```

### Schema Design

#### Request/Response Schemas
```python
# schemas.py
from pydantic import BaseModel, validator, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

class CustomerType(str, Enum):
    RESIDENTIAL = "residential"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"

class CustomerBase(BaseModel):
    """Base customer schema with common fields."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, regex=r'^\+?[\d\s\-\(\)]+$')
    customer_type: CustomerType = CustomerType.RESIDENTIAL
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and len(v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return v

class CustomerCreate(CustomerBase):
    """Schema for creating customers."""
    # Address fields
    street: str = Field(..., min_length=5, max_length=200)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=50)
    postal_code: str = Field(..., min_length=5, max_length=20)
    country: str = Field(default="US", min_length=2, max_length=2)
    
    # Portal account creation
    create_portal_account: bool = Field(default=True)
    portal_password: Optional[str] = Field(None, min_length=8)
    
    @validator('portal_password')
    def validate_portal_password(cls, v, values):
        if values.get('create_portal_account') and not v:
            raise ValueError('Portal password required when creating portal account')
        return v

class CustomerResponse(CustomerBase):
    """Schema for customer responses."""
    id: UUID
    customer_number: str
    account_status: AccountStatus
    created_at: datetime
    
    # Nested portal account info
    portal_account: Optional["PortalAccountSummary"] = None
    
    class Config:
        orm_mode = True

class PortalAccountSummary(BaseModel):
    """Nested portal account information."""
    portal_id: str
    status: PortalAccountStatus
    two_factor_enabled: bool
    last_login: Optional[datetime]
    
    class Config:
        orm_mode = True

# Update forward references
CustomerResponse.update_forward_refs()
```

### Dependency Injection

#### Service Dependencies
```python
# dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from dotmac_isp.core.database import get_async_session
from .services import CustomerService, PortalAccountService

async def get_customer_service(
    db: AsyncSession = Depends(get_async_session)
) -> CustomerService:
    """Get customer service dependency."""
    return CustomerService(db)

async def get_portal_service(
    db: AsyncSession = Depends(get_async_session)
) -> PortalAccountService:
    """Get portal account service dependency."""
    return PortalAccountService(db)

# Authentication dependencies
from jose import JWTError, jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(
    token: str = Depends(security),
    db: AsyncSession = Depends(get_async_session)
) -> User:
    """Get current authenticated user."""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_id(db, UUID(user_id))
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure current user has admin privileges."""
    
    if not any(role.name in ["super_admin", "tenant_admin"] for role in current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user
```

### Error Handling

#### Custom Exception Handlers
```python
# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

# Custom exception classes
class BusinessLogicError(Exception):
    """Base class for business logic errors."""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class PortalAccountNotFoundError(BusinessLogicError):
    def __init__(self, portal_id: str):
        super().__init__(
            message=f"Portal account '{portal_id}' not found",
            error_code="PORTAL_ACCOUNT_NOT_FOUND"
        )

# Exception handlers
@app.exception_handler(BusinessLogicError)
async def business_logic_exception_handler(request: Request, exc: BusinessLogicError):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": exc.error_code or "BUSINESS_LOGIC_ERROR",
                "message": exc.message,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid4())
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request data",
                "details": exc.errors(),
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid4())
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception occurred")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid4())
            }
        }
    )
```

## Testing Guidelines

### Test Structure

#### Test Organization
```
tests/
├── conftest.py                 # Shared test configuration
├── unit/                       # Unit tests
│   ├── test_models.py          # Model tests
│   ├── test_schemas.py         # Schema validation tests
│   ├── test_services.py        # Business logic tests
│   └── modules/
│       ├── test_identity.py
│       └── test_billing.py
├── integration/                # Integration tests
│   ├── test_api_endpoints.py   # API endpoint tests
│   ├── test_database.py        # Database integration tests
│   └── test_external_services.py
└── e2e/                        # End-to-end tests
    ├── test_customer_workflow.py
    └── test_portal_authentication.py
```

#### Test Configuration
```python
# conftest.py
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
from fastapi.testclient import TestClient

from dotmac_isp.main import app
from dotmac_isp.core.database import get_async_session, Base
from dotmac_isp.core.settings import get_settings

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/dotmac_isp_test"

# Test engine and session
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_database():
    """Setup test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for tests."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Get test client with database override."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_async_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
```

### Unit Testing

#### Model Tests
```python
# tests/unit/test_models.py
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from dotmac_isp.modules.portal_management.models import (
    PortalAccount, PortalAccountStatus, PortalAccountType
)

@pytest.mark.unit
def test_portal_account_creation():
    """Test Portal account model creation."""
    
    account = PortalAccount(
        tenant_id=uuid4(),
        customer_id=uuid4(),
        password_hash="hashed_password",
        account_type=PortalAccountType.CUSTOMER.value
    )
    
    # Portal ID should be auto-generated
    assert account.portal_id is not None
    assert len(account.portal_id) == 8
    assert account.status == PortalAccountStatus.PENDING_ACTIVATION.value

@pytest.mark.unit
def test_portal_account_lockout():
    """Test account lockout functionality."""
    
    account = PortalAccount(
        tenant_id=uuid4(),
        password_hash="hashed_password",
        status=PortalAccountStatus.ACTIVE.value
    )
    
    # Account should not be locked initially
    assert not account.is_locked
    
    # Lock account
    account.lock_account(duration_minutes=30, reason="Too many failed attempts")
    
    # Account should now be locked
    assert account.is_locked
    assert account.status == PortalAccountStatus.LOCKED.value
    assert account.locked_until > datetime.utcnow()

@pytest.mark.unit
def test_portal_account_password_expiry():
    """Test password expiry logic."""
    
    account = PortalAccount(
        tenant_id=uuid4(),
        password_hash="hashed_password",
        password_changed_at=datetime.utcnow() - timedelta(days=100)
    )
    
    # Password should be expired (90 day default)
    assert account.password_expired
    
    # Update password change date
    account.password_changed_at = datetime.utcnow()
    assert not account.password_expired
```

#### Service Tests
```python
# tests/unit/test_services.py
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from dotmac_isp.modules.portal_management.services import PortalAccountService
from dotmac_isp.modules.portal_management.models import PortalAccount, PortalAccountStatus
from dotmac_isp.modules.portal_management.schemas import PortalAccountCreate

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_account():
    """Test portal account creation service."""
    
    # Mock dependencies
    mock_db = Mock()
    mock_settings = Mock()
    
    service = PortalAccountService(mock_db)
    service.settings = mock_settings
    
    # Test data
    tenant_id = uuid4()
    account_data = PortalAccountCreate(
        customer_id=uuid4(),
        account_type=PortalAccountType.CUSTOMER,
        password="test_password123"
    )
    
    # Mock database operations
    mock_db.add = Mock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    # Execute service method
    result = await service.create_portal_account(
        tenant_id=tenant_id,
        account_data=account_data
    )
    
    # Verify results
    assert isinstance(result, PortalAccount)
    assert result.tenant_id == tenant_id
    assert result.customer_id == account_data.customer_id
    assert result.portal_id is not None
    
    # Verify database calls
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_portal_id_uniqueness():
    """Test Portal ID uniqueness validation."""
    
    service = PortalAccountService(Mock())
    
    # Mock existing Portal ID check
    service._portal_id_exists = AsyncMock(side_effect=[True, True, False])
    
    # Generate unique Portal ID
    portal_id = service._generate_unique_portal_id(uuid4())
    
    # Should have called exists check 3 times
    assert service._portal_id_exists.call_count == 3
    assert portal_id is not None
    assert len(portal_id) == 8
```

### Integration Testing

#### API Endpoint Tests
```python
# tests/integration/test_api_endpoints.py
import pytest
from httpx import AsyncClient
from uuid import uuid4

from dotmac_isp.modules.identity.models import Customer, User
from dotmac_isp.modules.portal_management.models import PortalAccount

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_customer_endpoint(client: AsyncClient, db_session):
    """Test customer creation endpoint."""
    
    # Create test admin user
    admin_user = User(
        tenant_id=uuid4(),
        username="admin",
        email="admin@test.com",
        password_hash="hashed",
        first_name="Admin",
        last_name="User"
    )
    db_session.add(admin_user)
    await db_session.commit()
    
    # Create JWT token (mock authentication)
    token = create_test_token(admin_user.id, admin_user.tenant_id)
    
    # Test data
    customer_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-0123",
        "customer_type": "residential",
        "street": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "postal_code": "12345",
        "create_portal_account": True,
        "portal_password": "secure_password123"
    }
    
    # Make API request
    response = await client.post(
        "/api/v1/identity/customers",
        json=customer_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verify response
    assert response.status_code == 201
    result = response.json()
    
    assert result["success"] is True
    assert "data" in result
    
    customer = result["data"]["customer"]
    assert customer["first_name"] == "John"
    assert customer["last_name"] == "Doe"
    assert customer["email"] == "john.doe@example.com"
    
    portal_account = result["data"]["portal_account"]
    assert portal_account["portal_id"] is not None
    assert len(portal_account["portal_id"]) == 8
    assert portal_account["status"] == "pending_activation"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_portal_authentication_flow(client: AsyncClient, db_session):
    """Test complete Portal ID authentication flow."""
    
    # Create customer with portal account
    tenant_id = uuid4()
    customer = Customer(
        tenant_id=tenant_id,
        customer_number="CUST-001",
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com"
    )
    db_session.add(customer)
    
    portal_account = PortalAccount(
        tenant_id=tenant_id,
        customer_id=customer.id,
        portal_id="ABC12345",
        password_hash=hash_password("test_password123"),
        status=PortalAccountStatus.ACTIVE.value,
        must_change_password=False
    )
    db_session.add(portal_account)
    await db_session.commit()
    
    # Test login
    login_data = {
        "portal_id": "ABC12345",
        "password": "test_password123",
        "device_fingerprint": "test_device"
    }
    
    response = await client.post("/api/portal/v1/auth/login", json=login_data)
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["success"] is True
    assert "access_token" in result["data"]
    assert "refresh_token" in result["data"]
    assert result["data"]["portal_id"] == "ABC12345"
```

### End-to-End Testing

#### Customer Workflow Tests
```python
# tests/e2e/test_customer_workflow.py
import pytest
from httpx import AsyncClient

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_customer_lifecycle(client: AsyncClient, db_session):
    """Test complete customer lifecycle from creation to service activation."""
    
    # Step 1: Create customer (admin operation)
    admin_token = await create_admin_test_token()
    
    customer_data = {
        "first_name": "Alice",
        "last_name": "Johnson", 
        "email": "alice.johnson@example.com",
        "customer_type": "business",
        "street": "456 Business Ave",
        "city": "Commerce City",
        "state": "NY",
        "postal_code": "10001",
        "create_portal_account": True,
        "portal_password": "business_password123"
    }
    
    create_response = await client.post(
        "/api/v1/identity/customers",
        json=customer_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert create_response.status_code == 201
    customer_result = create_response.json()
    portal_id = customer_result["data"]["portal_account"]["portal_id"]
    
    # Step 2: Activate portal account
    activation_data = {
        "portal_id": portal_id,
        "new_password": "alice_secure_password123"
    }
    
    # Note: In real implementation, activation would use token from email
    activation_response = await client.post(
        "/api/portal/v1/auth/activate",
        json=activation_data
    )
    
    assert activation_response.status_code == 200
    
    # Step 3: Customer portal login
    login_response = await client.post(
        "/api/portal/v1/auth/login",
        json={
            "portal_id": portal_id,
            "password": "alice_secure_password123"
        }
    )
    
    assert login_response.status_code == 200
    login_result = login_response.json()
    customer_token = login_result["data"]["access_token"]
    
    # Step 4: View customer profile
    profile_response = await client.get(
        "/api/portal/v1/account/profile",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    
    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["data"]["customer"]["first_name"] == "Alice"
    
    # Step 5: Admin provisions service
    service_data = {
        "customer_id": customer_result["data"]["customer"]["id"],
        "service_id": "uuid-internet-service-100mbps",
        "installation_date": "2024-02-01T00:00:00Z"
    }
    
    provision_response = await client.post(
        "/api/v1/services/instances",
        json=service_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert provision_response.status_code == 201
    
    # Step 6: Customer views services
    services_response = await client.get(
        "/api/portal/v1/services",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    
    assert services_response.status_code == 200
    services = services_response.json()
    assert len(services["data"]["services"]) == 1
    assert services["data"]["services"][0]["service_type"] == "internet"
```

## Security Best Practices

### Authentication Security

```python
# Secure password hashing
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Higher rounds for better security
)

def hash_password(password: str) -> str:
    """Hash password securely."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)
```

### Input Validation

```python
# Comprehensive input validation
from pydantic import BaseModel, validator, EmailStr
import re

class SecureUserInput(BaseModel):
    """Secure user input validation."""
    
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\?]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v
    
    @validator('first_name', 'last_name')
    def validate_name_fields(cls, v):
        """Validate name fields against XSS."""
        if not v or not v.strip():
            raise ValueError('Name field cannot be empty')
        
        # Remove any HTML tags
        clean_value = re.sub(r'<[^>]*>', '', v).strip()
        if clean_value != v.strip():
            raise ValueError('Name field contains invalid characters')
        
        return clean_value
```

### SQL Injection Prevention

```python
# Always use parameterized queries through ORM
from sqlalchemy import text

# Good: Using ORM
async def get_customer_by_email(db: AsyncSession, email: str) -> Optional[Customer]:
    result = await db.execute(
        select(Customer).where(Customer.email == email)
    )
    return result.scalar_one_or_none()

# Good: Using parameterized raw SQL when needed
async def custom_customer_query(db: AsyncSession, search_term: str) -> List[Customer]:
    result = await db.execute(
        text("""
            SELECT * FROM customers 
            WHERE email ILIKE :search 
            OR first_name ILIKE :search
        """),
        {"search": f"%{search_term}%"}
    )
    return result.fetchall()

# Bad: Never concatenate user input into SQL
# NEVER DO THIS:
# query = f"SELECT * FROM customers WHERE email = '{email}'"
```

### Rate Limiting

```python
# Implement rate limiting for sensitive endpoints
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/auth/login")
@limiter.limit("10/minute")  # 10 attempts per minute per IP
async def portal_login(
    request: Request,
    login_data: PortalLoginRequest
):
    """Rate-limited login endpoint."""
    pass

@router.post("/auth/password-reset")
@limiter.limit("3/hour")  # 3 password resets per hour per IP
async def request_password_reset(
    request: Request,
    reset_data: PasswordResetRequest
):
    """Rate-limited password reset endpoint."""
    pass
```

## Performance Guidelines

### Database Performance

```python
# Use database indexes effectively
from sqlalchemy import Index

class Customer(TenantModel):
    __tablename__ = "customers"
    
    email = Column(String(255), nullable=False)
    customer_number = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Define composite indexes
    __table_args__ = (
        Index('idx_customers_tenant_email', 'tenant_id', 'email'),
        Index('idx_customers_tenant_number', 'tenant_id', 'customer_number'),
        Index('idx_customers_tenant_created', 'tenant_id', 'created_at'),
    )

# Optimize queries with proper loading strategies
async def get_customers_with_services(tenant_id: UUID) -> List[Customer]:
    """Efficiently load customers with their services."""
    
    result = await db.execute(
        select(Customer)
        .options(
            selectinload(Customer.services),  # Avoid N+1 queries
            selectinload(Customer.portal_account)
        )
        .where(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.is_deleted == False
            )
        )
    )
    return result.scalars().all()

# Use database-level filtering instead of Python filtering
# Good: Database filtering
async def get_active_customers(tenant_id: UUID) -> List[Customer]:
    result = await db.execute(
        select(Customer).where(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.account_status == AccountStatus.ACTIVE,
                Customer.is_deleted == False
            )
        )
    )
    return result.scalars().all()

# Bad: Python filtering (loads all records)
# customers = await get_all_customers(tenant_id)
# return [c for c in customers if c.account_status == AccountStatus.ACTIVE]
```

### Caching Strategies

```python
# Implement Redis caching for frequently accessed data
import redis.asyncio as redis
import json
from typing import Optional

class CacheService:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def get(self, key: str) -> Optional[dict]:
        """Get cached value."""
        value = await self.redis.get(key)
        return json.loads(value) if value else None
    
    async def set(self, key: str, value: dict, ttl: int = 300) -> None:
        """Cache value with TTL."""
        await self.redis.setex(key, ttl, json.dumps(value, default=str))
    
    async def delete(self, key: str) -> None:
        """Delete cached value."""
        await self.redis.delete(key)

# Cache frequently accessed customer data
async def get_customer_cached(
    customer_id: UUID,
    tenant_id: UUID,
    cache: CacheService = Depends(get_cache_service)
) -> Optional[Customer]:
    """Get customer with caching."""
    
    cache_key = f"customer:{tenant_id}:{customer_id}"
    
    # Try cache first
    cached_customer = await cache.get(cache_key)
    if cached_customer:
        return Customer(**cached_customer)
    
    # Load from database
    customer = await get_customer_from_db(customer_id, tenant_id)
    if customer:
        # Cache for 5 minutes
        await cache.set(cache_key, customer.dict(), ttl=300)
    
    return customer

# Cache invalidation on updates
async def update_customer(
    customer_id: UUID,
    tenant_id: UUID,
    update_data: CustomerUpdate,
    cache: CacheService = Depends(get_cache_service)
) -> Customer:
    """Update customer and invalidate cache."""
    
    # Update in database
    customer = await update_customer_in_db(customer_id, tenant_id, update_data)
    
    # Invalidate cache
    cache_key = f"customer:{tenant_id}:{customer_id}"
    await cache.delete(cache_key)
    
    return customer
```

### Async Best Practices

```python
# Use async/await effectively
import asyncio
from typing import List

# Good: Concurrent operations
async def send_notifications_to_customers(customers: List[Customer]) -> None:
    """Send notifications concurrently."""
    
    tasks = []
    for customer in customers:
        if customer.email_notifications:
            tasks.append(send_email_notification(customer.email))
        if customer.sms_notifications:
            tasks.append(send_sms_notification(customer.phone))
    
    # Execute all notifications concurrently
    await asyncio.gather(*tasks, return_exceptions=True)

# Good: Batch database operations
async def create_multiple_customers(
    tenant_id: UUID,
    customers_data: List[CustomerCreate]
) -> List[Customer]:
    """Create multiple customers in batch."""
    
    async with db.begin():  # Single transaction
        customers = []
        for customer_data in customers_data:
            customer = Customer(
                tenant_id=tenant_id,
                **customer_data.dict()
            )
            db.add(customer)
            customers.append(customer)
        
        await db.flush()  # Get IDs without committing
        
        # Create portal accounts concurrently
        portal_tasks = [
            create_portal_account_for_customer(customer)
            for customer in customers
        ]
        await asyncio.gather(*portal_tasks)
        
        await db.commit()
        return customers

# Bad: Sequential operations when parallel is possible
# for customer in customers:
#     await send_email_notification(customer.email)  # Blocks each iteration
```

## Deployment Process

### Environment Configuration

#### Production Settings
```python
# core/settings.py
from pydantic import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # Application
    app_name: str = "DotMac ISP Framework"
    debug: bool = False
    environment: str = "production"
    
    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Security
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    
    # Portal ID System
    portal_id_length: int = 8
    portal_max_login_attempts: int = 5
    portal_lockout_duration_minutes: int = 30
    
    # Redis
    redis_url: str
    redis_pool_size: int = 10
    
    # CORS
    allowed_origins: List[str] = ["https://portal.yourisp.com"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Validate settings on startup
@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

#### Docker Production Setup
```dockerfile
# Dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-dev

FROM python:3.11-slim as runtime

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
WORKDIR /app
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Expose port
EXPOSE 8000

# Command
CMD ["uvicorn", "dotmac_isp.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### CI/CD Pipeline

#### GitHub Actions Workflow
```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: dotmac_isp_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
    
    - name: Install dependencies
      run: poetry install
    
    - name: Run linting
      run: |
        poetry run black --check .
        poetry run isort --check-only .
        poetry run flake8 .
        poetry run mypy .
    
    - name: Run security checks
      run: |
        poetry run bandit -r src/
        poetry run safety check
    
    - name: Run tests
      run: poetry run pytest --cov=dotmac_isp --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/dotmac_isp_test
        REDIS_URL: redis://localhost:6379/0
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
  
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Login to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ghcr.io/${{ github.repository }}:latest
        cache-from: type=gha
        cache-to: type=gha,mode=max
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to production
      run: |
        # Deployment script would go here
        # This could trigger Kubernetes deployment, 
        # AWS ECS update, or other deployment mechanism
        echo "Deploying to production..."
```

### Database Migration Strategy

```python
# scripts/migrate.py
"""Database migration script for production deployments."""

import asyncio
import logging
from alembic import command
from alembic.config import Config

from dotmac_isp.core.settings import get_settings

logger = logging.getLogger(__name__)

async def run_migrations():
    """Run database migrations safely."""
    
    settings = get_settings()
    
    # Create Alembic configuration
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    
    try:
        logger.info("Starting database migration...")
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migrations())
```

## Troubleshooting

### Common Development Issues

#### Database Connection Issues
```python
# Debug database connectivity
async def debug_database_connection():
    """Debug database connection issues."""
    
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Database connection successful: {result.scalar()}")
    except Exception as e:
        print(f"Database connection failed: {e}")
        
        # Check common issues
        print("Troubleshooting checklist:")
        print("1. Is PostgreSQL running?")
        print("2. Are credentials correct?") 
        print("3. Is database accessible from this network?")
        print("4. Are connection pool settings appropriate?")
```

#### Authentication Issues
```python
# Debug JWT token issues
def debug_jwt_token(token: str):
    """Debug JWT token problems."""
    
    try:
        # Decode without verification first
        unverified = jwt.decode(token, options={"verify_signature": False})
        print(f"Token payload: {unverified}")
        
        # Check expiration
        exp = unverified.get("exp")
        if exp:
            exp_time = datetime.fromtimestamp(exp)
            now = datetime.utcnow()
            print(f"Token expires: {exp_time}")
            print(f"Current time: {now}")
            print(f"Token expired: {now > exp_time}")
        
        # Verify signature
        verified = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        print("Token signature valid")
        
    except jwt.ExpiredSignatureError:
        print("Token has expired")
    except jwt.InvalidSignatureError:
        print("Token signature invalid")
    except jwt.InvalidTokenError as e:
        print(f"Token invalid: {e}")
```

### Performance Debugging

```python
# Database query performance monitoring
import time
from sqlalchemy import event

@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(engine, "after_cursor_execute")  
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    if total > 0.1:  # Log slow queries (>100ms)
        logger.warning(f"Slow query: {total:.3f}s - {statement[:100]}")

# Memory usage monitoring
import psutil
import os

def log_memory_usage():
    """Log current memory usage."""
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    logger.info(f"Memory usage: {memory_mb:.1f} MB")
```

### Logging and Monitoring

```python
# Structured logging configuration
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """Configure structured logging."""
    
    # Create formatter
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    
    # Configure handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Configure logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    # Configure third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

# Application metrics
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
active_sessions = Gauge('portal_active_sessions', 'Number of active portal sessions')

# Middleware for metrics collection
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record metrics
    duration = time.time() - start_time
    request_count.labels(method=request.method, endpoint=request.url.path).inc()
    request_duration.observe(duration)
    
    return response
```

This comprehensive developer guide provides all the necessary information for effectively developing with the DotMac ISP Framework, ensuring code quality, security, and performance standards are maintained throughout the development lifecycle.