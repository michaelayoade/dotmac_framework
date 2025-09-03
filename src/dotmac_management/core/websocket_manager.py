"""
WebSocket manager for real-time tenant deployment and management updates.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ManagementWebSocketManager:
    """
    WebSocket manager for Management Platform real-time updates.

    Handles tenant deployment status, infrastructure monitoring,
    billing updates, and administrative notifications.
    """

    def __init__(self):
        # Active connections organized by tenant and admin users
        self.tenant_connections: Dict[str, Set[WebSocket]] = (
            {}
        )  # tenant_id -> websockets
        self.admin_connections: Set[WebSocket] = set()  # Admin panel connections
        self.partner_connections: Dict[str, Set[WebSocket]] = (
            {}
        )  # partner_id -> websockets

        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

        self._running = False
        self._background_tasks: Set[asyncio.Task] = set()

    async def start(self):
        """Start the WebSocket manager."""
        self._running = True

        # Start background task for connection monitoring
        task = asyncio.create_task(self._monitor_connections())
        self._background_tasks.add(task)

        logger.info("🔌 Management Platform WebSocket manager started")

    async def stop(self):
        """Stop the WebSocket manager."""
        self._running = False

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._background_tasks.clear()

        # Close all connections
        await self._close_all_connections()

        logger.info("🔌 Management Platform WebSocket manager stopped")

    async def connect_admin(self, websocket: WebSocket, admin_id: str):
        """Connect an admin user to receive management updates."""
        await websocket.accept()
        self.admin_connections.add(websocket)

        self.connection_metadata[websocket] = {
            "type": "admin",
            "admin_id": admin_id,
            "connected_at": datetime.now(timezone.utc),
            "last_ping": datetime.now(timezone.utc),
        }

        # Send initial status
        await self._send_to_websocket(
            websocket,
            {
                "type": "connection_established",
                "role": "admin",
                "admin_id": admin_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"👑 Admin {admin_id} connected to WebSocket")

    async def connect_tenant(self, websocket: WebSocket, tenant_id: str):
        """Connect a tenant user to receive their deployment updates."""
        await websocket.accept()

        if tenant_id not in self.tenant_connections:
            self.tenant_connections[tenant_id] = set()

        self.tenant_connections[tenant_id].add(websocket)

        self.connection_metadata[websocket] = {
            "type": "tenant",
            "tenant_id": tenant_id,
            "connected_at": datetime.now(timezone.utc),
            "last_ping": datetime.now(timezone.utc),
        }

        # Send initial status
        await self._send_to_websocket(
            websocket,
            {
                "type": "connection_established",
                "role": "tenant",
                "tenant_id": tenant_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"🏢 Tenant {tenant_id} connected to WebSocket")

    async def connect_partner(self, websocket: WebSocket, partner_id: str):
        """Connect a partner user to receive their customer updates."""
        await websocket.accept()

        if partner_id not in self.partner_connections:
            self.partner_connections[partner_id] = set()

        self.partner_connections[partner_id].add(websocket)

        self.connection_metadata[websocket] = {
            "type": "partner",
            "partner_id": partner_id,
            "connected_at": datetime.now(timezone.utc),
            "last_ping": datetime.now(timezone.utc),
        }

        # Send initial status
        await self._send_to_websocket(
            websocket,
            {
                "type": "connection_established",
                "role": "partner",
                "partner_id": partner_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"🤝 Partner {partner_id} connected to WebSocket")

    async def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket."""
        metadata = self.connection_metadata.get(websocket, {})
        connection_type = metadata.get("type", "unknown")

        if connection_type == "admin":
            self.admin_connections.discard(websocket)
            admin_id = metadata.get("admin_id", "unknown")
            logger.info(f"👑 Admin {admin_id} disconnected from WebSocket")

        elif connection_type == "tenant":
            tenant_id = metadata.get("tenant_id")
            if tenant_id and tenant_id in self.tenant_connections:
                self.tenant_connections[tenant_id].discard(websocket)
                if not self.tenant_connections[tenant_id]:
                    del self.tenant_connections[tenant_id]
            logger.info(f"🏢 Tenant {tenant_id} disconnected from WebSocket")

        elif connection_type == "partner":
            partner_id = metadata.get("partner_id")
            if partner_id and partner_id in self.partner_connections:
                self.partner_connections[partner_id].discard(websocket)
                if not self.partner_connections[partner_id]:
                    del self.partner_connections[partner_id]
            logger.info(f"🤝 Partner {partner_id} disconnected from WebSocket")

        # Remove metadata
        self.connection_metadata.pop(websocket, None)

    async def broadcast_to_admins(self, message: Dict[str, Any]):
        """Broadcast a message to all connected admin users."""
        if not self.admin_connections:
            return

        message["timestamp"] = datetime.now(timezone.utc).isoformat()

        disconnected = []
        for websocket in self.admin_connections.copy():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send message to admin websocket: {e}")
                disconnected.append(websocket)

        # Clean up disconnected connections
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def send_to_tenant(self, tenant_id: str, message: Dict[str, Any]):
        """Send a message to all connections for a specific tenant."""
        if tenant_id not in self.tenant_connections:
            return

        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        message["tenant_id"] = tenant_id

        disconnected = []
        for websocket in self.tenant_connections[tenant_id].copy():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(
                    f"Failed to send message to tenant {tenant_id} websocket: {e}"
                )
                disconnected.append(websocket)

        # Clean up disconnected connections
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def send_to_partner(self, partner_id: str, message: Dict[str, Any]):
        """Send a message to all connections for a specific partner."""
        if partner_id not in self.partner_connections:
            return

        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        message["partner_id"] = partner_id

        disconnected = []
        for websocket in self.partner_connections[partner_id].copy():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(
                    f"Failed to send message to partner {partner_id} websocket: {e}"
                )
                disconnected.append(websocket)

        # Clean up disconnected connections
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def broadcast_deployment_update(
        self, tenant_id: str, deployment_status: Dict[str, Any]
    ):
        """Broadcast deployment status update to tenant and admins."""
        message = {
            "type": "deployment_update",
            "tenant_id": tenant_id,
            "deployment_status": deployment_status,
        }

        # Send to specific tenant
        await self.send_to_tenant(tenant_id, message)

        # Send to all admins for monitoring
        await self.broadcast_to_admins(message)

    async def broadcast_billing_update(
        self, tenant_id: str, billing_event: Dict[str, Any]
    ):
        """Broadcast billing event to tenant and admins."""
        message = {
            "type": "billing_update",
            "tenant_id": tenant_id,
            "billing_event": billing_event,
        }

        # Send to specific tenant
        await self.send_to_tenant(tenant_id, message)

        # Send to admins
        await self.broadcast_to_admins(message)

    async def broadcast_infrastructure_alert(self, alert: Dict[str, Any]):
        """Broadcast infrastructure alerts to admins."""
        message = {"type": "infrastructure_alert", "alert": alert}

        await self.broadcast_to_admins(message)

    async def _send_to_websocket(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to a specific websocket with error handling."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"Failed to send message to websocket: {e}")
            await self.disconnect(websocket)

    async def _monitor_connections(self):
        """Background task to monitor connection health."""
        while self._running:
            try:
                # Send ping to all connections every 30 seconds
                ping_message = {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                # Ping admin connections
                disconnected_admins = []
                for websocket in self.admin_connections.copy():
                    try:
                        await websocket.send_text(json.dumps(ping_message))
                        # Update last ping time
                        if websocket in self.connection_metadata:
                            self.connection_metadata[websocket][
                                "last_ping"
                            ] = datetime.now(timezone.utc)
                    except Exception:
                        disconnected_admins.append(websocket)

                # Clean up disconnected admin connections
                for websocket in disconnected_admins:
                    await self.disconnect(websocket)

                # Ping tenant connections
                for tenant_id in list(self.tenant_connections.keys()):
                    disconnected_tenants = []
                    for websocket in self.tenant_connections[tenant_id].copy():
                        try:
                            await websocket.send_text(json.dumps(ping_message))
                            if websocket in self.connection_metadata:
                                self.connection_metadata[websocket][
                                    "last_ping"
                                ] = datetime.now(timezone.utc)
                        except Exception:
                            disconnected_tenants.append(websocket)

                    # Clean up disconnected tenant connections
                    for websocket in disconnected_tenants:
                        await self.disconnect(websocket)

                # Ping partner connections
                for partner_id in list(self.partner_connections.keys()):
                    disconnected_partners = []
                    for websocket in self.partner_connections[partner_id].copy():
                        try:
                            await websocket.send_text(json.dumps(ping_message))
                            if websocket in self.connection_metadata:
                                self.connection_metadata[websocket][
                                    "last_ping"
                                ] = datetime.now(timezone.utc)
                        except Exception:
                            disconnected_partners.append(websocket)

                    # Clean up disconnected partner connections
                    for websocket in disconnected_partners:
                        await self.disconnect(websocket)

                await asyncio.sleep(30)  # Ping every 30 seconds

            except Exception as e:
                logger.error(f"Error in WebSocket connection monitor: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying

    async def _close_all_connections(self):
        """Close all WebSocket connections."""
        all_websockets = set()

        # Collect all websockets
        all_websockets.update(self.admin_connections)

        for tenant_websockets in self.tenant_connections.values():
            all_websockets.update(tenant_websockets)

        for partner_websockets in self.partner_connections.values():
            all_websockets.update(partner_websockets)

        # Close all connections
        for websocket in all_websockets:
            try:
                await websocket.close(code=1001, reason="Server shutdown")
            except Exception as e:
                logger.warning(f"Error closing websocket: {e}")

        # Clear all connection stores
        self.admin_connections.clear()
        self.tenant_connections.clear()
        self.partner_connections.clear()
        self.connection_metadata.clear()

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections."""
        return {
            "admin_connections": len(self.admin_connections),
            "tenant_connections": sum(
                len(conns) for conns in self.tenant_connections.values()
            ),
            "partner_connections": sum(
                len(conns) for conns in self.partner_connections.values()
            ),
            "active_tenants": len(self.tenant_connections),
            "active_partners": len(self.partner_connections),
            "total_connections": (
                len(self.admin_connections)
                + sum(len(conns) for conns in self.tenant_connections.values())
                + sum(len(conns) for conns in self.partner_connections.values())
            ),
        }


# Global instance
websocket_manager = ManagementWebSocketManager()
