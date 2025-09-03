"""
Alembic migration helpers and utilities.

Provides utilities for database migrations including:
- Database URL resolution with environment overrides
- Migration filtering callbacks
- Post-migration hook execution
- Schema-aware migration utilities
"""

import importlib
import logging
import os
from pathlib import Path
from typing import Any, Optional, Dict, List, Callable, Union

try:
    from alembic import context
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext
    from alembic.operations import Operations
    ALEMBIC_AVAILABLE = True
except ImportError:
    ALEMBIC_AVAILABLE = False
    context = None
    Config = None
    ScriptDirectory = None
    MigrationContext = None
    Operations = None

import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class AlembicError(Exception):
    """Base exception for Alembic-related errors."""
    pass


def get_alembic_config_url(
    config_url: Optional[str] = None,
    env_var: str = "DATABASE_URL",
    fallback_url: Optional[str] = None,
) -> str:
    """
    Get database URL for Alembic configuration with environment precedence.
    
    Resolution order:
    1. Explicit config_url parameter
    2. Environment variable (DATABASE_URL by default)
    3. Fallback URL parameter
    
    Args:
        config_url: Explicit database URL
        env_var: Environment variable name for URL
        fallback_url: Fallback URL if others not available
        
    Returns:
        Database URL string
        
    Raises:
        AlembicError: If no URL can be resolved
        
    Example:
        # In alembic/env.py
        from dotmac.database.alembic import get_alembic_config_url
        
        config.set_main_option(
            'sqlalchemy.url', 
            get_alembic_config_url()
        )
    """
    # Check explicit parameter first
    if config_url:
        logger.debug(f"Using explicit config URL: {config_url[:20]}...")
        return config_url
    
    # Check environment variable
    env_url = os.getenv(env_var)
    if env_url:
        logger.debug(f"Using URL from {env_var}: {env_url[:20]}...")
        return env_url
    
    # Check fallback
    if fallback_url:
        logger.debug(f"Using fallback URL: {fallback_url[:20]}...")
        return fallback_url
    
    raise AlembicError(
        f"No database URL found. Checked: config_url, {env_var}, fallback_url"
    )


def include_object(
    obj: Any,
    name: str,
    type_: str,
    reflected: bool,
    compare_to: Optional[Any] = None,
    *,
    skip_schemas: Optional[List[str]] = None,
    skip_tables: Optional[List[str]] = None,
    skip_indexes: bool = False,
    skip_views: bool = True,
    schema_patterns: Optional[List[str]] = None,
) -> bool:
    """
    Alembic include_object callback for filtering migration objects.
    
    Provides common filtering patterns for migrations:
    - Skip specific schemas (e.g., information_schema)
    - Skip specific tables (e.g., alembic_version)
    - Skip indexes if desired
    - Skip views by default
    - Include only matching schema patterns
    
    Args:
        obj: SQLAlchemy object being considered
        name: Object name
        type_: Object type ('schema', 'table', 'column', 'index', 'unique_constraint', etc.)
        reflected: Whether object was reflected from database
        compare_to: Object being compared to (for revisions)
        skip_schemas: List of schema names to skip
        skip_tables: List of table names to skip
        skip_indexes: Skip all indexes
        skip_views: Skip database views
        schema_patterns: Only include schemas matching these patterns
        
    Returns:
        True if object should be included in migration
        
    Example:
        # In alembic/env.py
        from dotmac.database.alembic import include_object
        
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=lambda obj, name, type_, reflected, compare_to: 
                include_object(
                    obj, name, type_, reflected, compare_to,
                    skip_schemas=['information_schema', 'pg_catalog'],
                    skip_tables=['spatial_ref_sys'],
                    skip_indexes=True
                )
        )
    """
    # Default schemas to skip
    default_skip_schemas = [
        'information_schema',
        'pg_catalog',
        'pg_toast',
        'pg_temp_1',
        'pg_toast_temp_1'
    ]
    
    skip_schemas = (skip_schemas or []) + default_skip_schemas
    skip_tables = skip_tables or []
    
    # Skip specific schemas
    if type_ == "schema":
        if name in skip_schemas:
            logger.debug(f"Skipping schema: {name}")
            return False
        
        # Check schema patterns if specified
        if schema_patterns:
            import fnmatch
            if not any(fnmatch.fnmatch(name, pattern) for pattern in schema_patterns):
                logger.debug(f"Schema {name} doesn't match patterns: {schema_patterns}")
                return False
    
    # Skip specific tables
    if type_ == "table":
        if name in skip_tables:
            logger.debug(f"Skipping table: {name}")
            return False
        
        # Skip views if requested
        if skip_views and hasattr(obj, 'info') and obj.info.get('is_view'):
            logger.debug(f"Skipping view: {name}")
            return False
    
    # Skip indexes if requested
    if skip_indexes and type_ == "index":
        logger.debug(f"Skipping index: {name}")
        return False
    
    # Skip foreign key constraints on tables we're skipping
    if type_ == "foreign_key_constraint":
        if hasattr(obj, 'referred_table') and obj.referred_table.name in skip_tables:
            logger.debug(f"Skipping foreign key to skipped table: {name}")
            return False
    
    return True


