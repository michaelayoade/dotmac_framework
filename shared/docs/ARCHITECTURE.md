# DotMac SaaS Platform Architecture

## Overview

The DotMac SaaS Platform is built using a **container-per-tenant architecture** where each ISP receives a dedicated, isolated container managed by the platform owner. This document provides a comprehensive overview of the SaaS platform architecture, multi-tenant design patterns, and container orchestration decisions.

## SaaS Architecture Principles

### 1. Container-per-Tenant Isolation
- **Complete Tenant Isolation**: Each ISP gets a dedicated container with isolated resources
- **Platform Owner Management**: All infrastructure managed centrally by platform owner
- **Automatic Scaling**: Containers scale based on ISP customer count and usage
- **Zero ISP Infrastructure**: ISPs never manage servers, databases, or Kubernetes

### 2. Usage-Based SaaS Model
- **Per-Customer Pricing**: Revenue based on ISP customer count with usage-based billing
- **Premium Bundle Marketplace**: Additional features as monthly bundles (CRM, Project Management, AI)
- **Vendor/Reseller Network**: Commission-based partner program for sales channels
- **Automated Billing**: Precise customer counting and automated invoice generation

### 3. Multi-Tenant Platform Management
- **Centralized Orchestration**: Single management platform controls all tenant containers
- **Unified Monitoring**: Fleet-wide observability across all ISP tenant containers
- **Shared Infrastructure**: Efficient resource utilization with tenant isolation
- **Container Lifecycle**: Automated provisioning, scaling, backup, and recovery

### 4. Security & Compliance for SaaS
- **Tenant Data Isolation**: Complete separation of ISP data with encrypted boundaries
- **Multi-Tenant Secrets**: OpenBao with per-tenant namespaces and automatic rotation
- **Compliance Ready**: SOC2, GDPR, PCI DSS compliance built into platform
- **Platform-Level Security**: Centralized security policies across all tenant containers

## SaaS Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          DotMac SaaS Platform Owner                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                    Platform Management & Orchestration                         │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐ │
│  │ Platform Admin  │  │ Vendor/Reseller │  │    Fleet Monitoring             │ │
│  │ Portal          │  │ Partner Portal  │  │    (SignOz)                     │ │
│  │ (Port 3000)     │  │ (Port 3002)     │  │    (Port 3301)                  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────────┘ │
│                                     │                                         │
│                        ┌─────────────────────────────────┐                    │
│                        │    Management Platform API     │                    │
│                        │    • Tenant Provisioning       │                    │
│                        │    • Usage-Based Billing       │                    │
│                        │    • Container Orchestration   │                    │
│                        │    • Premium Bundle Licensing  │                    │
│                        │    (Port 8000)                 │                    │
│                        └─────────────────────────────────┘                    │
│                                     │                                         │
├─────────────────────────────────────┼─────────────────────────────────────────┤
│                  Shared SaaS Infrastructure                                    │
│                                     │                                         │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐   │
│ │ PostgreSQL  │ │   Redis     │ │  OpenBao    │ │   Container Registry    │   │
│ │ (Platform)  │ │ (Shared)    │ │(Multi-Tenant│ │   (Platform Images)     │   │
│ │(Port 5434)  │ │(Port 6378)  │ │Secrets)     │ │                         │   │
│ └─────────────┘ └─────────────┘ │(Port 8200)  │ └─────────────────────────┘   │
│                                 └─────────────┘                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                           Container-per-Tenant Isolation                       │
│                                                                                 │
│ ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────────┐   │
│ │   ISP-Alpha         │ │   ISP-Beta          │ │   ISP-Gamma             │   │
│ │   Container         │ │   Container         │ │   Container             │   │
│ │                     │ │                     │ │                         │   │
│ │ ┌─────────────────┐ │ │ ┌─────────────────┐ │ │ ┌─────────────────────┐ │   │
│ │ │ ISP Framework   │ │ │ │ ISP Framework   │ │ │ │ ISP Framework       │ │   │
│ │ │ Application     │ │ │ │ Application     │ │ │ │ Application         │ │   │
│ │ │ (Port 8101)     │ │ │ │ (Port 8102)     │ │ │ │ (Port 8103)         │ │   │
│ │ └─────────────────┘ │ │ └─────────────────┘ │ │ └─────────────────────┘ │   │
│ │                     │ │                     │ │                         │   │
│ │ ┌─────────────────┐ │ │ ┌─────────────────┐ │ │ ┌─────────────────────┐ │   │
│ │ │ PostgreSQL      │ │ │ │ PostgreSQL      │ │ │ │ PostgreSQL          │ │   │
│ │ │ (Isolated DB)   │ │ │ │ (Isolated DB)   │ │ │ │ (Isolated DB)       │ │   │
│ │ └─────────────────┘ │ │ └─────────────────┘ │ │ └─────────────────────┘ │   │
│ │                     │ │                     │ │                         │   │
│ │ ┌─────────────────┐ │ │ ┌─────────────────┐ │ │ ┌─────────────────────┐ │   │
│ │ │Customer Portals │ │ │ │Customer Portals │ │ │ │Customer Portals     │ │   │
│ │ │& APIs           │ │ │ │& APIs           │ │ │ │& APIs               │ │   │
│ │ └─────────────────┘ │ │ └─────────────────┘ │ │ └─────────────────────┘ │   │
│ └─────────────────────┘ └─────────────────────┘ └─────────────────────────┘   │
│        500 customers        1,200 customers         3,000 customers           │
│    Usage-based pricing     Scaled pricing      Enterprise pricing             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Service Breakdown

