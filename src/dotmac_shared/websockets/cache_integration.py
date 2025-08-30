"""
WebSocket Cache Integration

Integrates WebSocket service with Developer A's cache service for
message persistence, connection state management, and real-time coordination.
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from ..cache import CacheManagerProtocol, create_cache_service

logger = logging.getLogger(__name__)


@dataclass
class CachedMessage:
    """Cached WebSocket message structure."""

    message_id: str
    connection_id: str
    user_id: str
    tenant_id: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    ttl_seconds: Optional[int] = None
    delivery_status: str = "pending"  # pending, delivered, failed
    retry_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ConnectionState:
    """Cached WebSocket connection state."""

    connection_id: str
    user_id: str
    tenant_id: str
    session_id: str
    server_id: str
    connected_at: datetime
    last_activity: datetime
    status: str = "active"  # active, idle, disconnected
    connection_metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.connection_metadata is None:
            self.connection_metadata = {}


class CacheServiceWebSocketStore:
    """
    WebSocket message and connection state caching using Developer A's cache service.

    Provides distributed message persistence, connection state management,
    and real-time coordination across multiple WebSocket server instances.
    """

    def __init__(
        self,
        cache_manager: CacheManagerProtocol,
        message_namespace: str = "ws_messages",
        connection_namespace: str = "ws_connections",
        room_namespace: str = "ws_rooms",
        server_id: str = "ws-server-1",
    ):
        """
        Initialize WebSocket cache store.

        Args:
            cache_manager: Cache manager from Developer A's service
            message_namespace: Namespace for message storage
            connection_namespace: Namespace for connection state
            room_namespace: Namespace for room management
            server_id: Unique identifier for this WebSocket server instance
        """
        self.cache = cache_manager
        self.message_namespace = message_namespace
        self.connection_namespace = connection_namespace
        self.room_namespace = room_namespace
        self.server_id = server_id

        logger.info(f"WebSocket Cache Store initialized (server: {server_id})")

    def _message_key(self, message_id: str) -> str:
        """Generate cache key for message."""
        return f"{self.message_namespace}:{message_id}"

    def _connection_key(self, connection_id: str) -> str:
        """Generate cache key for connection state."""
        return f"{self.connection_namespace}:{connection_id}"

    def _user_connections_key(self, user_id: str) -> str:
        """Generate cache key for user connections index."""
        return f"{self.connection_namespace}:user:{user_id}"

    def _room_key(self, room_id: str) -> str:
        """Generate cache key for room members."""
        return f"{self.room_namespace}:{room_id}"

    def _server_connections_key(self) -> str:
        """Generate cache key for server connections."""
        return f"{self.connection_namespace}:server:{self.server_id}"

    async def store_message(
        self, message: CachedMessage, tenant_id: Optional[str] = None
    ) -> bool:
        """Store message in cache for persistence and delivery guarantees."""
        try:
            message_key = self._message_key(message.message_id)
            tenant_uuid = UUID(tenant_id) if tenant_id else UUID(message.tenant_id)

            # Convert message to dict for storage
            message_data = asdict(message)
            message_data["timestamp"] = message.timestamp.isoformat()
            message_data["stored_at"] = datetime.now(timezone.utc).isoformat()

            # Calculate TTL (default 24 hours)
            ttl_seconds = message.ttl_seconds or 86400

            success = await self.cache.set(
                message_key, message_data, ttl=ttl_seconds, tenant_id=tenant_uuid
            )

            if success:
                # Add to user message queue for offline delivery
                await self._add_to_user_message_queue(message, tenant_uuid)

            return success

        except Exception as e:
            logger.error(f"Failed to store message {message.message_id}: {e}")
            return False

    async def get_message(
        self, message_id: str, tenant_id: str
    ) -> Optional[CachedMessage]:
        """Retrieve message from cache."""
        try:
            message_key = self._message_key(message_id)
            tenant_uuid = UUID(tenant_id)

            message_data = await self.cache.get(message_key, tenant_id=tenant_uuid)
            if not message_data:
                return None

            # Convert back to CachedMessage
            message_data["timestamp"] = datetime.fromisoformat(
                message_data["timestamp"]
            )
            del message_data["stored_at"]  # Remove storage metadata

            return CachedMessage(**message_data)

        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            return None

    async def update_message_status(
        self,
        message_id: str,
        status: str,
        tenant_id: str,
        retry_count: Optional[int] = None,
    ) -> bool:
        """Update message delivery status."""
        try:
            message = await self.get_message(message_id, tenant_id)
            if not message:
                return False

            message.delivery_status = status
            if retry_count is not None:
                message.retry_count = retry_count

            return await self.store_message(message, tenant_id)

        except Exception as e:
            logger.error(f"Failed to update message status {message_id}: {e}")
            return False

    async def store_connection_state(
        self, connection_state: ConnectionState, tenant_id: Optional[str] = None
    ) -> bool:
        """Store connection state in cache for coordination across servers."""
        try:
            connection_key = self._connection_key(connection_state.connection_id)
            tenant_uuid = (
                UUID(tenant_id) if tenant_id else UUID(connection_state.tenant_id)
            )

            # Convert to dict for storage
            state_data = asdict(connection_state)
            state_data["connected_at"] = connection_state.connected_at.isoformat()
            state_data["last_activity"] = connection_state.last_activity.isoformat()
            state_data["cached_at"] = datetime.now(timezone.utc).isoformat()

            # Store connection state (expires when connection should timeout)
            ttl_seconds = 3600  # 1 hour timeout

            success = await self.cache.set(
                connection_key, state_data, ttl=ttl_seconds, tenant_id=tenant_uuid
            )

            if success:
                # Update user connections index
                await self._update_user_connections_index(connection_state, tenant_uuid)

                # Update server connections index
                await self._update_server_connections_index(
                    connection_state.connection_id, tenant_uuid
                )

            return success

        except Exception as e:
            logger.error(
                f"Failed to store connection state {connection_state.connection_id}: {e}"
            )
            return False

    async def get_connection_state(
        self, connection_id: str, tenant_id: str
    ) -> Optional[ConnectionState]:
        """Get connection state from cache."""
        try:
            connection_key = self._connection_key(connection_id)
            tenant_uuid = UUID(tenant_id)

            state_data = await self.cache.get(connection_key, tenant_id=tenant_uuid)
            if not state_data:
                return None

            # Convert back to ConnectionState
            state_data["connected_at"] = datetime.fromisoformat(
                state_data["connected_at"]
            )
            state_data["last_activity"] = datetime.fromisoformat(
                state_data["last_activity"]
            )
            del state_data["cached_at"]  # Remove storage metadata

            return ConnectionState(**state_data)

        except Exception as e:
            logger.error(f"Failed to get connection state {connection_id}: {e}")
            return None

    async def remove_connection_state(self, connection_id: str, tenant_id: str) -> bool:
        """Remove connection state when disconnected."""
        try:
            # Get connection state first for cleanup
            connection_state = await self.get_connection_state(connection_id, tenant_id)

            connection_key = self._connection_key(connection_id)
            tenant_uuid = UUID(tenant_id)

            success = await self.cache.delete(connection_key, tenant_id=tenant_uuid)

            if success and connection_state:
                # Clean up indexes
                await self._remove_from_user_connections_index(
                    connection_state, tenant_uuid
                )
                await self._remove_from_server_connections_index(
                    connection_id, tenant_uuid
                )

            return success

        except Exception as e:
            logger.error(f"Failed to remove connection state {connection_id}: {e}")
            return False

    async def get_user_connections(self, user_id: str, tenant_id: str) -> List[str]:
        """Get all active connection IDs for a user."""
        try:
            user_connections_key = self._user_connections_key(user_id)
            tenant_uuid = UUID(tenant_id)

            connection_ids = await self.cache.get(
                user_connections_key, tenant_id=tenant_uuid
            )
            return connection_ids or []

        except Exception as e:
            logger.error(f"Failed to get user connections for {user_id}: {e}")
            return []

    async def join_room(self, room_id: str, connection_id: str, tenant_id: str) -> bool:
        """Add connection to a room."""
        try:
            room_key = self._room_key(room_id)
            tenant_uuid = UUID(tenant_id)

            # Get current room members
            members = await self.cache.get(room_key, tenant_id=tenant_uuid) or []

            if connection_id not in members:
                members.append(connection_id)

                success = await self.cache.set(
                    room_key, members, ttl=86400, tenant_id=tenant_uuid  # 24 hours
                )

                if success:
                    logger.info(f"Connection {connection_id} joined room {room_id}")
                return success

            return True  # Already in room

        except Exception as e:
            logger.error(f"Failed to join room {room_id}: {e}")
            return False

    async def leave_room(
        self, room_id: str, connection_id: str, tenant_id: str
    ) -> bool:
        """Remove connection from a room."""
        try:
            room_key = self._room_key(room_id)
            tenant_uuid = UUID(tenant_id)

            # Get current room members
            members = await self.cache.get(room_key, tenant_id=tenant_uuid) or []

            if connection_id in members:
                members.remove(connection_id)

                success = await self.cache.set(
                    room_key, members, ttl=86400, tenant_id=tenant_uuid  # 24 hours
                )

                if success:
                    logger.info(f"Connection {connection_id} left room {room_id}")
                return success

            return True  # Not in room

        except Exception as e:
            logger.error(f"Failed to leave room {room_id}: {e}")
            return False

    async def get_room_members(self, room_id: str, tenant_id: str) -> List[str]:
        """Get all connection IDs in a room."""
        try:
            room_key = self._room_key(room_id)
            tenant_uuid = UUID(tenant_id)

            members = await self.cache.get(room_key, tenant_id=tenant_uuid)
            return members or []

        except Exception as e:
            logger.error(f"Failed to get room members for {room_id}: {e}")
            return []

    async def get_server_connections(self, tenant_id: str) -> List[str]:
        """Get all connection IDs managed by this server."""
        try:
            server_connections_key = self._server_connections_key()
            tenant_uuid = UUID(tenant_id)

            connections = await self.cache.get(
                server_connections_key, tenant_id=tenant_uuid
            )
            return connections or []

        except Exception as e:
            logger.error(f"Failed to get server connections: {e}")
            return []

    async def get_pending_messages(
        self, user_id: str, tenant_id: str, limit: int = 100
    ) -> List[CachedMessage]:
        """Get pending messages for a user (for offline delivery)."""
        try:
            # This is a simplified implementation
            # In production, you'd want a more efficient message queue structure
            user_queue_key = f"{self.message_namespace}:queue:{user_id}"
            tenant_uuid = UUID(tenant_id)

            message_ids = (
                await self.cache.get(user_queue_key, tenant_id=tenant_uuid) or []
            )

            messages = []
            for message_id in message_ids[:limit]:
                message = await self.get_message(message_id, tenant_id)
                if message and message.delivery_status == "pending":
                    messages.append(message)

            return messages

        except Exception as e:
            logger.error(f"Failed to get pending messages for {user_id}: {e}")
            return []

    async def health_check(self) -> bool:
        """Check if cache service is healthy."""
        try:
            return await self.cache.ping()
        except Exception as e:
            logger.error(f"WebSocket cache health check failed: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket cache statistics."""
        try:
            cache_stats = await self.cache.get_stats()

            # Get server-specific stats
            server_connections = await self.get_server_connections("system")

            return {
                "cache_stats": cache_stats,
                "websocket_cache_healthy": await self.health_check(),
                "server_id": self.server_id,
                "server_connections": len(server_connections),
                "namespaces": {
                    "messages": self.message_namespace,
                    "connections": self.connection_namespace,
                    "rooms": self.room_namespace,
                },
            }
        except Exception as e:
            logger.error(f"Failed to get WebSocket cache stats: {e}")
            return {"error": str(e)}

    async def _add_to_user_message_queue(
        self, message: CachedMessage, tenant_uuid: UUID
    ):
        """Add message to user's offline delivery queue."""
        try:
            user_queue_key = f"{self.message_namespace}:queue:{message.user_id}"

            # Get current queue
            queue = await self.cache.get(user_queue_key, tenant_id=tenant_uuid) or []

            # Add message ID to queue
            queue.append(message.message_id)

            # Limit queue size (keep last 1000 messages)
            if len(queue) > 1000:
                queue = queue[-1000:]

            await self.cache.set(
                user_queue_key, queue, ttl=86400 * 7, tenant_id=tenant_uuid  # 7 days
            )

        except Exception as e:
            logger.error(f"Failed to update user message queue: {e}")

    async def _update_user_connections_index(
        self, connection_state: ConnectionState, tenant_uuid: UUID
    ):
        """Update user connections index."""
        try:
            user_connections_key = self._user_connections_key(connection_state.user_id)

            connections = (
                await self.cache.get(user_connections_key, tenant_id=tenant_uuid) or []
            )

            if connection_state.connection_id not in connections:
                connections.append(connection_state.connection_id)

                await self.cache.set(
                    user_connections_key,
                    connections,
                    ttl=3600,  # 1 hour
                    tenant_id=tenant_uuid,
                )

        except Exception as e:
            logger.error(f"Failed to update user connections index: {e}")

    async def _remove_from_user_connections_index(
        self, connection_state: ConnectionState, tenant_uuid: UUID
    ):
        """Remove from user connections index."""
        try:
            user_connections_key = self._user_connections_key(connection_state.user_id)

            connections = (
                await self.cache.get(user_connections_key, tenant_id=tenant_uuid) or []
            )

            if connection_state.connection_id in connections:
                connections.remove(connection_state.connection_id)

                if connections:
                    await self.cache.set(
                        user_connections_key,
                        connections,
                        ttl=3600,
                        tenant_id=tenant_uuid,
                    )
                else:
                    await self.cache.delete(user_connections_key, tenant_id=tenant_uuid)

        except Exception as e:
            logger.error(f"Failed to remove from user connections index: {e}")

    async def _update_server_connections_index(
        self, connection_id: str, tenant_uuid: UUID
    ):
        """Update server connections index."""
        try:
            server_connections_key = self._server_connections_key()

            connections = (
                await self.cache.get(server_connections_key, tenant_id=tenant_uuid)
                or []
            )

            if connection_id not in connections:
                connections.append(connection_id)

                await self.cache.set(
                    server_connections_key, connections, ttl=3600, tenant_id=tenant_uuid
                )

        except Exception as e:
            logger.error(f"Failed to update server connections index: {e}")

    async def _remove_from_server_connections_index(
        self, connection_id: str, tenant_uuid: UUID
    ):
        """Remove from server connections index."""
        try:
            server_connections_key = self._server_connections_key()

            connections = (
                await self.cache.get(server_connections_key, tenant_id=tenant_uuid)
                or []
            )

            if connection_id in connections:
                connections.remove(connection_id)

                await self.cache.set(
                    server_connections_key, connections, ttl=3600, tenant_id=tenant_uuid
                )

        except Exception as e:
            logger.error(f"Failed to remove from server connections index: {e}")


