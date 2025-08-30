# DotMac SDK Core - HTTP Client Framework

A comprehensive HTTP client framework for DotMac services providing standardized external API communication with built-in resilience, observability, and tenant context management.

## Features

### Core HTTP Client

- **Async & Sync Support**: Both async and sync interfaces for flexibility
- **Request/Response Standardization**: Consistent HTTP operations across services
- **Connection Management**: Connection pooling and keep-alive optimization
- **Context Management**: Automatic tenant and user context propagation

### Resilience Patterns

- **Circuit Breaker**: Prevents cascade failures with configurable thresholds
- **Retry Strategies**: Multiple backoff algorithms (exponential, linear, fixed)
- **Rate Limiting**: Client-side rate limiting to respect service limits
- **Timeout Handling**: Configurable timeouts with proper error handling

### Authentication

- **Bearer Token**: Standard bearer token authentication
- **API Key**: Custom API key authentication
- **JWT**: JWT token with expiry validation
- **Extensible**: Custom authentication providers

### Observability

- **OpenTelemetry Integration**: Distributed tracing and metrics
- **Request Logging**: Comprehensive request/response logging
- **Metrics Collection**: HTTP performance metrics
- **Error Tracking**: Structured error reporting

### Error Handling

- **Structured Exceptions**: Domain-specific error types
- **Response Context**: Errors include full response context
- **Status Code Mapping**: Automatic exception mapping by status code
- **Retry Logic**: Smart retry based on error types

## Installation

The package is integrated into the root DotMac Framework Poetry configuration:

```bash
# Install full DotMac framework (includes SDK core)
poetry install
```

## Quick Start

```python
import asyncio
from dotmac_sdk_core import (
    DotMacHTTPClient,
    HTTPClientConfig,
    BearerTokenAuth,
    ExponentialBackoffStrategy
)

# Configure client
config = HTTPClientConfig(
    base_url="https://api.example.com",
    timeout=30.0,
    auth_provider=BearerTokenAuth("your-token"),
    retry_strategy=ExponentialBackoffStrategy(max_attempts=3),
    enable_circuit_breaker=True,
    enable_telemetry=True
)

# Create client
async def main():
    async with DotMacHTTPClient(config) as client:
        # Make requests with automatic retry and circuit breaker
        response = await client.get(
            "/users",
            params={"page": 1, "limit": 10},
            tenant_id="tenant-123",
            user_id="user-456"
        )

        print(f"Status: {response.status_code}")
        print(f"Data: {response.json_data}")

asyncio.run(main())
```

## Configuration

### HTTPClientConfig Options

```python
config = HTTPClientConfig(
    # Connection settings
    base_url="https://api.example.com",
    timeout=30.0,
    follow_redirects=True,
    verify_ssl=True,
    max_connections=100,

    # Retry configuration
    retry_strategy=ExponentialBackoffStrategy(),
    max_retries=3,
    retry_on_status=[429, 502, 503, 504],

    # Circuit breaker
    enable_circuit_breaker=True,
    circuit_breaker_failure_threshold=5,
    circuit_breaker_recovery_timeout=60.0,

    # Authentication
    auth_provider=BearerTokenAuth("token"),

    # Rate limiting
    enable_rate_limiting=True,
    rate_limit_requests_per_second=10.0,

    # Observability
    enable_telemetry=True,
    service_name="my-service"
)
```

### Retry Strategies

```python
from dotmac_sdk_core import (
    ExponentialBackoffStrategy,
    FixedDelayStrategy,
    LinearBackoffStrategy
)

# Exponential backoff (default)
exponential = ExponentialBackoffStrategy(
    max_attempts=5,
    base_delay=1.0,
    multiplier=2.0,
    max_delay=60.0,
    jitter=True
)

# Fixed delay
fixed = FixedDelayStrategy(
    max_attempts=3,
    delay=2.0
)

# Linear backoff
linear = LinearBackoffStrategy(
    max_attempts=4,
    base_delay=1.0,
    increment=1.0
)
```

### Authentication Providers

```python
from dotmac_sdk_core import BearerTokenAuth, APIKeyAuth, JWTAuth

# Bearer token
auth = BearerTokenAuth("your-bearer-token")

# API key
auth = APIKeyAuth("your-api-key", header_name="X-API-Key")

# JWT with validation
auth = JWTAuth("your-jwt-token")
if not auth.is_valid():
    print("Token expired or invalid")
```

