# Configuration Management Guide

## Overview

The DotMac platform uses a standardized configuration management system based on Pydantic settings that ensures consistency, security, and observability across all services.

## Configuration Architecture

### Base Configuration Class

All services inherit from `BaseServiceSettings` located in `shared/configuration/base.py`. This provides:

- **Mandatory Security**: Required secret keys, JWT configuration
- **Required Infrastructure**: Database, cache, and background task connections
- **Mandatory Observability**: SignOz integration for metrics, traces, and logs
- **Consistent Validation**: Production security checks and field validation
- **Standardized Patterns**: Environment handling, CORS, rate limiting

### Service-Specific Configuration

Each service extends the base configuration with its specific needs:

- **ISP Framework**: `isp-framework/src/dotmac_isp/core/settings.py`
- **Management Platform**: `management-platform/app/config.py`

## Environment Files

### File Structure

All services follow this environment file structure:

```
.env.example          # Template with all possible settings (committed)
.env.development      # Development defaults (committed)
.env.staging          # Staging defaults (committed)
.env.production       # Production template with empty secrets (committed)
.env                  # Local overrides (NEVER committed)
```

### Loading Priority

Environment files are loaded in this order (highest to lowest priority):

1. `.env` - Local overrides
2. `.env.{ENVIRONMENT}` - Environment-specific settings
3. `.env.development` - Default fallback

## Mandatory Configuration Fields

### Core Application Settings

```bash
# REQUIRED - No defaults allowed
APP_NAME="Service Name"
APP_VERSION="1.0.0"
ENVIRONMENT="development"  # development|staging|production
```

### Security Settings (CRITICAL)

```bash
# REQUIRED - Must be at least 32 characters
# NO DEFAULTS - Must be explicitly set
SECRET_KEY=""              # Generate: openssl rand -hex 32
JWT_SECRET_KEY=""          # Generate: openssl rand -hex 32
JWT_ALGORITHM="HS256"
```

### Infrastructure Connections (REQUIRED)

```bash
# Database - PostgreSQL with async driver
DATABASE_URL="postgresql+asyncpg://user:pass@host:port/db"

# Cache - Redis
REDIS_URL="redis://host:port/db"

# Background Tasks - Celery
CELERY_BROKER_URL="redis://host:port/1"
CELERY_RESULT_BACKEND="redis://host:port/2"
```

### Observability (MANDATORY)

```bash
# SignOz endpoint - REQUIRED for all environments
SIGNOZ_ENDPOINT="http://localhost:3301"     # Development
# SIGNOZ_ENDPOINT="https://cloud.signoz.io" # Production

SIGNOZ_ACCESS_TOKEN=""     # Required for production
ENABLE_METRICS="true"
ENABLE_TRACES="true"
ENABLE_LOGS="true"
```

## Service Configuration Examples

### ISP Framework Configuration

```python
from shared.configuration.base import BaseServiceSettings
from pydantic import Field

class Settings(BaseServiceSettings):
    """ISP Framework specific settings."""

    # Override defaults
    app_name: str = Field(default="DotMac ISP Framework")
    port: int = Field(default=8001)

    # ISP-specific settings
    tenant_id: str = Field(default="development")
    base_domain: str = Field(default="dotmac.io")
    enable_multi_tenancy: bool = Field(default=True)
```

### Management Platform Configuration

```python
from shared.configuration.base import BaseServiceSettings
from pydantic import Field

class Settings(BaseServiceSettings):
    """Management Platform specific settings."""

    # Override defaults
    app_name: str = Field(default="DotMac Management Platform")

    # Management-specific settings
    aws_access_key_id: Optional[str] = Field(None)
    kubernetes_config_path: Optional[str] = Field(None)
    vault_url: Optional[str] = Field(None)
```

## Security Validation

### Automatic Validation

The base configuration automatically validates:

- **Secret Key Strength**: Minimum 32 characters
- **Insecure Patterns**: Rejects keys containing 'development', 'test', 'example', etc.
- **Production Requirements**: Enforces secure configurations in production
- **Observability**: Ensures SignOz is properly configured

### Production Security Checks

In production environment, the system validates:

- Debug mode is disabled
- Secret keys don't contain insecure patterns
- SignOz endpoint is not localhost
- CORS origins don't include localhost
- Database/Redis URLs don't use localhost

## Development Setup

### 1. Copy Environment Template

```bash
cp .env.example .env
```

### 2. Configure Required Fields

