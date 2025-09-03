#!/usr/bin/env python3
"""
Advanced features example for dotmac-websockets package.

This example demonstrates:
- JWT authentication
- Redis scaling backend
- Advanced broadcasting patterns
- Rate limiting
- Tenant isolation
- Health monitoring
- Observability integration
"""

import asyncio
import json
import jwt
import time
import logging
from dotmac.websockets import (
    # Core components
    WebSocketGateway,
    WebSocketConfig,
    RedisConfig,
    AuthConfig,
    create_production_config,
    
    # Configuration enums
    BackendType,
    
    # Observability
    create_default_hooks,
    create_dotmac_observability_hooks,
    
    # Broadcast utilities
    BroadcastTarget,
    BroadcastScope,
    BroadcastMessage,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT Secret for demo - NEVER use this in production
JWT_SECRET = os.getenv("JWT_SECRET", "INSECURE-EXAMPLE-KEY-NEVER-USE-IN-PRODUCTION")


def create_demo_jwt_token(user_id: str, tenant_id: str, roles=None, permissions=None):
    """Create a demo JWT token for testing."""
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "username": f"user_{user_id}",
        "email": f"user_{user_id}@example.com",
        "tenant_id": tenant_id,
        "roles": roles or ["user"],
        "permissions": permissions or ["read", "write"],
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,  # 1 hour expiration
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def main():
    """Main advanced features example."""
    print("🚀 DotMac WebSocket Gateway - Advanced Features Example")
    print("=" * 70)
    
    # 1. Create advanced configuration
    print("\n1. Creating advanced WebSocket configuration...")
    
    config = WebSocketConfig(
        # Server settings
        host="0.0.0.0",
        port=8766,
        path="/ws/v1",
        
        # Redis scaling backend
        backend_type=BackendType.REDIS,
        redis_config=RedisConfig(
            host="localhost",
            port=6379,
            db=0,
            channel_prefix="dotmac_ws"
        ),
        
        # Authentication configuration
        auth_config=AuthConfig(
            enabled=True,
            jwt_secret_key=JWT_SECRET,
            jwt_algorithm="HS256",
            require_token=False,  # Allow anonymous for demo
            require_permissions=[]
        ),
        
        # Rate limiting
        rate_limit_config=dict(
            enabled=True,
            max_connections_per_ip=20,
            max_connections_per_user=5,
            messages_per_minute=60,
            burst_size=10
        ),
        
        # Session configuration
        session_config=dict(
            idle_timeout_seconds=300,
            ping_interval_seconds=30
        ),
        
        # Tenant isolation
        tenant_isolation_enabled=True,
        
        # Observability
        observability_config=dict(
            enabled=True,
            health_check_enabled=True,
            export_metrics=True
        )
    )
    
    print(f"   ✅ Advanced configuration created:")
    print(f"      - Redis scaling: Enabled")
    print(f"      - Authentication: JWT with optional tokens")
    print(f"      - Rate limiting: 60 msg/min, 10 burst")
    print(f"      - Tenant isolation: Enabled")
    print(f"      - Health monitoring: Enabled")
    
    # 2. Create gateway with advanced features
    print("\n2. Creating WebSocket gateway with advanced features...")
    gateway = WebSocketGateway(config)
    
    # 3. Set up advanced observability
    print("\n3. Setting up advanced observability...")
    try:
        # Try to use OpenTelemetry if available
        hooks = create_dotmac_observability_hooks("dotmac-websockets-demo")
        print("   ✅ OpenTelemetry observability configured")
    except:
        # Fallback to default hooks
        hooks = create_default_hooks("dotmac.websockets.demo")
        print("   ✅ Default observability hooks configured")
    
    gateway.set_observability_hooks(hooks)
    
    # 4. Add advanced message handlers
    print("\n4. Adding advanced message handlers...")
    
    async def handle_admin_command(session, data):
        """Handle admin commands (requires admin role)."""
        if not session.is_authenticated:
            await session.send_message("error", {"message": "Authentication required"})
            return
        
        # Check if user has admin role (this would be set by JWT)
        user_info = getattr(session, 'user_info', None)
        if not user_info or not hasattr(user_info, 'has_role') or not user_info.has_role('admin'):
            await session.send_message("permission_denied", {
                "message": "Admin role required"
            })
            return
        
        command = data.get("command") if isinstance(data, dict) else None
        if command == "stats":
            stats = gateway.get_stats()
            await session.send_message("admin_stats", stats)
        elif command == "health":
            health = await gateway.health_check()
            await session.send_message("admin_health", health)
        elif command == "broadcast":
            message = data.get("message", "Admin broadcast")
            await gateway.broadcast_to_tenant(
                session.tenant_id,
                "admin_broadcast",
                {"message": message, "from": "admin"}
            )
            await session.send_message("broadcast_sent", {"message": "Broadcast sent to tenant"})
        else:
            await session.send_message("error", {"message": f"Unknown admin command: {command}"})
    
    async def handle_tenant_message(session, data):
        """Handle tenant-wide messaging."""
        if not session.is_authenticated:
            await session.send_message("error", {"message": "Authentication required"})
            return
        
        message = data.get("message") if isinstance(data, dict) else None
        if not message:
            await session.send_message("error", {"message": "Message required"})
            return
        
        # Broadcast to all users in the same tenant
        delivered = await gateway.broadcast_to_tenant(
            session.tenant_id,
            "tenant_message",
            {
                "message": message,
                "sender": session.user_id,
                "tenant_id": session.tenant_id,
                "timestamp": time.time()
            }
        )
        
        await session.send_message("message_sent", {
            "type": "tenant_broadcast",
            "delivered_count": delivered
        })
    
    async def handle_user_notification(session, data):
        """Send notification to specific user."""
        if not session.is_authenticated:
            await session.send_message("error", {"message": "Authentication required"})
            return
        
        target_user = data.get("target_user") if isinstance(data, dict) else None
        message = data.get("message") if isinstance(data, dict) else None
        
        if not target_user or not message:
            await session.send_message("error", {"message": "Target user and message required"})
            return
        
        # Send to specific user
        delivered = await gateway.broadcast_to_user(
            target_user,
            "user_notification",
            {
                "message": message,
                "from": session.user_id,
                "timestamp": time.time()
            }
        )
        
        await session.send_message("notification_sent", {
            "target_user": target_user,
            "delivered": delivered > 0
        })
    
    async def handle_advanced_broadcast(session, data):
        """Demonstrate advanced broadcast patterns."""
        if not session.is_authenticated:
            await session.send_message("error", {"message": "Authentication required"})
            return
        
        broadcast_type = data.get("type") if isinstance(data, dict) else None
        message_content = data.get("message") if isinstance(data, dict) else "Test message"
        
        broadcast_manager = gateway.channel_manager.broadcast_manager if hasattr(gateway.channel_manager, 'broadcast_manager') else None
        
        if broadcast_type == "role_based":
            # Broadcast to users with specific role
            target_role = data.get("role", "user")
            # This would work with the BroadcastManager
            await session.send_message("broadcast_info", {
                "message": f"Role-based broadcast to '{target_role}' users would be sent here"
            })
            
        elif broadcast_type == "permission_based":
            # Broadcast to users with specific permission
            permission = data.get("permission", "read")
            await session.send_message("broadcast_info", {
                "message": f"Permission-based broadcast to users with '{permission}' would be sent here"
            })
            
        else:
            await session.send_message("error", {"message": "Invalid broadcast type"})
    
    # Register advanced handlers
    gateway.add_message_handler("admin_command", handle_admin_command)
    gateway.add_message_handler("tenant_message", handle_tenant_message) 
    gateway.add_message_handler("user_notification", handle_user_notification)
    gateway.add_message_handler("advanced_broadcast", handle_advanced_broadcast)
    
    print("   ✅ Advanced message handlers added:")
    print("      - admin_command: Admin-only commands")
    print("      - tenant_message: Tenant-wide messaging")
    print("      - user_notification: Direct user messaging")
    print("      - advanced_broadcast: Role/permission-based broadcasting")
    
    # 5. Add authentication example
    print("\n5. Adding authentication demonstration...")
    
    async def handle_demo_auth(session, data):
        """Demonstrate authentication with different user types."""
        user_type = data.get("user_type", "user") if isinstance(data, dict) else "user"
        user_id = data.get("user_id", "demo_user") if isinstance(data, dict) else "demo_user"
        tenant_id = data.get("tenant_id", "demo_tenant") if isinstance(data, dict) else "demo_tenant"
        
        # Create appropriate JWT token based on user type
        if user_type == "admin":
            roles = ["user", "admin"]
            permissions = ["read", "write", "admin", "broadcast"]
        elif user_type == "moderator":
            roles = ["user", "moderator"]
            permissions = ["read", "write", "moderate"]
        else:
            roles = ["user"]
            permissions = ["read", "write"]
        
        token = create_demo_jwt_token(user_id, tenant_id, roles, permissions)
        
        # Authenticate the session
        auth_result = await gateway.auth_manager.authenticate_token(token)
        
        if auth_result.success:
            # Update session with user info
            gateway.session_manager.update_session_user_info(
                session.session_id,
                auth_result.user_info.user_id,
                auth_result.user_info.tenant_id,
                user_info=auth_result.user_info
            )
            
            await session.send_message("demo_auth_success", {
                "user_id": auth_result.user_info.user_id,
                "tenant_id": auth_result.user_info.tenant_id,
                "roles": auth_result.user_info.roles,
                "permissions": auth_result.user_info.permissions,
                "token": token[:20] + "...",  # Truncate for display
                "message": f"Authenticated as {user_type}"
            })
        else:
            await session.send_message("demo_auth_failed", {
                "error": auth_result.error
            })
    
    gateway.add_message_handler("demo_auth", handle_demo_auth)
    
    print("   ✅ Demo authentication handler added")
    
    # 6. Add connection handlers for advanced features
    async def on_advanced_connect(session):
        """Enhanced connection handler."""
        await session.send_message("welcome", {
            "message": "Welcome to DotMac WebSocket Gateway - Advanced Features Demo!",
            "session_id": session.session_id,
            "features": {
                "authentication": "JWT-based with roles and permissions",
                "scaling": "Redis backend for multi-instance deployment",
                "rate_limiting": "Per-IP and per-user limits",
                "tenant_isolation": "Multi-tenant support",
                "observability": "Health checks and metrics",
                "broadcasting": "Advanced targeting and patterns"
            },
            "demo_commands": [
                '{"type": "demo_auth", "data": {"user_type": "admin", "user_id": "admin1", "tenant_id": "acme"}}',
                '{"type": "demo_auth", "data": {"user_type": "user", "user_id": "user1", "tenant_id": "acme"}}',
                '{"type": "tenant_message", "data": {"message": "Hello tenant!"}}',
                '{"type": "user_notification", "data": {"target_user": "user1", "message": "Direct message"}}',
                '{"type": "admin_command", "data": {"command": "stats"}}',
                '{"type": "advanced_broadcast", "data": {"type": "role_based", "role": "admin"}}'
            ]
        })
        
        # Show rate limiting status
        if gateway.rate_limit_middleware.config.enabled:
            rate_status = gateway.rate_limit_middleware.get_rate_limit_status(session)
            await session.send_message("rate_limit_info", rate_status)
    
    gateway.add_connection_handler(on_advanced_connect)
    
    # 7. Start the advanced gateway
    print("\n7. Starting advanced WebSocket gateway...")
    try:
        await gateway.start_server()
        
        print(f"   🟢 Advanced WebSocket server started on ws://localhost:8766/ws/v1")
        print(f"   🔗 Redis backend: {'Connected' if gateway.scaling_backend else 'Local mode'}")
        
        print("\n📋 Advanced Test Scenarios:")
        print("   Connect to: ws://localhost:8766/ws/v1")
        print("   1. Authenticate as admin:")
        print('      {"type": "demo_auth", "data": {"user_type": "admin", "user_id": "admin1", "tenant_id": "acme"}}')
        print("   2. Get system stats (admin only):")
        print('      {"type": "admin_command", "data": {"command": "stats"}}')
        print("   3. Send tenant-wide message:")
        print('      {"type": "tenant_message", "data": {"message": "Hello tenant!"}}')
        print("   4. Rate limit test (send multiple messages quickly)")
        
        print("\n💡 Advanced features demonstrated:")
        print("   - JWT authentication with roles and permissions")
        print("   - Redis scaling backend for multi-instance deployment")
        print("   - Rate limiting with burst capacity")
        print("   - Tenant isolation and multi-tenancy")
        print("   - Role and permission-based message handling")
        print("   - Advanced broadcasting patterns")
        print("   - Health monitoring and metrics")
        print("   - Session management with timeout")
        
        # 8. Monitoring loop
        print("\n8. Starting monitoring loop...")
        print("   Server is running... Press Ctrl+C to stop")
        
        monitor_interval = 30  # 30 seconds
        last_stats = None
        
        while True:
            try:
                await asyncio.sleep(monitor_interval)
                
                # Get current stats
                current_stats = gateway.get_stats()
                sessions = current_stats['sessions']['total_sessions']
                channels = current_stats['channels']['total_channels']
                
                if sessions > 0 or (last_stats and last_stats != sessions):
                    print(f"   📊 Monitor - Sessions: {sessions}, Channels: {channels}")
                    
                    # Show health status
                    health = await gateway.health_check()
                    if health['status'] != 'healthy':
                        print(f"   ⚠️  Health status: {health['status']}")
                
                last_stats = sessions
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"   ❌ Monitor error: {e}")
    
    except Exception as e:
        print(f"   ❌ Failed to start server: {e}")
        return
    
    except KeyboardInterrupt:
        print("\n🛑 Shutting down advanced server...")
    
    finally:
        # 9. Graceful shutdown
        await gateway.stop_server()
        print("   ✅ Advanced server stopped gracefully")
    
    print("\n🎉 Advanced features example completed!")
    print("\nProduction considerations:")
    print("- Use environment variables for JWT secrets")
    print("- Configure Redis with authentication")
    print("- Set up proper SSL/TLS certificates")
    print("- Configure rate limiting based on your needs")
    print("- Set up monitoring and alerting")
    print("- Use load balancers for high availability")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAdvanced example interrupted by user")
    except Exception as e:
        print(f"Advanced example failed: {e}")
        import traceback
        traceback.print_exc()