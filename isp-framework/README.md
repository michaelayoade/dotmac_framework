# DotMac ISP Framework

A comprehensive modular monolith for Internet Service Provider management built with FastAPI, SQLAlchemy 2.0, and Pydantic v2.

## Overview

The DotMac ISP Framework is a complete ISP management platform designed as a modular monolith that provides all the essential functionality needed to run an Internet Service Provider business. This framework is deployed TO CUSTOMERS as their ISP management solution.

## Architecture

### Modular Monolith Design

Unlike microservices, this framework is built as a modular monolith, providing:
- **Single Deployment Unit**: Easier deployment and operations
- **Shared Database**: Consistent data integrity with ACID transactions
- **Module Boundaries**: Clear separation of concerns with defined interfaces
- **Simplified Development**: No distributed system complexity
- **Performance**: No network latency between modules

### Technology Stack

- **Framework**: FastAPI with async/await support
- **Database**: PostgreSQL with SQLAlchemy 2.0 ORM
- **Validation**: Pydantic v2 for data validation and serialization
- **Caching**: Redis for sessions and caching
- **Task Queue**: Celery with Redis broker
- **Authentication**: JWT tokens with bcrypt password hashing
- **API Documentation**: Automatic OpenAPI/Swagger generation

## Core Modules

### 1. Identity Module (`dotmac_isp.modules.identity`)
- **Users**: System user management with role-based access control
- **Customers**: Customer account management (residential, business, enterprise)
- **Authentication**: JWT-based authentication with refresh tokens
- **Roles & Permissions**: Flexible role-based authorization system

### 2. Billing Module (`dotmac_isp.modules.billing`)
- **Invoices**: Automated invoice generation and management
- **Payments**: Payment processing with multiple gateway support
- **Subscriptions**: Recurring billing for ongoing services
- **Credit Notes**: Refunds and billing adjustments

### 3. Services Module (`dotmac_isp.modules.services`)
- **Service Catalog**: Internet, phone, TV, and bundle offerings
- **Service Instances**: Active customer service management
- **Provisioning**: Automated service activation and configuration
- **Usage Tracking**: Bandwidth and data usage monitoring

### 4. Networking Module (`dotmac_isp.modules.networking`)
- **Device Management**: Router, switch, and infrastructure monitoring
- **IPAM**: IP address management and allocation
- **RADIUS**: Authentication for network access
- **Network Topology**: Infrastructure mapping and monitoring

### 5. Sales Module (`dotmac_isp.modules.sales`)
- **Lead Management**: Sales pipeline and opportunity tracking
- **CRM**: Customer relationship management
- **Campaigns**: Marketing campaign management
- **Sales Analytics**: Performance metrics and reporting

### 6. Support Module (`dotmac_isp.modules.support`)
- **Ticketing System**: Customer support ticket management
- **Knowledge Base**: Self-service documentation and FAQs
- **SLA Management**: Service level agreement tracking
- **Escalation Rules**: Automated ticket escalation

### 7. Resellers Module (`dotmac_isp.modules.resellers`)
- **Partner Management**: Reseller partner onboarding and management
- **Commission Tracking**: Automated commission calculations
- **Portal Access**: Dedicated reseller interface
- **Performance Analytics**: Sales performance metrics

### 8. Analytics Module (`dotmac_isp.modules.analytics`)
- **Business Intelligence**: Comprehensive reporting and dashboards
- **Data Visualization**: Charts, graphs, and interactive reports
- **Custom Reports**: Flexible report builder
- **Export Capabilities**: PDF, Excel, and CSV exports

### 9. Inventory Module (`dotmac_isp.modules.inventory`)
- **Equipment Tracking**: Router, modem, and hardware inventory
- **Warehouse Management**: Multi-location inventory control
- **Procurement**: Purchase order and vendor management
- **Asset Lifecycle**: Equipment deployment and retirement

### 10. Field Operations Module (`dotmac_isp.modules.field_ops`)
- **Work Orders**: Installation and maintenance scheduling
- **Technician Management**: Field staff coordination
- **Mobile App Support**: Technician mobile interface
- **GPS Tracking**: Real-time technician location

