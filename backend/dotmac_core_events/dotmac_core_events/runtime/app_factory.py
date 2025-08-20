"""
FastAPI application factory for dotmac_core_events.

Provides application factory functions to create configured FastAPI apps:
- Development app with all features enabled
- Production app with optimized settings
- SDK initialization and dependency injection
- API router registration
"""

from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import FastAPI

from ..adapters import KafkaAdapter, MemoryAdapter, RedisAdapter
from ..api import AdminAPI, EventsAPI, HealthAPI, SchemasAPI
from ..api.security import SecurityAPI
from ..core import set_event_bus_instance, set_outbox_instance, set_schema_registry_instance
from ..sdks import EventBusSDK, OutboxSDK, SchemaRegistrySDK
from .background_tasks import BackgroundTaskManager, start_background_tasks
from .config import RuntimeConfig
from .middleware import setup_middleware
from .security_validation import log_security_warnings

logger = structlog.get_logger(__name__)


async def initialize_sdks(config: RuntimeConfig) -> tuple[EventBusSDK, SchemaRegistrySDK, Optional[OutboxSDK]]:
    """
    Initialize and configure SDKs.

    Args:
        config: Runtime configuration

    Returns:
        Tuple of initialized SDKs
    """
    # Create event adapter
    adapter_config = config.get_adapter_config()

    if config.adapter_type == "redis":
        adapter = RedisAdapter(adapter_config)
    elif config.adapter_type == "kafka":
        adapter = KafkaAdapter(adapter_config)
    elif config.adapter_type == "memory":
        adapter = MemoryAdapter(adapter_config)
    else:
        raise ValueError(f"Unknown adapter type: {config.adapter_type}")

    # Connect adapter
    await adapter.connect()

    # Initialize EventBusSDK
    event_bus = EventBusSDK(adapter=adapter)

    # Initialize SchemaRegistrySDK
    schema_registry = SchemaRegistrySDK()

    # Initialize OutboxSDK if database is configured
    outbox = None
    if config.database:
        # This would require SQLAlchemy setup
        # outbox = OutboxSDK(database_url=config.database.url)
        pass

    return event_bus, schema_registry, outbox


def create_app(config: Optional[RuntimeConfig] = None) -> FastAPI:
    """
    Create FastAPI application for development.

    Args:
        config: Optional runtime configuration

    Returns:
        Configured FastAPI application
    """
    if config is None:
        from .config import load_config
        config = load_config()

    # Background task manager
    task_manager = BackgroundTaskManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan manager."""
        # Startup
        try:
            # Validate security configuration
            log_security_warnings()

            # Initialize SDKs
            event_bus, schema_registry, outbox = await initialize_sdks(config)

            # Set global SDK instances
            set_event_bus_instance(event_bus)
            set_schema_registry_instance(schema_registry)
            if outbox:
                set_outbox_instance(outbox)

            # Start background tasks
            if config.enable_background_tasks:
                await start_background_tasks(
                    task_manager,
                    event_bus,
                    schema_registry,
                    outbox,
                    config
                )

            yield

        finally:
            # Shutdown
            await task_manager.stop_all()

            # Disconnect adapter
            if hasattr(event_bus, "adapter"):
                await event_bus.adapter.disconnect()

    # Create FastAPI app
    app = FastAPI(
        title=config.app_name,
        version=config.app_version,
        debug=config.debug,
        lifespan=lifespan,
        docs_url="/docs" if config.debug else None,
        redoc_url="/redoc" if config.debug else None,
    )

    # Setup middleware
    setup_middleware(app, config)

    # Register API routers
    events_api = EventsAPI()
    schemas_api = SchemasAPI()
    health_api = HealthAPI()
    admin_api = AdminAPI()
    security_api = SecurityAPI()

    app.include_router(events_api.router, prefix="/api/v1")
    app.include_router(schemas_api.router, prefix="/api/v1")
    app.include_router(health_api.router, prefix="/api/v1")
    app.include_router(admin_api.router, prefix="/api/v1")
    app.include_router(security_api.router, prefix="/api/v1")

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "service": config.app_name,
            "version": config.app_version,
            "status": "running"
        }

    return app


def create_development_app(config: Optional[RuntimeConfig] = None) -> FastAPI:
    """
    Create FastAPI application for development.

    Args:
        config: Optional runtime configuration

    Returns:
        Development-optimized FastAPI application
    """
    if config is None:
        from .config import load_config
        config = load_config()

    # Force development settings
    config.debug = True

    # Create app with development settings
    return create_app(config)


def create_production_app(config: Optional[RuntimeConfig] = None) -> FastAPI:
    """
    Create FastAPI application for production.

    Args:
        config: Optional runtime configuration

    Returns:
        Production-optimized FastAPI application
    """
    if config is None:
        from .config import load_config
        config = load_config()

    # Force production settings
    config.debug = False

    # Validate security for production
    try:
        from .security_validation import validate_environment_security
        validate_environment_security(production_mode=True)
        logger.info("Production security validation passed")
    except Exception as e:
        logger.error("Production security validation failed", error=str(e))
        raise

    # Create app with production settings
    app = create_app(config)

    # Override docs URLs for production
    app.docs_url = None
    app.redoc_url = None

    return app
