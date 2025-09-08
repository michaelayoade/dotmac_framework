# Changelog

All notable changes to the dotmac-service-kernel package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-01

### Added
- Initial release of dotmac-service-kernel
- Repository protocols with generic CRUD interfaces
- Service framework with base classes and lifecycle management
- Pagination utilities with Page container
- Unit of Work protocol for transaction management
- Standardized error classes for services and repositories
- Type-safe protocols for consistent service architecture
- Comprehensive test suite
- Full documentation and examples

### Features
- Generic repository protocol with type safety
- Base service classes with CRUD operations
- Pagination helpers with Page[T] container
- Service lifecycle management (initialize, shutdown, health)
- Error handling with ServiceError and RepositoryError
- Unit of Work protocol for transaction management
- Both sync and async operation support
- Tenant isolation support in base implementations

### Dependencies
- Python ^3.9
- Pydantic ^2.0 (for data validation)
- typing-extensions ^4.0 (for Python <3.10 compatibility)

### Development Tools
- pytest ^7.4 for testing
- mypy ^1.5 for type checking  
- ruff ^0.0.285 for linting and formatting
- pytest-asyncio ^0.20 for async test support
- pytest-cov ^4.1 for coverage reporting