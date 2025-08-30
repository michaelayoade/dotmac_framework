# IPAM Migration Guide

## Overview

This guide helps migrate from the basic IPAM implementation to the enhanced version with performance optimizations and advanced features.

## Database Migrations

### PostgreSQL Schema Updates

```sql
-- 1. Update data types for better performance
ALTER TABLE ipam_networks ALTER COLUMN network_id TYPE UUID USING network_id::UUID;
ALTER TABLE ipam_networks ALTER COLUMN cidr TYPE INET USING cidr::INET;
ALTER TABLE ipam_allocations ALTER COLUMN allocation_id TYPE UUID USING allocation_id::UUID;
ALTER TABLE ipam_reservations ALTER COLUMN reservation_id TYPE UUID USING reservation_id::UUID;

-- 2. Add audit fields for user tracking
ALTER TABLE ipam_networks ADD COLUMN created_by VARCHAR(100);
ALTER TABLE ipam_networks ADD COLUMN updated_by VARCHAR(100);
ALTER TABLE ipam_allocations ADD COLUMN created_by VARCHAR(100);
ALTER TABLE ipam_allocations ADD COLUMN updated_by VARCHAR(100);
ALTER TABLE ipam_reservations ADD COLUMN created_by VARCHAR(100);
ALTER TABLE ipam_reservations ADD COLUMN updated_by VARCHAR(100);

-- 3. Add indexes for performance
CREATE INDEX CONCURRENTLY idx_ipam_networks_tenant_cidr ON ipam_networks(tenant_id, cidr);
CREATE INDEX CONCURRENTLY idx_ipam_allocations_ip_tenant ON ipam_allocations(ip_address, tenant_id);
CREATE INDEX CONCURRENTLY idx_ipam_reservations_ip_tenant ON ipam_reservations(ip_address, tenant_id);
CREATE INDEX CONCURRENTLY idx_ipam_allocations_expires ON ipam_allocations(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX CONCURRENTLY idx_ipam_reservations_expires ON ipam_reservations(expires_at);

-- 4. Update constraints if needed
ALTER TABLE ipam_allocations DROP CONSTRAINT IF EXISTS ipam_allocations_tenant_id_ip_address_key;
ALTER TABLE ipam_allocations ADD CONSTRAINT ipam_allocations_tenant_id_ip_address_unique
    UNIQUE (tenant_id, ip_address);
```

### Data Migration for UUIDs

```python
# Migration script for converting string IDs to UUIDs
import uuid
from sqlalchemy import text

def migrate_to_uuids(db_session):
    """Convert string IDs to proper UUIDs."""

    # Generate UUIDs for existing records
    networks = db_session.execute(
        text("SELECT id, network_id FROM ipam_networks WHERE network_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'")
    ).fetchall()

    for network in networks:
        new_uuid = str(uuid.uuid4())
        db_session.execute(
            text("UPDATE ipam_networks SET network_id = :new_id WHERE id = :id"),
            {"new_id": new_uuid, "id": network.id}
        )

    db_session.commit()
```

## Code Updates

### 1. Import Changes

**Before:**

```python
from dotmac_shared.ipam.services.ipam_service import IPAMService
```

**After:**

```python
from dotmac_shared.ipam import EnhancedIPAMService
# or
from dotmac_shared.ipam.enhanced_service import EnhancedIPAMService
```

### 2. Service Initialization

**Before:**

```python
ipam = IPAMService(database_session, config)
```

**After:**

```python
from dotmac_shared.ipam.config_example import setup_enhanced_ipam_service

ipam = setup_enhanced_ipam_service(
    database_session=db_session,
    environment="production",
    redis_url="redis://localhost:6379/0"
)
```

### 3. Rate Limiting Setup

```python
# Add rate limiting middleware (FastAPI example)
from dotmac_shared.ipam.middleware.rate_limiting import IPAMRateLimitMiddleware

app.add_middleware(
    IPAMRateLimitMiddleware,
    rate_limiter=ipam.rate_limiter,
    enabled=True
)
```

### 4. Background Tasks

```python
# celery_app.py
from dotmac_shared.ipam.config_example import CELERY_IPAM_CONFIG

# Add IPAM tasks to Celery Beat schedule
beat_schedule.update(CELERY_IPAM_CONFIG["beat_schedule"])
```

## Configuration Updates

### Environment Variables

Add these environment variables:

```bash
# Rate Limiting
IPAM_RATE_LIMITING_ENABLED=true
IPAM_RATE_LIMITING_REDIS_URL=redis://localhost:6379/0

# Performance
IPAM_BATCH_SCANNING_ENABLED=true
IPAM_BATCH_SIZE=1000
IPAM_ENABLE_CACHING=true

# Audit
IPAM_AUDIT_LOGGING_ENABLED=true
IPAM_AUDIT_LOG_LEVEL=INFO

# MAC Validation
IPAM_MAC_VALIDATION_ENABLED=true
IPAM_STRICT_MAC_VALIDATION=true
```

### Configuration File

Create or update your IPAM configuration:

```python
from dotmac_shared.ipam.config_example import get_ipam_config

config = get_ipam_config("production")

# Customize as needed
config["rate_limiting"]["default_limits"]["allocate_ip"]["requests"] = 200
config["performance"]["batch_size"] = 2000
```

## Testing the Migration

### 1. Verify Database Schema

```sql
-- Check data types
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name IN ('ipam_networks', 'ipam_allocations', 'ipam_reservations')
AND column_name IN ('network_id', 'allocation_id', 'reservation_id', 'cidr');

-- Check indexes
SELECT indexname, tablename
FROM pg_indexes
WHERE tablename LIKE 'ipam_%';
```

### 2. Test Enhanced Service

```python
# Test basic functionality
async def test_migration():
    # Create network
    network = await ipam.create_network(
        tenant_id="test_tenant",
        cidr="192.168.1.0/24",
        network_name="Test Network"
    )

    # Test allocation
    allocation = await ipam.allocate_ip(
        tenant_id="test_tenant",
        network_id=network["network_id"],
        assigned_to="test_device"
    )

    # Test bulk allocation
    bulk_result = await ipam.bulk_allocate_ips(
        tenant_id="test_tenant",
        network_id=network["network_id"],
        count=5
    )

    # Test analytics
    analytics = await ipam.get_network_analytics(
        tenant_id="test_tenant",
        network_id=network["network_id"]
    )

    print(f"Migration test passed: {len(bulk_result['allocations'])} IPs allocated")
```

### 3. Performance Validation

```python
import time
import asyncio

async def performance_test():
    start_time = time.time()

    # Allocate 100 IPs
    tasks = []
    for i in range(100):
        task = ipam.allocate_ip(
            tenant_id="perf_test",
            network_id="test_network",
            assigned_to=f"device_{i}"
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = time.time()
    duration = end_time - start_time

    success_count = sum(1 for r in results if not isinstance(r, Exception))

    print(f"Performance test: {success_count}/100 allocations in {duration:.2f}s")
    print(f"Rate: {success_count/duration:.2f} allocations/second")
```

## Rollback Plan

If issues occur, you can rollback:

### 1. Database Rollback

```sql
-- Revert data types (if needed)
ALTER TABLE ipam_networks ALTER COLUMN network_id TYPE VARCHAR(100);
ALTER TABLE ipam_networks ALTER COLUMN cidr TYPE VARCHAR(50);

-- Remove audit columns
ALTER TABLE ipam_networks DROP COLUMN created_by;
ALTER TABLE ipam_networks DROP COLUMN updated_by;
-- Repeat for other tables...

-- Drop new indexes
DROP INDEX IF EXISTS idx_ipam_networks_tenant_cidr;
DROP INDEX IF EXISTS idx_ipam_allocations_ip_tenant;
-- etc...
```

### 2. Code Rollback

```python
# Revert to basic service
from dotmac_shared.ipam.services.ipam_service import IPAMService

ipam = IPAMService(database_session, basic_config)
```

## Troubleshooting

### Common Issues

1. **UUID Conversion Errors**
   - Ensure all existing IDs are valid UUIDs or generate new ones
   - Check foreign key references

2. **INET Type Issues**
   - Validate all CIDR values before migration
   - Handle invalid IP addresses in existing data

3. **Rate Limiting Not Working**
   - Verify Redis connection
   - Check rate limiter configuration
   - Ensure middleware is properly registered

4. **Performance Not Improved**
   - Verify batch scanning is enabled
   - Check database indexes are created
   - Monitor query execution plans

### Monitoring

Add monitoring for:

- Database query performance
- Rate limit violations
- Background task success rates
- Network utilization trends
- Error rates and types

### Support

If you encounter issues:

1. Check logs for specific error messages
2. Verify all prerequisites are met
3. Test in a staging environment first
4. Contact support with specific error details and configuration

## Post-Migration Checklist

- [ ] Database schema updated successfully
- [ ] All existing data migrated without loss
- [ ] Performance improvements validated
- [ ] Rate limiting configured and working
- [ ] Background tasks scheduled and running
- [ ] Monitoring and alerting configured
- [ ] Documentation updated
- [ ] Team trained on new features
