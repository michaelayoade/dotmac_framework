"""
Database helpers for tenant isolation and multi-tenancy patterns.

Provides support for:
- Row-Level Security (RLS) with automatic tenant filtering
- Schema-per-tenant database isolation
- Database-per-tenant patterns
- Tenant-aware session management
"""

from typing import Optional, Dict, Any, AsyncContextManager, Union, List
from contextlib import asynccontextmanager
from enum import Enum
import asyncio

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy import text, MetaData, Table, Column, String, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import Engine
from loguru import logger

from .identity import TenantContext, get_current_tenant
from .config import TenantConfig, TenantDatabaseStrategy
from .exceptions import TenantContextError, TenantSecurityError


class TenantDatabaseManager:
    """
    Manages tenant-aware database operations and isolation strategies.
    
    Supports multiple tenancy patterns:
    - Shared database with RLS (Row-Level Security)
    - Schema-per-tenant within single database
    - Database-per-tenant with connection routing
    """
    
    def __init__(
        self, 
        config: TenantConfig,
        default_engine: Optional[AsyncEngine] = None
    ):
        self.config = config
        self.default_engine = default_engine
        self._tenant_engines: Dict[str, AsyncEngine] = {}
        self._rls_enabled_tables: Dict[str, str] = {}  # table_name -> tenant_column
        self._session_factory = None
        
        if default_engine:
            self._session_factory = sessionmaker(
                bind=default_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
    
    @asynccontextmanager
    async def get_tenant_aware_session(
        self, 
        tenant_context: Optional[TenantContext] = None
    ) -> AsyncContextManager[AsyncSession]:
        """
        Get a database session with tenant context applied.
        
        Args:
            tenant_context: Explicit tenant context (uses current if None)
            
        Yields:
            AsyncSession configured for tenant isolation
            
        Raises:
            TenantContextError: If no tenant context available
        """
        if not tenant_context:
            tenant_context = get_current_tenant()
            if not tenant_context:
                raise TenantContextError("No tenant context available for database session")
        
        tenant_id = tenant_context.tenant_id
        strategy = self.config.database_strategy
        
        if strategy == TenantDatabaseStrategy.RLS:
            async with self._get_rls_session(tenant_id) as session:
                yield session
                
        elif strategy == TenantDatabaseStrategy.SCHEMA_PER_TENANT:
            async with self._get_schema_session(tenant_id) as session:
                yield session
                
        elif strategy == TenantDatabaseStrategy.DATABASE_PER_TENANT:
            async with self._get_database_session(tenant_id) as session:
                yield session
                
        else:  # TenantDatabaseStrategy.SHARED
            async with self._get_shared_session() as session:
                yield session
    
    @asynccontextmanager
    async def _get_rls_session(self, tenant_id: str) -> AsyncContextManager[AsyncSession]:
        """Get RLS-enabled session with tenant context."""
        if not self._session_factory:
            raise RuntimeError("No default engine configured for RLS sessions")
        
        async with self._session_factory() as session:
            try:
                # Set tenant context for RLS
                await session.execute(
                    text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                    {"tenant_id": tenant_id}
                )
                
                logger.debug(f"RLS session created for tenant: {tenant_id}")
                yield session
                
            except Exception as e:
                logger.error(f"RLS session error for tenant {tenant_id}: {e}")
                await session.rollback()
                raise
            finally:
                # Clear tenant context
                try:
                    await session.execute(
                        text("SELECT set_config('app.current_tenant_id', '', true)")
                    )
                except Exception:
                    pass  # Ignore cleanup errors
    
    @asynccontextmanager
    async def _get_schema_session(self, tenant_id: str) -> AsyncContextManager[AsyncSession]:
        """Get session configured for tenant-specific schema."""
        if not self._session_factory:
            raise RuntimeError("No default engine configured for schema sessions")
        
        schema_name = f"{self.config.tenant_schema_prefix}{tenant_id}"
        
        async with self._session_factory() as session:
            try:
                # Set search path to tenant schema
                await session.execute(
                    text(f"SET search_path TO {schema_name}, public")
                )
                
                logger.debug(f"Schema session created for tenant: {tenant_id} (schema: {schema_name})")
                yield session
                
            except Exception as e:
                logger.error(f"Schema session error for tenant {tenant_id}: {e}")
                await session.rollback()
                raise
            finally:
                # Reset search path
                try:
                    await session.execute(text("SET search_path TO public"))
                except Exception:
                    pass
    
    @asynccontextmanager
    async def _get_database_session(self, tenant_id: str) -> AsyncContextManager[AsyncSession]:
        """Get session for tenant-specific database."""
        # Get or create tenant-specific engine
        engine = await self._get_tenant_engine(tenant_id)
        
        session_factory = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        async with session_factory() as session:
            try:
                logger.debug(f"Database session created for tenant: {tenant_id}")
                yield session
            except Exception as e:
                logger.error(f"Database session error for tenant {tenant_id}: {e}")
                await session.rollback()
                raise
    
    @asynccontextmanager
    async def _get_shared_session(self) -> AsyncContextManager[AsyncSession]:
        """Get regular shared session (no tenant isolation)."""
        if not self._session_factory:
            raise RuntimeError("No default engine configured")
        
        async with self._session_factory() as session:
            yield session
    
    async def _get_tenant_engine(self, tenant_id: str) -> AsyncEngine:
        """Get or create engine for tenant-specific database."""
        if tenant_id not in self._tenant_engines:
            # This would need to be configured with actual tenant database URLs
            # For now, using the default engine as fallback
            if self.default_engine:
                self._tenant_engines[tenant_id] = self.default_engine
            else:
                raise RuntimeError(f"No engine configuration for tenant: {tenant_id}")
        
        return self._tenant_engines[tenant_id]
    
    async def setup_rls(
        self,
        engine: AsyncEngine,
        table_name: str,
        tenant_column: str = "tenant_id"
    ) -> bool:
        """
        Setup Row-Level Security for a table.
        
        Args:
            engine: Database engine
            table_name: Name of table to enable RLS
            tenant_column: Column containing tenant ID
            
        Returns:
            True if RLS was successfully enabled
        """
        try:
            async with engine.begin() as conn:
                # Enable RLS on table
                await conn.execute(
                    text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
                )
                
                # Create policy for tenant isolation
                policy_name = f"{table_name}_tenant_isolation"
                await conn.execute(text(f"""
                    CREATE POLICY {policy_name} ON {table_name}
                    FOR ALL
                    TO public
                    USING ({tenant_column} = current_setting('app.current_tenant_id'))
                    WITH CHECK ({tenant_column} = current_setting('app.current_tenant_id'))
                """))
                
                # Track RLS-enabled table
                self._rls_enabled_tables[table_name] = tenant_column
                
                logger.info(f"RLS enabled for table {table_name} with tenant column {tenant_column}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to setup RLS for table {table_name}: {e}")
            return False
    
    async def create_tenant_schema(
        self,
        engine: AsyncEngine,
        tenant_id: str,
        copy_from_template: bool = True
    ) -> bool:
        """
        Create schema for tenant.
        
        Args:
            engine: Database engine
            tenant_id: Tenant identifier
            copy_from_template: Copy structure from template schema
            
        Returns:
            True if schema was created successfully
        """
        schema_name = f"{self.config.tenant_schema_prefix}{tenant_id}"
        
        try:
            async with engine.begin() as conn:
                # Create schema
                await conn.execute(
                    text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                )
                
                # Copy from template if requested
                if copy_from_template:
                    await self._copy_schema_structure(
                        conn, "template", schema_name
                    )
                
                logger.info(f"Created schema for tenant: {tenant_id} ({schema_name})")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create schema for tenant {tenant_id}: {e}")
            return False
    
    async def _copy_schema_structure(
        self,
        conn,
        source_schema: str,
        target_schema: str
    ):
        """Copy database structure from source to target schema."""
        # This is a simplified implementation
        # In practice, you'd need more sophisticated schema copying
        tables_query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = :schema
        """)
        
        result = await conn.execute(tables_query, {"schema": source_schema})
        tables = result.fetchall()
        
        for table_row in tables:
            table_name = table_row[0]
            await conn.execute(text(f"""
                CREATE TABLE {target_schema}.{table_name} 
                (LIKE {source_schema}.{table_name} INCLUDING ALL)
            """))
    
    def add_tenant_engine(self, tenant_id: str, engine: AsyncEngine):
        """Add engine for specific tenant (database-per-tenant pattern)."""
        self._tenant_engines[tenant_id] = engine
    
    def get_rls_enabled_tables(self) -> Dict[str, str]:
        """Get mapping of RLS-enabled tables to their tenant columns."""
        return self._rls_enabled_tables.copy()
    
    async def validate_tenant_data_isolation(
        self,
        tenant_id: str,
        table_name: str,
        sample_size: int = 100
    ) -> Dict[str, Any]:
        """
        Validate that tenant data isolation is working correctly.
        
        Args:
            tenant_id: Tenant to validate
            table_name: Table to check
            sample_size: Number of records to sample
            
        Returns:
            Validation results
        """
        results = {
            "tenant_id": tenant_id,
            "table_name": table_name,
            "isolation_working": False,
            "total_records": 0,
            "tenant_records": 0,
            "foreign_records": 0,
            "errors": []
        }
        
        try:
            async with self.get_tenant_aware_session() as session:
                # Get total records in table
                total_result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                )
                results["total_records"] = total_result.scalar()
                
                # Check if all records belong to current tenant
                if table_name in self._rls_enabled_tables:
                    tenant_column = self._rls_enabled_tables[table_name]
                    tenant_result = await session.execute(
                        text(f"SELECT COUNT(*) FROM {table_name} WHERE {tenant_column} = :tenant_id"),
                        {"tenant_id": tenant_id}
                    )
                    results["tenant_records"] = tenant_result.scalar()
                    
                    # In RLS setup, we should only see tenant records
                    results["isolation_working"] = (
                        results["total_records"] == results["tenant_records"]
                    )
        
        except Exception as e:
            results["errors"].append(str(e))
            logger.error(f"Tenant isolation validation failed: {e}")
        
        return results


# Convenience functions for common operations

@asynccontextmanager
async def get_tenant_aware_session(
    tenant_context: Optional[TenantContext] = None
) -> AsyncContextManager[AsyncSession]:
    """
    Convenience function to get tenant-aware database session.
    
    Note: Requires TenantDatabaseManager to be configured at application level.
    """
    # This would need to be injected/configured at application startup
    manager = getattr(get_tenant_aware_session, '_manager', None)
    if not manager:
        raise RuntimeError("TenantDatabaseManager not configured. Call configure_tenant_database() first.")
    
    async with manager.get_tenant_aware_session(tenant_context) as session:
        yield session


def configure_tenant_database(
    config: TenantConfig,
    default_engine: Optional[AsyncEngine] = None
) -> TenantDatabaseManager:
    """
    Configure tenant database management.
    
    Args:
        config: Tenant configuration
        default_engine: Default database engine
        
    Returns:
        Configured TenantDatabaseManager
    """
    manager = TenantDatabaseManager(config, default_engine)
    
    # Store manager for convenience functions
    get_tenant_aware_session._manager = manager
    
    return manager


async def setup_rls_for_table(
    engine: AsyncEngine,
    table_name: str,
    tenant_column: str = "tenant_id"
) -> bool:
    """
    Convenience function to setup RLS for a table.
    
    Args:
        engine: Database engine
        table_name: Table name
        tenant_column: Tenant ID column name
        
    Returns:
        True if successful
    """
    config = TenantConfig()  # Use default config
    manager = TenantDatabaseManager(config, engine)
    return await manager.setup_rls(engine, table_name, tenant_column)


# SQLAlchemy event listeners for automatic tenant filtering

def setup_automatic_tenant_filtering(engine: Engine):
    """
    Setup automatic tenant filtering using SQLAlchemy events.
    
    This adds tenant_id conditions to all queries automatically.
    """
    
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Add tenant filtering to queries."""
        current_tenant = get_current_tenant()
        if current_tenant and not executemany:
            # This is a simplified implementation
            # In practice, you'd need more sophisticated query modification
            if "SELECT" in statement.upper() and "WHERE" not in statement.upper():
                statement = statement + " WHERE tenant_id = %(tenant_id)s"
                if isinstance(parameters, dict):
                    parameters["tenant_id"] = current_tenant.tenant_id
                else:
                    parameters = list(parameters) + [current_tenant.tenant_id]
        
        return statement, parameters