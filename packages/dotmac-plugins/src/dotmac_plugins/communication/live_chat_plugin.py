"""
Live Chat Plugin - Real-time Customer Support
Leverages existing DotMac plugin architecture and WebSocket infrastructure
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

from dotmac_plugins.core.plugin_base import BasePlugin
from dotmac_shared.core.logging import get_logger
from dotmac_shared.tasks.notifications import NotificationChannel, NotificationChannelProvider

logger = get_logger(__name__)
Base = declarative_base()


class ChatStatus(str, Enum):
    """Chat session status."""

    ACTIVE = "active"
    WAITING = "waiting"
    ENDED = "ended"
    ABANDONED = "abandoned"


class MessageType(str, Enum):
    """Chat message types."""

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"
    TYPING = "typing"
    AGENT_JOIN = "agent_join"
    AGENT_LEAVE = "agent_leave"


class AgentStatus(str, Enum):
    """Agent availability status."""

    ONLINE = "online"
    BUSY = "busy"
    AWAY = "away"
    OFFLINE = "offline"


class ChatSession(Base):
    """Chat session model."""

    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, nullable=False, index=True)

    # Session info
    session_id = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, default=ChatStatus.WAITING, nullable=False, index=True)

    # Customer info
    customer_id = Column(String, nullable=True, index=True)
    customer_name = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    visitor_id = Column(String, nullable=True, index=True)  # Anonymous visitors

    # Agent assignment
    assigned_agent_id = Column(String, nullable=True, index=True)
    assigned_agent_name = Column(String, nullable=True)
    queue_id = Column(String, nullable=True, index=True)

    # Session metadata
    initial_message = Column(Text, nullable=True)
    page_url = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    referrer = Column(String, nullable=True)

    # Timing
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)  # When agent joined
    ended_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Metrics
    wait_time_seconds = Column(Integer, default=0)
    session_duration_seconds = Column(Integer, default=0)
    message_count = Column(Integer, default=0)

    # Feedback
    customer_rating = Column(Integer, nullable=True)  # 1-5 rating
    customer_feedback = Column(Text, nullable=True)

    # Related ticket
    ticket_id = Column(String, nullable=True, index=True)

    # Additional data
    session_metadata = Column(JSON, default=dict)

    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Chat message model."""

    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Message content
    message_type = Column(String, default=MessageType.TEXT, nullable=False)
    content = Column(Text, nullable=False)
    content_html = Column(Text, nullable=True)  # Rendered HTML if applicable

    # Sender info
    sender_type = Column(String, nullable=False)  # customer, agent, system
    sender_id = Column(String, nullable=True)
    sender_name = Column(String, nullable=False)

    # Message metadata
    is_internal = Column(Boolean, default=False)  # Internal agent notes
    file_attachments = Column(JSON, default=list)

    # Timestamps
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    # Additional data
    session_metadata = Column(JSON, default=dict)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")


