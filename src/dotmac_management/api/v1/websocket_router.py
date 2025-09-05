"""
WebSocket Router - DRY Migration
Real-time communication endpoints using RouterFactory patterns.
"""

from typing import Any

from fastapi import Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac_shared.api.dependencies import StandardDependencies, get_standard_deps

# === WebSocket Schemas ===


class WebSocketMessage(BaseModel):
    """WebSocket message schema."""

    type: str = Field(..., description="Message type")
    data: dict[str, Any] = Field(..., description="Message data")
    target: str | None = Field(None, description="Target recipient")
    channel: str | None = Field(None, description="Channel name")


# === WebSocket Router ===

websocket_router = RouterFactory.create_standard_router(
    prefix="/websockets",
    tags=["websockets"],
)


# === WebSocket Connection ===


@websocket_router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str | None = None,
    tenant_id: str | None = None,
) -> None:
    """WebSocket connection endpoint."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            message = WebSocketMessage(**data)

            if message.type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass


# === Health Check ===


@websocket_router.get("/health", response_model=dict[str, Any])
@standard_exception_handler
async def websocket_health_check(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """WebSocket service health check."""
    return {
        "status": "healthy",
        "active_connections": 0,
        "uptime_seconds": 0,
    }


# Export the router
__all__ = ["websocket_router"]