def run_post_migration_hooks(
    config: "Config",
    revision: str,
    hook_modules: Optional[List[str]] = None,
    hook_directory: Optional[Union[str, Path]] = None,
) -> None:
    """
    Execute post-migration hooks from configured modules or directory.
    
    Hooks are Python modules/scripts that should define a function:
    def post_migration_hook(config, revision, context, operations):
        # Custom logic here
        pass
    
    Args:
        config: Alembic configuration
        revision: Migration revision ID
        hook_modules: List of module names to import and execute
        hook_directory: Directory containing hook scripts
        
    Example:
        # In alembic/env.py after migration
        run_post_migration_hooks(
            config,
            revision,
            hook_modules=['myapp.migrations.hooks'],
            hook_directory='alembic/hooks'
        )
        
        # Hook module example (myapp/migrations/hooks.py):
        def post_migration_hook(config, revision, context, operations):
            # Apply RLS policies
            operations.execute("SELECT enable_rls_policies()")
    """
    if not ALEMBIC_AVAILABLE:
        logger.warning("Alembic not available, skipping post-migration hooks")
        return
    
    migration_context = context.get_context()
    operations = Operations(migration_context) if migration_context else None
    
    hooks_executed = 0
    
    # Execute hooks from modules
    if hook_modules:
        for module_name in hook_modules:
            try:
                module = importlib.import_module(module_name)
                
                if hasattr(module, 'post_migration_hook'):
                    logger.info(f"Executing post-migration hook from {module_name}")
                    module.post_migration_hook(config, revision, migration_context, operations)
                    hooks_executed += 1
                else:
                    logger.warning(f"Module {module_name} has no post_migration_hook function")
                    
            except ImportError as e:
                logger.error(f"Failed to import hook module {module_name}: {e}")
            except Exception as e:
                logger.error(f"Error executing hook from {module_name}: {e}")
    
    # Execute hooks from directory
    if hook_directory:
        hook_path = Path(hook_directory)
        
        if hook_path.exists() and hook_path.is_dir():
            # Find all .py files in hook directory
            hook_files = sorted(hook_path.glob("*.py"))
            
            for hook_file in hook_files:
                if hook_file.name.startswith('_'):
                    continue  # Skip private files
                
                try:
                    # Import hook file as module
                    spec = importlib.util.spec_from_file_location(
                        f"migration_hook_{hook_file.stem}",
                        hook_file
                    )
                    
                    if spec and spec.loader:
                        hook_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(hook_module)
                        
                        if hasattr(hook_module, 'post_migration_hook'):
                            logger.info(f"Executing post-migration hook from {hook_file}")
                            hook_module.post_migration_hook(config, revision, migration_context, operations)
                            hooks_executed += 1
                        else:
                            logger.warning(f"Hook file {hook_file} has no post_migration_hook function")
                            
                except Exception as e:
                    logger.error(f"Error executing hook from {hook_file}: {e}")
        else:
            logger.warning(f"Hook directory {hook_directory} not found or not a directory")
    
    logger.info(f"Executed {hooks_executed} post-migration hooks for revision {revision}")


def create_schema_if_not_exists(
    operations: "Operations",
    schema_name: str,
    owner: Optional[str] = None,
) -> None:
    """
    Create schema if it doesn't exist during migration.
    
    Args:
        operations: Alembic operations context
        schema_name: Name of schema to create
        owner: Optional schema owner
        
    Example:
        # In migration file
        from dotmac.database.alembic import create_schema_if_not_exists
        
        def upgrade():
            create_schema_if_not_exists(op, 'tenant_acme')
    """
    if not ALEMBIC_AVAILABLE:
        raise AlembicError("Alembic not available")
    
    try:
        if owner:
            operations.execute(
                f"CREATE SCHEMA IF NOT EXISTS {schema_name} AUTHORIZATION {owner}"
            )
        else:
            operations.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        
        logger.info(f"Created schema: {schema_name}")
        
    except Exception as e:
        logger.error(f"Failed to create schema {schema_name}: {e}")
        raise AlembicError(f"Failed to create schema {schema_name}: {e}") from e


def drop_schema_if_exists(
    operations: "Operations",
    schema_name: str,
    cascade: bool = False,
) -> None:
    """
    Drop schema if it exists during migration.
    
    Args:
        operations: Alembic operations context
        schema_name: Name of schema to drop
        cascade: Whether to use CASCADE
        
    Example:
        # In migration file
        from dotmac.database.alembic import drop_schema_if_exists
        
        def downgrade():
            drop_schema_if_exists(op, 'tenant_acme', cascade=True)
    """
    if not ALEMBIC_AVAILABLE:
        raise AlembicError("Alembic not available")
    
    try:
        cascade_clause = "CASCADE" if cascade else "RESTRICT"
        operations.execute(f"DROP SCHEMA IF EXISTS {schema_name} {cascade_clause}")
        
        logger.info(f"Dropped schema: {schema_name}")
        
    except Exception as e:
        logger.error(f"Failed to drop schema {schema_name}: {e}")
        raise AlembicError(f"Failed to drop schema {schema_name}: {e}") from e


