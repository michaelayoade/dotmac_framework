#!/usr/bin/env python3
"""
Simple validation for WebSocket service integration.

Validates that WebSocket integration components can be imported
and basic functionality works.
"""

import asyncio
import sys

# Add path for imports
sys.path.insert(0, "/home/dotmac_framework/src")


def test_auth_integration_imports():
    """Test WebSocket auth integration imports."""

    try:
        from dotmac_shared.websockets.auth_integration import (
            WebSocketAuthContext,
            WebSocketAuthManager,
        )

        return True
    except ImportError as e:
        return False


def test_cache_integration_imports():
    """Test WebSocket cache integration imports."""

    try:
        from dotmac_shared.websockets.cache_integration import (
            CachedMessage,
            CacheServiceWebSocketStore,
            ConnectionState,
        )

        return True
    except ImportError as e:
        return False


def test_basic_functionality():
    """Test basic WebSocket integration functionality."""

    try:
        from unittest.mock import Mock

        from dotmac_shared.websockets.cache_integration import (
            CacheServiceWebSocketStore,
        )

        # Create mock cache
        cache = Mock()

        # Create WebSocket cache store
        ws_cache = CacheServiceWebSocketStore(cache, server_id="test-server")

        # Test key generation
        message_key = ws_cache._message_key("msg-123")
        assert "ws_messages:msg-123" == message_key

        connection_key = ws_cache._connection_key("conn-456")
        assert "ws_connections:conn-456" == connection_key

        room_key = ws_cache._room_key("room-789")
        assert "ws_rooms:room-789" == room_key

        return True

    except Exception as e:
        return False


def main():
    """Run validation tests."""
    success = True

    # Test imports
    if not test_auth_integration_imports():
        success = False

    if not test_cache_integration_imports():
        success = False

    # Test basic functionality
    if not test_basic_functionality():
        success = False

    if success:

        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
