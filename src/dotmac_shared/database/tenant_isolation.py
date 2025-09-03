"""
Database-level tenant isolation utilities.
Provides RLS policies, schema-per-tenant guidance, and tenant security functions.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import text, DDL, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_, or_
import logging

logger = logging.getLogger(__name__)

# Current tenant context (set per request)
_current_tenant_id: Optional[str] = None

def set_current_tenant(tenant_id: str) -> None:
    """Set the current tenant context for RLS."""
    global _current_tenant_id
    _current_tenant_id = tenant_id

def get_current_tenant() -> Optional[str]:
    """Get the current tenant context."""
    return _current_tenant_id

def clear_tenant_context() -> None:
    """Clear the tenant context."""
    global _current_tenant_id
    _current_tenant_id = None

class TenantIsolationError(Exception):
    """Exception raised for tenant isolation violations."""
    pass

class RLSPolicyManager:
    """Manages Row Level Security policies for tenant isolation."""

    @staticmethod
    def create_tenant_policy_function(engine: Engine) -> None:
        """Create the tenant context function for RLS policies."""
        ddl = DDL("""
        -- Create or replace the tenant context function
        CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS TEXT AS $$
        BEGIN
            RETURN current_setting('app.current_tenant_id', true);
        EXCEPTION
            WHEN undefined_object THEN
                RETURN NULL;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        
        -- Create tenant isolation check function
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
        
        -- Create function to ensure tenant_id is set
        CREATE OR REPLACE FUNCTION ensure_tenant_id() RETURNS TEXT AS $$
        DECLARE
            tid TEXT;
        BEGIN
            tid := current_tenant_id();
            IF tid IS NULL THEN
                RAISE EXCEPTION 'No tenant context set. Call set_tenant_id() first.';
            END IF;
            RETURN tid;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        
        -- Create audit trigger function for tenant enforcement
        CREATE OR REPLACE FUNCTION enforce_tenant_on_insert() RETURNS TRIGGER AS $$
        BEGIN
            -- Ensure tenant_id is set on insert
            IF NEW.tenant_id IS NULL THEN
                NEW.tenant_id := ensure_tenant_id();
            ELSIF NEW.tenant_id != current_tenant_id() THEN
                RAISE EXCEPTION 'Cannot insert row with different tenant_id than current context';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Create audit trigger function for tenant validation
        CREATE OR REPLACE FUNCTION validate_tenant_on_update() RETURNS TRIGGER AS $$
        BEGIN
            -- Prevent tenant_id changes
            IF OLD.tenant_id != NEW.tenant_id THEN
                RAISE EXCEPTION 'Cannot change tenant_id of existing row';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)
        
        with engine.connect() as conn:
            conn.execute(ddl)
            conn.commit()
            logger.info("Created tenant isolation functions")

    @staticmethod
    def enable_rls_on_table(engine: Engine, table_name: str, schema: str = 'public') -> None:
        """Enable Row Level Security on a table."""
        ddl = DDL(f"""
        -- Enable RLS on table
        ALTER TABLE {schema}.{table_name} ENABLE ROW LEVEL SECURITY;
        
        -- Drop existing policies if they exist
        DROP POLICY IF EXISTS tenant_isolation_policy ON {schema}.{table_name};
        DROP POLICY IF EXISTS tenant_isolation_select ON {schema}.{table_name};
        DROP POLICY IF EXISTS tenant_isolation_insert ON {schema}.{table_name};
        DROP POLICY IF EXISTS tenant_isolation_update ON {schema}.{table_name};
        DROP POLICY IF EXISTS tenant_isolation_delete ON {schema}.{table_name};
        
        -- Create comprehensive RLS policies
        CREATE POLICY tenant_isolation_select ON {schema}.{table_name}
            FOR SELECT
            USING (check_tenant_access(tenant_id));
            
        CREATE POLICY tenant_isolation_insert ON {schema}.{table_name}
            FOR INSERT
            WITH CHECK (check_tenant_access(tenant_id));
            
        CREATE POLICY tenant_isolation_update ON {schema}.{table_name}
            FOR UPDATE
            USING (check_tenant_access(tenant_id))
            WITH CHECK (check_tenant_access(tenant_id));
            
        CREATE POLICY tenant_isolation_delete ON {schema}.{table_name}
            FOR DELETE
            USING (check_tenant_access(tenant_id));
        """)
        
        with engine.connect() as conn:
            conn.execute(ddl)
            conn.commit()
            logger.info(f"Enabled RLS on table {schema}.{table_name}")

    @staticmethod
    def create_tenant_triggers(engine: Engine, table_name: str, schema: str = 'public') -> None:
        """Create tenant enforcement triggers on a table."""
        ddl = DDL(f"""
        -- Drop existing triggers if they exist
        DROP TRIGGER IF EXISTS enforce_tenant_insert_trigger ON {schema}.{table_name};
        DROP TRIGGER IF EXISTS validate_tenant_update_trigger ON {schema}.{table_name};
        
        -- Create tenant enforcement triggers
        CREATE TRIGGER enforce_tenant_insert_trigger
            BEFORE INSERT ON {schema}.{table_name}
            FOR EACH ROW EXECUTE FUNCTION enforce_tenant_on_insert();
            
        CREATE TRIGGER validate_tenant_update_trigger
            BEFORE UPDATE ON {schema}.{table_name}
            FOR EACH ROW EXECUTE FUNCTION validate_tenant_on_update();
        """)
        
        with engine.connect() as conn:
            conn.execute(ddl)
            conn.commit()
            logger.info(f"Created tenant triggers on table {schema}.{table_name}")

