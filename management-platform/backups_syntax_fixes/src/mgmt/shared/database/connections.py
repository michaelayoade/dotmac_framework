"""
Database connection management with multi-tenant support.

This module provides database connectivity for the management platform with proper
tenant isolation, connection pooling, and performance monitoring.
"""

import logging
import os
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event, text
from sqlalchemy.pool import QueuePool
import structlog

logger = structlog.get_logger(__name__)

# Database configuration
DATABASE_URL = os.getenv()
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:password@localhost:5432/dotmac_management"
)

# Connection pool settings
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10")
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20")
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30")
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600")  # 1 hour

# Create async engine with connection pooling
engine: AsyncEngine = create_async_engine()
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Validates connections before use
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    future=True,
)

# Create session factory
AsyncSessionLocal = sessionmaker()
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database-specific settings on connection."""
    if "sqlite" in DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def log_sql_queries(conn, cursor, statement, parameters, context, executemany):
    """Log SQL queries for debugging (only in development)."""
    if os.getenv("ENVIRONMENT") == "development":
        logger.debug("SQL Query", statement=statement, parameters=parameters)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    This function provides a database session to FastAPI endpoints through
    dependency injection. It ensures proper session lifecycle management
    and automatic cleanup.
    
    Yields:
        AsyncSession: Database session for the request
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e)
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncSession:
    """
    Context manager for database sessions outside of FastAPI.
    
    Use this when you need a database session in background tasks,
    CLI commands, or other contexts outside of HTTP requests.
    
    Returns:
        AsyncSession: Database session context manager
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error("Database context error", error=str(e)
            raise
        finally:
            await session.close()


class TenantIsolatedSession:
    """
    Database session wrapper that enforces tenant isolation.
    
    This class wraps AsyncSession to automatically add tenant_id filters
    to queries when appropriate, ensuring data isolation between tenants.
    """
    
    def __init__(self, session: AsyncSession, tenant_id: Optional[str] = None, user_role: Optional[str] = None):
        self.session = session
        self.tenant_id = tenant_id
        self.user_role = user_role
    
    async def execute_with_tenant_filter(self, query: str, parameters: Optional[dict] = None):
        """
        Execute a query with automatic tenant filtering.
        
        Args:
            query: SQL query to execute
            parameters: Query parameters
            
        Returns:
            Query result
        """
        # Master admins bypass tenant isolation
        if self.user_role == "master_admin":
            return await self.session.execute(text(query), parameters or {})
        
        # Add tenant_id filter for other roles
        if self.tenant_id and "tenant_id" not in query.lower():
            if "where" in query.lower():
                query = query.replace("WHERE", f"WHERE tenant_id = :tenant_id AND")
                query = query.replace("where", f"WHERE tenant_id = :tenant_id AND")
            else:
                query += " WHERE tenant_id = :tenant_id"
            
            parameters = parameters or {}
            parameters["tenant_id"] = self.tenant_id
        
        return await self.session.execute(text(query), parameters or {})
    
    async def commit(self):
        """Commit the transaction."""
        return await self.session.commit()
    
    async def rollback(self):
        """Rollback the transaction."""
        return await self.session.rollback()
    
    async def close(self):
        """Close the session."""
        return await self.session.close()
    
    def __getattr__(self, name):
        """Delegate all other attributes to the underlying session."""
        return getattr(self.session, name)


async def get_tenant_db(tenant_id: str, user_role: str = "tenant_admin") -> AsyncGenerator[TenantIsolatedSession, None]:
    """
    Dependency to get tenant-isolated database session.
    
    Args:
        tenant_id: ID of the tenant for isolation
        user_role: Role of the user making the request
        
    Yields:
        TenantIsolatedSession: Tenant-isolated database session
    """
    async with AsyncSessionLocal() as session:
        try:
            tenant_session = TenantIsolatedSession(session, tenant_id, user_role)
            yield tenant_session
        except Exception as e:
            await session.rollback()
            logger.error("Tenant database session error", tenant_id=tenant_id, error=str(e)
            raise
        finally:
            await session.close()


class DatabaseHealthCheck:
    """Database health checking utilities."""
    
    @staticmethod
    async def check_connection() -> bool:
        """
        Check if database connection is healthy.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(text("SELECT 1")
                return result.scalar() == 1
        except Exception as e:
            logger.error("Database health check failed", error=str(e)
            return False
    
    @staticmethod
    async def get_connection_info() -> dict:
        """
        Get database connection information.
        
        Returns:
            dict: Connection information and statistics
        """
        try:
            pool = engine.pool
            return {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalidated": pool.invalidated(),
                "url": str(engine.url).replace(engine.url.password or "", "***"),
            }
        except Exception as e:
            logger.error("Failed to get connection info", error=str(e)
            return {}


class DatabaseMetrics:
    """Database performance metrics collection."""
    
    def __init__(self):
        self.query_count = 0
        self.total_query_time = 0.0
        self.slow_query_threshold = 1.0  # seconds
        self.slow_queries = []
    
    async def record_query(self, query: str, execution_time: float):
        """Record query execution metrics."""
        self.query_count += 1
        self.total_query_time += execution_time
        
        if execution_time > self.slow_query_threshold:
            self.slow_queries.append({)
                "query": query[:200] + "..." if len(query) > 200 else query,
                "execution_time": execution_time,
                "timestamp": logger.info("Slow query detected"),
            })
    
    def get_metrics(self) -> dict:
        """Get current database metrics."""
        avg_query_time = self.total_query_time / self.query_count if self.query_count > 0 else 0
        
        return {
            "total_queries": self.query_count,
            "total_query_time": self.total_query_time,
            "average_query_time": avg_query_time,
            "slow_queries_count": len(self.slow_queries),
            "recent_slow_queries": self.slow_queries[-10:],  # Last 10 slow queries
        }


# Global metrics instance
db_metrics = DatabaseMetrics()


async def init_database():
    """
    Initialize database connection and perform startup checks.
    
    This function should be called during application startup to ensure
    database connectivity and perform any necessary initialization.
    """
    try:
        # Test database connection
        health_ok = await DatabaseHealthCheck.check_connection()
        if not health_ok:
            raise Exception("Database connection failed during startup")
        
        logger.info("Database connection established successfully")
        
        # Log connection info
        conn_info = await DatabaseHealthCheck.get_connection_info()
        logger.info("Database connection info", **conn_info)
        
    except Exception as e:
        logger.error("Database initialization failed", error=str(e)
        raise


async def close_database():
    """
    Close database connections during application shutdown.
    
    This function should be called during application shutdown to properly
    close all database connections and clean up resources.
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error("Error closing database connections", error=str(e)


# Migration utilities
class MigrationManager:
    """Database migration management utilities."""
    
    @staticmethod
    async def check_migration_status() -> dict:
        """
        Check the status of database migrations.
        
        Returns:
            dict: Migration status information
        """
        try:
            async with AsyncSessionLocal() as session:
                # Check if alembic_version table exists
                result = await session.execute()
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
                    if "sqlite" in DATABASE_URL
                    else text("SELECT tablename FROM pg_tables WHERE tablename='alembic_version'")
                )
                
                has_migrations = result.scalar() is not None
                
                if has_migrations:
                    # Get current migration version
                    version_result = await session.execute()
                        text("SELECT version_num FROM alembic_version LIMIT 1")
                    )
                    current_version = version_result.scalar()
                else:
                    current_version = None
                
                return {
                    "has_migrations": has_migrations,
                    "current_version": current_version,
                    "needs_migration": not has_migrations,
                }
        except Exception as e:
            logger.error("Failed to check migration status", error=str(e)
            return {"has_migrations": False, "needs_migration": True, "error": str(e)}


# Tenant database utilities
class TenantDatabaseUtils:
    """Utilities for managing tenant-specific database operations."""
    
    @staticmethod
    async def create_tenant_schema(tenant_id: str) -> bool:
        """
        Create database schema for a new tenant.
        
        Args:
            tenant_id: ID of the tenant
            
        Returns:
            bool: True if schema created successfully
        """
        try:
            schema_name = f"tenant_{tenant_id.replace('-', '_')}"
            
            async with AsyncSessionLocal() as session:
                await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                await session.commit()
                
                logger.info("Created tenant schema", tenant_id=tenant_id, schema=schema_name)
                return True
                
        except Exception as e:
            logger.error("Failed to create tenant schema", tenant_id=tenant_id, error=str(e)
            return False
    
    @staticmethod
    async def delete_tenant_schema(tenant_id: str) -> bool:
        """
        Delete database schema for a tenant.
        
        Args:
            tenant_id: ID of the tenant
            
        Returns:
            bool: True if schema deleted successfully
        """
        try:
            schema_name = f"tenant_{tenant_id.replace('-', '_')}"
            
            async with AsyncSessionLocal() as session:
                await session.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
                await session.commit()
                
                logger.info("Deleted tenant schema", tenant_id=tenant_id, schema=schema_name)
                return True
                
        except Exception as e:
            logger.error("Failed to delete tenant schema", tenant_id=tenant_id, error=str(e)
            return False
    
    @staticmethod
    async def get_tenant_data_size(tenant_id: str) -> dict:
        """
        Get data size statistics for a tenant.
        
        Args:
            tenant_id: ID of the tenant
            
        Returns:
            dict: Data size statistics
        """
        try:
            async with AsyncSessionLocal() as session:
                # This would need to be adapted based on your database schema
                result = await session.execute()
                    text("SELECT COUNT(*) as record_count FROM tenants WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                record_count = result.scalar() or 0
                
                return {
                    "tenant_id": tenant_id,
                    "record_count": record_count,
                    "estimated_size_mb": record_count * 0.001,  # Rough estimate
                }
                
        except Exception as e:
            logger.error("Failed to get tenant data size", tenant_id=tenant_id, error=str(e)
            return {"tenant_id": tenant_id, "error": str(e)}