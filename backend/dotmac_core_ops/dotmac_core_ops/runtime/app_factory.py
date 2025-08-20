"""
Application factory for creating the DotMac Core Operations FastAPI app.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import structlog

from .config import OpsConfig
from .middleware import setup_middleware
from .background_services import BackgroundServiceManager
from ..api import (
    workflows_router,
    tasks_router,
    automation_router,
    scheduler_router,
    state_machines_router,
    sagas_router,
    job_queues_router,
    health_router,
)
from ..sdks import (
    WorkflowSDK,
    TaskSDK,
    AutomationSDK,
    SchedulerSDK,
    StateMachineSDK,
    SagaSDK,
    JobQueueSDK,
)

logger = structlog.get_logger(__name__)


class OpsApplication:
    """Main operations application class."""

    def __init__(self, config: OpsConfig):
        self.config = config
        self.app: FastAPI = None
        self.background_manager: BackgroundServiceManager = None

        # SDK instances
        self.workflow_sdk: WorkflowSDK = None
        self.task_sdk: TaskSDK = None
        self.automation_sdk: AutomationSDK = None
        self.scheduler_sdk: SchedulerSDK = None
        self.state_machine_sdk: StateMachineSDK = None
        self.saga_sdk: SagaSDK = None
        self.job_queue_sdk: JobQueueSDK = None

    async def initialize_sdks(self):
        """Initialize all SDK instances."""
        logger.info("Initializing SDKs")

        # Initialize SDKs with configuration
        self.workflow_sdk = WorkflowSDK()
        self.task_sdk = TaskSDK()
        self.automation_sdk = AutomationSDK()
        self.scheduler_sdk = SchedulerSDK()
        self.state_machine_sdk = StateMachineSDK()
        self.saga_sdk = SagaSDK()
        self.job_queue_sdk = JobQueueSDK()

        # Start SDK background processes
        await self.workflow_sdk.start()
        await self.task_sdk.start()
        await self.automation_sdk.start()
        await self.scheduler_sdk.start()
        await self.state_machine_sdk.start()
        await self.saga_sdk.start()
        await self.job_queue_sdk.start()

        logger.info("SDKs initialized successfully")

    async def shutdown_sdks(self):
        """Shutdown all SDK instances."""
        logger.info("Shutting down SDKs")

        if self.workflow_sdk:
            await self.workflow_sdk.stop()
        if self.task_sdk:
            await self.task_sdk.stop()
        if self.automation_sdk:
            await self.automation_sdk.stop()
        if self.scheduler_sdk:
            await self.scheduler_sdk.stop()
        if self.state_machine_sdk:
            await self.state_machine_sdk.stop()
        if self.saga_sdk:
            await self.saga_sdk.stop()
        if self.job_queue_sdk:
            await self.job_queue_sdk.stop()

        logger.info("SDKs shutdown complete")

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Starting DotMac Operations application")

            # Initialize SDKs
            await self.initialize_sdks()

            # Start background services
            self.background_manager = BackgroundServiceManager(self.config)
            await self.background_manager.start()

            logger.info("Application startup complete")

            yield

            # Shutdown
            logger.info("Shutting down DotMac Operations application")

            # Stop background services
            if self.background_manager:
                await self.background_manager.stop()

            # Shutdown SDKs
            await self.shutdown_sdks()

            logger.info("Application shutdown complete")

        # Create FastAPI app
        self.app = FastAPI(
            title=self.config.app_name,
            version=self.config.app_version,
            description="DotMac Core Operations - Workflow orchestration, task management, and automation platform",
            lifespan=lifespan,
            debug=self.config.debug,
        )

        # Setup middleware
        setup_middleware(self.app, self.config)

        # Setup dependency injection
        self._setup_dependencies()

        # Setup exception handlers
        self._setup_exception_handlers()

        # Include routers
        self._include_routers()

        return self.app

    def _setup_dependencies(self):
        """Setup dependency injection for SDKs."""

        # Override SDK dependencies
        def get_workflow_sdk():
            return self.workflow_sdk

        def get_task_sdk():
            return self.task_sdk

        def get_automation_sdk():
            return self.automation_sdk

        def get_scheduler_sdk():
            return self.scheduler_sdk

        def get_state_machine_sdk():
            return self.state_machine_sdk

        def get_saga_sdk():
            return self.saga_sdk

        def get_job_queue_sdk():
            return self.job_queue_sdk

        # Store dependency overrides
        self.app.dependency_overrides.update({
            "get_workflow_sdk": get_workflow_sdk,
            "get_task_sdk": get_task_sdk,
            "get_automation_sdk": get_automation_sdk,
            "get_scheduler_sdk": get_scheduler_sdk,
            "get_state_machine_sdk": get_state_machine_sdk,
            "get_saga_sdk": get_saga_sdk,
            "get_job_queue_sdk": get_job_queue_sdk,
        })

    def _setup_exception_handlers(self):
        """Setup global exception handlers."""

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": exc.status_code,
                        "message": exc.detail,
                        "type": "http_error"
                    }
                }
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": 500,
                        "message": "Internal server error",
                        "type": "internal_error"
                    }
                }
            )

    def _include_routers(self):
        """Include API routers."""

        # Health check router (no prefix)
        self.app.include_router(health_router)

        # API routers with /api/v1 prefix
        api_prefix = "/api/v1"

        self.app.include_router(workflows_router, prefix=api_prefix)
        self.app.include_router(tasks_router, prefix=api_prefix)
        self.app.include_router(automation_router, prefix=api_prefix)
        self.app.include_router(scheduler_router, prefix=api_prefix)
        self.app.include_router(state_machines_router, prefix=api_prefix)
        self.app.include_router(sagas_router, prefix=api_prefix)
        self.app.include_router(job_queues_router, prefix=api_prefix)


def create_ops_app(config: OpsConfig = None) -> FastAPI:
    """
    Create a DotMac Operations FastAPI application.

    Args:
        config: Operations configuration. If None, loads from environment.

    Returns:
        Configured FastAPI application.
    """
    if config is None:
        config = OpsConfig.from_env()

    ops_app = OpsApplication(config)
    return ops_app.create_app()


def create_ops_app_from_env() -> FastAPI:
    """Create operations app with configuration from environment variables."""
    config = OpsConfig.from_env()
    return create_ops_app(config)
