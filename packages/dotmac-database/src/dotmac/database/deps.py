"""
FastAPI dependencies for database session management.

Provides dependency functions for injecting database sessions
into FastAPI route handlers with proper lifecycle management.
"""

import logging
from typing import Any, AsyncIterator, Optional, Dict

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .engine import DatabaseManager

try:
    from fastapi import Depends
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Create dummy Depends for type hints when FastAPI not available
    def Depends(dependency: Any) -> Any:  # type: ignore
        return dependency

logger = logging.getLogger(__name__)


class DatabaseDependencyError(Exception):
    """Raised when database dependency configuration is invalid."""
    pass


class DatabaseDependencies:
    """
    Container for database dependencies with different session strategies.
    
    Supports read/write session separation and custom session configuration
    for different use cases.
    """
    
    def __init__(
        self,
        manager: Optional[DatabaseManager] = None,
        read_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None,
        write_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None,
    ):
        """
        Initialize database dependencies.
        
        Args:
            manager: DatabaseManager instance
            read_sessionmaker: Optional separate sessionmaker for read operations
            write_sessionmaker: Optional separate sessionmaker for write operations
        """
        self._manager = manager
        self._read_sessionmaker = read_sessionmaker
        self._write_sessionmaker = write_sessionmaker
        
        # Validate configuration
        if not manager and not (read_sessionmaker or write_sessionmaker):
            raise DatabaseDependencyError(
                "Either manager or explicit sessionmakers must be provided"
            )
    
    @property
    def manager(self) -> DatabaseManager:
        """Get the database manager."""
        if self._manager is None:
            raise DatabaseDependencyError("No database manager configured")
        return self._manager
    
    @property
    def default_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """Get the default sessionmaker."""
        if self._manager:
            return self._manager.sessionmaker
        elif self._write_sessionmaker:
            return self._write_sessionmaker
        elif self._read_sessionmaker:
            return self._read_sessionmaker
        else:
            raise DatabaseDependencyError("No sessionmaker available")
    
    @property
    def read_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """Get the read sessionmaker."""
        return self._read_sessionmaker or self.default_sessionmaker
    
    @property
    def write_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """Get the write sessionmaker."""
        return self._write_sessionmaker or self.default_sessionmaker
    
    async def get_db(self) -> AsyncIterator[AsyncSession]:
        """
        Get a database session for general use.
        
        This is the main dependency function for FastAPI routes.
        Handles commit/rollback automatically and ensures proper cleanup.
        
        Yields:
            AsyncSession instance
        """
        sessionmaker = self.default_sessionmaker
        session = sessionmaker()
        
        try:
            yield session
            
            # Commit if there are pending changes and no explicit transaction
            if session.dirty or session.new or session.deleted:
                if not session.in_transaction():
                    await session.commit()
                    logger.debug("Auto-committed session changes")
                    
        except Exception as e:
            # Rollback on any exception
            if session.in_transaction():
                await session.rollback()
                logger.warning(f"Session rolled back due to error: {e}")
            raise
            
        finally:
            await session.close()
            logger.debug("Database session closed")
    
    async def get_read_session(self) -> AsyncIterator[AsyncSession]:
        """
        Get a read-only database session.
        
        Optimized for read operations with potential routing to
        read replicas if configured.
        
        Yields:
            AsyncSession instance for read operations
        """
        sessionmaker = self.read_sessionmaker
        session = sessionmaker()
        
        try:
            yield session
            
            # Read sessions typically don't need commits, but handle gracefully
            if session.dirty or session.new or session.deleted:
                logger.warning("Read session has pending changes - this may indicate incorrect usage")
                
        except Exception as e:
            logger.warning(f"Read session error: {e}")
            raise
            
        finally:
            await session.close()
            logger.debug("Read session closed")
    
    async def get_write_session(self) -> AsyncIterator[AsyncSession]:
        """
        Get a write database session.
        
        Explicitly for write operations with automatic commit/rollback
        handling and routing to write-capable databases.
        
        Yields:
            AsyncSession instance for write operations
        """
        sessionmaker = self.write_sessionmaker
        session = sessionmaker()
        
        try:
            yield session
            
            # Always commit write sessions if there are changes
            if session.dirty or session.new or session.deleted:
                await session.commit()
                logger.debug("Write session committed successfully")
                
        except Exception as e:
            # Rollback write sessions on error
            if session.in_transaction():
                await session.rollback()
                logger.warning(f"Write session rolled back due to error: {e}")
            raise
            
        finally:
            await session.close()
            logger.debug("Write session closed")
    
    async def get_session_with_config(
        self,
        auto_commit: bool = True,
        auto_rollback: bool = True,
        read_only: bool = False,
    ) -> AsyncIterator[AsyncSession]:
        """
        Get a database session with custom configuration.
        
        Args:
            auto_commit: Automatically commit successful transactions
            auto_rollback: Automatically rollback failed transactions
            read_only: Use read sessionmaker if available
            
        Yields:
            AsyncSession instance with custom behavior
        """
        sessionmaker = self.read_sessionmaker if read_only else self.write_sessionmaker
        session = sessionmaker()
        
        try:
            yield session
            
            # Handle commit based on configuration
            if auto_commit and (session.dirty or session.new or session.deleted):
                if session.in_transaction():
                    await session.commit()
                    logger.debug("Custom session committed")
                    
        except Exception as e:
            # Handle rollback based on configuration
            if auto_rollback and session.in_transaction():
                await session.rollback()
                logger.warning(f"Custom session rolled back: {e}")
            raise
            
        finally:
            await session.close()


