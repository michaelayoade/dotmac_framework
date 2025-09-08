# Changelog

All notable changes to the dotmac-core package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-09-06

### Added

#### Core Foundation
- **Exception Hierarchy**: Comprehensive exception system with structured error details
  - Base `DotMacError` with error codes and metadata
  - Domain-specific exceptions (Database, Cache, Tenant, Service, etc.)
  - Production-ready error serialization and logging integration
  
- **Tenant Management**: Multi-tenant support with context isolation
  - `TenantContext` with metadata and feature flags
  - Subdomain and header-based tenant resolution
  - Thread-safe tenant context management with asyncio support
  - Tenant isolation for all framework components

- **Configuration Management**: Type-safe configuration with validation
  - `DatabaseConfig`, `CacheConfig`, `SecurityConfig` classes
  - Environment variable integration with Pydantic
  - Production security validations
  - Redis and logging configuration support

- **Core Types**: Database and framework types
  - Cross-database `GUID` type for SQLAlchemy
  - Production-ready type definitions
  - Full typing support for IDE integration

#### Development Tools
- **Decorators**: Production-ready decorators for common patterns
  - `@standard_exception_handler` for consistent error handling
  - `@retry_on_failure` with exponential backoff
  - `@rate_limit` for API rate limiting
  - `@timeout` for async operation timeouts

- **Cache Services**: High-performance caching infrastructure
  - Multi-backend cache service (Redis + Memory fallback)
  - Tenant-aware caching with isolation
  - `@cached` decorator for function memoization
  - Health checks and metrics collection

- **Logging Integration**: Structured logging with context
  - `get_logger()` helper with structured logging
  - Tenant context integration
  - Production-ready log formatting

#### Database Support
- **Compatibility Layer**: Database abstraction and utilities
  - `DatabaseManager` for connection management
  - Health check functions
  - Database availability detection
  - Graceful degradation when database components unavailable

#### Testing Infrastructure
- **Comprehensive Test Suite**: 211 tests with 37% coverage
  - Unit tests for all core components
  - Integration tests for cache and tenant systems
  - Mock-based testing for external dependencies
  - Async test support with pytest-asyncio

### Documentation
- **Complete README**: Comprehensive usage documentation
- **API Documentation**: Detailed docstrings for all public APIs
- **Migration Guide**: Instructions for migrating from legacy packages
- **Cache Service Documentation**: Detailed cache service documentation
- **Type Stubs**: Full typing support with py.typed marker

### Configuration
- **pyproject.toml**: Modern Python packaging configuration
  - Multiple optional dependencies (fastapi, redis, postgres, cache)
  - Development dependencies for testing and linting
  - Comprehensive tool configurations (pytest, mypy, ruff, black)
  - Python 3.9+ support

### Quality Assurance
- **Code Quality Tools**: Comprehensive linting and formatting
  - Black for code formatting
  - Ruff for linting with modern rules
  - MyPy for static type checking
  - isort for import organization

- **Testing Configuration**: Production-ready testing setup
  - pytest with async support
  - Coverage reporting with 90% requirement
  - Multiple test categories (unit, integration, database, redis)
  - HTML coverage reports

### Architecture
- **DRY Compliance**: Eliminates 500+ DRY violations from framework
  - Single source of truth for exceptions
  - Consolidated configuration patterns
  - Unified tenant management
  - Centralized type definitions

- **Production Ready**: Security and performance optimized
  - Security validations for production configurations
  - Efficient database connection handling
  - Comprehensive error handling and recovery
  - Structured logging with tenant context

- **Clean Architecture**: Proper separation of concerns
  - Clear package boundaries
  - Type safety throughout
  - Built-in testing patterns
  - Comprehensive documentation

### Migration Support
- **Legacy Package Compatibility**: Smooth migration paths
  - Drop-in replacement for dotmac-database components
  - Compatible tenant management API
  - Consolidated exception imports
  - Backward-compatible configuration patterns

[Unreleased]: https://github.com/dotmac-framework/dotmac-core/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/dotmac-framework/dotmac-core/releases/tag/v1.0.0