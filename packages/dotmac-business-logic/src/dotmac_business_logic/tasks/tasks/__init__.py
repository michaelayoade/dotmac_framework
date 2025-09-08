"""
DotMac Tasks - Background Operations, Idempotency, and Saga Workflows

A comprehensive package for managing background operations with:
- Idempotent operations with durable storage
- Saga workflows with step retries and compensations
- HTTP middleware for automatic idempotency enforcement
- Pluggable storage backends (memory, Redis)
- Observability and metrics integration

Usage:
    from dotmac.tasks import BackgroundOperationsManager, add_background_operations_middleware

    # Create manager
    manager = BackgroundOperationsManager()
    await manager.start()

    # Add middleware to FastAPI app
    add_background_operations_middleware(app, manager)

    # Register operation handlers
    @manager.register_operation_handler("send_email")
    async def send_email_handler(params):
        # Send email logic
        return {"message_id": "123", "status": "sent"}
"""

__version__ = "1.0.0"

# Core classes
# High-level API
from .api import (
    TasksAPI,
    compensation_handler,
    create_memory_tasks_api,
    create_redis_tasks_api,
    create_tasks_api,
    operation_handler,
)
from .manager import BackgroundOperationsManager

# Metrics and observability
from .metrics import (
    configure_metrics_hooks,
    get_metrics_hooks,
    record_idempotency_hit,
    record_idempotency_miss,
    record_operation_completed,
    record_operation_enqueued,
    record_saga_created,
    record_saga_status_change,
    setup_dotmac_observability_integration,
)
from .middleware import (
    BackgroundOperationsMiddleware,
    add_background_operations_middleware,
    get_idempotency_key,
    is_idempotent_request,
    set_operation_result,
)

# Models and enums
from .models import (
    BackgroundOperation,
    IdempotencyKey,
    OperationStatus,
    SagaHistoryEntry,
    SagaStep,
    SagaStepStatus,
    SagaWorkflow,
)

# Storage backends
from .storage import (
    MemoryStorage,
    Storage,
    StorageConnectionError,
    StorageException,
    StorageTimeoutError,
)

# Type definitions
from .types import (
    CompensationCallback,
    ManagerConfig,
    MiddlewareConfig,
    OperationCallback,
    OperationResult,
    SagaWorkflowDefinition,
    StepDefinition,
    StorageConfig,
)

# Optional Redis storage (only if available)
try:
    from .storage import RedisStorage
except ImportError:
    RedisStorage = None

__all__ = [
    # Core classes
    "BackgroundOperationsManager",
    "BackgroundOperationsMiddleware",
    "add_background_operations_middleware",
    # Middleware helpers
    "get_idempotency_key",
    "is_idempotent_request",
    "set_operation_result",
    # Models and enums
    "BackgroundOperation",
    "IdempotencyKey",
    "OperationStatus",
    "SagaHistoryEntry",
    "SagaStep",
    "SagaStepStatus",
    "SagaWorkflow",
    # Storage
    "Storage",
    "MemoryStorage",
    "RedisStorage",
    "StorageException",
    "StorageConnectionError",
    "StorageTimeoutError",
    # High-level API
    "TasksAPI",
    "create_tasks_api",
    "create_memory_tasks_api",
    "create_redis_tasks_api",
    "operation_handler",
    "compensation_handler",
    # Type definitions
    "OperationCallback",
    "CompensationCallback",
    "StepDefinition",
    "SagaWorkflowDefinition",
    "OperationResult",
    "ManagerConfig",
    "MiddlewareConfig",
    "StorageConfig",
    # Metrics
    "configure_metrics_hooks",
    "get_metrics_hooks",
    "record_idempotency_hit",
    "record_idempotency_miss",
    "record_operation_completed",
    "record_operation_enqueued",
    "record_saga_created",
    "record_saga_status_change",
    "setup_dotmac_observability_integration",
]
