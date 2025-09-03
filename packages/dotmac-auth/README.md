# dotmac.auth

Standalone authentication package for the DotMac platform with JWT management, edge validation, and service-to-service tokens.

## Features

- **JWT Service**: Complete JWT token management with RS256/HS256 support
- **Edge Validation**: Request-level JWT validation with sensitivity patterns
- **Service Tokens**: Service-to-service authentication with operation-based permissions
- **FastAPI Integration**: Ready-to-use dependencies and middleware
- **OpenBao Integration**: Secure secrets management
- **Comprehensive Testing**: 76% test coverage with 133 test cases

## Quick Start

### Installation

```bash
pip install dotmac-auth
```

For development with secrets support:
```bash
pip install dotmac-auth[secrets]
```

### Basic Usage

```python
from dotmac.auth import JWTService, get_current_user
from fastapi import FastAPI, Depends

# Create JWT service
jwt_service = JWTService(
    algorithm="HS256",
    secret="your-secret-key",
    issuer="your-app"
)

# Issue tokens
access_token = jwt_service.issue_access_token(
    sub="user123",
    scopes=["read", "write"],
    tenant_id="tenant1"
)

# FastAPI integration
app = FastAPI()

@app.get("/protected")
async def protected_route(user: UserClaims = Depends(get_current_user)):
    return {"user_id": user.user_id, "scopes": user.scopes}
```

### Edge Validation

```python
from dotmac.auth import create_edge_validator, EdgeAuthMiddleware

# Create edge validator with sensitivity patterns
validator = create_edge_validator(
    jwt_service=jwt_service,
    environment="production",
    patterns={
        ("GET", "/health"): "public",
        ("POST", "/admin/*"): "admin",
        ("GET", "/api/users/*"): "authenticated"
    }
)

# Add middleware
app.add_middleware(EdgeAuthMiddleware, validator=validator)
```

### Service-to-Service Authentication

```python
from dotmac.auth import ServiceTokenManager, ServiceIdentity

# Create service token manager
service_manager = ServiceTokenManager(jwt_service=jwt_service)

# Register a service
service_manager.register_service(
    ServiceIdentity(
        service_id="api-gateway",
        name="API Gateway Service",
        allowed_targets=["user-service", "billing-service"],
        operations=["users:read", "billing:*"]
    )
)

# Issue service token
service_token = service_manager.issue_service_token(
    service_id="api-gateway",
    target_service="user-service",
    operations=["users:read"]
)
```

## Migration from dotmac_shared.auth

If you're migrating from the old `dotmac_shared.auth` module:

```python
# Old import
from dotmac_shared.auth import JWTService

# New import
from dotmac.auth import JWTService
```

The migration shim provides backward compatibility with deprecation warnings.

## Configuration

### Environment Variables

- `JWT_ALGORITHM`: Token algorithm (default: "RS256")
- `JWT_SECRET`: Secret for HS256 (required for HS256)
- `JWT_PRIVATE_KEY`: Private key for RS256 (required for RS256)
- `JWT_PUBLIC_KEY`: Public key for RS256 (required for RS256)
- `OPENBAO_URL`: OpenBao server URL
- `OPENBAO_TOKEN`: OpenBao access token

### Configuration Object

```python
from dotmac.auth import create_jwt_service_from_config

config = {
    "algorithm": "HS256",
    "secret": "your-secret",
    "issuer": "your-app",
    "access_token_expire_minutes": 15,
    "refresh_token_expire_days": 7
}

jwt_service = create_jwt_service_from_config(config)
```

## Security Features

- **Algorithm Support**: RS256 (recommended) and HS256
- **Token Validation**: Comprehensive JWT validation with expiration, audience, and issuer checks
- **Route Sensitivity**: Configurable security levels (public, authenticated, sensitive, admin)
- **HTTPS Enforcement**: Production environment HTTPS requirement
- **Clock Skew Tolerance**: Configurable leeway for token validation
- **Service Isolation**: Operation-based service permissions

## Development

### Setup

```bash
git clone https://github.com/dotmac/dotmac-auth
cd packages/dotmac-auth
pip install -e .[dev]
```

### Testing

```bash
pytest tests/ -v
```

### Coverage Report

```bash
pytest tests/ --cov=dotmac.auth --cov-report=html
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/dotmac/dotmac-auth/issues
- Documentation: https://docs.dotmac.com/auth
- Migration Guide: https://docs.dotmac.com/auth/migration