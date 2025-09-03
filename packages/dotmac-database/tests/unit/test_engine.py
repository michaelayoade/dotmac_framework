"""
Unit tests for engine and session management.
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from dotmac.database.engine import (
    create_async_engine,
    create_async_session_factory,
    DatabaseManager,
    DatabaseURL,
)


class TestDatabaseURL:
    """Test DatabaseURL configuration class."""
    
    def test_database_url_creation(self):
        """Test creating DatabaseURL with various parameters."""
        url = DatabaseURL(
            driver="postgresql+asyncpg",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass"
        )
        
        assert url.driver == "postgresql+asyncpg"
        assert url.host == "localhost"
        assert url.port == 5432
        assert url.database == "testdb"
        assert url.username == "testuser"
        assert url.password == "testpass"
    
    def test_database_url_to_string(self):
        """Test converting DatabaseURL to connection string."""
        url = DatabaseURL(
            driver="postgresql+asyncpg",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass"
        )
        
        url_string = str(url)
        expected = "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"
        assert url_string == expected
    
    def test_database_url_without_credentials(self):
        """Test DatabaseURL without username/password."""
        url = DatabaseURL(
            driver="sqlite+aiosqlite",
            database="test.db"
        )
        
        url_string = str(url)
        assert url_string == "sqlite+aiosqlite:///test.db"
    
    def test_database_url_with_query_params(self):
        """Test DatabaseURL with query parameters."""
        url = DatabaseURL(
            driver="postgresql+asyncpg",
            host="localhost",
            database="testdb",
            username="testuser",
            password="testpass",
            query_params={"sslmode": "require", "pool_size": "20"}
        )
        
        url_string = str(url)
        assert "sslmode=require" in url_string
        assert "pool_size=20" in url_string


class TestCreateAsyncEngine:
    """Test async engine creation."""
    
    @patch('dotmac.database.engine.sa.create_async_engine')
    def test_create_engine_with_url_string(self, mock_create_engine):
        """Test creating engine with URL string."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine
        
        url = "postgresql+asyncpg://user:pass@localhost/db"
        result = create_async_engine(url)
        
        assert result == mock_engine
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args
        assert args[0] == url
    
    @patch('dotmac.database.engine.sa.create_async_engine')
    def test_create_engine_with_database_url(self, mock_create_engine):
        """Test creating engine with DatabaseURL object."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine
        
        url = DatabaseURL(
            driver="postgresql+asyncpg",
            host="localhost",
            database="testdb",
            username="user",
            password="pass"
        )
        
        result = create_async_engine(url)
        
        assert result == mock_engine
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args
        assert args[0] == str(url)
    
    @patch('dotmac.database.engine.sa.create_async_engine')
    def test_create_engine_with_options(self, mock_create_engine):
        """Test creating engine with configuration options."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine
        
        url = "postgresql+asyncpg://user:pass@localhost/db"
        result = create_async_engine(
            url,
            echo=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        
        assert result == mock_engine
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args
        
        assert kwargs['echo'] is True
        assert kwargs['pool_size'] == 10
        assert kwargs['max_overflow'] == 20
        assert kwargs['pool_recycle'] == 3600
        assert kwargs['pool_pre_ping'] is True
    
    @patch('dotmac.database.engine.sa.create_async_engine')
    def test_create_engine_defaults(self, mock_create_engine):
        """Test engine creation with default settings."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine
        
        url = "postgresql+asyncpg://user:pass@localhost/db"
        result = create_async_engine(url)
        
        assert result == mock_engine
        args, kwargs = mock_create_engine.call_args
        
        # Check default values are applied
        assert kwargs.get('echo', False) is False
        assert kwargs.get('pool_size', 10) == 10
        assert kwargs.get('pool_recycle', 3600) == 3600
        assert kwargs.get('pool_pre_ping', True) is True


class TestCreateAsyncSessionFactory:
    """Test async session factory creation."""
    
    def test_create_session_factory(self):
        """Test creating session factory."""
        mock_engine = MagicMock(spec=AsyncEngine)
        
        factory = create_async_session_factory(mock_engine)
        
        # Should return a callable
        assert callable(factory)
    
    def test_session_factory_with_options(self):
        """Test session factory with custom options."""
        mock_engine = MagicMock(spec=AsyncEngine)
        
        factory = create_async_session_factory(
            mock_engine,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        )
        
        assert callable(factory)


class TestDatabaseManager:
    """Test DatabaseManager class."""
    
    def test_database_manager_creation(self):
        """Test creating DatabaseManager with engines."""
        read_engine = MagicMock(spec=AsyncEngine)
        write_engine = MagicMock(spec=AsyncEngine)
        
        manager = DatabaseManager(
            read_engine=read_engine,
            write_engine=write_engine
        )
        
        assert manager.read_engine == read_engine
        assert manager.write_engine == write_engine
    
    def test_database_manager_single_engine(self):
        """Test DatabaseManager with single engine for both read/write."""
        engine = MagicMock(spec=AsyncEngine)
        
        manager = DatabaseManager(
            read_engine=engine,
            write_engine=engine
        )
        
        assert manager.read_engine == engine
        assert manager.write_engine == engine
    
    @pytest.mark.asyncio
    async def test_database_manager_get_read_session(self):
        """Test getting read session from manager."""
        read_engine = MagicMock(spec=AsyncEngine)
        write_engine = MagicMock(spec=AsyncEngine)
        
        manager = DatabaseManager(
            read_engine=read_engine,
            write_engine=write_engine
        )
        
        # Mock session factory
        mock_session = MagicMock(spec=AsyncSession)
        manager._read_session_factory = MagicMock(return_value=mock_session)
        
        async with manager.get_read_session() as session:
            assert session == mock_session
    
    @pytest.mark.asyncio
    async def test_database_manager_get_write_session(self):
        """Test getting write session from manager."""
        read_engine = MagicMock(spec=AsyncEngine)
        write_engine = MagicMock(spec=AsyncEngine)
        
        manager = DatabaseManager(
            read_engine=read_engine,
            write_engine=write_engine
        )
        
        # Mock session factory
        mock_session = MagicMock(spec=AsyncSession)
        manager._write_session_factory = MagicMock(return_value=mock_session)
        
        async with manager.get_write_session() as session:
            assert session == mock_session
    
    @pytest.mark.asyncio
    async def test_database_manager_get_db_session(self):
        """Test getting general db session (write) from manager."""
        read_engine = MagicMock(spec=AsyncEngine)
        write_engine = MagicMock(spec=AsyncEngine)
        
        manager = DatabaseManager(
            read_engine=read_engine,
            write_engine=write_engine
        )
        
        # Mock session factory
        mock_session = MagicMock(spec=AsyncSession)
        manager._write_session_factory = MagicMock(return_value=mock_session)
        
        async with manager.get_db() as session:
            assert session == mock_session
    
    @pytest.mark.asyncio
    async def test_database_manager_close(self):
        """Test closing database manager."""
        read_engine = MagicMock(spec=AsyncEngine)
        write_engine = MagicMock(spec=AsyncEngine)
        
        # Mock async dispose methods
        read_engine.dispose = MagicMock()
        write_engine.dispose = MagicMock()
        
        manager = DatabaseManager(
            read_engine=read_engine,
            write_engine=write_engine
        )
        
        await manager.close()
        
        read_engine.dispose.assert_called_once()
        write_engine.dispose.assert_called_once()
    
    def test_database_manager_context_manager_sync(self):
        """Test DatabaseManager as synchronous context manager."""
        read_engine = MagicMock(spec=AsyncEngine)
        write_engine = MagicMock(spec=AsyncEngine)
        
        manager = DatabaseManager(
            read_engine=read_engine,
            write_engine=write_engine
        )
        
        with manager:
            # Should not raise any exceptions
            pass
    
    @pytest.mark.asyncio
    async def test_database_manager_context_manager_async(self):
        """Test DatabaseManager as asynchronous context manager."""
        read_engine = MagicMock(spec=AsyncEngine)
        write_engine = MagicMock(spec=AsyncEngine)
        
        # Mock async dispose methods
        read_engine.dispose = MagicMock()
        write_engine.dispose = MagicMock()
        
        manager = DatabaseManager(
            read_engine=read_engine,
            write_engine=write_engine
        )
        
        async with manager:
            # Should not raise any exceptions during entry
            pass
        
        # Should call dispose on exit
        read_engine.dispose.assert_called_once()
        write_engine.dispose.assert_called_once()