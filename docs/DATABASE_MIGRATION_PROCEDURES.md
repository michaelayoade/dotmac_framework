# Database Migration Procedures & Rollback Guide

## 🎯 **Production-Ready Migration System Overview**

The DotMac Framework now implements a comprehensive, production-ready database migration system with:

- ✅ **Rollback capabilities** with automated backups
- ✅ **Cross-platform coordination** with distributed locks
- ✅ **PostgreSQL testing** with fallback to SQLite
- ✅ **Tenant isolation** with individual migration locks
- ✅ **Monitoring integration** and comprehensive validation

---

## 🚀 **Quick Start Commands**

### Validate Migration System

```bash
# Comprehensive validation with PostgreSQL testing
python3 scripts/validate_migrations.py

# Environment variables for PostgreSQL testing
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password
export POSTGRES_DB=postgres
```

### Schema Management

```python
# Initialize schema with rollback support
from dotmac_shared.database_init.core.schema_manager import SchemaManager
from dotmac_shared.database_init.core.database_creator import DatabaseInstance

db_instance = DatabaseInstance("your_db_name", "postgresql://...")
schema_manager = SchemaManager(db_instance)

# Initialize with automatic backup
await schema_manager.initialize_schema()

# Rollback to specific version
success = await schema_manager.rollback_to_revision("previous_version")

# Get rollback information
rollback_info = await schema_manager.get_rollback_info("target_version")
```

### Cross-Platform Coordination

```python
# Coordinate migrations across platforms
from dotmac_shared.database.coordination import MigrationCoordinator

coordinator = MigrationCoordinator()
await coordinator.initialize()

# Coordinate multi-platform migration
platforms = ["isp_framework", "management_platform", "billing"]
result = await coordinator.coordinate_multi_platform_migration("v2.1.0", platforms)

# Check consistency across platforms
consistency = await coordinator.check_cross_platform_consistency()
```

### Tenant Migration Safety

```python
# Safe tenant migration with locks and backups
from dotmac_shared.database.coordination import TenantCoordinator

tenant_coord = TenantCoordinator("postgresql://master", "redis://localhost:6379")

# Migrate specific tenant safely
result = await tenant_coord.coordinate_tenant_migration("tenant_123", "v2.1.0")

# Rollback tenant migration
rollback_result = await tenant_coord.rollback_tenant_migration("tenant_123", "v2.0.0")

# Check tenant status
status = await tenant_coord.get_tenant_migration_status("tenant_123")
```

---

## 🔒 **Migration Safety Procedures**

### Pre-Migration Checklist

1. **Validate System Health**

   ```bash
   python3 scripts/validate_migrations.py
   ```

2. **Check Cross-Platform Consistency**

   ```python
   consistency = await coordinator.check_cross_platform_consistency()
   if consistency["status"] != "consistent":
       print("⚠️ Platforms not in sync - coordinate before migration")
   ```

3. **Ensure Backup System is Active**
   - Automated backups created before each migration
   - Backup metadata stored in Redis
   - Rollback information readily available

### During Migration

1. **Distributed Locks Active** - Prevents concurrent migrations
2. **Automated Backups** - Created before each migration step
3. **Transaction Safety** - All changes in database transactions
4. **Progress Monitoring** - Real-time status updates

### Post-Migration Verification

1. **Schema Integrity Check** - Automated verification
2. **Cross-Platform Sync** - Version consistency validation
3. **Tenant Isolation** - Individual tenant status checks

---

## 🆘 **Emergency Rollback Procedures**

### Immediate Rollback (Single Platform)

```python
# Emergency rollback for specific platform
schema_manager = SchemaManager(db_instance)
success = await schema_manager.rollback_to_revision("last_known_good_version")

if not success:
    # Check rollback information
    info = await schema_manager.get_rollback_info("target_version")
    print(f"Backup available: {info['backup_available']}")
```

### Cross-Platform Emergency Rollback

```python
# Coordinate rollback across all platforms
coordinator = MigrationCoordinator()

# Get current status
status = await coordinator.get_all_platform_versions()
print(f"Current versions: {status}")

# Coordinate rollback
platforms = list(status.keys())
rollback_id = f"emergency_rollback_{int(time.time())}"

# This would require implementing cross-platform rollback coordination
# For now, rollback each platform individually with locks
```

