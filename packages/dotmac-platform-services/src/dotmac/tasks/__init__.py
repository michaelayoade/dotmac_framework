"""
DotMac Tasks - Background Operations and Workflow Management

Simple task management for background operations, sagas, and workflows.
This is a minimal implementation for backward compatibility.
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class OperationStatus(str, Enum):
    """Status of a background operation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SagaStepStatus(str, Enum):
    """Status of a saga step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


@dataclass
class IdempotencyKey:
    """Idempotency key for operations."""

    key: str
    operation_id: str
    created_at: datetime


@dataclass
class SagaStep:
    """A step in a saga workflow."""

    id: str
    name: str
    action: Callable
    compensate: Callable | None = None
    status: SagaStepStatus = SagaStepStatus.PENDING
    result: Any = None
    error: str | None = None


@dataclass
class SagaWorkflow:
    """Saga workflow definition."""

    id: str
    name: str
    steps: list[SagaStep]
    current_step: int = 0
    status: OperationStatus = OperationStatus.PENDING


@dataclass
class BackgroundOperation:
    """Background operation."""

    id: str
    name: str
    status: OperationStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any = None
    error: str | None = None


class MemoryStorage:
    """In-memory storage for operations."""

    def __init__(self) -> None:
        self.operations: dict[str, BackgroundOperation] = {}
        self.sagas: dict[str, SagaWorkflow] = {}
        self.idempotency_keys: dict[str, IdempotencyKey] = {}

    def get_operation(self, operation_id: str) -> BackgroundOperation | None:
        return self.operations.get(operation_id)

    def store_operation(self, operation: BackgroundOperation) -> None:
        self.operations[operation.id] = operation

    def get_saga(self, saga_id: str) -> SagaWorkflow | None:
        return self.sagas.get(saga_id)

    def store_saga(self, saga: SagaWorkflow) -> None:
        self.sagas[saga.id] = saga


class BackgroundOperationsManager:
    """Manager for background operations."""

    def __init__(self, storage: MemoryStorage | None = None) -> None:
        self.storage = storage or MemoryStorage()

    def start_operation(self, name: str, operation_id: str | None = None) -> BackgroundOperation:
        """Start a background operation."""
        operation = BackgroundOperation(
            id=operation_id or str(uuid.uuid4()),
            name=name,
            status=OperationStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        self.storage.store_operation(operation)
        logger.info(f"Started background operation: {operation.id}")
        return operation

    def complete_operation(self, operation_id: str, result: Any = None) -> None:
        """Complete a background operation."""
        operation = self.storage.get_operation(operation_id)
        if operation:
            operation.status = OperationStatus.COMPLETED
            operation.completed_at = datetime.utcnow()
            operation.result = result
            self.storage.store_operation(operation)

    def fail_operation(self, operation_id: str, error: str) -> None:
        """Fail a background operation."""
        operation = self.storage.get_operation(operation_id)
        if operation:
            operation.status = OperationStatus.FAILED
            operation.completed_at = datetime.utcnow()
            operation.error = error
            self.storage.store_operation(operation)


class BackgroundOperationsMiddleware:
    """FastAPI middleware for background operations."""

    def __init__(self, app, manager: BackgroundOperationsManager | None = None) -> None:
        self.app = app
        self.manager = manager or BackgroundOperationsManager()

    async def __call__(self, scope, receive, send):
        """Middleware call."""
        # Simple pass-through for now
        await self.app(scope, receive, send)


def add_background_operations_middleware(
    app, manager: BackgroundOperationsManager | None = None
):
    """Add background operations middleware to FastAPI app."""
    return BackgroundOperationsMiddleware(app, manager)


def get_idempotency_key(request_data: dict[str, Any]) -> str | None:
    """Get idempotency key from request data."""
    return request_data.get("idempotency_key")


def is_idempotent_request(request_data: dict[str, Any]) -> bool:
    """Check if request is idempotent."""
    return get_idempotency_key(request_data) is not None


def set_operation_result(operation_id: str, result: Any) -> None:
    """Set operation result."""
    # This would typically interact with a global manager
    logger.info(f"Setting result for operation {operation_id}: {result}")


# For backward compatibility, export everything
__all__ = [
    "OperationStatus",
    "SagaStepStatus",
    "IdempotencyKey",
    "SagaStep",
    "SagaWorkflow",
    "BackgroundOperation",
    "BackgroundOperationsManager",
    "BackgroundOperationsMiddleware",
    "MemoryStorage",
    "add_background_operations_middleware",
    "get_idempotency_key",
    "is_idempotent_request",
    "set_operation_result",
]
