"""
Redis WebSocket Backend for Horizontal Scaling

Production-ready Redis backend for WebSocket scaling across multiple instances
with message broadcasting, connection state sharing, and cluster coordination.
"""

import asyncio
import json
import logging
import pickle
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from ..core.config import WebSocketConfig
from ..core.events import WebSocketEvent

logger = logging.getLogger(__name__)


class RedisWebSocketBackend:
    """
    Redis-based WebSocket backend for horizontal scaling.

    Features:
    - Cross-instance message broadcasting
    - Distributed connection state management
    - Cluster coordination and health monitoring
    - Message persistence and replay
    - Connection migration support
    - Comprehensive metrics and monitoring
    """

    def __init__(self, config: WebSocketConfig):
        self.config = config
        self.instance_id = f"ws_{uuid4().hex[:8]}"
        self.is_running = False

        # Redis connections
        self.redis_pool = None
        self.redis_client = None
        self.pubsub = None

        # Channel configuration
        self.channels = {
            "broadcast": "websocket:broadcast",
            "instance_health": "websocket:instance:health",
            "connection_events": "websocket:connection:events",
            "room_events": "websocket:room:events",
            "system_events": "websocket:system:events",
        }

        # Instance state
        self.registered_instances: Set[str] = set()
        self.instance_info: Dict[str, Any] = {
            "instance_id": self.instance_id,
            "started_at": datetime.utcnow().isoformat(),
            "last_heartbeat": datetime.utcnow().isoformat(),
            "connection_count": 0,
            "message_count": 0,
            "status": "starting",
        }

        # Message handlers
        self.message_handlers: Dict[str, List[Callable]] = {}

        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Metrics
        self.metrics = {
            "messages_published": 0,
            "messages_received": 0,
            "broadcasts_sent": 0,
            "broadcasts_received": 0,
            "connection_events": 0,
            "redis_errors": 0,
        }

    async def start(self):
        """Start the Redis backend and background tasks."""
        if self.is_running:
            return

        try:
            # Create Redis connection pool
            if self.config.redis_cluster_nodes:
                # Redis Cluster setup
                from redis.asyncio.cluster import RedisCluster

                self.redis_client = RedisCluster(
                    startup_nodes=[
                        {
                            "host": node.split("://")[1].split(":")[0],
                            "port": int(node.split(":")[-1]),
                        }
                        for node in self.config.redis_cluster_nodes
                    ],
                    max_connections=self.config.redis_max_connections,
                    decode_responses=False,  # We handle encoding ourselves
                )
            else:
                # Single Redis instance
                self.redis_pool = ConnectionPool.from_url(
                    self.config.redis_url,
                    max_connections=self.config.redis_max_connections,
                    decode_responses=False,
                )
                self.redis_client = redis.Redis(connection_pool=self.redis_pool)

            # Test connection
            await self.redis_client.ping()

            # Create pub/sub client
            self.pubsub = self.redis_client.pubsub()

            # Subscribe to channels
            await self._subscribe_to_channels()

            # Register instance
            await self._register_instance()

            # Start background tasks
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._listener_task = asyncio.create_task(self._message_listener())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

            self.is_running = True
            self.instance_info["status"] = "running"

            logger.info(f"Redis WebSocket backend started: {self.instance_id}")

        except Exception as e:
            logger.error(f"Failed to start Redis backend: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop the Redis backend and cleanup resources."""
        if not self.is_running:
            return

        self.is_running = False
        self.instance_info["status"] = "stopping"

        # Cancel background tasks
        tasks = [self._heartbeat_task, self._listener_task, self._cleanup_task]
        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Unregister instance
        try:
            await self._unregister_instance()
        except Exception as e:
            logger.warning(f"Error unregistering instance: {e}")

        # Close Redis connections
        try:
            if self.pubsub:
                await self.pubsub.close()
            if self.redis_client:
                await self.redis_client.close()
            if self.redis_pool:
                await self.redis_pool.disconnect()
        except Exception as e:
            logger.warning(f"Error closing Redis connections: {e}")

        logger.info(f"Redis WebSocket backend stopped: {self.instance_id}")

    async def publish_message(
        self,
        channel: str,
        message: Dict[str, Any],
        target_instances: Optional[Set[str]] = None,
    ) -> int:
        """
        Publish message to Redis channel for cross-instance delivery.

        Args:
            channel: Redis channel name
            message: Message payload
            target_instances: Specific instance IDs to target (None = all)

        Returns:
            Number of instances that received the message
        """
        if not self.is_running:
            return 0

        try:
            # Create message envelope
            envelope = {
                "source_instance": self.instance_id,
                "target_instances": (
                    list(target_instances) if target_instances else None
                ),
                "timestamp": datetime.utcnow().isoformat(),
                "message_id": str(uuid4()),
                "payload": message,
            }

            # Serialize message
            serialized = json.dumps(envelope, default=str)

            # Publish to Redis
            result = await self.redis_client.publish(channel, serialized)

            # Update metrics
            self.metrics["messages_published"] += 1
            if channel == self.channels["broadcast"]:
                self.metrics["broadcasts_sent"] += 1

            logger.debug(f"Published message to {channel}: {result} subscribers")
            return result

        except Exception as e:
            logger.error(f"Error publishing message to {channel}: {e}")
            self.metrics["redis_errors"] += 1
            return 0

    async def broadcast_event(
        self, event: WebSocketEvent, exclude_instances: Optional[Set[str]] = None
    ) -> int:
        """
        Broadcast WebSocket event to all instances.

        Args:
            event: WebSocket event to broadcast
            exclude_instances: Instance IDs to exclude from broadcast

        Returns:
            Number of instances that received the event
        """
        target_instances = None
        if exclude_instances:
            target_instances = self.registered_instances - exclude_instances

        message = {
            "type": "websocket_event",
            "event": event.model_dump(),
        }

        return await self.publish_message(
            self.channels["broadcast"], message, target_instances
        )

    async def notify_connection_event(
        self,
        event_type: str,
        connection_id: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Notify other instances about connection events.

        Args:
            event_type: Type of event (connected, disconnected, etc.)
            connection_id: WebSocket connection ID
            user_id: User identifier
            tenant_id: Tenant identifier
            metadata: Additional metadata
        """
        message = {
            "type": "connection_event",
            "event_type": event_type,
            "connection_id": connection_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "metadata": metadata or {},
        }

        result = await self.publish_message(self.channels["connection_events"], message)
        if result > 0:
            self.metrics["connection_events"] += 1

    async def store_message(
        self, message_id: str, message: Dict[str, Any], ttl: Optional[int] = None
    ):
        """
        Store message in Redis for persistence and replay.

        Args:
            message_id: Unique message identifier
            message: Message data
            ttl: Time to live in seconds
        """
        if not self.is_running:
            return

        try:
            key = f"websocket:message:{message_id}"
            serialized = json.dumps(message, default=str)

            if ttl:
                await self.redis_client.setex(key, ttl, serialized)
            else:
                await self.redis_client.set(key, serialized)

            logger.debug(f"Stored message {message_id} in Redis")

        except Exception as e:
            logger.error(f"Error storing message {message_id}: {e}")
            self.metrics["redis_errors"] += 1

    async def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored message from Redis.

        Args:
            message_id: Message identifier

        Returns:
            Message data or None if not found
        """
        if not self.is_running:
            return None

        try:
            key = f"websocket:message:{message_id}"
            serialized = await self.redis_client.get(key)

            if serialized:
                return json.loads(serialized)

            return None

        except Exception as e:
            logger.error(f"Error retrieving message {message_id}: {e}")
            self.metrics["redis_errors"] += 1
            return None

    async def get_connection_count(self) -> int:
        """Get total connections across all instances."""
        if not self.is_running:
            return 0

        try:
            total_connections = 0

            # Get all instance keys
            pattern = "websocket:instance:*"
            keys = await self.redis_client.keys(pattern)

            for key in keys:
                instance_data = await self.redis_client.hgetall(key)
                if instance_data and b"connection_count" in instance_data:
                    count = int(instance_data[b"connection_count"].decode())
                    total_connections += count

            return total_connections

        except Exception as e:
            logger.error(f"Error getting connection count: {e}")
            self.metrics["redis_errors"] += 1
            return 0

    async def get_instance_info(self) -> List[Dict[str, Any]]:
        """Get information about all registered instances."""
        if not self.is_running:
            return []

        try:
            instances = []

            # Get all instance keys
            pattern = "websocket:instance:*"
            keys = await self.redis_client.keys(pattern)

            for key in keys:
                instance_data = await self.redis_client.hgetall(key)
                if instance_data:
                    # Convert bytes to strings
                    instance_info = {
                        k.decode(): v.decode() if isinstance(v, bytes) else v
                        for k, v in instance_data.items()
                    }
                    instances.append(instance_info)

            return instances

        except Exception as e:
            logger.error(f"Error getting instance info: {e}")
            self.metrics["redis_errors"] += 1
            return []

    async def add_message_handler(self, channel: str, handler: Callable):
        """
        Add message handler for specific channel.

        Args:
            channel: Channel name
            handler: Async callable that processes messages
        """
        if channel not in self.message_handlers:
            self.message_handlers[channel] = []

        self.message_handlers[channel].append(handler)
        logger.debug(f"Added message handler for channel: {channel}")

    async def remove_message_handler(self, channel: str, handler: Callable):
        """Remove message handler for specific channel."""
        if channel in self.message_handlers:
            try:
                self.message_handlers[channel].remove(handler)
                if not self.message_handlers[channel]:
                    del self.message_handlers[channel]
                logger.debug(f"Removed message handler for channel: {channel}")
            except ValueError:
                pass

    def get_metrics(self) -> Dict[str, Any]:
        """Get Redis backend metrics."""
        return {
            **self.metrics,
            "instance_id": self.instance_id,
            "registered_instances": len(self.registered_instances),
            "is_running": self.is_running,
            "channels_subscribed": len(self.channels),
        }

    # Private methods
    async def _subscribe_to_channels(self):
        """Subscribe to Redis channels."""
        channels_to_subscribe = list(self.channels.values())

        await self.pubsub.subscribe(*channels_to_subscribe)
        logger.info(f"Subscribed to Redis channels: {channels_to_subscribe}")

    async def _register_instance(self):
        """Register this instance in Redis."""
        try:
            key = f"websocket:instance:{self.instance_id}"

            # Set instance info with expiration
            await self.redis_client.hset(key, mapping=self.instance_info)
            await self.redis_client.expire(key, 120)  # 2 minute expiration

            # Add to active instances set
            await self.redis_client.sadd("websocket:active_instances", self.instance_id)

            logger.info(f"Registered instance: {self.instance_id}")

        except Exception as e:
            logger.error(f"Error registering instance: {e}")
            self.metrics["redis_errors"] += 1

    async def _unregister_instance(self):
        """Unregister this instance from Redis."""
        try:
            key = f"websocket:instance:{self.instance_id}"

            # Remove instance info
            await self.redis_client.delete(key)

            # Remove from active instances set
            await self.redis_client.srem("websocket:active_instances", self.instance_id)

            logger.info(f"Unregistered instance: {self.instance_id}")

        except Exception as e:
            logger.error(f"Error unregistering instance: {e}")
            self.metrics["redis_errors"] += 1

    async def _heartbeat_loop(self):
        """Background task to send heartbeats and update instance info."""
        while self.is_running:
            try:
                # Update instance info
                self.instance_info["last_heartbeat"] = datetime.utcnow().isoformat()

                # Update Redis
                key = f"websocket:instance:{self.instance_id}"
                await self.redis_client.hset(key, mapping=self.instance_info)
                await self.redis_client.expire(key, 120)  # Refresh expiration

                # Publish heartbeat
                heartbeat_message = {
                    "type": "heartbeat",
                    "instance_info": self.instance_info,
                }

                await self.publish_message(
                    self.channels["instance_health"], heartbeat_message
                )

                # Update registered instances list
                active_instances = await self.redis_client.smembers(
                    "websocket:active_instances"
                )
                self.registered_instances = {
                    instance.decode() if isinstance(instance, bytes) else instance
                    for instance in active_instances
                }

                await asyncio.sleep(30)  # Heartbeat every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                self.metrics["redis_errors"] += 1
                await asyncio.sleep(5)  # Error backoff

    async def _message_listener(self):
        """Background task to listen for Redis messages."""
        while self.is_running:
            try:
                message = await self.pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    await self._handle_redis_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message listener error: {e}")
                self.metrics["redis_errors"] += 1
                await asyncio.sleep(1)  # Error backoff

    async def _handle_redis_message(self, redis_message):
        """Handle incoming Redis message."""
        try:
            # Parse message
            channel = redis_message["channel"].decode()
            data = redis_message["data"]

            if isinstance(data, bytes):
                data = data.decode()

            message_envelope = json.loads(data)

            # Skip messages from this instance
            if message_envelope.get("source_instance") == self.instance_id:
                return

            # Check if message is targeted to this instance
            target_instances = message_envelope.get("target_instances")
            if target_instances and self.instance_id not in target_instances:
                return

            # Update metrics
            self.metrics["messages_received"] += 1
            if channel == self.channels["broadcast"]:
                self.metrics["broadcasts_received"] += 1

            # Call message handlers
            handlers = self.message_handlers.get(channel, [])
            if handlers:
                for handler in handlers:
                    try:
                        await handler(message_envelope["payload"])
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")

            logger.debug(f"Handled Redis message from {channel}")

        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")
            self.metrics["redis_errors"] += 1

    async def _cleanup_loop(self):
        """Background task to cleanup expired data."""
        while self.is_running:
            try:
                # Clean up expired instance data
                pattern = "websocket:instance:*"
                keys = await self.redis_client.keys(pattern)

                expired_instances = []
                for key in keys:
                    ttl = await self.redis_client.ttl(key)
                    if ttl == -1:  # No expiration set
                        await self.redis_client.expire(key, 120)
                    elif ttl == -2:  # Key expired
                        instance_id = key.decode().split(":")[-1]
                        expired_instances.append(instance_id)

                # Remove expired instances from active set
                if expired_instances:
                    await self.redis_client.srem(
                        "websocket:active_instances", *expired_instances
                    )
                    logger.info(
                        f"Cleaned up {len(expired_instances)} expired instances"
                    )

                # Clean up old messages (optional)
                # This could be extended to clean up old persistent messages

                await asyncio.sleep(300)  # Cleanup every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                self.metrics["redis_errors"] += 1
                await asyncio.sleep(60)  # Error backoff
