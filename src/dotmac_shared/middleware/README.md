# DotMac Middleware Suite

Unified request processing and security middleware for the DotMac Framework.

## Overview

The DotMac Middleware Suite consolidates **15+ scattered middleware implementations** across the DotMac Framework into a single, configurable, and consistent middleware stack. This provides:

- **Unified Security Posture** - Consistent CSRF, rate limiting, security headers, and input validation
- **Tenant Isolation** - Multi-tenant database context and security enforcement
- **Request Processing** - Structured logging, metrics, tracing, and performance monitoring
- **Authentication Integration** - JWT and session-based auth with RBAC
- **Plugin System** - Extensible middleware plugins for custom functionality

## Quick Start

```python
from fastapi import FastAPI
from dotmac_middleware import MiddlewareStack, SecurityConfig

app = FastAPI()

# Apply unified middleware stack
middleware_stack = MiddlewareStack(
    security=SecurityConfig(
        csrf_enabled=True,
        rate_limiting=True,
        tenant_isolation=True
    )
)
middleware_stack.apply(app)
```

## Key Features

### 🔒 Security Middleware

- **CSRF Protection** - Token-based CSRF with configurable exclusions
- **Rate Limiting** - Sliding window rate limiting with IP-based blocking
- **Security Headers** - Comprehensive security headers (CSP, HSTS, XSS protection)
- **Input Validation** - SQL injection and XSS detection with sanitization

### 🏢 Tenant Isolation

- **Multi-Tenant Context** - Extract tenant ID from headers, subdomains, or paths
- **Database Isolation** - Row Level Security (RLS) with tenant context switching
- **Access Control** - Tenant-scoped resource access validation

### 📊 Request Processing

- **Structured Logging** - Request/response logging with correlation IDs
- **Metrics Collection** - Prometheus metrics for monitoring and alerting
- **Performance Monitoring** - Slow request detection and performance stats
- **Distributed Tracing** - OpenTelemetry-compatible tracing support

### 🔐 Authentication & Authorization

- **JWT Middleware** - Token validation with caching and proper error handling
- **Session Management** - Cookie-based session authentication
- **RBAC** - Role-based access control with permission hierarchies
- **Tenant Security** - Tenant-aware authorization policies

### 🔌 Plugin System

- **Extensible Architecture** - Plugin-based middleware extensions
- **Phase-Based Execution** - Middleware execution phases with dependency management
- **Configuration Management** - Schema-based plugin configuration
- **Hot Reloading** - Dynamic plugin loading and reloading

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                 MiddlewareStack                             │
├─────────────────────────────────────────────────────────────┤
│  Security Middleware                                        │
│  ├─ SecurityHeadersMiddleware                               │
│  ├─ CSRFMiddleware                                          │
│  ├─ RateLimitingMiddleware                                  │
│  └─ InputValidationMiddleware                               │
├─────────────────────────────────────────────────────────────┤
│  Authentication Middleware                                  │
│  ├─ JWTMiddleware                                           │
│  ├─ SessionMiddleware                                       │
│  └─ AuthorizationMiddleware (RBAC)                          │
├─────────────────────────────────────────────────────────────┤
│  Tenant Middleware                                          │
│  ├─ TenantContextMiddleware                                 │
│  └─ DatabaseIsolationMiddleware                             │
├─────────────────────────────────────────────────────────────┤
│  Processing Middleware                                      │
│  ├─ RequestLoggingMiddleware                                │
│  ├─ MetricsMiddleware                                       │
│  ├─ TracingMiddleware                                       │
│  └─ PerformanceMiddleware                                   │
├─────────────────────────────────────────────────────────────┤
│  Plugin System                                              │
│  ├─ PluginManager                                           │
│  ├─ PluginRegistry                                          │
│  └─ Custom Plugins                                          │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Production Configuration

```python
from dotmac_middleware import create_production_stack

app = FastAPI()
middleware_stack = create_production_stack()
middleware_stack.apply(app)
```

