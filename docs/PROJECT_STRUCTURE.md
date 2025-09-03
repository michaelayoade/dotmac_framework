# DotMac Platform Project Structure

## Overview

The DotMac platform consists of two main components:

### 1. DotMac Management Platform (`dotmac_management`)
**The Master Control Plane** that manages:
- All tenant provisioning and lifecycle
- License assignment and feature control
- Billing and subscription management
- Container orchestration across all tenants
- Global monitoring and analytics
- Partner/reseller relationships

### 2. DotMac ISP Platform (`dotmac_isp`)
**The Tenant Application** deployed per customer with:
- Core ISP functionality (network, billing, auth)
- Licensed feature modules (CRM, tickets, projects, etc.)
- Feature activation controlled by Management Platform
- Complete isolation between tenants

## Directory Structure

```
dotmac_framework/
├── src/                          # Source code
│   ├── dotmac_management/       # MANAGEMENT PLATFORM (Control Plane)
│   │   ├── api/                 # Admin API endpoints
│   │   ├── modules/             # Management modules
│   │   │   ├── tenants/         # Tenant provisioning
│   │   │   ├── licensing/       # License administration
│   │   │   ├── billing/         # Subscription billing
│   │   │   ├── partners/        # Reseller management
│   │   │   └── monitoring/      # Global monitoring
│   │   ├── services/            # Business logic
│   │   └── workers/             # Background jobs
│   │
│   ├── dotmac_isp/              # ISP PLATFORM (Tenant Containers)
│   │   ├── core/                # Core ISP features (always active)
│   │   │   ├── network/         # Network provisioning
│   │   │   ├── billing/         # Customer billing
│   │   │   └── auth/            # Authentication
│   │   └── modules/             # Licensed feature modules
│   │   ├── crm/                 # Customer relationship management
│   │   ├── tickets/             # Support ticketing system
│   │   ├── projects/            # Project management
│   │   ├── fieldops/            # Field operations & dispatch
│   │   └── analytics/           # Business intelligence
│   │
│   ├── dotmac_shared/           # Shared utilities & components
│   │   ├── api/                 # Common API utilities
│   │   ├── database/            # Database utilities
│   │   ├── events/              # Event bus implementation
│   │   └── monitoring/          # Observability tools
│   │
│   └── dotmac_sdk/              # SDKs for platform communication
│       ├── management_client/   # ISP → Management API client
│       └── licensing_client/    # License verification client
│
├── frontend/                     # Frontend applications
│   ├── apps/                    # Portal applications
│   │   ├── customer/            # Customer self-service portal
│   │   ├── admin/               # Admin management portal
│   │   ├── technician/          # Field technician app
│   │   └── reseller/            # Reseller partner portal
│   │
│   └── packages/                # Shared frontend packages
│       ├── ui/                  # UI component library
│       ├── licensing/           # License management components
│       └── api-client/          # API client library
│
├── infrastructure/              # Infrastructure as Code
│   ├── kubernetes/              # K8s manifests
│   ├── terraform/               # Cloud infrastructure
│   └── docker/                  # Container definitions
│
├── migrations/                  # Database migrations
│   ├── core/                   # Core schema migrations
│   └── modules/                # Module-specific migrations
│
├── tests/                      # Test suites
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   ├── e2e/                    # End-to-end tests
│   └── licensing/              # License system tests
│
├── scripts/                    # Utility scripts
│   ├── deployment/             # Deployment automation
│   ├── licensing/              # License management scripts
│   └── development/            # Development tools
│
└── docs/                       # Documentation
    ├── architecture/           # Architecture documentation
    ├── api/                    # API documentation
    ├── licensing/              # Licensing guide
    └── deployment/             # Deployment guides
```

## Module Organization

### Core Modules (`src/dotmac_core/`)
Always active, providing fundamental ISP functionality:

```
dotmac_core/
├── network/
│   ├── models.py               # Network domain models
│   ├── services.py             # Business logic
│   ├── api.py                  # API endpoints
│   └── schemas.py              # Request/response schemas
├── billing/
│   ├── models.py               # Billing domain models
│   ├── services.py             # Payment processing
│   ├── api.py                  # Billing endpoints
│   └── schemas.py              # Billing schemas
└── licensing/
    ├── manager.py              # License management
    ├── decorators.py           # Feature decorators
    ├── models.py               # License models
    └── api.py                  # License endpoints
```

### Feature Modules (`src/dotmac_modules/`)
Licensed modules activated based on subscription:

```
dotmac_modules/
├── crm/
│   ├── __init__.py
│   ├── models.py               # CRM domain models
│   ├── services.py             # CRM business logic
│   ├── api.py                  # CRM endpoints
│   ├── schemas.py              # CRM schemas
│   └── events.py               # CRM event handlers
├── tickets/
│   ├── __init__.py
│   ├── models.py               # Ticket models
│   ├── services.py             # Ticket management
│   ├── api.py                  # Support endpoints
│   └── sla.py                  # SLA management
└── [other modules...]
```