### Core Services

#### 1. dotmac_identity
**Purpose**: Authentication, authorization, and user management

**Responsibilities**:
- User authentication (JWT tokens)
- Role-based access control (RBAC)
- Multi-tenant isolation
- Session management
- Password policies

**Technology Stack**:
- FastAPI for REST APIs
- SQLAlchemy for ORM
- JWT for token management
- bcrypt for password hashing

**Data Models**:
```python
class User(Base):
    id: UUID
    email: str
    password_hash: str
    is_active: bool
    tenant_id: UUID
    roles: List[Role]
    created_at: datetime
    last_login: datetime

class Role(Base):
    id: UUID
    name: str
    permissions: List[Permission]
    tenant_id: UUID

class Permission(Base):
    id: UUID
    resource: str
    action: str  # create, read, update, delete
```

#### 2. dotmac_billing
**Purpose**: Billing, invoicing, and payment processing

**Responsibilities**:
- Invoice generation
- Payment processing (Stripe integration)
- Subscription management
- Billing cycles
- Dunning management

**Technology Stack**:
- FastAPI for REST APIs
- Stripe SDK for payments
- Celery for background tasks
- SQLAlchemy for data persistence

**Data Models**:
```python
class Invoice(Base):
    id: UUID
    customer_id: UUID
    amount: Decimal
    status: InvoiceStatus
    due_date: date
    line_items: List[LineItem]
    
class Payment(Base):
    id: UUID
    invoice_id: UUID
    amount: Decimal
    status: PaymentStatus
    stripe_payment_intent_id: str
    processed_at: datetime

class Subscription(Base):
    id: UUID
    customer_id: UUID
    service_id: UUID
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    next_billing_date: date
```

#### 3. dotmac_services
**Purpose**: Service provisioning and lifecycle management

**Responsibilities**:
- Service catalog management
- Service provisioning
- Configuration management
- Service monitoring
- Lifecycle automation

**Technology Stack**:
- FastAPI for REST APIs
- Ansible for configuration management
- Docker for service isolation
- Redis for job queues