### 11. Compliance Module (`dotmac_isp.modules.compliance`)
- **Regulatory Compliance**: FCC, GDPR, and other regulations
- **Audit Trails**: Comprehensive activity logging
- **Data Protection**: Privacy and data security controls
- **Reporting**: Compliance reports and certifications

### 12. Notifications Module (`dotmac_isp.modules.notifications`)
- **Email Templates**: Customizable email communications
- **SMS Integration**: Text message notifications
- **Push Notifications**: Mobile and web push messages
- **Automation Rules**: Event-triggered communications

### 13. Licensing Module (`dotmac_isp.modules.licensing`)
- **Feature Control**: Module and feature licensing
- **Usage Limits**: Customer and service limitations
- **Plan Management**: Different licensing tiers
- **Compliance Tracking**: License usage monitoring

## Portal Interfaces

### Admin Portal (`dotmac_isp.portals.admin`)
**Target Users**: ISP administrators and managers
- System-wide dashboard and analytics
- Customer and service management
- Financial reporting and billing oversight
- Support ticket management
- System configuration and settings

### Customer Portal (`dotmac_isp.portals.customer`)
**Target Users**: End customers (residential and business)
- Account management and billing
- Service usage monitoring
- Payment processing and history
- Support ticket creation and tracking
- Service plan changes and upgrades

### Reseller Portal (`dotmac_isp.portals.reseller`)
**Target Users**: Partner resellers and agents
- Sales performance dashboard
- Customer management for reseller accounts
- Commission tracking and reporting
- Marketing materials and resources
- Lead and opportunity management

### Technician Portal (`dotmac_isp.portals.technician`)
**Target Users**: Field technicians and installers
- Work order management
- Customer service information
- Inventory tracking and usage
- GPS navigation and scheduling
- Mobile-optimized interface

## Database Architecture

### Multi-Tenant Support
- All models inherit from `TenantModel` for multi-tenancy
- Tenant isolation at the database level
- Shared infrastructure with isolated data

### Base Model Classes
- **BaseModel**: Common fields (id, timestamps, soft delete)
- **TenantModel**: Adds tenant_id for multi-tenancy
- **Mixins**: Reusable components (Contact, Address, Audit, Status)

### Relationships
- Well-defined foreign key relationships
- Proper cascade behaviors for data integrity
- Optimized queries with SQLAlchemy 2.0 patterns

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 12+
- Redis 6+
- Poetry for dependency management

### Installation

1. **Clone and navigate to the project**:
   ```bash
   cd /home/dotmac_framework/dotmac_isp_framework
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start services with Docker**:
   ```bash
   docker-compose up -d
   ```

5. **Run database migrations**:
   ```bash
   poetry run alembic upgrade head
   ```

6. **Start the development server**:
   ```bash
   poetry run uvicorn dotmac_isp.main:app --reload
   ```

### Docker Development

For containerized development:

```bash
# Build and start all services
docker-compose up --build

# View logs
docker-compose logs -f app

# Execute commands in container
docker-compose exec app poetry run alembic upgrade head
```

## API Documentation

Once running, access the interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Configuration

### Enhanced Configuration Management

The DotMac ISP Framework uses an advanced configuration system with:

- **OpenBao/Vault Integration**: Centralized secrets management with automatic rotation
- **Field-Level Encryption**: Sensitive configuration data encrypted at rest
- **Audit Logging**: Complete configuration change tracking with approval workflows
- **Hot-Reloading**: Zero-downtime configuration updates
- **Disaster Recovery**: Automated configuration backup and recovery
- **Compliance Validation**: SOC2, GDPR, PCI DSS, ISO27001 compliance checks

### Configuration Sources (Priority Order)

1. **OpenBao Vault**: Production secrets and sensitive configuration
2. **Environment Variables**: Runtime configuration overrides
3. **Configuration Files**: Default settings and templates
4. **Database**: Tenant-specific configuration settings

### Environment Variables

Key configuration options:

```env
# Application
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=your-secret-key

