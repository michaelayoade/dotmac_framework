# Docker Compose Quick Start Guide

## TL;DR - Get Started Fast

### Development
```bash
# Start core services
docker compose up

# Start with monitoring
docker compose --profile monitoring up

# Start with all dev tools
docker compose --profile dev-tools --profile monitoring up
```

### Production
```bash
# Simple production setup
docker compose -f docker-compose.yml -f docker-compose.prod.simple.yml up -d

# With monitoring
docker compose -f docker-compose.yml -f docker-compose.prod.simple.yml --profile monitoring up -d
```

### Testing
```bash
# Run all tests
docker compose --profile test run test-runner

# Run integration tests
docker compose --profile test run integration-test-runner
```

## Key Commands

| Purpose | Command |
|---------|---------|
| **Development** | `docker compose up` |
| **Development + Monitoring** | `docker compose --profile monitoring up` |
| **Production** | `docker compose -f docker-compose.yml -f docker-compose.prod.simple.yml up -d` |
| **Run Tests** | `docker compose --profile test run test-runner` |
| **View Logs** | `docker compose logs -f api-gateway` |
| **Scale Service** | `docker compose up -d --scale api-gateway=3` |
| **Stop All** | `docker compose down` |

## Available Services

### Core Services (Always Running)
- **postgres** - PostgreSQL database
- **redis** - Redis cache/message broker  
- **rabbitmq** - Message queue with management UI
- **api-gateway** - Main API gateway (port 8000)
- **identity** - User authentication (port 8001)
- **billing** - Billing and payments (port 8002)
- **services** - Service provisioning (port 8003)
- **networking** - Network management (port 8004)
- **analytics** - Business intelligence (port 8005)
- **core-ops** - Operations workflows (port 8006)
- **core-events** - Event processing (port 8007)
- **admin-portal** - Admin interface (port 3000)
- **customer-portal** - Customer interface (port 3001)
- **reseller-portal** - Reseller interface (port 3002)

### Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| *(default)* | Core services | Development |
| `monitoring` | SignOz stack | Observability |
| `security` | OpenBao | Secrets management |
| `test` | Test runners | CI/CD |
| `dev-tools` | pgAdmin, Redis Commander, MailHog | Development utilities |
| `legacy-monitoring` | Prometheus, Grafana | Legacy monitoring |
| `isp` | FreeRADIUS | ISP-specific services |
| `all` | Everything | Full stack |

## Environment Setup

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit key variables:**
   ```bash
   # Required for production
   POSTGRES_PASSWORD=secure-password
   REDIS_PASSWORD=secure-password
   SECRET_KEY=your-secret-key
   JWT_SECRET_KEY=your-jwt-key
   
   # External services
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

## Health Checks

```bash
# Check all services
docker compose ps

# Check specific service health
curl http://localhost:8000/health

# View service logs
docker compose logs -f api-gateway
```

## Common Issues

### Port Conflicts
If you get port binding errors:
```bash
# Check what's using the port
sudo lsof -i :8000

# Change port in .env
echo "API_GATEWAY_PORT=8080" >> .env
```

### Memory Issues
For development on low-memory systems:
```bash
# Start only essential services
docker compose up postgres redis api-gateway admin-portal
```

### Database Issues
```bash
# Reset database
docker compose down -v
docker compose up -d postgres
# Wait for it to be ready, then start other services
```

## Migration from Old Setup

If you have existing Docker Compose files:

```bash
# Run migration script
./scripts/migrate-docker-compose.sh

# Or manually backup and use new setup
mkdir backup
mv docker-compose.*.yml backup/
# Use new consolidated setup
```

## Quick Reference

### Service URLs
- **API Gateway:** http://localhost:8000
- **Admin Portal:** http://localhost:3000  
- **Customer Portal:** http://localhost:3001
- **Reseller Portal:** http://localhost:3002
- **SignOz UI:** http://localhost:3301 (with `--profile monitoring`)
- **RabbitMQ UI:** http://localhost:15672 (guest/guest)
- **pgAdmin:** http://localhost:5050 (with `--profile dev-tools`)

### Useful Profiles Combinations
```bash
# Full development stack
docker compose --profile monitoring --profile dev-tools up

# Production with monitoring and security  
docker compose -f docker-compose.yml -f docker-compose.prod.simple.yml --profile monitoring --profile security up -d

# Testing with monitoring
docker compose --profile test --profile monitoring up
```

Need more details? See [DOCKER_COMPOSE_CONSOLIDATION.md](./DOCKER_COMPOSE_CONSOLIDATION.md) for comprehensive documentation.