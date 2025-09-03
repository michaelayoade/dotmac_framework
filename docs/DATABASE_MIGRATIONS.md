# Database Migrations Guide

This document outlines the Alembic migration strategy for the DotMac Framework, covering both Management Platform and ISP Framework databases with proper tenant isolation.

## Architecture Overview

The DotMac Framework uses a dual-database approach:

- **Management Platform**: Central management database with multi-tenant data
- **ISP Framework**: Per-tenant ISP operations database with tenant isolation

## Migration Execution Order

### 1. Management Platform First
The Management Platform migrations must be executed before ISP Framework migrations because:

- Management Platform creates tenant definitions
- ISP Framework depends on tenant configurations
- Cross-platform references may exist

### 2. Migration Commands

```bash
# Management Platform Migrations
export SERVICE_TYPE=management
export DATABASE_URL="postgresql://user:pass@host:5432/dotmac_management"
alembic upgrade head

# ISP Framework Migrations  
export SERVICE_TYPE=isp
export DATABASE_URL="postgresql://user:pass@host:5432/dotmac_isp"
alembic upgrade head
```

### 3. Production Deployment Order

1. **Pre-deployment validation**
   ```bash
   # Check migration status
   alembic current
   alembic show head
   ```

2. **Execute Management migrations**
   ```bash
   SERVICE_TYPE=management alembic upgrade head
   ```

3. **Execute ISP migrations**
   ```bash
   SERVICE_TYPE=isp alembic upgrade head
   ```

4. **Post-migration validation**
   ```bash
   # Run database health checks
   python scripts/validate_db_health.py
   ```

## Tenant Isolation Strategies

### Row Level Security (RLS) - Recommended for Production

RLS provides database-level tenant isolation while using a single database:

```python
# Enable RLS on tenant-aware tables
from dotmac_shared.database.tenant_isolation import setup_tenant_isolation, enable_tenant_isolation_on_model

# Setup during application initialization
setup_tenant_isolation(engine, strategy="rls")

# Enable on specific models
enable_tenant_isolation_on_model(engine, MyModel, strategy="rls")
```

**Advantages:**
- Single database instance
- Automatic tenant filtering at DB level
- Better resource utilization
- Easier backup and maintenance

**Requirements:**
- All tenant-aware tables must have `tenant_id` column
- Proper tenant context must be set in each request
- Database user must have RLS privileges

### Schema-per-Tenant - For High Isolation Requirements

Each tenant gets a dedicated schema within the same database:

```python
from dotmac_shared.database.tenant_isolation import SchemaPerTenantManager

# Create tenant schema
schema_manager = SchemaPerTenantManager(engine)
schema_manager.create_tenant_schema("tenant-123")

# Use tenant-specific schema
tenant_engine = engine.execution_options(
    schema_translate_map={None: "tenant_123"}
)
```

**Advantages:**
- Complete data isolation
- Can have different schema versions per tenant
- Better for compliance requirements

**Disadvantages:**
- More complex migration management
- Higher resource overhead
- More complex queries for cross-tenant operations

## Migration Guards and Validation

### Tenant Column Guards

All migrations that affect tenant-aware tables must include validation guards:

```python
"""Add customer_profiles table

Revision ID: abc123
Revises: def456
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from dotmac_shared.database.migration_guards import (
    ensure_tenant_column,
    ensure_tenant_indexes,
    validate_tenant_isolation
)

# revision identifiers
revision = 'abc123'
down_revision = 'def456'
branch_labels = None
depends_on = None

def upgrade():
    # Create table with tenant isolation
    op.create_table('customer_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Apply tenant isolation guards
    ensure_tenant_column('customer_profiles')
    ensure_tenant_indexes('customer_profiles', ['name', 'email'])
    
    # Enable RLS if configured
    validate_tenant_isolation('customer_profiles')

def downgrade():
    op.drop_table('customer_profiles')
```

### Index Creation Guards

Ensure all tenant-aware tables have proper indexes:

```python
def upgrade():
    # Create tenant-optimized indexes
    op.create_index(
        'idx_customer_profiles_tenant_id', 
        'customer_profiles', 
        ['tenant_id']
    )
    op.create_index(
        'idx_customer_profiles_tenant_created', 
        'customer_profiles', 
        ['tenant_id', 'created_at']
    )
    op.create_index(
        'idx_customer_profiles_tenant_email', 
        'customer_profiles', 
        ['tenant_id', 'email'], 
        unique=True
    )
```

## Environment-Specific Configuration

### Development Environment

```ini
# alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://dev:dev@localhost:5432/dotmac_dev

[development]
# Enable verbose logging
sqlalchemy.echo = true

# Skip RLS setup in development
skip_rls_setup = true

# Allow unsafe operations
allow_unsafe_migrations = true
```

### Staging Environment

```ini
[staging]
# Use connection pooling
sqlalchemy.pool_size = 10
sqlalchemy.max_overflow = 20

# Enable RLS
enable_rls = true

# Require migration validation
require_migration_validation = true
```

### Production Environment

