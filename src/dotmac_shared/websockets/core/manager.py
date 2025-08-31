"""
WebSocket Connection Manager

High-performance WebSocket connection management with multi-tenant support,
heartbeat monitoring, and graceful connection lifecycle handling.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from .config import WebSocketConfig
from .events import EventManager, WebSocketEvent

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""

    websocket: WebSocket
    connection_id: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    rooms: Set[str] = field(default_factory=set)
    subscriptions: Set[str] = field(default_factory=set)


class MessageEnvelope(BaseModel):
    """WebSocket message envelope for structured communication."""

    type: str
    data: Dict[str, Any] = {}
    room: Optional[str] = None
    target: Optional[str] = None
    tenant_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    message_id: Optional[str] = None


class WebSocketManager:
    """
    Production-ready WebSocket connection manager with advanced features.

    Features:
    - Multi-tenant connection isolation
    - Heartbeat monitoring and auto-cleanup
    - Room-based message routing
    - Connection metadata and state management
    - Graceful shutdown and connection migration
    - Comprehensive metrics and monitoring
    """

    def __init__(
        self,
        config: WebSocketConfig,
        event_manager: Optional[EventManager] = None,
        redis_backend=None,
    ):
        self.config = config
        self.event_manager = event_manager
        self.redis_backend = redis_backend

        # Connection storage
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self.rooms: Dict[str, Set[str]] = defaultdict(set)
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)
        self.tenant_connections: Dict[str, Set[str]] = defaultdict(set)

        # Heartbeat monitoring
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False

        # Metrics
        self.metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "heartbeats_sent": 0,
            "connections_dropped": 0,
            "errors": 0,
        }

        # Event hooks
        self._connection_hooks: List[Callable] = []
        self._disconnection_hooks: List[Callable] = []
        self._message_hooks: List[Callable] = []

    async def start(self):
        """Start the WebSocket manager and background tasks."""
        if self._is_running:
            return

        self._is_running = True

        # Start background tasks
        if self.config.heartbeat_interval > 0:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

        self._cleanup_task = asyncio.create_task(self._connection_cleanup())

        logger.info(
            f"WebSocket manager started with max_connections={self.config.max_connections}"
        )

    async def stop(self):
        """Stop the WebSocket manager and clean up connections."""
        self._is_running = False

        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all active connections
        await self._close_all_connections()

        logger.info("WebSocket manager stopped")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Accept and register a WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Optional user identifier
            tenant_id: Optional tenant identifier
            connection_id: Optional custom connection ID
            metadata: Optional connection metadata

        Returns:
            Connection ID string

        Raises:
            ValueError: If max connections exceeded
        """
        if len(self.active_connections) >= self.config.max_connections:
            await websocket.close(code=1013, reason="Server overloaded")
            raise ValueError("Maximum connections exceeded")

        # Generate connection ID if not provided
        if not connection_id:
            connection_id = str(uuid4())

        # Accept the WebSocket connection
        await websocket.accept()

        # Create connection info
        conn_info = ConnectionInfo(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            tenant_id=tenant_id,
            metadata=metadata or {},
        )

        # Register connection
        self.active_connections[connection_id] = conn_info

        # Update indexes
        if user_id:
            self.user_connections[user_id].add(connection_id)
        if tenant_id:
            self.tenant_connections[tenant_id].add(connection_id)

        # Update metrics
        self.metrics["total_connections"] += 1
        self.metrics["active_connections"] = len(self.active_connections)

        # Call connection hooks
        for hook in self._connection_hooks:
            try:
                await hook(connection_id, conn_info)
            except Exception as e:
                logger.error(f"Connection hook error: {e}")

        # Send connection confirmation
        await self._send_system_message(
            connection_id,
            {
                "type": "connection_established",
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        logger.info(
            f"WebSocket connected: {connection_id} (user: {user_id}, tenant: {tenant_id})"
        )
        return connection_id

    async def disconnect(
        self, connection_id: str, code: int = 1000, reason: str = "Normal closure"
    ):
        """
        Disconnect and cleanup a WebSocket connection.

        Args:
            connection_id: Connection identifier
            code: WebSocket close code
            reason: Closure reason
        """
        conn_info = self.active_connections.get(connection_id)
        if not conn_info:
            return

        try:
            # Close WebSocket if still open
            if conn_info.websocket.client_state.name != "DISCONNECTED":
                await conn_info.websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.warning(f"Error closing WebSocket {connection_id}: {e}")

        # Remove from rooms
        for room in conn_info.rooms.copy():
            await self.leave_room(connection_id, room)

        # Update indexes
        if conn_info.user_id:
            self.user_connections[conn_info.user_id].discard(connection_id)
            if not self.user_connections[conn_info.user_id]:
                del self.user_connections[conn_info.user_id]

        if conn_info.tenant_id:
            self.tenant_connections[conn_info.tenant_id].discard(connection_id)
            if not self.tenant_connections[conn_info.tenant_id]:
                del self.tenant_connections[conn_info.tenant_id]

        # Remove connection
        del self.active_connections[connection_id]

        # Update metrics
        self.metrics["active_connections"] = len(self.active_connections)
        self.metrics["connections_dropped"] += 1

        # Call disconnection hooks
        for hook in self._disconnection_hooks:
            try:
                await hook(connection_id, conn_info)
            except Exception as e:
                logger.error(f"Disconnection hook error: {e}")

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_message(
        self,
        connection_id: str,
        message: Union[Dict[str, Any], MessageEnvelope],
        ensure_delivery: bool = False,
    ) -> bool:
        """
        Send message to specific connection.

        Args:
            connection_id: Target connection ID
            message: Message data or envelope
            ensure_delivery: Whether to ensure message delivery

        Returns:
            True if message sent successfully, False otherwise
        """
        conn_info = self.active_connections.get(connection_id)
        if not conn_info:
            logger.warning(f"Connection not found: {connection_id}")
            return False

        try:
            # Convert to envelope if needed
            if not isinstance(message, MessageEnvelope):
                envelope = MessageEnvelope(
                    type=message.get("type", "message"),
                    data=message.get("data", message),
                    timestamp=datetime.utcnow(),
                    message_id=str(uuid4()),
                )
            else:
                envelope = message

            # Tenant isolation check
            if (
                self.config.tenant_isolation
                and conn_info.tenant_id
                and envelope.tenant_id
                and conn_info.tenant_id != envelope.tenant_id
            ):
                logger.warning(f"Tenant isolation violation: {connection_id}")
                return False

            # Send message
            message_json = (
                envelope.model_dump_json()
                if isinstance(envelope, MessageEnvelope)
                else json.dumps(message)
            )

            await conn_info.websocket.send_text(message_json)

            # Update metrics
            self.metrics["messages_sent"] += 1

            # Call message hooks
            for hook in self._message_hooks:
                try:
                    await hook(connection_id, envelope, "outbound")
                except Exception as e:
                    logger.error(f"Message hook error: {e}")

            return True

        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            self.metrics["errors"] += 1

            # Disconnect on send errors
            await self.disconnect(connection_id, code=1011, reason="Send error")
            return False

    async def broadcast_to_room(
        self,
        room: str,
        message: Union[Dict[str, Any], MessageEnvelope],
        exclude: Optional[Set[str]] = None,
        tenant_id: Optional[str] = None,
    ) -> int:
        """
        Broadcast message to all connections in a room.

        Args:
            room: Room name
            message: Message to broadcast
            exclude: Connection IDs to exclude
            tenant_id: Optional tenant filter

        Returns:
            Number of connections message was sent to
        """
        exclude = exclude or set()
        connections_in_room = self.rooms.get(room, set())
        successful_sends = 0

        # Create broadcast tasks
        tasks = []
        for connection_id in connections_in_room:
            if connection_id in exclude:
                continue

            conn_info = self.active_connections.get(connection_id)
            if not conn_info:
                continue

            # Tenant filtering
            if tenant_id and conn_info.tenant_id != tenant_id:
                continue

            task = self.send_message(connection_id, message)
            tasks.append(task)

        # Execute broadcasts concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_sends = sum(1 for result in results if result is True)

        logger.debug(
            f"Broadcast to room '{room}': {successful_sends}/{len(tasks)} successful"
        )
        return successful_sends

    async def broadcast_to_tenant(
        self,
        tenant_id: str,
        message: Union[Dict[str, Any], MessageEnvelope],
        exclude: Optional[Set[str]] = None,
    ) -> int:
        """
        Broadcast message to all connections for a tenant.

        Args:
            tenant_id: Tenant identifier
            message: Message to broadcast
            exclude: Connection IDs to exclude

        Returns:
            Number of connections message was sent to
        """
        exclude = exclude or set()
        tenant_connections = self.tenant_connections.get(tenant_id, set())
        successful_sends = 0

        # Create broadcast tasks
        tasks = []
        for connection_id in tenant_connections:
            if connection_id not in exclude:
                task = self.send_message(connection_id, message)
                tasks.append(task)

        # Execute broadcasts concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_sends = sum(1 for result in results if result is True)

        logger.debug(
            f"Broadcast to tenant '{tenant_id}': {successful_sends}/{len(tasks)} successful"
        )
        return successful_sends

    async def join_room(self, connection_id: str, room: str) -> bool:
        """Add connection to a room."""
        conn_info = self.active_connections.get(connection_id)
        if not conn_info:
            return False

        self.rooms[room].add(connection_id)
        conn_info.rooms.add(room)

        logger.debug(f"Connection {connection_id} joined room '{room}'")
        return True

    async def leave_room(self, connection_id: str, room: str) -> bool:
        """Remove connection from a room."""
        conn_info = self.active_connections.get(connection_id)
        if not conn_info:
            return False

        self.rooms[room].discard(connection_id)
        conn_info.rooms.discard(room)

        # Clean up empty rooms
        if not self.rooms[room]:
            del self.rooms[room]

        logger.debug(f"Connection {connection_id} left room '{room}'")
        return True

    async def get_room_connections(
        self, room: str, tenant_id: Optional[str] = None
    ) -> Set[str]:
        """Get all connection IDs in a room, optionally filtered by tenant."""
        connections = self.rooms.get(room, set())

        if tenant_id:
            # Filter by tenant
            tenant_connections = set()
            for conn_id in connections:
                conn_info = self.active_connections.get(conn_id)
                if conn_info and conn_info.tenant_id == tenant_id:
                    tenant_connections.add(conn_id)
            return tenant_connections

        return connections.copy()

    async def update_heartbeat(self, connection_id: str):
        """Update heartbeat timestamp for connection."""
        conn_info = self.active_connections.get(connection_id)
        if conn_info:
            conn_info.last_heartbeat = datetime.utcnow()

    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection information."""
        return self.active_connections.get(connection_id)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            **self.metrics,
            "rooms": len(self.rooms),
            "users_online": len(self.user_connections),
            "tenants_active": len(self.tenant_connections),
        }

    # Event hooks
    def add_connection_hook(self, hook: Callable):
        """Add connection establishment hook."""
        self._connection_hooks.append(hook)

    def add_disconnection_hook(self, hook: Callable):
        """Add connection disconnection hook."""
        self._disconnection_hooks.append(hook)

    def add_message_hook(self, hook: Callable):
        """Add message processing hook."""
        self._message_hooks.append(hook)

    # Private methods
    async def _send_system_message(self, connection_id: str, data: Dict[str, Any]):
        """Send system message to connection."""
        message = MessageEnvelope(type="system", data=data, timestamp=datetime.utcnow())
        await self.send_message(connection_id, message)

    async def _heartbeat_monitor(self):
        """Background task to monitor connection heartbeats."""
        while self._is_running:
            try:
                now = datetime.utcnow()
                heartbeat_tasks = []

                for connection_id, conn_info in list(self.active_connections.items()):
                    # Send heartbeat
                    if conn_info.websocket.client_state.name == "CONNECTED":
                        task = self._send_system_message(
                            connection_id,
                            {"type": "heartbeat", "timestamp": now.isoformat()},
                        )
                        heartbeat_tasks.append(task)

                # Send heartbeats concurrently
                if heartbeat_tasks:
                    await asyncio.gather(*heartbeat_tasks, return_exceptions=True)
                    self.metrics["heartbeats_sent"] += len(heartbeat_tasks)

                await asyncio.sleep(self.config.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                await asyncio.sleep(5)  # Error backoff

    async def _connection_cleanup(self):
        """Background task to cleanup stale connections."""
        while self._is_running:
            try:
                now = datetime.utcnow()
                timeout_threshold = now - timedelta(
                    seconds=self.config.connection_timeout
                )

                stale_connections = []
                for connection_id, conn_info in list(self.active_connections.items()):
                    if (
                        conn_info.last_heartbeat < timeout_threshold
                        or conn_info.websocket.client_state.name == "DISCONNECTED"
                    ):
                        stale_connections.append(connection_id)

                # Clean up stale connections
                for connection_id in stale_connections:
                    await self.disconnect(
                        connection_id, code=1001, reason="Connection timeout"
                    )

                if stale_connections:
                    logger.info(
                        f"Cleaned up {len(stale_connections)} stale connections"
                    )

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection cleanup error: {e}")
                await asyncio.sleep(10)  # Error backoff

    async def _close_all_connections(self):
        """Close all active connections."""
        connection_ids = list(self.active_connections.keys())
        tasks = []

        for connection_id in connection_ids:
            task = self.disconnect(connection_id, code=1001, reason="Server shutdown")
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"Closed {len(tasks)} connections during shutdown")
