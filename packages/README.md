# DotMac Framework - Packages & Shared Services

This directory contains reusable packages and shared services that eliminate code duplication and provide consistent functionality across the DotMac Framework ecosystem.

## 📦 Current Packages

### ✅ dotmac-database-toolkit

**Status**: Production Ready
**Purpose**: Unified database operations with sync/async repositories, transaction management, and tenant isolation

**Key Features**:

- Eliminates 900+ lines of code duplication between platforms
- Unified sync/async repository interface with factory pattern
- Advanced tenant isolation with automatic filtering
- High-performance pagination (offset + cursor-based)
- Comprehensive transaction management with retry policies
- Database health monitoring and diagnostics

**Usage**:

```python
from dotmac_database import create_repository, QueryOptions, PaginationConfig
```

### ✅ dotmac-network-automation

**Status**: Production Ready
**Purpose**: Network infrastructure automation and monitoring for ISP operations

**Key Features**:

- RADIUS authentication and accounting management
- SSH automation with connection pooling
- SNMP monitoring and device health checks
- VOLTHA integration for fiber network management
- Device provisioning and configuration templates

## 🚀 Shared Services (src/dotmac_shared/)

The framework includes a comprehensive shared services ecosystem with **388 Python files** providing common functionality:

### ✅ Authentication Service (`auth/`)

**Status**: Production Ready
**Features**: JWT (RS256), RBAC with 60+ permissions, session management, MFA (TOTP/SMS), platform adapters

### ✅ Cache Service (`cache/`)

**Status**: Production Ready
**Features**: Multi-tier caching (Redis + Memory), tenant isolation, automatic failover, performance monitoring

### ✅ Billing Service (`billing/`)

**Status**: Production Ready
**Features**: Cross-platform billing logic, adapters for ISP and Management platforms, unified schemas

### ✅ File Service (`files/`)

**Status**: Production Ready
**Features**: PDF/Excel/CSV generation, template engine, tenant-isolated storage, async processing

### ✅ WebSocket Service (`websockets/`)

**Status**: Production Ready
**Features**: Real-time communication, room management, scaling with Redis, auth integration

### ✅ Observability Service (`observability/`)

**Status**: Production Ready
**Features**: Distributed tracing, OTLP metrics (SigNoz), health reporting

### ✅ Additional Services

- **Device Management** - Network device automation and monitoring
- **Provisioning** - Tenant and container provisioning
- **Events** - Event bus with Redis and in-memory adapters (Kafka support removed)
- **Secrets** - Enterprise secrets management with OpenBao
- **Plugins** - Plugin system with dependency resolution
- **Omnichannel** - Multi-channel communication orchestration

## Package Development Guidelines

### Creating New Packages

1. **Directory Structure**:

   ```
   packages/dotmac-[package-name]/
   ├── dotmac_[package_name]/
   │   ├── __init__.py
   │   └── [modules]/
   ├── tests/
   ├── pyproject.toml
   ├── README.md
   └── MIGRATION_GUIDE.md (if applicable)
   ```

2. **Naming Convention**:
   - Package directory: `dotmac-[package-name]` (with hyphens)
   - Python module: `dotmac_[package_name]` (with underscores)
   - Follow semantic versioning

3. **Configuration**:
   - Each package has its own `pyproject.toml` for Poetry
   - Main workspace includes package in root `pyproject.toml`
   - Add to test paths and coverage configuration

4. **Dependencies**:
   - Minimal external dependencies
   - Leverage existing framework dependencies where possible
   - Document any additional requirements

### Integration with Main Framework

Packages are integrated into the main framework workspace:

1. **Package Registration**:

   ```toml
   # In root pyproject.toml
   packages = [
       {include = "dotmac_[package_name]", from = "packages/dotmac-[package-name]"}
   ]
   ```

2. **Testing Integration**:

   ```toml
   testpaths = [
       "packages/dotmac-[package-name]/tests",
   ]
   ```

3. **Coverage Tracking**:

   ```toml
   source = [
       "packages/dotmac-[package-name]/dotmac_[package_name]",
   ]
   ```

## 📊 DRY Compliance Analysis

### ✅ Eliminated Duplications

- **Database Operations**: 900+ lines eliminated via `dotmac-database-toolkit`
- **Authentication Logic**: Unified across platforms via `dotmac_shared/auth/`
- **Cache Management**: Consistent caching patterns via `dotmac_shared/cache/`
- **File Processing**: Unified generation via `dotmac_shared/files/`
- **Billing Logic**: Cross-platform billing via `dotmac_shared/billing/`

