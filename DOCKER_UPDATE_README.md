# README Update - Docker Section

This is the updated Docker section that should replace the old Docker instructions in the main README.

---

## 🐳 Docker Setup

The DotMac platform uses a consolidated Docker Compose configuration with profiles for different environments and service groups.

### Quick Start

#### Development
```bash
# Start core services
docker compose up

# Start with monitoring (SignOz)
docker compose --profile monitoring up

# Start with development tools
docker compose --profile dev-tools up
```

#### Production
```bash
# Simple production deployment
docker compose -f docker-compose.yml -f docker-compose.prod.simple.yml up -d

# Production with monitoring
docker compose -f docker-compose.yml -f docker-compose.prod.simple.yml --profile monitoring up -d
```

### Available Profiles

| Profile | Description | Use Case |
|---------|-------------|----------|
| *(default)* | Core services (APIs, databases, frontends) | Development |
| `monitoring` | SignOz observability stack | Performance monitoring |
| `security` | OpenBao secrets management | Production security |
| `test` | Test runners and CI utilities | Testing and CI/CD |
| `dev-tools` | pgAdmin, Redis Commander, MailHog | Development utilities |
| `legacy-monitoring` | Prometheus/Grafana (deprecated) | Legacy monitoring |
| `isp` | FreeRADIUS and ISP-specific services | ISP operations |
| `all` | All services from all profiles | Full platform |

### Service Access

| Service | URL | Profile |
|---------|-----|---------|
| **API Gateway** | http://localhost:8000 | core |
| **Admin Portal** | http://localhost:3000 | core |
| **Customer Portal** | http://localhost:3001 | core |
| **Reseller Portal** | http://localhost:3002 | core |
| **SignOz UI** | http://localhost:3301 | monitoring |
| **pgAdmin** | http://localhost:5050 | dev-tools |
| **RabbitMQ UI** | http://localhost:15672 | core |
| **MailHog** | http://localhost:8025 | dev-tools |

### Environment Configuration

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit key variables for production:**
   ```bash
   ENVIRONMENT=production
   POSTGRES_PASSWORD=secure-password
   REDIS_PASSWORD=secure-password
   SECRET_KEY=your-secret-key-here
   JWT_SECRET_KEY=your-jwt-secret-here
   ```

### Common Commands

| Purpose | Command |
|---------|---------|
| **Start development** | `docker compose up` |
| **Start with monitoring** | `docker compose --profile monitoring up` |
| **Run tests** | `docker compose --profile test run test-runner` |
| **View logs** | `docker compose logs -f api-gateway` |
| **Scale service** | `docker compose up -d --scale api-gateway=3` |
| **Stop all** | `docker compose down` |
| **Clean volumes** | `docker compose down -v` |

### Health Checks

```bash
# Check all services
docker compose ps

# Test API Gateway
curl http://localhost:8000/health

# Check specific service logs
docker compose logs -f identity
```

### Migration from Old Setup

If you have existing Docker configurations:

```bash
# Run automated migration
./scripts/migrate-docker-compose.sh

# Or start fresh
docker compose down -v
docker compose up
```

For detailed information, see:
- [Docker Compose Consolidation Guide](./DOCKER_COMPOSE_CONSOLIDATION.md)
- [Quick Start Guide](./DOCKER_COMPOSE_QUICK_START.md)
- [Cleanup Summary](./DOCKER_CLEANUP_SUMMARY.md)

---

This section should replace any existing Docker documentation in the main README.md file.