# Global dependencies instance
_db_deps: Optional[DatabaseDependencies] = None


def configure_database_dependencies(
    manager: Optional[DatabaseManager] = None,
    read_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None,
    write_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None,
) -> DatabaseDependencies:
    """
    Configure global database dependencies.
    
    This should be called during application startup to set up
    the database dependencies that will be used by FastAPI routes.
    
    Args:
        manager: DatabaseManager instance
        read_sessionmaker: Optional read-only sessionmaker
        write_sessionmaker: Optional write sessionmaker
        
    Returns:
        Configured DatabaseDependencies instance
        
    Example:
        # During app startup
        db_manager = DatabaseManager(DATABASE_URL)
        await db_manager.startup()
        
        deps = configure_database_dependencies(manager=db_manager)
        
        # In routes
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    global _db_deps
    _db_deps = DatabaseDependencies(
        manager=manager,
        read_sessionmaker=read_sessionmaker,
        write_sessionmaker=write_sessionmaker,
    )
    return _db_deps


def get_database_dependencies() -> DatabaseDependencies:
    """
    Get the configured database dependencies.
    
    Returns:
        DatabaseDependencies instance
        
    Raises:
        DatabaseDependencyError: If dependencies not configured
    """
    if _db_deps is None:
        raise DatabaseDependencyError(
            "Database dependencies not configured. "
            "Call configure_database_dependencies() during application startup."
        )
    return _db_deps


# Convenience dependency functions for FastAPI
async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Get a database session dependency for FastAPI routes.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            return await db.execute(select(Item))
    
    Yields:
        AsyncSession with automatic lifecycle management
    """
    deps = get_database_dependencies()
    async with deps.get_db() as session:
        yield session


async def get_read_session() -> AsyncIterator[AsyncSession]:
    """
    Get a read-only database session dependency for FastAPI routes.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_read_session)):
            return await db.execute(select(Item))
    
    Yields:
        AsyncSession optimized for read operations
    """
    deps = get_database_dependencies()
    async with deps.get_read_session() as session:
        yield session