```bash
# Generate secure keys
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Set database connection
DATABASE_URL="postgresql+asyncpg://user:pass@localhost/dbname"

# Set cache connection
REDIS_URL="redis://localhost:6379/0"

# Set background tasks
CELERY_BROKER_URL="redis://localhost:6379/1"
CELERY_RESULT_BACKEND="redis://localhost:6379/2"

# Set observability (required)
SIGNOZ_ENDPOINT="http://localhost:3301"
```

### 3. Validate Configuration

```python
from your_service.settings import get_settings

settings = get_settings()
issues = settings.validate_production_security()
if issues:
    print("Configuration issues:", issues)
```

## Production Deployment

### 1. Environment Configuration

```bash
# Use production environment file
ENVIRONMENT=production

# Generate secure secrets
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)  # Must be different from SECRET_KEY

# Configure external services
DATABASE_URL="postgresql+asyncpg://user:pass@prod-db:5432/db"
REDIS_URL="redis://prod-redis:6379/0"
SIGNOZ_ENDPOINT="https://your-signoz-instance.com"
SIGNOZ_ACCESS_TOKEN="your-production-token"
```

### 2. Security Validation

Production deployments automatically fail if:

- Debug mode is enabled
- Secret keys are too short or contain insecure patterns
- SignOz endpoint uses localhost
- Required secrets are missing

## Common Patterns

### Environment-Specific Overrides

```python
class Settings(BaseServiceSettings):
    # Different defaults per environment
    database_pool_size: int = Field(
        default=10 if self.environment == "development" else 50
    )
```

### Custom Validation

```python
@field_validator('custom_field')
@classmethod
def validate_custom(cls, v: str) -> str:
    if not v.startswith('custom_'):
        raise ValueError("Custom field must start with 'custom_'")
    return v
```

### Service Discovery

```python
@property
def service_urls(self) -> dict:
    """Get URLs for dependent services."""
    return {
        'auth': f"http://auth-service:{self.auth_port}",
        'billing': f"http://billing-service:{self.billing_port}"
    }
```

## Troubleshooting

### Common Issues

1. **ImportError**: Check that `shared/configuration` is in Python path
2. **ValidationError**: Ensure all required fields are set in environment
3. **Secret Key Errors**: Generate proper length keys without insecure patterns
4. **Observability Failures**: Verify SignOz endpoint is accessible

### Debug Configuration

```python
# Check loaded configuration
settings = get_settings()
print(f"Environment: {settings.environment}")
print(f"Debug mode: {settings.debug}")
print(f"SignOz endpoint: {settings.signoz_endpoint}")

# Validate configuration
issues = settings.validate_required_services()
if issues:
    for issue in issues:
        print(f"⚠️  {issue}")
```

### Logging Configuration Issues

```python
import logging
logger = logging.getLogger(__name__)

try:
    settings = get_settings()
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Configuration error: {e}")
```

## Best Practices

### 1. Environment File Management

- ✅ Commit `.env.example` with all fields documented
- ✅ Never commit `.env` with actual secrets
- ✅ Use different `.env.{environment}` files for each deployment stage
- ❌ Don't put production secrets in code or committed files

### 2. Security

- ✅ Generate unique secrets for each environment
- ✅ Use strong, random secret keys (32+ characters)
- ✅ Rotate secrets regularly in production
- ❌ Don't use predictable or example secret keys

### 3. Observability

- ✅ Always configure SignOz endpoint
- ✅ Use access tokens in production
- ✅ Enable all telemetry types (metrics, traces, logs)
- ❌ Don't run production without observability

### 4. Validation

- ✅ Add custom validators for service-specific fields
- ✅ Test configuration loading in CI/CD
- ✅ Validate production configurations before deployment
- ❌ Don't skip configuration validation in tests

## Migration Guide

### Updating Existing Services

1. **Install shared configuration**:

   ```python
   from shared.configuration.base import BaseServiceSettings
   ```

2. **Update settings class**:

   ```python
   class Settings(BaseServiceSettings):
       # Keep only service-specific fields
       pass
   ```

3. **Remove duplicate fields**:
   - Remove fields already in BaseServiceSettings
   - Keep only service-specific configuration

4. **Update environment files**:
   - Add mandatory sections to `.env.example`
   - Ensure observability settings are included

5. **Test configuration**:

   ```bash
   python -c "from your_service.settings import get_settings; get_settings()"
   ```

This standardized approach ensures all DotMac services have consistent, secure, and observable configuration management.
