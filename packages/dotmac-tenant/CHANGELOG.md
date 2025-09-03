# Changelog

All notable changes to dotmac-tenant will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial tenant identity resolution system
- FastAPI middleware for automatic tenant context
- Multiple resolution strategies (host, subdomain, header-based)
- Tenant security enforcement and boundary validation
- Optional Row-Level Security (RLS) database helpers
- Schema-per-tenant database support
- Comprehensive test utilities
- Production-ready logging and monitoring
- Type-safe Pydantic v2 models throughout

### Security
- Tenant isolation enforcement
- Cross-tenant access prevention
- Security audit logging
- Request context boundaries

## [0.1.0] - 2024-01-XX

### Added
- Core tenant identity resolution
- TenantContext and TenantMiddleware
- Basic tenant resolution strategies
- Initial database integration
- Testing framework foundation

[Unreleased]: https://github.com/dotmac-framework/dotmac-tenant/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dotmac-framework/dotmac-tenant/releases/tag/v0.1.0