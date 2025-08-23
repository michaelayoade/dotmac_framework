"""WebSocket router for real-time billing events."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dotmac_isp.core.middleware import get_tenant_id_dependency
from .websocket_manager import websocket_manager, BillingEvent


logger = logging.getLogger(__name__)
security = HTTPBearer()

websocket_router = APIRouter(prefix="/ws", tags=["websocket"])


@websocket_router.websocket("/billing/{tenant_id}")
async def billing_websocket_endpoint(websocket: WebSocket, tenant_id: str):
    """WebSocket endpoint for real-time billing events."""
    await websocket.accept()
    await websocket_manager.connect(websocket, tenant_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Handle ping/pong for connection health
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket, tenant_id)
        logger.info(f"WebSocket disconnected for tenant {tenant_id}")
    except Exception as e:
        logger.error(f"WebSocket error for tenant {tenant_id}: {e}")
        await websocket_manager.disconnect(websocket, tenant_id)


@websocket_router.websocket("/billing/{tenant_id}/customer/{customer_id}")
async def customer_billing_websocket_endpoint(
    websocket: WebSocket, 
    tenant_id: str,
    customer_id: str
):
    """WebSocket endpoint for customer-specific billing events."""
    await websocket.accept()
    await websocket_manager.connect(websocket, f"{tenant_id}_{customer_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket, f"{tenant_id}_{customer_id}")
        logger.info(f"Customer WebSocket disconnected for tenant {tenant_id}, customer {customer_id}")
    except Exception as e:
        logger.error(f"Customer WebSocket error: {e}")
        await websocket_manager.disconnect(websocket, f"{tenant_id}_{customer_id}")


class BillingWebSocketNotifier:
    """Helper class to send notifications through WebSocket connections."""
    
    @staticmethod
    async def notify_invoice_status_change(tenant_id: str, customer_id: str, 
                                         invoice_id: str, old_status: str, new_status: str):
        """Notify about invoice status changes."""
        from .websocket_manager import event_publisher
        
        await event_publisher.publish_invoice_updated(
            tenant_id=tenant_id,
            customer_id=customer_id,
            invoice_id=invoice_id,
            invoice_data={
                'status_changed': True,
                'old_status': old_status,
                'new_status': new_status
            }
        )
    
    @staticmethod
    async def notify_payment_received(tenant_id: str, customer_id: str, 
                                    invoice_id: str, payment_amount: float):
        """Notify about payment received."""
        from .websocket_manager import event_publisher
        
        await event_publisher.publish_payment_received(
            tenant_id=tenant_id,
            customer_id=customer_id,
            entity_id=invoice_id,
            payment_data={
                'amount': payment_amount,
                'timestamp': None  # Will be set by the publisher
            }
        )
    
    @staticmethod
    async def notify_invoice_overdue(tenant_id: str, customer_id: str, invoice_id: str):
        """Notify about invoice becoming overdue."""
        from .websocket_manager import event_publisher
        
        await event_publisher.publish_invoice_overdue(
            tenant_id=tenant_id,
            customer_id=customer_id,
            invoice_id=invoice_id,
            invoice_data={'overdue_notification': True}
        )


# Export the notifier for use in services
billing_websocket_notifier = BillingWebSocketNotifier()