### Development Configuration

```python
from dotmac_middleware import create_development_stack

app = FastAPI()
middleware_stack = create_development_stack()
middleware_stack.apply(app)
```

### Custom Configuration

```python
from dotmac_middleware import MiddlewareStack, MiddlewareConfig

config = MiddlewareConfig(
    # Security settings
    security_enabled=True,
    csrf_enabled=True,
    rate_limiting_enabled=True,
    security_headers_enabled=True,
    input_validation_enabled=True,

    # Authentication settings
    auth_enabled=True,
    jwt_enabled=True,
    session_enabled=False,

    # Tenant settings
    tenant_isolation_enabled=True,
    database_isolation_enabled=True,

    # Processing settings
    logging_enabled=True,
    metrics_enabled=True,
    tracing_enabled=True,
    performance_monitoring_enabled=True,

    # Environment-specific overrides
    environment="production",
    debug=False
)

middleware_stack = MiddlewareStack(config)
middleware_stack.apply(app)
```

## Middleware Components

### Security Middleware

#### CSRF Protection

```python
from dotmac_middleware import CSRFMiddleware, SecurityConfig

config = SecurityConfig(
    csrf_secret_key="your-secret-key",
    csrf_token_lifetime=3600,
    csrf_excluded_paths=["/api/public", "/health"]
)

app.add_middleware(CSRFMiddleware, config=config)
```

#### Rate Limiting

```python
from dotmac_middleware import RateLimitingMiddleware, SecurityConfig

config = SecurityConfig(
    rate_limit_requests_per_minute=100,
    rate_limit_burst_size=200,
    rate_limit_excluded_paths=["/health", "/metrics"]
)

app.add_middleware(RateLimitingMiddleware, config=config)
```

### Tenant Isolation

#### Multi-Tenant Context

```python
from dotmac_middleware import TenantMiddleware, TenantConfig

config = TenantConfig(
    tenant_header_name="X-Tenant-ID",
    tenant_subdomain_enabled=True,
    tenant_validation_strict=True,
    database_isolation_enabled=True
)

app.add_middleware(TenantMiddleware, config=config)
```

#### FastAPI Dependencies

```python
from dotmac_middleware import get_current_tenant_id, require_tenant_context

@app.get("/api/data")
def get_data(tenant_id: str = Depends(get_current_tenant_id)):
    return {"tenant_id": tenant_id, "data": "..."}

@app.post("/api/resource")
def create_resource(
    data: dict,
    context: dict = Depends(require_tenant_context)
):
    tenant_id = context["tenant_id"]
    # Create resource in tenant context
```

### Authentication

#### JWT Authentication

```python
from dotmac_middleware import JWTMiddleware, AuthConfig

config = AuthConfig(
    jwt_secret_key="your-jwt-secret",
    jwt_algorithm="HS256",
    jwt_expiration_hours=24,
    require_authentication=True,
    allow_anonymous_paths=["/auth/login", "/health"]
)

app.add_middleware(JWTMiddleware, config=config)
```

#### RBAC Dependencies

```python
from dotmac_middleware import require_role, require_permission

@app.get("/admin/users")
def get_users(user: dict = Depends(require_role("admin"))):
    # Only admins can access this
    return {"users": [...]}

@app.delete("/api/resource/{id}")
def delete_resource(
    id: int,
    user: dict = Depends(require_permission("delete"))
):
    # Only users with delete permission can access
    return {"deleted": id}
```

### Request Processing

#### Metrics Collection

```python
from dotmac_middleware import MetricsMiddleware, ProcessingConfig

config = ProcessingConfig(
    collect_metrics=True,
    metrics_prefix="myapp",
    track_response_sizes=True
)

app.add_middleware(MetricsMiddleware, config=config)
```

#### Performance Monitoring

