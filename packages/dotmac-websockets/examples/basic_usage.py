#!/usr/bin/env python3
"""
Basic usage example for dotmac-websockets package.

This example demonstrates:
- Creating a WebSocket gateway
- Handling connections and messages
- Channel subscriptions and broadcasting
- Authentication integration
- Health monitoring
"""

import asyncio
import json
import logging
from dotmac.websockets import (
    # Core components
    WebSocketGateway,
    create_development_config,
    
    # Observability
    create_default_hooks,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main example function."""
    print("🚀 DotMac WebSocket Gateway - Basic Usage Example")
    print("=" * 60)
    
    # 1. Create configuration
    print("\n1. Creating WebSocket configuration...")
    config = create_development_config(
        host="0.0.0.0",
        port=8765,
        path="/ws"
    )
    print(f"   ✅ Configuration created - Server will run on ws://localhost:8765/ws")
    
    # 2. Create gateway
    print("\n2. Creating WebSocket gateway...")
    gateway = WebSocketGateway(config)
    
    # 3. Set up observability
    print("\n3. Setting up observability...")
    hooks = create_default_hooks()
    gateway.set_observability_hooks(hooks)
    print("   ✅ Observability hooks configured")
    
    # 4. Add custom message handlers
    print("\n4. Adding custom message handlers...")
    
    async def handle_echo(session, data):
        """Echo message back to sender."""
        await session.send_message("echo_response", {
            "original": data,
            "timestamp": asyncio.get_event_loop().time(),
            "session_id": session.session_id
        })
        logger.info(f"Echo message from session {session.session_id}")
    
    async def handle_join_room(session, data):
        """Handle room join requests."""
        room_name = data.get("room") if isinstance(data, dict) else None
        if not room_name:
            await session.send_message("error", {"message": "Room name required"})
            return
        
        # Subscribe to channel (room)
        success = await gateway.channel_manager.subscribe_session(session, room_name)
        if success:
            await session.send_message("joined_room", {"room": room_name})
            
            # Notify others in the room
            await gateway.broadcast_to_channel(
                room_name,
                "user_joined",
                {
                    "user_id": session.user_id or session.session_id,
                    "room": room_name
                },
                exclude_session=session.session_id
            )
            logger.info(f"Session {session.session_id} joined room {room_name}")
        else:
            await session.send_message("error", {"message": "Failed to join room"})
    
    async def handle_room_message(session, data):
        """Handle messages sent to rooms."""
        room_name = data.get("room") if isinstance(data, dict) else None
        message = data.get("message") if isinstance(data, dict) else None
        
        if not room_name or not message:
            await session.send_message("error", {"message": "Room and message required"})
            return
        
        # Broadcast to room
        delivered = await gateway.broadcast_to_channel(
            room_name,
            "room_message",
            {
                "room": room_name,
                "message": message,
                "sender": session.user_id or session.session_id,
                "timestamp": asyncio.get_event_loop().time()
            }
        )
        
        await session.send_message("message_sent", {
            "room": room_name,
            "delivered_to": delivered
        })
    
    # Register custom handlers
    gateway.add_message_handler("echo", handle_echo)
    gateway.add_message_handler("join_room", handle_join_room)
    gateway.add_message_handler("room_message", handle_room_message)
    
    print("   ✅ Custom message handlers added:")
    print("      - echo: Echo messages back")
    print("      - join_room: Join a chat room")
    print("      - room_message: Send message to room")
    
    # 5. Add connection handlers
    print("\n5. Adding connection handlers...")
    
    async def on_connect(session):
        """Called when a client connects."""
        await session.send_message("welcome", {
            "message": "Welcome to DotMac WebSocket Gateway!",
            "session_id": session.session_id,
            "available_commands": [
                "ping - Test connection",
                "echo - Echo messages back", 
                "join_room - Join a chat room",
                "room_message - Send message to room",
                "subscribe - Subscribe to channels",
                "auth - Authenticate (optional)"
            ]
        })
        logger.info(f"New connection: {session.session_id}")
    
    async def on_disconnect(session):
        """Called when a client disconnects."""
        logger.info(f"Disconnected: {session.session_id}")
    
    gateway.add_connection_handler(on_connect)
    gateway.add_disconnection_handler(on_disconnect)
    
    print("   ✅ Connection handlers added")
    
    # 6. Start the gateway
    print("\n6. Starting WebSocket gateway...")
    await gateway.start_server()
    
    print(f"   🟢 WebSocket server started on ws://localhost:8765/ws")
    print("\n📋 Test Commands:")
    print("   You can test the WebSocket server using a WebSocket client:")
    print("   1. Connect to: ws://localhost:8765/ws")
    print("   2. Send messages in JSON format:")
    print('      {"type": "ping"}')
    print('      {"type": "echo", "data": "Hello WebSocket!"}')
    print('      {"type": "join_room", "data": {"room": "general"}}')
    print('      {"type": "room_message", "data": {"room": "general", "message": "Hello room!"}}')
    
    print("\n💡 Features demonstrated:")
    print("   - Basic WebSocket connection handling")
    print("   - Custom message routing")
    print("   - Channel/room subscriptions")
    print("   - Broadcasting to channels")
    print("   - Session management")
    print("   - Observability integration")
    
    # 7. Run health checks and show stats
    print("\n7. Running health checks...")
    health = await gateway.health_check()
    print(f"   📊 Gateway Health: {health['status']}")
    
    stats = gateway.get_stats()
    print(f"   📈 Current Stats:")
    print(f"      - Sessions: {stats['sessions']['total_sessions']}")
    print(f"      - Channels: {stats['channels']['total_channels']}")
    print(f"      - Server running: {stats['server']['running']}")
    
    # 8. Keep server running
    print("\n8. Server is running... Press Ctrl+C to stop")
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(10)
            
            # Show periodic stats
            current_stats = gateway.get_stats()
            if current_stats['sessions']['total_sessions'] > 0:
                print(f"   📊 Active sessions: {current_stats['sessions']['total_sessions']}")
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        
    finally:
        # 9. Clean shutdown
        await gateway.stop_server()
        print("   ✅ Server stopped gracefully")
    
    print("\n🎉 Example completed successfully!")
    print("\nNext steps:")
    print("- Try the authentication examples")
    print("- Explore Redis scaling with multiple instances")
    print("- Add FastAPI integration for REST endpoints")
    print("- Set up production monitoring")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample interrupted by user")
    except Exception as e:
        print(f"Example failed: {e}")
        import traceback
        traceback.print_exc()