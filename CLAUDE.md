# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **DotMac ISP Framework** - a comprehensive telecommunications management platform for Internet Service Providers. The repository is a monorepo containing the ISP Framework and the Management Platform that orchestrates it, with a unified configuration management system ensuring security parity across both platforms.

## Architecture

**Microservices Architecture**: Event-driven design with 10 core Python services:
- `dotmac_core_events` - Event bus and messaging system (Redis/Kafka)
- `dotmac_core_ops` - Operational utilities (workflows, sagas, job queues)
- `dotmac_identity` - Authentication and authorization service
- `dotmac_billing` - Billing, invoicing, and payment processing
- `dotmac_services` - Service provisioning and lifecycle management  
- `dotmac_networking` - Network infrastructure management (SNMP, device monitoring)
- `dotmac_analytics` - Business intelligence and reporting
- `dotmac_api_gateway` - API routing, rate limiting, load balancing
- `dotmac_platform` - Platform coordination and shared services
- `dotmac_devtools` - Development tools and service generators

**Frontend**: React/Next.js applications in `frontend/` using pnpm workspaces and Turbo for monorepo management.

## Essential Commands

### Quick Start
```bash
# Show all available commands
make help

# Check version and environment
make version && make env-check
```

### Development Setup
```bash
# Set up development environment
make install-dev

# Clean and reset environment
make clean && make install-dev
```

### Docker Development Environment (✅ WORKING)
```bash
# Build Docker image (all dependencies resolved)
make docker-build

# Start complete containerized environment
make docker-run

# Alternative: Start individual services
docker-compose up -d postgres redis  # Infrastructure only
docker-compose up -d app             # Add main application

# Health check
curl http://localhost:8001/health
```
**Status**: Docker environment fully configured with OpenTelemetry stack working.
**See**: `DOCKER_DEPLOYMENT_STATUS.md` for complete setup details.

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
# Start development server with auto-reload
make run-dev

# Start production server
make run

# Start API Gateway for development
make run-api-gateway

# Serve using main entry point
make serve
```

### Database Management
```bash
# Set up database and run migrations
make setup-db

# Run Alembic migrations
make alembic-upgrade

# Reset database (WARNING: destroys data)
make reset-db
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

## Service Dependencies

**Database**: PostgreSQL primary, Redis cache, TimescaleDB for metrics
**Message Bus**: Redis Pub/Sub + message queues
**Auth**: JWT-based authentication with RBAC
**Multi-tenant**: All services support tenant isolation via tenant_id

## Key Patterns

**Repository Pattern**: Each service uses repository pattern for data access
**Dependency Injection**: FastAPI Depends() for dependency management
**Event Sourcing**: Critical business entities use event sourcing
**CQRS**: Command Query Responsibility Separation for complex operations

## Development Workflow

1. Always run `make install-dev` for initial setup
2. Run `make check` before committing (includes lint, type-check, test, security)
3. Use `make test-package PACKAGE=service_name` for focused testing
4. Each service has its own `pyproject.toml` with service-specific dependencies
5. Root `pyproject.toml` contains unified tooling configuration

## Deployment

**Docker**: Each service has a Dockerfile
**Kubernetes**: Deployment manifests in `deployments/kubernetes/`
**Environments**: development, staging, production docker-compose files available

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

- **Import errors**: Ensure you're in the correct service directory when running tests
- **Complexity violations**: Refactor functions instead of ignoring rules
- **Test failures**: Check that services are using proper test markers
- **Docker builds**: Use `make docker-config` to generate configurations

## Service Interaction

Services communicate via:
1. **HTTP APIs** for synchronous operations
2. **Events** via Redis Pub/Sub for asynchronous operations
3. **Shared database** for some cross-cutting concerns (carefully managed)

All services follow the same patterns for consistency across the platform.