"""WebSocket Manager for Real-time Frontend Integration."""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import redis.asyncio as redis

logger = logging.getLogger(__name__, timezone)


class EventType(Enum):
    """WebSocket event types."""
    
    BILLING_UPDATE = "billing_update"
    PAYMENT_PROCESSED = "payment_processed"
    INVOICE_GENERATED = "invoice_generated"
    SERVICE_ACTIVATED = "service_activated"
    SERVICE_SUSPENDED = "service_suspended"
    CUSTOMER_CREATED = "customer_created"
    TICKET_UPDATED = "ticket_updated"
    NETWORK_ALERT = "network_alert"
    SYSTEM_NOTIFICATION = "system_notification"
    USER_SESSION = "user_session"


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    
    event_type: EventType
    data: Dict[str, Any]
    tenant_id: str
    user_id: Optional[str] = None
    timestamp: str = None
    message_id: str = None
    
    def __post_init__(self):
        """  Post Init   operation."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
        }


@dataclass
class ConnectionInfo:
    """WebSocket connection information."""
    
    websocket: WebSocket
    user_id: str
    tenant_id: str
    session_id: str
    connected_at: datetime
    subscriptions: Set[str]
    
    def __post_init__(self):
        """  Post Init   operation."""
        if isinstance(self.subscriptions, list):
            self.subscriptions = set(self.subscriptions)


class WebSocketManager:
    """
    WebSocket Manager for real-time communication with frontend.
    
    Features:
    - Multi-tenant connection management
    - Event broadcasting and subscriptions
    - Connection health monitoring
    - Redis pub/sub for horizontal scaling
    - Automatic reconnection handling
    """
    
    def __init__(self, redis_url: str = None):
        """Initialize WebSocket manager."""
        from dotmac_isp.core.settings import get_settings
        
        self.connections: Dict[str, ConnectionInfo] = {}
        self.tenant_connections: Dict[str, Set[str]] = {}
        self.user_connections: Dict[str, Set[str]] = {}
        self.subscription_connections: Dict[str, Set[str]] = {}
        
        # Redis for pub/sub across multiple instances - use centralized settings
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub = None
        
        # Event handlers
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        
        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()
        self.is_running = False
        
    async def start(self):
        """Start the WebSocket manager."""
        if self.is_running:
            return
            
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(self.redis_url)
            self.pubsub = self.redis_client.pubsub()
            
            # Subscribe to WebSocket events channel
            await self.pubsub.subscribe("websocket:events")
            
            # Start background tasks
            self._start_background_tasks()
            
            self.is_running = True
            logger.info("WebSocket manager started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket manager: {e}")
            raise
    
    async def stop(self):
        """Stop the WebSocket manager."""
        if not self.is_running:
            return
            
        self.is_running = False
        
        # Close all connections
        await self._close_all_connections()
        
        # Stop background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        self.background_tasks.clear()
        
        # Close Redis connections
        if self.pubsub:
            await self.pubsub.unsubscribe("websocket:events")
            await self.pubsub.close()
            
        if self.redis_client:
            await self.redis_client.close()
            
        logger.info("WebSocket manager stopped")
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        tenant_id: str,
        session_id: str = None
    ) -> str:
        """
        Connect a WebSocket client.
        
        Args:
            websocket: WebSocket connection
            user_id: User ID
            tenant_id: Tenant ID
            session_id: Session ID (optional, will be generated if not provided)
            
        Returns:
            Connection ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
            
        connection_id = f"{tenant_id}:{user_id}:{session_id}"
        
        try:
            await websocket.accept()
            
            # Create connection info
            connection_info = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                tenant_id=tenant_id,
                session_id=session_id,
                connected_at=datetime.now(timezone.utc),
                subscriptions=set()
            )
            
            # Store connection
            self.connections[connection_id] = connection_info
            
            # Update indexes
            if tenant_id not in self.tenant_connections:
                self.tenant_connections[tenant_id] = set()
            self.tenant_connections[tenant_id].add(connection_id)
            
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
            
            # Send welcome message
            welcome_message = WebSocketMessage(
                event_type=EventType.USER_SESSION,
                data={
                    "action": "connected",
                    "connection_id": connection_id,
                    "session_id": session_id,
                },
                tenant_id=tenant_id,
                user_id=user_id,
            )
            
            await self._send_to_connection(connection_id, welcome_message)
            
            logger.info(f"WebSocket connected: {connection_id}")
            return connection_id
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket {connection_id}: {e}")
            raise
    
    async def disconnect(self, connection_id: str):
        """
        Disconnect a WebSocket client.
        
        Args:
            connection_id: Connection ID
        """
        if connection_id not in self.connections:
            return
            
        connection_info = self.connections[connection_id]
        
        try:
            # Close WebSocket if still open
            if connection_info.websocket.client_state == WebSocketState.CONNECTED:
                await connection_info.websocket.close()
                
        except Exception as e:
            logger.error(f"Error closing WebSocket {connection_id}: {e}")
        
        # Remove from indexes
        self.tenant_connections[connection_info.tenant_id].discard(connection_id)
        self.user_connections[connection_info.user_id].discard(connection_id)
        
        for subscription in connection_info.subscriptions:
            if subscription in self.subscription_connections:
                self.subscription_connections[subscription].discard(connection_id)
        
        # Remove connection
        del self.connections[connection_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def subscribe(self, connection_id: str, subscription: str):
        """
        Subscribe connection to event type.
        
        Args:
            connection_id: Connection ID
            subscription: Subscription name (e.g., "billing_updates", "network_alerts")
        """
        if connection_id not in self.connections:
            logger.warning(f"Cannot subscribe unknown connection: {connection_id}")
            return
            
        connection_info = self.connections[connection_id]
        connection_info.subscriptions.add(subscription)
        
        if subscription not in self.subscription_connections:
            self.subscription_connections[subscription] = set()
        self.subscription_connections[subscription].add(connection_id)
        
        logger.debug(f"Connection {connection_id} subscribed to {subscription}")
    
    async def unsubscribe(self, connection_id: str, subscription: str):
        """
        Unsubscribe connection from event type.
        
        Args:
            connection_id: Connection ID
            subscription: Subscription name
        """
        if connection_id not in self.connections:
            return
            
        connection_info = self.connections[connection_id]
        connection_info.subscriptions.discard(subscription)
        
        if subscription in self.subscription_connections:
            self.subscription_connections[subscription].discard(connection_id)
        
        logger.debug(f"Connection {connection_id} unsubscribed from {subscription}")
    
    async def broadcast_to_tenant(
        self,
        tenant_id: str,
        message: WebSocketMessage,
        subscription_filter: str = None
    ):
        """
        Broadcast message to all connections for a tenant.
        
        Args:
            tenant_id: Tenant ID
            message: Message to broadcast
            subscription_filter: Only send to connections with this subscription
        """
        if tenant_id not in self.tenant_connections:
            return
            
        connection_ids = self.tenant_connections[tenant_id].model_copy()
        
        # Apply subscription filter
        if subscription_filter:
            filtered_ids = set()
            if subscription_filter in self.subscription_connections:
                subscription_ids = self.subscription_connections[subscription_filter]
                filtered_ids = connection_ids.intersection(subscription_ids)
            connection_ids = filtered_ids
        
        await self._send_to_connections(connection_ids, message)
        
        # Publish to Redis for other instances
        await self._publish_to_redis(message, tenant_id, subscription_filter)
    
    async def broadcast_to_user(
        self,
        user_id: str,
        message: WebSocketMessage,
        subscription_filter: str = None
    ):
        """
        Broadcast message to all connections for a user.
        
        Args:
            user_id: User ID
            message: Message to broadcast
            subscription_filter: Only send to connections with this subscription
        """
        if user_id not in self.user_connections:
            return
            
        connection_ids = self.user_connections[user_id].model_copy()
        
        # Apply subscription filter
        if subscription_filter:
            filtered_ids = set()
            if subscription_filter in self.subscription_connections:
                subscription_ids = self.subscription_connections[subscription_filter]
                filtered_ids = connection_ids.intersection(subscription_ids)
            connection_ids = filtered_ids
        
        await self._send_to_connections(connection_ids, message)
    
    async def broadcast_to_subscription(
        self,
        subscription: str,
        message: WebSocketMessage,
        tenant_filter: str = None
    ):
        """
        Broadcast message to all connections with a subscription.
        
        Args:
            subscription: Subscription name
            message: Message to broadcast
            tenant_filter: Only send to connections with this tenant
        """
        if subscription not in self.subscription_connections:
            return
            
        connection_ids = self.subscription_connections[subscription].model_copy()
        
        # Apply tenant filter
        if tenant_filter:
            filtered_ids = set()
            for conn_id in connection_ids:
                if conn_id in self.connections:
                    conn_info = self.connections[conn_id]
                    if conn_info.tenant_id == tenant_filter:
                        filtered_ids.add(conn_id)
            connection_ids = filtered_ids
        
        await self._send_to_connections(connection_ids, message)
    
    def register_event_handler(self, event_type: EventType, handler: Callable):
        """
        Register an event handler.
        
        Args:
            event_type: Event type to handle
            handler: Handler function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def emit_event(self, message: WebSocketMessage, target_type: str = "tenant", target_id: str = None, subscription_filter: str = None):
        """
        Emit an event to WebSocket connections.
        
        Args:
            message: Message to emit
            target_type: Target type ("tenant", "user", "subscription", "all")
            target_id: Target ID (tenant_id, user_id, subscription name)
            subscription_filter: Optional subscription filter
        """
        # Call registered event handlers
        if message.event_type in self.event_handlers:
            for handler in self.event_handlers[message.event_type]:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Event handler failed for {message.event_type}: {e}")
        
        # Broadcast message
        if target_type == "tenant":
            await self.broadcast_to_tenant(target_id or message.tenant_id, message, subscription_filter)
        elif target_type == "user":
            await self.broadcast_to_user(target_id or message.user_id, message, subscription_filter)
        elif target_type == "subscription":
            await self.broadcast_to_subscription(target_id, message, message.tenant_id)
        elif target_type == "all":
            # Broadcast to all connections
            await self._send_to_connections(set(self.connections.keys()), message)
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        return {
            "total_connections": len(self.connections),
            "tenant_counts": {
                tenant_id: len(conn_ids) 
                for tenant_id, conn_ids in self.tenant_connections.items()
            },
            "user_counts": {
                user_id: len(conn_ids)
                for user_id, conn_ids in self.user_connections.items()
            },
            "subscription_counts": {
                sub: len(conn_ids)
                for sub, conn_ids in self.subscription_connections.items()
            },
        }
    
    # Private methods
    
    async def _send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send message to a specific connection."""
        if connection_id not in self.connections:
            return
            
        connection_info = self.connections[connection_id]
        
        try:
            if connection_info.websocket.client_state == WebSocketState.CONNECTED:
                await connection_info.websocket.send_text(json.dumps(message.to_dict()
            else:
                # Connection is closed, remove it
                await self.disconnect(connection_id)
                
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            await self.disconnect(connection_id)
    
    async def _send_to_connections(self, connection_ids: Set[str], message: WebSocketMessage):
        """Send message to multiple connections."""
        tasks = []
        for connection_id in connection_ids:
            task = asyncio.create_task(self._send_to_connection(connection_id, message)
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _close_all_connections(self):
        """Close all WebSocket connections."""
        connection_ids = list(self.connections.keys()
        for connection_id in connection_ids:
            await self.disconnect(connection_id)
    
    async def _publish_to_redis(self, message: WebSocketMessage, tenant_id: str = None, subscription_filter: str = None):
        """Publish message to Redis for other instances."""
        if not self.redis_client:
            return
            
        try:
            event_data = {
                "message": message.to_dict(),
                "tenant_id": tenant_id,
                "subscription_filter": subscription_filter,
            }
            
            await self.redis_client.publish("websocket:events", json.dumps(event_data)
            
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")
    
    def _start_background_tasks(self):
        """Start background monitoring tasks."""
        # Health check task
        health_task = asyncio.create_task(self._health_check_loop()
        self.background_tasks.add(health_task)
        health_task.add_done_callback(self.background_tasks.discard)
        
        # Redis message listener
        redis_task = asyncio.create_task(self._redis_message_loop()
        self.background_tasks.add(redis_task)
        redis_task.add_done_callback(self.background_tasks.discard)
    
    async def _health_check_loop(self):
        """Background health check for connections."""
        while self.is_running:
            try:
                # Check for stale connections
                current_time = datetime.now(timezone.utc)
                stale_connections = []
                
                for connection_id, conn_info in self.connections.items():
                    try:
                        # Send ping to check connection health
                        if conn_info.websocket.client_state == WebSocketState.CONNECTED:
                            ping_message = WebSocketMessage(
                                event_type=EventType.SYSTEM_NOTIFICATION,
                                data={"type": "ping", "timestamp": current_time.isoformat()},
                                tenant_id=conn_info.tenant_id,
                                user_id=conn_info.user_id,
                            )
                            await conn_info.websocket.send_text(json.dumps(ping_message.to_dict()
                        else:
                            stale_connections.append(connection_id)
                    except:
                        stale_connections.append(connection_id)
                
                # Remove stale connections
                for connection_id in stale_connections:
                    await self.disconnect(connection_id)
                
                await asyncio.sleep(60)  # Health check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket health check: {e}")
                await asyncio.sleep(60)
    
    async def _redis_message_loop(self):
        """Listen for Redis pub/sub messages."""
        if not self.pubsub:
            return
            
        while self.is_running:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    await self._handle_redis_message(message)
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Redis message loop: {e}")
                await asyncio.sleep(1)
    
    async def _handle_redis_message(self, redis_message):
        """Handle messages from Redis pub/sub."""
        try:
            data = json.loads(redis_message['data'])
            message_data = data['message']
            tenant_id = data.get('tenant_id')
            subscription_filter = data.get('subscription_filter')
            
            # Reconstruct WebSocket message
            message = WebSocketMessage(
                event_type=EventType(message_data['event_type']),
                data=message_data['data'],
                tenant_id=message_data['tenant_id'],
                user_id=message_data.get('user_id'),
                timestamp=message_data['timestamp'],
                message_id=message_data['message_id'],
            )
            
            # Broadcast to local connections
            if tenant_id:
                await self.broadcast_to_tenant(tenant_id, message, subscription_filter)
            
        except Exception as e:
            logger.error(f"Failed to handle Redis message: {e}")


# Singleton instance
websocket_manager = WebSocketManager()