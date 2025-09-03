"""
Tests for WebSocket session management.
"""

import asyncio
import json
import time
import pytest
from unittest.mock import Mock, AsyncMock

from dotmac.websockets.core.session import (
    WebSocketSession,
    SessionManager,
    SessionState,
    SessionMetadata,
)
from dotmac.websockets.core.config import WebSocketConfig, create_development_config


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages_sent = []
        self.closed = False
        self.close_code = None
        self.close_reason = None
    
    async def send(self, message):
        if self.closed:
            raise Exception("WebSocket closed")
        self.messages_sent.append(message)
    
    async def close(self, code=1000, reason=""):
        self.closed = True
        self.close_code = code
        self.close_reason = reason
    
    async def ping(self):
        if self.closed:
            raise Exception("WebSocket closed")
        return Mock()


class TestWebSocketSession:
    """Test WebSocket session functionality."""
    
    def test_session_initialization(self):
        """Test session initialization."""
        websocket = MockWebSocket()
        session = WebSocketSession(websocket, "test-session-1")
        
        assert session.session_id == "test-session-1"
        assert session.websocket == websocket
        assert session.state == SessionState.CONNECTING
        assert not session.is_authenticated
        assert session.user_id is None
        assert session.tenant_id is None
    
    def test_session_metadata(self):
        """Test session metadata handling."""
        websocket = MockWebSocket()
        metadata = SessionMetadata(
            session_id="test-session-1",
            user_id="user123",
            tenant_id="tenant456",
            ip_address="192.168.1.1"
        )
        
        session = WebSocketSession(websocket, "test-session-1", metadata)
        
        assert session.metadata.user_id == "user123"
        assert session.metadata.tenant_id == "tenant456" 
        assert session.metadata.ip_address == "192.168.1.1"
    
    def test_user_info_setting(self):
        """Test setting user information."""
        websocket = MockWebSocket()
        session = WebSocketSession(websocket, "test-session-1")
        
        # Initially not authenticated
        assert not session.is_authenticated
        assert session.user_id is None
        
        # Set user info
        session.set_user_info("user123", "tenant456", role="admin")
        
        # Should now be authenticated
        assert session.is_authenticated
        assert session.user_id == "user123"
        assert session.tenant_id == "tenant456"
        assert session.state == SessionState.AUTHENTICATED
        assert session.metadata.custom_data["role"] == "admin"
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending messages."""
        websocket = MockWebSocket()
        session = WebSocketSession(websocket, "test-session-1")
        session.state = SessionState.CONNECTED
        
        # Send a message
        success = await session.send_message("test_type", {"data": "test"})
        
        assert success
        assert len(websocket.messages_sent) == 1
        
        # Parse sent message
        message = json.loads(websocket.messages_sent[0])
        assert message["type"] == "test_type"
        assert message["data"]["data"] == "test"
        assert "timestamp" in message
        
        # Check statistics
        assert session.metadata.messages_sent == 1
        assert session.metadata.bytes_sent > 0
    
    @pytest.mark.asyncio
    async def test_send_raw_data(self):
        """Test sending raw data."""
        websocket = MockWebSocket()
        session = WebSocketSession(websocket, "test-session-1")
        session.state = SessionState.CONNECTED
        
        # Send raw data
        success = await session.send_raw("Hello, WebSocket!")
        
        assert success
        assert len(websocket.messages_sent) == 1
        assert websocket.messages_sent[0] == "Hello, WebSocket!"
        
        # Check statistics
        assert session.metadata.messages_sent == 1
        assert session.metadata.bytes_sent == len("Hello, WebSocket!")
    
    @pytest.mark.asyncio
    async def test_send_message_closed_session(self):
        """Test sending message to closed session."""
        websocket = MockWebSocket()
        session = WebSocketSession(websocket, "test-session-1")
        session._closed = True
        
        # Try to send message
        success = await session.send_message("test_type", {"data": "test"})
        
        assert not success
        assert len(websocket.messages_sent) == 0
    
    @pytest.mark.asyncio
    async def test_handle_message(self):
        """Test handling incoming messages."""
        websocket = MockWebSocket()
        session = WebSocketSession(websocket, "test-session-1")
        
        handler_calls = []
        
        async def test_handler(message_type, data):
            handler_calls.append((message_type, data))
        
        session.add_message_handler(test_handler)
        
        # Handle JSON message
        await session.handle_message(json.dumps({
            "type": "test_message",
            "data": {"content": "Hello"}
        }))
        
        assert len(handler_calls) == 1
        assert handler_calls[0][0] == "test_message"
        assert handler_calls[0][1]["content"] == "Hello"
        
        # Check statistics
        assert session.metadata.messages_received == 1
        assert session.metadata.bytes_received > 0
        assert session.metadata.last_activity > 0
    
    @pytest.mark.asyncio
    async def test_handle_raw_message(self):
        """Test handling raw (non-JSON) messages."""
        websocket = MockWebSocket()
        session = WebSocketSession(websocket, "test-session-1")
        
        handler_calls = []
        
        async def test_handler(message_type, data):
            handler_calls.append((message_type, data))
        
        session.add_message_handler(test_handler)
        
        # Handle raw message
        await session.handle_message("raw message content")
        
        assert len(handler_calls) == 1
        assert handler_calls[0][0] == "raw"
        assert handler_calls[0][1] == "raw message content"
    
    @pytest.mark.asyncio
    async def test_ping_functionality(self):
        """Test ping functionality."""
        websocket = MockWebSocket()
        session = WebSocketSession(websocket, "test-session-1")
        
        # Ping should succeed
        success = await session.ping()
        assert success
        assert session.metadata.last_ping is not None
    
    @pytest.mark.asyncio
    async def test_ping_task(self):
        """Test periodic ping task."""
        websocket = MockWebSocket()
        session = WebSocketSession(websocket, "test-session-1")
        session.state = SessionState.CONNECTED
        
        # Start ping task with very short interval
        session.start_ping_task(interval=0.1, timeout=1)
        
        # Wait a bit
        await asyncio.sleep(0.2)
        
        # Should have pinged
        assert session.metadata.last_ping is not None
        
        # Close session to stop ping task
        await session.close()
    
    @pytest.mark.asyncio
    async def test_session_close(self):
        """Test session closing."""
        websocket = MockWebSocket()
        session = WebSocketSession(websocket, "test-session-1")
        session.state = SessionState.CONNECTED
        
        disconnect_called = False
        
        async def disconnect_handler():
            nonlocal disconnect_called
            disconnect_called = True
        
        session.add_disconnect_handler(disconnect_handler)
        
        # Close session
        await session.close(1000, "Test close")
        
        assert session._closed
        assert session.state == SessionState.DISCONNECTED
        assert websocket.closed
        assert websocket.close_code == 1000
        assert websocket.close_reason == "Test close"
        assert disconnect_called
    
    def test_session_serialization(self):
        """Test session serialization."""
        websocket = MockWebSocket()
        metadata = SessionMetadata(
            session_id="test-session-1",
            user_id="user123",
            tenant_id="tenant456",
            ip_address="192.168.1.1"
        )
        
        session = WebSocketSession(websocket, "test-session-1", metadata)
        session.set_user_info("user123", "tenant456")
        
        # Convert to dict
        session_dict = session.to_dict()
        
        assert session_dict["session_id"] == "test-session-1"
        assert session_dict["state"] == SessionState.AUTHENTICATED.value
        assert session_dict["metadata"]["user_id"] == "user123"
        assert session_dict["metadata"]["tenant_id"] == "tenant456"
        assert session_dict["metadata"]["ip_address"] == "192.168.1.1"


class TestSessionManager:
    """Test session manager functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return create_development_config()
    
    @pytest.fixture
    def session_manager(self, config):
        """Create session manager."""
        return SessionManager(config)
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """Test session creation."""
        websocket = MockWebSocket()
        session = await session_manager.create_session(websocket)
        
        assert session is not None
        assert session.session_id is not None
        assert session.state == SessionState.CONNECTED
        assert session_manager.get_session(session.session_id) == session
    
    @pytest.mark.asyncio
    async def test_create_session_with_id(self, session_manager):
        """Test session creation with specific ID."""
        websocket = MockWebSocket()
        session = await session_manager.create_session(websocket, "custom-id")
        
        assert session.session_id == "custom-id"
        assert session_manager.get_session("custom-id") == session
    
    @pytest.mark.asyncio
    async def test_create_session_with_metadata(self, session_manager):
        """Test session creation with metadata."""
        websocket = MockWebSocket()
        metadata = SessionMetadata(
            session_id="test-session",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        session = await session_manager.create_session(websocket, "test-session", metadata)
        
        assert session.metadata.ip_address == "192.168.1.1"
        assert session.metadata.user_agent == "Test Agent"
    
    @pytest.mark.asyncio
    async def test_remove_session(self, session_manager):
        """Test session removal."""
        websocket = MockWebSocket()
        session = await session_manager.create_session(websocket)
        session_id = session.session_id
        
        # Session should exist
        assert session_manager.get_session(session_id) is not None
        
        # Remove session
        removed = await session_manager.remove_session(session_id)
        
        assert removed
        assert session_manager.get_session(session_id) is None
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_session(self, session_manager):
        """Test removing non-existent session."""
        removed = await session_manager.remove_session("nonexistent")
        assert not removed
    
    @pytest.mark.asyncio
    async def test_user_session_tracking(self, session_manager):
        """Test user session tracking."""
        # Create sessions for user
        websocket1 = MockWebSocket()
        session1 = await session_manager.create_session(websocket1)
        
        websocket2 = MockWebSocket()
        session2 = await session_manager.create_session(websocket2)
        
        # Update with user info
        session_manager.update_session_user_info(session1.session_id, "user123", "tenant456")
        session_manager.update_session_user_info(session2.session_id, "user123", "tenant456")
        
        # Get user sessions
        user_sessions = session_manager.get_user_sessions("user123")
        assert len(user_sessions) == 2
        assert session1 in user_sessions
        assert session2 in user_sessions
        
        # Remove one session
        await session_manager.remove_session(session1.session_id)
        
        user_sessions = session_manager.get_user_sessions("user123")
        assert len(user_sessions) == 1
        assert session2 in user_sessions
    
    @pytest.mark.asyncio
    async def test_tenant_session_tracking(self, session_manager):
        """Test tenant session tracking."""
        # Create sessions for tenant
        websocket1 = MockWebSocket()
        session1 = await session_manager.create_session(websocket1)
        
        websocket2 = MockWebSocket()
        session2 = await session_manager.create_session(websocket2)
        
        # Update with tenant info
        session_manager.update_session_user_info(session1.session_id, "user1", "tenant123")
        session_manager.update_session_user_info(session2.session_id, "user2", "tenant123")
        
        # Get tenant sessions
        tenant_sessions = session_manager.get_tenant_sessions("tenant123")
        assert len(tenant_sessions) == 2
        assert session1 in tenant_sessions
        assert session2 in tenant_sessions
    
    @pytest.mark.asyncio
    async def test_broadcast_to_user(self, session_manager):
        """Test broadcasting to user sessions."""
        # Create sessions for user
        websocket1 = MockWebSocket()
        session1 = await session_manager.create_session(websocket1)
        
        websocket2 = MockWebSocket()
        session2 = await session_manager.create_session(websocket2)
        
        # Update with user info
        session_manager.update_session_user_info(session1.session_id, "user123", "tenant456")
        session_manager.update_session_user_info(session2.session_id, "user123", "tenant456")
        
        # Broadcast to user
        sent_count = await session_manager.broadcast_to_user(
            "user123", 
            "broadcast_message", 
            {"content": "Hello user!"}
        )
        
        assert sent_count == 2
        
        # Check messages were sent
        assert len(websocket1.messages_sent) == 1
        assert len(websocket2.messages_sent) == 1
        
        # Parse messages
        message1 = json.loads(websocket1.messages_sent[0])
        assert message1["type"] == "broadcast_message"
        assert message1["data"]["content"] == "Hello user!"
    
    @pytest.mark.asyncio
    async def test_broadcast_to_tenant(self, session_manager):
        """Test broadcasting to tenant sessions."""
        # Create sessions for tenant
        websocket1 = MockWebSocket()
        session1 = await session_manager.create_session(websocket1)
        
        websocket2 = MockWebSocket()
        session2 = await session_manager.create_session(websocket2)
        
        # Update with tenant info
        session_manager.update_session_user_info(session1.session_id, "user1", "tenant123")
        session_manager.update_session_user_info(session2.session_id, "user2", "tenant123")
        
        # Broadcast to tenant
        sent_count = await session_manager.broadcast_to_tenant(
            "tenant123", 
            "tenant_message", 
            {"announcement": "Maintenance tonight"}
        )
        
        assert sent_count == 2
        
        # Check messages were sent
        assert len(websocket1.messages_sent) == 1
        assert len(websocket2.messages_sent) == 1
    
    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, session_manager):
        """Test broadcasting to all sessions."""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            websocket = MockWebSocket()
            session = await session_manager.create_session(websocket)
            sessions.append((session, websocket))
        
        # Broadcast to all
        sent_count = await session_manager.broadcast_to_all(
            "global_message", 
            {"content": "Server maintenance"}
        )
        
        assert sent_count == 3
        
        # Check all got messages
        for session, websocket in sessions:
            assert len(websocket.messages_sent) == 1
            message = json.loads(websocket.messages_sent[0])
            assert message["type"] == "global_message"
    
    @pytest.mark.asyncio
    async def test_session_cleanup_task(self, session_manager):
        """Test session cleanup task."""
        # Start cleanup task
        session_manager.start_cleanup_task()
        
        # Create an expired session by manipulating timestamps
        websocket = MockWebSocket()
        session = await session_manager.create_session(websocket)
        
        # Make session appear expired
        session.metadata.last_activity = time.time() - 1000  # 1000 seconds ago
        session.metadata.connected_at = time.time() - 2000   # 2000 seconds ago
        
        # Manually run cleanup
        await session_manager._cleanup_expired_sessions()
        
        # Session should be removed
        assert session_manager.get_session(session.session_id) is None
        
        # Stop cleanup task
        session_manager.stop_cleanup_task()
    
    def test_statistics(self, session_manager):
        """Test statistics collection."""
        stats = session_manager.get_stats()
        
        assert "total_sessions" in stats
        assert "authenticated_sessions" in stats
        assert "anonymous_sessions" in stats
        assert "unique_users" in stats
        assert "unique_tenants" in stats
        assert "sessions_by_state" in stats
        
        # Initially no sessions
        assert stats["total_sessions"] == 0
        assert stats["authenticated_sessions"] == 0
        assert stats["anonymous_sessions"] == 0
    
    @pytest.mark.asyncio
    async def test_close_all_sessions(self, session_manager):
        """Test closing all sessions."""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            websocket = MockWebSocket()
            session = await session_manager.create_session(websocket)
            sessions.append(session)
        
        assert len(session_manager.get_all_sessions()) == 3
        
        # Close all sessions
        await session_manager.close_all_sessions()
        
        # All sessions should be closed
        assert len(session_manager.get_all_sessions()) == 0
        
        # All WebSockets should be closed
        for session in sessions:
            assert session._closed


if __name__ == "__main__":
    pytest.main([__file__])