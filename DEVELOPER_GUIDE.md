# Developer Guide

This file provides guidance for developers working with this repository.

## Repository Overview

This is the **DotMac Unified Platform** - a comprehensive telecommunications management ecosystem. The repository contains two distinct but coordinated platforms:

1. **ISP Framework** (`isp-framework/`) - Monolithic ISP management application
2. **Management Platform** (`management-platform/`) - SaaS orchestration platform for multi-tenant deployments

Both platforms share unified configuration management, security policies, and deployment infrastructure.

## Architecture

### **Two-Platform Structure**

#### **ISP Framework** (`isp-framework/`)
**Monolithic FastAPI Application**: Single integrated application with modular architecture:

**Core Modules:**
- `modules/identity/` - Customer and user management
- `modules/billing/` - Billing, invoicing, and payment processing
- `modules/services/` - Service provisioning and lifecycle management
- `modules/networking/` - Network infrastructure management (SNMP, device monitoring)
- `modules/analytics/` - Business intelligence and reporting
- `modules/support/` - Ticketing and customer support
- `modules/inventory/` - Equipment and asset management
- `modules/field_ops/` - Field operations and work orders
- `modules/compliance/` - Regulatory compliance and reporting
- `modules/omnichannel/` - Multi-channel customer communication

**Platform Infrastructure:**
- `core/` - Shared utilities, database, security, configuration
- `integrations/` - External system integrations (FreeRADIUS, Ansible, VOLTHA)
- `plugins/` - Vendor plugin system for extensibility
- `portals/` - Portal-specific APIs (admin, customer, reseller, technician)
- `sdks/` - Internal SDK library for cross-module communication

#### **Management Platform** (`management-platform/`)
**SaaS Orchestration Platform**: Multi-tenant platform for managing ISP Framework deployments:

**Core Services:**
- `app/services/tenant_service.py` - Tenant lifecycle management
- `app/services/billing_service.py` - SaaS subscription billing
- `app/services/deployment_service.py` - Kubernetes orchestration
- `app/services/plugin_service.py` - Plugin marketplace and licensing
- `app/services/monitoring_service.py` - Platform health monitoring

**Multi-Tenant Portals:**
- `portals/master_admin/` - Platform operator interface
- `portals/tenant_admin/` - ISP customer management
- `portals/reseller/` - Partner and reseller portal

**Frontend**: React/Next.js applications in `frontend/` using pnpm workspaces and Turbo for monorepo management.

## Essential Commands

### Quick Start
```bash
# Root level - manages both platforms
make help

# Platform-specific commands
cd isp-framework && make help           # ISP Framework commands
cd management-platform && make help    # Management Platform commands
```

### Development Setup
```bash
# Set up both platforms
make install-dev

# Platform-specific setup
cd isp-framework && make install-dev
cd management-platform && make install-dev
```

### Docker Development Environment
```bash
# Start unified development environment (both platforms)
docker-compose -f docker-compose.unified.yml up -d

# Start ISP Framework only
cd isp-framework && make docker-run

# Start Management Platform only  
cd management-platform && make up

# Health checks
curl http://localhost:8001/health      # ISP Framework
curl http://localhost:8000/health      # Management Platform
```

### Platform Access Points
- **ISP Framework API**: http://localhost:8001
- **Management Platform API**: http://localhost:8000
- **Admin Portal**: http://localhost:3000
- **Customer Portal**: http://localhost:3001  
- **Reseller Portal**: http://localhost:3002
- **Technician Portal**: http://localhost:3003
- **Management Admin**: http://localhost:3004
- **Tenant Portal**: http://localhost:3005

### AI-First Development Workflow
```bash
# AI Safety Checks (Fast - Primary gate)
make ai-safety-check

# Generate property-based tests with AI
make ai-generate-tests

# Run AI-optimized test suite (Fast feedback)
make test-ai-first

# Optional: Traditional quality checks (AI can skip these)
make lint-optional && make type-check-optional
```

### AI-First Testing Strategy (NEW PARADIGM)
```bash
# Property-based testing (AI generates thousands of test cases)
make test-property-based

# Contract testing (AI validates API schemas)
make test-contracts

# Behavior testing (AI tests business outcomes)
make test-behaviors

# Revenue-critical smoke tests only
make test-smoke-critical

# AI test generation and execution
make test-ai-suite
```

### Traditional Testing (Legacy - Optional)
```bash
# Legacy unit tests (use only for critical business logic)
make test-unit-legacy

# Integration tests (AI can generate better versions)
make test-integration-legacy

# Full coverage report (AI focuses on smart coverage)
make coverage-traditional
```

### Security
```bash
# Run security scans (always check before production)
make security

# Run strict security scans (fails on issues)
make security-strict
```

### Development Servers
```bash
# ISP Framework
cd isp-framework && make run-dev       # Development server
cd isp-framework && make run           # Production server

# Management Platform  
cd management-platform && make run-api # API server
cd management-platform && make run-worker # Background workers
```

### Database Management
```bash
# ISP Framework
cd isp-framework && make setup-db      # Setup and migrate
cd isp-framework && make alembic-upgrade

# Management Platform
cd management-platform && make db-migrate
cd management-platform && make db-reset
```

### Docker Operations
```bash
# Build and run Docker containers
make docker-build && make docker-run

# Stop Docker containers
make docker-stop

# Clean Docker environment
make docker-clean

# Production Docker build
make docker-prod-build && make docker-prod-run
```

### Utilities
```bash
# Generate API documentation (starts server)
make docs

# Check environment configuration
make env-check

# Update requirements files (use with caution)
make requirements-update
```

