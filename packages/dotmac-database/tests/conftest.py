"""
Test configuration and fixtures for dotmac-database package.
"""

import asyncio
import uuid
from typing import AsyncIterator
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from dotmac.database import Base, DatabaseManager
from dotmac.database.engine import create_async_session_factory


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Create test database engine using in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Create database session for testing."""
    session_factory = create_async_session_factory(test_engine)
    
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def db_manager(test_engine: AsyncEngine) -> DatabaseManager:
    """Create database manager for testing."""
    return DatabaseManager(
        read_engine=test_engine,
        write_engine=test_engine
    )


@pytest.fixture
def sample_tenant_id() -> str:
    """Generate sample tenant ID for testing."""
    return f"tenant_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sample_user_id() -> str:
    """Generate sample user ID for testing."""
    return f"user_{uuid.uuid4().hex[:8]}"


# Mock Redis client for caching tests
@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    class MockRedis:
        def __init__(self):
            self._data = {}
            self._expires = {}
        
        def set(self, key, value, ex=None, nx=False):
            if nx and key in self._data:
                return False
            self._data[key] = value
            if ex:
                import time
                self._expires[key] = time.time() + ex
            return True
        
        def get(self, key):
            import time
            if key in self._expires and time.time() > self._expires[key]:
                del self._data[key]
                del self._expires[key]
                return None
            return self._data.get(key)
        
        def delete(self, *keys):
            deleted = 0
            for key in keys:
                if key in self._data:
                    del self._data[key]
                    deleted += 1
                if key in self._expires:
                    del self._expires[key]
            return deleted
        
        def exists(self, key):
            return 1 if key in self._data else 0
        
        def keys(self, pattern="*"):
            import fnmatch
            return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]
        
        def ttl(self, key):
            if key not in self._data:
                return -2
            if key not in self._expires:
                return -1
            import time
            remaining = self._expires[key] - time.time()
            return max(0, int(remaining))
        
        def ping(self):
            return True
    
    return MockRedis()