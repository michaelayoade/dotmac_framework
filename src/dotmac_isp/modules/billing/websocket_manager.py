"""WebSocket integration for real-time billing events."""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import redis.asyncio as redis
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from dotmac_isp.core.settings import get_settings
from dotmac_shared.api.exception_handlers import standard_exception_handler

logger = logging.getLogger(__name__)
settings = get_settings()


class BillingEventType(Enum):
    """Billing event types for WebSocket notifications."""

    INVOICE_CREATED = "invoice_created"
    INVOICE_UPDATED = "invoice_updated"
    INVOICE_PAID = "invoice_paid"
    INVOICE_OVERDUE = "invoice_overdue"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    LATE_FEE_APPLIED = "late_fee_applied"
    CREDIT_NOTE_ISSUED = "credit_note_issued"


@dataclass
class BillingEvent:
    """Billing event data structure."""

    event_type: BillingEventType
    tenant_id: str
    customer_id: str
    entity_id: str  # Invoice ID, Payment ID, etc.
    timestamp: datetime
    data: Dict[str, Any]
    user_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result["event_type"] = self.event_type.value
        result["timestamp"] = self.timestamp.isoformat()
        return result


class WebSocketConnectionManager:
    """Manages WebSocket connections for billing events."""

    def __init__(self):
        """Init   operation."""
        self.connections: Dict[str, List[websockets.WebSocketServerProtocol]] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.retry_counts: Dict[str, int] = {}
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds

    async def initialize(self):
        """Initialize Redis connection for event publishing."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("WebSocket manager initialized with Redis connection")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise

    async def connect(
        self, websocket: websockets.WebSocketServerProtocol, tenant_id: str
    ):
        """Register a new WebSocket connection."""
        if tenant_id not in self.connections:
            self.connections[tenant_id] = []

        self.connections[tenant_id].append(websocket)
        self.retry_counts[f"{tenant_id}_{id(websocket)}"] = 0
        logger.info(f"WebSocket connected for tenant {tenant_id}")

        # Send connection confirmation
        await self._send_to_websocket(
            websocket,
            {
                "type": "connection_established",
                "tenant_id": tenant_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def disconnect(
        self, websocket: websockets.WebSocketServerProtocol, tenant_id: str
    ):
        """Unregister a WebSocket connection."""
        if tenant_id in self.connections:
            try:
                self.connections[tenant_id].remove(websocket)
                if not self.connections[tenant_id]:
                    del self.connections[tenant_id]

                # Clean up retry count
                connection_key = f"{tenant_id}_{id(websocket)}"
                self.retry_counts.pop(connection_key, None)

                logger.info(f"WebSocket disconnected for tenant {tenant_id}")
            except ValueError:
                # Connection already removed
                pass

    async def broadcast_event(self, event: BillingEvent):
        """Broadcast billing event to all connections for a tenant."""
        tenant_id = event.tenant_id

        if tenant_id not in self.connections:
            logger.debug(f"No WebSocket connections for tenant {tenant_id}")
            return

        # Also publish to Redis for cross-instance communication
        if self.redis_client:
            await self._publish_to_redis(event)

        connections = self.connections[tenant_id].model_copy()

        for websocket in connections:
            await self._send_with_retry(websocket, tenant_id, event.to_dict())

    async def _send_with_retry(
        self,
        websocket: websockets.WebSocketServerProtocol,
        tenant_id: str,
        message: Dict[str, Any],
    ):
        """Send message to WebSocket with retry logic."""
        connection_key = f"{tenant_id}_{id(websocket)}"

        for attempt in range(self.max_retries + 1):
            try:
                await self._send_to_websocket(websocket, message)
                # Reset retry count on success
                self.retry_counts[connection_key] = 0
                return

            except (ConnectionClosedError, ConnectionClosedOK):
                logger.info(f"WebSocket connection closed for tenant {tenant_id}")
                await self.disconnect(websocket, tenant_id)
                break

            except Exception as e:
                self.retry_counts[connection_key] = attempt + 1
                logger.warning(
                    f"Failed to send message to WebSocket (attempt {attempt + 1}): {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(
                        self.retry_delay * (2**attempt)
                    )  # Exponential backoff
                else:
                    logger.error(f"Max retries exceeded for WebSocket connection")
                    await self.disconnect(websocket, tenant_id)

    async def _send_to_websocket(
        self, websocket: websockets.WebSocketServerProtocol, message: Dict[str, Any]
    ):
        """Send message to a single WebSocket connection."""
        await websocket.send(json.dumps(message))

    async def _publish_to_redis(self, event: BillingEvent):
        """Publish event to Redis for cross-instance communication."""
        try:
            channel = f"billing_events:{event.tenant_id}"
            await self.redis_client.publish(channel, json.dumps(event.to_dict()))
        except Exception as e:
            logger.error(f"Failed to publish event to Redis: {e}")

    async def subscribe_to_redis_events(
        self, tenant_id: str, callback: Callable[[BillingEvent], None]
    ):
        """Subscribe to Redis events for cross-instance communication."""
        if not self.redis_client:
            logger.error("Redis client not initialized")
            return

        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(f"billing_events:{tenant_id}")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        event = BillingEvent(
                            event_type=BillingEventType(event_data["event_type"]),
                            tenant_id=event_data["tenant_id"],
                            customer_id=event_data["customer_id"],
                            entity_id=event_data["entity_id"],
                            timestamp=datetime.fromisoformat(event_data["timestamp"]),
                            data=event_data["data"],
                            user_id=event_data.get("user_id"),
                        )
                        await callback(event)
                    except Exception as e:
                        logger.error(f"Failed to process Redis event: {e}")

        except Exception as e:
            logger.error(f"Redis subscription error: {e}")

    async def get_connection_count(self, tenant_id: str) -> int:
        """Get number of active connections for a tenant."""
        return len(self.connections.get(tenant_id, []))

    async def health_check(self) -> Dict[str, Any]:
        """Return health check information."""
        total_connections = sum(len(conns) for conns in self.connections.values())

        return {
            "total_connections": total_connections,
            "tenant_count": len(self.connections),
            "redis_connected": self.redis_client is not None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Global WebSocket manager instance
websocket_manager = WebSocketConnectionManager()


class BillingEventPublisher:
    """Service for publishing billing events."""

    def __init__(self, manager: WebSocketConnectionManager):
        """Init   operation."""
        self.manager = manager

    async def publish_invoice_created(
        self,
        tenant_id: str,
        customer_id: str,
        invoice_id: str,
        invoice_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """Publish invoice created event."""
        event = BillingEvent(
            event_type=BillingEventType.INVOICE_CREATED,
            tenant_id=tenant_id,
            customer_id=customer_id,
            entity_id=invoice_id,
            timestamp=datetime.now(timezone.utc),
            data=invoice_data,
            user_id=user_id,
        )
        await self.manager.broadcast_event(event)

    async def publish_invoice_paid(
        self,
        tenant_id: str,
        customer_id: str,
        invoice_id: str,
        payment_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """Publish invoice paid event."""
        event = BillingEvent(
            event_type=BillingEventType.INVOICE_PAID,
            tenant_id=tenant_id,
            customer_id=customer_id,
            entity_id=invoice_id,
            timestamp=datetime.now(timezone.utc),
            data=payment_data,
            user_id=user_id,
        )
        await self.manager.broadcast_event(event)

    async def publish_payment_failed(
        self,
        tenant_id: str,
        customer_id: str,
        payment_id: str,
        failure_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """Publish payment failed event."""
        event = BillingEvent(
            event_type=BillingEventType.PAYMENT_FAILED,
            tenant_id=tenant_id,
            customer_id=customer_id,
            entity_id=payment_id,
            timestamp=datetime.now(timezone.utc),
            data=failure_data,
            user_id=user_id,
        )
        await self.manager.broadcast_event(event)

    async def publish_subscription_cancelled(
        self,
        tenant_id: str,
        customer_id: str,
        subscription_id: str,
        cancellation_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """Publish subscription cancelled event."""
        event = BillingEvent(
            event_type=BillingEventType.SUBSCRIPTION_CANCELLED,
            tenant_id=tenant_id,
            customer_id=customer_id,
            entity_id=subscription_id,
            timestamp=datetime.now(timezone.utc),
            data=cancellation_data,
            user_id=user_id,
        )
        await self.manager.broadcast_event(event)


# Global event publisher instance
event_publisher = BillingEventPublisher(websocket_manager)


async def initialize_websocket_manager():
    """Initialize the WebSocket manager."""
    await websocket_manager.initialize()


async def cleanup_websocket_manager():
    """Cleanup WebSocket manager resources."""
    if websocket_manager.redis_client:
        await websocket_manager.redis_client.close()