class TenantAwareSession:
    """Database session wrapper with automatic tenant context management."""
    
    def __init__(self, session: Session, tenant_id: str, bypass_rls: bool = False):
        self.session = session
        self.tenant_id = tenant_id
        self.bypass_rls = bypass_rls
        self._original_tenant = get_current_tenant()
        
        # Set tenant context in database session
        self._set_session_tenant()
        
    def _set_session_tenant(self) -> None:
        """Set the tenant context in the database session."""
        try:
            if self.bypass_rls:
                # Set superuser flag for admin operations
                self.session.execute(text("SELECT set_config('is_superuser', 'true', true)"))
            else:
                self.session.execute(text("SELECT set_config('is_superuser', 'false', true)"))
                
            # Set tenant context
            self.session.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": self.tenant_id}
            )
            
            # Set global context for application code
            set_current_tenant(self.tenant_id)
            
        except Exception as e:
            logger.error(f"Failed to set tenant context: {e}")
            raise TenantIsolationError(f"Failed to set tenant context: {e}")
    
    def __enter__(self):
        return self.session
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original tenant context
        if self._original_tenant:
            set_current_tenant(self._original_tenant)
        else:
            clear_tenant_context()
            
        # Clear database session context
        try:
            self.session.execute(text("SELECT set_config('app.current_tenant_id', NULL, true)"))
            self.session.execute(text("SELECT set_config('is_superuser', 'false', true)"))
        except Exception as e:
            logger.warning(f"Failed to clear tenant context: {e}")

class SchemaPerTenantManager:
    """Manager for schema-per-tenant isolation strategy."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        
    def create_tenant_schema(self, tenant_id: str) -> None:
        """Create a dedicated schema for a tenant."""
        schema_name = f"tenant_{tenant_id.replace('-', '_')}"
        
        ddl = DDL(f"""
        -- Create tenant schema
        CREATE SCHEMA IF NOT EXISTS {schema_name};
        
        -- Create tenant-specific role
        CREATE ROLE {schema_name}_role;
        
        -- Grant schema usage to tenant role
        GRANT USAGE ON SCHEMA {schema_name} TO {schema_name}_role;
        GRANT CREATE ON SCHEMA {schema_name} TO {schema_name}_role;
        
        -- Set default privileges for future tables
        ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name}
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {schema_name}_role;
        
        ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name}
        GRANT USAGE, SELECT ON SEQUENCES TO {schema_name}_role;
        """)
        
        with self.engine.connect() as conn:
            conn.execute(ddl)
            conn.commit()
            logger.info(f"Created tenant schema: {schema_name}")
    
    def drop_tenant_schema(self, tenant_id: str, cascade: bool = False) -> None:
        """Drop a tenant's schema."""
        schema_name = f"tenant_{tenant_id.replace('-', '_')}"
        cascade_clause = "CASCADE" if cascade else "RESTRICT"
        
        ddl = DDL(f"""
        -- Drop tenant schema
        DROP SCHEMA IF EXISTS {schema_name} {cascade_clause};
        
        -- Drop tenant role
        DROP ROLE IF EXISTS {schema_name}_role;
        """)
        
        with self.engine.connect() as conn:
            conn.execute(ddl)
            conn.commit()
            logger.info(f"Dropped tenant schema: {schema_name}")
    
    def get_tenant_schema_name(self, tenant_id: str) -> str:
        """Get the schema name for a tenant."""
        return f"tenant_{tenant_id.replace('-', '_')}"

