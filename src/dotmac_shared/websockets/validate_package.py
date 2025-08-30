#!/usr/bin/env python3
"""
WebSocket Service Package Validation Script

This script validates the complete WebSocket service package implementation,
testing all components, integrations, and functionality.
"""

import asyncio
import logging
import sys
from typing import Any, Dict

# Setup logging
logging.basicConfig(level=logging.INFO, format='.format(levelname)s: .format(message)s')
logger = logging.getLogger(__name__)


def test_imports():
    """Test all package imports."""

    tests = [
        ("Core components", [
            "dotmac_shared.websockets.core.config",
            "dotmac_shared.websockets.core.manager",
            "dotmac_shared.websockets.core.events",
        ]),
        ("Pattern implementations", [
            "dotmac_shared.websockets.patterns.rooms",
            "dotmac_shared.websockets.patterns.broadcasting",
        ]),
        ("Scaling components", [
            "dotmac_shared.websockets.scaling.redis_backend",
        ]),
        ("Integration layer", [
            "dotmac_shared.websockets.integration.service_factory",
            "dotmac_shared.websockets.integration.service_integration",
        ]),
        ("Main package", [
            "dotmac_shared.websockets",
        ])
    ]

    all_passed = True

    for category, modules in tests:
        for module in modules:
            try:
                __import__(module)
            except ImportError as e:
                all_passed = False

    return all_passed


def test_configuration():
    """Test configuration system."""

    try:
        from dotmac_shared.websockets.core.config import WebSocketConfig

        # Test basic config
        config = WebSocketConfig(
            max_connections=1000,
            heartbeat_interval=30,
            redis_url="redis://localhost:6379"
        )

        # Test testing config - create with valid heartbeat_interval
        test_config = WebSocketConfig(
            max_connections=10,
            heartbeat_interval=10,  # Use minimum allowed value
            redis_url="redis://localhost:6379",
            enable_persistence=False
        )

        # Test production config
        prod_config = WebSocketConfig.for_production()

        # Test config validation
        try:
            invalid_config = WebSocketConfig(max_connections=-1)
        except Exception:


        return True

    except Exception as e:
        return False


def test_service_creation():
    """Test service creation without starting."""

    try:
        from dotmac_shared.websockets.core.config import WebSocketConfig
        from dotmac_shared.websockets.core.events import (
            EventManager,
            EventPriority,
            WebSocketEvent,
        )
        from dotmac_shared.websockets.core.manager import WebSocketManager
        from dotmac_shared.websockets.patterns.broadcasting import BroadcastManager
        from dotmac_shared.websockets.patterns.rooms import RoomManager

        # Create config
        config = WebSocketConfig(
            max_connections=100,
            heartbeat_interval=30,
            redis_url="redis://localhost:6379",
            enable_persistence=False  # Disable for testing
        )

        # Create managers (don't start them)
        websocket_manager = WebSocketManager(config)

        event_manager = EventManager(websocket_manager, config=config.to_dict())

        room_manager = RoomManager(websocket_manager, event_manager, config.to_dict())

        broadcast_manager = BroadcastManager(websocket_manager, event_manager, config.to_dict())

        # Test event creation
        event = WebSocketEvent(
            event_type="test_event",
            data={"message": "Hello, World!"},
            priority=EventPriority.NORMAL
        )

        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False


def test_integration_factory():
    """Test service integration factory."""

    try:
        from dotmac_shared.websockets.integration.service_factory import (
            UnifiedServiceFactory,
        )
        from dotmac_shared.websockets.integration.service_integration import (
            ServiceHealth,
            ServiceStatus,
        )

        # Create factory configuration
        global_config = {
            'cache': {'enabled': False},  # Disable for testing
            'auth': {'enabled': False},
            'files': {'enabled': False},
            'websocket': {
                'enabled': True,
                'max_connections': 100,
                'heartbeat_interval': 30,
                'redis_url': 'redis://localhost:6379',
                'enable_persistence': False,
            },
            'health_checks_enabled': True,
        }

        # Create factory
        factory = UnifiedServiceFactory(global_config)

        # Test service health object
        health = ServiceHealth(ServiceStatus.READY, "Test service healthy")

        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False


async def test_async_functionality():
    """Test basic async functionality."""

    try:
        from dotmac_shared.websockets.core.config import WebSocketConfig
        from dotmac_shared.websockets.core.events import EventManager
        from dotmac_shared.websockets.core.manager import WebSocketManager

        # Create minimal config
        config = WebSocketConfig(
            max_connections=10,
            heartbeat_interval=30,
            redis_url="redis://localhost:6379",
            enable_persistence=False
        )

        # Create manager
        manager = WebSocketManager(config)

        # Test basic operations without starting

        # Test metrics
        metrics = manager.get_metrics()

        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False


def test_package_structure():
    """Test package structure and exports."""

    try:
        # Test package metadata
        import dotmac_shared.websockets as ws_package
        from dotmac_shared.websockets import (
            BroadcastManager,
            EventManager,
            RedisWebSocketBackend,
            RoomManager,
            UnifiedServiceFactory,
            WebSocketConfig,
            WebSocketEvent,
            WebSocketManager,
            create_websocket_service,
        )

        # Test default configuration
        default_config = ws_package.get_config()

        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""

    tests = [
        ("Import Tests", test_imports),
        ("Configuration Tests", test_configuration),
        ("Service Creation Tests", test_service_creation),
        ("Integration Factory Tests", test_integration_factory),
        ("Package Structure Tests", test_package_structure),
    ]

    results = {}

    # Run synchronous tests
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            results[test_name] = False

    # Run async tests
    try:
        async_result = asyncio.run(test_async_functionality())
        results["Async Functionality Tests"] = async_result
    except Exception as e:
        results["Async Functionality Tests"] = False

    # Print summary

    passed = 0
    total = len(results)

    for test_name, passed_test in results.items():
        status = "✅ PASSED" if passed_test else "❌ FAILED"
        if passed_test:
            passed += 1


    if passed == total:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
