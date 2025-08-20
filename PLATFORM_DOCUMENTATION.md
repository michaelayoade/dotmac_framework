# DotMac Platform Documentation

## Overview

The DotMac Platform is a comprehensive ISP management framework built with zero-trust security principles, microservices architecture, and enterprise-grade observability. This documentation provides a complete guide to understanding, deploying, and maintaining the platform.

## Architecture

### Core Components

The platform consists of 10 microservices organized into logical domains:

#### Platform Core
- **dotmac_platform**: Core platform SDK and shared utilities
- **dotmac_api_gateway**: API gateway with authentication, rate limiting, and routing

#### Business Services  
- **dotmac_identity**: Customer identity and authentication management
- **dotmac_services**: Service catalog and provisioning management
- **dotmac_networking**: Network infrastructure and device management
- **dotmac_billing**: Billing, invoicing, and payment processing
- **dotmac_analytics**: Business intelligence and reporting

#### Operations
- **dotmac_core_events**: Event streaming and message processing
- **dotmac_core_ops**: Operations management and monitoring
- **dotmac_devtools**: Development and debugging utilities

### Security Architecture

#### Zero-Trust Implementation
- **Continuous Verification**: Every request authenticated and authorized
- **Least Privilege Access**: Role-based permissions with minimal scope
- **Encryption Everywhere**: Data encrypted at rest and in transit
- **Multi-Factor Authentication**: Required for all administrative access

#### Security Components
- **RBAC Engine**: Advanced role-based access control with policy evaluation
- **AST Security Evaluator**: Safe expression evaluation for security rules
- **Rate Limiting**: Redis-backed rate limiting with multiple strategies
- **Distributed Tracing**: OpenTelemetry-compatible request tracing

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Git

### Quick Start

1. **Clone Repository**
   ```bash
   git clone https://github.com/michaelayoade/dotmac-framework
   cd dotmac-framework
   ```

2. **Environment Setup**
   ```bash
   # Copy environment template
   cp .env.template .env
   
   # Edit configuration
   nano .env
   ```

3. **Build Services**
   ```bash
   # Generate Docker configurations
   python scripts/generate_docker_configs.py --all
   
   # Build all services
   ./scripts/docker/build-all.sh
   ```

4. **Start Platform**
   ```bash
   # Development environment
   docker-compose -f docker-compose.development.yml up -d
   
   # Production environment  
   docker-compose -f docker-compose.production.yml up -d
   ```

### Development Workflow

#### Code Quality Standards

The platform maintains strict code quality standards:

- **Type Safety**: Full type annotations with mypy validation
- **Code Formatting**: Black formatting with 88-character line length
- **Linting**: Ruff for fast Python linting
- **Security**: Bandit security scanning for all code
- **Testing**: Comprehensive test coverage (unit, integration, e2e)

#### Running Tests

```bash
# Run all tests
python scripts/run_tests.py

# Run specific service tests
python scripts/run_tests.py --service dotmac_platform

# Run with coverage
python scripts/run_tests.py --coverage

# Run performance tests
python scripts/run_tests.py --category performance
```

#### Code Quality Checks

```bash
# Run formatting
black . --line-length 88

# Run linting  
ruff check .

# Run type checking
mypy .

# Run security scan
bandit -r . -f json
```

## Service Documentation

### Platform Core (dotmac_platform)

**Purpose**: Provides core SDK functionality, security primitives, and shared utilities.

**Key Components**:
- Security framework (RBAC, encryption, audit)
- Repository patterns for data access
- Business intelligence analytics
- Distributed tracing and observability

**Configuration**:
```yaml
SECURITY_ENABLED: true
ENCRYPTION_KEY_PATH: /secrets/encryption.key
DATABASE_URL: postgresql://user:pass@localhost/dotmac
REDIS_URL: redis://localhost:6379/0
```

### API Gateway (dotmac_api_gateway)

**Purpose**: Central entry point for all API requests with authentication, rate limiting, and routing.

**Features**:
- JWT-based authentication
- Redis-backed rate limiting
- Request/response transformation
- API versioning support
- Health check aggregation

**Configuration**:
```yaml
GATEWAY_MODE: production
RATE_LIMIT_ENABLED: true
UPSTREAM_SERVICES:
  platform: http://dotmac-platform:8000
  identity: http://dotmac-identity:8001
  services: http://dotmac-services:8002
```

### Identity Management (dotmac_identity)

**Purpose**: Customer identity, authentication, and portal management.

**Features**:
- Customer lifecycle management
- Multi-factor authentication
- Session management
- Customer portal access
- Identity federation

### Service Management (dotmac_services)

**Purpose**: Service catalog, provisioning, and lifecycle management.

**Features**:
- Service catalog management
- Automated provisioning workflows
- Service lifecycle tracking
- Tariff and pricing management
- SLA monitoring

### Networking (dotmac_networking)

**Purpose**: Network infrastructure and device management.

**Features**:
- Device monitoring and management
- IP address management (IPAM)
- RADIUS authentication
- VLAN management
- Network topology mapping

### Billing (dotmac_billing)

**Purpose**: Billing, invoicing, and payment processing.

**Features**:
- Automated billing cycles
- Invoice generation
- Payment processing
- Tax calculation
- Billing analytics

### Analytics (dotmac_analytics)

**Purpose**: Business intelligence and reporting platform.

