# Database Architecture and Tenant Isolation

This document provides comprehensive information about the DotMac Framework database architecture, tenant isolation strategies, and production deployment patterns.

## Architecture Overview

The DotMac Framework implements a sophisticated multi-tenant database architecture with two primary database systems:

### Database System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DotMac Database Architecture                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐                 ┌─────────────────┐        │
│  │  Management     │                 │   ISP Framework │        │
│  │  Platform DB    │◄────────────────┤   Database      │        │
│  │                 │   tenant info   │                 │        │
│  │ • Tenants       │                 │ • Customers     │        │
│  │ • Users         │                 │ • Services      │        │
│  │ • Billing       │                 │ • Network       │        │
│  │ • Monitoring    │                 │ • Analytics     │        │
│  │ • Tasks         │                 │ • Provisioning  │        │
│  └─────────────────┘                 └─────────────────┘        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                      Tenant Isolation Layer                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Row Level Security (RLS)                       ││
│  │  • Automatic tenant filtering at database level           ││
│  │  • Policy-based access control                            ││
│  │  • Tenant context enforcement                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Schema-per-Tenant (Optional)                  ││
│  │  • Complete data isolation                                 ││
│  │  • Individual schema per tenant                           ││
│  │  • Compliance-ready isolation                             ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Database Systems

### 1. Management Platform Database

**Purpose**: Central management and coordination of all ISP operations.

**Schema**: `dotmac_management`

**Key Tables**:
- `tenants` - Tenant definitions and configurations
- `users` - System users and authentication
- `monitoring_*` - System health and performance metrics
- `tasks_*` - Background job management
- `audit_*` - System audit trails

**Characteristics**:
- Multi-tenant with RLS enforcement
- Central source of truth for tenant configuration
- Cross-tenant reporting and analytics
- System-wide monitoring and alerting

### 2. ISP Framework Database

**Purpose**: Day-to-day ISP operations and customer management.

**Schema**: `dotmac_isp`

**Key Tables**:
- `isp_customers` - Customer records and profiles
- `isp_services` - Service definitions and provisioning
- `isp_billing_*` - Billing and invoicing
- `isp_network_*` - Network topology and configuration
- `isp_analytics_*` - Usage analytics and reporting

**Characteristics**:
- Tenant-isolated operations
- High-volume transactional data
- Real-time service provisioning
- Performance-optimized for operations

## Tenant Isolation Strategies

### Row Level Security (RLS) - Production Recommended

RLS provides robust database-level tenant isolation while maintaining operational simplicity.

#### Implementation Details

```sql
-- Core tenant isolation function
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('app.current_tenant_id', true);
EXCEPTION
    WHEN undefined_object THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Tenant access validation
CREATE OR REPLACE FUNCTION check_tenant_access(tenant_id TEXT) RETURNS BOOLEAN AS $$
BEGIN
    -- Allow superuser bypass for admin operations
    IF current_setting('is_superuser', true)::boolean THEN
        RETURN TRUE;
    END IF;
    
    -- Check if current tenant matches row tenant
    RETURN current_tenant_id() IS NOT NULL AND current_tenant_id() = tenant_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### RLS Policy Example

```sql
-- Enable RLS on customer table
ALTER TABLE isp_customers ENABLE ROW LEVEL SECURITY;

-- Create comprehensive policies
CREATE POLICY tenant_isolation_select ON isp_customers
    FOR SELECT
    USING (check_tenant_access(tenant_id));
    
CREATE POLICY tenant_isolation_insert ON isp_customers
    FOR INSERT
    WITH CHECK (check_tenant_access(tenant_id));
    
CREATE POLICY tenant_isolation_update ON isp_customers
    FOR UPDATE
    USING (check_tenant_access(tenant_id))
    WITH CHECK (check_tenant_access(tenant_id));
    
CREATE POLICY tenant_isolation_delete ON isp_customers
    FOR DELETE
    USING (check_tenant_access(tenant_id));
```

#### Application Integration

```python
from dotmac_shared.database.tenant_isolation import TenantAwareSession

# Automatic tenant context management
def get_customers(session: Session, tenant_id: str):
    with TenantAwareSession(session, tenant_id) as tenant_session:
        # All queries automatically filtered by tenant
        return tenant_session.query(Customer).all()
