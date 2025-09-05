# DotMac Platform Services

Unified platform services package providing authentication, secrets management, and observability capabilities for DotMac applications.

## Features

### 🔐 Authentication Services
- JWT token management with RS256/HS256 support
- Role-Based Access Control (RBAC) engine
- Multi-factor authentication (TOTP, SMS, Email)
- Session management with Redis backend
- Service-to-service authentication
- API key management
- OAuth2/OIDC provider integration

### 🔒 Secrets Management
- HashiCorp Vault integration
- Field-level encryption/decryption
- Secrets rotation automation
- Multi-tenant secrets isolation
- Environment-based configuration
- Audit logging for secret access

### 📊 Observability
- OpenTelemetry tracing and metrics
- Prometheus metrics export
- Structured logging with correlation IDs
- Performance monitoring
- Business metrics tracking
- Health check endpoints
- Dashboard integration ready

## Installation

```bash
# Basic installation
pip install dotmac-platform-services

# With core utilities
pip install "dotmac-platform-services[core]"

# With database integration
pip install "dotmac-platform-services[database]"

# Full installation
pip install "dotmac-platform-services[all]"
```

## Quick Start

### Authentication

```python
from dotmac.platform.auth import AuthService, JWTService, RBACEngine

# JWT token management
jwt_service = JWTService(
    secret_key="your-secret",
    algorithm="HS256"
)

token = jwt_service.create_access_token(
    subject="user123",
    permissions=["read:users", "write:users"]
)

# RBAC permissions
rbac = RBACEngine()
rbac.add_role("admin", ["read:*", "write:*", "delete:*"])
rbac.add_role("user", ["read:own", "write:own"])

has_permission = rbac.check_permission(
    user_roles=["admin"],
    required_permission="write:users"
)
```

### Secrets Management

```python
from dotmac.platform.secrets import SecretsManager, VaultProvider

# Vault-backed secrets
secrets = SecretsManager(
    provider=VaultProvider(
        url="https://vault.company.com",
        token="vault-token"
    )
)

# Store and retrieve secrets
await secrets.set_secret("database/password", "secure-password")
password = await secrets.get_secret("database/password")

# Field encryption
encrypted = await secrets.encrypt_field("sensitive-data")
decrypted = await secrets.decrypt_field(encrypted)
```

### Observability

```python
from dotmac.platform.observability import init_observability, get_tracer, get_metrics

# Initialize observability
init_observability(
    service_name="my-service",
    otlp_endpoint="http://jaeger:14268",
    prometheus_port=9090
)

# Distributed tracing
tracer = get_tracer(__name__)
with tracer.start_as_current_span("operation"):
    # Your code here
    pass

# Custom metrics
metrics = get_metrics()
counter = metrics.create_counter("requests_total")
counter.add(1, {"method": "GET", "status": "200"})
```

## Architecture

### Design Principles

1. **DRY (Don't Repeat Yourself)**: Shared utilities in dotmac-core
2. **Logical Grouping**: Related functionality organized together
3. **Production Ready**: Battle-tested components with comprehensive testing
4. **Clear Dependencies**: core → platform-services → business-logic
5. **Extensible**: Plugin architecture for custom providers

### Package Structure

```
dotmac/platform/
├── auth/           # Authentication services
│   ├── jwt.py      # JWT token management
│   ├── rbac.py     # Role-based access control
│   ├── sessions.py # Session management
│   ├── mfa.py      # Multi-factor authentication
│   └── providers/  # OAuth2/OIDC providers
├── secrets/        # Secrets management
│   ├── manager.py  # Secrets manager interface
│   ├── vault.py    # HashiCorp Vault provider
│   ├── encryption.py # Field encryption
│   └── rotation.py # Secrets rotation
└── observability/  # Monitoring and observability
    ├── tracing.py  # OpenTelemetry tracing
    ├── metrics.py  # Prometheus metrics
    ├── logging.py  # Structured logging
    └── health.py   # Health checks
```

### Integration with DotMac Core

Platform Services integrates seamlessly with other DotMac packages:

- **dotmac-core**: Shared utilities, exceptions, and base classes
- **dotmac-database**: Database session management and models
- **dotmac-tenant**: Multi-tenant awareness and isolation

## Configuration

### Environment Variables

```bash
# Authentication
DOTMAC_JWT_SECRET_KEY=your-jwt-secret
DOTMAC_JWT_ALGORITHM=HS256
DOTMAC_JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

# Secrets Management
DOTMAC_VAULT_URL=https://vault.company.com
DOTMAC_VAULT_TOKEN=vault-token
DOTMAC_VAULT_MOUNT_POINT=secret

# Observability
DOTMAC_OTLP_ENDPOINT=http://jaeger:14268
DOTMAC_PROMETHEUS_PORT=9090
DOTMAC_LOG_LEVEL=INFO
```

### Application Factory Integration

```python
from fastapi import FastAPI
from dotmac.platform.auth import add_auth_middleware
from dotmac.platform.observability import add_observability_middleware

app = FastAPI()

# Add platform services
add_auth_middleware(app)
add_observability_middleware(app)
```

## Development

### Setup

```bash
cd packages/dotmac-platform-services
poetry install --with dev
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/test_auth.py -v
```

### Code Quality

```bash
# Format code
poetry run black src tests

# Lint code
poetry run ruff check src tests

# Type checking
poetry run mypy src
```

## Migration Guide

### From Individual Packages

If you're migrating from separate `dotmac-auth`, `dotmac-secrets`, and `dotmac-observability` packages:

```python
# Old imports
from dotmac.auth import JWTService
from dotmac.secrets import SecretsManager
from dotmac.observability import get_tracer

# New imports
from dotmac.platform.auth import JWTService
from dotmac.platform.secrets import SecretsManager  
from dotmac.platform.observability import get_tracer
```

The APIs remain the same, only import paths change.

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://docs.dotmac.com/platform-services
- Issues: https://github.com/dotmac/platform-services/issues
- Discussions: https://github.com/dotmac/platform-services/discussions