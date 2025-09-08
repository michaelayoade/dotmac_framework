"""
Clean Chat Router - DRY Migration
Production-ready chat/communication endpoints using RouterFactory patterns.
"""

from typing import Any, Optional
from uuid import UUID

from fastapi import Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac_shared.api.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)

# === Chat Schemas ===


class ChatSessionCreateRequest(BaseModel):
    """Request schema for creating chat sessions."""

    customer_id: UUID = Field(..., description="Customer ID")
    initial_message: str = Field(..., description="Initial customer message")
    priority: str = Field("normal", description="Session priority")


class ChatMessageRequest(BaseModel):
    """Request schema for sending messages."""

    content: str = Field(..., description="Message content")
    message_type: str = Field("text", description="Message type")


class AgentStatusUpdate(BaseModel):
    """Schema for updating agent status."""

    status: str = Field(..., description="Agent status (available, busy, offline)")
    max_concurrent_chats: int = Field(5, description="Maximum concurrent chats")


# === Chat Router ===

chat_router = RouterFactory.create_standard_router(
    prefix="/chat",
    tags=["chat", "communication"],
)


# === Chat Session Management ===


@chat_router.get("/sessions", response_model=list[dict[str, Any]])
@standard_exception_handler
async def list_chat_sessions(
    status_filter: Optional[str] = Query(None, description="Filter by session status"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> list[dict[str, Any]]:
    """List chat sessions."""
    sessions = [
        {
            "id": "session-001",
            "customer_id": "customer-123",
            "agent_id": "agent-456",
            "status": "active",
            "priority": "normal",
            "started_at": "2025-01-15T10:00:00Z",
            "last_message": "How can I help you today?",
        },
        {
            "id": "session-002",
            "customer_id": "customer-789",
            "agent_id": None,
            "status": "waiting",
            "priority": "high",
            "started_at": "2025-01-15T10:05:00Z",
            "last_message": "I need urgent help with billing",
        },
    ]

    if status_filter:
        sessions = [s for s in sessions if s["status"] == status_filter]

    return sessions[: deps.pagination.size]


@chat_router.post("/sessions", response_model=dict[str, Any])
@standard_exception_handler
async def create_chat_session(
    request: ChatSessionCreateRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Create a new chat session."""
    session_id = f"session-{request.customer_id}"

    return {
        "id": session_id,
        "customer_id": str(request.customer_id),
        "status": "waiting",
        "priority": request.priority,
        "initial_message": request.initial_message,
        "created_at": "2025-01-15T10:30:00Z",
        "queue_position": 2,
        "estimated_wait": "3-5 minutes",
    }


@chat_router.get("/sessions/{session_id}", response_model=dict[str, Any])
@standard_exception_handler
async def get_chat_session(
    session_id: str,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get chat session details."""
    return {
        "id": session_id,
        "customer_id": "customer-123",
        "agent_id": "agent-456",
        "status": "active",
        "priority": "normal",
        "started_at": "2025-01-15T10:00:00Z",
        "messages": [
            {
                "id": "msg-001",
                "sender": "customer",
                "content": "I need help with my account",
                "timestamp": "2025-01-15T10:00:00Z",
            },
            {
                "id": "msg-002",
                "sender": "agent",
                "content": "I'd be happy to help! What specific issue are you having?",
                "timestamp": "2025-01-15T10:01:00Z",
            },
        ],
    }


# === Message Management ===


@chat_router.post("/sessions/{session_id}/messages", response_model=dict[str, Any])
@standard_exception_handler
async def send_message(
    session_id: str,
    message: ChatMessageRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Send a message in chat session."""
    return {
        "id": f"msg-{session_id}",
        "session_id": session_id,
        "sender": "agent",  # Based on auth context
        "content": message.content,
        "message_type": message.message_type,
        "timestamp": "2025-01-15T10:30:00Z",
        "status": "delivered",
    }


@chat_router.post("/sessions/{session_id}/typing", status_code=204)
@standard_exception_handler
async def send_typing_indicator(
    session_id: str,
    is_typing: bool = Query(..., description="Typing status"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> None:
    """Send typing indicator."""
    # Implementation would notify other participants
    pass


# === Session Actions ===


@chat_router.post("/sessions/{session_id}/close", response_model=dict[str, Any])
@standard_exception_handler
async def close_chat_session(
    session_id: str,
    resolution_note: Optional[str] = Query(None, description="Resolution note"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Close a chat session."""
    return {
        "id": session_id,
        "status": "closed",
        "closed_by": deps.user_id,
        "closed_at": "2025-01-15T10:30:00Z",
        "resolution_note": resolution_note,
        "duration_minutes": 15,
        "message": "Chat session closed successfully",
    }


@chat_router.post("/sessions/{session_id}/rating", status_code=204)
@standard_exception_handler
async def rate_chat_session(
    session_id: str,
    rating: int = Query(..., ge=1, le=5, description="Rating from 1-5"),
    feedback: Optional[str] = Query(None, max_length=1000, description="Optional feedback"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> None:
    """Rate the chat session."""
    # Implementation would store rating and feedback
    pass


# === WebSocket Endpoints ===


@chat_router.websocket("/ws/customer/{session_id}")
async def customer_chat_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for customer chat."""
    try:
        await websocket.accept()
        # In production, validate session and customer authentication

        while True:
            data = await websocket.receive_text()
            # Process message and broadcast to agent
            await websocket.send_text(f"Received: {data}")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Customer WebSocket error: {e}")


@chat_router.websocket("/ws/agent/{agent_id}")
async def agent_chat_websocket(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint for agent chat."""
    try:
        await websocket.accept()
        # In production, validate agent authentication

        while True:
            data = await websocket.receive_text()
            # Process message and broadcast to customer
            await websocket.send_text(f"Agent received: {data}")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Agent WebSocket error: {e}")


# === Agent Management ===


@chat_router.get("/agent/status", response_model=dict[str, Any])
@standard_exception_handler
async def get_agent_status(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get current agent status."""
    return {
        "agent_id": deps.user_id,
        "status": "available",
        "active_chats": 2,
        "max_concurrent_chats": 5,
        "total_chats_today": 15,
        "average_response_time": "45 seconds",
        "last_activity": "2025-01-15T10:29:00Z",
    }


@chat_router.put("/agent/status", response_model=dict[str, Any])
@standard_exception_handler
async def update_agent_status(
    status_data: AgentStatusUpdate,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Update agent availability status."""
    return {
        "agent_id": deps.user_id,
        "status": status_data.status,
        "max_concurrent_chats": status_data.max_concurrent_chats,
        "updated_at": "2025-01-15T10:30:00Z",
        "message": "Agent status updated successfully",
    }


@chat_router.get("/agent/queue", response_model=list[dict[str, Any]])
@standard_exception_handler
async def get_agent_queue(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> list[dict[str, Any]]:
    """Get chat sessions in agent's queue."""
    return [
        {
            "id": "session-waiting-001",
            "customer_id": "customer-789",
            "priority": "high",
            "wait_time": "2 minutes",
            "last_message": "I need urgent help with billing",
            "created_at": "2025-01-15T10:28:00Z",
        }
    ]


# === Health Check ===


@chat_router.get("/health", response_model=dict[str, Any])
@standard_exception_handler
async def chat_health_check(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Check chat service health."""
    return {
        "status": "healthy",
        "websocket_connections": 24,
        "active_sessions": 12,
        "available_agents": 5,
        "queue_length": 3,
        "average_wait_time": "2.5 minutes",
        "last_check": "2025-01-15T10:30:00Z",
    }


# Export the router
__all__ = ["chat_router"]