```

**Advantages**:
- ✅ Single database instance reduces operational complexity
- ✅ Automatic tenant filtering at database level
- ✅ Better resource utilization and cost efficiency
- ✅ Simplified backup and maintenance procedures
- ✅ Cross-tenant reporting capabilities when needed

**Requirements**:
- All tenant-aware tables must have `tenant_id` column
- Proper tenant context must be set for each request
- Database user must have appropriate RLS privileges

### Schema-per-Tenant - High Isolation Requirements

For organizations requiring complete data isolation or regulatory compliance.

#### Implementation

```python
from dotmac_shared.database.tenant_isolation import SchemaPerTenantManager

# Create dedicated tenant schema
schema_manager = SchemaPerTenantManager(engine)
schema_manager.create_tenant_schema("acme-corp-123")

# Results in schema: tenant_acme_corp_123
# With dedicated role: tenant_acme_corp_123_role
```

#### Usage Example

```python
# Tenant-specific database session
tenant_engine = engine.execution_options(
    schema_translate_map={None: "tenant_acme_corp_123"}
)

# All operations isolated to tenant schema
with tenant_engine.connect() as conn:
    result = conn.execute("SELECT * FROM customers")  # Uses tenant schema
```

**Advantages**:
- ✅ Complete data isolation between tenants
- ✅ Can support different schema versions per tenant
- ✅ Excellent for regulatory compliance (GDPR, HIPAA)
- ✅ Tenant-specific performance tuning possible

**Disadvantages**:
- ❌ More complex migration management
- ❌ Higher resource overhead per tenant
- ❌ Cross-tenant queries require special handling
- ❌ Backup and maintenance complexity

## Data Model Patterns

### Tenant-Aware Base Models

All tenant-aware models inherit from enhanced base classes:

```python
from dotmac_shared.database.mixins import ISPModelMixin, ManagementModelMixin

# ISP Framework models
class Customer(Base, ISPModelMixin):
    __tablename__ = "isp_customers"
    
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    # tenant_id, id, created_at, updated_at, is_active automatically included

# Management Platform models  
class MonitoringAlert(Base, ManagementModelMixin):
    __tablename__ = "monitoring_alerts"
    
    title = Column(String(255), nullable=False)
    severity = Column(String(50), nullable=False)
    # tenant_id, id, created_at, updated_at, deleted_at, audit fields included
```

### Automatic Index Generation

Models automatically generate tenant-optimized indexes:

```python
class Customer(Base, ISPModelMixin):
    __tablename__ = "isp_customers"
    
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)

# Automatically creates:
# - idx_isp_customers_tenant_id
# - idx_isp_customers_tenant_created  
# - idx_isp_customers_tenant_active
# - idx_isp_customers_tenant_email (composite with tenant_id)
```

## Performance Optimization

### Index Strategy

All tenant-aware tables follow a consistent indexing strategy:

```sql
-- Required base indexes
CREATE INDEX idx_table_tenant_id ON table_name (tenant_id);
CREATE INDEX idx_table_tenant_created ON table_name (tenant_id, created_at);
CREATE INDEX idx_table_tenant_updated ON table_name (tenant_id, updated_at);

-- Query-specific indexes (tenant_id always first)
CREATE INDEX idx_table_tenant_status ON table_name (tenant_id, status);
CREATE INDEX idx_table_tenant_email ON table_name (tenant_id, email);

-- Unique constraints include tenant_id
CREATE UNIQUE INDEX idx_table_tenant_email_unique ON table_name (tenant_id, email);
```

### Query Optimization

Tenant-aware queries are automatically optimized:

```python
# Automatic tenant filtering
from dotmac_shared.database.mixins import tenant_scope_query

def get_active_customers(session: Session) -> List[Customer]:
    query = tenant_scope_query(session, Customer)
    return query.filter(Customer.is_active == True).all()

# Generated SQL automatically includes tenant filter:
# SELECT * FROM isp_customers 
# WHERE tenant_id = 'current-tenant' AND is_active = true
```

### Connection Pooling

Tenant-aware connection pooling configuration:

```python
# Database configuration
DATABASE_CONFIG = {
    'pool_size': 20,
    'max_overflow': 50,
    'pool_timeout': 30,
    'pool_recycle': 3600,
    
    # Tenant-specific settings
    'tenant_pool_per_tenant': 5,
    'tenant_connection_timeout': 10,
}
```

## Security Implementation

### Tenant Context Management

Secure tenant context handling throughout the request lifecycle:

```python
from dotmac_shared.database.tenant_isolation import with_tenant_context

class CustomerService:
    @with_tenant_context(tenant_id="from-jwt-token")
    def create_customer(self, session: Session, customer_data: dict) -> Customer:
        # Tenant context automatically set
        customer = Customer(**customer_data)
        session.add(customer)
        session.commit()
        return customer