## Advanced Usage

### Custom Middleware

```python
from dotmac_sdk_core.middleware.base import RequestMiddleware

class CustomHeaderMiddleware(RequestMiddleware):
    async def process_request(self, request_data):
        request_data['headers']['X-Custom'] = 'value'
        return request_data

config = HTTPClientConfig(
    base_url="https://api.example.com",
    middleware=[CustomHeaderMiddleware()]
)
```

### Circuit Breaker Monitoring

```python
client = DotMacHTTPClient(config)

# Check circuit breaker status
stats = client.get_circuit_breaker_stats()
print(f"Circuit state: {stats['state']}")
print(f"Failure rate: {stats['failure_rate']:.2%}")
print(f"Total requests: {stats['total_requests']}")
```

### Pagination Support

```python
# Automatic pagination
async for user in client.paginate("/users", page_size=50):
    print(f"User: {user['name']}")

# Manual pagination
response = await client.get("/users", params={
    "page": 1,
    "per_page": 25
})
```

## Error Handling

```python
from dotmac_sdk_core.exceptions import (
    HTTPClientError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    CircuitBreakerError
)

try:
    response = await client.get("/protected")
except AuthenticationError as e:
    print(f"Auth failed: {e.message}")
    print(f"Status: {e.status_code}")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}s")
except CircuitBreakerError as e:
    print(f"Circuit breaker {e.state}: {e.message}")
except HTTPClientError as e:
    print(f"HTTP error: {e.message}")
    if e.response:
        print(f"Response: {e.response.text}")
```

## Testing

Run the test suite:

```bash
# Run SDK core tests
pytest src/dotmac_sdk_core/tests/

# Run with coverage
pytest src/dotmac_sdk_core/tests/ --cov=src/dotmac_sdk_core --cov-report=html

# Run integration tests
pytest src/dotmac_sdk_core/tests/test_integration.py -v
```

## Architecture

### Package Structure

```
src/dotmac_sdk_core/
├── __init__.py              # Main package exports
├── client/                  # HTTP client implementation
│   ├── http_client.py       # Core client and config
│   └── __init__.py
├── resilience/              # Resilience patterns
│   ├── circuit_breaker.py   # Circuit breaker implementation
│   ├── retry_strategies.py  # Retry strategy implementations
│   └── __init__.py
├── auth/                    # Authentication providers
│   ├── providers.py         # Auth provider implementations
│   └── __init__.py
├── middleware/              # Request/response middleware
│   ├── base.py             # Base middleware classes
│   ├── tenant_context.py   # Tenant context handling
│   ├── rate_limiting.py    # Client-side rate limiting
│   └── __init__.py
├── observability/          # Telemetry and tracing
│   ├── telemetry.py        # Metrics collection
│   ├── tracing.py          # Distributed tracing
│   └── __init__.py
├── utils/                  # Utilities
│   ├── response_parser.py  # Response parsing
│   ├── request_builder.py  # Request construction
│   ├── header_utils.py     # Header utilities
│   └── __init__.py
├── exceptions.py           # Exception hierarchy
└── tests/                  # Test suite
    ├── test_http_client.py
    ├── test_circuit_breaker.py
    ├── test_retry_strategies.py
    └── test_integration.py
```

### Key Design Principles

1. **Standardization**: Consistent HTTP operations across all DotMac services
2. **Resilience**: Built-in patterns to handle service failures gracefully
3. **Observability**: Comprehensive monitoring and tracing capabilities
4. **Extensibility**: Plugin architecture for custom auth, middleware, and strategies
5. **Performance**: Connection pooling, async support, and efficient retry logic

## Integration with DotMac Framework

The SDK Core is designed for seamless integration with other DotMac components:

- **Tenant Context**: Automatic tenant ID propagation in multi-tenant systems
- **Authentication**: Integration with DotMac auth services
- **Observability**: Compatible with DotMac monitoring infrastructure
- **Configuration**: Uses DotMac configuration patterns and conventions

## Contributing

This package follows DotMac framework development standards:

1. Add comprehensive tests for new features
2. Follow existing code patterns and conventions
3. Update documentation for public APIs
4. Ensure observability for all operations

## License

MIT License - see the main DotMac Framework license for details.