class WebSocketCacheIntegrationFactory:
    """Factory for creating WebSocket cache integration components."""

    @staticmethod
    async def create_websocket_cache_store(
        cache_service_config: Optional[Dict[str, Any]] = None,
        server_id: str = "ws-server-1",
    ) -> CacheServiceWebSocketStore:
        """Create WebSocket cache store."""
        try:
            # Create cache service
            cache_service = create_cache_service()
            await cache_service.initialize()

            # Get cache manager
            cache_manager = cache_service.cache_manager

            # Create WebSocket cache store
            ws_cache_store = CacheServiceWebSocketStore(
                cache_manager, server_id=server_id
            )

            logger.info(f"WebSocket cache store created (server: {server_id})")
            return ws_cache_store

        except Exception as e:
            logger.error(f"Failed to create WebSocket cache store: {e}")
            raise

    @staticmethod
    async def create_integrated_websocket_components(
        cache_service_config: Optional[Dict[str, Any]] = None,
        server_id: str = "ws-server-1",
    ) -> Dict[str, Any]:
        """Create all WebSocket cache-integrated components."""
        try:
            # Create cache service
            cache_service = create_cache_service()
            await cache_service.initialize()

            # Get cache manager
            cache_manager = cache_service.cache_manager

            # Create components
            components = {
                "websocket_cache_store": CacheServiceWebSocketStore(
                    cache_manager, server_id=server_id
                ),
                "cache_service": cache_service,
                "cache_manager": cache_manager,
                "server_id": server_id,
            }

            logger.info(
                f"All WebSocket cache integration components created (server: {server_id})"
            )
            return components

        except Exception as e:
            logger.error(f"Failed to create WebSocket cache components: {e}")
            raise
