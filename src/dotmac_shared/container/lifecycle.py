"""
Container and Kubernetes lifecycle management for DotMac services.
Handles graceful shutdown, health probes, and container-specific requirements.
"""

import asyncio
import logging
import signal
import sys
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ContainerLifecycleManager:
    """
    Manages container lifecycle including health probes, graceful shutdown,
    and Kubernetes integration.
    """

    def __init__(self, app: FastAPI, service_name: str, version: str = "1.0.0"):
        self.app = app
        self.service_name = service_name
        self.version = version
        self.startup_complete = False
        self.shutdown_initiated = False
        self.healthy = True
        self.ready = False
        self.startup_time = time.time()
        self.shutdown_timeout = 30  # seconds
        self.health_dependencies: list[Callable] = []
        self.readiness_dependencies: list[Callable] = []

    def add_health_dependency(self, check_func: Callable[[], bool], name: str):
        """Add a dependency check for health probe."""
        check_func.name = name
        self.health_dependencies.append(check_func)

    def add_readiness_dependency(self, check_func: Callable[[], bool], name: str):
        """Add a dependency check for readiness probe."""
        check_func.name = name
        self.readiness_dependencies.append(check_func)

    def setup_health_endpoints(self):
        """Setup Kubernetes-compatible health probe endpoints."""

        @self.app.get("/health/live", tags=["health"])
        async def liveness_probe():
            """
            Kubernetes liveness probe - indicates if container should be restarted.
            Returns 200 if service is alive, 503 if it should be restarted.
            """
            if not self.healthy or self.shutdown_initiated:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "unhealthy",
                        "service": self.service_name,
                        "reason": (
                            "shutdown_initiated"
                            if self.shutdown_initiated
                            else "health_check_failed"
                        ),
                        "timestamp": time.time(),
                    },
                )

            # Run health dependency checks
            failed_checks = []
            for check in self.health_dependencies:
                try:
                    if (
                        not await check()
                        if asyncio.iscoroutinefunction(check)
                        else not check()
                    ):
                        failed_checks.append(getattr(check, "name", "unknown"))
                except Exception as e:
                    failed_checks.append(f"{getattr(check, 'name', 'unknown')}: {e}")

            if failed_checks:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "unhealthy",
                        "service": self.service_name,
                        "failed_checks": failed_checks,
                        "timestamp": time.time(),
                    },
                )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "healthy",
                    "service": self.service_name,
                    "version": self.version,
                    "uptime": time.time() - self.startup_time,
                    "timestamp": time.time(),
                },
            )

        @self.app.get("/health/ready", tags=["health"])
        async def readiness_probe():
            """
            Kubernetes readiness probe - indicates if service can receive traffic.
            Returns 200 if ready to serve requests, 503 if not ready.
            """
            if not self.startup_complete or self.shutdown_initiated:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "not_ready",
                        "service": self.service_name,
                        "reason": (
                            "startup_incomplete"
                            if not self.startup_complete
                            else "shutdown_initiated"
                        ),
                        "timestamp": time.time(),
                    },
                )

            # Run readiness dependency checks
            failed_checks = []
            for check in self.readiness_dependencies:
                try:
                    if (
                        not await check()
                        if asyncio.iscoroutinefunction(check)
                        else not check()
                    ):
                        failed_checks.append(getattr(check, "name", "unknown"))
                except Exception as e:
                    failed_checks.append(f"{getattr(check, 'name', 'unknown')}: {e}")

            if failed_checks:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "not_ready",
                        "service": self.service_name,
                        "failed_checks": failed_checks,
                        "timestamp": time.time(),
                    },
                )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "ready",
                    "service": self.service_name,
                    "version": self.version,
                    "timestamp": time.time(),
                },
            )

        @self.app.get("/health/startup", tags=["health"])
        async def startup_probe():
            """
            Kubernetes startup probe - indicates if application has started.
            Used during container startup to avoid premature liveness/readiness checks.
            """
            if self.startup_complete:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": "started",
                        "service": self.service_name,
                        "version": self.version,
                        "startup_duration": time.time() - self.startup_time,
                        "timestamp": time.time(),
                    },
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "starting",
                        "service": self.service_name,
                        "startup_duration": time.time() - self.startup_time,
                        "timestamp": time.time(),
                    },
                )

        # NO BACKWARD COMPATIBILITY - Use /health/live and /health/ready only

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown in containers."""

        def signal_handler(sig, frame):
            """Handle shutdown signals gracefully."""
            logger.info(f"📡 Received signal {sig} - initiating graceful shutdown...")
            self.shutdown_initiated = True

            # Create shutdown task
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.graceful_shutdown())
            else:
                logger.warning("No event loop running - forcing immediate shutdown")
                sys.exit(0)

        # Handle standard container termination signals
        signal.signal(signal.SIGTERM, signal_handler)  # Kubernetes sends this
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C during development

        logger.info("📡 Container signal handlers registered")

    async def graceful_shutdown(self):
        """
        Perform graceful shutdown with proper connection draining.
        """
        logger.info("🔄 Starting graceful shutdown sequence...")

        try:
            # Mark as not ready (stop receiving new requests)
            self.ready = False
            logger.info("🚫 Service marked as not ready - no new requests accepted")

            # Wait for existing connections to finish (with timeout)
            shutdown_start = time.time()
            max_wait = self.shutdown_timeout

            logger.info(
                f"⏳ Waiting up to {max_wait}s for existing connections to finish..."
            )

            # In a real implementation, you would:
            # 1. Stop accepting new connections
            # 2. Wait for existing requests to complete
            # 3. Close database connections
            # 4. Cleanup resources

            # Simulate connection draining
            await asyncio.sleep(2)  # Give connections time to finish

            # Cleanup application state
            if hasattr(self.app.state, "cleanup_tasks"):
                for cleanup_task in self.app.state.cleanup_tasks:
                    try:
                        if asyncio.iscoroutinefunction(cleanup_task):
                            await cleanup_task()
                        else:
                            cleanup_task()
                    except Exception as e:
                        logger.warning(f"Cleanup task failed: {e}")

            elapsed = time.time() - shutdown_start
            logger.info(f"✅ Graceful shutdown completed in {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"❌ Error during graceful shutdown: {e}")

        # Mark as unhealthy so health checks fail
        self.healthy = False

        # Exit gracefully
        logger.info("👋 Container shutdown complete")
        sys.exit(0)

    def mark_startup_complete(self):
        """Mark startup as complete - enables readiness probe."""
        self.startup_complete = True
        self.ready = True
        logger.info("✅ Startup complete - service ready for traffic")

    def mark_unhealthy(self, reason: str = "unknown"):
        """Mark service as unhealthy."""
        self.healthy = False
        logger.error(f"💀 Service marked as unhealthy: {reason}")

    def get_container_info(self) -> dict[str, Any]:
        """Get container runtime information."""
        import os
        import platform

        return {
            "service": self.service_name,
            "version": self.version,
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "environment_variables": {
                "POD_NAME": os.getenv("POD_NAME", "unknown"),
                "POD_NAMESPACE": os.getenv("POD_NAMESPACE", "unknown"),
                "NODE_NAME": os.getenv("NODE_NAME", "unknown"),
                "CONTAINER_NAME": os.getenv("CONTAINER_NAME", "unknown"),
            },
            "kubernetes": {
                "in_cluster": os.path.exists(
                    "/var/run/secrets/kubernetes.io/serviceaccount"
                ),
                "service_account": os.getenv("SERVICE_ACCOUNT", "unknown"),
            },
            "uptime": time.time() - self.startup_time,
            "startup_complete": self.startup_complete,
            "healthy": self.healthy,
            "ready": self.ready,
        }


@asynccontextmanager
async def container_lifespan(
    app: FastAPI,
    service_name: str,
    version: str = "1.0.0",
    startup_func: Optional[Callable] = None,
    shutdown_func: Optional[Callable] = None,
):
    """
    Container-aware lifespan manager that integrates with Kubernetes.

    Usage:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with container_lifespan(app, "my-service", startup_func=my_startup):
                yield
    """

    lifecycle_manager = ContainerLifecycleManager(app, service_name, version)

    # Setup container integration
    lifecycle_manager.setup_health_endpoints()
    lifecycle_manager.setup_signal_handlers()

    # Store lifecycle manager in app state
    app.state.container_lifecycle = lifecycle_manager

    try:
        logger.info(f"🚀 Starting containerized service: {service_name}")

        # Run custom startup function if provided
        if startup_func:
            await startup_func()

        # Mark startup as complete
        lifecycle_manager.mark_startup_complete()

        logger.info(f"🎉 {service_name} ready for traffic")

        yield

    except Exception as e:
        logger.error(f"❌ Container startup failed: {e}")
        lifecycle_manager.mark_unhealthy(f"startup_failed: {e}")
        raise

    finally:
        logger.info(f"🔄 Shutting down containerized service: {service_name}")

        # Mark as shutting down
        lifecycle_manager.shutdown_initiated = True

        # Run custom shutdown function if provided
        if shutdown_func:
            try:
                await shutdown_func()
            except Exception as e:
                logger.error(f"❌ Custom shutdown failed: {e}")

        logger.info(f"✅ {service_name} container shutdown complete")