def enable_rls_on_table(
    operations: "Operations",
    table_name: str,
    schema: str = "public",
) -> None:
    """
    Enable Row Level Security on table during migration.
    
    Args:
        operations: Alembic operations context
        table_name: Name of table
        schema: Schema name (default: public)
        
    Example:
        # In migration file
        from dotmac.database.alembic import enable_rls_on_table
        
        def upgrade():
            enable_rls_on_table(op, 'users')
    """
    if not ALEMBIC_AVAILABLE:
        raise AlembicError("Alembic not available")
    
    try:
        operations.execute(f"ALTER TABLE {schema}.{table_name} ENABLE ROW LEVEL SECURITY")
        logger.info(f"Enabled RLS on {schema}.{table_name}")
        
    except Exception as e:
        logger.error(f"Failed to enable RLS on {schema}.{table_name}: {e}")
        raise AlembicError(f"Failed to enable RLS: {e}") from e


def create_rls_policy(
    operations: "Operations",
    policy_name: str,
    table_name: str,
    using_expression: str,
    check_expression: Optional[str] = None,
    schema: str = "public",
    command: str = "ALL",
    role: str = "public",
) -> None:
    """
    Create RLS policy during migration.
    
    Args:
        operations: Alembic operations context
        policy_name: Name of the policy
        table_name: Target table name
        using_expression: USING expression for policy
        check_expression: Optional WITH CHECK expression
        schema: Schema name (default: public)
        command: Policy command (ALL, SELECT, INSERT, UPDATE, DELETE)
        role: Target role (default: public)
        
    Example:
        # In migration file
        from dotmac.database.alembic import create_rls_policy
        
        def upgrade():
            create_rls_policy(
                op,
                'users_tenant_policy',
                'users',
                "tenant_id = current_setting('app.current_tenant_id', true)",
                "tenant_id = current_setting('app.current_tenant_id', true)"
            )
    """
    if not ALEMBIC_AVAILABLE:
        raise AlembicError("Alembic not available")
    
    try:
        policy_sql = f"""
        CREATE POLICY {policy_name} ON {schema}.{table_name}
        FOR {command}
        TO {role}
        USING ({using_expression})
        """
        
        if check_expression:
            policy_sql += f"\nWITH CHECK ({check_expression})"
        
        operations.execute(policy_sql)
        logger.info(f"Created RLS policy {policy_name} on {schema}.{table_name}")
        
    except Exception as e:
        logger.error(f"Failed to create RLS policy {policy_name}: {e}")
        raise AlembicError(f"Failed to create RLS policy: {e}") from e


class MigrationHelpers:
    """
    Collection of migration helper utilities.
    
    Provides common patterns for database migrations including
    schema management, RLS setup, and index creation.
    """
    
    def __init__(self, operations: "Operations"):
        if not ALEMBIC_AVAILABLE:
            raise AlembicError("Alembic not available")
        self.operations = operations
    
    def create_tenant_schema(
        self,
        tenant_id: str,
        schema_prefix: str = "tenant_",
        owner: Optional[str] = None,
    ) -> str:
        """Create tenant-specific schema."""
        schema_name = f"{schema_prefix}{tenant_id}"
        create_schema_if_not_exists(self.operations, schema_name, owner)
        return schema_name
    
    def setup_tenant_rls(
        self,
        table_name: str,
        tenant_column: str = "tenant_id",
        schema: str = "public",
    ) -> None:
        """Setup complete tenant RLS for a table."""
        # Enable RLS
        enable_rls_on_table(self.operations, table_name, schema)
        
        # Create tenant policy
        policy_name = f"{table_name}_tenant_policy"
        using_expr = f"{tenant_column} = current_setting('app.current_tenant_id', true)"
        
        create_rls_policy(
            self.operations,
            policy_name,
            table_name,
            using_expr,
            using_expr,  # Same for WITH CHECK
            schema
        )
    
    def create_indexes_for_tenant_aware_table(
        self,
        table_name: str,
        tenant_column: str = "tenant_id",
        additional_columns: Optional[List[str]] = None,
        schema: str = "public",
    ) -> None:
        """Create standard indexes for tenant-aware tables."""
        # Tenant isolation index
        self.operations.create_index(
            f"idx_{table_name}_{tenant_column}",
            table_name,
            [tenant_column],
            schema=schema if schema != "public" else None
        )
        
        # Composite indexes with tenant_id
        if additional_columns:
            for col in additional_columns:
                self.operations.create_index(
                    f"idx_{table_name}_{tenant_column}_{col}",
                    table_name,
                    [tenant_column, col],
                    schema=schema if schema != "public" else None
                )