```

### Access Control

Multi-layered access control:

1. **Application Level**: JWT token validation and tenant extraction
2. **Database Level**: RLS policies enforce tenant boundaries
3. **Audit Level**: All tenant violations logged and monitored

```python
# Application-level tenant extraction
def get_tenant_from_request(request: Request) -> str:
    token = request.headers.get("Authorization")
    claims = decode_jwt(token)
    return claims.get("tenant_id")

# Database-level enforcement (automatic)
# RLS policies prevent cross-tenant data access

# Audit-level monitoring
@event.listens_for(Session, "before_flush")
def audit_tenant_violations(session, flush_context, instances):
    # Log any tenant isolation violations
    pass
```

## Migration Management

### Dual-Database Migration Strategy

Migrations are executed in specific order:

```bash
# 1. Management Platform (creates tenant definitions)
SERVICE_TYPE=management alembic upgrade head

# 2. ISP Framework (uses tenant information) 
SERVICE_TYPE=isp alembic upgrade head
```

### Migration Guards

All migrations include automatic tenant isolation validation:

```python
from dotmac_shared.database.migration_guards import (
    ensure_tenant_column,
    ensure_tenant_indexes,
    validate_tenant_isolation
)

def upgrade():
    # Create table
    op.create_table('new_service', ...)
    
    # Apply tenant isolation
    ensure_tenant_column('new_service')
    ensure_tenant_indexes('new_service', ['name', 'type'])
    validate_tenant_isolation('new_service')
```

## Monitoring and Observability

### Database Health Monitoring

Comprehensive monitoring of tenant isolation:

```python
# Tenant isolation health checks
def validate_tenant_isolation_health():
    checks = [
        validate_rls_policies(),
        validate_tenant_indexes(),
        validate_cross_tenant_queries(),
        validate_tenant_context_leaks()
    ]
    return all(checks)
```

### Performance Metrics

Key metrics for tenant-aware systems:

- **Tenant Distribution**: Query volume per tenant
- **Index Usage**: Effectiveness of tenant indexes
- **RLS Performance**: Policy evaluation overhead
- **Cross-Tenant Queries**: Unauthorized access attempts

### Audit Trail

Complete audit trail for compliance:

```sql
-- Audit table structure
CREATE TABLE audit_tenant_access (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    operation VARCHAR(50) NOT NULL,
    success BOOLEAN NOT NULL,
    access_time TIMESTAMP DEFAULT NOW(),
    client_ip INET,
    user_agent TEXT
);
```

## Production Deployment

### Environment Configuration

```bash
# Production RLS settings
ENABLE_RLS=true
REQUIRE_TENANT_COLUMN=true
ENABLE_AUDIT_TRIGGERS=true

# Performance settings
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
DB_POOL_TIMEOUT=30

# Security settings
TENANT_ISOLATION_STRICT=true
AUDIT_TENANT_ACCESS=true
```

### Backup Strategy

Tenant-aware backup and recovery:

```bash
# Full database backup
pg_dump -h $DB_HOST -U $DB_USER dotmac_management > management_backup.sql
pg_dump -h $DB_HOST -U $DB_USER dotmac_isp > isp_backup.sql

# Tenant-specific backup (for schema-per-tenant)
pg_dump -h $DB_HOST -U $DB_USER -n tenant_acme_corp_123 dotmac_isp > tenant_backup.sql
```

### Disaster Recovery

Multi-level recovery procedures:

1. **Database Level**: Point-in-time recovery with tenant validation
2. **Tenant Level**: Individual tenant data recovery
3. **Cross-Platform**: Coordinated recovery across management/ISP systems

## Best Practices

### Development Guidelines

1. **Always use tenant-aware mixins** for new models
2. **Include tenant_id in all unique constraints** 
3. **Test tenant isolation** in all new features
4. **Use migration guards** for all schema changes
5. **Monitor cross-tenant query attempts**

### Security Guidelines

1. **Never bypass tenant context** in production code
2. **Validate tenant access** at multiple levels
3. **Audit all tenant violations**
4. **Use least-privilege principles** for database users
5. **Regular security assessments** of tenant isolation

### Performance Guidelines

1. **Tenant_id first** in all composite indexes
2. **Monitor query performance** per tenant
3. **Use connection pooling** appropriately
4. **Regular index maintenance** and optimization
5. **Partition large tables** by tenant when needed

This architecture provides robust, scalable, and secure multi-tenant database operations while maintaining operational simplicity and performance optimization.