**Features**:
- Real-time metrics collection
- Custom dashboard creation
- Report generation
- Data visualization
- Performance analytics

## Deployment Guide

### Environment Configuration

#### Development Environment

```yaml
# docker-compose.development.yml
services:
  dotmac-platform:
    build:
      target: development
    environment:
      ENVIRONMENT: development
      DEBUG: true
      LOG_LEVEL: DEBUG
    volumes:
      - .:/app:ro
```

#### Staging Environment

```yaml
# docker-compose.staging.yml
services:
  dotmac-platform:
    build:
      target: production
    environment:
      ENVIRONMENT: staging
      LOG_LEVEL: INFO
    deploy:
      replicas: 2
```

#### Production Environment

```yaml
# docker-compose.production.yml
services:
  dotmac-platform:
    build:
      target: hardened
    environment:
      ENVIRONMENT: production
      LOG_LEVEL: WARNING
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 1G
```

### Security Configuration

#### Secrets Management

```bash
# Create secrets directory
mkdir -p secrets/

# Generate secrets
openssl rand -hex 32 > secrets/postgres_password.txt
openssl rand -hex 32 > secrets/redis_password.txt  
openssl rand -hex 64 > secrets/jwt_secret.txt

# Set permissions
chmod 600 secrets/*
```

#### SSL/TLS Configuration

```bash
# Generate certificates
openssl req -x509 -newkey rsa:4096 -keyout secrets/tls.key -out secrets/tls.crt -days 365 -nodes

# Configure nginx/traefik for SSL termination
```

### Monitoring and Observability

#### Metrics Collection

The platform includes comprehensive monitoring:

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards  
- **Distributed Tracing**: Request flow tracking
- **Log Aggregation**: Centralized logging with structured format

#### Health Checks

Each service implements comprehensive health checks:

```python
# Example health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "version": "1.0.0",
        "dependencies": {
            "database": await check_database(),
            "redis": await check_redis(),
            "external_apis": await check_external_apis()
        }
    }
```

### Performance Optimization

#### Caching Strategy

- **Redis Caching**: Application-level caching for frequently accessed data
- **CDN Integration**: Static asset delivery optimization
- **Database Optimization**: Query optimization and connection pooling

#### Scaling Guidelines

- **Horizontal Scaling**: Use Docker Swarm or Kubernetes for service scaling
- **Database Scaling**: Implement read replicas for heavy read workloads
- **Load Balancing**: Use nginx or Traefik for load distribution

## API Documentation

### Authentication

All API endpoints require authentication via JWT tokens:

```bash
# Login to get token
curl -X POST /api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Use token in requests
curl -H "Authorization: Bearer <token>" /api/v1/customers
```

### Core Endpoints

#### Customer Management
- `GET /api/v1/customers` - List customers
- `POST /api/v1/customers` - Create customer
- `GET /api/v1/customers/{id}` - Get customer details
- `PUT /api/v1/customers/{id}` - Update customer
- `DELETE /api/v1/customers/{id}` - Delete customer

#### Service Management
- `GET /api/v1/services` - List services
- `POST /api/v1/services` - Create service
- `GET /api/v1/services/{id}` - Get service details
- `POST /api/v1/services/{id}/provision` - Provision service

#### Billing
- `GET /api/v1/billing/invoices` - List invoices
- `GET /api/v1/billing/invoices/{id}` - Get invoice
- `POST /api/v1/billing/payments` - Process payment

## Troubleshooting

### Common Issues

#### Database Connection Issues

```bash
# Check database connectivity
docker exec -it postgres psql -U dotmac -d dotmac_platform -c "\dt"

# Check logs
docker logs dotmac-platform
```

#### Redis Connection Issues

```bash
# Test Redis connectivity
docker exec -it redis redis-cli ping

# Check Redis memory usage
docker exec -it redis redis-cli info memory
```

#### Service Discovery Issues

```bash
# Check service health
docker exec -it dotmac-platform curl http://localhost:8000/health

# Check network connectivity
docker network ls
docker network inspect dotmac_dotmac-backend
```

### Performance Issues

#### High Memory Usage

```bash
# Check container memory usage
docker stats

# Analyze memory leaks
docker exec -it dotmac-platform python -m memory_profiler app.py
```

#### Slow Database Queries

```bash
# Enable query logging
echo "log_statement = 'all'" >> postgresql.conf

# Analyze slow queries
docker exec -it postgres psql -U dotmac -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC;"
```

### Log Analysis

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f dotmac-platform

# Search logs for errors
docker-compose logs | grep ERROR
```

## Contributing

### Development Setup

1. **Fork Repository**
2. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-feature
   ```

3. **Make Changes**
4. **Run Tests**
   ```bash
   python scripts/run_tests.py
   ```

5. **Submit Pull Request**

### Code Standards

- Follow PEP 8 style guidelines
- Include comprehensive type annotations
- Write thorough documentation
- Maintain test coverage above 90%
- Include security considerations

### Security Guidelines

- Never commit secrets or credentials
- Use environment variables for configuration
- Implement proper input validation
- Follow least privilege principles
- Regular security audits

## License

MIT License - see LICENSE file for details.

## Support

For support and questions:
- GitHub Issues: https://github.com/michaelayoade/dotmac-framework/issues
- Documentation: https://docs.dotmac.com
- Community: https://community.dotmac.com