**Data Models**:
```python
class Service(Base):
    id: UUID
    customer_id: UUID
    service_type: ServiceType
    configuration: dict
    status: ServiceStatus
    provisioned_at: datetime
    
class ServiceTemplate(Base):
    id: UUID
    name: str
    service_type: ServiceType
    default_configuration: dict
    provisioning_script: str

class ServiceInstance(Base):
    id: UUID
    service_id: UUID
    instance_type: str
    ip_address: str
    configuration: dict
    health_status: HealthStatus
```

### Supporting Services

#### 4. dotmac_networking
**Purpose**: Network infrastructure management

**Responsibilities**:
- Network device discovery
- SNMP monitoring
- Bandwidth management
- Network topology mapping
- Performance monitoring

#### 5. dotmac_analytics
**Purpose**: Business intelligence and reporting

**Responsibilities**:
- Data aggregation
- Report generation
- Dashboard APIs
- KPI calculations
- Trend analysis

#### 6. dotmac_api_gateway
**Purpose**: API routing and management

**Responsibilities**:
- Request routing
- Rate limiting
- Authentication middleware
- Load balancing
- API versioning

## Event-Driven Architecture

### Event Flow

```
Service A                Event Bus               Service B
    │                       │                       │
    │ 1. Publish Event      │                       │
    ├──────────────────────►│                       │
    │                       │ 2. Route Event       │
    │                       ├──────────────────────►│
    │                       │                       │ 3. Process Event
    │                       │                       ├─────────────────┐
    │                       │                       │                 │
    │                       │ 4. Publish Result    │◄────────────────┘
    │                       │◄──────────────────────┤
    │ 5. Receive Result     │                       │
    │◄──────────────────────┤                       │
    │                       │                       │
```

### Event Types

#### Domain Events
Events that represent business state changes:
```python
@dataclass
class CustomerCreatedEvent:
    customer_id: UUID
    email: str
    tenant_id: UUID
    timestamp: datetime
    event_type: str = "customer.created"

@dataclass
class ServiceProvisionedEvent:
    service_id: UUID
    customer_id: UUID
    service_type: str
    configuration: dict
    timestamp: datetime
    event_type: str = "service.provisioned"
```

#### Integration Events
Events for cross-service coordination:
```python
@dataclass
class BillingCycleStartedEvent:
    billing_cycle_id: UUID
    start_date: date
    end_date: date
    customer_count: int
    timestamp: datetime
    event_type: str = "billing.cycle_started"
```

### Event Sourcing Pattern

For critical business entities, we implement event sourcing:

```python
class CustomerAggregate:
    def __init__(self, customer_id: UUID):
        self.customer_id = customer_id
        self.events: List[DomainEvent] = []
        self.version = 0
    
    def create_customer(self, email: str, tenant_id: UUID):
        event = CustomerCreatedEvent(
            customer_id=self.customer_id,
            email=email,
            tenant_id=tenant_id,
            timestamp=datetime.now(timezone.utc)
        )
        self.apply_event(event)
    
    def apply_event(self, event: DomainEvent):
        self.events.append(event)
        self.version += 1
        # Apply event to update state
```

## Data Architecture

### Database Strategy

#### Primary Database (PostgreSQL)
- **Transactional Data**: Customer records, orders, configurations
- **ACID Compliance**: Ensures data consistency
- **JSON Support**: Flexible schema for configuration data
- **Full-Text Search**: For customer and service searches

#### Cache Layer (Redis)
- **Session Storage**: User sessions and JWT blacklists
- **Application Cache**: Frequently accessed data
- **Job Queues**: Background task processing
- **Pub/Sub**: Real-time event distribution

#### Time-Series Database (TimescaleDB)
- **Metrics Storage**: Performance and monitoring data
- **Log Aggregation**: Application and system logs
- **Analytics**: Historical trend analysis
- **Automatic Partitioning**: Efficient time-based queries

### Data Consistency Strategy

#### Eventual Consistency
For cross-service operations, we accept eventual consistency:
- **Saga Pattern**: Coordinate long-running transactions
- **Compensation**: Rollback operations on failure
- **Idempotency**: Safe retry mechanisms

