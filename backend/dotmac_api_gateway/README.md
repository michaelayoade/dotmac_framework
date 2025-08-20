# DotMac API Gateway

**Centralized API Gateway for DotMac ISP Framework**

The DotMac API Gateway provides enterprise-grade API management, authentication, rate limiting, and external API exposure for Internet Service Provider operations. It acts as the single entry point for all external API access to the DotMac platform.

## Features

### 🚪 **Gateway Management**
- **API Gateway SDK** - Centralized gateway configuration and management
- **Route Management** - Dynamic routing with path-based and host-based routing
- **Load Balancing** - Multiple algorithms (round-robin, least-connections, weighted)
- **Health Checks** - Upstream service health monitoring and circuit breakers
- **Service Discovery** - Automatic service registration and discovery

### 🔐 **Authentication & Authorization**
- **Authentication Proxy SDK** - Multi-provider authentication (JWT, OAuth2, API Keys)
- **Authorization Engine** - Role-based and attribute-based access control
- **Token Management** - JWT validation, refresh, and revocation
- **API Key Management** - API key generation, rotation, and validation
- **Multi-Tenant Security** - Tenant-based access isolation

### ⚡ **Rate Limiting & Throttling**
- **Rate Limiting SDK** - Multiple algorithms (token bucket, sliding window, fixed window)
- **Throttling Engine** - Request throttling with backpressure handling
- **Quota Management** - Daily, monthly, and custom quota enforcement
- **Burst Control** - Burst allowances and spike protection
- **Per-User/Per-API Limits** - Granular rate limiting policies

### 📊 **API Management**
- **API Versioning SDK** - Semantic versioning with backward compatibility
- **Request/Response Transformation** - Header manipulation, body transformation
- **Content Negotiation** - Format conversion (JSON, XML, protobuf)
- **CORS Management** - Cross-origin resource sharing configuration
- **Caching Layer** - Response caching with TTL and invalidation

### 📈 **Monitoring & Analytics**
- **Gateway Analytics SDK** - Request metrics, performance monitoring
- **API Usage Tracking** - Per-API, per-user usage analytics
- **Error Tracking** - Error rates, failure analysis
- **Performance Metrics** - Latency, throughput, and availability metrics
- **Real-time Monitoring** - Live traffic monitoring and alerting

### 📚 **Documentation & Portal**
- **API Documentation SDK** - Automatic OpenAPI/Swagger documentation generation
- **Developer Portal** - Self-service API documentation and testing
- **API Explorer** - Interactive API testing interface
- **Code Examples** - Auto-generated code samples in multiple languages

## Installation

```bash
pip install dotmac-api-gateway
```

For development:
```bash
pip install dotmac-api-gateway[dev]
```

## Quick Start

```python
import asyncio
from dotmac_api_gateway import (
    GatewaySDK,
    AuthenticationProxySDK,
    RateLimitingSDK,
    APIVersioningSDK,
    GatewayAnalyticsSDK
)

async def main():
    tenant_id = "isp-tenant-1"
    
    # Initialize SDKs
    gateway_sdk = GatewaySDK(tenant_id)
    auth_sdk = AuthenticationProxySDK(tenant_id)
    rate_limit_sdk = RateLimitingSDK(tenant_id)
    versioning_sdk = APIVersioningSDK(tenant_id)
    analytics_sdk = GatewayAnalyticsSDK(tenant_id)
    
    # Create API gateway
    gateway = await gateway_sdk.create_gateway(
        name="Customer API Gateway",
        description="Public APIs for customer portal",
        domains=["api.isp.com"]
    )
    
    # Add route to customer service
    route = await gateway_sdk.create_route(
        gateway_id=gateway["gateway_id"],
        path="/v1/customers/*",
        upstream_service="dotmac-identity",
        upstream_url="http://identity-service:8000",
        methods=["GET", "POST", "PUT", "DELETE"]
    )
    
    # Configure authentication
    auth_policy = await auth_sdk.create_auth_policy(
        name="JWT Authentication",
        auth_type="jwt",
        jwt_secret_key="your-secret-key",
        required_scopes=["customer:read", "customer:write"]
    )
    
    # Apply authentication to route
    await gateway_sdk.apply_auth_policy(
        route_id=route["route_id"],
        auth_policy_id=auth_policy["policy_id"]
    )
    
    # Configure rate limiting
    rate_limit_policy = await rate_limit_sdk.create_rate_limit_policy(
        name="Customer API Limits",
        algorithm="sliding_window",
        requests_per_minute=100,
        burst_size=20
    )
    
    # Apply rate limiting to route
    await gateway_sdk.apply_rate_limit_policy(
        route_id=route["route_id"],
        rate_limit_policy_id=rate_limit_policy["policy_id"]
    )
    
    # Create API version
    api_version = await versioning_sdk.create_api_version(
        api_name="Customer API",
        version="v1",
        gateway_id=gateway["gateway_id"],
        deprecation_date=None
    )
    
    # Start monitoring
    await analytics_sdk.start_monitoring(
        gateway_id=gateway["gateway_id"],
        metrics=["requests", "latency", "errors", "rate_limits"]
    )
    
    print(f"Gateway: {gateway['gateway_id']}")
    print(f"Route: {route['route_id']}")
    print(f"API Version: {api_version['version_id']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

Configure via environment variables:

```bash
# Gateway
DOTMAC_GATEWAY_HOST=0.0.0.0
DOTMAC_GATEWAY_PORT=8080
DOTMAC_GATEWAY_WORKERS=4
DOTMAC_GATEWAY_ENABLE_DOCS=true