# Enhanced Configuration
OPENBAO_URL=https://vault.dotmac.internal:8200
OPENBAO_TOKEN=hvs.your-token-here
OPENBAO_NAMESPACE=dotmac/tenant-{tenant-id}
CONFIG_ENCRYPTION_KEY=base64-encoded-key
ENABLE_CONFIG_HOT_RELOAD=true
CONFIG_AUDIT_WEBHOOK_URL=https://audit.dotmac.internal/webhook

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dotmac_isp
ASYNC_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dotmac_isp

# Redis
REDIS_URL=redis://localhost:6379/0

# External Services (Managed via OpenBao in production)
STRIPE_SECRET_KEY=sk_test_...  # Development only
TWILIO_ACCOUNT_SID=AC...       # Development only
SMTP_SERVER=smtp.example.com   # Development only
```

### Configuration Management CLI

```bash
# Manage secrets through OpenBao
poetry run python -m dotmac_isp.cli.secrets store "stripe/secret_key" "sk_live_..."
poetry run python -m dotmac_isp.cli.secrets rotate "database/password"
poetry run python -m dotmac_isp.cli.secrets list

# Hot-reload configuration without downtime
curl -X POST http://localhost:8000/admin/config/reload \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"component": "database", "validate_only": false}'

# Create configuration backup
curl -X POST http://localhost:8000/admin/config/backup \
  -H "Authorization: Bearer <admin-token>"

# Validate compliance
curl -X GET http://localhost:8000/admin/config/compliance \
  -H "Authorization: Bearer <admin-token>"
```

## Security Features

### Authentication & Authorization
- JWT access and refresh tokens
- Password hashing with bcrypt
- Role-based access control (RBAC)
- Multi-factor authentication support

### Data Protection
- SQL injection prevention through ORM
- Input validation with Pydantic
- CORS protection
- Rate limiting capabilities
- Audit logging for compliance

### Multi-Tenancy
- Complete data isolation between tenants
- Secure tenant identification
- Shared infrastructure with isolated data

## Deployment

### Production Deployment

1. **Environment Setup**:
   ```bash
   # Set production environment variables
   export ENVIRONMENT=production
   export DEBUG=false
   export DATABASE_URL=postgresql://...
   ```

2. **Database Migration**:
   ```bash
   poetry run alembic upgrade head
   ```

3. **Start Services**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Scaling Considerations
- **Horizontal Scaling**: Deploy multiple app instances behind load balancer
- **Database**: Use PostgreSQL read replicas for read-heavy workloads
- **Caching**: Redis cluster for high availability
- **Monitoring**: Integrate with Prometheus, Grafana, or similar

## Testing

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=dotmac_isp

# Run specific test categories
poetry run pytest -m unit
poetry run pytest -m integration
```

### Test Structure
- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: Database and external service integration
- **API Tests**: End-to-end API functionality testing

## Monitoring & Observability

### Health Checks
- **Application**: `/health` endpoint
- **Database**: Connection and query tests
- **Redis**: Cache connectivity tests
- **External Services**: Payment gateway and SMS provider checks

### Logging
- Structured JSON logging
- Request/response logging
- Error tracking and alerting
- Performance monitoring

## Contributing

### Code Standards
- Follow PEP 8 style guidelines
- Use type hints throughout
- Maintain test coverage above 80%
- Document all public APIs

### Development Workflow
1. Create feature branch from main
2. Implement changes with tests
3. Run quality checks: `poetry run black . && poetry run isort . && poetry run mypy .`
4. Submit pull request for review

## Support & Documentation

### Additional Resources
- **API Reference**: Available at `/docs` when running
- **Database Schema**: Generated ERD in `/docs/database/`
- **Module Documentation**: Individual module README files
- **Deployment Guides**: Production deployment instructions

### Getting Help
- Review API documentation at `/docs`
- Check module-specific documentation
- Examine test files for usage examples
- Review Docker Compose configuration for deployment

## License

This project is licensed under the MIT License. See LICENSE file for details.

---

**DotMac ISP Framework** - Complete ISP management platform built for scale, security, and reliability.