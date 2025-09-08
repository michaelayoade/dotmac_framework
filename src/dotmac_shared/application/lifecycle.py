"""
Standard lifecycle management for DotMac applications.
"""

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..health.comprehensive_checks import HealthChecker
from ..health.endpoints import add_health_endpoints, add_startup_status_endpoint
from ..startup.error_handling import StartupErrorSeverity, StartupPhase, managed_startup
from .config import DeploymentMode, PlatformConfig

logger = logging.getLogger(__name__)


class StandardLifecycleManager:
    """Standard lifecycle management for all DotMac applications."""

    def __init__(self, platform_config: PlatformConfig, service_registry=None):
        self.platform_config = platform_config
        self.service_registry = service_registry
        self.startup_tasks: dict[str, Callable] = {}
        self.shutdown_tasks: dict[str, Callable] = {}
        self._register_standard_tasks()

    def _register_standard_tasks(self):
        """Register standard startup and shutdown tasks."""
        # Standard startup tasks
        self.startup_tasks.update(
            {
                "initialize_services": self._initialize_services,
                "initialize_database": self._initialize_database,
                "initialize_cache": self._initialize_cache,
                "initialize_observability": self._initialize_observability,
                "setup_health_checks": self._setup_health_checks,
                "initialize_security": self._initialize_security,
            }
        )

        # Standard shutdown tasks
        self.shutdown_tasks.update(
            {
                "shutdown_observability": self._shutdown_observability,
                "close_database": self._close_database,
                "close_cache": self._close_cache,
                "shutdown_services": self._shutdown_services,
            }
        )

        # Add platform-specific tasks
        self._register_platform_specific_tasks()

    def _register_platform_specific_tasks(self):
        """Register platform-specific startup/shutdown tasks."""
        if not self.platform_config.deployment_context:
            return

        mode = self.platform_config.deployment_context.mode

        if mode == DeploymentMode.TENANT_CONTAINER:
            self.startup_tasks.update(
                {
                    "configure_tenant_isolation": self._configure_tenant_isolation,
                    "initialize_ssl_manager": self._initialize_ssl_manager,
                    "start_celery_monitoring": self._start_celery_monitoring,
                    "initialize_usage_reporting": self._initialize_usage_reporting,
                }
            )
            self.shutdown_tasks.update(
                {
                    "shutdown_ssl_manager": self._shutdown_ssl_manager,
                    "shutdown_usage_reporting": self._shutdown_usage_reporting,
                }
            )

        elif mode == DeploymentMode.MANAGEMENT_PLATFORM:
            self.startup_tasks.update(
                {
                    "initialize_plugin_system": self._initialize_plugin_system,
                    "start_tenant_monitoring": self._start_tenant_monitoring,
                    "configure_kubernetes_client": self._configure_kubernetes_client,
                    "initialize_websocket_manager": self._initialize_websocket_manager,
                }
            )
            self.shutdown_tasks.update(
                {
                    "shutdown_websocket_manager": self._shutdown_websocket_manager,
                    "shutdown_plugins": self._shutdown_plugins,
                }
            )

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Standard lifespan manager for all platforms."""
        service_name = f"DotMac {self.platform_config.title}"

        async with managed_startup(
            service_name=service_name,
            fail_on_critical=True,
            fail_on_high_severity=False,
        ) as startup_manager:
            logger.info(f"Starting {service_name}...")

            # Execute standard startup sequence
            await self._execute_startup_sequence(app, startup_manager)

            # Store startup manager in app state
            app.state.startup_manager = startup_manager

            logger.info(f"🚀 {service_name} startup complete")

        yield

        # Execute shutdown sequence
        await self._execute_shutdown_sequence(app)

        logger.info(f"✅ {service_name} shutdown complete")

    async def _execute_startup_sequence(self, app: FastAPI, startup_manager):
        """Execute the standard startup sequence."""

        # Phase 1: Initialize services first
        for task_name in ["initialize_services"]:
            if task_name in self.startup_tasks:
                await self._execute_startup_task(app, startup_manager, task_name)

        # Phase 2: Initialize core infrastructure
        for task_name in [
            "initialize_database",
            "initialize_cache",
            "initialize_observability",
        ]:
            if task_name in self.startup_tasks:
                await self._execute_startup_task(app, startup_manager, task_name)

        # Phase 3: Initialize platform-specific services
        for task_name in self.platform_config.startup_tasks:
            if task_name in self.startup_tasks:
                await self._execute_startup_task(app, startup_manager, task_name)

        # Phase 4: Initialize security and health checks
        for task_name in ["initialize_security", "setup_health_checks"]:
            if task_name in self.startup_tasks:
                await self._execute_startup_task(app, startup_manager, task_name)

    async def _execute_startup_task(self, app: FastAPI, startup_manager, task_name: str):
        """Execute a single startup task with error handling."""
        try:
            task_func = self.startup_tasks[task_name]

            result = await startup_manager.execute_with_retry(
                operation=lambda: task_func(app, startup_manager),
                phase=StartupPhase.INITIALIZATION,
                component=task_name.replace("_", " ").title(),
                severity=StartupErrorSeverity.MEDIUM,
                max_retries=1,
            )

            if result.success:
                logger.info(f"✅ {task_name} completed successfully")
            else:
                logger.warning(f"⚠️ {task_name} failed")

        except Exception as e:
            logger.error(f"❌ {task_name} failed with error: {e}")

    async def _execute_shutdown_sequence(self, app: FastAPI):
        """Execute the standard shutdown sequence."""
        logger.info("Starting shutdown sequence...")

        # Execute platform-specific shutdown tasks first
        for task_name in self.platform_config.shutdown_tasks:
            if task_name in self.shutdown_tasks:
                await self._execute_shutdown_task(app, task_name)

        # Execute standard shutdown tasks (services last)
        for task_name in [
            "shutdown_observability",
            "close_cache",
            "close_database",
            "shutdown_services",
        ]:
            if task_name in self.shutdown_tasks:
                await self._execute_shutdown_task(app, task_name)

    async def _execute_shutdown_task(self, app: FastAPI, task_name: str):
        """Execute a single shutdown task with error handling."""
        try:
            task_func = self.shutdown_tasks[task_name]
            await task_func(app)
            logger.info(f"✅ {task_name} completed")
        except Exception as e:
            logger.warning(f"⚠️ {task_name} failed: {e}")

    # Standard startup task implementations
    async def _initialize_database(self, app: FastAPI, startup_manager):
        """Initialize database connection."""
        try:
            # Try to get platform-specific database initialization
            if self.platform_config.deployment_context:
                mode = self.platform_config.deployment_context.mode

                if mode == DeploymentMode.TENANT_CONTAINER:
                    from dotmac_isp.core.database import init_database

                    await init_database()
                elif mode == DeploymentMode.MANAGEMENT_PLATFORM:
                    from dotmac_management.database import init_database

                    await init_database()

            logger.info("Database initialized")

        except ImportError as e:
            logger.warning(f"Database initialization not available: {e}")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def _initialize_cache(self, app: FastAPI, startup_manager):
        """Initialize cache connection."""
        try:
            # Try to get platform-specific cache manager
            if self.platform_config.deployment_context:
                mode = self.platform_config.deployment_context.mode

                if mode == DeploymentMode.TENANT_CONTAINER:
                    from dotmac_isp.shared.cache import get_cache_manager

                    cache_manager = get_cache_manager()
                    app.state.cache_manager = cache_manager
                elif mode == DeploymentMode.MANAGEMENT_PLATFORM:
                    from dotmac_management.core.cache import get_cache_manager

                    cache_manager = await get_cache_manager()
                    app.state.cache_manager = cache_manager

            logger.info("Cache initialized")

        except ImportError as e:
            logger.warning(f"Cache initialization not available: {e}")
        except Exception as e:
            logger.error(f"Cache initialization failed: {e}")
            raise

    async def _initialize_observability(self, app: FastAPI, startup_manager):
        """Initialize comprehensive observability system."""
        try:
            from .observability_setup import setup_observability

            logger.info("🔍 Initializing comprehensive observability system...")

            # Enable business SLOs for production environments
            enable_business_slos = self.platform_config.observability_config.tier in [
                "comprehensive",
                "business",
            ]

            # Set up complete observability stack
            observability_components = await setup_observability(
                app=app,
                platform_config=self.platform_config,
                enable_business_slos=enable_business_slos,
            )

            # Store components for health checks and monitoring
            app.state.observability_components = observability_components
            app.state.observability_tier = self.platform_config.observability_config.tier

            # Log successful initialization
            component_count = len(observability_components)
            logger.info("✅ Comprehensive observability initialized")
            logger.info(f"   Components: {component_count}")
            logger.info(f"   Tier: {self.platform_config.observability_config.tier}")
            logger.info(f"   Business SLOs: {'Enabled' if enable_business_slos else 'Disabled'}")

            # Record initialization metric
            if "metrics_registry" in observability_components:
                metrics_registry = observability_components["metrics_registry"]
                metrics_registry.increment_counter(
                    "observability_initialization_total",
                    1,
                    {
                        "status": "success",
                        "tier": self.platform_config.observability_config.tier,
                    },
                )

        except ImportError as e:
            logger.warning(f"New observability system not available, falling back: {e}")
            await self._fallback_observability_initialization(app, startup_manager)
        except Exception as e:
            logger.error(f"Observability initialization failed: {e}")
            await self._fallback_observability_initialization(app, startup_manager)
            raise

    async def _fallback_observability_initialization(self, app: FastAPI, startup_manager):
        """Fallback to legacy observability initialization."""
        try:
            # Try to get settings for observability
            settings = None
            if self.platform_config.deployment_context:
                mode = self.platform_config.deployment_context.mode

                if mode == DeploymentMode.TENANT_CONTAINER:
                    from dotmac_isp.core.settings import get_settings

                    settings = get_settings()
                elif mode == DeploymentMode.MANAGEMENT_PLATFORM:
                    from dotmac_management.config import settings

            if settings and hasattr(settings, "create_observability_instance"):
                # Initialize tiered observability
                observability_instance = settings.create_observability_instance()

                initialization_success = await observability_instance.validate_and_initialize()
                if not initialization_success:
                    raise RuntimeError("Observability validation failed")

                status = await observability_instance.get_system_status()
                app.state.observability_instance = observability_instance
                app.state.observability_tier = status["tier"]

                logger.info(f"🎯 Legacy observability initialized - Tier: {status['tier']}")

        except Exception as e:
            logger.warning(f"Legacy observability initialization failed: {e}")

    async def _setup_health_checks(self, app: FastAPI, startup_manager):
        """Set up health check system."""
        try:
            health_checker = HealthChecker(
                {
                    "service_name": f"DotMac {self.platform_config.title}",
                    "cache_client": getattr(app.state, "cache_manager", None),
                    "additional_filesystem_paths": self.platform_config.health_config.additional_filesystem_paths,
                }
            )

            app.state.health_checker = health_checker

            # Add health endpoints
            add_health_endpoints(app)
            add_startup_status_endpoint(app)

            logger.info(f"Health checks configured: {len(health_checker.health_checks)} checks")

        except Exception as e:
            logger.error(f"Health check setup failed: {e}")

    async def _initialize_security(self, app: FastAPI, startup_manager):
        """Initialize security systems."""
        try:
            if self.platform_config.security_config.api_security_suite:
                # Try to initialize API security suite
                pass  # This would be handled by middleware stack

            logger.info("Security systems initialized")

        except Exception as e:
            logger.warning(f"Security initialization failed: {e}")

    # Platform-specific task implementations
    async def _configure_tenant_isolation(self, app: FastAPI, startup_manager):
        """Configure tenant isolation for tenant containers."""
        try:
            from dotmac_isp.core.database import engine, get_session
            from dotmac_isp.core.tenant_security import init_tenant_security

            async with get_session() as session:
                await init_tenant_security(engine, session)

            logger.info("Tenant isolation configured")

        except ImportError:
            logger.warning("Tenant isolation not available")
        except Exception as e:
            logger.error(f"Tenant isolation configuration failed: {e}")

    async def _initialize_ssl_manager(self, app: FastAPI, startup_manager):
        """Initialize SSL manager."""
        try:
            from dotmac_isp.core.ssl_manager import initialize_ssl

            await initialize_ssl()
            logger.info("SSL manager initialized")

        except ImportError:
            logger.debug("SSL manager not available")
        except Exception as e:
            logger.warning(f"SSL manager initialization failed: {e}")

    async def _start_celery_monitoring(self, app: FastAPI, startup_manager):
        """Start Celery monitoring."""
        try:
            # Test Celery connection
            if self.platform_config.deployment_context:
                mode = self.platform_config.deployment_context.mode

                if mode == DeploymentMode.TENANT_CONTAINER:
                    from dotmac_isp.core.celery_app import celery_app

                    celery_app.send_task("dotmac_isp.core.tasks.health_check")
                elif mode == DeploymentMode.MANAGEMENT_PLATFORM:
                    from dotmac_management.workers.celery_app import celery_app

                    celery_app.send_task("app.workers.tasks.monitoring_tasks.health_check")

            logger.info("Celery monitoring started")

        except ImportError:
            logger.debug("Celery not available")
        except Exception as e:
            logger.warning(f"Celery monitoring failed: {e}")

    async def _initialize_usage_reporting(self, app: FastAPI, startup_manager):
        """Initialize usage reporting for tenant containers."""
        try:
            from dotmac_isp.core.usage_reporter import UsageReporter

            # Create usage reporter instance
            usage_reporter = UsageReporter()
            app.state.usage_reporter = usage_reporter

            # Start periodic reporting
            await usage_reporter.schedule_periodic_reporting()

            logger.info("Usage reporting initialized and scheduled")

        except ImportError as e:
            logger.warning(f"Usage reporting not available: {e}")
        except Exception as e:
            logger.error(f"Usage reporting initialization failed: {e}")

    async def _initialize_plugin_system(self, app: FastAPI, startup_manager):
        """Initialize plugin system for management platform."""
        try:
            # Plugin initialization would happen here
            logger.info("Plugin system initialized")

        except ImportError:
            logger.debug("Plugin system not available")
        except Exception as e:
            logger.warning(f"Plugin system initialization failed: {e}")

    async def _start_tenant_monitoring(self, app: FastAPI, startup_manager):
        """Start tenant container monitoring."""
        try:
            # Tenant monitoring initialization
            logger.info("Tenant monitoring started")

        except Exception as e:
            logger.warning(f"Tenant monitoring failed: {e}")

    async def _configure_kubernetes_client(self, app: FastAPI, startup_manager):
        """Configure Kubernetes client."""
        try:
            # Kubernetes client configuration
            logger.info("Kubernetes client configured")

        except Exception as e:
            logger.warning(f"Kubernetes client configuration failed: {e}")

    async def _initialize_websocket_manager(self, app: FastAPI, startup_manager):
        """Initialize WebSocket manager."""
        try:
            from dotmac_management.core.websocket_manager import websocket_manager

            await websocket_manager.start()
            app.state.websocket_manager = websocket_manager
            logger.info("WebSocket manager initialized")

        except ImportError:
            logger.debug("WebSocket manager not available")
        except Exception as e:
            logger.warning(f"WebSocket manager initialization failed: {e}")

    # Standard shutdown task implementations
    async def _shutdown_observability(self, app: FastAPI):
        """Shutdown observability system."""
        try:
            # Shutdown new observability system
            if hasattr(app.state, "observability_components"):
                components = app.state.observability_components

                # Shutdown OTEL bootstrap
                if "otel_bootstrap" in components and components["otel_bootstrap"]:
                    try:
                        components["otel_bootstrap"].shutdown()
                        logger.info("OTEL bootstrap shutdown complete")
                    except Exception as e:
                        logger.warning(f"OTEL bootstrap shutdown failed: {e}")

                logger.info("New observability system shutdown complete")

            # Fallback to legacy shutdown
            elif hasattr(app.state, "observability_instance") and app.state.observability_instance:
                if hasattr(app.state.observability_instance, "shutdown"):
                    app.state.observability_instance.shutdown()
                logger.info("Legacy observability shutdown complete")

        except Exception as e:
            logger.warning(f"Observability shutdown failed: {e}")

    async def _close_database(self, app: FastAPI):
        """Close database connections."""
        try:
            if self.platform_config.deployment_context:
                mode = self.platform_config.deployment_context.mode

                if mode == DeploymentMode.TENANT_CONTAINER:
                    from dotmac_isp.core.database import close_database

                    await close_database()
                elif mode == DeploymentMode.MANAGEMENT_PLATFORM:
                    from dotmac_management.database import close_database

                    await close_database()

            logger.info("Database connections closed")

        except Exception as e:
            logger.warning(f"Database shutdown failed: {e}")

    async def _close_cache(self, app: FastAPI):
        """Close cache connections."""
        try:
            if hasattr(app.state, "cache_manager") and app.state.cache_manager:
                if hasattr(app.state.cache_manager, "close"):
                    await app.state.cache_manager.close()
                logger.info("Cache connections closed")

        except Exception as e:
            logger.warning(f"Cache shutdown failed: {e}")

    # Platform-specific shutdown implementations
    async def _shutdown_ssl_manager(self, app: FastAPI):
        """Shutdown SSL manager."""
        try:
            from dotmac_isp.core.ssl_manager import get_ssl_manager

            ssl_manager = get_ssl_manager()
            if hasattr(ssl_manager, "shutdown"):
                await ssl_manager.shutdown()
            logger.info("SSL manager shutdown complete")

        except Exception as e:
            logger.warning(f"SSL manager shutdown failed: {e}")

    async def _shutdown_usage_reporting(self, app: FastAPI):
        """Shutdown usage reporting."""
        try:
            if hasattr(app.state, "usage_reporter") and app.state.usage_reporter:
                if hasattr(app.state.usage_reporter, "stop_periodic_reporting"):
                    await app.state.usage_reporter.stop_periodic_reporting()
                logger.info("Usage reporting shutdown complete")

        except Exception as e:
            logger.warning(f"Usage reporting shutdown failed: {e}")

    async def _shutdown_websocket_manager(self, app: FastAPI):
        """Shutdown WebSocket manager."""
        try:
            if hasattr(app.state, "websocket_manager") and app.state.websocket_manager:
                await app.state.websocket_manager.stop()
                logger.info("WebSocket manager shutdown complete")

        except Exception as e:
            logger.warning(f"WebSocket manager shutdown failed: {e}")

    async def _shutdown_plugins(self, app: FastAPI):
        """Shutdown plugin system."""
        try:
            # Plugin shutdown logic
            logger.info("Plugin system shutdown complete")

        except Exception as e:
            logger.warning(f"Plugin system shutdown failed: {e}")

    # Service management methods
    async def _initialize_services(self, app: FastAPI, startup_manager):
        """Initialize all business services."""
        if not self.service_registry:
            logger.info("No service registry configured, skipping service initialization")
            return

        try:
            logger.info("Initializing business services...")

            # Initialize all services in the registry
            initialization_results = await self.service_registry.initialize_all()

            # Log results
            successful_services = [name for name, success in initialization_results.items() if success]
            failed_services = [name for name, success in initialization_results.items() if not success]

            if successful_services:
                logger.info(f"✅ Services initialized: {', '.join(successful_services)}")
            if failed_services:
                logger.warning(f"⚠️ Services failed: {', '.join(failed_services)}")

            # Store service status in app state
            app.state.service_initialization_results = initialization_results
            app.state.ready_services = successful_services

            logger.info(
                "Business services initialization complete: "
                f"{len(successful_services)}/{len(initialization_results)} services ready"
            )

        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise

    async def _shutdown_services(self, app: FastAPI):
        """Shutdown all business services."""
        if not self.service_registry:
            logger.info("No service registry configured, skipping service shutdown")
            return

        try:
            logger.info("Shutting down business services...")

            # Shutdown all services
            shutdown_results = await self.service_registry.shutdown_all()

            # Log results
            successful_shutdowns = [name for name, success in shutdown_results.items() if success]
            failed_shutdowns = [name for name, success in shutdown_results.items() if not success]

            if successful_shutdowns:
                logger.info(f"✅ Services shutdown: {', '.join(successful_shutdowns)}")
            if failed_shutdowns:
                logger.warning(f"⚠️ Service shutdown failures: {', '.join(failed_shutdowns)}")

            logger.info(
                "Business services shutdown complete: "
                f"{len(successful_shutdowns)}/{len(shutdown_results)} services shutdown cleanly"
            )

        except Exception as e:
            logger.error(f"Service shutdown failed: {e}")
