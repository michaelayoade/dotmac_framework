"""
Platform Database SDK - Centralized database access for all Dotmac planes

Provides unified database operations with connection pooling, transaction management,
and multi-tenant support. Used by all other planes for data persistence.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


class DatabaseSDK:
    """
    Platform Database SDK providing unified database access across all Dotmac planes.

    Features:
    - Connection pooling and management
    - Transaction support with rollback
    - Multi-tenant data isolation
    - Both sync and async operations
    - Query builder helpers
    - Migration support
    """

    def __init__(self, database_url: str, tenant_id: str | None = None):
        self.database_url = database_url
        self.tenant_id = tenant_id
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None
        self.metadata = MetaData()

    def _get_engine(self):
        """Get or create synchronous database engine."""
        if self._engine is None:
            self._engine = create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False,
            )
            self._session_factory = sessionmaker(bind=self._engine)
        return self._engine

    def _get_async_engine(self):
        """Get or create asynchronous database engine."""
        if self._async_engine is None:
            # Convert sync URL to async if needed
            async_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            self._async_engine = create_async_engine(
                async_url, pool_size=10, max_overflow=20, pool_pre_ping=True, echo=False
            )
            self._async_session_factory = async_sessionmaker(bind=self._async_engine)
        return self._async_engine

    @contextmanager
    def get_session(self) -> Session:
        """Get synchronous database session with automatic cleanup."""
        engine = self._get_engine()
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=engine)

        session = self._session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get asynchronous database session with automatic cleanup."""
        engine = self._get_async_engine()
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(bind=engine)

        session = self._async_session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    def _add_tenant_filter(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> tuple[str, tuple[Any, ...]]:
        """Add tenant filtering to query if tenant_id is set."""
        if self.tenant_id and "tenant_id" not in query.lower():
            # Simple tenant filtering - can be enhanced based on table structure
            if "WHERE" in query.upper():
                query += " AND tenant_id = :tenant_id"
            else:
                query += " WHERE tenant_id = :tenant_id"

            params = params or ()
            params = params + (self.tenant_id,)

        return query, params

    def exec(self, query: str, params: tuple[Any, ...] | None = None) -> bool:
        """Execute a statement (INSERT/UPDATE/DELETE) synchronously."""
        try:
            query, params = self._add_tenant_filter(query, params)

            with self.get_session() as session:
                session.execute(text(query), params or ())
                session.commit()
                return True
        except Exception as e:
            logger.error(f"DatabaseSDK.exec failed: {e}")
            return False

    async def exec_async(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> bool:
        """Execute a statement (INSERT/UPDATE/DELETE) asynchronously."""
        try:
            query, params = self._add_tenant_filter(query, params)

            async with self.get_async_session() as session:
                await session.execute(text(query), params or ())
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"DatabaseSDK.exec_async failed: {e}")
            return False

    def query(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Run a SELECT and return rows as dicts synchronously."""
        try:
            query, params = self._add_tenant_filter(query, params)

            with self.get_session() as session:
                result = session.execute(text(query), params or ())
                columns = list(result.keys())
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"DatabaseSDK.query failed: {e}")
            return []

    async def query_async(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Run a SELECT and return rows as dicts asynchronously."""
        try:
            query, params = self._add_tenant_filter(query, params)

            async with self.get_async_session() as session:
                result = await session.execute(text(query), params or ())
                columns = list(result.keys())
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"DatabaseSDK.query_async failed: {e}")
            return []

    def query_one(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> dict[str, Any] | None:
        """Run a SELECT and return first row as dict synchronously."""
        results = self.query(query, params)
        return results[0] if results else None

    async def query_one_async(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> dict[str, Any] | None:
        """Run a SELECT and return first row as dict asynchronously."""
        results = await self.query_async(query, params)
        return results[0] if results else None

    def query_scalar(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """Run a SELECT and return first column of first row synchronously."""
        result = self.query_one(query, params)
        if result:
            return next(iter(result.values()))
        return None

    async def query_scalar_async(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> Any:
        """Run a SELECT and return first column of first row asynchronously."""
        result = await self.query_one_async(query, params)
        if result:
            return next(iter(result.values()))
        return None

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        with self.get_session() as session:
            trans = session.begin()
            try:
                yield session
                trans.commit()
            except Exception:
                trans.rollback()
                raise

    @asynccontextmanager
    async def async_transaction(self):
        """Context manager for async database transactions."""
        async with self.get_async_session() as session:
            trans = await session.begin()
            try:
                yield session
                await trans.commit()
            except Exception:
                await trans.rollback()
                raise

    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def health_check_async(self) -> bool:
        """Check database connectivity asynchronously."""
        try:
            async with self.get_async_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_table_info(self, table_name: str) -> dict[str, Any]:
        """Get information about a table."""
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = :table_name
        ORDER BY ordinal_position
        """
        columns = self.query(query, (table_name,))
        return {
            "table_name": table_name,
            "columns": columns,
            "tenant_filtered": self.tenant_id is not None,
        }

    def close(self):
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
        if self._async_engine:
            # Note: async engine disposal should be awaited in real usage
            pass


# Legacy compatibility
class DatabaseClient(DatabaseSDK):
    """Legacy compatibility alias."""

    pass


__all__ = ["DatabaseSDK", "DatabaseClient"]
