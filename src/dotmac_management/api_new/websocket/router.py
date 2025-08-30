"""WebSocket Router for Management Platform Real-time Communication."""

import json
import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.security import HTTPBearer

from dotmac_shared.api.router_factory import (
    Query,
    RouterFactory,
    WebSocket,
    WebSocketDisconnect,
)

from ...core.auth import verify_token
from ...core.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()
router = APIRouter()
security = HTTPBearer()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    user_type: Optional[str] = Query(None),  # admin, tenant, partner
    user_id: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for Management Platform real-time communication.

    Query Parameters:
    - token: JWT authentication token
    - user_type: Type of user (admin, tenant, partner)
    - user_id: User ID

    Usage:
    ```javascript
    const ws = new WebSocket(`ws://localhost:8001/api/ws?token=${jwt_token}&user_type=admin`);
    ```
    """
    connection_id = None

    try:
        # Authenticate the WebSocket connection
        if not token:
            await websocket.close(code=4001, reason="Authentication token required")
            return

        try:
            # Verify token and get user info
            user_info = await verify_token(token)
            user_id = user_id or user_info.get("sub")
            user_type = user_type or user_info.get("user_type", "admin")

        except Exception as auth_error:
            logger.warning(f"WebSocket authentication failed: {auth_error}")
            await websocket.close(code=4003, reason="Invalid authentication token")
            return

        # Connect based on user type
        if user_type == "admin":
            await websocket_manager.connect_admin(websocket, user_id)
        elif user_type == "tenant":
            tenant_id = user_info.get("tenant_id") or user_id
            await websocket_manager.connect_tenant(websocket, tenant_id)
        elif user_type == "partner":
            partner_id = user_info.get("partner_id") or user_id
            await websocket_manager.connect_partner(websocket, partner_id)
        else:
            await websocket.close(code=4004, reason="Invalid user type")
            return

        logger.info(f"WebSocket connected: {user_type}:{user_id}")

        # WebSocket message loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle different message types
                message_type = message.get("type")

                if message_type == "ping":
                    # Respond to ping with pong
                    await websocket.send_text(
                        json.dumps(
                            {"type": "pong", "timestamp": message.get("timestamp")}
                        )
                    )

                elif message_type == "subscribe":
                    # Subscribe to specific events (implement as needed)
                    events = message.get("events", [])
                    logger.info(f"User {user_id} subscribed to events: {events}")
                    await websocket.send_text(
                        json.dumps({"type": "subscription_confirmed", "events": events})
                    )

                elif message_type == "get_status":
                    # Send current status
                    stats = websocket_manager.get_connection_stats()
                    await websocket.send_text(
                        json.dumps({"type": "status", "stats": stats})
                    )

                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "message": f"Unknown message type: {message_type}",
                            }
                        )
                    )

            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON format"})
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {user_type}:{user_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass

    finally:
        # Ensure disconnection is handled
        if connection_id:
            await websocket_manager.disconnect(websocket)
