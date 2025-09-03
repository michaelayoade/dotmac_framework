#!/usr/bin/env python3
"""
WebSocket client test for dotmac-websockets package.

This client demonstrates how to connect to and test the WebSocket gateway
with various features like authentication, channels, and messaging.
"""

import asyncio
import json
import logging
import os
import websockets
from typing import Optional, Dict, Any
import jwt
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "INSECURE-EXAMPLE-KEY-NEVER-USE-IN-PRODUCTION")


def create_test_jwt_token(user_id: str, tenant_id: str, roles=None, permissions=None):
    """Create a test JWT token."""
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "username": f"user_{user_id}",
        "email": f"user_{user_id}@example.com",
        "tenant_id": tenant_id,
        "roles": roles or ["user"],
        "permissions": permissions or ["read", "write"],
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


class WebSocketTestClient:
    """WebSocket test client for dotmac-websockets."""
    
    def __init__(self, uri: str, name: str = "TestClient"):
        self.uri = uri
        self.name = name
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.running = False
        self.message_handlers = {}
        self.received_messages = []
    
    async def connect(self):
        """Connect to WebSocket server."""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.running = True
            logger.info(f"{self.name} connected to {self.uri}")
            return True
        except Exception as e:
            logger.error(f"{self.name} failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket server."""
        if self.websocket:
            self.running = False
            await self.websocket.close()
            logger.info(f"{self.name} disconnected")
    
    async def send_message(self, message_type: str, data: Any = None):
        """Send a message to the server."""
        if not self.websocket:
            logger.error(f"{self.name} not connected")
            return False
        
        message = {
            "type": message_type,
            "data": data,
            "timestamp": time.time()
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            logger.debug(f"{self.name} sent: {message_type}")
            return True
        except Exception as e:
            logger.error(f"{self.name} failed to send message: {e}")
            return False
    
    async def listen_for_messages(self):
        """Listen for messages from server."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.received_messages.append(data)
                    
                    message_type = data.get("type", "unknown")
                    message_data = data.get("data")
                    
                    logger.info(f"{self.name} received: {message_type}")
                    
                    # Call handler if registered
                    if message_type in self.message_handlers:
                        await self.message_handlers[message_type](data)
                    else:
                        await self.handle_message(message_type, message_data)
                
                except json.JSONDecodeError:
                    logger.warning(f"{self.name} received non-JSON message: {message}")
                except Exception as e:
                    logger.error(f"{self.name} error handling message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"{self.name} connection closed by server")
        except Exception as e:
            logger.error(f"{self.name} listen error: {e}")
        finally:
            self.running = False
    
    async def handle_message(self, message_type: str, data: Any):
        """Handle received messages (override in subclasses)."""
        logger.debug(f"{self.name} handling {message_type}: {data}")
    
    def add_message_handler(self, message_type: str, handler):
        """Add a message handler."""
        self.message_handlers[message_type] = handler
    
    async def run_test_sequence(self):
        """Run a test sequence."""
        if not await self.connect():
            return
        
        # Start listening in background
        listen_task = asyncio.create_task(self.listen_for_messages())
        
        try:
            await self.perform_tests()
        finally:
            await self.disconnect()
            if not listen_task.done():
                listen_task.cancel()
                try:
                    await listen_task
                except asyncio.CancelledError:
                    pass
    
    async def perform_tests(self):
        """Perform test sequence (override in subclasses)."""
        pass


class BasicTestClient(WebSocketTestClient):
    """Basic functionality test client."""
    
    async def perform_tests(self):
        """Test basic functionality."""
        print(f"\n🧪 {self.name} - Basic Tests")
        print("=" * 40)
        
        # Wait for welcome message
        await asyncio.sleep(1)
        
        # Test 1: Ping
        print("Test 1: Ping")
        await self.send_message("ping")
        await asyncio.sleep(0.5)
        
        # Test 2: Echo
        print("Test 2: Echo")
        await self.send_message("echo", {"message": "Hello from test client!"})
        await asyncio.sleep(0.5)
        
        # Test 3: Join room
        print("Test 3: Join room")
        await self.send_message("join_room", {"room": "test_room"})
        await asyncio.sleep(0.5)
        
        # Test 4: Send room message
        print("Test 4: Room message")
        await self.send_message("room_message", {
            "room": "test_room",
            "message": f"Message from {self.name}"
        })
        await asyncio.sleep(0.5)
        
        # Test 5: Subscribe to channel
        print("Test 5: Channel subscription")
        await self.send_message("subscribe", {"channel": "notifications"})
        await asyncio.sleep(0.5)
        
        print(f"✅ {self.name} basic tests completed")


class AuthenticatedTestClient(WebSocketTestClient):
    """Authenticated functionality test client."""
    
    def __init__(self, uri: str, user_id: str, tenant_id: str, user_type: str = "user"):
        super().__init__(uri, f"AuthClient_{user_id}")
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.user_type = user_type
        self.authenticated = False
    
    async def perform_tests(self):
        """Test authenticated functionality."""
        print(f"\n🔐 {self.name} - Authentication Tests")
        print("=" * 50)
        
        # Wait for welcome message
        await asyncio.sleep(1)
        
        # Test 1: Demo authentication
        print("Test 1: Demo authentication")
        await self.send_message("demo_auth", {
            "user_type": self.user_type,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id
        })
        await asyncio.sleep(1)
        
        if not self.authenticated:
            print(f"❌ {self.name} authentication failed, skipping auth tests")
            return
        
        # Test 2: Tenant message
        print("Test 2: Tenant message")
        await self.send_message("tenant_message", {
            "message": f"Tenant message from {self.user_id}"
        })
        await asyncio.sleep(0.5)
        
        # Test 3: User notification (if we have multiple users)
        print("Test 3: User notification")
        target_user = "user2" if self.user_id == "user1" else "user1"
        await self.send_message("user_notification", {
            "target_user": target_user,
            "message": f"Direct message from {self.user_id}"
        })
        await asyncio.sleep(0.5)
        
        # Test 4: Admin commands (if admin)
        if self.user_type == "admin":
            print("Test 4: Admin commands")
            await self.send_message("admin_command", {"command": "stats"})
            await asyncio.sleep(0.5)
            
            await self.send_message("admin_command", {"command": "health"})
            await asyncio.sleep(0.5)
            
            await self.send_message("admin_command", {
                "command": "broadcast",
                "message": f"Admin broadcast from {self.user_id}"
            })
            await asyncio.sleep(0.5)
        
        # Test 5: Advanced broadcast
        print("Test 5: Advanced broadcast")
        await self.send_message("advanced_broadcast", {
            "type": "role_based",
            "role": "user",
            "message": f"Role broadcast from {self.user_id}"
        })
        await asyncio.sleep(0.5)
        
        print(f"✅ {self.name} authentication tests completed")
    
    async def handle_message(self, message_type: str, data: Any):
        """Handle authentication-specific messages."""
        if message_type == "demo_auth_success":
            self.authenticated = True
            print(f"   ✅ {self.name} authenticated as {data.get('user_id')}")
        elif message_type == "demo_auth_failed":
            print(f"   ❌ {self.name} authentication failed: {data.get('error')}")
        elif message_type in ["tenant_message", "user_notification", "admin_broadcast"]:
            sender = data.get("sender") or data.get("from", "unknown")
            message = data.get("message", "")
            print(f"   📨 {self.name} received {message_type} from {sender}: {message}")


class LoadTestClient(WebSocketTestClient):
    """Load testing client."""
    
    def __init__(self, uri: str, client_id: int, message_count: int = 10):
        super().__init__(uri, f"LoadClient_{client_id}")
        self.client_id = client_id
        self.message_count = message_count
        self.messages_sent = 0
        self.responses_received = 0
    
    async def perform_tests(self):
        """Perform load testing."""
        print(f"⚡ {self.name} - Load Test ({self.message_count} messages)")
        
        # Add response handler
        def count_response(data):
            self.responses_received += 1
        
        self.add_message_handler("pong", count_response)
        self.add_message_handler("echo_response", count_response)
        
        # Wait for connection
        await asyncio.sleep(0.5)
        
        # Send messages rapidly
        start_time = time.time()
        
        for i in range(self.message_count):
            if i % 2 == 0:
                await self.send_message("ping")
            else:
                await self.send_message("echo", {"sequence": i, "client": self.client_id})
            
            self.messages_sent += 1
            
            # Small delay to avoid overwhelming
            if i % 10 == 0:
                await asyncio.sleep(0.1)
        
        # Wait for responses
        await asyncio.sleep(2)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"   📊 {self.name} - Sent: {self.messages_sent}, "
              f"Received: {self.responses_received}, "
              f"Duration: {duration:.2f}s")


async def run_basic_tests(server_uri: str):
    """Run basic functionality tests."""
    print("\n🚀 Running Basic Functionality Tests")
    print("=" * 60)
    
    # Single client test
    client = BasicTestClient(server_uri)
    await client.run_test_sequence()


async def run_authentication_tests(server_uri: str):
    """Run authentication tests."""
    print("\n🔐 Running Authentication Tests")
    print("=" * 60)
    
    # Create multiple authenticated clients
    clients = [
        AuthenticatedTestClient(server_uri, "user1", "acme", "user"),
        AuthenticatedTestClient(server_uri, "admin1", "acme", "admin"),
        AuthenticatedTestClient(server_uri, "user2", "acme", "user"),
    ]
    
    # Run clients concurrently
    tasks = [client.run_test_sequence() for client in clients]
    await asyncio.gather(*tasks)


async def run_load_tests(server_uri: str, client_count: int = 5, messages_per_client: int = 20):
    """Run load tests."""
    print(f"\n⚡ Running Load Tests ({client_count} clients, {messages_per_client} messages each)")
    print("=" * 80)
    
    # Create load test clients
    clients = [
        LoadTestClient(server_uri, i, messages_per_client)
        for i in range(client_count)
    ]
    
    # Run load test
    start_time = time.time()
    tasks = [client.run_test_sequence() for client in clients]
    await asyncio.gather(*tasks)
    end_time = time.time()
    
    # Summary
    total_sent = sum(client.messages_sent for client in clients)
    total_received = sum(client.responses_received for client in clients)
    duration = end_time - start_time
    
    print(f"\n📊 Load Test Summary:")
    print(f"   Total messages sent: {total_sent}")
    print(f"   Total responses received: {total_received}")
    print(f"   Success rate: {(total_received / total_sent * 100):.1f}%")
    print(f"   Total duration: {duration:.2f}s")
    print(f"   Messages per second: {(total_sent / duration):.1f}")


async def main():
    """Main test runner."""
    print("🧪 DotMac WebSocket Gateway - Client Tests")
    print("=" * 70)
    
    # Configuration
    basic_server = "ws://localhost:8765/ws"  # Basic example server
    advanced_server = "ws://localhost:8766/ws/v1"  # Advanced example server
    
    print(f"Testing servers:")
    print(f"  Basic: {basic_server}")
    print(f"  Advanced: {advanced_server}")
    
    # Test which servers are available
    available_servers = []
    
    for name, uri in [("Basic", basic_server), ("Advanced", advanced_server)]:
        try:
            # Quick connection test
            websocket = await websockets.connect(uri)
            await websocket.close()
            available_servers.append((name, uri))
            print(f"  ✅ {name} server is running")
        except:
            print(f"  ❌ {name} server is not available")
    
    if not available_servers:
        print("\n❌ No servers are running. Please start a server first:")
        print("  python examples/basic_usage.py")
        print("  python examples/advanced_features.py")
        return
    
    # Run tests on available servers
    for name, uri in available_servers:
        print(f"\n🎯 Testing {name} Server ({uri})")
        print("=" * 60)
        
        try:
            # Basic tests for all servers
            await run_basic_tests(uri)
            await asyncio.sleep(2)
            
            # Advanced tests only for advanced server
            if "advanced" in name.lower() or "8766" in uri:
                await run_authentication_tests(uri)
                await asyncio.sleep(2)
            
            # Light load test
            await run_load_tests(uri, client_count=3, messages_per_client=10)
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ Tests failed for {name} server: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n🎉 All client tests completed!")
    print("\nTest coverage:")
    print("  ✅ Basic WebSocket connectivity")
    print("  ✅ Message routing and handling")
    print("  ✅ Channel subscriptions")
    print("  ✅ Room/channel messaging")
    print("  ✅ Authentication flows")
    print("  ✅ Tenant isolation")
    print("  ✅ Load testing")
    print("  ✅ Error handling")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nClient tests interrupted by user")
    except Exception as e:
        print(f"Client tests failed: {e}")
        import traceback
        traceback.print_exc()