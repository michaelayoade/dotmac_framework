# Changelog

All notable changes to the `dotmac-application` package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-XX

### Added

#### Core Features
- **Application Factory**: Unified factory for creating FastAPI applications with deployment awareness
- **Provider-Based Middleware**: Clean composition interfaces for security, tenant, and observability providers
- **Deployment Contexts**: Support for Management Platform, Tenant Container, Standalone, and Development modes
- **Lifecycle Management**: Standardized startup/shutdown orchestration with error handling
- **Router Registry**: Safe auto-discovery and registration of API routers with security validation
- **Standard Endpoints**: Health checks, platform info, and deployment-specific endpoints

#### Configuration System
- `PlatformConfig`: Main configuration class with deployment awareness
- `DeploymentContext`: Deployment-specific configuration and resource limits
- `TenantConfig`: Tenant container configuration with isolation settings
- `RouterConfig`: Router registration configuration with auto-discovery
- `ResourceLimits`: Container resource limits with plan-based defaults

#### Provider Protocols
- `SecurityProvider`: Interface for JWT auth, CSRF protection, and rate limiting
- `TenantBoundaryProvider`: Interface for tenant security and isolation
- `ObservabilityProvider`: Interface for metrics, tracing, and logging

#### Factory Functions
- `create_app()`: Create standard DotMac application
- `create_management_platform_app()`: Create management platform with defaults
- `create_isp_framework_app()`: Create ISP framework application with tenant support

#### Standard Endpoints
- Health check endpoints: `/health`, `/health/live`, `/health/ready`, `/health/startup`
- Platform information: `/` (root endpoint with deployment context)
- Deployment-specific endpoints for tenant containers, management platform, and development

#### Middleware Composition
- `apply_standard_middleware()`: Provider-based middleware application
- `StandardMiddlewareStack`: Configurable middleware stack with deployment awareness
- Support for CORS, TrustedHost, and provider-based middleware components

#### Router Management
- `SafeRouterLoader`: Secure router loading with validation
- `RouterRegistry`: Central router registration with auto-discovery
- Security validation for router module paths
- Support for both explicit and auto-discovered routers

#### Lifecycle Management
- `StandardLifecycleManager`: Coordinated startup/shutdown sequences
- Platform-specific lifecycle tasks
- Error handling and graceful degradation
- Integration with FastAPI lifespan context

### Architecture

#### Decoupled Design
- Removed direct platform-specific imports from application package
- Provider interfaces allow clean separation of concerns
- Deployment-aware configuration without tight coupling

#### Security
- Router module path validation prevents unauthorized imports
- Tenant container mode disables API documentation for security
- Configurable security middleware through provider interfaces

#### Observability
- Tiered observability configuration (minimal, standard, comprehensive, enterprise)
- Resource-aware observability tier selection
- Provider-based metrics, tracing, and logging integration

### Migration Notes

#### From dotmac_shared.application

This package replaces `dotmac_shared.application` with a cleaner, provider-based architecture:

**Before:**
```python
from dotmac_shared.application import create_management_platform_app
app = create_management_platform_app(config)
```

**After:**
```python  
from dotmac.application import create_management_platform_app
app = create_management_platform_app(config)
```

#### Middleware Changes

**Before (tightly coupled):**
```python
# Middleware was applied with hardcoded platform imports
middleware_stack = StandardMiddlewareStack(config)
middleware_stack.apply_to_app(app)
```

**After (provider-based):**
```python
# Middleware applied through provider interfaces
providers = Providers(
    security=MySecurityProvider(),
    tenant=MyTenantProvider(),
    observability=MyObservabilityProvider()
)
apply_standard_middleware(app, config=config, providers=providers)
```

### Breaking Changes

- Middleware composition now requires provider implementations
- Direct platform imports removed from application package
- Some lifecycle task implementations moved to provider interfaces

### Dependencies

- Python 3.10+
- FastAPI 0.110+  
- Starlette 0.36+
- typing-extensions for Protocol support
- Pydantic 2.0+ for configuration validation

### Development

- Full type hints support (PEP 561 compliant)
- Comprehensive test suite covering factory, middleware, routing, and lifecycle
- Development tools integration (black, ruff, mypy)
- Performance optimizations for container deployments

---

## [Unreleased]

### Planned Features
- Integration with OpenTelemetry for observability providers
- Enhanced auto-discovery for router modules
- Performance monitoring and metrics collection
- Additional deployment modes (edge, serverless)
- Configuration validation enhancements