"""WebSocket Router for Real-time Frontend Communication."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer
from starlette.websockets import WebSocketState

from dotmac.application import standard_exception_handler
from dotmac_shared.api.rate_limiting_decorators import RateLimitDecorators

from ..core.websocket_manager import EventType, WebSocketMessage, websocket_manager
from ..shared.auth import get_current_user_optional, verify_websocket_token

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """
    WebSocket endpoint for real-time communication.

    Query Parameters:
    - token: JWT authentication token
    - tenant_id: Tenant ID (optional, will be extracted from token if not provided)
    - user_id: User ID (optional, will be extracted from token if not provided)
    Usage:
    ```javascript
    const ws = new WebSocket(`ws://localhost:8000/api/ws?token=${jwt_token}`);
    ```
    """
    connection_id = None

    # WebSocket connection rate limiting
    client_ip = websocket.client.host if websocket.client else "unknown"
    rate_limiter = RateLimitDecorators()._rate_limiter

    try:
        # Check connection rate limit (max 10 connections per minute per IP)
        is_allowed, remaining, reset_time = await rate_limiter.is_request_allowed(
            ip_address=client_ip,
            user_id=None,  # Will be set after authentication
            endpoint="/ws",
            method="WEBSOCKET",
        )

        if not is_allowed:
            await websocket.close(
                code=4029, reason="WebSocket connection rate limit exceeded"
            )
            return

    except Exception as e:
        logger.error(f"WebSocket rate limiting error: {e}")
        # Continue with connection (fail-open policy)

    try:
        # Authenticate the WebSocket connection
        if not token:
            await websocket.close(code=4001, reason="Authentication token required")
            return

        try:
            # Verify token and get user info
            user_info = await verify_websocket_token(token)
            authenticated_user_id = user_info.get("user_id") or user_info.get("sub")
            authenticated_tenant_id = user_info.get("tenant_id")

            # Use authenticated values or fallback to query params
            final_user_id = user_id or authenticated_user_id
            final_tenant_id = tenant_id or authenticated_tenant_id

            if not final_user_id or not final_tenant_id:
                await websocket.close(
                    code=4001, reason="Invalid token or missing user/tenant info"
                )
                return

        except Exception as e:
            logger.error(f"WebSocket authentication failed: {e}")
            await websocket.close(code=4001, reason="Authentication failed")
            return

        # Connect to WebSocket manager
        connection_id = await websocket_manager.connect(
            websocket=websocket, user_id=final_user_id, tenant_id=final_tenant_id
        )
        logger.info(f"WebSocket client connected: {connection_id}")

        # Handle incoming messages
        while websocket.client_state == WebSocketState.CONNECTED:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                # Handle client message
                await _handle_client_message(
                    connection_id, message, final_user_id, final_tenant_id
                )
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {connection_id}")
                break
            except json.JSONDecodeError:
                # Send error message for invalid JSON
                error_message = WebSocketMessage(
                    event_type=EventType.SYSTEM_NOTIFICATION,
                    data={"error": "Invalid JSON format"},
                    tenant_id=final_tenant_id,
                    user_id=final_user_id,
                )
                await websocket.send_text(json.dumps(error_message.to_dict()))
            except Exception as e:
                logger.error(
                    f"Error handling WebSocket message from {connection_id}: {e}"
                )
                # Send error notification
                error_message = WebSocketMessage(
                    event_type=EventType.SYSTEM_NOTIFICATION,
                    data={"error": f"Message handling failed: {str(e)}"},
                    tenant_id=final_tenant_id,
                    user_id=final_user_id,
                )
                await websocket.send_text(json.dumps(error_message.to_dict()))

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=4000, reason=f"Connection error: {str(e)}")

    finally:
        # Clean up connection
        if connection_id:
            await websocket_manager.disconnect(connection_id)


async def _handle_client_message(
    connection_id: str, message: dict, user_id: str, tenant_id: str
):
    """Handle messages received from WebSocket clients."""
    message_type = message.get("type")

    if message_type == "subscribe":
        # Subscribe to event types
        subscriptions = message.get("subscriptions", [])
        for subscription in subscriptions:
            await websocket_manager.subscribe(connection_id, subscription)
        # Send confirmation
        response = WebSocketMessage(
            event_type=EventType.SYSTEM_NOTIFICATION,
            data={"type": "subscription_confirmed", "subscriptions": subscriptions},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        await websocket_manager.broadcast_to_user(user_id, response)
    elif message_type == "unsubscribe":
        # Unsubscribe from event types
        subscriptions = message.get("subscriptions", [])
        for subscription in subscriptions:
            await websocket_manager.unsubscribe(connection_id, subscription)
        # Send confirmation
        response = WebSocketMessage(
            event_type=EventType.SYSTEM_NOTIFICATION,
            data={"type": "unsubscription_confirmed", "subscriptions": subscriptions},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        await websocket_manager.broadcast_to_user(user_id, response)
    elif message_type == "ping":
        # Respond to ping with pong
        response = WebSocketMessage(
            event_type=EventType.SYSTEM_NOTIFICATION,
            data={"type": "pong", "timestamp": message.get("timestamp")},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        await websocket_manager.broadcast_to_user(user_id, response)
    elif message_type == "get_stats":
        # Return connection statistics
        stats = await websocket_manager.get_connection_stats()
        response = WebSocketMessage(
            event_type=EventType.SYSTEM_NOTIFICATION,
            data={"type": "stats", "stats": stats},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        await websocket_manager.broadcast_to_user(user_id, response)
    else:
        # Unknown message type
        response = WebSocketMessage(
            event_type=EventType.SYSTEM_NOTIFICATION,
            data={"error": f"Unknown message type: {message_type}"},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        await websocket_manager.broadcast_to_user(user_id, response)


# REST API endpoints for WebSocket management


@router.post("/broadcast/tenant/{tenant_id}")
@standard_exception_handler
async def broadcast_to_tenant(
    tenant_id: str,
    message_data: dict,
    subscription_filter: Optional[str] = None,
    current_user=Depends(get_current_user_optional),
):
    """
    Broadcast message to all WebSocket connections for a tenant.

    Args:
        tenant_id: Target tenant ID
        message_data: Message data containing event_type and data
        subscription_filter: Optional subscription filter
    """
    # Verify user has permission to broadcast to this tenant
    if current_user and current_user.get("tenant_id") != tenant_id:
        raise HTTPException(
            status_code=403, detail="Cannot broadcast to different tenant"
        )

    # Create WebSocket message
    message = WebSocketMessage(
        event_type=EventType(message_data["event_type"]),
        data=message_data["data"],
        tenant_id=tenant_id,
        user_id=current_user.get("user_id") if current_user else None,
    )

    try:
        # Broadcast message
        await websocket_manager.broadcast_to_tenant(
            tenant_id, message, subscription_filter
        )
        return {"status": "success", "message": "Broadcast sent"}

    except Exception as e:
        logger.error(f"Failed to broadcast to tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Broadcast failed: {str(e)}"
        ) from e


@router.post("/broadcast/user/{user_id}")
@standard_exception_handler
async def broadcast_to_user(
    user_id: str,
    message_data: dict,
    subscription_filter: Optional[str] = None,
    current_user=Depends(get_current_user_optional),
):
    """
    Broadcast message to all WebSocket connections for a user.

    Args:
        user_id: Target user ID
        message_data: Message data containing event_type and data
        subscription_filter: Optional subscription filter
    """
    # Verify user has permission (can only broadcast to self unless admin)
    if current_user and current_user.get("user_id") != user_id:
        # Check if user is admin or has broadcast permissions
        user_roles = current_user.get("roles", [])
        if "admin" not in user_roles and "broadcast" not in user_roles:
            raise HTTPException(
                status_code=403, detail="Cannot broadcast to different user"
            )

    # Create WebSocket message
    message = WebSocketMessage(
        event_type=EventType(message_data["event_type"]),
        data=message_data["data"],
        tenant_id=current_user.get("tenant_id") if current_user else "system",
        user_id=current_user.get("user_id") if current_user else None,
    )

    try:
        # Broadcast message
        await websocket_manager.broadcast_to_user(user_id, message, subscription_filter)
        return {"status": "success", "message": "Broadcast sent"}

    except Exception as e:
        logger.error(f"Failed to broadcast to user {user_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Broadcast failed: {str(e)}"
        ) from e


@router.post("/broadcast/subscription/{subscription}")
@standard_exception_handler
async def broadcast_to_subscription(
    subscription: str,
    message_data: dict,
    tenant_filter: Optional[str] = None,
    current_user=Depends(get_current_user_optional),
):
    """
    Broadcast message to all WebSocket connections with a specific subscription.

    Args:
        subscription: Target subscription name
        message_data: Message data containing event_type and data
        tenant_filter: Optional tenant filter
    """
    # Create WebSocket message
    message = WebSocketMessage(
        event_type=EventType(message_data["event_type"]),
        data=message_data["data"],
        tenant_id=current_user.get("tenant_id") if current_user else "system",
        user_id=current_user.get("user_id") if current_user else None,
    )

    try:
        # Broadcast message
        await websocket_manager.broadcast_to_subscription(
            subscription, message, tenant_filter
        )
        return {"status": "success", "message": "Broadcast sent"}

    except Exception as e:
        logger.error(f"Failed to broadcast to subscription {subscription}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Broadcast failed: {str(e)}"
        ) from e


@router.get("/stats")
@standard_exception_handler
async def get_websocket_stats(current_user=Depends(get_current_user_optional)):
    """Get WebSocket connection statistics."""
    stats = await websocket_manager.get_connection_stats()
    return {"status": "success", "stats": stats}


# Event broadcasting helper functions for use by other modules


async def broadcast_billing_event(
    event_type: str, data: dict, tenant_id: str, user_id: Optional[str] = None
):
    """
    Broadcast billing-related events.

    Args:
        event_type: Billing event type (payment_processed, invoice_generated, etc.)
        data: Event data
        tenant_id: Tenant ID
        user_id: Optional user ID for user-specific events
    """
    # Map event types to WebSocket event types
    event_mapping = {
        "payment_processed": EventType.PAYMENT_PROCESSED,
        "invoice_generated": EventType.INVOICE_GENERATED,
        "billing_updated": EventType.BILLING_UPDATE,
    }

    websocket_event_type = event_mapping.get(event_type, EventType.BILLING_UPDATE)
    message = WebSocketMessage(
        event_type=websocket_event_type, data=data, tenant_id=tenant_id, user_id=user_id
    )
    # Broadcast to billing subscription subscribers
    await websocket_manager.broadcast_to_subscription(
        "billing_updates", message, tenant_id
    )


async def broadcast_service_event(
    event_type: str, data: dict, tenant_id: str, user_id: Optional[str] = None
):
    """
    Broadcast service-related events.

    Args:
        event_type: Service event type (activated, suspended, etc.)
        data: Event data
        tenant_id: Tenant ID
        user_id: Optional user ID for user-specific events
    """
    # Map event types to WebSocket event types
    event_mapping = {
        "service_activated": EventType.SERVICE_ACTIVATED,
        "service_suspended": EventType.SERVICE_SUSPENDED,
    }

    websocket_event_type = event_mapping.get(event_type, EventType.SYSTEM_NOTIFICATION)
    message = WebSocketMessage(
        event_type=websocket_event_type, data=data, tenant_id=tenant_id, user_id=user_id
    )
    # Broadcast to service subscription subscribers
    await websocket_manager.broadcast_to_subscription(
        "service_updates", message, tenant_id
    )


async def broadcast_network_alert(
    alert_data: dict, tenant_id: str, severity: str = "medium"
):
    """
    Broadcast network alerts.

    Args:
        alert_data: Alert data
        tenant_id: Tenant ID
        severity: Alert severity (low, medium, high, critical)
    """
    message = WebSocketMessage(
        event_type=EventType.NETWORK_ALERT,
        data={"severity": severity, "alert": alert_data},
        tenant_id=tenant_id,
    )
    # Broadcast to network monitoring subscription subscribers
    await websocket_manager.broadcast_to_subscription(
        "network_alerts", message, tenant_id
    )


async def broadcast_ticket_update(
    ticket_data: dict, tenant_id: str, user_id: Optional[str] = None
):
    """
    Broadcast ticket updates.

    Args:
        ticket_data: Ticket data
        tenant_id: Tenant ID
        user_id: Optional user ID for user-specific updates
    """
    message = WebSocketMessage(
        event_type=EventType.TICKET_UPDATED,
        data=ticket_data,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    # Broadcast to support subscription subscribers
    await websocket_manager.broadcast_to_subscription(
        "support_updates", message, tenant_id
    )
