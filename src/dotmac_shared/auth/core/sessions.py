"""
Session Management System

Implements secure session management with:
- Distributed session storage (Redis integration)
- Concurrent session handling
- Session timeout and cleanup
- Session hijacking protection
- Device/browser tracking
- Integration with cache service
"""

import hashlib
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session status enumeration."""

    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPICIOUS = "suspicious"


@dataclass
class SessionInfo:
    """Session information container."""

    session_id: str
    user_id: str
    tenant_id: str
    created_at: datetime
    last_accessed_at: datetime
    expires_at: datetime
    status: SessionStatus
    ip_address: str
    user_agent: str
    device_fingerprint: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) >= self.expires_at

    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status == SessionStatus.ACTIVE and not self.is_expired()

    def time_until_expiry(self) -> timedelta:
        """Get time until session expires."""
        return max(timedelta(0), self.expires_at - datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert datetime objects to ISO format
        data["created_at"] = self.created_at.isoformat()
        data["last_accessed_at"] = self.last_accessed_at.isoformat()
        data["expires_at"] = self.expires_at.isoformat()
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionInfo":
        """Create from dictionary."""
        # Convert ISO format back to datetime
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_accessed_at"] = datetime.fromisoformat(data["last_accessed_at"])
        data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        data["status"] = SessionStatus(data["status"])
        return cls(**data)


@dataclass
class DeviceInfo:
    """Device information for session tracking."""

    device_fingerprint: str
    ip_address: str
    user_agent: str
    browser: Optional[str] = None
    os: Optional[str] = None
    device_type: Optional[str] = None
    location: Optional[Dict[str, Any]] = None

    def is_trusted(self, other: "DeviceInfo") -> bool:
        """Check if this device matches another trusted device."""
        return (
            self.device_fingerprint == other.device_fingerprint
            and self.ip_address == other.ip_address
            and self.user_agent == other.user_agent
        )


class SessionStore(ABC):
    """Abstract session storage interface."""

    @abstractmethod
    async def store_session(self, session: SessionInfo) -> bool:
        """Store session data."""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Retrieve session data."""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete session data."""
        pass

    @abstractmethod
    async def get_user_sessions(
        self, user_id: str, tenant_id: str
    ) -> List[SessionInfo]:
        """Get all active sessions for a user."""
        pass

    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count."""
        pass


