# DotMac Application Factory

A unified application factory and lifecycle management package for DotMac platforms.

## Features

- **App Factory**: Deployment-aware builders for different platform types
- **Platform/Tenant Configuration**: Comprehensive configuration types with deployment contexts
- **Lifecycle Orchestration**: Standardized startup/shutdown procedures
- **Router Registration**: Auto-discovery and safe router loading
- **Middleware Composition**: Provider-based middleware stack with clean interfaces
- **Standard Endpoints**: Health checks, platform info, and deployment-specific endpoints

## Quick Start

### Basic Usage

```python
from dotmac.application import create_app, PlatformConfig

# Create a basic platform configuration
config = PlatformConfig(
    platform_name="my_platform",
    title="My Platform",
    description="My platform description"
)

# Create the FastAPI application
app = create_app(config)
```

### Platform-Specific Apps

```python
from dotmac.application import (
    create_management_platform_app,
    create_isp_framework_app,
    TenantConfig,
    DeploymentContext,
    DeploymentMode
)

# Create management platform app
management_app = create_management_platform_app()

# Create ISP framework app for specific tenant
tenant_config = TenantConfig(
    tenant_id="example-tenant",
    deployment_context=DeploymentContext(
        mode=DeploymentMode.TENANT_CONTAINER,
        tenant_id="example-tenant"
    )
)

isp_app = create_isp_framework_app(tenant_config=tenant_config)
```

### Provider-Based Middleware

```python
from dotmac.application import create_app, Providers, PlatformConfig

# Define your providers (implement the provider protocols)
class MySecurityProvider:
    def apply_jwt_authentication(self, app, config):
        # Your JWT auth implementation
        pass
    
    def apply_csrf_protection(self, app, config):
        # Your CSRF protection implementation  
        pass
    
    def apply_rate_limiting(self, app, config):
        # Your rate limiting implementation
        pass

class MyTenantProvider:
    def apply_tenant_security(self, app, config):
        # Your tenant security implementation
        pass
    
    def apply_tenant_isolation(self, app, config):
        # Your tenant isolation implementation
        pass

class MyObservabilityProvider:
    def apply_metrics(self, app, config):
        # Your metrics implementation
        pass
    
    def apply_tracing(self, app, config):
        # Your tracing implementation
        pass
    
    def apply_logging(self, app, config):
        # Your logging implementation
        pass

# Create providers container
providers = Providers(
    security=MySecurityProvider(),
    tenant=MyTenantProvider(),
    observability=MyObservabilityProvider()
)

# Create app with providers
config = PlatformConfig(
    platform_name="my_platform",
    title="My Platform",
    description="My platform with providers"
)

app = create_app(config, providers=providers)
```

### Router Configuration

```python
from dotmac.application import PlatformConfig, RouterConfig

config = PlatformConfig(
    platform_name="my_platform",
    title="My Platform",
    description="Platform with routers",
    routers=[
        # Specific router
        RouterConfig(
            module_path="my_app.routers.auth",
            prefix="/api/v1/auth",
            required=True,
            tags=["authentication"]
        ),
        
        # Auto-discovery
        RouterConfig(
            module_path="my_app.modules",
            prefix="/api/v1",
            auto_discover=True,
            tags=["api"]
        ),
    ]
)

app = create_app(config)
```

## Configuration

### PlatformConfig

The main configuration class that defines your platform:

```python
from dotmac.application import (
    PlatformConfig, 
    DeploymentContext,
    DeploymentMode,
    ResourceLimits
)

config = PlatformConfig(
    # Basic info
    platform_name="my_platform",
    title="My Platform",
    description="Platform description",
    version="1.0.0",
    
    # Deployment context
    deployment_context=DeploymentContext(
        mode=DeploymentMode.TENANT_CONTAINER,
        tenant_id="my-tenant",
        resource_limits=ResourceLimits(
            memory_limit="1Gi",
            cpu_limit="500m"
        )
    ),
    
    # Router configuration
    routers=[...],
    
    # Feature flags and startup tasks
    startup_tasks=["initialize_database", "setup_ssl"],
    shutdown_tasks=["cleanup_resources"]
)
```

### Deployment Modes

- `MANAGEMENT_PLATFORM`: Multi-tenant management platform
- `TENANT_CONTAINER`: Individual tenant container deployment
- `STANDALONE`: Standalone deployment
- `DEVELOPMENT`: Development mode with extra debugging

### Provider Interfaces

The package defines protocol interfaces for clean middleware composition:

- `SecurityProvider`: JWT auth, CSRF, rate limiting
- `TenantBoundaryProvider`: Tenant security and isolation  
- `ObservabilityProvider`: Metrics, tracing, logging

## Standard Endpoints

Every app gets these standard endpoints:

- `GET /` - Platform information and status
- `GET /health` - Basic health check
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe  
- `GET /health/startup` - Kubernetes startup probe
- `GET /favicon.ico` - Favicon (204 No Content)

### Deployment-Specific Endpoints

**Tenant Container Mode:**
- `GET /tenant/info` - Tenant container information

**Management Platform Mode:**
- `GET /management/stats` - Platform statistics

**Development Mode:**
- `GET /dev/config` - Current configuration
- `GET /dev/routes` - All registered routes
- `GET /dev/app-state` - Current app state

## Migration from dotmac_shared.application

### Before (dotmac_shared)
```python
from dotmac_shared.application import create_management_platform_app

app = create_management_platform_app(config)
```

### After (dotmac.application)
```python
from dotmac.application import create_management_platform_app

app = create_management_platform_app(config)
```

The API is largely compatible, but now uses provider-based composition for middleware.

## Architecture

### Provider-Based Composition

Instead of hardcoded platform-specific imports, the new architecture uses provider interfaces:

```python
# Old approach - hardcoded imports
from dotmac_isp.middleware import add_tenant_security  # ❌

# New approach - provider interface
class TenantProvider:
    def apply_tenant_security(self, app, config):  # ✅
        from dotmac_isp.middleware import add_tenant_security
        add_tenant_security(app)
```

### Deployment Awareness

The package automatically configures based on deployment context:

- Container resource limits affect observability tier
- Tenant containers disable API docs for security  
- Management platforms get enhanced monitoring
- Development mode enables debugging endpoints

## Development

### Testing Your Providers

```python
import pytest
from fastapi import FastAPI
from dotmac.application import apply_standard_middleware, PlatformConfig, Providers

def test_my_providers():
    app = FastAPI()
    config = PlatformConfig(
        platform_name="test",
        title="Test Platform",
        description="Test"
    )
    
    providers = Providers(
        security=MySecurityProvider(),
        tenant=MyTenantProvider(), 
        observability=MyObservabilityProvider()
    )
    
    # Apply middleware
    applied = apply_standard_middleware(app, config=config, providers=providers)
    
    # Test middleware was applied
    assert "JWTAuthenticationMiddleware" in applied
    assert "TenantSecurityEnforcerMiddleware" in applied
    assert "MetricsMiddleware" in applied
```

## Requirements

- Python 3.10+
- FastAPI 0.110+
- Starlette 0.36+

## License

MIT License