```python
from dotmac_middleware import PerformanceMiddleware, ProcessingConfig

config = ProcessingConfig(
    performance_monitoring=True,
    slow_request_threshold=2.0,  # 2 seconds
    alert_on_slow_requests=True
)

app.add_middleware(PerformanceMiddleware, config=config)

# Get performance stats
middleware = PerformanceMiddleware(None, config)
stats = middleware.get_performance_stats()
slow_requests = middleware.get_slow_requests()
```

## Plugin Development

### Creating Custom Plugins

```python
from dotmac_middleware import MiddlewarePlugin, PluginMetadata, MiddlewarePhase

class MyCustomPlugin(MiddlewarePlugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_custom_plugin",
            version="1.0.0",
            description="My custom middleware plugin",
            author="Me",
            phase=MiddlewarePhase.PROCESSING,
            priority=100,
            config_schema={
                "required": ["api_key"],
                "properties": {
                    "api_key": {"type": "string"}
                }
            }
        )

    async def process_request(self, request: Request, call_next: Callable) -> Response:
        # Custom processing logic
        api_key = self.config.get("api_key")

        # Validate API key from request
        if request.headers.get("X-API-Key") != api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )

        response = await call_next(request)
        response.headers["X-Processed-By"] = "MyCustomPlugin"

        return response
```

### Plugin Configuration

```python
from dotmac_middleware import PluginManager

plugin_config = {
    "my_custom_plugin": {
        "api_key": "secret-api-key",
        "timeout": 30
    }
}

plugin_manager = PluginManager(plugin_config)
plugin_manager.add_plugin_directory("./plugins")
plugin_manager.load_all_plugins()

# Get middleware stack with plugins
middlewares = plugin_manager.get_middleware_stack()
for middleware in reversed(middlewares):
    app.add_middleware(type(middleware))
```

## Migration Guide

### From ISP Framework Middleware

**Before (ISP Framework):**

```python
from dotmac_isp.core.middleware import RequestLoggingMiddleware
from dotmac_isp.core.security_middleware import EnhancedSecurityHeadersMiddleware
from dotmac_isp.core.csrf_middleware import CSRFProtectionMiddleware

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(EnhancedSecurityHeadersMiddleware)
app.add_middleware(CSRFProtectionMiddleware)
```

**After (Unified Suite):**

```python
from dotmac_middleware import create_production_stack

middleware_stack = create_production_stack()
middleware_stack.apply(app)
```

### From Management Platform Middleware

**Before (Management Platform):**

```python
from dotmac_management.core.middleware import LoggingMiddleware
from dotmac_management.core.csrf_middleware import CSRFMiddleware
from dotmac_management.core.tenant_security import TenantSecurityMiddleware

app.add_middleware(LoggingMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(TenantSecurityMiddleware)
```

**After (Unified Suite):**

```python
from dotmac_middleware import MiddlewareStack, MiddlewareConfig

config = MiddlewareConfig(
    logging_enabled=True,
    csrf_enabled=True,
    tenant_isolation_enabled=True
)
middleware_stack = MiddlewareStack(config)
middleware_stack.apply(app)
```

## Environment Variables

```bash
# Security Configuration
DOTMAC_CSRF_SECRET_KEY=your-csrf-secret-key
DOTMAC_JWT_SECRET_KEY=your-jwt-secret-key
DOTMAC_RATE_LIMIT_REQUESTS_PER_MINUTE=100

# Tenant Configuration
DOTMAC_TENANT_HEADER_NAME=X-Tenant-ID
DOTMAC_TENANT_VALIDATION_STRICT=true
DOTMAC_DATABASE_ISOLATION_ENABLED=true

# Processing Configuration
DOTMAC_METRICS_PREFIX=myapp
DOTMAC_SLOW_REQUEST_THRESHOLD=2.0
DOTMAC_TRACING_ENABLED=true
DOTMAC_TRACE_SAMPLING_RATE=0.1

# Plugin Configuration
DOTMAC_PLUGIN_DIRECTORIES=./plugins,./custom_plugins
```

