"""
WebSocket Authentication Integration

Integrates WebSocket service with Developer B's authentication service
for secure WebSocket connections, session validation, and real-time permissions.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from ..auth.core.permissions import Permission, PermissionManager, UserPermissions
from ..auth.core.sessions import SessionInfo, SessionManager, SessionStatus
from ..auth.core.tokens import JWTTokenManager
from ..auth.middleware.audit_logging import AuditEvent as SecurityEvent
from ..auth.middleware.audit_logging import AuditLogger
from ..auth.middleware.rate_limiting import RateLimiter


@dataclass
class TokenValidationResult:
    """Token validation result structure."""

    is_valid: bool
    payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


logger = logging.getLogger(__name__)


@dataclass
class WebSocketAuthContext:
    """Authentication context for WebSocket connections."""

    user_id: str
    tenant_id: str
    session_id: str
    permissions: UserPermissions
    connection_id: str
    ip_address: str
    user_agent: str
    authenticated_at: datetime
    last_activity: datetime
    connection_metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.connection_metadata is None:
            self.connection_metadata = {}


class WebSocketAuthManager:
    """
    WebSocket authentication manager integrating with Developer B's auth service.

    Provides secure WebSocket authentication, session validation,
    and real-time permission checking.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        token_manager: JWTTokenManager,
        permission_manager: PermissionManager,
        rate_limiter: Optional[RateLimiter] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """
        Initialize WebSocket auth manager.

        Args:
            session_manager: Session management from auth service
            token_manager: JWT token management from auth service
            permission_manager: Permission validation from auth service
            rate_limiter: Optional rate limiting for connections
            audit_logger: Optional audit logging for security events
        """
        self.session_manager = session_manager
        self.token_manager = token_manager
        self.permission_manager = permission_manager
        self.rate_limiter = rate_limiter
        self.audit_logger = audit_logger

        # Track active WebSocket connections
        self._active_connections: Dict[str, WebSocketAuthContext] = {}
        self._user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids

        logger.info("WebSocket Authentication Manager initialized")

    async def authenticate_websocket_connection(
        self,
        connection_id: str,
        token: str,
        ip_address: str,
        user_agent: str,
        connection_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[WebSocketAuthContext]:
        """
        Authenticate a WebSocket connection using JWT token.

        Args:
            connection_id: Unique connection identifier
            token: JWT authentication token
            ip_address: Client IP address
            user_agent: Client user agent string
            connection_metadata: Optional connection metadata

        Returns:
            WebSocketAuthContext if authentication successful, None otherwise
        """
        try:
            # Rate limiting check
            if self.rate_limiter:
                rate_key = f"ws_auth:{ip_address}"
                allowed = await self.rate_limiter.check_rate_limit(
                    rate_key, window_seconds=60, max_requests=10
                )
                if not allowed:
                    await self._log_security_event(
                        "websocket_auth_rate_limited",
                        {"ip_address": ip_address, "connection_id": connection_id},
                    )
                    return None

            # Validate JWT token
            validation_result = await self.token_manager.validate_token(token)
            if not validation_result.is_valid:
                await self._log_security_event(
                    "websocket_auth_invalid_token",
                    {"connection_id": connection_id, "error": validation_result.error},
                )
                return None

            user_id = validation_result.payload.get("sub")
            tenant_id = validation_result.payload.get("tenant_id")
            session_id = validation_result.payload.get("session_id")

            if not all([user_id, tenant_id, session_id]):
                await self._log_security_event(
                    "websocket_auth_incomplete_token",
                    {
                        "connection_id": connection_id,
                        "missing_fields": [
                            f
                            for f, v in {
                                "user_id": user_id,
                                "tenant_id": tenant_id,
                                "session_id": session_id,
                            }.items()
                            if not v
                        ],
                    },
                )
                return None

            # Validate session
            session = await self.session_manager.get_session(session_id, tenant_id)
            if not session or session.status != SessionStatus.ACTIVE:
                await self._log_security_event(
                    "websocket_auth_invalid_session",
                    {
                        "connection_id": connection_id,
                        "session_id": session_id,
                        "user_id": user_id,
                    },
                )
                return None

            # Update session activity
            await self.session_manager.update_session_activity(session_id, tenant_id)

            # Create auth context
            auth_context = WebSocketAuthContext(
                user_id=user_id,
                tenant_id=tenant_id,
                session_id=session_id,
                permissions=session.permissions,
                connection_id=connection_id,
                ip_address=ip_address,
                user_agent=user_agent,
                authenticated_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                connection_metadata=connection_metadata or {},
            )

            # Track connection
            self._active_connections[connection_id] = auth_context
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

            await self._log_security_event(
                "websocket_auth_success",
                {
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                },
            )

            logger.info(
                f"WebSocket connection authenticated: {connection_id} for user {user_id}"
            )
            return auth_context

        except Exception as e:
            logger.error(f"WebSocket authentication failed: {e}")
            await self._log_security_event(
                "websocket_auth_error",
                {"connection_id": connection_id, "error": str(e)},
            )
            return None

    async def check_message_permission(
        self,
        connection_id: str,
        message_type: str,
        message_data: Dict[str, Any],
        required_permission: Optional[Permission] = None,
    ) -> bool:
        """
        Check if connection has permission to send a message.

        Args:
            connection_id: Connection identifier
            message_type: Type of message being sent
            message_data: Message payload
            required_permission: Required permission for this message type

        Returns:
            True if authorized, False otherwise
        """
        try:
            auth_context = self._active_connections.get(connection_id)
            if not auth_context:
                logger.warning(
                    f"Permission check for unknown connection: {connection_id}"
                )
                return False

            # Update last activity
            auth_context.last_activity = datetime.now(timezone.utc)

            # Check specific permission if required
            if required_permission:
                has_permission = self.permission_manager.check_permission(
                    auth_context.permissions, required_permission
                )

                if not has_permission:
                    await self._log_security_event(
                        "websocket_permission_denied",
                        {
                            "connection_id": connection_id,
                            "user_id": auth_context.user_id,
                            "message_type": message_type,
                            "required_permission": required_permission.value,
                        },
                    )
                    return False

            # Message-specific authorization logic
            if (
                message_type == "admin_broadcast"
                and not auth_context.permissions.is_admin()
            ):
                return False
            elif (
                message_type == "tenant_message"
                and message_data.get("tenant_id") != auth_context.tenant_id
            ):
                return False
            elif (
                message_type == "user_message"
                and message_data.get("target_user_id") != auth_context.user_id
            ):
                # Check if user can send messages to other users
                if not self.permission_manager.check_permission(
                    auth_context.permissions, Permission.USER_IMPERSONATE
                ):
                    return False

            return True

        except Exception as e:
            logger.error(f"Permission check failed for connection {connection_id}: {e}")
            return False

    async def disconnect_websocket(
        self, connection_id: str, reason: str = "client_disconnect"
    ) -> bool:
        """
        Handle WebSocket disconnection and cleanup.

        Args:
            connection_id: Connection identifier
            reason: Reason for disconnection

        Returns:
            True if cleanup successful
        """
        try:
            auth_context = self._active_connections.get(connection_id)
            if not auth_context:
                logger.debug(f"Disconnect for unknown connection: {connection_id}")
                return True

            # Remove from tracking
            del self._active_connections[connection_id]

            # Remove from user connections
            user_connections = self._user_connections.get(auth_context.user_id, set())
            user_connections.discard(connection_id)
            if not user_connections:
                del self._user_connections[auth_context.user_id]

            # Log disconnection
            await self._log_security_event(
                "websocket_disconnect",
                {
                    "connection_id": connection_id,
                    "user_id": auth_context.user_id,
                    "tenant_id": auth_context.tenant_id,
                    "reason": reason,
                    "session_duration_seconds": int(
                        (
                            datetime.now(timezone.utc) - auth_context.authenticated_at
                        ).total_seconds()
                    ),
                },
            )

            logger.info(f"WebSocket disconnected: {connection_id} ({reason})")
            return True

        except Exception as e:
            logger.error(f"WebSocket disconnect cleanup failed: {e}")
            return False

    async def get_user_connections(self, user_id: str) -> List[str]:
        """Get all active connection IDs for a user."""
        return list(self._user_connections.get(user_id, set()))

    async def disconnect_user_connections(
        self, user_id: str, reason: str = "user_logout"
    ) -> int:
        """
        Disconnect all WebSocket connections for a user.

        Args:
            user_id: User identifier
            reason: Reason for disconnection

        Returns:
            Number of connections disconnected
        """
        connections = await self.get_user_connections(user_id)
        disconnected = 0

        for connection_id in connections:
            success = await self.disconnect_websocket(connection_id, reason)
            if success:
                disconnected += 1

        logger.info(
            f"Disconnected {disconnected} WebSocket connections for user {user_id}"
        )
        return disconnected

    async def get_connection_context(
        self, connection_id: str
    ) -> Optional[WebSocketAuthContext]:
        """Get authentication context for a connection."""
        return self._active_connections.get(connection_id)

    async def get_active_connections_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections."""
        return {
            "total_connections": len(self._active_connections),
            "unique_users": len(self._user_connections),
            "connections_by_tenant": self._get_connections_by_tenant(),
            "average_session_duration": self._get_average_session_duration(),
        }

    def _get_connections_by_tenant(self) -> Dict[str, int]:
        """Get connection count by tenant."""
        tenant_counts = {}
        for context in self._active_connections.values():
            tenant_id = context.tenant_id
            tenant_counts[tenant_id] = tenant_counts.get(tenant_id, 0) + 1
        return tenant_counts

    def _get_average_session_duration(self) -> float:
        """Get average session duration in seconds."""
        if not self._active_connections:
            return 0.0

        now = datetime.now(timezone.utc)
        total_duration = sum(
            (now - context.authenticated_at).total_seconds()
            for context in self._active_connections.values()
        )

        return total_duration / len(self._active_connections)

    async def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event if audit logger available."""
        if self.audit_logger:
            event = SecurityEvent(
                event_type=event_type,
                user_id=details.get("user_id"),
                tenant_id=details.get("tenant_id"),
                ip_address=details.get("ip_address"),
                user_agent=details.get("user_agent"),
                resource=f"websocket:{details.get('connection_id')}",
                details=details,
                risk_score=self._calculate_risk_score(event_type, details),
                timestamp=datetime.now(timezone.utc),
            )
            await self.audit_logger.log_security_event(event)

    def _calculate_risk_score(self, event_type: str, details: Dict[str, Any]) -> float:
        """Calculate risk score for security event."""
        base_scores = {
            "websocket_auth_success": 0.1,
            "websocket_auth_invalid_token": 0.7,
            "websocket_auth_invalid_session": 0.6,
            "websocket_auth_rate_limited": 0.8,
            "websocket_permission_denied": 0.5,
            "websocket_disconnect": 0.1,
            "websocket_auth_error": 0.4,
        }
        return base_scores.get(event_type, 0.3)


class WebSocketAuthIntegrationFactory:
    """Factory for creating WebSocket auth integration components."""

    @staticmethod
    async def create_websocket_auth_manager(
        auth_components: Dict[str, Any]
    ) -> WebSocketAuthManager:
        """
        Create WebSocket auth manager with integrated auth components.

        Args:
            auth_components: Dict containing auth service components

        Returns:
            WebSocketAuthManager instance
        """
        try:
            session_manager = auth_components.get("session_manager")
            token_manager = auth_components.get("token_manager")
            permission_manager = auth_components.get("permission_manager")
            rate_limiter = auth_components.get("rate_limiter")
            audit_logger = auth_components.get("audit_logger")

            if not all([session_manager, token_manager, permission_manager]):
                raise ValueError("Missing required auth components")

            websocket_auth = WebSocketAuthManager(
                session_manager=session_manager,
                token_manager=token_manager,
                permission_manager=permission_manager,
                rate_limiter=rate_limiter,
                audit_logger=audit_logger,
            )

            logger.info("WebSocket auth manager created with integrated components")
            return websocket_auth

        except Exception as e:
            logger.error(f"Failed to create WebSocket auth manager: {e}")
            raise

    @staticmethod
    async def create_integrated_websocket_system(
        cache_service=None, auth_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create complete integrated WebSocket system with auth and cache.

        Args:
            cache_service: Cache service instance
            auth_config: Optional auth configuration

        Returns:
            Dict containing all integrated components
        """
        try:
            # Import auth components
            from ..auth.core.permissions import PermissionManager
            from ..auth.core.sessions import SessionManager
            from ..auth.core.tokens import JWTTokenManager
            from ..auth.middleware.audit_logging import AuditLogger
            from ..auth.middleware.rate_limiting import RateLimiter

            # Create auth components
            # Note: In real implementation, these would be properly configured
            # This is a simplified version for integration testing

            components = {}

            if cache_service:
                # Use cache-integrated components
                from ..auth.cache_integration import CacheIntegrationFactory

                cache_components = (
                    await CacheIntegrationFactory.create_integrated_components(
                        cache_service
                    )
                )

                components.update(cache_components)

                # Create WebSocket auth manager
                websocket_auth = (
                    await WebSocketAuthIntegrationFactory.create_websocket_auth_manager(
                        components
                    )
                )

                components["websocket_auth_manager"] = websocket_auth

            logger.info("Integrated WebSocket system with auth and cache created")
            return components

        except Exception as e:
            logger.error(f"Failed to create integrated WebSocket system: {e}")
            raise
