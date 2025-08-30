"""
Cache Service Integration for Authentication

Provides integration layers between the authentication service components
and Developer A's cache service, enabling distributed session storage,
token blacklisting, and rate limiting.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from ..cache import CacheManagerProtocol, create_cache_service
from .core.sessions import SessionInfo, SessionStore
from .core.tokens import TokenError
from .middleware.rate_limiting import RateLimitStore

logger = logging.getLogger(__name__)


class CacheServiceSessionStore(SessionStore):
    """
    Session store implementation using Developer A's cache service.

    Provides distributed session storage with tenant isolation,
    automatic expiration, and high performance.
    """

    def __init__(
        self,
        cache_manager: CacheManagerProtocol,
        session_namespace: str = "auth_sessions",
        user_sessions_namespace: str = "user_sessions",
    ):
        """
        Initialize cache service session store.

        Args:
            cache_manager: Cache manager from Developer A's service
            session_namespace: Namespace for session data
            user_sessions_namespace: Namespace for user session indexes
        """
        self.cache = cache_manager
        self.session_namespace = session_namespace
        self.user_sessions_namespace = user_sessions_namespace

        logger.info("Cache Service Session Store initialized")

    def _session_key(self, session_id: str) -> str:
        """Generate cache key for session."""
        return f"{self.session_namespace}:{session_id}"

    def _user_sessions_key(self, user_id: str, tenant_id: str) -> str:
        """Generate cache key for user sessions index."""
        return f"{self.user_sessions_namespace}:{tenant_id}:{user_id}"

    async def store_session(self, session: SessionInfo) -> bool:
        """Store session in cache with TTL."""
        try:
            session_key = self._session_key(session.session_id)
            user_key = self._user_sessions_key(session.user_id, session.tenant_id)

            # Calculate TTL in seconds
            ttl_seconds = max(1, int(session.time_until_expiry().total_seconds()))

            # Convert session to JSON-serializable dict
            session_data = session.to_dict()

            # Convert tenant_id to UUID for cache service
            tenant_uuid = UUID(session.tenant_id) if session.tenant_id else None

            # Store session data
            success = await self.cache.set(
                session_key, session_data, ttl=ttl_seconds, tenant_id=tenant_uuid
            )

            if success:
                # Add to user sessions index (store as set of session IDs)
                user_sessions = (
                    await self.cache.get(user_key, tenant_id=tenant_uuid) or []
                )
                if session.session_id not in user_sessions:
                    user_sessions.append(session.session_id)

                # Store user sessions index with same TTL
                await self.cache.set(
                    user_key,
                    user_sessions,
                    ttl=ttl_seconds + 300,  # Slightly longer TTL
                    tenant_id=tenant_uuid,
                )

            return success

        except Exception as e:
            logger.error(f"Failed to store session {session.session_id}: {e}")
            return False

    async def get_session(
        self, session_id: str, tenant_id: Optional[str] = None
    ) -> Optional[SessionInfo]:
        """Retrieve session from cache."""
        try:
            session_key = self._session_key(session_id)

            # Convert tenant_id to UUID if provided
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Get from cache with tenant isolation
            session_data = await self.cache.get(session_key, tenant_id=tenant_uuid)

            if not session_data:
                return None

            # Convert back to SessionInfo
            return SessionInfo.from_dict(session_data)

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def delete_session(
        self, session_id: str, tenant_id: Optional[str] = None
    ) -> bool:
        """Delete session from cache."""
        try:
            # First get session to find user and tenant for index cleanup
            session = await self.get_session(session_id, tenant_id)

            session_key = self._session_key(session_id)

            # Convert tenant_id to UUID
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Delete session with tenant isolation
            success = await self.cache.delete(session_key, tenant_id=tenant_uuid)

            # Clean up user sessions index
            if session and success:
                user_key = self._user_sessions_key(session.user_id, session.tenant_id)

                user_sessions = (
                    await self.cache.get(user_key, tenant_id=tenant_uuid) or []
                )
                if session_id in user_sessions:
                    user_sessions.remove(session_id)
                    await self.cache.set(user_key, user_sessions, tenant_id=tenant_uuid)

            return success

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    async def get_user_sessions(
        self, user_id: str, tenant_id: str
    ) -> List[SessionInfo]:
        """Get all sessions for a user."""
        try:
            tenant_uuid = UUID(tenant_id) if tenant_id else None
            user_key = self._user_sessions_key(user_id, tenant_id)

            # Get user session IDs
            session_ids = await self.cache.get(user_key, tenant_id=tenant_uuid) or []

            # Get all sessions concurrently
            tasks = [self.get_session(session_id) for session_id in session_ids]
            sessions_data = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter valid sessions
            valid_sessions = []
            for session in sessions_data:
                if (
                    isinstance(session, SessionInfo)
                    and session.is_active()
                    and session.user_id == user_id
                    and session.tenant_id == tenant_id
                ):
                    valid_sessions.append(session)

            return valid_sessions

        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Note: With Developer A's cache service, expired sessions are
        automatically cleaned up by Redis TTL, so this returns 0.
        """
        # Cache service handles TTL automatically
        logger.debug("Cache service handles automatic session cleanup via TTL")
        return 0