## AI-First Code Standards

**NEW PARADIGM**: This project is optimized for AI development:

### Critical Gates (Always Enforced)
- **Business logic correctness** - AI must not change revenue/billing logic
- **Security patterns** - AI-generated code security scanned
- **Performance baseline** - AI changes monitored for regressions
- **API contracts** - Service interfaces remain stable

### Optional Gates (Human Convenience Only)
- Code formatting - AI reads messy code fine
- Complexity limits - AI handles complex functions better than humans
- Traditional coverage - AI uses property-based testing instead

**Philosophy**: Focus on business outcomes, not code aesthetics.

## AI-First Testing Strategy

**NEW Testing Pyramid**: AI-generated and business-focused testing.

### Primary Test Types:
- `@pytest.mark.property_based` - AI-generated test cases (40%)
- `@pytest.mark.behavior` - Business outcome testing (30%)
- `@pytest.mark.contract` - API/Service contract validation (20%)
- `@pytest.mark.smoke_critical` - Revenue-critical paths only (10%)  
- `@pytest.mark.e2e` - Full workflow tests

## Platform Dependencies

### **ISP Framework**
- **Database**: PostgreSQL primary, Redis cache
- **Auth**: Portal-based authentication (Portal ID system)  
- **Architecture**: Modular monolith with plugin system
- **Communication**: Internal module communication via SDKs

### **Management Platform**  
- **Database**: PostgreSQL with multi-tenant isolation
- **Auth**: JWT-based authentication with RBAC
- **Architecture**: Multi-tenant SaaS application
- **Message Queue**: Celery with Redis for background tasks

### **Shared Infrastructure**
- **Configuration**: Unified OpenBao-based secrets management
- **Monitoring**: SignOz observability stack
- **Networking**: Nginx reverse proxy with SSL termination

## Key Patterns

### **ISP Framework Patterns**
- **Modular Architecture**: Domain-driven modules with clear boundaries
- **Repository Pattern**: Data access abstraction layer
- **Plugin System**: Extensible vendor integration architecture  
- **Portal Authentication**: Multi-portal access with Portal ID system

### **Management Platform Patterns**
- **Multi-Tenant**: Complete tenant isolation at database and application level
- **SaaS Orchestration**: Kubernetes-based tenant deployment automation
- **Event-Driven**: Async processing for tenant provisioning and billing
- **API-First**: RESTful APIs with OpenAPI documentation

## Development Workflow

1. **Platform Selection**: Choose ISP Framework or Management Platform for your work
2. **Environment Setup**: Run platform-specific `make install-dev` 
3. **Development**: Use platform-specific commands and testing approaches
4. **Cross-Platform**: Use unified config system for shared resources
5. **Testing**: Each platform has its own test suite and CI/CD pipeline

## Deployment

### **ISP Framework**
- **Single Application**: Deployed as unified FastAPI application
- **Database**: Single PostgreSQL instance per deployment
- **Scaling**: Vertical scaling with horizontal read replicas

### **Management Platform**
- **Multi-Tenant SaaS**: Kubernetes-orchestrated deployments
- **Database**: Shared PostgreSQL with tenant isolation
- **Scaling**: Horizontal auto-scaling based on tenant load

## Security Notes

- **Unified Configuration Management**: Cross-platform encrypted configuration with centralized secrets management
- **OpenBao/Vault Integration**: Automatic secret rotation and secure credential management
- **Multi-tenant Isolation**: Complete data isolation with encrypted configuration per tenant
- **Cross-Platform Audit Orchestration**: Unified audit trails between Management Platform and ISP Framework instances
- **Configuration Hot-Reloading**: Zero-downtime configuration updates with disaster recovery automation
- **Compliance Validation**: SOC2, GDPR, PCI DSS, ISO27001 configuration compliance
- **JWT authentication**: Required for all APIs with RBAC
- **Security scanning**: Mandatory (`make security`)
- **No secrets in code**: Use environment variables and OpenBao vault
- **Defensive security framework only**: All security features are for protection, not exploitation

## Common Issues

### **ISP Framework Issues**
- **Module imports**: Ensure you're in `isp-framework/` directory when running commands
- **Portal routing**: Check portal detection logic for authentication issues
- **Plugin loading**: Verify plugin registration and dependency resolution
- **Database migrations**: Run `make alembic-upgrade` after model changes

### **Management Platform Issues**
- **Tenant isolation**: Verify all queries include tenant context
- **Multi-tenancy**: Check tenant detection in middleware
- **Background tasks**: Ensure Celery workers are running for async operations
- **Kubernetes integration**: Verify kubectl access and cluster connectivity

### **Cross-Platform Issues**
- **Configuration sync**: Check OpenBao connectivity for shared secrets
- **Database connections**: Verify platform-specific database credentials
- **Port conflicts**: Ensure different ports for each platform service

## Platform Communication

### **ISP Framework Internal**
- **Module-to-Module**: SDK-based internal APIs
- **Database**: Shared PostgreSQL with cross-module relationships
- **Caching**: Redis for session and application cache
- **Events**: Internal event system for workflow orchestration

### **Management Platform Internal**
- **Multi-Tenant**: Row-level security and tenant-aware queries
- **Background Processing**: Celery for tenant provisioning and billing
- **External APIs**: REST APIs for tenant and resource management
- **Kubernetes**: Direct cluster interaction for tenant deployments

### **Cross-Platform Integration**
- **Configuration**: Shared OpenBao secrets management
- **Monitoring**: Unified SignOz observability
- **Deployment**: Coordinated Docker Compose for development
- **Authentication**: Cross-platform session sharing (where applicable)