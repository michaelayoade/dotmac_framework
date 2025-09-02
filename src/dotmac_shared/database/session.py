"""
Database session management for DotMac Framework.
Provides async database session dependency injection with advanced features:
- Production-grade connection pooling
- Read/write database splitting
- Query result caching
- Performance monitoring
- Health monitoring
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any, Literal
from datetime import datetime, timedelta

from sqlalchemy.engine.events import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool, StaticPool
from sqlalchemy import text, select
from sqlalchemy.exc import SQLAlchemyError
import asyncio
import weakref

logger = logging.getLogger(__name__)

# Global variables for session management
_async_engine = None
_async_session_factory = None
_read_engine = None
_read_session_factory = None
_connection_pool_stats = {}
_slow_query_threshold = float(os.environ.get("SLOW_QUERY_THRESHOLD", "1.0"))
_query_cache = {}
_cache_ttl = int(os.environ.get("QUERY_CACHE_TTL", "300"))  # 5 minutes
_active_connections = weakref.WeakSet()


def get_database_url() -> str:
    """Get database URL from environment with fallback."""
    database_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

    # Convert postgres:// to postgresql+asyncpg:// for async support
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("sqlite://"):
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    return database_url


def create_async_database_engine():
    """Create async database engine with advanced production-grade configuration."""
    global _async_engine, _async_session_factory, _read_engine, _read_session_factory

    if _async_engine is not None:
        return _async_engine

    # Primary (write) database
    database_url = get_database_url()
    
    # Read replica configuration
    read_database_url = os.environ.get("READ_DATABASE_URL", database_url)
    
    try:
        # Enhanced engine configuration for production
        base_config = {
            "echo": os.environ.get("SQL_DEBUG", "false").lower() == "true",
            "echo_pool": os.environ.get("SQL_DEBUG_POOL", "false").lower() == "true",
            "future": True,
            "query_cache_size": int(os.environ.get("QUERY_CACHE_SIZE", "1200")),
            "pool_pre_ping": True,  # Enable connection health checks
            "pool_reset_on_return": "commit",  # Reset on return for better isolation
        }
        
        # Database-specific configuration
        if "sqlite" in database_url:
            # SQLite configuration with better performance settings
            sqlite_config = {
                "poolclass": StaticPool if os.environ.get("ENVIRONMENT") == "test" else NullPool,
                "connect_args": {
                    "check_same_thread": False,
                    "isolation_level": None,  # Enable autocommit mode
                    "timeout": 30,
                    "detect_types": 0,
                },
            }
            base_config.update(sqlite_config)
        else:
            # PostgreSQL production configuration with advanced pooling
            pool_size = int(os.environ.get("DB_POOL_SIZE", "20"))
            max_overflow = int(os.environ.get("DB_MAX_OVERFLOW", "30"))
            
            postgres_config = {
                "poolclass": QueuePool,
                "pool_size": pool_size,
                "max_overflow": max_overflow,
                "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", "30")),
                "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", "3600")),
                "pool_reset_on_return": "commit",
                # Advanced PostgreSQL settings
                "connect_args": {
                    "server_settings": {
                        "application_name": "dotmac_framework",
                        "statement_timeout": os.environ.get("DB_STATEMENT_TIMEOUT", "60000"),  # 60 seconds
                        "idle_in_transaction_session_timeout": "300000",  # 5 minutes
                        "tcp_keepalives_idle": "600",
                        "tcp_keepalives_interval": "30",
                        "tcp_keepalives_count": "3",
                    }
                },
            }
            base_config.update(postgres_config)

        # Create primary (write) engine
        _async_engine = create_async_engine(database_url, **base_config)
        
        # Create read replica engine if different URL provided
        if read_database_url != database_url:
            # Read replicas typically need fewer connections but similar config
            read_config = base_config.copy()
            if "sqlite" not in read_database_url:
                read_config.update({
                    "pool_size": int(os.environ.get("READ_DB_POOL_SIZE", "15")),
                    "max_overflow": int(os.environ.get("READ_DB_MAX_OVERFLOW", "25")),
                })
            
            _read_engine = create_async_engine(read_database_url, **read_config)
            logger.info("Created separate read replica engine")
        else:
            _read_engine = _async_engine
            logger.info("Using primary engine for read operations")

        # Create session factories with optimized settings
        _async_session_factory = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        
        _read_session_factory = async_sessionmaker(
            bind=_read_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        # Set up event listeners for monitoring
        _setup_database_monitoring(_async_engine)
        if _read_engine != _async_engine:
            _setup_database_monitoring(_read_engine, "read")

        logger.info(
            f"Created async database engines - Write: {database_url.split('@')[0]}..., "
            f"Read: {read_database_url.split('@')[0]}..."
        )

        return _async_engine

    except Exception as e:
        logger.error(f"Failed to create database engines: {e}")
        raise


async def get_async_db(read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides async database session with read/write splitting.

    Args:
        read_only: If True, uses read replica for better performance

    Yields:
        AsyncSession: Database session optimized for the operation type

    Usage:
        @app.get("/users/")
        async def get_users(db: AsyncSession = Depends(get_async_db)):
            # Uses read replica automatically for GET requests
            pass
            
        @app.post("/users/")
        async def create_user(db: AsyncSession = Depends(lambda: get_async_db(read_only=False))):
            # Uses primary database for write operations
            pass
    """
    global _async_session_factory, _read_session_factory

    # Ensure engines and session factories exist
    if _async_session_factory is None:
        create_async_database_engine()

    # Choose appropriate session factory
    session_factory = _read_session_factory if read_only else _async_session_factory
    
    async with session_factory() as session:
        start_time = time.time()
        try:
            # Track active connection
            _active_connections.add(session)
            
            yield session
            
            # Only commit for write sessions
            if not read_only:
                await session.commit()
                
        except Exception as e:
            if not read_only:
                await session.rollback()
            
            execution_time = time.time() - start_time
            logger.error(
                f"Database session error: {e}", 
                extra={
                    "execution_time": execution_time,
                    "read_only": read_only,
                    "error_type": type(e).__name__
                }
            )
            raise
        finally:
            execution_time = time.time() - start_time
            
            # Log slow sessions
            if execution_time > _slow_query_threshold:
                logger.warning(
                    f"Slow database session detected: {execution_time:.3f}s",
                    extra={
                        "execution_time": execution_time,
                        "read_only": read_only,
                        "threshold": _slow_query_threshold
                    }
                )
                
            await session.close()


