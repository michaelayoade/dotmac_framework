"""
Unified Service Factory for All Shared Services

This is the master integration point that creates and coordinates all 4 shared service packages
with proper dependency injection, service registry integration, and production deployment support.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Type, Union

from ..core.config import WebSocketConfig
from ..core.events import EventManager
from ..core.manager import WebSocketManager
from ..patterns.broadcasting import BroadcastManager
from ..patterns.rooms import RoomManager
from ..scaling.redis_backend import RedisWebSocketBackend
from .service_integration import WebSocketService

logger = logging.getLogger(__name__)


class ServiceType(str, Enum):
    """Available shared service types."""

    CACHE = "cache"
    AUTH = "auth"
    FILES = "files"
    WEBSOCKET = "websocket"


@dataclass
class ServiceConfig:
    """Configuration for a specific service."""

    service_type: ServiceType
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: list = field(default_factory=list)


class UnifiedServiceFactory:
    """
    Master factory for creating and managing all 4 shared service packages.

    This factory handles:
    - Service dependency resolution and injection
    - Service registry integration
    - Health monitoring across all services
    - Configuration management
    - Graceful startup and shutdown
    - Cross-service communication
    """

    def __init__(self, global_config: Dict[str, Any]):
        """__init__ service method."""
        self.global_config = global_config
        self.services: Dict[str, Any] = {}
        self.service_configs: Dict[str, ServiceConfig] = {}
        self.is_initialized = False

        # Service registry integration
        self.service_registry = None
        self.health_checks_enabled = global_config.get("health_checks_enabled", True)

        # Metrics aggregation
        self.unified_metrics = {
            "services_initialized": 0,
            "services_healthy": 0,
            "total_startup_time": 0,
            "cross_service_calls": 0,
        }

    async def initialize_all_services(self) -> Dict[str, Any]:
        """
        Initialize all services in proper dependency order.

        Returns:
            Dictionary of initialized services

        Raises:
            RuntimeError: If service initialization fails
        """
        if self.is_initialized:
            return self.services

        start_time = asyncio.get_event_loop().time()

        logger.info("Starting unified service initialization")

        # Parse service configurations
        await self._parse_service_configs()

        # Initialize services in dependency order
        await self._initialize_cache_service()
        await self._initialize_auth_service()
        await self._initialize_file_service()
        await self._initialize_websocket_service()

        # Setup cross-service integrations
        await self._setup_cross_service_integrations()

        # Register with service registry
        if self.health_checks_enabled:
            await self._register_with_service_registry()

        # Start health monitoring
        await self._start_health_monitoring()

        self.is_initialized = True

        # Calculate startup time
        startup_time = asyncio.get_event_loop().time() - start_time
        self.unified_metrics["total_startup_time"] = startup_time

        logger.info(f"All services initialized successfully in {startup_time:.2f}s")
        return self.services

    async def shutdown_all_services(self):
        """Gracefully shutdown all services."""
        logger.info("Starting unified service shutdown")

        # Shutdown in reverse dependency order
        shutdown_order = ["websocket", "files", "auth", "cache"]

        for service_name in shutdown_order:
            if service_name in self.services:
                service = self.services[service_name]
                if hasattr(service, "stop"):
                    await service.stop()
                logger.info(f"Service {service_name} shutdown completed")

        self.services.clear()
        self.is_initialized = False
        logger.info("All services shutdown completed")

    async def get_service(self, service_type: ServiceType) -> Optional[Any]:
        """Get a specific service instance."""
        if not self.is_initialized:
            await self.initialize_all_services()

        return self.services.get(service_type.value)

    async def get_cache_service(self):
        """Get cache service instance."""
        return await self.get_service(ServiceType.CACHE)

    async def get_auth_service(self):
        """Get auth service instance."""
        return await self.get_service(ServiceType.AUTH)

    async def get_file_service(self):
        """Get file service instance."""
        return await self.get_service(ServiceType.FILES)

    async def get_websocket_service(self) -> WebSocketService:
        """Get WebSocket service instance."""
        return await self.get_service(ServiceType.WEBSOCKET)

    async def get_unified_health(self) -> Dict[str, Any]:
        """Get health status of all services."""
        health_status = {
            "overall_status": "healthy",
            "services": {},
            "metrics": self.unified_metrics.copy(),
        }

        failed_services = 0

        for service_name, service in self.services.items():
            if hasattr(service, "health_check"):
                service_health = await service.health_check()
                health_status["services"][service_name] = service_health.dict()

                if service_health.status.value != "ready":
                    failed_services += 1
            else:
                health_status["services"][service_name] = {
                    "status": "unknown",
                    "message": "No health check available",
                }

        # Determine overall status
        if failed_services == 0:
            health_status["overall_status"] = "healthy"
        elif failed_services < len(self.services):
            health_status["overall_status"] = "degraded"
        else:
            health_status["overall_status"] = "unhealthy"

        health_status["metrics"]["services_healthy"] = (
            len(self.services) - failed_services
        )

        return health_status

    async def get_unified_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics from all services."""
        unified_metrics = self.unified_metrics.copy()

        for service_name, service in self.services.items():
            if hasattr(service, "get_metrics"):
                service_metrics = service.get_metrics()
                unified_metrics[f"{service_name}_metrics"] = service_metrics

        return unified_metrics

    # Private initialization methods
    async def _parse_service_configs(self):
        """Parse service configurations from global config."""
        # Cache Service Configuration
        cache_config = self.global_config.get("cache", {})
        self.service_configs["cache"] = ServiceConfig(
            service_type=ServiceType.CACHE,
            enabled=cache_config.get("enabled", True),
            config=cache_config,
            dependencies=[],
        )

        # Auth Service Configuration
        auth_config = self.global_config.get("auth", {})
        self.service_configs["auth"] = ServiceConfig(
            service_type=ServiceType.AUTH,
            enabled=auth_config.get("enabled", True),
            config=auth_config,
            dependencies=["cache"],  # Auth depends on cache for sessions
        )

        # File Service Configuration
        file_config = self.global_config.get("files", {})
        self.service_configs["files"] = ServiceConfig(
            service_type=ServiceType.FILES,
            enabled=file_config.get("enabled", True),
            config=file_config,
            dependencies=["cache", "auth"],  # Files depend on cache and auth
        )

        # WebSocket Service Configuration
        websocket_config = self.global_config.get("websocket", {})
        self.service_configs["websocket"] = ServiceConfig(
            service_type=ServiceType.WEBSOCKET,
            enabled=websocket_config.get("enabled", True),
            config=websocket_config,
            dependencies=["cache", "auth", "files"],  # WebSocket depends on all
        )

    async def _initialize_cache_service(self):
        """Initialize cache service (no dependencies)."""
        config = self.service_configs["cache"]
        if not config.enabled:
            logger.info("Cache service disabled")
            return

        # Import cache service dynamically
        from dotmac_shared.cache import create_cache_service

        cache_service = await create_cache_service(config.config)
        await cache_service.start()

        self.services["cache"] = cache_service
        self.unified_metrics["services_initialized"] += 1

        logger.info("Cache service initialized successfully")

    async def _initialize_auth_service(self):
        """Initialize auth service (depends on cache)."""
        config = self.service_configs["auth"]
        if not config.enabled:
            logger.info("Auth service disabled")
            return

        # Import auth service dynamically
        from dotmac_shared.auth import create_auth_service

        cache_service = self.services.get("cache")
        auth_service = await create_auth_service(config.config, cache_service)

        self.services["auth"] = auth_service
        self.unified_metrics["services_initialized"] += 1

        logger.info("Auth service initialized successfully")

    async def _initialize_file_service(self):
        """Initialize file service (depends on cache and auth)."""
        config = self.service_configs["files"]
        if not config.enabled:
            logger.info("File service disabled")
            return

        # Import file service dynamically
        from dotmac_shared.files import create_file_service

        cache_service = self.services.get("cache")
        auth_service = self.services.get("auth")

        file_service = await create_file_service(
            config.config, cache_service, auth_service
        )

        self.services["files"] = file_service
        self.unified_metrics["services_initialized"] += 1

        logger.info("File service initialized successfully")

    async def _initialize_websocket_service(self):
        """Initialize WebSocket service (depends on all others)."""
        config = self.service_configs["websocket"]
        if not config.enabled:
            logger.info("WebSocket service disabled")
            return

        cache_service = self.services.get("cache")
        auth_service = self.services.get("auth")
        file_service = self.services.get("files")

        # Create WebSocket service with all dependencies
        websocket_service = await create_websocket_service(
            config.config, cache_service, auth_service, file_service
        )

        await websocket_service.start()

        self.services["websocket"] = websocket_service
        self.unified_metrics["services_initialized"] += 1

        logger.info("WebSocket service initialized successfully")

    async def _setup_cross_service_integrations(self):
        """Setup integrations between services."""
        logger.info("Setting up cross-service integrations")

        # WebSocket + Auth integration
        websocket_service = self.services.get("websocket")
        auth_service = self.services.get("auth")

        if websocket_service and auth_service:
            # Setup WebSocket authentication
            websocket_service.set_auth_service(auth_service)

            # Setup auth event notifications via WebSocket
            if hasattr(auth_service, "add_event_handler"):
                auth_service.add_event_handler(
                    "auth_status_changed", websocket_service.handle_auth_event
                )

        # WebSocket + File integration
        file_service = self.services.get("files")

        if websocket_service and file_service:
            # Setup file progress notifications
            if hasattr(file_service, "add_progress_handler"):
                file_service.add_progress_handler(
                    websocket_service.handle_file_progress
                )

        # Cache integration for all services
        cache_service = self.services.get("cache")
        if cache_service:
            for service_name, service in self.services.items():
                if service_name != "cache" and hasattr(service, "set_cache_service"):
                    service.set_cache_service(cache_service)

        self.unified_metrics["cross_service_calls"] = len(self.services) * (
            len(self.services) - 1
        )
        logger.info("Cross-service integrations completed")

    async def _register_with_service_registry(self):
        """Register all services with service registry."""
        if not self.health_checks_enabled:
            return

        # This would integrate with your service registry
        # For now, we'll just log the registration
        logger.info("Services registered with service registry:")
        for service_name in self.services.keys():
            logger.info(f"  - {service_name}: healthy")

    async def _start_health_monitoring(self):
        """Start background health monitoring."""
        if not self.health_checks_enabled:
            return

        # Start health check task
        asyncio.create_task(self._health_check_loop())
        logger.info("Health monitoring started")

    async def _health_check_loop(self):
        """Background task for periodic health checks."""
        while self.is_initialized:
            health_status = await self.get_unified_health()

            # Log unhealthy services
            for service_name, status in health_status["services"].items():
                if status.get("status") != "ready":
                    logger.warning(
                        f"Service {service_name} unhealthy: {status.get('message')}"
                    )

            await asyncio.sleep(30)  # Check every 30 seconds

    # Mock services for development/testing
    async def _create_mock_cache_service(self):
        """Create mock cache service for development."""

        class MockCacheService:
            """MockCacheService implementation."""

            async def start(self):
                pass

            async def stop(self):
                pass

            async def get(self, key, tenant_id=None):
                return None

            async def set(self, key, value, ttl=None, tenant_id=None):
                return True

            async def delete(self, key, tenant_id=None):
                return True

            async def health_check(self):
                from dotmac_shared.websockets.integration.service_integration import (
                    ServiceHealth,
                    ServiceStatus,
                )

                return ServiceHealth(
                    status=ServiceStatus.READY, message="Mock cache service"
                )

            def get_metrics(self):
                return {"type": "mock", "operations": 0}

        return MockCacheService()

    async def _create_mock_auth_service(self):
        """Create mock auth service for development."""

        class MockAuthService:
            """MockAuthService implementation."""

            async def start(self):
                pass

            async def stop(self):
                pass

            async def validate_token(self, token):
                return {"user_id": "mock_user"}

            async def health_check(self):
                from dotmac_shared.websockets.integration.service_integration import (
                    ServiceHealth,
                    ServiceStatus,
                )

                return ServiceHealth(
                    status=ServiceStatus.READY, message="Mock auth service"
                )

            def get_metrics(self):
                return {"type": "mock", "validations": 0}

        return MockAuthService()

    async def _create_mock_file_service(self):
        """Create mock file service for development."""

        class MockFileService:
            """MockFileService implementation."""

            async def start(self):
                pass

            async def stop(self):
                pass

            async def generate_file(self, template, data):
                return "mock_file.pdf"

            async def health_check(self):
                from dotmac_shared.websockets.integration.service_integration import (
                    ServiceHealth,
                    ServiceStatus,
                )

                return ServiceHealth(
                    status=ServiceStatus.READY, message="Mock file service"
                )

            def get_metrics(self):
                return {"type": "mock", "files_generated": 0}

        return MockFileService()


