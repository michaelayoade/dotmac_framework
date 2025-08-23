# Docker Compose Consolidation Guide

## Overview

The DotMac platform Docker Compose configuration has been consolidated from multiple files into a profile-based system for better maintainability and clarity.

## File Structure

### Core Files
- **`docker-compose.yml`** - Base configuration with all service definitions
- **`docker-compose.override.yml`** - Development overrides (auto-loaded)
- **`docker-compose.prod.yml`** - Production overrides

### Legacy Files (Deprecated)
The following files have been consolidated and should be removed:
- `docker-compose.development.yml` → Use default setup
- `docker-compose.monitoring.yml` → Use `--profile monitoring`
- `docker-compose.signoz.yml` → Use `--profile monitoring`
- `docker-compose.secure.yml` → Use `--profile security`
- `docker-compose.test.yml` → Use `--profile test`
- `docker-compose.staging.yml` → Use prod override with staging env
- `docker-compose.production.yml` → Use `docker-compose.prod.yml`

## Profiles

The consolidated configuration uses Docker Compose profiles to organize services:

| Profile | Description | Services Included |
|---------|-------------|-------------------|
| *(default)* | Core services | postgres, redis, rabbitmq, all backend services, frontends |
| `monitoring` | SignOz observability stack | clickhouse, signoz-collector, signoz-query, signoz-frontend, alertmanager |
| `legacy-monitoring` | Prometheus/Grafana (deprecated) | prometheus, grafana |
| `security` | Security services | openbao |
| `test` | Test runners | test-runner, integration-test-runner |
| `dev-tools` | Development utilities | pgadmin, redis-commander, mailhog |
| `isp` | ISP-specific services | freeradius |
| `all` | Everything | All services from all profiles |

## Usage Examples

### Development (Default)
```bash
# Start core services with development settings
docker compose up

# Start with monitoring
docker compose --profile monitoring up

# Start with all development tools
docker compose --profile dev-tools --profile monitoring up
```

### Production
```bash
# Use production overrides
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Production with monitoring
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile monitoring up -d

# Production with security (OpenBao)
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile security up -d
```

### Testing
```bash
# Run unit tests
docker compose --profile test run test-runner

# Run integration tests
docker compose --profile test run integration-test-runner

# Run tests with custom arguments
docker compose --profile test run -e PYTEST_ARGS="-v -k test_billing" test-runner
```

### Specific Service Groups
```bash
# Only infrastructure
docker compose up postgres redis rabbitmq

# Only backend services
docker compose up api-gateway identity billing services networking analytics core-ops core-events

# Only frontend
docker compose up admin-portal customer-portal reseller-portal

# SignOz monitoring stack
docker compose --profile monitoring up clickhouse signoz-collector signoz-query signoz-frontend
```

## Environment Variables

Key environment variables (set in `.env` file):

```bash
# Environment
ENVIRONMENT=development  # or production, staging

# Database
POSTGRES_USER=dotmac
POSTGRES_PASSWORD=secure-password
POSTGRES_DB=dotmac

# Redis
REDIS_PASSWORD=secure-password  # Optional in dev

# RabbitMQ
RABBITMQ_USER=dotmac
RABBITMQ_PASSWORD=secure-password

# OpenBao
OPENBAO_ENABLED=true
OPENBAO_ROOT_TOKEN=root-token

# SignOz/OTEL
OTEL_EXPORTER_OTLP_ENDPOINT=http://signoz-collector:4317

# API Gateway
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Ports (customize if needed)
API_GATEWAY_PORT=8000
IDENTITY_PORT=8001
BILLING_PORT=8002
SERVICES_PORT=8003
NETWORKING_PORT=8004
ANALYTICS_PORT=8005
CORE_OPS_PORT=8006
CORE_EVENTS_PORT=8007
```

## Migration from Old Setup

### Step 1: Stop existing services
```bash
docker compose -f docker-compose.old.yml down
```

### Step 2: Copy environment variables
```bash
# Ensure your .env file has all required variables
cp .env.example .env
# Edit .env with your values
```

### Step 3: Start with new configuration
```bash
# Development
docker compose up

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Step 4: Verify services
```bash
# Check all services are running
docker compose ps

# Check health
docker compose ps --format json | jq '.[].Health'

# View logs
docker compose logs -f api-gateway
```

## Benefits of Consolidation

1. **Single Source of Truth**: All service definitions in one file
2. **Profile-based Organization**: Easy to enable/disable service groups
3. **Environment Flexibility**: Simple override system for dev/prod
4. **Reduced Duplication**: Shared configurations using extension fields
5. **Better Maintainability**: Fewer files to manage
6. **Clear Separation**: Development vs Production settings clearly separated

## Common Tasks

### View running services
```bash
docker compose ps
```

### Scale a service
```bash
docker compose up -d --scale api-gateway=3
```

### Update a single service
```bash
docker compose up -d --no-deps api-gateway
```

### View logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api-gateway

# Last 100 lines
docker compose logs --tail=100 api-gateway
```

### Clean up
```bash
# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v

# Remove only test containers
docker compose --profile test down
```

## Troubleshooting

### Port conflicts
If you get port binding errors, check the ports section in `.env` and adjust as needed.

### Memory issues
In production, ensure Docker has enough memory allocated. The production override includes resource limits.

### Service dependencies
Services will wait for their dependencies. If a service fails to start, check its dependencies first.

### Profile not working
Ensure you're using Docker Compose v2.x or later:
```bash
docker compose version
```

## Next Steps

1. **Remove old files**: Delete deprecated docker-compose files
2. **Update CI/CD**: Update pipelines to use new commands
3. **Update documentation**: Replace references to old files
4. **Test thoroughly**: Verify all environments work correctly
5. **Monitor resources**: Check resource usage with new limits