class CacheServiceTokenBlacklist:
    """
    Token blacklisting implementation using Developer A's cache service.

    Provides distributed token revocation for secure logout and
    token invalidation across multiple application instances.
    """

    def __init__(
        self,
        cache_manager: CacheManagerProtocol,
        blacklist_namespace: str = "token_blacklist",
    ):
        """
        Initialize token blacklist.

        Args:
            cache_manager: Cache manager from Developer A's service
            blacklist_namespace: Namespace for blacklisted tokens
        """
        self.cache = cache_manager
        self.blacklist_namespace = blacklist_namespace

        logger.info("Cache Service Token Blacklist initialized")

    def _blacklist_key(self, jti: str) -> str:
        """Generate cache key for blacklisted token."""
        return f"{self.blacklist_namespace}:{jti}"

    async def add_to_blacklist(
        self, jti: str, ttl_seconds: int, tenant_id: Optional[str] = None
    ) -> bool:
        """
        Add token to blacklist.

        Args:
            jti: JWT ID (unique identifier)
            ttl_seconds: Time until token naturally expires
            tenant_id: Optional tenant ID for isolation

        Returns:
            True if successfully blacklisted
        """
        try:
            blacklist_key = self._blacklist_key(jti)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Store blacklist entry with TTL matching token expiry
            success = await self.cache.set(
                blacklist_key,
                {
                    "blacklisted_at": datetime.now(timezone.utc).isoformat(),
                    "jti": jti,
                    "tenant_id": tenant_id,
                },
                ttl=ttl_seconds,
                tenant_id=tenant_uuid,
            )

            if success:
                logger.debug(f"Added token to blacklist: {jti}")

            return success

        except Exception as e:
            logger.error(f"Failed to blacklist token {jti}: {e}")
            return False

    async def is_blacklisted(self, jti: str, tenant_id: Optional[str] = None) -> bool:
        """
        Check if token is blacklisted.

        Args:
            jti: JWT ID to check
            tenant_id: Optional tenant ID for isolation

        Returns:
            True if token is blacklisted
        """
        try:
            blacklist_key = self._blacklist_key(jti)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Check if key exists in cache
            exists = await self.cache.exists(blacklist_key, tenant_id=tenant_uuid)

            return exists

        except Exception as e:
            logger.error(f"Failed to check blacklist for token {jti}: {e}")
            return False

    async def remove_from_blacklist(
        self, jti: str, tenant_id: Optional[str] = None
    ) -> bool:
        """
        Remove token from blacklist (for testing/admin purposes).

        Args:
            jti: JWT ID to remove
            tenant_id: Optional tenant ID for isolation

        Returns:
            True if successfully removed
        """
        try:
            blacklist_key = self._blacklist_key(jti)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            success = await self.cache.delete(blacklist_key, tenant_id=tenant_uuid)

            if success:
                logger.debug(f"Removed token from blacklist: {jti}")

            return success

        except Exception as e:
            logger.error(f"Failed to remove token from blacklist {jti}: {e}")
            return False


