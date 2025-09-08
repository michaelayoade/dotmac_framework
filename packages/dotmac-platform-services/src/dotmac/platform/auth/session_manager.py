"""
Production-ready session management with Redis and memory backends.
"""

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class SessionStatus(str, Enum):
    """Session status enumeration."""

    ACTIVE = "active"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    SUSPICIOUS = "suspicious"


@dataclass
class SessionData:
    """Session data structure."""

    session_id: str
    user_id: str
    tenant_id: str | None
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    status: SessionStatus
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key in ["created_at", "last_accessed", "expires_at"]:
            if data[key]:
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionData":
        """Create from dictionary."""
        # Convert ISO strings back to datetime objects
        for key in ["created_at", "last_accessed", "expires_at"]:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])

        return cls(**data)

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at

    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status == SessionStatus.ACTIVE and not self.is_expired()


class SessionBackend(ABC):
    """Abstract base class for session storage backends."""

    @abstractmethod
    async def get_session(self, session_id: str) -> SessionData | None:
        """Get session by ID."""

    @abstractmethod
    async def store_session(self, session: SessionData) -> bool:
        """Store session data."""

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""

    @abstractmethod
    async def get_user_sessions(self, user_id: str) -> set[str]:
        """Get all session IDs for a user."""

    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions. Returns count of cleaned sessions."""


class MemorySessionBackend(SessionBackend):
    """In-memory session backend for development."""

    def __init__(self) -> None:
        self.sessions: dict[str, SessionData] = {}
        self.user_sessions: dict[str, set[str]] = {}

    async def get_session(self, session_id: str) -> SessionData | None:
        """Get session by ID."""
        session = self.sessions.get(session_id)
        if session and session.is_expired():
            await self.delete_session(session_id)
            return None
        return session

    async def store_session(self, session: SessionData) -> bool:
        """Store session data."""
        self.sessions[session.session_id] = session

        # Update user sessions index
        if session.user_id not in self.user_sessions:
            self.user_sessions[session.user_id] = set()
        self.user_sessions[session.user_id].add(session.session_id)

        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        session = self.sessions.pop(session_id, None)
        if session:
            # Remove from user sessions index
            user_sessions = self.user_sessions.get(session.user_id, set())
            user_sessions.discard(session_id)
            if not user_sessions:
                self.user_sessions.pop(session.user_id, None)
            return True
        return False

    async def get_user_sessions(self, user_id: str) -> set[str]:
        """Get all session IDs for a user."""
        return self.user_sessions.get(user_id, set()).copy()

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        expired_sessions = []
        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self.delete_session(session_id)

        return len(expired_sessions)


class RedisSessionBackend(SessionBackend):
    """Redis session backend for production."""

    def __init__(self, redis_url: str, key_prefix: str = "session:") -> None:
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis = None

    @property
    def redis(self):
        """Lazy Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(self.redis_url, decode_responses=True)
            except ImportError:
                raise ImportError("redis package required for RedisSessionBackend")
        return self._redis

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.key_prefix}{session_id}"

    def _user_sessions_key(self, user_id: str) -> str:
        """Generate Redis key for user sessions set."""
        return f"{self.key_prefix}user:{user_id}"

    async def get_session(self, session_id: str) -> SessionData | None:
        """Get session by ID."""
        try:
            data = await self.redis.get(self._session_key(session_id))
            if data:
                session_dict = json.loads(data)
                session = SessionData.from_dict(session_dict)

                # Check if expired
                if session.is_expired():
                    await self.delete_session(session_id)
                    return None

                return session
            return None
        except Exception as e:
            logger.error("Failed to get session", session_id=session_id, error=str(e))
            return None

    async def store_session(self, session: SessionData) -> bool:
        """Store session data."""
        try:
            session_key = self._session_key(session.session_id)
            user_sessions_key = self._user_sessions_key(session.user_id)

            # Calculate TTL
            ttl = int((session.expires_at - datetime.utcnow()).total_seconds())
            if ttl <= 0:
                return False

            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            pipe.setex(session_key, ttl, json.dumps(session.to_dict()))
            pipe.sadd(user_sessions_key, session.session_id)
            pipe.expire(user_sessions_key, ttl)
            await pipe.execute()

            return True
        except Exception as e:
            logger.error("Failed to store session", session_id=session.session_id, error=str(e))
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        try:
            # Get session first to find user_id
            session = await self.get_session(session_id)

            pipe = self.redis.pipeline()
            pipe.delete(self._session_key(session_id))

            if session:
                pipe.srem(self._user_sessions_key(session.user_id), session_id)

            results = await pipe.execute()
            return bool(results[0])  # Return True if session was deleted
        except Exception as e:
            logger.error("Failed to delete session", session_id=session_id, error=str(e))
            return False

    async def get_user_sessions(self, user_id: str) -> set[str]:
        """Get all session IDs for a user."""
        try:
            sessions = await self.redis.smembers(self._user_sessions_key(user_id))
            return set(sessions)
        except Exception as e:
            logger.error("Failed to get user sessions", user_id=user_id, error=str(e))
            return set()

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        # Redis automatically expires keys with TTL, so this is primarily for cleanup
        # of user session sets that might have stale references
        try:
            # This would require a more complex implementation with scanning
            # For now, return 0 as Redis handles expiration automatically
            return 0
        except Exception as e:
            logger.error("Failed to cleanup expired sessions", error=str(e))
            return 0


