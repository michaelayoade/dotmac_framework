"""
Row-Level Security (RLS) and schema management helpers.

Provides generic database helpers for:
- Setting RLS context variables for tenant/user/IP isolation
- Managing schema search paths for schema-per-tenant patterns
- Creating and managing RLS policies
- Schema creation and management utilities
"""

import logging
from typing import Optional, Union, List, Dict, Any
from ipaddress import IPv4Address, IPv6Address

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from .types import TenantIdType, UserIdType

logger = logging.getLogger(__name__)


class RLSError(Exception):
    """Raised when RLS operations fail."""
    pass


class SchemaManagementError(Exception):
    """Raised when schema management operations fail."""
    pass


# Context variable names for RLS
RLS_TENANT_ID = "app.current_tenant_id"
RLS_USER_ID = "app.current_user_id"
RLS_CLIENT_IP = "app.client_ip"
RLS_REQUEST_ID = "app.request_id"
RLS_SESSION_ID = "app.session_id"


async def set_rls_context(
    session: AsyncSession,
    *,
    tenant_id: Optional[TenantIdType] = None,
    user_id: Optional[UserIdType] = None,
    client_ip: Optional[Union[str, IPv4Address, IPv6Address]] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """
    Set RLS context variables for the current session.
    
    These variables can be used in RLS policies to enforce
    tenant isolation, user-level security, and audit trails.
    
    Args:
        session: AsyncSession instance
        tenant_id: Current tenant identifier
        user_id: Current user identifier  
        client_ip: Client IP address for audit/security
        request_id: Request correlation ID
        session_id: Session identifier
        
    Example:
        await set_rls_context(
            session,
            tenant_id="tenant123",
            user_id="user456",
            client_ip="192.168.1.100"
        )
        
        # RLS policies can now use:
        # current_setting('app.current_tenant_id')
        # current_setting('app.current_user_id') 
        # current_setting('app.client_ip')
    """
    try:
        # Set tenant context
        if tenant_id is not None:
            await session.execute(
                text("SELECT set_config(:name, :value, true)"),
                {"name": RLS_TENANT_ID, "value": str(tenant_id)}
            )
            logger.debug(f"Set RLS tenant_id: {tenant_id}")
        
        # Set user context
        if user_id is not None:
            await session.execute(
                text("SELECT set_config(:name, :value, true)"),
                {"name": RLS_USER_ID, "value": str(user_id)}
            )
            logger.debug(f"Set RLS user_id: {user_id}")
        
        # Set client IP context
        if client_ip is not None:
            await session.execute(
                text("SELECT set_config(:name, :value, true)"),
                {"name": RLS_CLIENT_IP, "value": str(client_ip)}
            )
            logger.debug(f"Set RLS client_ip: {client_ip}")
        
        # Set request ID context
        if request_id is not None:
            await session.execute(
                text("SELECT set_config(:name, :value, true)"),
                {"name": RLS_REQUEST_ID, "value": str(request_id)}
            )
            logger.debug(f"Set RLS request_id: {request_id}")
        
        # Set session ID context
        if session_id is not None:
            await session.execute(
                text("SELECT set_config(:name, :value, true)"),
                {"name": RLS_SESSION_ID, "value": str(session_id)}
            )
            logger.debug(f"Set RLS session_id: {session_id}")
            
    except Exception as e:
        logger.error(f"Failed to set RLS context: {e}")
        raise RLSError(f"Failed to set RLS context: {e}") from e


async def get_rls_context(session: AsyncSession) -> Dict[str, Optional[str]]:
    """
    Get current RLS context variables.
    
    Args:
        session: AsyncSession instance
        
    Returns:
        Dictionary of current RLS context values
    """
    context = {}
    context_vars = [
        ("tenant_id", RLS_TENANT_ID),
        ("user_id", RLS_USER_ID), 
        ("client_ip", RLS_CLIENT_IP),
        ("request_id", RLS_REQUEST_ID),
        ("session_id", RLS_SESSION_ID),
    ]
    
    try:
        for key, var_name in context_vars:
            result = await session.execute(
                text("SELECT current_setting(:name, true)"),
                {"name": var_name}
            )
            value = result.scalar()
            context[key] = value if value != "" else None
            
    except Exception as e:
        logger.error(f"Failed to get RLS context: {e}")
        raise RLSError(f"Failed to get RLS context: {e}") from e
    
    return context


async def clear_rls_context(session: AsyncSession) -> None:
    """
    Clear all RLS context variables.
    
    Args:
        session: AsyncSession instance
    """
    context_vars = [RLS_TENANT_ID, RLS_USER_ID, RLS_CLIENT_IP, RLS_REQUEST_ID, RLS_SESSION_ID]
    
    try:
        for var_name in context_vars:
            await session.execute(
                text("SELECT set_config(:name, '', true)"),
                {"name": var_name}
            )
        
        logger.debug("Cleared all RLS context variables")
        
    except Exception as e:
        logger.error(f"Failed to clear RLS context: {e}")
        raise RLSError(f"Failed to clear RLS context: {e}") from e


async def set_schema_search_path(
    session: AsyncSession,
    *,
    tenant_id: TenantIdType,
    schema_prefix: str = "tenant_",
    include_public: bool = True,
    additional_schemas: Optional[List[str]] = None,
) -> None:
    """
    Set schema search path for schema-per-tenant isolation.
    
    Args:
        session: AsyncSession instance
        tenant_id: Tenant identifier for schema selection
        schema_prefix: Prefix for tenant schemas (default: "tenant_")
        include_public: Include public schema in search path
        additional_schemas: Additional schemas to include
        
    Example:
        await set_schema_search_path(session, tenant_id="acme")
        # Sets search path to: tenant_acme, public
        
        await set_schema_search_path(
            session, 
            tenant_id="acme",
            additional_schemas=["shared", "analytics"]  
        )
        # Sets search path to: tenant_acme, shared, analytics, public
    """
    try:
        # Build schema list
        schemas = [f"{schema_prefix}{tenant_id}"]
        
        if additional_schemas:
            schemas.extend(additional_schemas)
        
        if include_public:
            schemas.append("public")
        
        # Set search path
        search_path = ", ".join(schemas)
        await session.execute(
            text(f"SET search_path TO {search_path}")
        )
        
        logger.debug(f"Set schema search path: {search_path}")
        
    except Exception as e:
        logger.error(f"Failed to set schema search path: {e}")
        raise SchemaManagementError(f"Failed to set schema search path: {e}") from e


async def get_current_schema_search_path(session: AsyncSession) -> List[str]:
    """
    Get current schema search path.
    
    Args:
        session: AsyncSession instance
        
    Returns:
        List of schemas in current search path
    """
    try:
        result = await session.execute(text("SHOW search_path"))
        search_path = result.scalar()
        
        # Parse schema list (handle quoted identifiers)
        schemas = [s.strip().strip('"') for s in search_path.split(',')]
        
        return schemas
        
    except Exception as e:
        logger.error(f"Failed to get schema search path: {e}")
        raise SchemaManagementError(f"Failed to get schema search path: {e}") from e


async def reset_schema_search_path(session: AsyncSession) -> None:
    """
    Reset schema search path to default (public).
    
    Args:
        session: AsyncSession instance
    """
    try:
        await session.execute(text("SET search_path TO public"))
        logger.debug("Reset schema search path to public")
        
    except Exception as e:
        logger.error(f"Failed to reset schema search path: {e}")
        raise SchemaManagementError(f"Failed to reset schema search path: {e}") from e


async def create_tenant_schema(
    session: AsyncSession,
    tenant_id: TenantIdType,
    schema_prefix: str = "tenant_",
    owner: Optional[str] = None,
) -> str:
    """
    Create a new tenant schema.
    
    Args:
        session: AsyncSession instance
        tenant_id: Tenant identifier
        schema_prefix: Schema name prefix
        owner: Optional schema owner (defaults to current user)
        
    Returns:
        Created schema name
    """
    schema_name = f"{schema_prefix}{tenant_id}"
    
    try:
        # Create schema
        if owner:
            await session.execute(
                text(f"CREATE SCHEMA IF NOT EXISTS {schema_name} AUTHORIZATION {owner}")
            )
        else:
            await session.execute(
                text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            )
        
        logger.info(f"Created tenant schema: {schema_name}")
        return schema_name
        
    except Exception as e:
        logger.error(f"Failed to create tenant schema {schema_name}: {e}")
        raise SchemaManagementError(f"Failed to create tenant schema: {e}") from e


async def drop_tenant_schema(
    session: AsyncSession,
    tenant_id: TenantIdType,
    schema_prefix: str = "tenant_",
    cascade: bool = False,
) -> None:
    """
    Drop a tenant schema.
    
    Args:
        session: AsyncSession instance
        tenant_id: Tenant identifier
        schema_prefix: Schema name prefix
        cascade: Drop cascade (removes all objects in schema)
    """
    schema_name = f"{schema_prefix}{tenant_id}"
    
    try:
        cascade_clause = "CASCADE" if cascade else "RESTRICT"
        await session.execute(
            text(f"DROP SCHEMA IF EXISTS {schema_name} {cascade_clause}")
        )
        
        logger.info(f"Dropped tenant schema: {schema_name}")
        
    except Exception as e:
        logger.error(f"Failed to drop tenant schema {schema_name}: {e}")
        raise SchemaManagementError(f"Failed to drop tenant schema: {e}") from e


async def list_tenant_schemas(
    session: AsyncSession,
    schema_prefix: str = "tenant_",
) -> List[str]:
    """
    List all tenant schemas.
    
    Args:
        session: AsyncSession instance
        schema_prefix: Schema name prefix to filter
        
    Returns:
        List of tenant schema names
    """
    try:
        result = await session.execute(
            text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name LIKE :prefix
                ORDER BY schema_name
            """),
            {"prefix": f"{schema_prefix}%"}
        )
        
        schemas = [row[0] for row in result.fetchall()]
        logger.debug(f"Found {len(schemas)} tenant schemas")
        
        return schemas
        
    except Exception as e:
        logger.error(f"Failed to list tenant schemas: {e}")
        raise SchemaManagementError(f"Failed to list tenant schemas: {e}") from e


async def copy_schema_structure(
    session: AsyncSession,
    source_schema: str,
    target_schema: str,
    include_data: bool = False,
) -> None:
    """
    Copy schema structure from source to target.
    
    Args:
        session: AsyncSession instance
        source_schema: Source schema name
        target_schema: Target schema name  
        include_data: Copy data along with structure
    """
    try:
        # First ensure target schema exists
        await session.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {target_schema}")
        )
        
        # Get all tables in source schema
        result = await session.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema
                AND table_type = 'BASE TABLE'
            """),
            {"schema": source_schema}
        )
        
        tables = [row[0] for row in result.fetchall()]
        
        # Copy each table structure
        for table_name in tables:
            if include_data:
                await session.execute(
                    text(f"""
                        CREATE TABLE {target_schema}.{table_name} 
                        (LIKE {source_schema}.{table_name} INCLUDING ALL)
                    """)
                )
                await session.execute(
                    text(f"""
                        INSERT INTO {target_schema}.{table_name}
                        SELECT * FROM {source_schema}.{table_name}
                    """)
                )
            else:
                await session.execute(
                    text(f"""
                        CREATE TABLE {target_schema}.{table_name} 
                        (LIKE {source_schema}.{table_name} INCLUDING ALL)
                    """)
                )
        
        logger.info(f"Copied {len(tables)} tables from {source_schema} to {target_schema}")
        
    except Exception as e:
        logger.error(f"Failed to copy schema structure: {e}")
        raise SchemaManagementError(f"Failed to copy schema structure: {e}") from e


