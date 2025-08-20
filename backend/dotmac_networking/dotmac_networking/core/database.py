"""
Database connection management for PostgreSQL.
"""

import asyncio
import asyncpg
import os
from typing import Optional
from contextlib import asynccontextmanager


class DatabaseManager:
    """Manages PostgreSQL connection pool."""
    
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
    
    @property
    def database_url(self) -> str:
        """Get database URL from environment."""
        return os.getenv(
            'DATABASE_URL', 
            'postgresql://dotmac:dotmac_secure_password@localhost:5432/dotmac_networking'
        )
    
    async def initialize_pool(self, min_connections: int = 5, max_connections: int = 20) -> None:
        """Initialize connection pool."""
        async with self._lock:
            if self._pool is None:
                self._pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=min_connections,
                    max_size=max_connections,
                    command_timeout=30
                )
    
    async def close_pool(self) -> None:
        """Close connection pool."""
        async with self._lock:
            if self._pool is not None:
                await self._pool.close()
                self._pool = None
    
    @property
    def pool(self) -> asyncpg.Pool:
        """Get connection pool."""
        if self._pool is None:
            raise RuntimeError("Database pool not initialized. Call initialize_pool() first.")
        return self._pool
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool."""
        async with self.pool.acquire() as conn:
            yield conn
    
    async def execute_migration(self, migration_sql: str) -> None:
        """Execute database migration."""
        async with self.get_connection() as conn:
            await conn.execute(migration_sql)
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")
                return True
        except Exception:
            return False


# Global database manager instance
db_manager = DatabaseManager()