class SessionManager:
    """Production-ready session manager."""

    def __init__(
        self,
        backend: SessionBackend,
        default_ttl: int = 3600,  # 1 hour
        max_sessions_per_user: int = 10,
        cleanup_interval: int = 300,
    ) -> None:  # 5 minutes
        self.backend = backend
        self.default_ttl = default_ttl
        self.max_sessions_per_user = max_sessions_per_user
        self.cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

    async def create_session(
        self,
        user_id: str,
        tenant_id: str | None = None,
        ttl: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionData:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl or self.default_ttl)

        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            created_at=now,
            last_accessed=now,
            expires_at=expires_at,
            status=SessionStatus.ACTIVE,
            metadata=metadata or {},
        )

        # Enforce max sessions per user
        await self._enforce_session_limit(user_id)

        # Store session
        success = await self.backend.store_session(session)
        if not success:
            raise RuntimeError("Failed to store session")

        logger.info("Session created", session_id=session_id, user_id=user_id)
        return session

    async def get_session(self, session_id: str) -> SessionData | None:
        """Get session and update last accessed time."""
        session = await self.backend.get_session(session_id)
        if session and session.is_active():
            # Update last accessed time
            session.last_accessed = datetime.utcnow()
            await self.backend.store_session(session)

            # Periodic cleanup
            await self._maybe_cleanup()

        return session

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        session = await self.backend.get_session(session_id)
        if session:
            session.status = SessionStatus.INVALIDATED
            await self.backend.store_session(session)
            logger.info("Session invalidated", session_id=session_id)
            return True
        return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session completely."""
        success = await self.backend.delete_session(session_id)
        if success:
            logger.info("Session deleted", session_id=session_id)
        return success

    async def invalidate_user_sessions(
        self, user_id: str, exclude_session: str | None = None
    ) -> int:
        """Invalidate all sessions for a user."""
        session_ids = await self.backend.get_user_sessions(user_id)
        if exclude_session:
            session_ids.discard(exclude_session)

        count = 0
        for session_id in session_ids:
            if await self.invalidate_session(session_id):
                count += 1

        logger.info("User sessions invalidated", user_id=user_id, count=count)
        return count

    async def extend_session(self, session_id: str, additional_ttl: int) -> bool:
        """Extend session expiration time."""
        session = await self.backend.get_session(session_id)
        if session and session.is_active():
            session.expires_at += timedelta(seconds=additional_ttl)
            success = await self.backend.store_session(session)
            if success:
                logger.info(
                    "Session extended", session_id=session_id, additional_ttl=additional_ttl
                )
            return success
        return False

    async def get_user_sessions(self, user_id: str) -> list[SessionData]:
        """Get all active sessions for a user."""
        session_ids = await self.backend.get_user_sessions(user_id)
        sessions = []

        for session_id in session_ids:
            session = await self.backend.get_session(session_id)
            if session and session.is_active():
                sessions.append(session)

        return sessions

    async def _enforce_session_limit(self, user_id: str) -> None:
        """Enforce maximum sessions per user."""
        sessions = await self.get_user_sessions(user_id)
        if len(sessions) >= self.max_sessions_per_user:
            # Remove oldest sessions
            sessions.sort(key=lambda s: s.created_at)
            sessions_to_remove = sessions[: len(sessions) - self.max_sessions_per_user + 1]

            for session in sessions_to_remove:
                await self.delete_session(session.session_id)

    async def _maybe_cleanup(self) -> None:
        """Run cleanup if needed."""
        now = time.time()
        if now - self._last_cleanup > self.cleanup_interval:
            await self.cleanup_expired_sessions()
            self._last_cleanup = now

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        count = await self.backend.cleanup_expired_sessions()
        if count > 0:
            logger.info("Cleaned up expired sessions", count=count)
        return count

    async def get_session_stats(self) -> dict[str, Any]:
        """Get session statistics."""
        # This would need backend-specific implementation
        return {
            "backend_type": type(self.backend).__name__,
            "default_ttl": self.default_ttl,
            "max_sessions_per_user": self.max_sessions_per_user,
        }


# Factory functions
def create_memory_session_manager(**kwargs) -> SessionManager:
    """Create session manager with memory backend."""
    backend = MemorySessionBackend()
    return SessionManager(backend, **kwargs)


def create_redis_session_manager(redis_url: str, **kwargs) -> SessionManager:
    """Create session manager with Redis backend."""
    backend = RedisSessionBackend(redis_url)
    return SessionManager(backend, **kwargs)


def create_session_manager(backend_type: str = "memory", **config) -> SessionManager:
    """Create session manager with specified backend."""
    if backend_type.lower() == "redis":
        redis_url = config.pop("redis_url", "redis://localhost:6379")
        return create_redis_session_manager(redis_url, **config)
    if backend_type.lower() == "memory":
        return create_memory_session_manager(**config)
    raise ValueError(f"Unknown backend type: {backend_type}")