# Authentication
DOTMAC_AUTH_JWT_SECRET_KEY=your-jwt-secret
DOTMAC_AUTH_JWT_ALGORITHM=HS256
DOTMAC_AUTH_JWT_EXPIRATION_HOURS=24
DOTMAC_AUTH_API_KEY_HEADER=X-API-Key

# Rate Limiting
DOTMAC_RATE_LIMIT_REDIS_URL=redis://localhost:6379
DOTMAC_RATE_LIMIT_DEFAULT_RPM=1000
DOTMAC_RATE_LIMIT_BURST_SIZE=100

# Caching
DOTMAC_CACHE_REDIS_URL=redis://localhost:6379
DOTMAC_CACHE_DEFAULT_TTL=300
DOTMAC_CACHE_MAX_SIZE=1000

# Monitoring
DOTMAC_MONITORING_ENABLED=true
DOTMAC_MONITORING_PROMETHEUS_PORT=9090
DOTMAC_MONITORING_METRICS_INTERVAL=30

# Upstream Services
DOTMAC_UPSTREAM_ANALYTICS=http://analytics-service:8000
DOTMAC_UPSTREAM_IDENTITY=http://identity-service:8000
DOTMAC_UPSTREAM_NETWORKING=http://networking-service:8000
DOTMAC_UPSTREAM_SERVICES=http://services-service:8000
DOTMAC_UPSTREAM_BILLING=http://billing-service:8000
```

## Gateway Deployment Patterns

### Single Gateway
```python
# Single gateway for all APIs
gateway = await gateway_sdk.create_gateway(
    name="Unified API Gateway",
    domains=["api.isp.com"],
    load_balancer="round_robin"
)
```

### Service-Specific Gateways
```python
# Separate gateways per service domain
customer_gateway = await gateway_sdk.create_gateway(
    name="Customer Gateway",
    domains=["customer-api.isp.com"],
    upstream_services=["identity", "services", "billing"]
)

admin_gateway = await gateway_sdk.create_gateway(
    name="Admin Gateway", 
    domains=["admin-api.isp.com"],
    upstream_services=["platform", "analytics", "networking"]
)
```

## Authentication Providers

### JWT Authentication
```python
jwt_auth = await auth_sdk.create_jwt_auth_provider(
    name="Platform JWT",
    secret_key="your-secret-key",
    algorithm="HS256",
    issuer="dotmac-platform",
    audience=["customer-portal", "admin-portal"]
)
```

### OAuth2 Authentication
```python
oauth2_auth = await auth_sdk.create_oauth2_auth_provider(
    name="Google OAuth2",
    client_id="your-client-id",
    client_secret="your-client-secret",
    authorization_url="https://accounts.google.com/o/oauth2/auth",
    token_url="https://oauth2.googleapis.com/token"
)
```

### API Key Authentication
```python
api_key_auth = await auth_sdk.create_api_key_auth_provider(
    name="Partner API Keys",
    header_name="X-API-Key",
    key_format="ak_[a-zA-Z0-9]{32}",
    allow_query_param=False
)
```

## Rate Limiting Algorithms

### Token Bucket
```python
token_bucket = await rate_limit_sdk.create_rate_limit_policy(
    name="Token Bucket",
    algorithm="token_bucket",
    tokens_per_second=10,
    bucket_size=100,
    refill_rate=1
)
```

### Sliding Window
```python
sliding_window = await rate_limit_sdk.create_rate_limit_policy(
    name="Sliding Window",
    algorithm="sliding_window",
    requests_per_minute=1000,
    window_size_seconds=60
)
```

### Fixed Window
```python
fixed_window = await rate_limit_sdk.create_rate_limit_policy(
    name="Fixed Window",
    algorithm="fixed_window",
    requests_per_hour=10000,
    window_reset_time="00:00"
)
```

## Load Balancing Strategies

### Round Robin
```python
await gateway_sdk.configure_load_balancer(
    gateway_id=gateway_id,
    algorithm="round_robin",
    health_check_path="/health",
    health_check_interval=30
)
```

### Least Connections
```python
await gateway_sdk.configure_load_balancer(
    gateway_id=gateway_id,
    algorithm="least_connections",
    connection_timeout=5000,
    max_connections_per_upstream=100
)
```

### Weighted Round Robin
```python
await gateway_sdk.configure_load_balancer(
    gateway_id=gateway_id,
    algorithm="weighted_round_robin",
    upstream_weights={
        "analytics-1": 70,
        "analytics-2": 30
    }
)
```

## API Versioning Strategies

### Path-Based Versioning
```python
v1_route = await versioning_sdk.create_versioned_route(
    api_name="Customer API",
    version="v1",
    path="/v1/customers",
    upstream_service="identity-v1"
)

