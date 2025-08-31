"""WebSocket Events API Router for the Management Platform."""

import json
import logging
from typing import List, Optional

from fastapi import Depends, Query, WebSocket, WebSocketDisconnect

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.rate_limiting_decorators import rate_limit, rate_limit_strict
from dotmac_shared.api.router_factory import RouterFactory

from ...dependencies import get_current_user, get_websocket_service
from ...models.websocket_event import EventPriority, EventType
from ...schemas.websocket_schemas import (
    BroadcastRequest,
    ConnectionStatsResponse,
    EventAcknowledgmentRequest,
    EventStatsResponse,
    WebSocketConnectionResponse,
    WebSocketEventCreate,
    WebSocketEventListResponse,
    WebSocketEventResponse,
    WebSocketSubscriptionCreate,
)
from ...services.websocket_service import WebSocketEventService

logger = logging.getLogger(__name__)

# Create router using RouterFactory
router = RouterFactory.create_router(
    prefix="/websocket",
    tags=["WebSocket Events"],
    dependencies=[Depends(get_current_user)]
)


# WebSocket Connection Endpoint

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT authentication token"),
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """
    WebSocket endpoint for real-time communication.
    
    Supports:
    - Event subscriptions
    - Real-time notifications
    - Event acknowledgments
    - Connection health monitoring
    """
    connection_id = None
    
    try:
        # For demo purposes, extract user info from token
        # In production, implement proper JWT token validation
        if not token:
            await websocket.close(code=4001, reason="Authentication token required")
            return
        
        # Mock user extraction - replace with actual JWT validation
        user_id = "demo_user"
        tenant_id = "demo_tenant"
        
        # Register connection
        connection_id = await websocket_service.register_connection(
            websocket=websocket,
            user_id=user_id,
            tenant_id=tenant_id,
            client_ip=websocket.client.host if websocket.client else None
        )
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                await _handle_websocket_message(
                    connection_id=connection_id,
                    message=message,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    websocket_service=websocket_service
                )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {connection_id}")
                break
            except json.JSONDecodeError:
                # Send error message for invalid JSON
                error_message = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_message))
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                error_message = {
                    "type": "error",
                    "message": f"Message handling failed: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_message))
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        if websocket.client_state.CONNECTED:
            await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
    
    finally:
        # Clean up connection
        if connection_id:
            await websocket_service.unregister_connection(connection_id)


async def _handle_websocket_message(
    connection_id: str,
    message: dict,
    user_id: str,
    tenant_id: str,
    websocket_service: WebSocketEventService
):
    """Handle messages received from WebSocket clients."""
    message_type = message.get("type")
    
    if message_type == "subscribe":
        # Subscribe to event types
        subscription_name = message.get("subscription_name", "default")
        event_types = message.get("event_types", [])
        entity_filter = message.get("entity_filter")
        
        await websocket_service.subscribe_to_events(
            connection_id=connection_id,
            user_id=user_id,
            tenant_id=tenant_id,
            subscription_name=subscription_name,
            event_types=event_types,
            entity_filter=entity_filter
        )
        
        # Send confirmation
        websocket = websocket_service.active_connections.get(connection_id)
        if websocket:
            response = {
                "type": "subscription_confirmed",
                "subscription_name": subscription_name,
                "event_types": event_types,
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(response))
    
    elif message_type == "acknowledge":
        # Acknowledge an event
        event_id = message.get("event_id")
        if event_id:
            await websocket_service.acknowledge_event(
                event_id=event_id,
                tenant_id=tenant_id,
                user_id=user_id
            )
    
    elif message_type == "ping":
        # Respond to ping with pong
        websocket = websocket_service.active_connections.get(connection_id)
        if websocket:
            response = {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(response))
    
    elif message_type == "get_events":
        # Send recent events to client
        limit = message.get("limit", 10)
        event_types = message.get("event_types")
        unacknowledged_only = message.get("unacknowledged_only", False)
        
        events = await websocket_service.get_user_events(
            user_id=user_id,
            tenant_id=tenant_id,
            event_types=event_types,
            limit=limit,
            unacknowledged_only=unacknowledged_only
        )
        
        websocket = websocket_service.active_connections.get(connection_id)
        if websocket:
            response = {
                "type": "events_list",
                "events": [
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "title": event.title,
                        "data": event.event_data,
                        "priority": event.priority,
                        "created_at": event.created_at.isoformat(),
                        "requires_acknowledgment": event.requires_acknowledgment
                    }
                    for event in events
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(response))


# REST API Endpoints for Event Management

@router.post("/events", response_model=WebSocketEventResponse)
@rate_limit_strict(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def create_event(
    event_data: WebSocketEventCreate,
    current_user: dict = Depends(get_current_user),
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """Create a new WebSocket event."""
    event = await websocket_service.create_event(
        tenant_id=current_user["tenant_id"],
        event_type=event_data.event_type,
        title=event_data.title,
        event_data=event_data.event_data,
        user_id=current_user["user_id"],
        target_user_id=event_data.target_user_id,
        target_user_ids=event_data.target_user_ids,
        priority=event_data.priority,
        requires_acknowledgment=event_data.requires_acknowledgment,
        expires_in_hours=event_data.expires_in_hours,
        broadcast_to_tenant=event_data.broadcast_to_tenant
    )
    
    return WebSocketEventResponse(
        id=event.id,
        event_id=event.event_id,
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        event_category=event.event_category,
        title=event.title,
        description=event.description,
        event_data=event.event_data,
        priority=event.priority,
        target_user_id=event.target_user_id,
        target_user_ids=event.target_user_ids,
        broadcast_to_tenant=event.broadcast_to_tenant,
        delivery_status=event.delivery_status,
        delivery_attempts=event.delivery_attempts,
        delivered_at=event.delivered_at,
        expires_at=event.expires_at,
        source_service=event.source_service,
        acknowledged_by=event.acknowledged_by,
        acknowledged_at=event.acknowledged_at,
        created_at=event.created_at,
        updated_at=event.updated_at
    )


@router.post("/broadcast/tenant", response_model=WebSocketEventResponse)
@rate_limit_strict(max_requests=30, time_window_seconds=60)
@standard_exception_handler
async def broadcast_to_tenant(
    broadcast_data: BroadcastRequest,
    current_user: dict = Depends(get_current_user),
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """Broadcast event to all users in the tenant."""
    event = await websocket_service.broadcast_to_tenant(
        tenant_id=current_user["tenant_id"],
        event_type=broadcast_data.event_type,
        title=broadcast_data.title,
        event_data=broadcast_data.data,
        user_id=current_user["user_id"],
        priority=broadcast_data.priority
    )
    
    return WebSocketEventResponse(
        id=event.id,
        event_id=event.event_id,
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        event_category=event.event_category,
        title=event.title,
        event_data=event.event_data,
        priority=event.priority,
        broadcast_to_tenant=event.broadcast_to_tenant,
        delivery_status=event.delivery_status,
        created_at=event.created_at
    )


@router.post("/send/{user_id}", response_model=WebSocketEventResponse)
@rate_limit_strict(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def send_to_user(
    user_id: str,
    event_data: WebSocketEventCreate,
    current_user: dict = Depends(get_current_user),
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """Send event to a specific user."""
    event = await websocket_service.send_to_user(
        user_id=user_id,
        tenant_id=current_user["tenant_id"],
        event_type=event_data.event_type,
        title=event_data.title,
        event_data=event_data.event_data,
        sender_user_id=current_user["user_id"],
        priority=event_data.priority,
        requires_acknowledgment=event_data.requires_acknowledgment
    )
    
    return WebSocketEventResponse(
        id=event.id,
        event_id=event.event_id,
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        title=event.title,
        event_data=event.event_data,
        priority=event.priority,
        target_user_id=event.target_user_id,
        delivery_status=event.delivery_status,
        created_at=event.created_at
    )


# Event Management

@router.get("/events", response_model=WebSocketEventListResponse)
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def list_user_events(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    event_types: Optional[str] = Query(None, description="Comma-separated event types"),
    unacknowledged_only: bool = Query(False, description="Only unacknowledged events"),
    current_user: dict = Depends(get_current_user),
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """List events for the current user."""
    # Parse event types
    parsed_event_types = None
    if event_types:
        try:
            parsed_event_types = [EventType(et.strip()) for et in event_types.split(",")]
        except ValueError:
            parsed_event_types = None
    
    events = await websocket_service.get_user_events(
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        event_types=parsed_event_types,
        limit=size,
        unacknowledged_only=unacknowledged_only
    )
    
    # Convert to response format
    event_responses = []
    for event in events:
        event_responses.append(WebSocketEventResponse(
            id=event.id,
            event_id=event.event_id,
            tenant_id=event.tenant_id,
            event_type=event.event_type,
            event_category=event.event_category,
            title=event.title,
            description=event.description,
            event_data=event.event_data,
            priority=event.priority,
            delivery_status=event.delivery_status,
            acknowledged_by=event.acknowledged_by,
            acknowledged_at=event.acknowledged_at,
            created_at=event.created_at
        ))
    
    total = len(event_responses)
    pages = (total + size - 1) // size
    
    return WebSocketEventListResponse(
        items=event_responses,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.post("/events/{event_id}/acknowledge")
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def acknowledge_event(
    event_id: str,
    acknowledgment: EventAcknowledgmentRequest,
    current_user: dict = Depends(get_current_user),
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """Acknowledge an event."""
    success = await websocket_service.acknowledge_event(
        event_id=event_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"]
    )
    
    return {"success": success, "message": "Event acknowledged successfully"}


# Statistics and Monitoring

@router.get("/stats/events", response_model=EventStatsResponse)
@rate_limit(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def get_event_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user),
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """Get event statistics for the tenant."""
    stats = await websocket_service.get_tenant_event_stats(
        tenant_id=current_user["tenant_id"],
        days=days
    )
    
    return EventStatsResponse(
        tenant_id=current_user["tenant_id"],
        **stats
    )


@router.get("/stats/connections", response_model=ConnectionStatsResponse)
@rate_limit(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def get_connection_stats(
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """Get current connection statistics."""
    stats = await websocket_service.get_connection_stats()
    
    return ConnectionStatsResponse(**stats)


# Administrative Endpoints

@router.post("/admin/broadcast", response_model=WebSocketEventResponse)
@rate_limit_strict(max_requests=10, time_window_seconds=60)
@standard_exception_handler
async def admin_broadcast(
    broadcast_data: BroadcastRequest,
    target_tenant_id: Optional[str] = Query(None, description="Target tenant ID"),
    current_user: dict = Depends(get_current_user),
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """Administrative broadcast to specific tenant or all tenants."""
    # Check if user has admin privileges
    user_roles = current_user.get("roles", [])
    if "admin" not in user_roles:
        raise PermissionError("Admin privileges required")
    
    # Use target tenant or current user's tenant
    tenant_id = target_tenant_id or current_user["tenant_id"]
    
    event = await websocket_service.broadcast_to_tenant(
        tenant_id=tenant_id,
        event_type=broadcast_data.event_type,
        title=broadcast_data.title,
        event_data=broadcast_data.data,
        user_id=current_user["user_id"],
        priority=broadcast_data.priority
    )
    
    return WebSocketEventResponse(
        id=event.id,
        event_id=event.event_id,
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        title=event.title,
        event_data=event.event_data,
        priority=event.priority,
        broadcast_to_tenant=event.broadcast_to_tenant,
        delivery_status=event.delivery_status,
        created_at=event.created_at
    )


@router.post("/admin/process-pending")
@rate_limit_strict(max_requests=5, time_window_seconds=60)
@standard_exception_handler
async def process_pending_events(
    target_tenant_id: Optional[str] = Query(None, description="Target tenant ID"),
    current_user: dict = Depends(get_current_user),
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """Process pending events (admin only)."""
    # Check if user has admin privileges
    user_roles = current_user.get("roles", [])
    if "admin" not in user_roles:
        raise PermissionError("Admin privileges required")
    
    count = await websocket_service.process_pending_events(target_tenant_id)
    
    return {
        "processed_events": count,
        "message": f"Processed {count} pending events"
    }


@router.post("/admin/cleanup")
@rate_limit_strict(max_requests=2, time_window_seconds=300)
@standard_exception_handler
async def cleanup_websocket_data(
    current_user: dict = Depends(get_current_user),
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """Clean up expired events and stale connections (admin only)."""
    # Check if user has admin privileges
    user_roles = current_user.get("roles", [])
    if "admin" not in user_roles:
        raise PermissionError("Admin privileges required")
    
    expired_events = await websocket_service.cleanup_expired_events()
    stale_connections = await websocket_service.cleanup_stale_connections()
    
    return {
        "expired_events_cleaned": expired_events,
        "stale_connections_cleaned": stale_connections,
        "message": f"Cleaned up {expired_events} events and {stale_connections} connections"
    }


# Health Check

@router.get("/health")
@standard_exception_handler
async def websocket_service_health(
    websocket_service: WebSocketEventService = Depends(get_websocket_service)
):
    """Check WebSocket service health."""
    stats = await websocket_service.get_connection_stats()
    
    return {
        "status": "healthy",
        "service": "websocket_events",
        "active_connections": stats["total_connections"],
        "timestamp": datetime.utcnow().isoformat()
    }