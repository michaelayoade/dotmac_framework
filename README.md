# DotMac ISP Framework

[![CI/CD Pipeline](https://github.com/your-org/dotmac-framework/actions/workflows/lint-and-test.yml/badge.svg)](https://github.com/your-org/dotmac-framework/actions)
[![Security Audit](https://github.com/your-org/dotmac-framework/actions/workflows/security-audit.yml/badge.svg)](https://github.com/your-org/dotmac-framework/actions)
[![Code Quality](https://img.shields.io/codeclimate/maintainability/your-org/dotmac-framework)](https://codeclimate.com/github/your-org/dotmac-framework)
[![Coverage](https://codecov.io/gh/your-org/dotmac-framework/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/dotmac-framework)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive, security-focused telecommunications management framework for Internet Service Providers (ISPs). Built with Python, FastAPI, and modern development practices.

## 🚀 Features

### Core Services
- **Customer Management** - Complete customer lifecycle management
- **Billing & Invoicing** - Automated billing with multiple payment options
- **Service Provisioning** - Automated service deployment and management
- **Network Monitoring** - Real-time network infrastructure monitoring
- **Analytics Dashboard** - Business intelligence and reporting

### Technical Highlights
- **Microservices Architecture** - Scalable, loosely-coupled services
- **Event-Driven Design** - Asynchronous communication via Redis/RabbitMQ
- **API-First Approach** - RESTful APIs with OpenAPI documentation
- **Multi-Tenant Support** - Isolated data and configurations per tenant
- **Security First** - Comprehensive security scanning and best practices

## 📋 Quick Start

### Prerequisites
- Python 3.9+ 
- PostgreSQL 12+
- Redis 6+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/dotmac-framework.git
   cd dotmac-framework
   ```

2. **Set up development environment**
   ```bash
   make install-dev
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run tests**
   ```bash
   make test
   ```

5. **Start development servers**
   ```bash
   # API Gateway
   make run-api-gateway
   
   # Customer Portal (separate terminal)
   make run-customer-portal
   
   # Reseller Portal (separate terminal)  
   make run-reseller-portal
   ```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Customer      │    │   Reseller      │    │   Admin         │
│   Portal        │    │   Portal        │    │   Dashboard     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   API Gateway   │
                    └─────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │   Identity      │ │   Billing       │ │   Services      │
    │   Service       │ │   Service       │ │   Service       │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Event Bus     │
                    │   (Redis)       │
                    └─────────────────┘
```

### Package Structure
```
dotmac_framework/
├── dotmac_core_events/     # Event system and messaging
├── dotmac_core_ops/        # Operational utilities
├── dotmac_identity/        # Authentication and authorization
├── dotmac_billing/         # Billing and payment processing
├── dotmac_services/        # Service management
├── dotmac_networking/      # Network infrastructure
├── dotmac_analytics/       # Business intelligence
├── dotmac_api_gateway/     # API gateway and routing
├── dotmac_platform/        # Platform coordination
├── dotmac_devtools/        # Development tools
└── templates/              # Service templates and examples
```

## 🛠️ Development

### Available Commands

```bash
# Environment Setup
make install-dev           # Set up development environment
make clean                 # Clean build artifacts

# Code Quality
make lint                  # Run linting with complexity checks
make format                # Format code with Black and Ruff
make type-check           # Run MyPy type checking
make security             # Run security scans

# Testing
make test                 # Run all tests with coverage
make test-unit           # Run only unit tests (fast)
make test-integration    # Run integration tests
make test-package PACKAGE=dotmac_identity  # Test specific package

# Dependencies
make deps-compile        # Compile dependency lockfiles
make deps-update         # Update dependencies
make deps-check          # Check for vulnerabilities

# Build & Package
make build               # Build all packages
make validate-packages   # Validate package structure

# Quality Assurance
make check               # Run all quality checks
make fix                 # Fix auto-fixable issues
make complexity-report   # Generate complexity analysis
```

### Code Quality Standards

We maintain high code quality through:

- **Complexity Limits**: Functions max 10 complexity, 8 arguments, 50 statements
- **Test Coverage**: Minimum 80% coverage required
- **Security Scanning**: Bandit, Safety, Semgrep, pip-audit
- **Type Checking**: MyPy for gradual type adoption
- **Code Formatting**: Black + Ruff for consistent style

### Contributing Guidelines

1. **Fork the repository** and create a feature branch
2. **Follow code quality standards** - run `make check` before committing
3. **Write tests** for new functionality (maintain 80%+ coverage)
4. **Update documentation** for user-facing changes
5. **Submit a pull request** with clear description

## 🔒 Security

Security is a top priority for the DotMac Framework:

- **Automated Scanning**: Daily security audits via GitHub Actions
- **Dependency Monitoring**: Dependabot for vulnerability tracking
- **SARIF Integration**: Security findings in GitHub Security tab
- **Secret Detection**: TruffleHog prevents credential leaks
- **Compliance**: SOC 2, GDPR, and PCI DSS considerations

See [SECURITY.md](.github/SECURITY.md) for security policy and reporting guidelines.

## 📚 Documentation

- **[API Reference](docs/api/)** - OpenAPI/Swagger documentation
- **[Architecture Guide](docs/architecture.md)** - System design and patterns
- **[Deployment Guide](docs/deployment.md)** - Production deployment instructions
- **[Developer Guide](docs/development.md)** - Detailed development setup
- **[User Manual](docs/user-guide/)** - End-user documentation

## 🧪 Testing

The framework includes comprehensive testing:

```bash
# Unit Tests - Fast, isolated tests
pytest -m unit

# Integration Tests - Cross-service testing  
pytest -m integration

# Contract Tests - API compatibility
pytest -m contract

# End-to-End Tests - Full workflow testing
pytest -m e2e

# Performance Tests - Load and stress testing
pytest -m performance
```

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**
   ```bash
   # Production dependencies only
   pip install --require-hashes -r requirements.lock
   ```

2. **Database Migration**
   ```bash
   alembic upgrade head
   ```

3. **Security Configuration**
   ```bash
   # Ensure all security environment variables are set
   export SECURE_SSL_REDIRECT=true
   export SECURE_HSTS_SECONDS=31536000
   ```

4. **Service Start**
   ```bash
   # Use process manager like systemd or supervisor
   uvicorn dotmac_api_gateway.runtime.app:app --host 0.0.0.0 --port 8000
   ```

### Docker Deployment

```bash
# Clone the repository
git clone https://github.com/michaelayoade/dotmac-platform-core.git
cd dotmac-platform-core

# Start with Docker Compose
docker-compose up -d

# The platform will be available at:
# - API: http://localhost:8000
# - Admin UI: http://localhost:3000
# - Docs: http://localhost:8000/docs
```

## 📊 Monitoring

### Application Monitoring
- **Metrics**: Prometheus-compatible metrics endpoint
- **Logging**: Structured JSON logging with ELK stack support
- **Tracing**: OpenTelemetry for distributed tracing
- **Health Checks**: Built-in health check endpoints

### Business Monitoring
- **KPIs**: Customer acquisition, churn, revenue metrics
- **SLA Monitoring**: Service uptime and performance tracking
- **Network Monitoring**: SNMP-based infrastructure monitoring

## 🤝 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: [GitHub Issues](https://github.com/your-org/dotmac-framework/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/dotmac-framework/discussions)
- **Security**: See [SECURITY.md](.github/SECURITY.md) for security issues

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Acknowledgments

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Python SQL toolkit and ORM
- **Pydantic** - Data validation using Python type hints
- **Redis** - In-memory data structure store
- **PostgreSQL** - Advanced open source database

---

**Built with ❤️ for the ISP community**

*This framework is designed for defensive security purposes only. Any use for malicious activities is strictly prohibited.*