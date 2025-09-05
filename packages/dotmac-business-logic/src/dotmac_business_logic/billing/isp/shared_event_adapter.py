"""
Adapter to replace ISP billing event publisher with shared EventBus.
Maintains backward compatibility while using shared event system.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from dotmac.communications.events import Event, EventBus

from .websocket_manager import (
    BillingEvent,
    BillingEventType,
    WebSocketConnectionManager,
)

logger = logging.getLogger(__name__)


class SharedBillingEventPublisher:
    """
    Adapter that provides ISP billing event interface using shared EventBus.
    Maintains backward compatibility with existing billing event API.
    """

    def __init__(
        self,
        event_bus: EventBus,
        websocket_manager: Optional[WebSocketConnectionManager] = None,
    ):
        self.event_bus = event_bus
        self.websocket_manager = websocket_manager  # Keep for WebSocket notifications

    async def publish_invoice_created(
        self,
        tenant_id: str,
        customer_id: str,
        invoice_id: str,
        invoice_data: dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """Publish invoice created event using shared EventBus."""
        try:
            # Publish to shared EventBus for cross-service communication
            event = Event(
                event_type="billing.invoice_created",
                entity_id=invoice_id,
                tenant_id=tenant_id,
                data={
                    "customer_id": customer_id,
                    "invoice_data": invoice_data,
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            await self.event_bus.publish(event)

            # Also publish to WebSocket for real-time UI updates
            if self.websocket_manager:
                billing_event = BillingEvent(
                    event_type=BillingEventType.INVOICE_CREATED,
                    tenant_id=tenant_id,
                    customer_id=customer_id,
                    entity_id=invoice_id,
                    timestamp=datetime.now(timezone.utc),
                    data=invoice_data,
                    user_id=user_id,
                )
                await self.websocket_manager.broadcast_event(billing_event)

            logger.info(f"Published invoice_created event for invoice {invoice_id}")

        except Exception as e:
            logger.error(f"Failed to publish invoice_created event: {e}")

    async def publish_invoice_paid(
        self,
        tenant_id: str,
        customer_id: str,
        invoice_id: str,
        payment_data: dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """Publish invoice paid event using shared EventBus."""
        try:
            # Publish to shared EventBus
            event = Event(
                event_type="billing.invoice_paid",
                entity_id=invoice_id,
                tenant_id=tenant_id,
                data={
                    "customer_id": customer_id,
                    "payment_data": payment_data,
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            await self.event_bus.publish(event)

            # Also publish to WebSocket
            if self.websocket_manager:
                billing_event = BillingEvent(
                    event_type=BillingEventType.INVOICE_PAID,
                    tenant_id=tenant_id,
                    customer_id=customer_id,
                    entity_id=invoice_id,
                    timestamp=datetime.now(timezone.utc),
                    data=payment_data,
                    user_id=user_id,
                )
                await self.websocket_manager.broadcast_event(billing_event)

            logger.info(f"Published invoice_paid event for invoice {invoice_id}")

        except Exception as e:
            logger.error(f"Failed to publish invoice_paid event: {e}")

    async def publish_payment_received(
        self,
        tenant_id: str,
        customer_id: str,
        payment_id: str,
        payment_data: dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """Publish payment received event using shared EventBus."""
        try:
            # Publish to shared EventBus
            event = Event(
                event_type="billing.payment_received",
                entity_id=payment_id,
                tenant_id=tenant_id,
                data={
                    "customer_id": customer_id,
                    "payment_data": payment_data,
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            await self.event_bus.publish(event)

            # Also publish to WebSocket
            if self.websocket_manager:
                billing_event = BillingEvent(
                    event_type=BillingEventType.PAYMENT_RECEIVED,
                    tenant_id=tenant_id,
                    customer_id=customer_id,
                    entity_id=payment_id,
                    timestamp=datetime.now(timezone.utc),
                    data=payment_data,
                    user_id=user_id,
                )
                await self.websocket_manager.broadcast_event(billing_event)

            logger.info(f"Published payment_received event for payment {payment_id}")

        except Exception as e:
            logger.error(f"Failed to publish payment_received event: {e}")

    async def publish_invoice_updated(
        self,
        tenant_id: str,
        customer_id: str,
        invoice_id: str,
        invoice_data: dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """Publish invoice updated event using shared EventBus."""
        try:
            # Publish to shared EventBus
            event = Event(
                event_type="billing.invoice_updated",
                entity_id=invoice_id,
                tenant_id=tenant_id,
                data={
                    "customer_id": customer_id,
                    "invoice_data": invoice_data,
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            await self.event_bus.publish(event)

            # Also publish to WebSocket
            if self.websocket_manager:
                billing_event = BillingEvent(
                    event_type=BillingEventType.INVOICE_UPDATED,
                    tenant_id=tenant_id,
                    customer_id=customer_id,
                    entity_id=invoice_id,
                    timestamp=datetime.now(timezone.utc),
                    data=invoice_data,
                    user_id=user_id,
                )
                await self.websocket_manager.broadcast_event(billing_event)

            logger.info(f"Published invoice_updated event for invoice {invoice_id}")

        except Exception as e:
            logger.error(f"Failed to publish invoice_updated event: {e}")

    async def publish_invoice_overdue(
        self,
        tenant_id: str,
        customer_id: str,
        invoice_id: str,
        invoice_data: dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """Publish invoice overdue event using shared EventBus."""
        try:
            # Publish to shared EventBus
            event = Event(
                event_type="billing.invoice_overdue",
                entity_id=invoice_id,
                tenant_id=tenant_id,
                data={
                    "customer_id": customer_id,
                    "invoice_data": invoice_data,
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            await self.event_bus.publish(event)

            # Also publish to WebSocket
            if self.websocket_manager:
                billing_event = BillingEvent(
                    event_type=BillingEventType.INVOICE_OVERDUE,
                    tenant_id=tenant_id,
                    customer_id=customer_id,
                    entity_id=invoice_id,
                    timestamp=datetime.now(timezone.utc),
                    data=invoice_data,
                    user_id=user_id,
                )
                await self.websocket_manager.broadcast_event(billing_event)

            logger.info(f"Published invoice_overdue event for invoice {invoice_id}")

        except Exception as e:
            logger.error(f"Failed to publish invoice_overdue event: {e}")


# Factory function for easy adapter creation
async def create_shared_billing_event_publisher(
    event_bus: EventBus, websocket_manager: Optional[WebSocketConnectionManager] = None
) -> SharedBillingEventPublisher:
    """Create shared billing event publisher."""
    return SharedBillingEventPublisher(event_bus, websocket_manager)