### Shared Components (`src/dotmac_shared/`)
Common utilities used across all modules:

```
dotmac_shared/
├── api/
│   ├── dependencies.py         # Common dependencies
│   ├── exceptions.py           # Exception handlers
│   ├── middleware.py           # Common middleware
│   └── router_factory.py       # Router factories
├── database/
│   ├── base.py                 # Base models
│   ├── session.py              # Session management
│   └── utils.py                # Database utilities
└── events/
    ├── bus.py                  # Event bus implementation
    ├── handlers.py             # Event handlers
    └── schemas.py              # Event schemas
```

## Frontend Structure

### Portal Applications (`frontend/apps/`)
Each portal is a separate Next.js application:

```
frontend/apps/customer/
├── src/
│   ├── app/                    # Next.js app directory
│   ├── components/             # React components
│   │   ├── billing/           # Billing components
│   │   ├── services/          # Service management
│   │   └── support/           # Support components
│   ├── hooks/                 # Custom React hooks
│   │   ├── useLicense.ts      # License checking
│   │   └── useFeature.ts      # Feature gating
│   └── lib/                   # Utilities
└── package.json
```

### Shared Packages (`frontend/packages/`)
Reusable frontend libraries:

```
frontend/packages/
├── ui/                         # Component library
│   ├── components/
│   ├── styles/
│   └── index.ts
├── licensing/                  # License utilities
│   ├── FeatureGate.tsx
│   ├── LicenseProvider.tsx
│   └── hooks.ts
└── api-client/                # API client
    ├── client.ts
    ├── types.ts
    └── hooks.ts
```

## Configuration Files

### Root Configuration
```
dotmac_framework/
├── pyproject.toml             # Python project config
├── package.json               # Node.js workspace config
├── docker-compose.yml         # Local development
├── .env.example               # Environment variables
└── Makefile                   # Build automation
```

### Module Configuration
Each module can have its own configuration:
```
src/dotmac_modules/crm/
├── config.yaml                # Module configuration
├── requirements.txt           # Module dependencies
└── README.md                  # Module documentation
```

## Database Schema Organization

### Schema Separation
```sql
-- Core schemas (always present)
CREATE SCHEMA core;              -- Core platform data
CREATE SCHEMA billing;           -- Billing and subscriptions
CREATE SCHEMA auth;              -- Authentication

-- Module schemas (created on demand)
CREATE SCHEMA IF NOT EXISTS crm;      -- CRM data
CREATE SCHEMA IF NOT EXISTS tickets;  -- Support tickets
CREATE SCHEMA IF NOT EXISTS projects; -- Project management
CREATE SCHEMA IF NOT EXISTS fieldops; -- Field operations
CREATE SCHEMA IF NOT EXISTS analytics;-- Analytics data
```

## Build & Deployment

### Single Container Build
```dockerfile
# Build all modules into single image
FROM python:3.11 as backend
COPY src/ /app/src/
RUN pip install -r requirements.txt

FROM node:20 as frontend
COPY frontend/ /app/frontend/
RUN npm install && npm run build

FROM python:3.11-slim
COPY --from=backend /app /app
COPY --from=frontend /app/frontend/dist /app/static
CMD ["python", "-m", "dotmac_isp"]
```

### Feature Activation Flow
1. Container starts with all modules
2. License manager checks tenant license
3. Modules register if licensed
4. API routes activate based on features
5. Frontend receives feature flags
6. UI adapts to available features

## Development Workflow

### Adding a New Module
1. Create module directory in `src/dotmac_modules/`
2. Implement models, services, and API
3. Add feature flag in license system
4. Create frontend components
5. Add module tests
6. Update documentation

### Testing Feature Flags
```bash
# Enable feature for testing
export FEATURE_OVERRIDE=crm,tickets,projects

# Run with specific license tier
export LICENSE_TIER=professional

# Test feature activation
pytest tests/licensing/test_feature_activation.py
```

## Best Practices

### Module Independence
- Modules should not directly import from each other
- Use event bus for inter-module communication
- Share data through well-defined interfaces

### License Checking
- Always use decorators for API endpoints
- Check features in frontend before rendering
- Handle graceful degradation

### Resource Management
- Lazy load module resources
- Disable background tasks for unlicensed features
- Optimize cache allocation based on active features

## Migration Path

### From Microservices to Modular Monolith
1. Consolidate services into modules
2. Implement shared database with schemas
3. Add license management layer
4. Deploy as single container
5. Control features via licensing

### From Monolith to Licensed Modules
1. Identify feature boundaries
2. Refactor into modules
3. Add feature flags
4. Implement license checking
5. Update frontend for feature gating