## Integration Examples

### With Database Dependencies

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dotmac_middleware import get_tenant_database_session

@app.get("/api/users")
async def get_users(
    session: AsyncSession = Depends(get_tenant_database_session)
):
    # Session automatically has tenant context set
    # RLS policies will automatically filter results
    result = await session.execute("SELECT * FROM users")
    return result.fetchall()
```

### With Caching

```python
import redis
from dotmac_middleware import get_current_tenant_id

redis_client = redis.Redis()

@app.get("/api/data")
def get_cached_data(tenant_id: str = Depends(get_current_tenant_id)):
    cache_key = f"data:{tenant_id}"

    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    # Fetch and cache data
    data = fetch_data_for_tenant(tenant_id)
    redis_client.setex(cache_key, 300, json.dumps(data))
    return data
```

### With Background Tasks

```python
from fastapi import BackgroundTasks
from dotmac_middleware import get_tenant_context

def process_in_background(tenant_context: dict, data: dict):
    # Background task has access to tenant context
    tenant_id = tenant_context["tenant_id"]
    user_id = tenant_context["user_id"]

    # Process data in tenant context
    process_tenant_data(tenant_id, user_id, data)

@app.post("/api/process")
async def start_processing(
    data: dict,
    background_tasks: BackgroundTasks,
    context: dict = Depends(get_tenant_context)
):
    background_tasks.add_task(process_in_background, context, data)
    return {"status": "processing"}
```

## Monitoring and Metrics

The middleware suite automatically provides Prometheus metrics:

```
# Request metrics
dotmac_requests_total{method="GET", path="/api/users", status_code="200"} 150
dotmac_request_duration_seconds{method="GET", path="/api/users", status_code="200"} 0.45

# Active requests
dotmac_active_requests 5

# Response size metrics
dotmac_response_size_bytes{method="GET", path="/api/users", status_code="200"} 2048

# Security metrics (via plugins)
dotmac_csrf_tokens_generated_total 100
dotmac_rate_limit_blocked_total{client_ip="192.168.1.100"} 5
```

## Testing

```python
import pytest
from fastapi.testclient import TestClient
from dotmac_middleware import create_minimal_stack

@pytest.fixture
def app():
    from fastapi import FastAPI

    app = FastAPI()

    # Use minimal stack for testing
    middleware_stack = create_minimal_stack()
    middleware_stack.apply(app)

    return app

@pytest.fixture
def client(app):
    return TestClient(app)

def test_authenticated_request(client):
    # Test with JWT token
    headers = {"Authorization": "Bearer valid-jwt-token"}
    response = client.get("/api/protected", headers=headers)
    assert response.status_code == 200

def test_tenant_isolation(client):
    # Test tenant context
    headers = {"X-Tenant-ID": "tenant-123"}
    response = client.get("/api/data", headers=headers)
    assert response.status_code == 200
```

## Performance Considerations

- **Token Caching**: JWT tokens are cached to reduce validation overhead
- **Metrics Sampling**: Tracing uses configurable sampling rates
- **Path Normalization**: Metrics use normalized paths to prevent high cardinality
- **Memory Management**: Plugin registry manages lifecycle to prevent leaks
- **Database Connections**: Tenant isolation reuses existing database sessions

## Security Considerations

- **Secret Management**: All secrets should be stored securely (environment variables, vault)
- **HTTPS Enforcement**: Production configurations enforce HTTPS
- **Token Validation**: JWT validation includes issuer, audience, and expiration checks
- **Input Sanitization**: All user input is validated and sanitized
- **Rate Limiting**: Protects against DoS attacks with configurable thresholds
- **CSRF Protection**: Prevents cross-site request forgery with token validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For questions and support:

- GitHub Issues: [dotmac-framework/issues](https://github.com/dotmac/framework/issues)
- Documentation: [docs.dotmac.com](https://docs.dotmac.com)
- Email: <support@dotmac.com>
