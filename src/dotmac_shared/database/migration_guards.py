"""
Migration guards for ensuring proper tenant isolation in Alembic migrations.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from alembic import op
from sqlalchemy import text, inspect, Table, MetaData
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

class MigrationValidationError(Exception):
    """Exception raised when migration validation fails."""
    pass

def get_environment_config() -> Dict[str, Any]:
    """Get environment-specific configuration."""
    return {
        'enable_rls': os.getenv('ENABLE_RLS', 'true').lower() == 'true',
        'require_tenant_column': os.getenv('REQUIRE_TENANT_COLUMN', 'true').lower() == 'true',
        'enable_audit_triggers': os.getenv('ENABLE_AUDIT_TRIGGERS', 'false').lower() == 'true',
        'skip_validation': os.getenv('SKIP_MIGRATION_VALIDATION', 'false').lower() == 'true',
        'service_type': os.getenv('SERVICE_TYPE', 'management'),
    }

def ensure_tenant_column(table_name: str, column_name: str = 'tenant_id') -> None:
    """
    Ensure a table has a proper tenant_id column with constraints and indexes.
    
    Args:
        table_name: Name of the table to validate
        column_name: Name of the tenant column (default: 'tenant_id')
    """
    config = get_environment_config()
    
    if config['skip_validation']:
        logger.info(f"Skipping tenant column validation for {table_name}")
        return
    
    if not config['require_tenant_column']:
        logger.info(f"Tenant column not required for {table_name}")
        return
    
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Check if table exists
    if not inspector.has_table(table_name):
        raise MigrationValidationError(f"Table {table_name} does not exist")
    
    # Check if tenant column exists
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    
    if column_name not in columns:
        logger.warning(f"Adding missing {column_name} column to {table_name}")
        
        # Add the tenant column
        op.add_column(
            table_name,
            op.Column(column_name, op.String(255), nullable=False, server_default='unknown')
        )
        
        # Remove server default after adding
        op.alter_column(table_name, column_name, server_default=None)
    
    # Verify column is not nullable
    column_info = None
    for col in inspector.get_columns(table_name):
        if col['name'] == column_name:
            column_info = col
            break
    
    if column_info and column_info['nullable']:
        logger.warning(f"Making {column_name} column NOT NULL in {table_name}")
        op.alter_column(table_name, column_name, nullable=False)
    
    logger.info(f"✅ Tenant column validated for {table_name}")

def ensure_tenant_indexes(table_name: str, additional_columns: List[str] = None) -> None:
    """
    Ensure a table has proper tenant-optimized indexes.
    
    Args:
        table_name: Name of the table
        additional_columns: Additional columns to include in composite indexes
    """
    config = get_environment_config()
    additional_columns = additional_columns or []
    
    if config['skip_validation']:
        logger.info(f"Skipping index validation for {table_name}")
        return
    
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Get existing indexes
    existing_indexes = {idx['name']: idx for idx in inspector.get_indexes(table_name)}
    
    # Required tenant indexes
    required_indexes = [
        {
            'name': f'idx_{table_name}_tenant_id',
            'columns': ['tenant_id'],
            'unique': False
        },
        {
            'name': f'idx_{table_name}_tenant_created',
            'columns': ['tenant_id', 'created_at'],
            'unique': False
        },
    ]
    
    # Add indexes for additional columns
    for col in additional_columns:
        required_indexes.append({
            'name': f'idx_{table_name}_tenant_{col}',
            'columns': ['tenant_id', col],
            'unique': False
        })
    
    # Create missing indexes
    for index_spec in required_indexes:
        index_name = index_spec['name']
        
        if index_name not in existing_indexes:
            try:
                logger.info(f"Creating index {index_name}")
                if index_spec['unique']:
                    op.create_index(
                        index_name, 
                        table_name, 
                        index_spec['columns'],
                        unique=True
                    )
                else:
                    op.create_index(
                        index_name, 
                        table_name, 
                        index_spec['columns']
                    )
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {e}")
        else:
            logger.info(f"Index {index_name} already exists")
    
    logger.info(f"✅ Tenant indexes validated for {table_name}")

def validate_tenant_isolation(table_name: str) -> None:
    """
    Validate and enable tenant isolation features for a table.
    
    Args:
        table_name: Name of the table to enable isolation for
    """
    config = get_environment_config()
    
    if config['skip_validation']:
        logger.info(f"Skipping tenant isolation validation for {table_name}")
        return
    
    connection = op.get_bind()
    
    try:
        # Enable RLS if configured
        if config['enable_rls']:
            enable_rls_policies(table_name, connection)
        
        # Enable audit triggers if configured
        if config['enable_audit_triggers']:
            enable_audit_triggers(table_name, connection)
        
        logger.info(f"✅ Tenant isolation validated for {table_name}")
        
    except Exception as e:
        if config.get('strict_validation', True):
            raise MigrationValidationError(f"Failed to enable tenant isolation for {table_name}: {e}")
        else:
            logger.warning(f"Failed to enable tenant isolation for {table_name}: {e}")

def enable_rls_policies(table_name: str, connection) -> None:
    """Enable Row Level Security policies on a table."""
    logger.info(f"Enabling RLS policies for {table_name}")
    
    # Enable RLS
    connection.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    
    # Create policies
    policies = [
        f"""
        CREATE POLICY IF NOT EXISTS tenant_isolation_select ON {table_name}
        FOR SELECT
        USING (check_tenant_access(tenant_id))
        """,
        f"""
        CREATE POLICY IF NOT EXISTS tenant_isolation_insert ON {table_name}
        FOR INSERT
        WITH CHECK (check_tenant_access(tenant_id))
        """,
        f"""
        CREATE POLICY IF NOT EXISTS tenant_isolation_update ON {table_name}
        FOR UPDATE
        USING (check_tenant_access(tenant_id))
        WITH CHECK (check_tenant_access(tenant_id))
        """,
        f"""
        CREATE POLICY IF NOT EXISTS tenant_isolation_delete ON {table_name}
        FOR DELETE
        USING (check_tenant_access(tenant_id))
        """
    ]
    
    for policy in policies:
        try:
            connection.execute(text(policy))
        except Exception as e:
            logger.warning(f"Failed to create RLS policy for {table_name}: {e}")

def enable_audit_triggers(table_name: str, connection) -> None:
    """Enable audit triggers on a table."""
    logger.info(f"Enabling audit triggers for {table_name}")
    
    triggers = [
        f"""
        CREATE TRIGGER IF NOT EXISTS enforce_tenant_insert_trigger
        BEFORE INSERT ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION enforce_tenant_on_insert()
        """,
        f"""
        CREATE TRIGGER IF NOT EXISTS validate_tenant_update_trigger
        BEFORE UPDATE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION validate_tenant_on_update()
        """
    ]
    
    for trigger in triggers:
        try:
            connection.execute(text(trigger))
        except Exception as e:
            logger.warning(f"Failed to create audit trigger for {table_name}: {e}")

def validate_foreign_key_constraints(table_name: str, foreign_keys: List[Dict[str, str]]) -> None:
    """
    Validate that foreign key constraints are tenant-aware.
    
    Args:
        table_name: Name of the table
        foreign_keys: List of foreign key definitions
    """
    config = get_environment_config()
    
    if config['skip_validation']:
        return
    
    connection = op.get_bind()
    inspector = inspect(connection)
    
    for fk_spec in foreign_keys:
        source_table = table_name
        target_table = fk_spec['target_table']
        source_column = fk_spec['source_column']
        target_column = fk_spec['target_column']
        
        # Check if both tables are tenant-aware
        source_columns = [col['name'] for col in inspector.get_columns(source_table)]
        target_columns = [col['name'] for col in inspector.get_columns(target_table)]
        
        source_has_tenant = 'tenant_id' in source_columns
        target_has_tenant = 'tenant_id' in target_columns
        
        if source_has_tenant and target_has_tenant:
            # Create composite foreign key including tenant_id
            logger.info(f"Creating tenant-aware foreign key from {source_table} to {target_table}")
            
            try:
                op.create_foreign_key(
                    f"fk_{source_table}_{target_table}_tenant",
                    source_table,
                    target_table,
                    [source_column, 'tenant_id'],
                    [target_column, 'tenant_id']
                )
            except Exception as e:
                logger.warning(f"Failed to create tenant-aware foreign key: {e}")
        else:
            logger.warning(
                f"Foreign key between {source_table} and {target_table} may not be tenant-safe"
            )

def validate_unique_constraints(table_name: str, unique_columns: List[List[str]]) -> None:
    """
    Validate that unique constraints include tenant_id.
    
    Args:
        table_name: Name of the table
        unique_columns: List of column lists that should be unique
    """
    config = get_environment_config()
    
    if config['skip_validation']:
        return
    
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Check if table has tenant_id
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    if 'tenant_id' not in columns:
        logger.warning(f"Table {table_name} doesn't have tenant_id column")
        return
    
    for i, column_list in enumerate(unique_columns):
        if 'tenant_id' not in column_list:
            # Create tenant-aware unique constraint
            constraint_name = f"uq_{table_name}_tenant_{'_'.join(column_list)}"
            tenant_aware_columns = ['tenant_id'] + column_list
            
            logger.info(f"Creating tenant-aware unique constraint: {constraint_name}")
            
            try:
                op.create_unique_constraint(
                    constraint_name,
                    table_name,
                    tenant_aware_columns
                )
            except Exception as e:
                logger.warning(f"Failed to create unique constraint {constraint_name}: {e}")

def create_tenant_aware_table(table_name: str, columns: List, **kwargs) -> None:
    """
    Create a table with automatic tenant isolation features.
    
    Args:
        table_name: Name of the table to create
        columns: List of SQLAlchemy Column objects
        **kwargs: Additional arguments for create_table
    """
    config = get_environment_config()
    
    # Ensure tenant_id column exists
    has_tenant_id = any(col.name == 'tenant_id' for col in columns if hasattr(col, 'name'))
    
    if not has_tenant_id and config['require_tenant_column']:
        from sqlalchemy import Column, String
        tenant_column = Column('tenant_id', String(255), nullable=False, index=True)
        columns.insert(1, tenant_column)  # Insert after id column
    
    # Create the table
    op.create_table(table_name, *columns, **kwargs)
    
    # Apply tenant isolation features
    if config['require_tenant_column']:
        ensure_tenant_column(table_name)
        ensure_tenant_indexes(table_name)
        validate_tenant_isolation(table_name)
    
    logger.info(f"✅ Created tenant-aware table: {table_name}")

def migration_safety_check() -> None:
    """
    Perform general migration safety checks.
    """
    config = get_environment_config()
    
    if config['skip_validation']:
        logger.info("Skipping migration safety checks")
        return
    
    connection = op.get_bind()
    
    # Check if tenant isolation functions exist
    try:
        result = connection.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_proc 
                WHERE proname = 'current_tenant_id'
            )
        """)).scalar()
        
        if not result:
            logger.warning("Tenant isolation functions not found - RLS may not work properly")
            
            if config['enable_rls']:
                logger.info("Creating tenant isolation functions...")
                from .tenant_isolation import RLSPolicyManager
                RLSPolicyManager.create_tenant_policy_function(connection.engine)
    
    except Exception as e:
        logger.warning(f"Failed to check tenant isolation functions: {e}")
    
    logger.info("✅ Migration safety check completed")