class CacheServiceRateLimitStore(RateLimitStore):
    """
    Rate limiting store implementation using Developer A's cache service.

    Provides distributed rate limiting with sliding windows,
    account lockouts, and high-performance counters.
    """

    def __init__(
        self,
        cache_manager: CacheManagerProtocol,
        rate_limit_namespace: str = "rate_limits",
        lockout_namespace: str = "lockouts",
    ):
        """
        Initialize rate limit store.

        Args:
            cache_manager: Cache manager from Developer A's service
            rate_limit_namespace: Namespace for rate limit counters
            lockout_namespace: Namespace for lockout entries
        """
        self.cache = cache_manager
        self.rate_limit_namespace = rate_limit_namespace
        self.lockout_namespace = lockout_namespace

        logger.info("Cache Service Rate Limit Store initialized")

    def _rate_limit_key(self, key: str) -> str:
        """Generate cache key for rate limit counter."""
        return f"{self.rate_limit_namespace}:{key}"

    def _lockout_key(self, key: str) -> str:
        """Generate cache key for lockout entry."""
        return f"{self.lockout_namespace}:{key}"

    async def increment_counter(
        self,
        key: str,
        window_seconds: int,
        max_requests: int,
        tenant_id: Optional[str] = None,
    ) -> Tuple[int, bool]:
        """
        Increment rate limit counter using sliding window.

        Args:
            key: Rate limit key (e.g., "ip:hash", "user:id")
            window_seconds: Time window in seconds
            max_requests: Maximum requests allowed in window
            tenant_id: Optional tenant ID for isolation

        Returns:
            Tuple of (current_count, is_allowed)
        """
        try:
            rate_key = self._rate_limit_key(key)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Get current counter data
            counter_data = await self.cache.get(rate_key, tenant_id=tenant_uuid) or {
                "requests": [],
                "window_seconds": window_seconds,
            }

            # Clean old entries (sliding window)
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(seconds=window_seconds)

            # Filter requests within current window
            requests = counter_data.get("requests", [])
            current_requests = [
                req_time
                for req_time in requests
                if datetime.fromisoformat(req_time) > window_start
            ]

            # Add current request
            current_requests.append(now.isoformat())

            # Update counter
            counter_data = {
                "requests": current_requests,
                "window_seconds": window_seconds,
                "last_updated": now.isoformat(),
            }

            # Store with TTL slightly longer than window
            await self.cache.set(
                rate_key, counter_data, ttl=window_seconds + 60, tenant_id=tenant_uuid
            )

            current_count = len(current_requests)
            is_allowed = current_count <= max_requests

            return current_count, is_allowed

        except Exception as e:
            logger.error(f"Failed to increment rate limit counter for {key}: {e}")
            # Fail open - allow request on error
            return 1, True

    async def get_counter(self, key: str, tenant_id: Optional[str] = None) -> int:
        """Get current counter value."""
        try:
            rate_key = self._rate_limit_key(key)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            counter_data = await self.cache.get(rate_key, tenant_id=tenant_uuid)
            if not counter_data:
                return 0

            return len(counter_data.get("requests", []))

        except Exception as e:
            logger.error(f"Failed to get counter for {key}: {e}")
            return 0

    async def reset_counter(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """Reset counter for key."""
        try:
            rate_key = self._rate_limit_key(key)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            success = await self.cache.delete(rate_key, tenant_id=tenant_uuid)

            if success:
                logger.debug(f"Reset rate limit counter: {key}")

            return success

        except Exception as e:
            logger.error(f"Failed to reset counter for {key}: {e}")
            return False

    async def add_lockout(
        self, key: str, duration_seconds: int, tenant_id: Optional[str] = None
    ) -> bool:
        """Add lockout for key."""
        try:
            lockout_key = self._lockout_key(key)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            lockout_data = {
                "locked_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": duration_seconds,
                "key": key,
            }

            success = await self.cache.set(
                lockout_key, lockout_data, ttl=duration_seconds, tenant_id=tenant_uuid
            )

            if success:
                logger.warning(
                    f"Added lockout for key: {key} (duration: {duration_seconds}s)"
                )

            return success

        except Exception as e:
            logger.error(f"Failed to add lockout for {key}: {e}")
            return False

    async def is_locked_out(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """Check if key is locked out."""
        try:
            lockout_key = self._lockout_key(key)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Check if lockout key exists (TTL handles expiry)
            exists = await self.cache.exists(lockout_key, tenant_id=tenant_uuid)

            return exists

        except Exception as e:
            logger.error(f"Failed to check lockout for {key}: {e}")
            return False

    async def remove_lockout(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """Remove lockout for key."""
        try:
            lockout_key = self._lockout_key(key)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            success = await self.cache.delete(lockout_key, tenant_id=tenant_uuid)

            if success:
                logger.info(f"Removed lockout for key: {key}")

            return success

        except Exception as e:
            logger.error(f"Failed to remove lockout for {key}: {e}")
            return False

    async def get_rate_limit_stats(
        self, key: str, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get rate limiting statistics for key."""
        try:
            rate_key = self._rate_limit_key(key)
            lockout_key = self._lockout_key(key)
            tenant_uuid = UUID(tenant_id) if tenant_id else None

            # Get counter data and lockout status
            counter_data = await self.cache.get(rate_key, tenant_id=tenant_uuid) or {}
            is_locked = await self.cache.exists(lockout_key, tenant_id=tenant_uuid)
            lockout_data = (
                await self.cache.get(lockout_key, tenant_id=tenant_uuid)
                if is_locked
                else {}
            )

            stats = {
                "key": key,
                "current_requests": len(counter_data.get("requests", [])),
                "window_seconds": counter_data.get("window_seconds", 0),
                "last_updated": counter_data.get("last_updated"),
                "is_locked_out": is_locked,
                "lockout_info": lockout_data,
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get rate limit stats for {key}: {e}")
            return {"key": key, "error": str(e)}


class CacheIntegrationFactory:
    """
    Factory for creating cache-integrated authentication components.

    Provides a central place to create all cache-integrated components
    with proper configuration and error handling.
    """

    @staticmethod
    async def create_integrated_components(
        cache_service_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create all cache-integrated authentication components.

        Args:
            cache_service_config: Optional cache service configuration

        Returns:
            Dict containing all integrated components
        """
        try:
            # Create cache service
            cache_service = create_cache_service()
            await cache_service.initialize()

            # Get cache manager
            cache_manager = cache_service.cache_manager

            # Create integrated components
            session_store = CacheServiceSessionStore(cache_manager)
            token_blacklist = CacheServiceTokenBlacklist(cache_manager)
            rate_limit_store = CacheServiceRateLimitStore(cache_manager)

            logger.info("Created all cache-integrated authentication components")

            return {
                "cache_service": cache_service,
                "cache_manager": cache_manager,
                "session_store": session_store,
                "token_blacklist": token_blacklist,
                "rate_limit_store": rate_limit_store,
            }

        except Exception as e:
            logger.error(f"Failed to create cache-integrated components: {e}")
            raise

    @staticmethod
    async def create_session_manager_with_cache():
        """Create SessionManager with cache integration."""
        from .core.sessions import SessionManager

        components = await CacheIntegrationFactory.create_integrated_components()

        session_manager = SessionManager(
            session_store=components["session_store"],
            session_timeout_hours=8,
            max_concurrent_sessions=5,
            enable_device_tracking=True,
        )

        return session_manager, components

    @staticmethod
    async def create_jwt_manager_with_cache():
        """Create JWTTokenManager with cache integration."""
        from .core.tokens import JWTTokenManager

        components = await CacheIntegrationFactory.create_integrated_components()

        jwt_manager = JWTTokenManager(
            issuer="dotmac-auth-service",
            access_token_expire_minutes=15,
            refresh_token_expire_days=30,
            blacklist_provider=components["token_blacklist"],
        )

        return jwt_manager, components

    @staticmethod
    async def create_rate_limiter_with_cache():
        """Create RateLimiter with cache integration."""
        from .middleware.rate_limiting import RateLimiter

        components = await CacheIntegrationFactory.create_integrated_components()

        rate_limiter = RateLimiter(
            store=components["rate_limit_store"],
            lockout_threshold=10,
            lockout_duration_minutes=15,
            enable_lockout=True,
        )

        return rate_limiter, components


# Convenience functions for easy integration
async def create_cache_integrated_auth_service() -> Dict[str, Any]:
    """
    Create a complete cache-integrated authentication service.

    Returns:
        Dict containing all authentication components with cache integration
    """
    try:
        # Create base components
        components = await CacheIntegrationFactory.create_integrated_components()

        # Create authentication components
        session_manager, _ = (
            await CacheIntegrationFactory.create_session_manager_with_cache()
        )
        jwt_manager, _ = await CacheIntegrationFactory.create_jwt_manager_with_cache()
        rate_limiter, _ = await CacheIntegrationFactory.create_rate_limiter_with_cache()

        # Create additional components
        from .core.multi_factor import MFAManager
        from .core.permissions import PermissionManager

        permission_manager = PermissionManager()
        mfa_manager = MFAManager(
            mfa_provider=None
        )  # Would need MFA provider implementation

        # Combine all components
        auth_service = {
            **components,
            "session_manager": session_manager,
            "jwt_manager": jwt_manager,
            "permission_manager": permission_manager,
            "mfa_manager": mfa_manager,
            "rate_limiter": rate_limiter,
        }

        logger.info("Created complete cache-integrated authentication service")
        return auth_service

    except Exception as e:
        logger.error(f"Failed to create cache-integrated auth service: {e}")
        raise


# Export integration components
__all__ = [
    "CacheServiceSessionStore",
    "CacheServiceTokenBlacklist",
    "CacheServiceRateLimitStore",
    "CacheIntegrationFactory",
    "create_cache_integrated_auth_service",
]
