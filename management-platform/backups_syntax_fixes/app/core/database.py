"""
Core database utilities and transaction management.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from database import get_db, async_session_maker as SessionLocal

logger = logging.getLogger(__name__)


# Re-export get_db from main database module for compatibility
__all__ = ["get_db", "database_transaction", "get_db_session"]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session (alias for get_db)."""
    async for session in get_db():
        yield session


@asynccontextmanager
async def database_transaction(session: Optional[AsyncSession] = None) -> AsyncGenerator[AsyncSession, None]:
    """
    Database transaction context manager.
    
    Provides automatic transaction management with rollback on errors.
    """
    if session is None:
        async with SessionLocal() as db_session:
            try:
                await db_session.begin()
                yield db_session
                await db_session.commit()
            except SQLAlchemyError as e:
                await db_session.rollback()
                logger.error(f"Database transaction error: {e}")
                raise
            except Exception as e:
                await db_session.rollback()
                logger.error(f"Unexpected error in database transaction: {e}")
                raise
    else:
        # Use existing session
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database transaction error: {e}")
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error in database transaction: {e}")
            raise


async def execute_with_retry():
    session: AsyncSession, 
    operation_func,
    max_retries: int = 3,
    retry_delay: float = 1.0
):
    """
    Execute database operation with retry logic.
    
    Args:
        session: Database session
        operation_func: Async function to execute
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    """
    import asyncio
    
    for attempt in range(max_retries + 1):
        try:
            return await operation_func(session)
        except (SQLAlchemyError, ConnectionError) as e:
            if attempt == max_retries:
                logger.error(f"Database operation failed after {max_retries} retries: {e}")
                raise
            
            logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff


async def check_database_health(session: AsyncSession) -> dict:
    """
    Check database health and connectivity.
    
    Returns:
        Dict with health status information
    """
    try:
        # Execute a simple query to test connectivity
        from sqlalchemy import text
        result = await session.execute(text("SELECT 1 as health_check")
        row = result.fetchone()
        
        if row and row[0] == 1:
            return {
                "status": "healthy",
                "message": "Database connection successful",
                "timestamp": logger.name  # This will be replaced with actual timestamp in real implementation
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Database query returned unexpected result",
                "timestamp": logger.name
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database health check failed: {str(e)}",
            "error": str(e),
            "timestamp": logger.name
        }


async def get_database_stats(session: AsyncSession) -> dict:
    """
    Get database statistics and metrics.
    
    Returns:
        Dict with database statistics
    """
    try:
        from sqlalchemy import text
        
        # Get connection info
        connection_info = await session.execute(text("SELECT version()")
        version = connection_info.scalar()
        
        # Get active connections (PostgreSQL specific)
        active_connections = await session.execute(text(""")
            SELECT count(*) 
            FROM pg_stat_activity 
            WHERE state = 'active'
        """)
        active_count = active_connections.scalar()
        
        return {
            "database_version": version,
            "active_connections": active_count,
            "status": "operational"
        }
    except Exception as e:
        logger.warning(f"Failed to get database stats: {e}")
        return {
            "status": "stats_unavailable",
            "error": str(e)
        }