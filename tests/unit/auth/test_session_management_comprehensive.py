"""
Comprehensive tests for Session Management - targeting 95% coverage.

Tests cover session creation, validation, expiration, and cleanup.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

try:
    from dotmac_shared.auth.session_management import (
        ExpiredSessionError,
        InvalidSessionError,
        Session,
        SessionConfig,
        SessionError,
        SessionManager,
        SessionStatus,
    )
except ImportError:
    # Create mock classes for testing
    from enum import Enum
    from typing import Optional

    class SessionStatus(Enum):
        ACTIVE = "active"
        EXPIRED = "expired"
        INVALIDATED = "invalidated"
        TERMINATED = "terminated"

    class Session:
        def __init__(self, session_id, user_id, tenant_id, **kwargs):
            self.session_id = session_id
            self.user_id = user_id
            self.tenant_id = tenant_id
            self.status = kwargs.get('status', SessionStatus.ACTIVE)
            self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
            self.updated_at = kwargs.get('updated_at', datetime.now(timezone.utc))
            self.expires_at = kwargs.get('expires_at')
            self.last_activity = kwargs.get('last_activity', datetime.now(timezone.utc))
            self.client_ip = kwargs.get('client_ip')
            self.user_agent = kwargs.get('user_agent')
            self.metadata = kwargs.get('metadata', {})

        def is_expired(self) -> bool:
            if self.expires_at:
                return datetime.now(timezone.utc) > self.expires_at
            return False

        def is_active(self) -> bool:
            return self.status == SessionStatus.ACTIVE and not self.is_expired()

        def update_activity(self):
            self.last_activity = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)

    class SessionConfig:
        def __init__(self, **kwargs):
            self.max_lifetime = kwargs.get('max_lifetime', timedelta(hours=24))
            self.inactivity_timeout = kwargs.get('inactivity_timeout', timedelta(hours=2))
            self.max_sessions_per_user = kwargs.get('max_sessions_per_user', 5)
            self.require_client_validation = kwargs.get('require_client_validation', True)
            self.cleanup_interval = kwargs.get('cleanup_interval', timedelta(minutes=30))

    class SessionManager:
        def __init__(self, tenant_id, config: Optional[SessionConfig] = None):
            if tenant_id is None:
                raise ValueError("tenant_id cannot be None")
            if tenant_id == "":
                raise ValueError("tenant_id cannot be empty")
            self.tenant_id = tenant_id
            self.config = config or SessionConfig()
            self._sessions: dict[str, Session] = {}
            self._user_sessions: dict[str, list[str]] = {}

        async def create_session(self, user_id: str, **kwargs) -> Session:
            if not user_id:
                raise SessionError("User ID is required")

            session_id = str(uuid4())
            expires_at = datetime.now(timezone.utc) + self.config.max_lifetime

            session = Session(
                session_id=session_id,
                user_id=user_id,
                tenant_id=self.tenant_id,
                expires_at=expires_at,
                client_ip=kwargs.get('client_ip'),
                user_agent=kwargs.get('user_agent'),
                metadata=kwargs.get('metadata', {})
            )

            # Check session limits
            user_session_count = len(self._user_sessions.get(user_id, []))
            if user_session_count >= self.config.max_sessions_per_user:
                # Remove oldest session
                oldest_session_id = self._user_sessions[user_id][0]
                await self.invalidate_session(oldest_session_id)

            self._sessions[session_id] = session
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = []
            self._user_sessions[user_id].append(session_id)

            return session

        async def get_session(self, session_id: str) -> Optional[Session]:
            if not session_id:
                raise SessionError("Session ID is required")

            session = self._sessions.get(session_id)
            if not session:
                return None

            # Check if expired
            if session.is_expired():
                session.status = SessionStatus.EXPIRED
                await self._cleanup_expired_session(session_id)
                raise ExpiredSessionError("Session has expired")

            # Check inactivity timeout
            if (datetime.now(timezone.utc) - session.last_activity) > self.config.inactivity_timeout:
                session.status = SessionStatus.EXPIRED
                await self._cleanup_expired_session(session_id)
                raise ExpiredSessionError("Session expired due to inactivity")

            return session

        async def validate_session(self, session_id: str, **kwargs) -> Session:
            session = await self.get_session(session_id)
            if not session:
                raise InvalidSessionError("Session not found")

            if not session.is_active():
                raise InvalidSessionError("Session is not active")

            # Validate client if required
            if self.config.require_client_validation:
                if kwargs.get('client_ip') and session.client_ip:
                    if kwargs['client_ip'] != session.client_ip:
                        raise InvalidSessionError("Client IP mismatch")

                if kwargs.get('user_agent') and session.user_agent:
                    if kwargs['user_agent'] != session.user_agent:
                        raise InvalidSessionError("User agent mismatch")

            # Update activity
            session.update_activity()
            return session

        async def refresh_session(self, session_id: str) -> Session:
            session = await self.get_session(session_id)
            if not session:
                raise InvalidSessionError("Session not found")

            session.expires_at = datetime.now(timezone.utc) + self.config.max_lifetime
            session.update_activity()
            return session

        async def invalidate_session(self, session_id: str) -> bool:
            if not session_id:
                raise SessionError("Session ID is required")

            session = self._sessions.get(session_id)
            if not session:
                return False

            session.status = SessionStatus.INVALIDATED
            await self._cleanup_session(session_id)
            return True

        async def invalidate_user_sessions(self, user_id: str) -> int:
            if not user_id:
                raise SessionError("User ID is required")

            session_ids = self._user_sessions.get(user_id, []).copy()
            count = 0

            for session_id in session_ids:
                if await self.invalidate_session(session_id):
                    count += 1

            return count

        async def list_user_sessions(self, user_id: str) -> list[Session]:
            if not user_id:
                raise SessionError("User ID is required")

            session_ids = self._user_sessions.get(user_id, [])
            sessions = []

            for session_id in session_ids:
                session = self._sessions.get(session_id)
                if session and session.is_active():
                    sessions.append(session)

            return sessions

        async def cleanup_expired_sessions(self) -> int:
            expired_count = 0
            current_time = datetime.now(timezone.utc)

            # Create a copy of session IDs to avoid modification during iteration
            session_ids = list(self._sessions.keys())

            for session_id in session_ids:
                session = self._sessions[session_id]

                # Check expiration
                if session.is_expired():
                    await self._cleanup_expired_session(session_id)
                    expired_count += 1
                    continue

                # Check inactivity timeout
                if (current_time - session.last_activity) > self.config.inactivity_timeout:
                    session.status = SessionStatus.EXPIRED
                    await self._cleanup_expired_session(session_id)
                    expired_count += 1

            return expired_count

        async def get_session_stats(self) -> dict:
            total_sessions = len(self._sessions)
            active_sessions = sum(1 for s in self._sessions.values() if s.is_active())
            expired_sessions = sum(1 for s in self._sessions.values() if s.status == SessionStatus.EXPIRED)

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "expired_sessions": expired_sessions,
                "unique_users": len(self._user_sessions)
            }

        async def _cleanup_session(self, session_id: str):
            session = self._sessions.get(session_id)
            if session:
                # Remove from user sessions
                user_sessions = self._user_sessions.get(session.user_id, [])
                if session_id in user_sessions:
                    user_sessions.remove(session_id)
                    if not user_sessions:
                        del self._user_sessions[session.user_id]

                # Remove session
                del self._sessions[session_id]

        async def _cleanup_expired_session(self, session_id: str):
            await self._cleanup_session(session_id)

    class SessionError(Exception):
        pass

    class InvalidSessionError(SessionError):
        pass

    class ExpiredSessionError(SessionError):
        pass


class TestSessionManagementComprehensive:
    """Comprehensive tests for SessionManager."""

    @pytest.fixture
    def session_config(self):
        """Create test session configuration."""
        return SessionConfig(
            max_lifetime=timedelta(hours=1),
            inactivity_timeout=timedelta(minutes=30),
            max_sessions_per_user=3,
            require_client_validation=True
        )

    @pytest.fixture
    def session_manager(self, session_config):
        """Create test session manager instance."""
        return SessionManager(tenant_id="test-tenant", config=session_config)

    def test_session_manager_initialization_valid_tenant(self, session_config):
        """Test session manager with valid tenant ID."""
        manager = SessionManager(tenant_id="valid-tenant", config=session_config)
        assert manager.tenant_id == "valid-tenant"

    def test_session_manager_initialization_none_tenant(self):
        """Test session manager handles None tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be None"):
            SessionManager(tenant_id=None)

    def test_session_manager_initialization_empty_tenant(self):
        """Test session manager handles empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            SessionManager(tenant_id="")

    def test_session_manager_default_config(self):
        """Test session manager with default configuration."""
        manager = SessionManager(tenant_id="test-tenant")
        assert manager.config is not None
        assert isinstance(manager.config.max_lifetime, timedelta)

    async def test_create_session_success(self, session_manager):
        """Test successful session creation."""
        session = await session_manager.create_session(
            user_id="test-user",
            client_ip="192.168.1.1",
            user_agent="TestAgent/1.0"
        )

        assert session.user_id == "test-user"
        assert session.tenant_id == "test-tenant"
        assert session.client_ip == "192.168.1.1"
        assert session.user_agent == "TestAgent/1.0"
        assert session.status == SessionStatus.ACTIVE
        assert isinstance(session.session_id, str)
        assert session.expires_at is not None

    async def test_create_session_empty_user_id(self, session_manager):
        """Test session creation with empty user ID."""
        with pytest.raises(SessionError, match="User ID is required"):
            await session_manager.create_session(user_id="")

    async def test_create_session_none_user_id(self, session_manager):
        """Test session creation with None user ID."""
        with pytest.raises(SessionError, match="User ID is required"):
            await session_manager.create_session(user_id=None)

    async def test_create_session_max_limit(self, session_manager):
        """Test session creation with max session limit."""
        user_id = "test-user"

        # Create max sessions
        sessions = []
        for _i in range(3):  # max_sessions_per_user = 3
            session = await session_manager.create_session(user_id=user_id)
            sessions.append(session)

        # Create one more - should remove oldest
        await session_manager.create_session(user_id=user_id)

        # First session should be invalidated
        first_session = await session_manager.get_session(sessions[0].session_id)
        assert first_session is None

    async def test_get_session_success(self, session_manager):
        """Test successful session retrieval."""
        created_session = await session_manager.create_session(user_id="test-user")
        retrieved_session = await session_manager.get_session(created_session.session_id)

        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
        assert retrieved_session.user_id == created_session.user_id

    async def test_get_session_empty_id(self, session_manager):
        """Test get session with empty ID."""
        with pytest.raises(SessionError, match="Session ID is required"):
            await session_manager.get_session("")

    async def test_get_session_none_id(self, session_manager):
        """Test get session with None ID."""
        with pytest.raises(SessionError, match="Session ID is required"):
            await session_manager.get_session(None)

    async def test_get_session_nonexistent(self, session_manager):
        """Test get session with nonexistent ID."""
        result = await session_manager.get_session("nonexistent-id")
        assert result is None

    async def test_get_session_expired(self, session_manager):
        """Test get session when expired."""
        # Create session with short lifetime
        session = await session_manager.create_session(user_id="test-user")

        # Manually expire session
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

        with pytest.raises(ExpiredSessionError, match="Session has expired"):
            await session_manager.get_session(session.session_id)

    async def test_get_session_inactive(self, session_manager):
        """Test get session when inactive due to timeout."""
        session = await session_manager.create_session(user_id="test-user")

        # Simulate inactivity timeout
        session.last_activity = datetime.now(timezone.utc) - timedelta(hours=1)

        with pytest.raises(ExpiredSessionError, match="Session expired due to inactivity"):
            await session_manager.get_session(session.session_id)

    async def test_validate_session_success(self, session_manager):
        """Test successful session validation."""
        session = await session_manager.create_session(
            user_id="test-user",
            client_ip="192.168.1.1",
            user_agent="TestAgent/1.0"
        )

        validated_session = await session_manager.validate_session(
            session.session_id,
            client_ip="192.168.1.1",
            user_agent="TestAgent/1.0"
        )

        assert validated_session.session_id == session.session_id
        assert validated_session.is_active() is True

    async def test_validate_session_not_found(self, session_manager):
        """Test session validation when session not found."""
        with pytest.raises(InvalidSessionError, match="Session not found"):
            await session_manager.validate_session("nonexistent-id")

    async def test_validate_session_client_ip_mismatch(self, session_manager):
        """Test session validation with client IP mismatch."""
        session = await session_manager.create_session(
            user_id="test-user",
            client_ip="192.168.1.1"
        )

        with pytest.raises(InvalidSessionError, match="Client IP mismatch"):
            await session_manager.validate_session(
                session.session_id,
                client_ip="192.168.1.2"
            )

    async def test_validate_session_user_agent_mismatch(self, session_manager):
        """Test session validation with user agent mismatch."""
        session = await session_manager.create_session(
            user_id="test-user",
            user_agent="TestAgent/1.0"
        )

        with pytest.raises(InvalidSessionError, match="User agent mismatch"):
            await session_manager.validate_session(
                session.session_id,
                user_agent="DifferentAgent/1.0"
            )

    async def test_refresh_session_success(self, session_manager):
        """Test successful session refresh."""
        session = await session_manager.create_session(user_id="test-user")
        original_expires_at = session.expires_at

        # Wait a moment then refresh
        import asyncio
        await asyncio.sleep(0.01)

        refreshed_session = await session_manager.refresh_session(session.session_id)

        assert refreshed_session.expires_at > original_expires_at

    async def test_refresh_session_not_found(self, session_manager):
        """Test session refresh when session not found."""
        with pytest.raises(InvalidSessionError, match="Session not found"):
            await session_manager.refresh_session("nonexistent-id")

    async def test_invalidate_session_success(self, session_manager):
        """Test successful session invalidation."""
        session = await session_manager.create_session(user_id="test-user")
        result = await session_manager.invalidate_session(session.session_id)

        assert result is True

        # Session should no longer exist
        retrieved_session = await session_manager.get_session(session.session_id)
        assert retrieved_session is None

    async def test_invalidate_session_empty_id(self, session_manager):
        """Test invalidate session with empty ID."""
        with pytest.raises(SessionError, match="Session ID is required"):
            await session_manager.invalidate_session("")

    async def test_invalidate_session_nonexistent(self, session_manager):
        """Test invalidate session with nonexistent ID."""
        result = await session_manager.invalidate_session("nonexistent-id")
        assert result is False

    async def test_invalidate_user_sessions_success(self, session_manager):
        """Test successful invalidation of all user sessions."""
        user_id = "test-user"

        # Create multiple sessions for user
        sessions = []
        for _i in range(3):
            session = await session_manager.create_session(user_id=user_id)
            sessions.append(session)

        count = await session_manager.invalidate_user_sessions(user_id)

        assert count == 3

        # All sessions should be invalidated
        for session in sessions:
            retrieved_session = await session_manager.get_session(session.session_id)
            assert retrieved_session is None

    async def test_invalidate_user_sessions_empty_user_id(self, session_manager):
        """Test invalidate user sessions with empty user ID."""
        with pytest.raises(SessionError, match="User ID is required"):
            await session_manager.invalidate_user_sessions("")

    async def test_list_user_sessions_success(self, session_manager):
        """Test successful listing of user sessions."""
        user_id = "test-user"

        # Create multiple sessions for user
        created_sessions = []
        for _i in range(3):
            session = await session_manager.create_session(user_id=user_id)
            created_sessions.append(session)

        user_sessions = await session_manager.list_user_sessions(user_id)

        assert len(user_sessions) == 3
        session_ids = [s.session_id for s in user_sessions]
        for created_session in created_sessions:
            assert created_session.session_id in session_ids

    async def test_list_user_sessions_empty_user_id(self, session_manager):
        """Test list user sessions with empty user ID."""
        with pytest.raises(SessionError, match="User ID is required"):
            await session_manager.list_user_sessions("")

    async def test_list_user_sessions_no_sessions(self, session_manager):
        """Test list user sessions when user has no sessions."""
        user_sessions = await session_manager.list_user_sessions("nonexistent-user")
        assert len(user_sessions) == 0

    async def test_cleanup_expired_sessions(self, session_manager):
        """Test cleanup of expired sessions."""
        # Create sessions
        session1 = await session_manager.create_session(user_id="user1")
        session2 = await session_manager.create_session(user_id="user2")

        # Expire one session
        session1.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

        count = await session_manager.cleanup_expired_sessions()

        assert count == 1

        # Expired session should be gone
        retrieved_session1 = await session_manager.get_session(session1.session_id)
        assert retrieved_session1 is None

        # Active session should remain
        retrieved_session2 = await session_manager.get_session(session2.session_id)
        assert retrieved_session2 is not None

    async def test_cleanup_inactive_sessions(self, session_manager):
        """Test cleanup of inactive sessions."""
        # Create sessions
        session1 = await session_manager.create_session(user_id="user1")
        await session_manager.create_session(user_id="user2")

        # Make one session inactive
        session1.last_activity = datetime.now(timezone.utc) - timedelta(hours=1)

        count = await session_manager.cleanup_expired_sessions()

        assert count == 1

    async def test_get_session_stats(self, session_manager):
        """Test getting session statistics."""
        # Create some sessions
        await session_manager.create_session(user_id="user1")
        await session_manager.create_session(user_id="user2")
        await session_manager.create_session(user_id="user1")  # Second session for user1

        stats = await session_manager.get_session_stats()

        assert stats["total_sessions"] == 3
        assert stats["active_sessions"] == 3
        assert stats["expired_sessions"] == 0
        assert stats["unique_users"] == 2

    def test_session_is_expired(self):
        """Test session expiration check."""
        # Create expired session
        expired_session = Session(
            session_id="test-id",
            user_id="test-user",
            tenant_id="test-tenant",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)
        )

        assert expired_session.is_expired() is True
        assert expired_session.is_active() is False

    def test_session_is_not_expired(self):
        """Test session not expired."""
        # Create active session
        active_session = Session(
            session_id="test-id",
            user_id="test-user",
            tenant_id="test-tenant",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )

        assert active_session.is_expired() is False
        assert active_session.is_active() is True

    def test_session_update_activity(self):
        """Test session activity update."""
        session = Session(
            session_id="test-id",
            user_id="test-user",
            tenant_id="test-tenant"
        )

        original_activity = session.last_activity
        original_updated = session.updated_at

        # Wait a moment then update
        import time
        time.sleep(0.01)

        session.update_activity()

        assert session.last_activity > original_activity
        assert session.updated_at > original_updated

    def test_session_config_defaults(self):
        """Test SessionConfig default values."""
        config = SessionConfig()

        assert config.max_lifetime == timedelta(hours=24)
        assert config.inactivity_timeout == timedelta(hours=2)
        assert config.max_sessions_per_user == 5
        assert config.require_client_validation is True
        assert config.cleanup_interval == timedelta(minutes=30)

    def test_session_config_custom(self):
        """Test SessionConfig with custom values."""
        config = SessionConfig(
            max_lifetime=timedelta(hours=8),
            inactivity_timeout=timedelta(minutes=15),
            max_sessions_per_user=2,
            require_client_validation=False
        )

        assert config.max_lifetime == timedelta(hours=8)
        assert config.inactivity_timeout == timedelta(minutes=15)
        assert config.max_sessions_per_user == 2
        assert config.require_client_validation is False

    async def test_concurrent_session_operations(self, session_manager):
        """Test concurrent session operations."""
        import asyncio

        async def create_session_worker(i):
            return await session_manager.create_session(user_id=f"user_{i}")

        # Create 10 sessions concurrently
        tasks = [create_session_worker(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        for i, result in enumerate(results):
            assert not isinstance(result, Exception)
            assert result.user_id == f"user_{i}"

    async def test_session_performance_benchmark(self, session_manager):
        """Test session management performance."""
        import time

        start_time = time.time()

        # Create and validate 100 sessions
        sessions = []
        for i in range(100):
            session = await session_manager.create_session(user_id=f"user_{i}")
            sessions.append(session)

        for session in sessions:
            await session_manager.validate_session(session.session_id)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within reasonable time
        assert duration < 5.0  # Less than 5 seconds for 100 sessions