#### Strong Consistency
Within service boundaries, we maintain strong consistency:
- **Database Transactions**: ACID properties
- **Optimistic Locking**: Prevent concurrent modifications
- **Foreign Key Constraints**: Referential integrity

## Security Architecture

### Authentication Flow

```
Client                  API Gateway            Identity Service
  │                         │                         │
  │ 1. Login Request        │                         │
  ├────────────────────────►│                         │
  │                         │ 2. Validate Credentials│
  │                         ├────────────────────────►│
  │                         │                         │ 3. Generate JWT
  │                         │                         ├──────────────┐
  │                         │ 4. Return JWT          │              │
  │                         │◄────────────────────────┤◄─────────────┘
  │ 5. JWT Response         │                         │
  │◄────────────────────────┤                         │
  │                         │                         │
  │ 6. API Request + JWT    │                         │
  ├────────────────────────►│                         │
  │                         │ 7. Validate JWT        │
  │                         ├─────────────────┐       │
  │                         │                 │       │
  │                         │ 8. Proceed      │       │
  │                         │◄────────────────┘       │
```

### Authorization Model

#### Role-Based Access Control (RBAC)
```python
class Permission:
    resource: str  # "customers", "invoices", "services"
    action: str    # "create", "read", "update", "delete"
    scope: str     # "own", "tenant", "global"

class Role:
    name: str
    permissions: List[Permission]

# Example roles
CUSTOMER_USER = Role(
    name="customer_user",
    permissions=[
        Permission("services", "read", "own"),
        Permission("invoices", "read", "own"),
        Permission("payments", "create", "own")
    ]
)

ADMIN_USER = Role(
    name="admin",
    permissions=[
        Permission("*", "*", "tenant")
    ]
)
```

#### Multi-Tenant Isolation
- **Tenant ID**: Every entity has a tenant_id
- **Row-Level Security**: Database-level isolation
- **API Filters**: Automatic tenant filtering
- **Data Encryption**: Tenant-specific encryption keys

### Network Security

#### API Security
- **TLS/HTTPS**: All communication encrypted
- **CORS Policies**: Cross-origin request restrictions
- **Rate Limiting**: DoS protection
- **Input Validation**: Prevent injection attacks

#### Service Mesh (Future)
- **mTLS**: Service-to-service encryption
- **Service Discovery**: Secure service communication
- **Traffic Policies**: Fine-grained access control
- **Observability**: Traffic monitoring and logging

## Scalability Patterns

### Horizontal Scaling
- **Stateless Services**: Easy to scale horizontally
- **Load Balancing**: Distribute traffic across instances
- **Database Sharding**: Split data across databases
- **Caching Strategies**: Reduce database load

### Performance Optimization
- **Connection Pooling**: Efficient database connections
- **Async I/O**: Non-blocking operations
- **Background Jobs**: Offload heavy processing
- **CDN Integration**: Static asset delivery

### Monitoring and Observability

#### Metrics Collection
```python
from prometheus_client import Counter, Histogram, Gauge

# Business metrics
customer_registrations = Counter(
    'customer_registrations_total',
    'Total customer registrations',
    ['tenant_id']
)

invoice_generation_time = Histogram(
    'invoice_generation_duration_seconds',
    'Time spent generating invoices',
    ['invoice_type']
)

active_services = Gauge(
    'active_services_count',
    'Number of active services',
    ['service_type', 'tenant_id']
)
```

#### Distributed Tracing
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def process_payment(payment_request):
    with tracer.start_as_current_span("payment_processing") as span:
        span.set_attribute("payment.amount", payment_request.amount)
        span.set_attribute("payment.method", payment_request.method)
        
        # Process payment
        result = await payment_processor.charge(payment_request)
        
        span.set_attribute("payment.status", result.status)
        return result
```

## Deployment Architecture

### Container Strategy
```dockerfile
# Multi-stage build for optimization
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