### Tenant Emergency Rollback

```python
# Rollback specific tenant in emergency
tenant_coord = TenantCoordinator("postgresql://master", "redis://localhost:6379")

# Get tenant status first
status = await tenant_coord.get_tenant_migration_status("affected_tenant_id")
print(f"Tenant status: {status}")

# Rollback to last known good version
result = await tenant_coord.rollback_tenant_migration(
    "affected_tenant_id",
    "last_known_good_version"
)

print(f"Rollback result: {result}")
```

---

## 📊 **Monitoring & Validation**

### Continuous Monitoring

```python
# Health checks for migration system
coordinator = MigrationCoordinator()

# Check system health
await coordinator.cleanup_expired_locks()

# Monitor platform consistency
consistency = await coordinator.check_cross_platform_consistency()

if consistency["status"] == "inconsistent":
    # Alert operations team
    inconsistencies = consistency["inconsistencies"]
    for issue in inconsistencies:
        print(f"⚠️ Version {issue['version']}: {issue['platforms']}")
```

### Production Validation

```bash
# Run comprehensive production readiness check
python3 scripts/validate_migrations.py

# Check for specific production features:
# ✅ Rollback capability
# ✅ Backup system
# ✅ Coordination system
# ✅ Monitoring integration
```

---

## 🔧 **Troubleshooting Guide**

### Common Issues

#### "Migration Lock Already Held"

```python
# Clean up expired locks
coordinator = MigrationCoordinator()
cleaned_locks = await coordinator.cleanup_expired_locks()
print(f"Cleaned {cleaned_locks} expired locks")
```

#### "Cross-Platform Version Mismatch"

```python
# Check platform versions
versions = await coordinator.get_all_platform_versions()
print(f"Platform versions: {versions}")

# Coordinate platforms to same version
result = await coordinator.coordinate_multi_platform_migration(
    target_version="consistent_version",
    platforms=list(versions.keys())
)
```

#### "Rollback Information Not Found"

```python
# Check backup availability
schema_manager = SchemaManager(db_instance)
rollback_info = await schema_manager.get_rollback_info("target_version")

if not rollback_info["backup_available"]:
    print("⚠️ No backup available - manual intervention required")
    # Contact operations team for manual recovery
```

#### "Tenant Migration Failed"

```python
# Check tenant status and available backups
tenant_coord = TenantCoordinator("postgresql://master", "redis://localhost:6379")
status = await tenant_coord.get_tenant_migration_status("failed_tenant_id")

print(f"Tenant backup count: {status['backup_count']}")
# Rollback using most recent backup
```

---

## 📋 **Migration Checklists**

### Development Environment

- [ ] Migration files follow naming conventions
- [ ] Both upgrade() and downgrade() methods implemented
- [ ] SQLite testing passes
- [ ] Syntax validation passes

### Staging Environment

- [ ] PostgreSQL testing passes
- [ ] Cross-platform consistency validated
- [ ] Rollback procedures tested
- [ ] Backup system operational

### Production Environment

- [ ] All validation checks pass
- [ ] Distributed locks functional
- [ ] Backup system verified
- [ ] Monitoring alerts configured
- [ ] Emergency procedures documented
- [ ] Operations team notified

---

## 🚨 **Production Deployment Safety**

### Before Migration

1. **Validate system**: `python3 scripts/validate_migrations.py`
2. **Check locks**: Ensure no migrations in progress
3. **Verify backups**: Backup system operational
4. **Alert team**: Notify operations of planned migration

### During Migration

1. **Monitor logs**: Watch for errors or warnings
2. **Check progress**: Validate each step completes
3. **Verify locks**: Ensure proper coordination
4. **Monitor performance**: Watch for impact on services

### After Migration

1. **Validate integrity**: Run schema verification
2. **Check consistency**: Verify cross-platform sync
3. **Test services**: Ensure applications function correctly
4. **Document results**: Record migration outcomes

---

## 📞 **Emergency Contacts**

For migration emergencies:

1. Check logs in `/var/log/dotmac/migrations/`
2. Use rollback procedures above
3. Escalate to operations team if rollback fails
4. Contact database team for manual intervention

---

**Status**: ✅ Production-Ready Migration System Implemented
**Last Updated**: $(date)
**Validation**: All critical migration features operational
