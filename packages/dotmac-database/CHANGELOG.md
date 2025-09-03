# Changelog

All notable changes to dotmac-database will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial database foundation package for DotMac Framework
- Declarative base with BaseModel containing common fields (id, created_at, updated_at)
- Comprehensive mixins system:
  - SoftDeleteMixin for logical deletion with is_active/deleted_at
  - AuditMixin for audit trails with created_by/updated_by/request_id  
  - TenantAwareMixin for multi-tenant applications with tenant_id
- Async engine and session management with SQLAlchemy 2.0+
- FastAPI dependencies for database session injection
- Row-Level Security (RLS) helpers for tenant isolation
- Schema-per-tenant support with search path management
- Smart caching system with Redis backend and pattern invalidation
- Distributed coordination with Redis locks and PostgreSQL advisory locks
- Alembic integration helpers for complex migration scenarios
- Comprehensive test suite with fixtures and utilities
- Type-safe implementation with full mypy support

### Features
- **Engine Management**: Async engine creation with connection pooling
- **Session Lifecycle**: Context managers with proper cleanup and error handling
- **Multi-Tenancy**: Generic RLS and schema-per-tenant patterns
- **Performance**: Redis-based caching with statistics and invalidation patterns
- **Coordination**: Distributed locking for exclusive operations
- **Migration Support**: Alembic helpers for database evolution
- **Framework Integration**: Ready-to-use FastAPI dependencies
- **Testing**: Comprehensive test utilities and fixtures

### Dependencies
- SQLAlchemy >= 2.0.0 (async support)
- typing-extensions >= 4.0.0
- Optional extras for FastAPI, Redis, Alembic, PostgreSQL drivers

### Migration Notice
This package replaces `dotmac_shared.database` with enhanced functionality:
- Async-first design with SQLAlchemy 2.0+
- Framework-agnostic mixins (no middleware coupling)
- Enhanced caching with statistics and pattern matching
- Comprehensive coordination primitives
- Better separation of concerns

## [1.0.0] - 2024-XX-XX

### Added
- Initial release of dotmac-database package
- Core database primitives for DotMac Framework
- Full backward compatibility shims for migration from dotmac_shared.database

[Unreleased]: https://github.com/dotmac-framework/dotmac-database/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/dotmac-framework/dotmac-database/releases/tag/v1.0.0