### ⚠️ Remaining Service Duplications

**Analysis Results**: Found **527 service classes** across platforms:

- **ISP Framework**: 432 service occurrences across 151 files
- **Management Platform**: 95 service occurrences across 38 files

**Key Duplication Areas**:

1. **Notification Services**: 3+ implementations across platforms
2. **Monitoring Services**: 2+ implementations with similar patterns
3. **User Management**: Duplicate user service logic
4. **Plugin Services**: Multiple plugin management implementations

### 🎯 Next DRY Improvements

**Priority Recommendations**:

1. **Extract Notification Service Package**
   - Consolidate 3+ notification implementations
   - Create `dotmac_shared/notifications/` with unified API
   - Support email, SMS, push notifications, webhooks

2. **Standardize Monitoring Services**
   - Merge monitoring service implementations
   - Leverage existing `dotmac_shared/observability/`
   - Create consistent metrics collection patterns

3. **Unify User Management**
   - Extract common user service patterns
   - Build on `dotmac_shared/auth/` foundation
   - Create user lifecycle management service

4. **Consolidate Plugin Systems**
   - Already have `dotmac_shared/plugins/` foundation
   - Migrate platform-specific plugin services
   - Create unified plugin discovery and management

## 🔧 DRY Implementation Checklist

### Before Adding New Services

- [ ] Check if functionality exists in `dotmac_shared/`
- [ ] Review if similar pattern exists in other platform
- [ ] Consider extracting to shared service if used >1 time
- [ ] Use existing adapters pattern for platform integration

### Service Integration Pattern

```python
# ✅ Good: Use shared service with adapter
from dotmac_shared.auth import AuthService
from dotmac_shared.auth.adapters import ISPAuthAdapter

auth_service = AuthService()
isp_auth = ISPAuthAdapter(auth_service)

# ❌ Bad: Duplicate service implementation
class ISPAuthService:  # Don't create if shared service exists
    pass
```

### Best Practices

- **Single Responsibility**: Each package should have one clear purpose
- **Minimal Dependencies**: Avoid heavy external dependencies
- **Comprehensive Testing**: Include unit, integration, and migration tests
- **Documentation**: Provide clear README and migration guides
- **Backward Compatibility**: Maintain API stability where possible
- **Performance**: Consider performance impact of abstractions

### Migration Strategy

When extracting code into packages:

1. **Analysis Phase**: Identify code duplication and shared patterns
2. **Design Phase**: Create unified interface and architecture
3. **Implementation Phase**: Build package with comprehensive features
4. **Testing Phase**: Ensure all functionality works correctly
5. **Migration Phase**: Update existing code to use package
6. **Cleanup Phase**: Remove old duplicated code

### Benefits of Package Architecture

- **Code Reuse**: Eliminate duplication across modules
- **Consistent APIs**: Unified interfaces for common operations
- **Better Testing**: Isolated testing of core functionality
- **Easier Maintenance**: Single codebase for shared logic
- **Performance**: Optimized implementations in one place
- **Documentation**: Centralized documentation for common patterns

## 📈 Impact Summary

The DotMac Framework has successfully implemented a comprehensive shared services architecture:

### ✅ Achievements

- **2 Production Packages**: Database toolkit + Network automation
- **388 Shared Service Files**: Comprehensive cross-platform functionality
- **900+ Lines Eliminated**: Database duplication removed
- **527 Service Classes**: Identified across both platforms
- **Production-Ready Services**: Auth, Cache, Billing, Files, WebSockets, Observability

### 📊 Current Architecture Status

- **Shared Services Coverage**: ~70% of common functionality
- **Code Duplication Remaining**: ~30% (primarily notifications, monitoring, user management)
- **Platform Integration**: Mature adapter pattern implemented
- **DRY Compliance**: Strong foundation with clear improvement path

### 🎯 Next Steps

1. **Priority**: Extract notification service (3+ implementations identified)
2. **Standardize**: Monitoring service implementations
3. **Unify**: User management patterns across platforms
4. **Complete**: Plugin system consolidation

This architecture supports the DotMac Framework's goal of providing a comprehensive, maintainable, and scalable ISP management solution while maintaining DRY principles and consistent APIs across platforms.