v2_route = await versioning_sdk.create_versioned_route(
    api_name="Customer API", 
    version="v2",
    path="/v2/customers",
    upstream_service="identity-v2"
)
```

### Header-Based Versioning
```python
await versioning_sdk.configure_header_versioning(
    api_name="Customer API",
    version_header="API-Version",
    default_version="v1",
    supported_versions=["v1", "v2"]
)
```

### Content Negotiation Versioning
```python
await versioning_sdk.configure_content_negotiation_versioning(
    api_name="Customer API",
    media_types={
        "application/vnd.dotmac.v1+json": "v1",
        "application/vnd.dotmac.v2+json": "v2"
    }
)
```

## Monitoring & Analytics

### Request Metrics
```python
# Get request metrics
metrics = await analytics_sdk.get_request_metrics(
    gateway_id=gateway_id,
    time_range="24h",
    group_by=["route", "status_code"]
)

print(f"Total requests: {metrics['total_requests']}")
print(f"Average latency: {metrics['avg_latency_ms']}ms")
print(f"Error rate: {metrics['error_rate']}%")
```

### Usage Analytics
```python
# Get API usage analytics
usage = await analytics_sdk.get_usage_analytics(
    gateway_id=gateway_id,
    time_range="7d",
    group_by=["api_key", "endpoint"]
)

for api_key, stats in usage.items():
    print(f"API Key: {api_key}")
    print(f"  Requests: {stats['requests']}")
    print(f"  Data transferred: {stats['bytes_transferred']}")
```

### Real-time Monitoring
```python
# Start real-time monitoring
async def on_request(event):
    print(f"Request: {event['method']} {event['path']}")
    print(f"Latency: {event['latency_ms']}ms")
    
await analytics_sdk.start_real_time_monitoring(
    gateway_id=gateway_id,
    on_request=on_request,
    on_error=lambda event: print(f"Error: {event}")
)
```

## Developer Portal

### Auto-Generated Documentation
```python
# Generate OpenAPI documentation
openapi_spec = await doc_sdk.generate_openapi_spec(
    gateway_id=gateway_id,
    include_examples=True,
    include_schemas=True
)

# Create developer portal
portal = await doc_sdk.create_developer_portal(
    name="Customer API Portal",
    gateway_id=gateway_id,
    openapi_spec=openapi_spec,
    custom_css="/static/portal.css"
)
```

### Interactive API Explorer
```python
# Add API explorer
explorer = await doc_sdk.create_api_explorer(
    portal_id=portal["portal_id"],
    enable_try_it_out=True,
    default_auth_header="X-API-Key"
)
```

## Security Features

### CORS Configuration
```python
await gateway_sdk.configure_cors(
    gateway_id=gateway_id,
    allowed_origins=["https://customer.isp.com"],
    allowed_methods=["GET", "POST", "PUT", "DELETE"],
    allowed_headers=["Content-Type", "Authorization"],
    max_age=86400
)
```

### Request/Response Transformation
```python
# Transform request headers
await gateway_sdk.add_request_transformation(
    route_id=route_id,
    transformation_type="add_header",
    config={
        "header_name": "X-Tenant-ID",
        "header_value": "${tenant_id}"
    }
)

# Transform response body
await gateway_sdk.add_response_transformation(
    route_id=route_id,
    transformation_type="remove_field",
    config={
        "field_path": "user.internal_id"
    }
)
```

## Architecture

The API Gateway follows the DotMac framework patterns:

- **Core**: Configuration management and exceptions
- **SDKs**: Focused SDKs for gateway domains
- **Runtime**: Production-ready configuration
- **Multi-tenant**: Complete tenant isolation
- **Event-driven**: Integration with platform events

## Integration

### Platform Integration
```python
# Integrate with platform authentication
from dotmac_platform import AuthSDK, TenancySDK

platform_auth = AuthSDK(tenant_id)
tenancy = TenancySDK(tenant_id)

# Use platform auth for gateway authentication
gateway_auth = await auth_sdk.create_platform_auth_provider(
    platform_auth_sdk=platform_auth,
    tenancy_sdk=tenancy
)
```

### Event Integration
```python
# Integrate with event system
from dotmac_core_events import EventBusSDK

events = EventBusSDK(tenant_id)

# Publish gateway events
await events.publish("gateway.request.received", {
    "gateway_id": gateway_id,
    "route_id": route_id,
    "request_id": request_id
})
```

## Development

```bash
# Clone repository
git clone https://github.com/dotmac/dotmac-api-gateway.git
cd dotmac-api-gateway

# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Format code
black dotmac_api_gateway/
ruff --fix dotmac_api_gateway/

# Type checking
mypy dotmac_api_gateway/
```

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://docs.dotmac.com/api-gateway
- Issues: https://github.com/dotmac/dotmac-api-gateway/issues
- Email: support@dotmac.com

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

Please ensure all tests pass and code follows the project style guidelines.