FROM python:3.11-slim as runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ /app/
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotmac-identity-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dotmac-identity
  template:
    metadata:
      labels:
        app: dotmac-identity
    spec:
      containers:
      - name: identity-service
        image: dotmac/identity:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Development Patterns

### Repository Pattern
```python
from abc import ABC, abstractmethod

class CustomerRepository(ABC):
    @abstractmethod
    async def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        pass
    
    @abstractmethod
    async def create(self, customer: Customer) -> Customer:
        pass
    
    @abstractmethod
    async def update(self, customer: Customer) -> Customer:
        pass

class SqlAlchemyCustomerRepository(CustomerRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        result = await self.session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()
```

### Dependency Injection
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def get_customer_repository(
    session: AsyncSession = Depends(get_db_session)
) -> CustomerRepository:
    return SqlAlchemyCustomerRepository(session)

@router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: UUID,
    repository: CustomerRepository = Depends(get_customer_repository)
):
    customer = await repository.get_by_id(customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    return customer
```

### Error Handling Strategy
```python
class DomainError(Exception):
    """Base class for domain-specific errors."""
    pass

class CustomerNotFoundError(DomainError):
    def __init__(self, customer_id: UUID):
        self.customer_id = customer_id
        super().__init__(f"Customer {customer_id} not found")

@app.exception_handler(CustomerNotFoundError)
async def customer_not_found_handler(request: Request, exc: CustomerNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "CUSTOMER_NOT_FOUND",
                "message": str(exc),
                "details": {
                    "customer_id": str(exc.customer_id)
                }
            }
        }
    )
```

## Testing Strategy

### Testing Pyramid
1. **Unit Tests (70%)**: Fast, isolated tests of business logic
2. **Integration Tests (20%)**: Test service interactions
3. **End-to-End Tests (10%)**: Full workflow testing

### Contract Testing
```python
# Consumer contract (Customer Portal)
def test_customer_api_contract():
    """Test that customer API matches expected contract."""
    response = customer_api.get_customer("cust_123")
    
    # Verify contract
    assert response.status_code == 200
    assert "id" in response.json()
    assert "email" in response.json()
    assert "created_at" in response.json()

# Provider contract (Identity Service)
def test_customer_service_provides_contract():
    """Test that service provides expected contract."""
    customer = create_test_customer()
    response = client.get(f"/customers/{customer.id}")
    
    # Verify provider contract
    validate_customer_schema(response.json())
```

## Migration Strategy

### Database Migrations
Using Alembic for schema evolution:
```python
"""Add customer preferences table

Revision ID: 001_customer_preferences
Revises: 000_initial_schema
Create Date: 2024-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'customer_preferences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('preferences', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('customer_preferences')
```

### API Versioning
```python
from fastapi import APIRouter

# Version 1 API
v1_router = APIRouter(prefix="/api/v1")

@v1_router.get("/customers/{customer_id}")
async def get_customer_v1(customer_id: UUID):
    # V1 implementation
    pass

# Version 2 API with new fields
v2_router = APIRouter(prefix="/api/v2")

@v2_router.get("/customers/{customer_id}")
async def get_customer_v2(customer_id: UUID):
    # V2 implementation with new features
    pass
```

## Future Considerations

### Planned Enhancements

1. **Service Mesh Integration**
   - Istio for traffic management
   - mTLS for service communication
   - Advanced observability

2. **Machine Learning Integration**
   - Predictive analytics for network issues
   - Customer churn prediction
   - Automated capacity planning

3. **Multi-Cloud Strategy**
   - Cloud-agnostic deployments
   - Disaster recovery across regions
   - Cost optimization

4. **Advanced Security**
   - Zero-trust architecture
   - Runtime security monitoring
   - Automated threat response

This architecture provides a solid foundation for building a scalable, secure, and maintainable ISP management framework while allowing for future enhancements and evolution.