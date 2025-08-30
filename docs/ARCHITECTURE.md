# DotMac Platform Architecture Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Component Architecture](#component-architecture)
4. [Container Lifecycle Architecture](#container-lifecycle-architecture)
5. [Data Architecture](#data-architecture)
6. [Security Architecture](#security-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Technology Stack](#technology-stack)

## System Overview

DotMac is a enterprise-grade SaaS platform designed for Internet Service Providers (ISPs) to manage their operations, customers, and infrastructure. The platform employs a **container-per-tenant** architecture ensuring complete data isolation and security.

### Key Characteristics

- **Multi-tenant SaaS**: Isolated tenant environments with shared infrastructure
- **Modular Monolith**: Service-oriented design within a monolithic deployment
- **Cloud-Native**: Kubernetes-ready with horizontal scaling capabilities
- **Enterprise Security**: SSL/TLS encryption, rate limiting, and automated failover

## Architecture Principles

### 1. Domain-Driven Design (DDD)

- **Bounded Contexts**: Clear separation between business domains (Customer, Billing, Network, Support)
- **Aggregate Roots**: Well-defined entity boundaries with consistent transaction scopes
- **Value Objects**: Immutable domain concepts (Money, IPAddress, ServicePlan)

### 2. SOLID Principles

- **Single Responsibility**: Each module handles one business capability
- **Open/Closed**: Extension through plugins without core modifications
- **Liskov Substitution**: Interface-based contracts for all services
- **Interface Segregation**: Focused interfaces for specific operations
- **Dependency Inversion**: Core business logic independent of infrastructure

### 3. Security by Design

- **Zero Trust**: All communications encrypted and authenticated
- **Defense in Depth**: Multiple security layers (WAF, rate limiting, encryption)
- **Least Privilege**: Minimal permissions for all components
- **Audit Trail**: Comprehensive logging and monitoring

## Component Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React UI]
        HL[Headless Components]
        DS[Design System]
    end

    subgraph "API Gateway"
        NG[Nginx]
        RL[Rate Limiter]
        LB[Load Balancer]
    end

    subgraph "Application Layer"
        API[FastAPI Services]
        WS[WebSocket Handler]
        BG[Background Workers]
    end

    subgraph "Business Logic"
        CM[Customer Module]
        BM[Billing Module]
        NM[Network Module]
        SM[Support Module]
    end

    subgraph "Data Layer"
        PG[PostgreSQL]
        RD[Redis]
        S3[Object Storage]
    end

    subgraph "Infrastructure"
        K8S[Kubernetes]
        MON[Monitoring]
        LOG[Logging]
    end

    UI --> NG
    HL --> NG
    NG --> API
    API --> CM
    API --> BM
    API --> NM
    API --> SM
    CM --> PG
    BM --> PG
    NM --> PG
    SM --> PG
    API --> RD
    API --> S3
    K8S --> MON
    K8S --> LOG
```

## Container Lifecycle Architecture

### Simplified Startup/Shutdown Design

The platform implements a **streamlined container lifecycle** with significant improvements over traditional approaches:

#### ✅ Performance Improvements

- **66.7% Code Reduction**: From 300+ lines to ~100 lines
- **5x Faster Startup**: 0.50s → 0.10s initialization time
- **Phase-Based Dependencies**: 6 ordered initialization phases
- **Better Error Handling**: Critical vs non-critical failure classification

#### Initialization Phases

```mermaid
graph TD
    A[Container Start] --> B[Phase 1: Critical Foundation]
    B --> C[Phase 2: Core Services]
    C --> D[Phase 3: Infrastructure]
    D --> E[Phase 4: Security & API]
    E --> F[Phase 5: Real-time Services]
    F --> G[Phase 6: Health Monitoring]
    G --> H[Service Ready]

    B --> B1[Database Connection]
    B --> B2[Observability Setup]

    C --> C1[Row Level Security]
    C --> C2[Tenant Security]

    D --> D1[Cache Layer]
    D --> D2[Middleware Stack]

    E --> E1[Authentication]
    E --> E2[Rate Limiting]

    F --> F1[WebSocket Manager]
    F --> F2[Event System]

    G --> G1[Health Dependencies]
    G --> G2[Readiness Checks]
```

#### Container State Management

```mermaid
stateDiagram-v2
    [*] --> Starting
    Starting --> Initializing: Container startup
    Initializing --> Ready: All phases complete
    Ready --> Healthy: Health checks pass
    Healthy --> ShuttingDown: SIGTERM received
    ShuttingDown --> [*]: Graceful shutdown complete

    Initializing --> Failed: Critical failure
    Failed --> [*]: Container restart
    Healthy --> Unhealthy: Health check fails
    Unhealthy --> Healthy: Health restored
    Unhealthy --> ShuttingDown: Manual shutdown
```

### Kubernetes Health Probe Integration

#### Health Endpoint Architecture

```python
# Container Lifecycle Manager
class ContainerLifecycleManager:
    def setup_health_endpoints(self):
        # /health/live - Liveness probe
        # /health/ready - Readiness probe
        # /health/startup - Startup probe
        # /health - Legacy compatibility
```

#### Probe Configuration Strategy

| Probe Type | Endpoint | Purpose | Failure Action |
|------------|----------|---------|----------------|
| **Liveness** | `/health/live` | Container should restart | Pod restart |
| **Readiness** | `/health/ready` | Traffic acceptance | Remove from service |
| **Startup** | `/health/startup` | Initialization complete | Delay other probes |

#### Health Dependencies

```mermaid
graph LR
    A[Health Check] --> B[Database]
    A --> C[Cache]
    A --> D[Observability]
    A --> E[External APIs]

    B --> B1[Connection Pool]
    B --> B2[Query Performance]

    C --> C1[Redis Connection]
    C --> C2[Cache Hit Rate]

    D --> D1[SignOz Endpoint]
    D --> D2[Metrics Collection]
```

### Graceful Shutdown Architecture

#### Signal Handling Flow

```mermaid
sequenceDiagram
    participant K8s as Kubernetes
    participant App as Application
    participant DB as Database
    participant Cache as Cache

    K8s->>App: SIGTERM Signal
    App->>App: Mark as shutting down
    App->>App: Stop accepting new requests
    App->>App: Wait for existing requests (30s timeout)
    App->>Cache: Close connections
    App->>DB: Close connection pool
    App->>K8s: Container exit (0)
```

#### Resource Cleanup Strategy

1. **Immediate**: Stop accepting new requests
2. **Graceful**: Allow existing requests to complete (30s max)
3. **Cleanup**: Close database connections, cache clients
4. **Exit**: Clean container termination

### Frontend Architecture

#### React Application (`/frontend`)

- **Framework**: React 18 with TypeScript
- **State Management**: Zustand for global state
- **Routing**: React Router v6
- **Styling**: Tailwind CSS with custom design system
- **Forms**: React Hook Form with Zod validation
- **API Client**: Axios with automatic retry and error handling

#### Headless Components (`/frontend/packages/headless`)

- Unstyled, accessible UI components
- WCAG 2.1 AA compliant
- Keyboard navigation support
- Screen reader optimized

### Backend Architecture

#### FastAPI Application (`/isp-framework`)

- **Framework**: FastAPI with async/await
- **ORM**: SQLAlchemy 2.0 with async support
- **Validation**: Pydantic v2 models
- **Authentication**: JWT with refresh tokens
- **Authorization**: Role-based access control (RBAC)
- **WebSockets**: Real-time updates for monitoring

#### Core Modules

##### Customer Management

```python
/isp-framework/src/dotmac_isp/modules/customer/
├── models.py       # SQLAlchemy models
├── schemas.py      # Pydantic schemas
├── service.py      # Business logic
├── repository.py   # Data access layer
└── api.py         # REST endpoints
```

##### Billing System

```python
/isp-framework/src/dotmac_isp/modules/billing/
├── models.py       # Invoice, Payment models
├── engine.py       # Billing calculation engine
├── recurring.py    # Subscription management
├── payment.py      # Payment processing
└── api.py         # Billing endpoints
```

##### Network Management

```python
/isp-framework/src/dotmac_isp/modules/network/
├── models.py       # Equipment, Circuit models
├── ipam.py        # IP address management
├── monitoring.py   # Network monitoring
├── automation.py   # Provisioning automation
└── api.py         # Network endpoints
```

## Data Architecture

### Database Design

#### PostgreSQL Schema

```sql
-- Tenant isolation through schemas
CREATE SCHEMA tenant_001;
CREATE SCHEMA tenant_002;

-- Shared tables in public schema
public.tenants
public.licenses
public.audit_logs

-- Tenant-specific tables
tenant_001.customers
tenant_001.invoices
tenant_001.services
```

#### Data Partitioning Strategy

- **Horizontal Partitioning**: Time-series data (logs, metrics)
- **Vertical Partitioning**: Large objects in separate tables
- **Schema-per-tenant**: Complete isolation for multi-tenant data

### Caching Strategy

#### Redis Layers

1. **Session Cache**: User sessions and auth tokens (TTL: 1 hour)
2. **API Cache**: Frequently accessed data (TTL: 5 minutes)
3. **Rate Limiting**: Request counters (TTL: varies)
4. **Queue**: Background job processing

### Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant Nginx
    participant FastAPI
    participant Redis
    participant PostgreSQL

    Client->>Nginx: HTTPS Request
    Nginx->>Nginx: Rate Limit Check
    Nginx->>FastAPI: Proxy Request
    FastAPI->>Redis: Check Cache
    alt Cache Hit
        Redis-->>FastAPI: Cached Data
    else Cache Miss
        FastAPI->>PostgreSQL: Query Database
        PostgreSQL-->>FastAPI: Result Set
        FastAPI->>Redis: Update Cache
    end
    FastAPI-->>Nginx: JSON Response
    Nginx-->>Client: HTTPS Response
```

## Security Architecture

### Authentication & Authorization

#### JWT Token Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Redis

    User->>Frontend: Login Credentials
    Frontend->>API: POST /auth/login
    API->>API: Validate Credentials
    API->>Redis: Store Session
    API-->>Frontend: Access + Refresh Tokens
    Frontend->>Frontend: Store Tokens
    Frontend->>API: API Request + Access Token
    API->>API: Validate Token
    API-->>Frontend: Protected Resource
```

### Security Layers

1. **Network Security**
   - Cloudflare WAF (optional)
   - Nginx rate limiting
   - DDoS protection
   - Geo-blocking capabilities

2. **Application Security**
   - Input validation (Pydantic)
   - SQL injection prevention (SQLAlchemy)
   - XSS protection (React)
   - CSRF tokens
   - Secure headers

3. **Data Security**
   - Encryption at rest (PostgreSQL)
   - Encryption in transit (TLS 1.3)
   - Field-level encryption for PII
   - Secure key management (HashiCorp Vault)

4. **Infrastructure Security**
   - Container scanning
   - Dependency scanning
   - Secret management
   - Network policies

### Rate Limiting Architecture

```python
# Redis-based distributed rate limiting
Rate Limits:
- API: 100 requests/minute per user
- Login: 5 attempts/minute per IP
- Search: 30 requests/minute per tenant
- Bulk operations: 10 requests/hour
```

## Deployment Architecture

### Kubernetes Deployment

```yaml
# High-level deployment structure
Namespaces:
├── dotmac-system      # Platform services
├── dotmac-tenants     # Tenant containers
├── dotmac-monitoring  # Observability stack
└── dotmac-security    # Security tools

Deployments:
├── frontend          # React application
├── api-gateway       # Nginx ingress
├── api-backend       # FastAPI replicas
├── worker            # Background jobs
├── postgresql        # Database cluster
└── redis            # Cache cluster
```

### High Availability Setup

```mermaid
graph LR
    subgraph "Load Balancer"
        LB[HAProxy/Nginx]
    end

    subgraph "Application Tier"
        API1[API Server 1]
        API2[API Server 2]
        API3[API Server 3]
    end

    subgraph "Database Tier"
        PG1[PostgreSQL Primary]
        PG2[PostgreSQL Standby]
        PG3[PostgreSQL Standby]
    end

    subgraph "Cache Tier"
        R1[Redis Primary]
        R2[Redis Replica]
    end

    LB --> API1
    LB --> API2
    LB --> API3

    API1 --> PG1
    API2 --> PG1
    API3 --> PG1

    PG1 -.->|Streaming Replication| PG2
    PG1 -.->|Streaming Replication| PG3

    API1 --> R1
    API2 --> R1
    API3 --> R1

    R1 -.->|Replication| R2
```

### Disaster Recovery

#### Backup Strategy

- **Database**: Daily full backups, hourly incrementals
- **File Storage**: Continuous sync to S3-compatible storage
- **Configuration**: Git-based version control
- **Secrets**: Encrypted backups of Vault data

#### Recovery Objectives

- **RTO (Recovery Time Objective)**: 1 hour
- **RPO (Recovery Point Objective)**: 1 hour
- **Failover Time**: < 5 minutes (automated)

## Technology Stack

### Core Technologies

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Frontend** | React | 18.x | UI Framework |
| | TypeScript | 5.x | Type Safety |
| | Tailwind CSS | 3.x | Styling |
| | Vite | 5.x | Build Tool |
| **Backend** | Python | 3.11+ | Runtime |
| | FastAPI | 0.104+ | Web Framework |
| | SQLAlchemy | 2.0+ | ORM |
| | Pydantic | 2.x | Validation |
| **Database** | PostgreSQL | 14+ | Primary Database |
| | Redis | 7+ | Cache & Queue |
| | MinIO | Latest | Object Storage |
| **Infrastructure** | Docker | 24+ | Containerization |
| | Kubernetes | 1.28+ | Orchestration |
| | Nginx | 1.24+ | Reverse Proxy |
| | Prometheus | 2.x | Monitoring |

### Development Tools

| Tool | Purpose | Configuration |
|------|---------|--------------|
| **Black** | Python Formatting | `line-length=88` |
| **Ruff** | Python Linting | Strict mode |
| **MyPy** | Type Checking | `strict=true` |
| **Pytest** | Testing | Coverage > 80% |
| **ESLint** | JS Linting | Airbnb config |
| **Prettier** | JS Formatting | Standard config |
| **Playwright** | E2E Testing | Cross-browser |
| **Storybook** | Component Development | v7+ |

## Performance Considerations

### Optimization Strategies

1. **Database Performance**
   - Connection pooling (pgBouncer)
   - Query optimization (EXPLAIN ANALYZE)
   - Proper indexing strategy
   - Materialized views for reports

2. **API Performance**
   - Response caching
   - Pagination for large datasets
   - Lazy loading relationships
   - Background job processing

3. **Frontend Performance**
   - Code splitting
   - Lazy loading routes
   - Image optimization
   - CDN for static assets

### Scalability Targets

| Metric | Target | Current Capability |
|--------|--------|-------------------|
| Concurrent Users | 10,000 | 5,000 |
| API Requests/sec | 1,000 | 500 |
| Database Connections | 500 | 200 |
| Response Time (p95) | < 200ms | < 300ms |
| Uptime | 99.9% | 99.5% |

## Monitoring & Observability

### Metrics Collection

```mermaid
graph LR
    subgraph "Application"
        APP[FastAPI App]
        METRICS[/metrics endpoint]
    end

    subgraph "Collection"
        PROM[Prometheus]
        LOKI[Loki]
        TEMPO[Tempo]
    end

    subgraph "Visualization"
        GRAF[Grafana]
        ALERT[AlertManager]
    end

    APP --> METRICS
    METRICS --> PROM
    APP --> LOKI
    APP --> TEMPO
    PROM --> GRAF
    LOKI --> GRAF
    TEMPO --> GRAF
    PROM --> ALERT
```

### Key Metrics

#### Application Metrics

- Request rate and latency
- Error rate by endpoint
- Active connections
- Queue depth

#### Business Metrics

- Active tenants
- Revenue per tenant
- Feature usage
- Support ticket volume

#### Infrastructure Metrics

- CPU and memory usage
- Disk I/O
- Network throughput
- Container health

## API Design Standards

### RESTful Conventions

```http
GET    /api/v1/customers           # List
GET    /api/v1/customers/{id}      # Retrieve
POST   /api/v1/customers           # Create
PUT    /api/v1/customers/{id}      # Update
PATCH  /api/v1/customers/{id}      # Partial update
DELETE /api/v1/customers/{id}      # Delete
```

### Response Format

```json
{
  "data": {
    "id": "123",
    "type": "customer",
    "attributes": {}
  },
  "meta": {
    "timestamp": "2024-08-24T20:00:00Z",
    "version": "1.0"
  },
  "links": {
    "self": "/api/v1/customers/123"
  }
}
```

### Error Handling

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "req_123456"
  }
}
```

---

*Last Updated: August 2024*
*Version: 1.0*
*Maintained by: DotMac Engineering Team*
