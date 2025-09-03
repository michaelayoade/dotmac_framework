# Changelog

All notable changes to the dotmac.auth package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-01

### Added

#### Core Authentication
- **JWTService**: Complete JWT token management with RS256/HS256 support
  - Token issuance with configurable expiration
  - Token verification with audience, issuer, and signature validation
  - Token refresh functionality
  - RSA key pair generation utilities
  - HS256 secret generation helpers
  - Clock skew tolerance (leeway) support

#### FastAPI Integration
- **UserClaims**: Pydantic model for user JWT claims with permission helpers
- **ServiceClaims**: Pydantic model for service-to-service authentication
- **get_current_user**: FastAPI dependency for authenticated routes
- **get_optional_user**: FastAPI dependency for optional authentication
- **get_current_service**: FastAPI dependency for service authentication

#### Authorization Helpers
- **require_scopes**: Dependency for scope-based authorization
- **require_roles**: Dependency for role-based authorization  
- **require_admin**: Dependency for admin-level access
- **require_tenant_access**: Dependency for tenant isolation
- **require_service_operation**: Dependency for service operation permissions

#### Edge Validation
- **EdgeJWTValidator**: Request-level JWT validation with sensitivity patterns
- **EdgeAuthMiddleware**: FastAPI middleware for edge validation
- **SensitivityLevel**: Enum for route security levels (public, authenticated, sensitive, admin)
- **Common sensitivity patterns**: Pre-configured patterns for typical API routes
- Route-specific validation rules
- HTTPS enforcement for production environments
- Tenant validation with configurable resolvers

#### Service-to-Service Authentication
- **ServiceTokenManager**: Complete service token lifecycle management
- **ServiceIdentity**: Service registration and permission model
- **ServiceAuthMiddleware**: FastAPI middleware for service authentication
- Service registry with operation-based permissions
- Wildcard operation support (`service:*`)
- Token revocation and service management

#### Secrets Management
- **SecretsProvider**: Abstract interface for secure secret storage
- **OpenBaoProvider**: OpenBao/Vault integration for production secrets
- JWT service integration with automatic secret retrieval
- Fallback mechanism for development environments

#### Exception System
- Comprehensive exception hierarchy with HTTP status code mapping
- **AuthError**: Base authentication exception
- **TokenError**: Token-specific exceptions (expired, invalid, missing)
- **ValidationError**: Validation-specific exceptions
- **ConfigurationError**: Service configuration exceptions
- **SecretsProviderError**: Secrets management exceptions

#### API Factory
- **create_auth_api**: FastAPI router factory for authentication endpoints
- Token validation endpoints
- Health check integration
- Error handling with proper HTTP status codes

### Testing
- 133 test cases with 76% code coverage
- Comprehensive JWT service testing (HS256 and RS256)
- Edge validation integration tests
- Service token management tests
- FastAPI dependency testing
- Error handling and edge case coverage

### Configuration
- Environment variable support
- Configuration dictionary support
- Development vs production environment handling
- Flexible algorithm selection (RS256/HS256)
- Configurable token expiration times

### Migration Support
- **Migration shim**: Backward compatibility for `dotmac_shared.auth`
- Deprecation warnings for old import paths
- Automatic re-export of new functionality
- Dynamic attribute access for unlisted exports
- Submodule compatibility (`dotmac_shared.auth.current_user`)

### Documentation
- Comprehensive README with examples
- API documentation with type hints
- Migration guide from legacy system
- Security best practices
- Development setup instructions

### Security Features
- RS256 public key cryptography (recommended)
- HS256 symmetric key support
- Token signature validation
- Audience and issuer verification
- Automatic token expiration
- Route sensitivity patterns
- Service operation isolation
- HTTPS enforcement
- Clock skew tolerance

### Performance Optimizations
- Efficient token validation with caching support
- Minimal import overhead
- FastAPI dependency injection optimization
- Lazy loading of optional dependencies

### Development Features
- Type hints throughout codebase
- Pydantic v2 integration
- FastAPI native integration
- Poetry packaging
- Pytest test suite
- Coverage reporting
- Black code formatting
- Ruff linting