```ini
[production]
# Strict validation
require_migration_validation = true
require_backup_before_migration = true

# Enable all security features
enable_rls = true
enable_audit_triggers = true

# Performance settings
sqlalchemy.pool_size = 20
sqlalchemy.max_overflow = 50
```

## Migration Best Practices

### 1. Tenant-Safe Migrations

Always consider tenant isolation when writing migrations:

```python
def upgrade():
    # ✅ Good: Includes tenant_id
    op.create_table('orders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Decimal(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'])
    )
    
    # ❌ Bad: Missing tenant_id
    op.create_table('global_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value', sa.String(255), nullable=False)
    )
```

### 2. Index Strategy

Always create tenant-optimized indexes:

```python
def upgrade():
    # Required tenant indexes
    op.create_index('idx_table_tenant_id', 'table_name', ['tenant_id'])
    
    # Composite indexes with tenant_id first
    op.create_index('idx_table_tenant_status', 'table_name', ['tenant_id', 'status'])
    op.create_index('idx_table_tenant_created', 'table_name', ['tenant_id', 'created_at'])
    
    # Unique constraints must include tenant_id
    op.create_index(
        'idx_table_tenant_email', 
        'table_name', 
        ['tenant_id', 'email'], 
        unique=True
    )
```

### 3. Data Migration with Tenant Context

When migrating data, ensure tenant isolation:

```python
def upgrade():
    # Create table first
    op.create_table('new_customers', ...)
    
    # Migrate data with tenant awareness
    connection = op.get_bind()
    
    # Get all tenants
    tenants = connection.execute(
        sa.text("SELECT DISTINCT tenant_id FROM old_customers")
    ).fetchall()
    
    for tenant in tenants:
        # Set tenant context for migration
        connection.execute(
            sa.text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant.tenant_id}
        )
        
        # Migrate tenant data
        connection.execute(sa.text("""
            INSERT INTO new_customers (id, tenant_id, name, email)
            SELECT id, tenant_id, name, email 
            FROM old_customers 
            WHERE tenant_id = :tenant_id
        """), {"tenant_id": tenant.tenant_id})
```

### 4. Rollback Safety

Ensure all migrations are safely reversible:

```python
def upgrade():
    # Store backup information
    op.execute("CREATE TABLE backup_customer_profiles AS SELECT * FROM customer_profiles")
    
    # Make changes
    op.add_column('customer_profiles', sa.Column('new_field', sa.String(255)))
    
def downgrade():
    # Restore from backup if needed
    op.drop_column('customer_profiles', 'new_field')
    op.execute("DROP TABLE IF EXISTS backup_customer_profiles")
```

## Monitoring and Validation

### Migration Health Checks

After each migration, run validation:

```bash
# Validate tenant isolation
python scripts/validate_tenant_isolation.py

# Check index performance  
python scripts/validate_tenant_indexes.py

# Verify RLS policies
python scripts/validate_rls_policies.py
```

### Performance Monitoring

Monitor migration performance:

```python
# In migration files
import time
import logging

def upgrade():
    start_time = time.time()
    
    # Migration operations here
    op.create_table(...)
    
    duration = time.time() - start_time
    logging.info(f"Migration completed in {duration:.2f} seconds")
```

## Troubleshooting

### Common Issues

1. **Missing tenant_id column**
   ```
   Error: TenantIsolationError: No tenant context set
   Solution: Add tenant_id column and proper indexes
   ```

2. **RLS policy conflicts**
   ```
   Error: permission denied for relation table_name
   Solution: Check RLS policies and tenant context
   ```

3. **Index performance issues**
   ```
   Error: Slow query performance
   Solution: Ensure tenant_id is first column in composite indexes
   ```

### Recovery Procedures

1. **Failed migration recovery**
   ```bash
   # Check migration status
   alembic current
   
   # Rollback to previous version
   alembic downgrade -1
   
   # Fix issues and retry
   alembic upgrade head
   ```

2. **Tenant isolation validation**
   ```bash
   # Validate all tenant isolation
   python scripts/repair_tenant_isolation.py
   ```

## Security Considerations

### 1. Migration User Privileges

Migration user needs specific privileges:

```sql
-- Create migration user
CREATE USER alembic_user WITH PASSWORD 'secure_password';

-- Grant necessary privileges
GRANT CONNECT ON DATABASE dotmac_management TO alembic_user;
GRANT USAGE ON SCHEMA public TO alembic_user;
GRANT CREATE ON SCHEMA public TO alembic_user;

-- For RLS setup
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO alembic_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO alembic_user;
```

### 2. Tenant Data Protection

Ensure migrations don't leak tenant data:

```python
def upgrade():
    # ✅ Good: Tenant-aware data migration
    op.execute(sa.text("""
        UPDATE customers 
        SET status = 'active' 
        WHERE tenant_id = current_setting('app.current_tenant_id')
    """))
    
    # ❌ Bad: Cross-tenant data access
    op.execute(sa.text("UPDATE customers SET status = 'active'"))
```

This comprehensive migration strategy ensures proper tenant isolation while maintaining database consistency across the DotMac Framework platforms.