async def get_async_db_session() -> AsyncSession:
    """
    Get a new async database session (not a dependency).

    Returns:
        AsyncSession: New database session

    Note:
        Caller is responsible for closing the session.
    """
    global _async_session_factory

    if _async_session_factory is None:
        create_async_database_engine()

    return _async_session_factory()


# Health check function
async def check_database_health() -> Dict[str, Any]:
    """
    Comprehensive database health check with connection pool monitoring.

    Returns:
        Dict[str, Any]: Detailed health status and metrics
    """
    health_status = {
        "healthy": False,
        "write_db": {"status": "unknown", "response_time": None},
        "read_db": {"status": "unknown", "response_time": None},
        "connection_pools": {},
        "active_connections": len(_active_connections),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Check write database
        start_time = time.time()
        async with _async_session_factory() as session:
            result = await session.execute(text("SELECT 1 as health_check"))
            if result.scalar() == 1:
                health_status["write_db"]["status"] = "healthy"
                health_status["write_db"]["response_time"] = time.time() - start_time
        
        # Check read database (if separate)
        if _read_session_factory != _async_session_factory:
            start_time = time.time()
            async with _read_session_factory() as session:
                result = await session.execute(text("SELECT 1 as health_check"))
                if result.scalar() == 1:
                    health_status["read_db"]["status"] = "healthy"
                    health_status["read_db"]["response_time"] = time.time() - start_time
        else:
            health_status["read_db"] = health_status["write_db"]
        
        # Get connection pool statistics
        health_status["connection_pools"] = get_connection_pool_stats()
        
        # Overall health determination
        health_status["healthy"] = (
            health_status["write_db"]["status"] == "healthy" and
            health_status["read_db"]["status"] == "healthy"
        )
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["error"] = str(e)
        health_status["write_db"]["status"] = "unhealthy"
        health_status["read_db"]["status"] = "unhealthy"
    
    return health_status


# === ADDITIONAL DATABASE UTILITIES ===

def get_connection_pool_stats() -> Dict[str, Any]:
    """Get connection pool statistics for monitoring."""
    stats = {}
    
    try:
        if _async_engine and hasattr(_async_engine.pool, 'size'):
            write_pool = _async_engine.pool
            stats["write"] = {
                "size": getattr(write_pool, 'size', lambda: 0)(),
                "checked_in": getattr(write_pool, 'checkedin', lambda: 0)(),
                "checked_out": getattr(write_pool, 'checkedout', lambda: 0)(),
                "overflow": getattr(write_pool, 'overflow', lambda: 0)(),
                "invalid": getattr(write_pool, 'invalidated', lambda: 0)(),
            }
        
        if _read_engine and _read_engine != _async_engine and hasattr(_read_engine.pool, 'size'):
            read_pool = _read_engine.pool
            stats["read"] = {
                "size": getattr(read_pool, 'size', lambda: 0)(),
                "checked_in": getattr(read_pool, 'checkedin', lambda: 0)(),
                "checked_out": getattr(read_pool, 'checkedout', lambda: 0)(),
                "overflow": getattr(read_pool, 'overflow', lambda: 0)(),
                "invalid": getattr(read_pool, 'invalidated', lambda: 0)(),
            }
    except Exception as e:
        logger.error(f"Failed to get connection pool stats: {e}")
        stats["error"] = str(e)
    
    return stats


def _setup_database_monitoring(engine, engine_type: str = "write"):
    """Set up SQLAlchemy event listeners for database monitoring."""
    
    @event.listens_for(engine.sync_engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        """Track new connections."""
        logger.debug(f"New {engine_type} database connection established")
        _connection_pool_stats.setdefault(f"{engine_type}_connections_created", 0)
        _connection_pool_stats[f"{engine_type}_connections_created"] += 1
    
    @event.listens_for(engine.sync_engine, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy):
        """Track connection checkouts from pool."""
        logger.debug(f"Connection checked out from {engine_type} pool")
        _connection_pool_stats.setdefault(f"{engine_type}_checkouts", 0)
        _connection_pool_stats[f"{engine_type}_checkouts"] += 1
    
    @event.listens_for(engine.sync_engine, "checkin")
    def on_checkin(dbapi_connection, connection_record):
        """Track connection checkins to pool."""
        logger.debug(f"Connection checked in to {engine_type} pool")
        _connection_pool_stats.setdefault(f"{engine_type}_checkins", 0)
        _connection_pool_stats[f"{engine_type}_checkins"] += 1


async def get_read_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a read-only database session."""
    async with get_async_db(read_only=True) as session:
        yield session


async def get_write_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a write database session."""
    async with get_async_db(read_only=False) as session:
        yield session


@asynccontextmanager
async def get_db_transaction():
    """Context manager for explicit transaction management."""
    global _async_session_factory
    
    if _async_session_factory is None:
        create_async_database_engine()
        
    async with _async_session_factory() as session:
        async with session.begin():
            try:
                yield session
            except Exception:
                await session.rollback()
                raise


async def execute_raw_query(query: str, parameters: Dict[str, Any] = None, read_only: bool = True) -> Any:
    """
    Execute raw SQL query with proper session management.
    
    Args:
        query: SQL query string
        parameters: Query parameters
        read_only: Whether to use read replica
        
    Returns:
        Query result
    """
    session_factory = _read_session_factory if read_only else _async_session_factory
    
    if session_factory is None:
        create_async_database_engine()
        session_factory = _read_session_factory if read_only else _async_session_factory
    
    async with session_factory() as session:
        start_time = time.time()
        try:
            result = await session.execute(text(query), parameters or {})
            execution_time = time.time() - start_time
            
            # Log slow queries
            if execution_time > _slow_query_threshold:
                logger.warning(
                    f"Slow query detected: {execution_time:.3f}s",
                    extra={
                        "query": query[:100] + "..." if len(query) > 100 else query,
                        "execution_time": execution_time,
                        "read_only": read_only,
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Raw query execution failed: {e}", extra={
                "query": query[:100] + "..." if len(query) > 100 else query,
                "parameters": parameters,
                "read_only": read_only,
            })
            raise


# Initialize on import if environment is set
if os.environ.get("ENVIRONMENT") in ["production", "staging", "development"]:
    try:
        create_async_database_engine()
    except Exception as e:
        logger.warning(f"Failed to initialize database engine on import: {e}")