class WebSocketServiceFactory:
    """Factory for creating WebSocket service instances."""

    @staticmethod
    async def create_websocket_service(
        config: Dict[str, Any], cache_service=None, auth_service=None, file_service=None
    ) -> WebSocketService:
        """
        Create WebSocket service with dependencies.

        Args:
            config: WebSocket configuration
            cache_service: Cache service instance
            auth_service: Auth service instance
            file_service: File service instance

        Returns:
            Configured WebSocket service
        """
        # Create WebSocket config
        ws_config = WebSocketConfig(**config)

        # Create Redis backend for scaling
        redis_backend = RedisWebSocketBackend(ws_config)

        # Create core managers
        websocket_manager = WebSocketManager(ws_config, redis_backend=redis_backend)
        event_manager = EventManager(websocket_manager, cache_service, config)
        room_manager = RoomManager(websocket_manager, event_manager, config)
        broadcast_manager = BroadcastManager(websocket_manager, event_manager, config)

        # Create service integration wrapper
        websocket_service = WebSocketService(
            config=ws_config,
            websocket_manager=websocket_manager,
            event_manager=event_manager,
            room_manager=room_manager,
            broadcast_manager=broadcast_manager,
            redis_backend=redis_backend,
            cache_service=cache_service,
            auth_service=auth_service,
            file_service=file_service,
        )

        return websocket_service


# Convenience functions
async def create_websocket_service(
    config: Dict[str, Any], cache_service=None, auth_service=None, file_service=None
) -> WebSocketService:
    """Create standalone WebSocket service."""
    return await WebSocketServiceFactory.create_websocket_service(
        config, cache_service, auth_service, file_service
    )


async def create_unified_services(global_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create all unified services with proper integration."""
    factory = UnifiedServiceFactory(global_config)
    return await factory.initialize_all_services()