class TenantIndexManager:
    """Manager for tenant-aware database indexes."""
    
    @staticmethod
    def create_tenant_indexes(engine: Engine, table_name: str, additional_columns: List[str] = None) -> None:
        """Create optimized indexes for tenant isolation."""
        additional_columns = additional_columns or []
        
        indexes = [
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_{table_name}_tenant_id ON {table_name} (tenant_id)",
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_{table_name}_tenant_created ON {table_name} (tenant_id, created_at)",
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_{table_name}_tenant_updated ON {table_name} (tenant_id, updated_at)",
        ]
        
        # Add composite indexes with additional columns
        for col in additional_columns:
            indexes.append(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_{table_name}_tenant_{col} ON {table_name} (tenant_id, {col})"
            )
        
        with engine.connect() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Failed to create index: {index_sql}, error: {e}")
        
        logger.info(f"Created tenant indexes for table {table_name}")

def setup_tenant_isolation(engine: Engine, strategy: str = "rls") -> None:
    """Set up tenant isolation for the database."""
    if strategy == "rls":
        # Create RLS functions
        RLSPolicyManager.create_tenant_policy_function(engine)
        logger.info("Set up RLS-based tenant isolation")
        
    elif strategy == "schema":
        # Schema-per-tenant setup is done per tenant
        logger.info("Schema-per-tenant isolation ready")
        
    else:
        raise ValueError(f"Unknown isolation strategy: {strategy}")

def enable_tenant_isolation_on_model(engine: Engine, model_class, strategy: str = "rls") -> None:
    """Enable tenant isolation on a specific model."""
    table_name = model_class.__tablename__
    
    if strategy == "rls":
        # Enable RLS policies and triggers
        RLSPolicyManager.enable_rls_on_table(engine, table_name)
        RLSPolicyManager.create_tenant_triggers(engine, table_name)
        
        # Create optimized tenant indexes
        TenantIndexManager.create_tenant_indexes(engine, table_name)
        
    logger.info(f"Enabled tenant isolation on model {model_class.__name__}")

# Decorator for automatic tenant context management
def with_tenant_context(tenant_id: str, bypass_rls: bool = False):
    """Decorator to automatically set tenant context for database operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Find Session parameter
            session = None
            for arg in args:
                if isinstance(arg, Session):
                    session = arg
                    break
            
            if 'session' in kwargs:
                session = kwargs['session']
            
            if session is None:
                # No session found, just set global context
                original_tenant = get_current_tenant()
                try:
                    set_current_tenant(tenant_id)
                    return func(*args, **kwargs)
                finally:
                    if original_tenant:
                        set_current_tenant(original_tenant)
                    else:
                        clear_tenant_context()
            else:
                # Use TenantAwareSession
                with TenantAwareSession(session, tenant_id, bypass_rls) as tenant_session:
                    # Replace session parameter
                    if 'session' in kwargs:
                        kwargs['session'] = tenant_session
                    else:
                        # Replace session in args
                        args = list(args)
                        for i, arg in enumerate(args):
                            if isinstance(arg, Session):
                                args[i] = tenant_session
                                break
                        args = tuple(args)
                    
                    return func(*args, **kwargs)
        return wrapper
    return decorator