class AgentStatusModel(Base):
    """Agent availability and status tracking."""

    __tablename__ = "chat_agent_status"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    agent_id = Column(String, unique=True, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Status info
    status = Column(String, default=AgentStatus.OFFLINE, nullable=False)
    status_message = Column(String, nullable=True)

    # Capacity management
    max_concurrent_chats = Column(Integer, default=3)
    current_chat_count = Column(Integer, default=0)

    # Skills and queues
    skills = Column(JSON, default=list)
    queue_memberships = Column(JSON, default=list)

    # Timestamps
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    status_changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Session info
    websocket_connection_id = Column(String, nullable=True)

    # Metadata
    session_metadata = Column(JSON, default=dict)


# Pydantic Models


class ChatSessionCreate(BaseModel):
    """Create chat session request."""

    model_config = ConfigDict(from_attributes=True)

    customer_name: Optional[str] = Field(None, max_length=100)
    customer_email: Optional[str] = Field(None, max_length=255)
    initial_message: Optional[str] = Field(None, max_length=5000)
    page_url: Optional[str] = Field(None, max_length=500)
    user_agent: Optional[str] = None
    session_metadata: dict[str, Any] = Field(default_factory=dict)


class ChatMessageCreate(BaseModel):
    """Create chat message request."""

    model_config = ConfigDict(from_attributes=True)

    content: str = Field(..., min_length=1, max_length=5000)
    message_type: MessageType = MessageType.TEXT
    file_attachments: list[str] = Field(default_factory=list, max_items=5)
    is_internal: bool = False


class ChatSessionResponse(BaseModel):
    """Chat session API response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    status: ChatStatus
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    assigned_agent_name: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    wait_time_seconds: int = 0
    session_duration_seconds: int = 0
    message_count: int = 0
    customer_rating: Optional[int] = None


class ChatMessageResponse(BaseModel):
    """Chat message API response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    message_type: MessageType
    content: str
    sender_type: str
    sender_name: str
    is_internal: bool
    sent_at: datetime
    file_attachments: list[str] = Field(default_factory=list)


class AgentStatusUpdate(BaseModel):
    """Agent status update request."""

    model_config = ConfigDict(from_attributes=True)

    status: AgentStatus
    status_message: Optional[str] = Field(None, max_length=200)
    max_concurrent_chats: Optional[int] = Field(None, ge=1, le=10)


# WebSocket Connection Manager


class ChatConnectionManager:
    """Manages WebSocket connections for live chat."""

    def __init__(self):
        # Active connections: {session_id: {websocket, user_type, user_id}}
        self.active_connections: dict[str, dict[str, Any]] = {}
        # Agent connections: {agent_id: {websocket, sessions}}
        self.agent_connections: dict[str, dict[str, Any]] = {}
        # Chat queues: {queue_id: [session_ids]}
        self.chat_queues: dict[str, list[str]] = {}

    async def connect_customer(self, websocket: WebSocket, session_id: str, customer_id: Optional[str] = None):
        """Connect customer to chat session."""
        await websocket.accept()

        self.active_connections[session_id] = {
            "websocket": websocket,
            "user_type": "customer",
            "user_id": customer_id,
            "connected_at": datetime.now(timezone.utc),
        }

        logger.info(f"Customer connected to chat session {session_id}")

        # Send welcome message
        await self.send_to_session(
            session_id,
            {
                "type": "system",
                "message": "Connected to support chat. Please wait for an agent.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def connect_agent(self, websocket: WebSocket, agent_id: str, tenant_id: str):
        """Connect agent for handling chats."""
        await websocket.accept()

        self.agent_connections[agent_id] = {
            "websocket": websocket,
            "tenant_id": tenant_id,
            "sessions": set(),
            "connected_at": datetime.now(timezone.utc),
        }

        logger.info(f"Agent {agent_id} connected")

        # Send agent status update
        await self.send_to_agent(
            agent_id, {"type": "connected", "agent_id": agent_id, "timestamp": datetime.now(timezone.utc).isoformat()}
        )

    async def disconnect_customer(self, session_id: str):
        """Disconnect customer from session."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Customer disconnected from session {session_id}")

    async def disconnect_agent(self, agent_id: str):
        """Disconnect agent."""
        if agent_id in self.agent_connections:
            # Notify all sessions this agent was handling
            agent_data = self.agent_connections[agent_id]
            for session_id in agent_data["sessions"]:
                await self.send_to_session(
                    session_id,
                    {
                        "type": "agent_disconnected",
                        "message": "Agent disconnected. Please wait while we connect you to another agent.",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

            del self.agent_connections[agent_id]
            logger.info(f"Agent {agent_id} disconnected")

    async def assign_agent_to_session(self, session_id: str, agent_id: str):
        """Assign agent to handle a session."""
        if agent_id in self.agent_connections and session_id in self.active_connections:
            self.agent_connections[agent_id]["sessions"].add(session_id)

            # Notify customer
            await self.send_to_session(
                session_id,
                {
                    "type": "agent_joined",
                    "agent_id": agent_id,
                    "message": "An agent has joined the chat.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Notify agent
            await self.send_to_agent(
                agent_id,
                {
                    "type": "session_assigned",
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.info(f"Assigned agent {agent_id} to session {session_id}")
            return True
        return False

    async def send_message_to_session(self, session_id: str, message: dict[str, Any], exclude_sender: Optional[str] = None):
        """Send message to all participants in a session."""
        # Send to customer
        if session_id in self.active_connections:
            connection = self.active_connections[session_id]
            if exclude_sender != connection["user_id"]:
                try:
                    await connection["websocket"].send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Failed to send message to customer in session {session_id}: {e}")

        # Send to assigned agents
        for agent_id, agent_data in self.agent_connections.items():
            if session_id in agent_data["sessions"] and exclude_sender != agent_id:
                try:
                    await agent_data["websocket"].send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Failed to send message to agent {agent_id}: {e}")

    async def send_to_session(self, session_id: str, message: dict[str, Any]):
        """Send system message to session."""
        await self.send_message_to_session(session_id, message)

    async def send_to_agent(self, agent_id: str, message: dict[str, Any]):
        """Send message to specific agent."""
        if agent_id in self.agent_connections:
            try:
                await self.agent_connections[agent_id]["websocket"].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to agent {agent_id}: {e}")

    def get_available_agents(self, tenant_id: str, skills: Optional[list[str]] = None) -> list[str]:
        """Get list of available agents for assignment."""
        available_agents = []

        for agent_id, agent_data in self.agent_connections.items():
            if agent_data["tenant_id"] == tenant_id:
                session_count = len(agent_data["sessions"])
                # In production, would check agent max capacity and skills
                if session_count < 3:  # Max 3 concurrent chats per agent
                    available_agents.append(agent_id)

        return available_agents


# Live Chat Plugin


class LiveChatPlugin(BasePlugin, NotificationChannelProvider):
    """Live chat plugin for real-time customer support."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        self.connection_manager = ChatConnectionManager()
        self.chat_service = None  # Will be injected

        # Plugin configuration
        self.max_wait_time_minutes = self.config.get("max_wait_time", 15)
        self.auto_close_minutes = self.config.get("auto_close_minutes", 30)
        self.enable_file_sharing = self.config.get("enable_file_sharing", True)
        self.max_file_size_mb = self.config.get("max_file_size_mb", 10)

    def get_plugin_name(self) -> str:
        return "live_chat"

    def get_plugin_version(self) -> str:
        return "1.0.0"

    def get_channel(self) -> NotificationChannel:
        return NotificationChannel.CHAT

    async def initialize(self):
        """Initialize the live chat plugin."""
        logger.info("Initializing Live Chat Plugin")

        # Start background tasks
        asyncio.create_task(self._queue_monitor())
        asyncio.create_task(self._session_cleanup())

    async def send_notification(self, request) -> bool:
        """Send chat notification (not typically used for live chat)."""
        # Live chat uses real-time WebSocket connections
        # This method could be used for offline messages
        return True

    async def validate_recipient(self, recipient: str) -> bool:
        """Validate chat recipient (session ID)."""
        return len(recipient) > 0

    async def handle_customer_websocket(self, websocket: WebSocket, session_id: str, customer_id: Optional[str] = None):
        """Handle customer WebSocket connection."""
        try:
            await self.connection_manager.connect_customer(websocket, session_id, customer_id)

            # Add customer to queue for agent assignment
            await self._add_to_queue(session_id)

            while True:
                try:
                    # Receive message from customer
                    data = await websocket.receive_text()
                    message_data = json.loads(data)

                    # Process customer message
                    await self._handle_customer_message(session_id, message_data, customer_id)

                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Invalid message format"}))
                except Exception as e:
                    logger.error(f"Error handling customer message: {e}")
                    await websocket.send_text(json.dumps({"type": "error", "message": "Message processing error"}))

        finally:
            await self.connection_manager.disconnect_customer(session_id)

    async def handle_agent_websocket(self, websocket: WebSocket, agent_id: str, tenant_id: str):
        """Handle agent WebSocket connection."""
        try:
            await self.connection_manager.connect_agent(websocket, agent_id, tenant_id)

            while True:
                try:
                    # Receive message from agent
                    data = await websocket.receive_text()
                    message_data = json.loads(data)

                    # Process agent message
                    await self._handle_agent_message(agent_id, message_data)

                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Invalid message format"}))
                except Exception as e:
                    logger.error(f"Error handling agent message: {e}")

        finally:
            await self.connection_manager.disconnect_agent(agent_id)

    async def _handle_customer_message(self, session_id: str, message_data: dict[str, Any], customer_id: Optional[str] = None):
        """Process message from customer."""
        message_type = message_data.get("type", "message")

        if message_type == "message":
            content = message_data.get("content", "")
            if content:
                # Save message to database
                if self.chat_service:
                    await self.chat_service.add_message(
                        session_id=session_id,
                        content=content,
                        sender_type="customer",
                        sender_id=customer_id,
                        sender_name=message_data.get("sender_name", "Customer"),
                    )

                # Broadcast to session participants
                await self.connection_manager.send_message_to_session(
                    session_id,
                    {
                        "type": "message",
                        "content": content,
                        "sender_type": "customer",
                        "sender_name": message_data.get("sender_name", "Customer"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    exclude_sender=customer_id,
                )

        elif message_type == "typing":
            # Broadcast typing indicator
            await self.connection_manager.send_message_to_session(
                session_id,
                {"type": "typing", "sender_type": "customer", "timestamp": datetime.now(timezone.utc).isoformat()},
                exclude_sender=customer_id,
            )

    async def _handle_agent_message(self, agent_id: str, message_data: dict[str, Any]):
        """Process message from agent."""
        message_type = message_data.get("type", "message")
        session_id = message_data.get("session_id")

        if not session_id:
            return

        if message_type == "message":
            content = message_data.get("content", "")
            if content:
                # Save message to database
                if self.chat_service:
                    await self.chat_service.add_message(
                        session_id=session_id,
                        content=content,
                        sender_type="agent",
                        sender_id=agent_id,
                        sender_name=message_data.get("sender_name", "Agent"),
                    )

                # Broadcast to session participants
                await self.connection_manager.send_message_to_session(
                    session_id,
                    {
                        "type": "message",
                        "content": content,
                        "sender_type": "agent",
                        "sender_name": message_data.get("sender_name", "Agent"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    exclude_sender=agent_id,
                )

        elif message_type == "typing":
            # Broadcast typing indicator
            await self.connection_manager.send_message_to_session(
                session_id,
                {"type": "typing", "sender_type": "agent", "timestamp": datetime.now(timezone.utc).isoformat()},
                exclude_sender=agent_id,
            )

        elif message_type == "end_chat":
            # End chat session
            if self.chat_service:
                await self.chat_service.end_session(session_id, agent_id)

    async def _add_to_queue(self, session_id: str, queue_id: str = "general"):
        """Add session to queue for agent assignment."""
        if queue_id not in self.connection_manager.chat_queues:
            self.connection_manager.chat_queues[queue_id] = []

        self.connection_manager.chat_queues[queue_id].append(session_id)

        # Try to assign agent immediately
        await self._try_assign_agent(session_id, queue_id)

    async def _try_assign_agent(self, session_id: str, queue_id: str = "general"):
        """Try to assign an available agent to the session."""
        # Get available agents
        available_agents = self.connection_manager.get_available_agents(
            "default_tenant"
        )  # In production, get from session

        if available_agents:
            # Assign first available agent
            agent_id = available_agents[0]
            success = await self.connection_manager.assign_agent_to_session(session_id, agent_id)

            if success:
                # Remove from queue
                if queue_id in self.connection_manager.chat_queues:
                    try:
                        self.connection_manager.chat_queues[queue_id].remove(session_id)
                    except ValueError:
                        pass

                # Update session status in database
                if self.chat_service:
                    await self.chat_service.assign_agent(session_id, agent_id)

    async def _queue_monitor(self):
        """Monitor queues and assign agents to waiting sessions."""
        while True:
            try:
                for queue_id, session_ids in self.connection_manager.chat_queues.items():
                    for session_id in session_ids[:]:  # Copy list to avoid modification during iteration
                        await self._try_assign_agent(session_id, queue_id)

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"Error in queue monitor: {e}")
                await asyncio.sleep(5)

    async def _session_cleanup(self):
        """Clean up abandoned or old sessions."""
        while True:
            try:
                # Clean up sessions older than auto_close_minutes with no activity
                datetime.now(timezone.utc) - timedelta(minutes=self.auto_close_minutes)

                # In production, would query database for inactive sessions
                # and close them automatically

                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(300)
