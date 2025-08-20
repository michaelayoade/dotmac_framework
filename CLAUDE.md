# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **DotMac ISP Framework** - a comprehensive microservices-based telecommunications management platform for Internet Service Providers. The repository is a monorepo containing 10 interconnected Python services plus frontend applications.

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

### Development Setup
```bash
# Set up development environment
make install-dev

# Clean and reset environment
make clean && make install-dev
```

### Code Quality (CRITICAL - Always run before commits)
```bash
# Run linting with complexity enforcement (FAILS on violations)
make lint

# Auto-fix code issues
make format && make lint-fix

# Run type checking
make type-check

# Run all quality checks
make check
```

### Testing (Docker-Standardized - RECOMMENDED)
```bash
# Run all tests in Docker (standardized environment)
make test-docker

# Run unit tests in Docker (fast)
make test-docker-unit

# Run integration tests in Docker
make test-docker-integration

# Run smoke tests in Docker
make test-docker-smoke

# Clean Docker test environment
make test-docker-clean
```

### Legacy Testing (Local Environment)
```bash
# Run all tests with coverage (80% minimum required)
make test

# Run tests for specific package
make test-package PACKAGE=dotmac_identity

# Run only unit tests (fast)
make test-unit

# Run integration tests  
make test-integration
```

### Security
```bash
# Run security scans (always check before production)
make security

# Run strict security scans (fails on issues)
make security-strict
```

### Package-Specific Development
```bash
# Start API Gateway for development
make run-api-gateway

# Build specific package
make build-package PACKAGE=dotmac_identity
```

### Frontend (in frontend/ directory)
```bash
# Start all frontend apps
pnpm dev

# Build all frontend apps
pnpm build

# Run frontend tests
pnpm test
```

## Code Quality Standards

**CRITICAL**: This project enforces strict complexity limits:
- **Max function complexity**: 10 (McCabe)
- **Max arguments**: 8 per function
- **Max statements**: 50 per function
- **Coverage requirement**: 80% minimum

**Do NOT ignore complexity violations** - refactor code instead. The `make lint` command will fail if complexity rules are violated.

## Testing Strategy

**Testing Pyramid**: 70% unit tests, 20% integration tests, 10% e2e tests.

Test markers:
- `@pytest.mark.unit` - Fast isolated tests
- `@pytest.mark.integration` - Cross-service tests  
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

- All services implement multi-tenant isolation
- JWT authentication required for all APIs
- Security scanning is mandatory (`make security`)
- No secrets in code - use environment variables
- This is a defensive security framework only

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