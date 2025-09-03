"""
Live Chat API Router - WebSocket and REST API endpoints
Leverages existing DotMac patterns for authentication and routing
"""

from typing import Any, Dict, List, Optional
from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, status
from fastapi.responses import JSONResponse

from dotmac_shared.api.dependencies import (
    StandardDependencies, PaginatedDependencies,
    get_standard_deps, get_paginated_deps, get_admin_deps
)
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.rate_limiting_decorators import rate_limit
from dotmac_shared.api.router_factory import RouterFactory

from .live_chat_plugin import (
    ChatSessionCreate, ChatSessionResponse, ChatMessageCreate, ChatMessageResponse,
    AgentStatusUpdate, LiveChatPlugin
)
from .chat_service import ChatService

# Initialize services
live_chat_plugin = LiveChatPlugin()
chat_service = ChatService()

# Create router using existing RouterFactory pattern
router = RouterFactory.create_crud_router(
    service_class=ChatService,
    create_schema=ChatSessionCreate,
    update_schema=None,  # Chat sessions are managed through WebSocket
    response_schema=ChatSessionResponse,
    prefix="/chat",
    tags=["live-chat"],
    enable_search=False,
    enable_bulk_operations=False
)


# Customer Chat Endpoints

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, time_window_seconds=300)  # Prevent session spam
@standard_exception_handler
async def create_chat_session(
    session_data: ChatSessionCreate,
    deps: StandardDependencies = Depends(get_standard_deps)
):
    """Create a new chat session."""
    customer_info = getattr(deps, 'current_customer', None) if hasattr(deps, 'current_customer') else None
    
    session = await chat_service.create_session(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        session_data=session_data,
        customer_id=customer_info.get('id') if customer_info else None,
        ip_address=deps.request.client.host,
        user_agent=deps.request.headers.get('user-agent')
    )
    
    return session


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
@standard_exception_handler
async def get_chat_session(
    session_id: str,
    deps: StandardDependencies = Depends(get_standard_deps)
):
    """Get chat session details."""
    session = await chat_service.get_session(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        session_id=session_id
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    # Verify customer has access to this session
    customer_info = getattr(deps, 'current_customer', None) if hasattr(deps, 'current_customer') else None
    if customer_info and session.customer_id != str(customer_info.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return session


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
@standard_exception_handler
async def get_chat_messages(
    session_id: str,
    deps: PaginatedDependencies = Depends(get_paginated_deps),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """Get chat messages for a session."""
    messages = await chat_service.get_session_messages(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        session_id=session_id,
        page=page,
        page_size=page_size,
        include_internal=False  # Hide internal messages from customers
    )
    
    return messages


@router.post("/sessions/{session_id}/rating", status_code=status.HTTP_204_NO_CONTENT)
@standard_exception_handler
async def rate_chat_session(
    session_id: str,
    rating: int = Query(..., ge=1, le=5, description="Rating from 1-5"),
    feedback: Optional[str] = Query(None, max_length=1000, description="Optional feedback"),
    deps: StandardDependencies = Depends(get_standard_deps)
):
    """Rate the chat session."""
    success = await chat_service.rate_session(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        session_id=session_id,
        rating=rating,
        feedback=feedback
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )


# WebSocket Endpoints

@router.websocket("/ws/customer/{session_id}")
async def customer_chat_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for customer chat."""
    try:
        # In production, would validate session_id and get customer_id from JWT token
        customer_id = None  # Extract from WebSocket query params or headers
        
        await live_chat_plugin.handle_customer_websocket(
            websocket=websocket,
            session_id=session_id,
            customer_id=customer_id
        )
        
    except WebSocketDisconnect:
        pass
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Customer WebSocket error: {e}")


@router.websocket("/ws/agent/{agent_id}")
async def agent_chat_websocket(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint for agent chat."""
    try:
        # In production, would validate agent authentication from JWT token
        tenant_id = "default_tenant"  # Extract from auth token
        
        await live_chat_plugin.handle_agent_websocket(
            websocket=websocket,
            agent_id=agent_id,
            tenant_id=tenant_id
        )
        
    except WebSocketDisconnect:
        pass
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Agent WebSocket error: {e}")


# Agent Management Endpoints

@router.get("/agent/status", response_model=Dict[str, Any])
@standard_exception_handler
async def get_agent_status(
    deps: StandardDependencies = Depends(get_admin_deps)
):
    """Get current agent status."""
    if not hasattr(deps, 'current_user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent authentication required"
        )
    
    status_info = await chat_service.get_agent_status(
        db=deps.db,
        agent_id=str(deps.current_user.id),
        tenant_id=str(deps.tenant_id)
    )
    
    return status_info


@router.put("/agent/status", response_model=Dict[str, Any])
@standard_exception_handler
async def update_agent_status(
    status_data: AgentStatusUpdate,
    deps: StandardDependencies = Depends(get_admin_deps)
):
    """Update agent availability status."""
    if not hasattr(deps, 'current_user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent authentication required"
        )
    
    status_info = await chat_service.update_agent_status(
        db=deps.db,
        agent_id=str(deps.current_user.id),
        tenant_id=str(deps.tenant_id),
        status_data=status_data
    )
    
    return status_info


@router.get("/agent/queue", response_model=List[ChatSessionResponse])
@standard_exception_handler
async def get_agent_queue(
    deps: StandardDependencies = Depends(get_admin_deps)
):
    """Get chat sessions in agent's queue."""
    if not hasattr(deps, 'current_user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent authentication required"
        )
    
    sessions = await chat_service.get_agent_sessions(
        db=deps.db,
        agent_id=str(deps.current_user.id),
        tenant_id=str(deps.tenant_id),
        status_filter=["waiting", "active"]
    )
    
    return sessions


@router.post("/agent/sessions/{session_id}/accept", response_model=ChatSessionResponse)
@standard_exception_handler
async def accept_chat_session(
    session_id: str,
    deps: StandardDependencies = Depends(get_admin_deps)
):
    """Accept and start handling a chat session."""
    if not hasattr(deps, 'current_user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent authentication required"
        )
    
    session = await chat_service.assign_agent(
        db=deps.db,
        session_id=session_id,
        agent_id=str(deps.current_user.id),
        agent_name=deps.current_user.name or deps.current_user.email
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or already assigned"
        )
    
    return session


@router.post("/agent/sessions/{session_id}/transfer", response_model=ChatSessionResponse)
@standard_exception_handler
async def transfer_chat_session(
    session_id: str,
    target_agent_id: str,
    reason: Optional[str] = None,
    deps: StandardDependencies = Depends(get_admin_deps)
):
    """Transfer chat session to another agent."""
    if not hasattr(deps, 'current_user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent authentication required"
        )
    
    session = await chat_service.transfer_session(
        db=deps.db,
        session_id=session_id,
        from_agent_id=str(deps.current_user.id),
        to_agent_id=target_agent_id,
        reason=reason
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or transfer failed"
        )
    
    return session


@router.post("/agent/sessions/{session_id}/end", response_model=ChatSessionResponse)
@standard_exception_handler
async def end_chat_session(
    session_id: str,
    summary: Optional[str] = None,
    create_ticket: bool = False,
    deps: StandardDependencies = Depends(get_admin_deps)
):
    """End a chat session."""
    if not hasattr(deps, 'current_user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent authentication required"
        )
    
    session = await chat_service.end_session(
        db=deps.db,
        session_id=session_id,
        agent_id=str(deps.current_user.id),
        summary=summary,
        create_ticket=create_ticket
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    return session


# Admin Analytics Endpoints

@router.get("/admin/analytics/overview", response_model=Dict[str, Any])
@standard_exception_handler
async def get_chat_analytics_overview(
    deps: StandardDependencies = Depends(get_admin_deps),
    days: int = Query(30, ge=1, le=365, description="Analytics period in days")
):
    """Get chat analytics overview."""
    analytics = await chat_service.get_analytics_overview(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        days=days
    )
    
    return analytics


@router.get("/admin/analytics/agents", response_model=List[Dict[str, Any]])
@standard_exception_handler
async def get_agent_performance_analytics(
    deps: StandardDependencies = Depends(get_admin_deps),
    days: int = Query(30, ge=1, le=365, description="Analytics period in days")
):
    """Get agent performance analytics."""
    analytics = await chat_service.get_agent_performance_analytics(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        days=days
    )
    
    return analytics


@router.get("/admin/sessions", response_model=List[ChatSessionResponse])
@standard_exception_handler
async def list_chat_sessions(
    deps: PaginatedDependencies = Depends(get_paginated_deps),
    status_filter: Optional[List[str]] = Query(None, description="Filter by status"),
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """List chat sessions for admin review."""
    sessions, total_count = await chat_service.list_sessions(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        filters={
            "status": status_filter,
            "agent_id": agent_id,
            "date_from": date_from,
            "date_to": date_to
        },
        page=page,
        page_size=page_size
    )
    
    # Add pagination headers
    deps.response.headers["X-Total-Count"] = str(total_count)
    deps.response.headers["X-Page"] = str(page)
    deps.response.headers["X-Page-Size"] = str(page_size)
    
    return sessions


@router.get("/admin/queue/status", response_model=Dict[str, Any])
@standard_exception_handler
async def get_queue_status(
    deps: StandardDependencies = Depends(get_admin_deps)
):
    """Get current queue status and wait times."""
    queue_status = await chat_service.get_queue_status(
        db=deps.db,
        tenant_id=str(deps.tenant_id)
    )
    
    return queue_status


# Chat Widget Configuration Endpoint

@router.get("/widget/config", response_model=Dict[str, Any])
async def get_chat_widget_config():
    """Get chat widget configuration for frontend."""
    return {
        "enabled": True,
        "welcome_message": "Hello! How can we help you today?",
        "placeholder_text": "Type your message...",
        "business_hours": {
            "enabled": True,
            "timezone": "UTC",
            "monday": {"start": "09:00", "end": "17:00"},
            "tuesday": {"start": "09:00", "end": "17:00"},
            "wednesday": {"start": "09:00", "end": "17:00"},
            "thursday": {"start": "09:00", "end": "17:00"},
            "friday": {"start": "09:00", "end": "17:00"},
            "saturday": {"start": "10:00", "end": "16:00"},
            "sunday": None
        },
        "offline_message": "We're currently offline. Please leave a message and we'll get back to you.",
        "max_file_size_mb": 10,
        "allowed_file_types": [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx"],
        "enable_file_upload": True,
        "enable_emoji": True,
        "show_agent_typing": True,
        "auto_suggest_articles": True
    }


# Health Check Endpoint

@router.get("/health", response_model=Dict[str, Any])
async def chat_health_check():
    """Health check for chat system."""
    return {
        "status": "healthy",
        "timestamp": "2025-01-01T00:00:00Z",
        "active_connections": len(live_chat_plugin.connection_manager.active_connections),
        "agent_connections": len(live_chat_plugin.connection_manager.agent_connections),
        "queue_length": sum(len(queue) for queue in live_chat_plugin.connection_manager.chat_queues.values())
    }


# Export router for app inclusion
def get_chat_routers():
    """Get all chat routers."""
    return [router]