# Decorator for tenant-aware migrations
def tenant_aware_migration(func):
    """
    Decorator to ensure migration follows tenant isolation best practices.
    """
    def wrapper(*args, **kwargs):
        logger.info("Running tenant-aware migration")
        
        # Run safety checks
        migration_safety_check()
        
        # Execute migration
        result = func(*args, **kwargs)
        
        logger.info("✅ Tenant-aware migration completed")
        return result
    
    return wrapper

# Context manager for tenant-safe operations
class TenantSafeMigration:
    """Context manager for tenant-safe migration operations."""
    
    def __init__(self, require_tenant_context: bool = False):
        self.require_tenant_context = require_tenant_context
        self.config = get_environment_config()
    
    def __enter__(self):
        if not self.config['skip_validation']:
            migration_safety_check()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Migration failed: {exc_val}")
        else:
            logger.info("✅ Migration completed successfully")

# Utility functions for common migration patterns
def add_tenant_aware_column(table_name: str, column_name: str, column_type, **kwargs) -> None:
    """Add a column to a tenant-aware table with proper indexing."""
    op.add_column(table_name, op.Column(column_name, column_type, **kwargs))
    
    # Create tenant-aware index if the column should be indexed
    if kwargs.get('index', False):
        index_name = f"idx_{table_name}_tenant_{column_name}"
        op.create_index(index_name, table_name, ['tenant_id', column_name])

def rename_tenant_aware_table(old_name: str, new_name: str) -> None:
    """Rename a tenant-aware table and update related constraints/indexes."""
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Rename table
    op.rename_table(old_name, new_name)
    
    # Update indexes
    for index in inspector.get_indexes(new_name):
        old_index_name = index['name']
        if old_index_name.startswith(f"idx_{old_name}_"):
            new_index_name = old_index_name.replace(f"idx_{old_name}_", f"idx_{new_name}_")
            op.drop_index(old_index_name, table_name=new_name)
            op.create_index(new_index_name, new_name, index['column_names'])
    
    logger.info(f"✅ Renamed tenant-aware table: {old_name} -> {new_name}")

# Export commonly used functions
__all__ = [
    'ensure_tenant_column',
    'ensure_tenant_indexes', 
    'validate_tenant_isolation',
    'validate_foreign_key_constraints',
    'validate_unique_constraints',
    'create_tenant_aware_table',
    'migration_safety_check',
    'tenant_aware_migration',
    'TenantSafeMigration',
    'add_tenant_aware_column',
    'rename_tenant_aware_table'
]