async def get_write_session() -> AsyncIterator[AsyncSession]:
    """
    Get a write database session dependency for FastAPI routes.
    
    Usage:
        @app.post("/items")
        async def create_item(
            item: ItemCreate,
            db: AsyncSession = Depends(get_write_session)
        ):
            db_item = Item(**item.dict())
            db.add(db_item)
            await db.flush()
            return db_item
    
    Yields:
        AsyncSession optimized for write operations
    """
    deps = get_database_dependencies()
    async with deps.get_write_session() as session:
        yield session


def create_custom_session_dependency(
    auto_commit: bool = True,
    auto_rollback: bool = True,
    read_only: bool = False,
):
    """
    Create a custom session dependency with specific configuration.
    
    Args:
        auto_commit: Automatically commit successful transactions
        auto_rollback: Automatically rollback failed transactions  
        read_only: Use read sessionmaker if available
        
    Returns:
        Dependency function for FastAPI
        
    Example:
        # Create custom dependency
        get_manual_session = create_custom_session_dependency(
            auto_commit=False,
            auto_rollback=True
        )
        
        # Use in route
        @app.post("/items")
        async def create_item(
            item: ItemCreate,
            db: AsyncSession = Depends(get_manual_session)
        ):
            db_item = Item(**item.dict())
            db.add(db_item)
            await db.commit()  # Manual commit
            return db_item
    """
    async def custom_session_dependency() -> AsyncIterator[AsyncSession]:
        deps = get_database_dependencies()
        async with deps.get_session_with_config(
            auto_commit=auto_commit,
            auto_rollback=auto_rollback,
            read_only=read_only,
        ) as session:
            yield session
    
    return custom_session_dependency


# Transaction management utilities
class TransactionManager:
    """
    Utility class for managing complex transactions.
    
    Provides savepoints, nested transactions, and batch operations
    with proper error handling and rollback capabilities.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._savepoints = []
    
    async def savepoint(self, name: Optional[str] = None) -> str:
        """
        Create a savepoint within the current transaction.
        
        Args:
            name: Optional savepoint name
            
        Returns:
            Savepoint name
        """
        if name is None:
            name = f"sp_{len(self._savepoints) + 1}"
        
        savepoint = await self.session.begin_nested()
        self._savepoints.append((name, savepoint))
        
        logger.debug(f"Created savepoint: {name}")
        return name
    
    async def rollback_to_savepoint(self, name: str) -> None:
        """
        Rollback to a specific savepoint.
        
        Args:
            name: Savepoint name to rollback to
        """
        # Find the savepoint
        for i, (sp_name, savepoint) in enumerate(self._savepoints):
            if sp_name == name:
                await savepoint.rollback()
                # Remove this and later savepoints
                self._savepoints = self._savepoints[:i]
                logger.debug(f"Rolled back to savepoint: {name}")
                return
        
        raise ValueError(f"Savepoint '{name}' not found")
    
    async def release_savepoint(self, name: str) -> None:
        """
        Release a savepoint (commit it).
        
        Args:
            name: Savepoint name to release
        """
        for i, (sp_name, savepoint) in enumerate(self._savepoints):
            if sp_name == name:
                await savepoint.commit()
                self._savepoints.pop(i)
                logger.debug(f"Released savepoint: {name}")
                return
        
        raise ValueError(f"Savepoint '{name}' not found")
    
    async def batch_execute(
        self,
        statements: list[Any],
        rollback_on_error: bool = True,
    ) -> list[Any]:
        """
        Execute multiple statements as a batch with error handling.
        
        Args:
            statements: List of SQLAlchemy statements to execute
            rollback_on_error: Rollback all on first error
            
        Returns:
            List of results
        """
        results = []
        savepoint_name = None
        
        if rollback_on_error:
            savepoint_name = await self.savepoint("batch_execute")
        
        try:
            for stmt in statements:
                result = await self.session.execute(stmt)
                results.append(result)
            
            if savepoint_name:
                await self.release_savepoint(savepoint_name)
                
        except Exception as e:
            if savepoint_name:
                await self.rollback_to_savepoint(savepoint_name)
            logger.error(f"Batch execute failed: {e}")
            raise
        
        return results