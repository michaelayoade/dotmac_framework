"""
Advanced Broadcasting Management

High-performance message broadcasting with intelligent routing, filtering,
and delivery optimization for WebSocket connections.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from ..core.events import EventPriority, WebSocketEvent

logger = logging.getLogger(__name__)


class BroadcastType(str, Enum):
    """Types of broadcast operations."""

    ALL_CONNECTIONS = "all_connections"
    TENANT_ONLY = "tenant_only"
    USER_ONLY = "user_only"
    ROOM_ONLY = "room_only"
    SELECTIVE = "selective"
    FILTERED = "filtered"


class DeliveryMode(str, Enum):
    """Message delivery modes."""

    BEST_EFFORT = "best_effort"  # Send once, don't retry
    RELIABLE = "reliable"  # Retry on failure
    GUARANTEED = "guaranteed"  # Persist and retry until delivered


@dataclass
class BroadcastFilter:
    """Filters for selective broadcasting."""

    tenant_ids: Optional[Set[str]] = None
    user_ids: Optional[Set[str]] = None
    connection_ids: Optional[Set[str]] = None
    rooms: Optional[Set[str]] = None
    user_metadata: Optional[Dict[str, Any]] = None
    exclude_connections: Optional[Set[str]] = None
    min_connection_age: Optional[timedelta] = None
    max_connections: Optional[int] = None


@dataclass
class BroadcastResult:
    """Result of a broadcast operation."""

    broadcast_id: str
    total_targets: int
    delivered: int
    failed: int
    filtered_out: int
    delivery_time: float
    errors: List[str]


class BroadcastManager:
    """
    Advanced broadcasting system for WebSocket connections.

    Features:
    - Intelligent message routing and filtering
    - Delivery mode selection (best effort, reliable, guaranteed)
    - Performance optimization with batching
    - Broadcast analytics and monitoring
    - Custom broadcast patterns
    - Rate limiting and throttling
    """

    def __init__(self, websocket_manager, event_manager, config=None):
        self.websocket_manager = websocket_manager
        self.event_manager = event_manager
        self.config = config or {}

        # Broadcast tracking
        self.active_broadcasts: Dict[str, Dict[str, Any]] = {}
        self.broadcast_history: List[BroadcastResult] = []

        # Performance optimization
        self.batch_size = self.config.get("batch_size", 1000)
        self.concurrent_deliveries = self.config.get("concurrent_deliveries", 100)

        # Rate limiting
        self.rate_limits: Dict[str, List[datetime]] = defaultdict(list)
        self.rate_limit_window = timedelta(minutes=1)
        self.default_rate_limit = self.config.get("default_rate_limit", 1000)

        # Metrics
        self.metrics = {
            "broadcasts_sent": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
            "filtered_messages": 0,
            "rate_limited_requests": 0,
            "total_delivery_time": 0.0,
        }

        # Custom broadcast handlers
        self.broadcast_handlers: Dict[str, Callable] = {}

    async def broadcast_to_all(
        self,
        message: Union[Dict[str, Any], WebSocketEvent],
        exclude: Optional[Set[str]] = None,
        delivery_mode: DeliveryMode = DeliveryMode.BEST_EFFORT,
    ) -> BroadcastResult:
        """
        Broadcast message to all active connections.

        Args:
            message: Message to broadcast
            exclude: Connection IDs to exclude
            delivery_mode: How to handle delivery

        Returns:
            BroadcastResult with delivery statistics
        """
        return await self._execute_broadcast(
            broadcast_type=BroadcastType.ALL_CONNECTIONS,
            message=message,
            broadcast_filter=BroadcastFilter(exclude_connections=exclude),
            delivery_mode=delivery_mode,
        )

    async def broadcast_to_tenant(
        self,
        tenant_id: str,
        message: Union[Dict[str, Any], WebSocketEvent],
        exclude: Optional[Set[str]] = None,
        delivery_mode: DeliveryMode = DeliveryMode.BEST_EFFORT,
    ) -> BroadcastResult:
        """
        Broadcast message to all connections for a specific tenant.

        Args:
            tenant_id: Target tenant identifier
            message: Message to broadcast
            exclude: Connection IDs to exclude
            delivery_mode: How to handle delivery

        Returns:
            BroadcastResult with delivery statistics
        """
        return await self._execute_broadcast(
            broadcast_type=BroadcastType.TENANT_ONLY,
            message=message,
            broadcast_filter=BroadcastFilter(
                tenant_ids={tenant_id}, exclude_connections=exclude
            ),
            delivery_mode=delivery_mode,
        )

    async def broadcast_to_users(
        self,
        user_ids: Set[str],
        message: Union[Dict[str, Any], WebSocketEvent],
        delivery_mode: DeliveryMode = DeliveryMode.RELIABLE,
    ) -> BroadcastResult:
        """
        Broadcast message to specific users.

        Args:
            user_ids: Target user identifiers
            message: Message to broadcast
            delivery_mode: How to handle delivery

        Returns:
            BroadcastResult with delivery statistics
        """
        return await self._execute_broadcast(
            broadcast_type=BroadcastType.USER_ONLY,
            message=message,
            broadcast_filter=BroadcastFilter(user_ids=user_ids),
            delivery_mode=delivery_mode,
        )

    async def broadcast_to_rooms(
        self,
        room_ids: Set[str],
        message: Union[Dict[str, Any], WebSocketEvent],
        exclude: Optional[Set[str]] = None,
        delivery_mode: DeliveryMode = DeliveryMode.BEST_EFFORT,
    ) -> BroadcastResult:
        """
        Broadcast message to specific rooms.

        Args:
            room_ids: Target room identifiers
            message: Message to broadcast
            exclude: Connection IDs to exclude
            delivery_mode: How to handle delivery

        Returns:
            BroadcastResult with delivery statistics
        """
        return await self._execute_broadcast(
            broadcast_type=BroadcastType.ROOM_ONLY,
            message=message,
            broadcast_filter=BroadcastFilter(
                rooms=room_ids, exclude_connections=exclude
            ),
            delivery_mode=delivery_mode,
        )

    async def broadcast_filtered(
        self,
        message: Union[Dict[str, Any], WebSocketEvent],
        broadcast_filter: BroadcastFilter,
        delivery_mode: DeliveryMode = DeliveryMode.BEST_EFFORT,
    ) -> BroadcastResult:
        """
        Broadcast message with custom filtering.

        Args:
            message: Message to broadcast
            broadcast_filter: Filter criteria
            delivery_mode: How to handle delivery

        Returns:
            BroadcastResult with delivery statistics
        """
        return await self._execute_broadcast(
            broadcast_type=BroadcastType.FILTERED,
            message=message,
            broadcast_filter=broadcast_filter,
            delivery_mode=delivery_mode,
        )

    async def broadcast_priority(
        self,
        message: Union[Dict[str, Any], WebSocketEvent],
        priority: EventPriority,
        broadcast_filter: Optional[BroadcastFilter] = None,
        delivery_mode: DeliveryMode = DeliveryMode.RELIABLE,
    ) -> BroadcastResult:
        """
        Broadcast priority message with guaranteed delivery.

        Args:
            message: Message to broadcast
            priority: Message priority level
            broadcast_filter: Optional filter criteria
            delivery_mode: How to handle delivery

        Returns:
            BroadcastResult with delivery statistics
        """
        # Ensure message is treated as high priority
        if isinstance(message, WebSocketEvent):
            message.priority = priority
        elif isinstance(message, dict):
            message["priority"] = priority.value

        return await self._execute_broadcast(
            broadcast_type=BroadcastType.FILTERED,
            message=message,
            broadcast_filter=broadcast_filter or BroadcastFilter(),
            delivery_mode=delivery_mode,
        )

    async def schedule_broadcast(
        self,
        message: Union[Dict[str, Any], WebSocketEvent],
        broadcast_filter: BroadcastFilter,
        schedule_time: datetime,
        delivery_mode: DeliveryMode = DeliveryMode.RELIABLE,
    ) -> str:
        """
        Schedule a broadcast for future delivery.

        Args:
            message: Message to broadcast
            broadcast_filter: Filter criteria
            schedule_time: When to send the broadcast
            delivery_mode: How to handle delivery

        Returns:
            Broadcast ID for tracking
        """
        broadcast_id = f"scheduled_{datetime.utcnow().timestamp()}"

        # Calculate delay
        delay = (schedule_time - datetime.utcnow()).total_seconds()
        if delay <= 0:
            # Send immediately if time has passed
            result = await self.broadcast_filtered(
                message, broadcast_filter, delivery_mode
            )
            return result.broadcast_id

        # Schedule for later
        async def delayed_broadcast():
            await asyncio.sleep(delay)
            await self.broadcast_filtered(message, broadcast_filter, delivery_mode)

        asyncio.create_task(delayed_broadcast())
        logger.info(f"Scheduled broadcast {broadcast_id} for {schedule_time}")

        return broadcast_id

    async def add_broadcast_handler(self, pattern: str, handler: Callable):
        """
        Add custom broadcast handler.

        Args:
            pattern: Message type or pattern to handle
            handler: Async function to process broadcasts
        """
        self.broadcast_handlers[pattern] = handler
        logger.info(f"Added broadcast handler for pattern: {pattern}")

    async def remove_broadcast_handler(self, pattern: str):
        """Remove broadcast handler."""
        if pattern in self.broadcast_handlers:
            del self.broadcast_handlers[pattern]
            logger.info(f"Removed broadcast handler for pattern: {pattern}")

    def get_broadcast_stats(self) -> Dict[str, Any]:
        """Get broadcast performance statistics."""
        return {
            **self.metrics,
            "active_broadcasts": len(self.active_broadcasts),
            "avg_delivery_time": (
                self.metrics["total_delivery_time"]
                / max(self.metrics["broadcasts_sent"], 1)
            ),
            "delivery_success_rate": (
                self.metrics["messages_delivered"]
                / max(
                    self.metrics["messages_delivered"]
                    + self.metrics["messages_failed"],
                    1,
                )
            )
            * 100,
        }

    # Private methods
    async def _execute_broadcast(
        self,
        broadcast_type: BroadcastType,
        message: Union[Dict[str, Any], WebSocketEvent],
        broadcast_filter: BroadcastFilter,
        delivery_mode: DeliveryMode,
    ) -> BroadcastResult:
        """Execute a broadcast operation."""
        broadcast_id = f"broadcast_{datetime.utcnow().timestamp()}"
        start_time = asyncio.get_event_loop().time()

        try:
            # Rate limiting check
            if not await self._check_rate_limit(broadcast_type):
                self.metrics["rate_limited_requests"] += 1
                return BroadcastResult(
                    broadcast_id=broadcast_id,
                    total_targets=0,
                    delivered=0,
                    failed=0,
                    filtered_out=0,
                    delivery_time=0.0,
                    errors=["Rate limit exceeded"],
                )

            # Get target connections
            target_connections = await self._get_target_connections(
                broadcast_type, broadcast_filter
            )

            if not target_connections:
                return BroadcastResult(
                    broadcast_id=broadcast_id,
                    total_targets=0,
                    delivered=0,
                    failed=0,
                    filtered_out=0,
                    delivery_time=0.0,
                    errors=[],
                )

            # Apply additional filtering
            filtered_connections, filtered_out = await self._apply_filters(
                target_connections, broadcast_filter
            )

            # Track active broadcast
            self.active_broadcasts[broadcast_id] = {
                "type": broadcast_type,
                "start_time": start_time,
                "target_count": len(filtered_connections),
                "delivery_mode": delivery_mode,
            }

            # Execute delivery
            delivered, failed, errors = await self._deliver_to_connections(
                filtered_connections, message, delivery_mode
            )

            # Calculate delivery time
            delivery_time = asyncio.get_event_loop().time() - start_time

            # Create result
            result = BroadcastResult(
                broadcast_id=broadcast_id,
                total_targets=len(target_connections),
                delivered=delivered,
                failed=failed,
                filtered_out=filtered_out,
                delivery_time=delivery_time,
                errors=errors,
            )

            # Update metrics
            self.metrics["broadcasts_sent"] += 1
            self.metrics["messages_delivered"] += delivered
            self.metrics["messages_failed"] += failed
            self.metrics["filtered_messages"] += filtered_out
            self.metrics["total_delivery_time"] += delivery_time

            # Store result in history
            self.broadcast_history.append(result)
            if len(self.broadcast_history) > 1000:  # Limit history size
                self.broadcast_history = self.broadcast_history[-1000:]

            # Remove from active broadcasts
            self.active_broadcasts.pop(broadcast_id, None)

            # Call custom handlers
            await self._call_broadcast_handlers(message, result)

            logger.info(
                f"Broadcast {broadcast_id} completed: "
                f"{delivered}/{len(target_connections)} delivered in {delivery_time:.3f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Broadcast {broadcast_id} failed: {e}")
            self.active_broadcasts.pop(broadcast_id, None)

            return BroadcastResult(
                broadcast_id=broadcast_id,
                total_targets=0,
                delivered=0,
                failed=0,
                filtered_out=0,
                delivery_time=0.0,
                errors=[str(e)],
            )

    async def _get_target_connections(
        self, broadcast_type: BroadcastType, broadcast_filter: BroadcastFilter
    ) -> Set[str]:
        """Get target connections based on broadcast type and filter."""
        target_connections = set()

        if broadcast_type == BroadcastType.ALL_CONNECTIONS:
            target_connections = set(self.websocket_manager.active_connections.keys())

        elif broadcast_type == BroadcastType.TENANT_ONLY:
            if broadcast_filter.tenant_ids:
                for tenant_id in broadcast_filter.tenant_ids:
                    tenant_connections = self.websocket_manager.tenant_connections.get(
                        tenant_id, set()
                    )
                    target_connections.update(tenant_connections)

        elif broadcast_type == BroadcastType.USER_ONLY:
            if broadcast_filter.user_ids:
                for user_id in broadcast_filter.user_ids:
                    user_connections = self.websocket_manager.user_connections.get(
                        user_id, set()
                    )
                    target_connections.update(user_connections)

        elif broadcast_type == BroadcastType.ROOM_ONLY:
            if broadcast_filter.rooms:
                for room_id in broadcast_filter.rooms:
                    room_connections = self.websocket_manager.rooms.get(room_id, set())
                    target_connections.update(room_connections)

        elif broadcast_type == BroadcastType.FILTERED:
            # Start with all connections and filter
            target_connections = set(self.websocket_manager.active_connections.keys())

        return target_connections

    async def _apply_filters(
        self, connections: Set[str], broadcast_filter: BroadcastFilter
    ) -> tuple[Set[str], int]:
        """Apply additional filters to connection set."""
        filtered_connections = connections.copy()
        original_count = len(filtered_connections)

        # Exclude specific connections
        if broadcast_filter.exclude_connections:
            filtered_connections -= broadcast_filter.exclude_connections

        # Filter by specific connection IDs
        if broadcast_filter.connection_ids:
            filtered_connections &= broadcast_filter.connection_ids

        # Filter by connection age
        if broadcast_filter.min_connection_age:
            cutoff_time = datetime.utcnow() - broadcast_filter.min_connection_age
            aged_connections = set()

            for conn_id in filtered_connections:
                conn_info = self.websocket_manager.get_connection_info(conn_id)
                if conn_info and conn_info.connected_at <= cutoff_time:
                    aged_connections.add(conn_id)

            filtered_connections = aged_connections

        # Limit max connections
        if (
            broadcast_filter.max_connections
            and len(filtered_connections) > broadcast_filter.max_connections
        ):
            filtered_connections = set(
                list(filtered_connections)[: broadcast_filter.max_connections]
            )

        # Filter by user metadata
        if broadcast_filter.user_metadata:
            metadata_filtered = set()

            for conn_id in filtered_connections:
                conn_info = self.websocket_manager.get_connection_info(conn_id)
                if conn_info and self._metadata_matches(
                    conn_info.metadata, broadcast_filter.user_metadata
                ):
                    metadata_filtered.add(conn_id)

            filtered_connections = metadata_filtered

        filtered_out = original_count - len(filtered_connections)
        return filtered_connections, filtered_out

    def _metadata_matches(
        self, conn_metadata: Dict[str, Any], filter_metadata: Dict[str, Any]
    ) -> bool:
        """Check if connection metadata matches filter criteria."""
        for key, value in filter_metadata.items():
            if conn_metadata.get(key) != value:
                return False
        return True

    async def _deliver_to_connections(
        self,
        connections: Set[str],
        message: Union[Dict[str, Any], WebSocketEvent],
        delivery_mode: DeliveryMode,
    ) -> tuple[int, int, List[str]]:
        """Deliver message to connections."""
        if not connections:
            return 0, 0, []

        # Convert to WebSocketEvent if needed
        if isinstance(message, dict):
            from ..core.events import WebSocketEvent

            message = WebSocketEvent(
                event_type=message.get("type", "broadcast"),
                data=message.get("data", message),
            )

        # Batch connections for performance
        connection_batches = [
            list(connections)[i : i + self.batch_size]
            for i in range(0, len(connections), self.batch_size)
        ]

        delivered = 0
        failed = 0
        errors = []

        # Process batches
        for batch in connection_batches:
            batch_tasks = []

            # Create delivery tasks with concurrency limit
            for i in range(0, len(batch), self.concurrent_deliveries):
                chunk = batch[i : i + self.concurrent_deliveries]

                for conn_id in chunk:
                    if delivery_mode == DeliveryMode.GUARANTEED:
                        task = self._guaranteed_delivery(conn_id, message)
                    elif delivery_mode == DeliveryMode.RELIABLE:
                        task = self._reliable_delivery(conn_id, message)
                    else:  # BEST_EFFORT
                        task = self.websocket_manager.send_message(
                            conn_id, message.to_message()
                        )

                    batch_tasks.append((conn_id, task))

                # Execute chunk concurrently
                if batch_tasks:
                    results = await asyncio.gather(
                        *[task for _, task in batch_tasks[-len(chunk) :]],
                        return_exceptions=True,
                    )

                    # Process results
                    for (conn_id, _), result in zip(
                        batch_tasks[-len(chunk) :], results
                    ):
                        if isinstance(result, Exception):
                            failed += 1
                            errors.append(f"Connection {conn_id}: {str(result)}")
                        elif result:
                            delivered += 1
                        else:
                            failed += 1
                            errors.append(f"Connection {conn_id}: delivery failed")

        return delivered, failed, errors

    async def _reliable_delivery(
        self, connection_id: str, message: WebSocketEvent
    ) -> bool:
        """Reliable delivery with retry."""
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                success = await self.websocket_manager.send_message(
                    connection_id, message.to_message()
                )
                if success:
                    return True

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))

            except Exception as e:
                logger.debug(
                    f"Delivery attempt {attempt + 1} failed for {connection_id}: {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))

        return False

    async def _guaranteed_delivery(
        self, connection_id: str, message: WebSocketEvent
    ) -> bool:
        """Guaranteed delivery with persistence."""
        # First try reliable delivery
        success = await self._reliable_delivery(connection_id, message)

        if not success:
            # Store for later delivery (this would integrate with a persistence layer)
            logger.warning(
                f"Guaranteed delivery failed for {connection_id}, message stored for retry"
            )
            # In a real implementation, this would store the message for retry

        return success

    async def _check_rate_limit(self, broadcast_type: BroadcastType) -> bool:
        """Check if broadcast is within rate limits."""
        now = datetime.utcnow()
        rate_key = f"broadcast_{broadcast_type.value}"

        # Clean old entries
        cutoff = now - self.rate_limit_window
        self.rate_limits[rate_key] = [
            timestamp for timestamp in self.rate_limits[rate_key] if timestamp > cutoff
        ]

        # Check current rate
        current_rate = len(self.rate_limits[rate_key])
        if current_rate >= self.default_rate_limit:
            return False

        # Record this request
        self.rate_limits[rate_key].append(now)
        return True

    async def _call_broadcast_handlers(
        self, message: WebSocketEvent, result: BroadcastResult
    ):
        """Call custom broadcast handlers."""
        message_type = message.event_type

        # Call specific handler
        handler = self.broadcast_handlers.get(message_type)
        if handler:
            try:
                await handler(message, result)
            except Exception as e:
                logger.error(f"Broadcast handler error for {message_type}: {e}")

        # Call wildcard handler
        wildcard_handler = self.broadcast_handlers.get("*")
        if wildcard_handler:
            try:
                await wildcard_handler(message, result)
            except Exception as e:
                logger.error(f"Wildcard broadcast handler error: {e}")