class RLSPolicyManager:
    """
    Manager for creating and managing RLS policies.
    
    Provides helpers for common RLS policy patterns.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def enable_rls(self, table_name: str, schema: str = "public") -> None:
        """Enable RLS on a table."""
        try:
            await self.session.execute(
                text(f"ALTER TABLE {schema}.{table_name} ENABLE ROW LEVEL SECURITY")
            )
            logger.info(f"Enabled RLS on {schema}.{table_name}")
        except Exception as e:
            raise RLSError(f"Failed to enable RLS on {table_name}: {e}") from e
    
    async def disable_rls(self, table_name: str, schema: str = "public") -> None:
        """Disable RLS on a table."""
        try:
            await self.session.execute(
                text(f"ALTER TABLE {schema}.{table_name} DISABLE ROW LEVEL SECURITY")
            )
            logger.info(f"Disabled RLS on {schema}.{table_name}")
        except Exception as e:
            raise RLSError(f"Failed to disable RLS on {table_name}: {e}") from e
    
    async def create_tenant_policy(
        self,
        table_name: str,
        tenant_column: str = "tenant_id",
        schema: str = "public",
        policy_name: Optional[str] = None,
    ) -> None:
        """
        Create a tenant isolation RLS policy.
        
        Args:
            table_name: Table name
            tenant_column: Column containing tenant ID
            schema: Schema name
            policy_name: Custom policy name
        """
        if policy_name is None:
            policy_name = f"{table_name}_tenant_policy"
        
        try:
            await self.session.execute(
                text(f"""
                    CREATE POLICY {policy_name} ON {schema}.{table_name}
                    FOR ALL
                    TO public
                    USING ({tenant_column} = current_setting('{RLS_TENANT_ID}', true))
                    WITH CHECK ({tenant_column} = current_setting('{RLS_TENANT_ID}', true))
                """)
            )
            logger.info(f"Created tenant policy {policy_name} on {schema}.{table_name}")
            
        except Exception as e:
            raise RLSError(f"Failed to create tenant policy: {e}") from e
    
    async def create_user_policy(
        self,
        table_name: str,
        user_column: str = "user_id",
        schema: str = "public",
        policy_name: Optional[str] = None,
    ) -> None:
        """
        Create a user-level RLS policy.
        
        Args:
            table_name: Table name
            user_column: Column containing user ID
            schema: Schema name
            policy_name: Custom policy name
        """
        if policy_name is None:
            policy_name = f"{table_name}_user_policy"
        
        try:
            await self.session.execute(
                text(f"""
                    CREATE POLICY {policy_name} ON {schema}.{table_name}
                    FOR ALL
                    TO public
                    USING ({user_column} = current_setting('{RLS_USER_ID}', true))
                    WITH CHECK ({user_column} = current_setting('{RLS_USER_ID}', true))
                """)
            )
            logger.info(f"Created user policy {policy_name} on {schema}.{table_name}")
            
        except Exception as e:
            raise RLSError(f"Failed to create user policy: {e}") from e
    
    async def drop_policy(
        self,
        policy_name: str,
        table_name: str,
        schema: str = "public",
    ) -> None:
        """Drop an RLS policy."""
        try:
            await self.session.execute(
                text(f"DROP POLICY IF EXISTS {policy_name} ON {schema}.{table_name}")
            )
            logger.info(f"Dropped policy {policy_name} from {schema}.{table_name}")
            
        except Exception as e:
            raise RLSError(f"Failed to drop policy {policy_name}: {e}") from e