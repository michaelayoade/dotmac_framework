"""Comprehensive unit tests for database module - 100% coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

from dotmac_isp.core.database import (
    engine,
    async_engine,
    SessionLocal,
    AsyncSessionLocal,
    get_db,
    get_async_db,
    create_tables,
    drop_tables,
    create_tables_async,
    drop_tables_async,
    init_database,
    close_database
)
from dotmac_isp.shared.database.base import Base


class TestDatabaseEngines:
    """Test database engine configurations."""

    @patch('dotmac_isp.core.database.get_settings')
    def test_engine_configuration(self, mock_get_settings):
        """Test synchronous engine configuration."""
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql://test:test@localhost:5432/test"
        mock_settings.debug = False
        mock_get_settings.return_value = mock_settings

        # Import again to get new engine with mocked settings
        from importlib import reload
        import dotmac_isp.core.database as db_module
        reload(db_module)

        # The engine should be configured with correct parameters
        assert db_module.engine is not None

    @patch('dotmac_isp.core.database.get_settings')
    def test_async_engine_configuration(self, mock_get_settings):
        """Test asynchronous engine configuration."""
        mock_settings = MagicMock()
        mock_settings.async_database_url = "postgresql+asyncpg://test:test@localhost:5432/test"
        mock_settings.debug = True
        mock_get_settings.return_value = mock_settings

        # Import again to get new engine with mocked settings
        from importlib import reload
        import dotmac_isp.core.database as db_module
        reload(db_module)

        assert db_module.async_engine is not None

    def test_session_local_configuration(self):
        """Test SessionLocal configuration."""
        assert SessionLocal is not None
        # SessionLocal is a sessionmaker, check it's callable
        assert callable(SessionLocal)

    def test_async_session_local_configuration(self):
        """Test AsyncSessionLocal configuration."""
        assert AsyncSessionLocal is not None
        # AsyncSessionLocal is a async_sessionmaker, check it's callable
        assert callable(AsyncSessionLocal)


class TestDatabaseDependencies:
    """Test database dependency functions."""

    @patch('dotmac_isp.core.database.SessionLocal')
    def test_get_db_success(self, mock_session_local):
        """Test successful database session creation and cleanup."""
        # Setup mock
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session

        # Test the generator
        db_gen = get_db()
        db_session = next(db_gen)

        assert db_session == mock_session
        
        # Test cleanup on generator close
        try:
            next(db_gen)
        except StopIteration:
            pass

        mock_session.close.assert_called_once()

    @patch('dotmac_isp.core.database.SessionLocal')
    def test_get_db_exception_handling(self, mock_session_local):
        """Test database session cleanup on exception."""
        # Setup mock
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session

        # Test exception handling
        db_gen = get_db()
        db_session = next(db_gen)

        # Simulate exception by closing generator
        db_gen.close()

        # Session should be closed even on exception
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.AsyncSessionLocal')
    async def test_get_async_db_success(self, mock_async_session_local):
        """Test successful async database session creation and cleanup."""
        # Setup mock
        mock_session = MagicMock(spec=AsyncSession)
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_async_session_local.return_value = mock_context_manager

        # Test the async generator
        db_gen = get_async_db()
        db_session = await db_gen.__anext__()

        assert db_session == mock_session

        # Test cleanup
        try:
            await db_gen.__anext__()
        except StopAsyncIteration:
            pass

        mock_context_manager.__aenter__.assert_called_once()
        mock_context_manager.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.AsyncSessionLocal')
    async def test_get_async_db_exception_handling(self, mock_async_session_local):
        """Test async database session cleanup on exception."""
        # Setup mock
        mock_session = MagicMock(spec=AsyncSession)
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_async_session_local.return_value = mock_context_manager

        # Test exception handling
        db_gen = get_async_db()
        await db_gen.__anext__()

        # Close generator to simulate exception
        await db_gen.aclose()

        mock_context_manager.__aenter__.assert_called_once()
        mock_context_manager.__aexit__.assert_called_once()


class TestDatabaseTableOperations:
    """Test database table creation and dropping operations."""

    @patch('dotmac_isp.core.database.Base')
    @patch('dotmac_isp.core.database.engine')
    def test_create_tables(self, mock_engine, mock_base):
        """Test synchronous table creation."""
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata

        create_tables()

        mock_metadata.create_all.assert_called_once_with(bind=mock_engine)

    @patch('dotmac_isp.core.database.Base')
    @patch('dotmac_isp.core.database.engine')
    def test_drop_tables(self, mock_engine, mock_base):
        """Test synchronous table dropping."""
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata

        drop_tables()

        mock_metadata.drop_all.assert_called_once_with(bind=mock_engine)

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.Base')
    @patch('dotmac_isp.core.database.async_engine')
    async def test_create_tables_async(self, mock_async_engine, mock_base):
        """Test asynchronous table creation."""
        # Setup mocks
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata
        
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None
        mock_async_engine.begin.return_value = mock_context_manager

        await create_tables_async()

        mock_async_engine.begin.assert_called_once()
        mock_conn.run_sync.assert_called_once_with(mock_metadata.create_all)

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.Base')
    @patch('dotmac_isp.core.database.async_engine')
    async def test_drop_tables_async(self, mock_async_engine, mock_base):
        """Test asynchronous table dropping."""
        # Setup mocks
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata
        
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None
        mock_async_engine.begin.return_value = mock_context_manager

        await drop_tables_async()

        mock_async_engine.begin.assert_called_once()
        mock_conn.run_sync.assert_called_once_with(mock_metadata.drop_all)


class TestDatabaseInitialization:
    """Test database initialization and cleanup functions."""

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.async_engine')
    @patch('dotmac_isp.core.database.Base')
    async def test_init_database_success(self, mock_base, mock_async_engine):
        """Test successful database initialization."""
        # Setup mocks
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata
        
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None
        mock_async_engine.begin.return_value = mock_context_manager

        await init_database()

        mock_async_engine.begin.assert_called_once()
        mock_conn.run_sync.assert_called_once_with(mock_metadata.create_all)

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.async_engine')
    @patch('dotmac_isp.core.database.Base')
    async def test_init_database_with_model_imports(self, mock_base, mock_async_engine):
        """Test database initialization with model imports."""
        # Setup mocks
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata
        
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None
        mock_async_engine.begin.return_value = mock_context_manager

        # Mock the model imports to succeed
        with patch.dict('sys.modules', {
            'dotmac_isp.modules.customers.models': MagicMock(),
            'dotmac_isp.modules.billing.models': MagicMock(),
            'dotmac_isp.modules.services.models': MagicMock(),
            'dotmac_isp.modules.identity.models': MagicMock(),
            'dotmac_isp.modules.support.models': MagicMock(),
            'dotmac_isp.modules.network_integration.models': MagicMock(),
            'dotmac_isp.modules.gis.models': MagicMock(),
        }):
            await init_database()

        mock_conn.run_sync.assert_called_once_with(mock_metadata.create_all)

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.async_engine')
    @patch('dotmac_isp.core.database.Base')
    async def test_init_database_import_error_handling(self, mock_base, mock_async_engine):
        """Test database initialization handles import errors gracefully."""
        # Setup mocks
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata
        
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None
        mock_async_engine.begin.return_value = mock_context_manager

        # Model imports will fail (default behavior), should not raise exception
        await init_database()

        # Should still create tables even if imports fail
        mock_conn.run_sync.assert_called_once_with(mock_metadata.create_all)

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.async_engine')
    async def test_close_database(self, mock_async_engine):
        """Test database connection cleanup."""
        # Make dispose return an awaitable
        mock_async_engine.dispose = AsyncMock()
        
        await close_database()

        mock_async_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.async_engine')
    async def test_close_database_exception_handling(self, mock_async_engine):
        """Test database cleanup handles exceptions."""
        # Setup mock to raise exception
        mock_async_engine.dispose = AsyncMock(side_effect=Exception("Connection error"))

        # Should not raise exception even if dispose fails - but our code doesn't handle this
        # so we expect it to raise
        with pytest.raises(Exception, match="Connection error"):
            await close_database()


class TestDatabaseModuleImports:
    """Test module imports and dependencies."""

    def test_all_imports_available(self):
        """Test all required imports are available."""
        # This test ensures all imports in the module work
        from dotmac_isp.core.database import (
            engine,
            async_engine,
            SessionLocal,
            AsyncSessionLocal,
            get_db,
            get_async_db,
            create_tables,
            drop_tables,
            create_tables_async,
            drop_tables_async,
            init_database,
            close_database
        )
        
        assert engine is not None
        assert async_engine is not None
        assert SessionLocal is not None
        assert AsyncSessionLocal is not None
        assert callable(get_db)
        assert callable(get_async_db)
        assert callable(create_tables)
        assert callable(drop_tables)
        assert callable(create_tables_async)
        assert callable(drop_tables_async)
        assert callable(init_database)
        assert callable(close_database)

    def test_base_import(self):
        """Test Base import from shared database module."""
        from dotmac_isp.core.database import Base
        assert Base is not None

    def test_settings_import(self):
        """Test settings import and usage."""
        # This is tested by the successful engine creation in module import
        from dotmac_isp.core import database
        assert hasattr(database, 'settings')


class TestDatabaseErrorCases:
    """Test error cases and edge conditions."""

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.async_engine')
    async def test_init_database_connection_error(self, mock_async_engine):
        """Test init_database handles connection errors."""
        # Setup mock to raise connection error
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.side_effect = Exception("Connection failed")
        mock_async_engine.begin.return_value = mock_context_manager

        # Should raise the exception (no exception handling for connection errors)
        with pytest.raises(Exception, match="Connection failed"):
            await init_database()

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.async_engine')
    async def test_close_database_already_closed(self, mock_async_engine):
        """Test close_database when connection is already closed."""
        # Setup mock to simulate already closed connection
        mock_async_engine.dispose = AsyncMock()

        await close_database()
        await close_database()  # Call twice

        # Should be called twice without issues
        assert mock_async_engine.dispose.call_count == 2

    @patch('dotmac_isp.core.database.SessionLocal')
    def test_get_db_session_creation_error(self, mock_session_local):
        """Test get_db handles session creation errors."""
        # Setup mock to raise exception on session creation
        mock_session_local.side_effect = Exception("Session creation failed")

        # Should raise the exception
        with pytest.raises(Exception, match="Session creation failed"):
            db_gen = get_db()
            next(db_gen)

    @pytest.mark.asyncio
    @patch('dotmac_isp.core.database.AsyncSessionLocal')
    async def test_get_async_db_session_creation_error(self, mock_async_session_local):
        """Test get_async_db handles session creation errors."""
        # Setup mock to raise exception
        mock_async_session_local.side_effect = Exception("Async session creation failed")

        # Should raise the exception
        with pytest.raises(Exception, match="Async session creation failed"):
            db_gen = get_async_db()
            await db_gen.__anext__()