class CacheServiceSessionStore(SessionStore):
    """Session store implementation using cache service (Redis)."""

    def __init__(self, cache_service: Any, key_prefix: str = "session"):
        """
        Initialize with cache service.

        Args:
            cache_service: Cache service instance (from Developer A)
            key_prefix: Prefix for session keys in cache
        """
        self.cache_service = cache_service
        self.key_prefix = key_prefix

    def _session_key(self, session_id: str) -> str:
        """Generate cache key for session."""
        return f"{self.key_prefix}:{session_id}"

    def _user_sessions_key(self, user_id: str, tenant_id: str) -> str:
        """Generate cache key for user sessions index."""
        return f"{self.key_prefix}_user:{tenant_id}:{user_id}"

    async def store_session(self, session: SessionInfo) -> bool:
        """Store session in cache with TTL."""
        try:
            session_key = self._session_key(session.session_id)
            user_key = self._user_sessions_key(session.user_id, session.tenant_id)

            # Calculate TTL in seconds
            ttl = max(1, int(session.time_until_expiry().total_seconds()))

            # Store session data
            session_data = json.dumps(session.to_dict())
            await self.cache_service.set(session_key, session_data, ttl=ttl)

            # Add to user sessions index
            await self.cache_service.sadd(user_key, session.session_id)
            await self.cache_service.expire(user_key, ttl)

            return True

        except Exception as e:
            logger.error(f"Failed to store session {session.session_id}: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Retrieve session from cache."""
        try:
            session_key = self._session_key(session_id)
            session_data = await self.cache_service.get(session_key)

            if not session_data:
                return None

            data = json.loads(session_data)
            return SessionInfo.from_dict(data)

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete session from cache."""
        try:
            session_key = self._session_key(session_id)

            # Get session to remove from user index
            session = await self.get_session(session_id)
            if session:
                user_key = self._user_sessions_key(session.user_id, session.tenant_id)
                await self.cache_service.srem(user_key, session_id)

            # Delete session
            result = await self.cache_service.delete(session_key)
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    async def get_user_sessions(
        self, user_id: str, tenant_id: str
    ) -> List[SessionInfo]:
        """Get all sessions for a user."""
        try:
            user_key = self._user_sessions_key(user_id, tenant_id)
            session_ids = await self.cache_service.smembers(user_key)

            sessions = []
            for session_id in session_ids:
                session = await self.get_session(session_id)
                if session and session.is_active():
                    sessions.append(session)

            return sessions

        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        # Note: Redis TTL will automatically clean up expired sessions
        # This method is for manual cleanup if needed
        try:
            # Get all session keys
            pattern = f"{self.key_prefix}:*"
            session_keys = await self.cache_service.keys(pattern)

            cleaned_count = 0
            for key in session_keys:
                session_data = await self.cache_service.get(key)
                if session_data:
                    try:
                        data = json.loads(session_data)
                        session = SessionInfo.from_dict(data)
                        if session.is_expired():
                            await self.cache_service.delete(key)
                            cleaned_count += 1
                    except Exception:
                        # Invalid session data, clean it up
                        await self.cache_service.delete(key)
                        cleaned_count += 1

            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0


class InMemorySessionStore(SessionStore):
    """In-memory session store for development/testing."""

    def __init__(self):
        """Initialize in-memory storage."""
        self._sessions: Dict[str, SessionInfo] = {}
        self._user_sessions: Dict[str, set] = {}

    async def store_session(self, session: SessionInfo) -> bool:
        """Store session in memory."""
        self._sessions[session.session_id] = session

        user_key = f"{session.tenant_id}:{session.user_id}"
        if user_key not in self._user_sessions:
            self._user_sessions[user_key] = set()
        self._user_sessions[user_key].add(session.session_id)

        return True

    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session from memory."""
        return self._sessions.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete session from memory."""
        session = self._sessions.pop(session_id, None)
        if session:
            user_key = f"{session.tenant_id}:{session.user_id}"
            if user_key in self._user_sessions:
                self._user_sessions[user_key].discard(session_id)
            return True
        return False

    async def get_user_sessions(
        self, user_id: str, tenant_id: str
    ) -> List[SessionInfo]:
        """Get all sessions for a user."""
        user_key = f"{tenant_id}:{user_id}"
        session_ids = self._user_sessions.get(user_key, set())

        sessions = []
        for session_id in session_ids:
            session = self._sessions.get(session_id)
            if session and session.is_active():
                sessions.append(session)

        return sessions

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        expired_sessions = [
            session_id
            for session_id, session in self._sessions.items()
            if session.is_expired()
        ]

        for session_id in expired_sessions:
            await self.delete_session(session_id)

        return len(expired_sessions)


class SessionManager:
    """
    Comprehensive session management system.

    Features:
    - Distributed session storage with Redis
    - Concurrent session management
    - Session security and hijacking protection
    - Device tracking and trusted devices
    - Automatic session cleanup
    - Session analytics and monitoring
    """

    def __init__(
        self,
        session_store: SessionStore,
        session_timeout_hours: int = 8,
        max_concurrent_sessions: int = 5,
        enable_device_tracking: bool = True,
        suspicious_activity_threshold: int = 3,
    ):
        """
        Initialize session manager.

        Args:
            session_store: Session storage backend
            session_timeout_hours: Session timeout in hours
            max_concurrent_sessions: Maximum concurrent sessions per user
            enable_device_tracking: Enable device fingerprinting
            suspicious_activity_threshold: Threshold for suspicious activity detection
        """
        self.session_store = session_store
        self.session_timeout_hours = session_timeout_hours
        self.max_concurrent_sessions = max_concurrent_sessions
        self.enable_device_tracking = enable_device_tracking
        self.suspicious_activity_threshold = suspicious_activity_threshold

        logger.info(
            f"Session Manager initialized (timeout: {session_timeout_hours}h, max_sessions: {max_concurrent_sessions})"
        )

    async def create_session(
        self,
        user_id: str,
        tenant_id: str,
        ip_address: str,
        user_agent: str,
        device_fingerprint: Optional[str] = None,
        remember_device: bool = False,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionInfo:
        """
        Create new user session.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            ip_address: Client IP address
            user_agent: Client user agent
            device_fingerprint: Device fingerprint for tracking
            remember_device: Whether to remember this device
            additional_metadata: Additional session metadata

        Returns:
            Created SessionInfo object
        """
        try:
            # Generate unique session ID
            session_id = self._generate_session_id()

            # Check for suspicious activity
            await self._check_suspicious_activity(user_id, tenant_id, ip_address)

            # Create session
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(hours=self.session_timeout_hours)

            session = SessionInfo(
                session_id=session_id,
                user_id=user_id,
                tenant_id=tenant_id,
                created_at=now,
                last_accessed_at=now,
                expires_at=expires_at,
                status=SessionStatus.ACTIVE,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                metadata=additional_metadata or {},
            )

            # Add device tracking metadata
            if self.enable_device_tracking:
                session.metadata["device_info"] = self._parse_device_info(user_agent)
                session.metadata["remember_device"] = remember_device

            # Enforce concurrent session limit
            await self._enforce_session_limit(user_id, tenant_id)

            # Store session
            await self.session_store.store_session(session)

            logger.info(
                f"Created session {session_id} for user {user_id} (tenant: {tenant_id})"
            )
            return session

        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            SessionInfo object or None if not found/expired
        """
        session = await self.session_store.get_session(session_id)

        if not session:
            return None

        # Check if session is expired
        if session.is_expired():
            await self.terminate_session(session_id)
            return None

        return session

    async def update_session_activity(self, session_id: str) -> bool:
        """
        Update session last accessed time.

        Args:
            session_id: Session identifier

        Returns:
            True if session was updated
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                return False

            # Update last accessed time
            session.last_accessed_at = datetime.now(timezone.utc)

            # Store updated session
            await self.session_store.store_session(session)

            logger.debug(f"Updated activity for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update session activity {session_id}: {e}")
            return False

    async def extend_session(
        self, session_id: str, extend_by_hours: Optional[int] = None
    ) -> bool:
        """
        Extend session expiration time.

        Args:
            session_id: Session identifier
            extend_by_hours: Hours to extend by (default: session_timeout_hours)

        Returns:
            True if session was extended
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                return False

            extend_by = extend_by_hours or self.session_timeout_hours
            session.expires_at = datetime.now(timezone.utc) + timedelta(hours=extend_by)

            await self.session_store.store_session(session)

            logger.info(f"Extended session {session_id} by {extend_by} hours")
            return True

        except Exception as e:
            logger.error(f"Failed to extend session {session_id}: {e}")
            return False

    async def terminate_session(self, session_id: str, reason: str = "logout") -> bool:
        """
        Terminate a session.

        Args:
            session_id: Session identifier
            reason: Termination reason for logging

        Returns:
            True if session was terminated
        """
        try:
            session = await self.get_session(session_id)
            if session:
                logger.info(f"Terminating session {session_id} (reason: {reason})")

            return await self.session_store.delete_session(session_id)

        except Exception as e:
            logger.error(f"Failed to terminate session {session_id}: {e}")
            return False

    async def terminate_all_user_sessions(
        self, user_id: str, tenant_id: str, exclude_session_id: Optional[str] = None
    ) -> int:
        """
        Terminate all sessions for a user.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            exclude_session_id: Session to exclude from termination

        Returns:
            Number of sessions terminated
        """
        try:
            sessions = await self.session_store.get_user_sessions(user_id, tenant_id)

            terminated_count = 0
            for session in sessions:
                if session.session_id != exclude_session_id:
                    if await self.terminate_session(
                        session.session_id, "user_logout_all"
                    ):
                        terminated_count += 1

            logger.info(f"Terminated {terminated_count} sessions for user {user_id}")
            return terminated_count

        except Exception as e:
            logger.error(f"Failed to terminate user sessions for {user_id}: {e}")
            return 0

    async def get_user_sessions(
        self, user_id: str, tenant_id: str
    ) -> List[SessionInfo]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            List of active sessions
        """
        return await self.session_store.get_user_sessions(user_id, tenant_id)

    async def validate_session_security(
        self, session_id: str, ip_address: str, user_agent: str
    ) -> bool:
        """
        Validate session security (detect hijacking).

        Args:
            session_id: Session identifier
            ip_address: Current IP address
            user_agent: Current user agent

        Returns:
            True if session is valid and secure
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                return False

            # Check IP address consistency
            if session.ip_address != ip_address:
                logger.warning(
                    f"IP address mismatch for session {session_id}: {session.ip_address} != {ip_address}"
                )
                # Mark as suspicious but don't immediately terminate
                session.status = SessionStatus.SUSPICIOUS
                session.metadata["security_warnings"] = session.metadata.get(
                    "security_warnings", []
                )
                session.metadata["security_warnings"].append(
                    {
                        "type": "ip_mismatch",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "original_ip": session.ip_address,
                        "current_ip": ip_address,
                    }
                )
                await self.session_store.store_session(session)

            # Check user agent consistency
            if session.user_agent != user_agent:
                logger.warning(f"User agent mismatch for session {session_id}")
                session.metadata["security_warnings"] = session.metadata.get(
                    "security_warnings", []
                )
                session.metadata["security_warnings"].append(
                    {
                        "type": "user_agent_mismatch",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "original_ua": session.user_agent,
                        "current_ua": user_agent,
                    }
                )
                await self.session_store.store_session(session)

            # Terminate session if too many security warnings
            warnings = session.metadata.get("security_warnings", [])
            if len(warnings) >= self.suspicious_activity_threshold:
                await self.terminate_session(session_id, "security_violation")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to validate session security {session_id}: {e}")
            return False

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        try:
            count = await self.session_store.cleanup_expired_sessions()
            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")
            return count

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0

    def _generate_session_id(self) -> str:
        """Generate cryptographically secure session ID."""
        return str(uuid.uuid4())

    async def _enforce_session_limit(self, user_id: str, tenant_id: str):
        """Enforce maximum concurrent sessions per user."""
        try:
            sessions = await self.session_store.get_user_sessions(user_id, tenant_id)

            if len(sessions) >= self.max_concurrent_sessions:
                # Terminate oldest sessions
                sessions.sort(key=lambda s: s.last_accessed_at)
                sessions_to_remove = len(sessions) - self.max_concurrent_sessions + 1

                for i in range(sessions_to_remove):
                    await self.terminate_session(
                        sessions[i].session_id, "session_limit_exceeded"
                    )

                logger.info(
                    f"Enforced session limit for user {user_id}: terminated {sessions_to_remove} old sessions"
                )

        except Exception as e:
            logger.error(f"Failed to enforce session limit for user {user_id}: {e}")

    async def _check_suspicious_activity(
        self, user_id: str, tenant_id: str, ip_address: str
    ):
        """Check for suspicious login activity."""
        try:
            # Get recent sessions for this user
            sessions = await self.session_store.get_user_sessions(user_id, tenant_id)

            # Check for multiple IPs in short time period
            recent_sessions = [
                s
                for s in sessions
                if (datetime.now(timezone.utc) - s.created_at).total_seconds()
                < 3600  # Last hour
            ]

            unique_ips = set(s.ip_address for s in recent_sessions)
            if len(unique_ips) > 3:  # More than 3 different IPs in an hour
                logger.warning(
                    f"Suspicious activity detected for user {user_id}: {len(unique_ips)} IPs in last hour"
                )
                # Could implement additional security measures here

        except Exception as e:
            logger.error(f"Failed to check suspicious activity for user {user_id}: {e}")

    def _parse_device_info(self, user_agent: str) -> Dict[str, Any]:
        """Parse device information from user agent."""
        # Basic user agent parsing (in production, use a proper user agent parser)
        device_info = {
            "user_agent": user_agent,
            "browser": "unknown",
            "os": "unknown",
            "device_type": "unknown",
        }

        ua_lower = user_agent.lower()

        # Browser detection
        if "chrome" in ua_lower:
            device_info["browser"] = "Chrome"
        elif "firefox" in ua_lower:
            device_info["browser"] = "Firefox"
        elif "safari" in ua_lower:
            device_info["browser"] = "Safari"
        elif "edge" in ua_lower:
            device_info["browser"] = "Edge"

        # OS detection
        if "windows" in ua_lower:
            device_info["os"] = "Windows"
        elif "macos" in ua_lower or "mac os" in ua_lower:
            device_info["os"] = "macOS"
        elif "linux" in ua_lower:
            device_info["os"] = "Linux"
        elif "android" in ua_lower:
            device_info["os"] = "Android"
        elif "ios" in ua_lower:
            device_info["os"] = "iOS"

        # Device type detection
        if "mobile" in ua_lower:
            device_info["device_type"] = "mobile"
        elif "tablet" in ua_lower:
            device_info["device_type"] = "tablet"
        else:
            device_info["device_type"] = "desktop"

        return device_info
