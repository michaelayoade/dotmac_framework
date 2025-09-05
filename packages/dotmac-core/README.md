# DotMac Core

**Production-ready core foundation package for the DotMac Framework.**

## Overview

`dotmac-core` consolidates foundational components from `dotmac-database`, `dotmac-tenant`, and other core packages into a unified, production-ready package that eliminates DRY violations across the framework.

## Features

### 🗄️ Database Foundation
- **Declarative Base**: SQLAlchemy 2.0+ compatible base classes
- **Model Mixins**: UUID primary keys, timestamps, audit trails, table naming
- **Multi-tenant Support**: Tenant isolation patterns and utilities
- **Production Ready**: Connection pooling, error handling, type safety

### 🏢 Tenant Management
- **Identity Resolution**: Subdomain and header-based tenant resolution
- **Context Management**: Thread-safe tenant context with asyncio support
- **Metadata Support**: Configurable tenant settings and feature flags
- **Security Integration**: Tenant-aware permissions and isolation

### 🚨 Exception Hierarchy
- **Consolidated Exceptions**: Single source of truth for all framework exceptions
- **Structured Error Details**: Rich error context with codes and metadata
- **Production Logging**: Structured error logging with tenant context
- **API Integration**: HTTP-ready error serialization

### ⚙️ Configuration Management
- **Environment-based**: Secure configuration from environment variables
- **Validation**: Pydantic-based configuration validation
- **Production Hardening**: Security validations for production deployments
- **Feature Flags**: Runtime feature toggling support

### 🔧 Common Types
- **UUID Support**: Cross-database UUID type handling
- **Type Safety**: Full mypy compatibility with proper annotations
- **Production Patterns**: Optimized for high-performance applications

## Installation

```bash
# Core installation
pip install dotmac-core

# With optional dependencies
pip install "dotmac-core[all]"
pip install "dotmac-core[fastapi,postgres,redis]"
```

## Quick Start

### Database Models

```python
from dotmac.core import BaseModel, TenantBaseModel

class User(BaseModel):
    """User model with automatic UUID, timestamps, audit trail."""
    __tablename__ = "users"
    
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)

class TenantData(TenantBaseModel):
    """Tenant-isolated data model."""
    __tablename__ = "tenant_data"
    
    name: Mapped[str] = mapped_column(String(100))
    # tenant_id automatically included and indexed
```

### Configuration

```python
from dotmac.core import CoreSettings, get_settings

# Environment-based configuration
settings = get_settings()

# Access typed configuration
db_url = settings.database.url
cache_backend = settings.cache.backend
jwt_secret = settings.security.secret_key
```

### Tenant Context

```python
from dotmac.core import get_current_tenant, require_current_tenant

# Get current tenant (returns None if not set)
tenant = get_current_tenant()

# Require tenant context (raises TenantNotFoundError if not set)
tenant = require_current_tenant()

# Use tenant context
if tenant.has_feature("advanced_analytics"):
    # Feature-flagged code
    pass
```

### Exception Handling

```python
from dotmac.core import (
    DotMacError, 
    ValidationError, 
    TenantNotFoundError,
    DatabaseError
)

try:
    # Framework operations
    pass
except ValidationError as e:
    # Handle validation errors
    logger.error("Validation failed", error=e.to_dict())
except TenantNotFoundError as e:
    # Handle tenant resolution errors
    return {"error": e.to_dict()}, 404
except DatabaseError as e:
    # Handle database errors
    logger.error("Database error", error=e.to_dict())
    return {"error": "Internal server error"}, 500
```

## Architecture Benefits

### ✅ DRY Compliance
- **Single Source of Truth**: Eliminates 562+ DRY violations found in audit
- **Consistent Patterns**: Standardized approaches across all framework components
- **Centralized Exceptions**: Consolidated exception hierarchy prevents duplication

### 🔒 Production Ready
- **Security Hardened**: Validates production configurations and secrets
- **Performance Optimized**: Efficient database connections and caching
- **Error Resilience**: Comprehensive error handling and recovery patterns
- **Observability**: Structured logging with tenant and request context

### 🏗️ Clean Architecture
- **Package Boundaries**: Clear separation of concerns and dependencies
- **Type Safety**: Full typing support for IDE integration and validation
- **Testing Support**: Built-in patterns for unit and integration testing
- **Documentation**: Comprehensive docstrings and usage examples

## Migration from Legacy Packages

### From dotmac-database

```python
# Before
from dotmac.database import Base, UUIDMixin, TimestampMixin

# After  
from dotmac.core import Base, UUIDMixin, TimestampMixin
```

### From dotmac-tenant

```python
# Before
from dotmac.tenant import get_current_tenant, TenantContext

# After
from dotmac.core import get_current_tenant, TenantContext
```

### From scattered exceptions

```python
# Before
from dotmac_shared.exceptions import ValidationError
from dotmac_isp.exceptions import AuthenticationError
from some_package.exceptions import ConfigurationError

# After
from dotmac.core import ValidationError, AuthenticationError, ConfigurationError
```

## Development

```bash
# Development installation
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Code formatting
black src/
isort src/

# Linting
ruff check src/
```

## License

MIT License - see LICENSE file for details.

## Support

- **Documentation**: https://docs.dotmac.com/core
- **Issues**: https://github.com/dotmac-framework/dotmac-core/issues
- **Discussions**: https://github.com/dotmac-framework/dotmac-core/discussions