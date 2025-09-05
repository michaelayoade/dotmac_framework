"""
Type definitions and typing helpers for the tasks package.
"""

from collections.abc import Awaitable, Callable
from typing import Any, Optional, Protocol, Union

from typing_extensions import TypedDict


class OperationHandler(Protocol):
    """Protocol for operation handlers."""

    async def __call__(self, parameters: dict[str, Any]) -> Any:
        """Execute an operation with given parameters."""
        ...


class CompensationHandler(Protocol):
    """Protocol for compensation handlers."""

    async def __call__(self, parameters: dict[str, Any]) -> None:
        """Execute compensation with given parameters."""
        ...


class StepDefinition(TypedDict, total=False):
    """Type definition for saga step configuration."""

    step_id: str  # Optional, will be generated if not provided
    name: str  # Required
    operation: str  # Required
    parameters: dict[str, Any]  # Optional, defaults to {}
    compensation_operation: Optional[str]  # Optional
    compensation_parameters: dict[str, Any]  # Optional, defaults to {}
    max_retries: int  # Optional, defaults to 3


class SagaWorkflowDefinition(TypedDict, total=False):
    """Type definition for saga workflow configuration."""

    tenant_id: str  # Required
    workflow_type: str  # Required
    steps: list[StepDefinition]  # Required
    idempotency_key: Optional[str]  # Optional
    timeout_seconds: int  # Optional, uses manager default


class IdempotencyKeyData(TypedDict, total=False):
    """Type definition for idempotency key creation."""

    tenant_id: str  # Required
    user_id: Optional[str]  # Optional
    operation_type: str  # Required
    key: Optional[str]  # Optional, will be generated if not provided
    ttl: Optional[int]  # Optional, uses manager default
    parameters: dict[str, Any]  # Optional, for key generation


class OperationResult(TypedDict, total=False):
    """Type definition for operation results."""

    status: str  # Required: "success", "error", etc.
    data: Any  # Optional result data
    error: Optional[str]  # Optional error message
    metadata: dict[str, Any]  # Optional metadata


class HealthCheckResult(TypedDict, total=False):
    """Type definition for health check results."""

    status: str  # Required: "healthy", "unhealthy"
    backend: str  # Required: storage backend name
    metrics: dict[str, Any]  # Optional metrics data
    error: Optional[str]  # Optional error message


# Type aliases for common callback types
OperationCallback = Callable[[dict[str, Any]], Awaitable[Any]]
CompensationCallback = Callable[[dict[str, Any]], Awaitable[None]]
LifecycleCallback = Callable[[], Awaitable[None]]
MetricsCallback = Callable[..., None]

# Union types for flexible parameters
StepParameters = Union[dict[str, Any], None]
OperationParameters = Union[dict[str, Any], list[Any], str, int, float, bool, None]
StorageKey = Union[str, int]

# Generic types for storage operations
StorageValue = Union[dict[str, Any], str, int, float, bool, None]
StorageMapping = dict[str, StorageValue]

# Request/Response types for middleware
RequestMetadata = dict[str, Any]
ResponseData = dict[str, Any]


# Configuration types
class MiddlewareConfig(TypedDict, total=False):
    exempt_paths: Optional[list[str]]
    idempotency_header: str
    cache_hit_header: str
    idempotency_response_header: str


class StorageConfig(TypedDict, total=False):
    backend: str
    redis_url: Optional[str]
    prefix: Optional[str]
    max_connections: Optional[int]
    timeout: Optional[int]


class ManagerConfig(TypedDict, total=False):
    default_idempotency_ttl: int
    saga_timeout: int
    cleanup_interval: int
    enable_background_cleanup: bool


# Custom exceptions types
class TasksError(Exception):
    """Base exception for tasks package."""

    pass


class IdempotencyError(TasksError):
    """Idempotency-related error."""

    pass


class SagaError(TasksError):
    """Saga workflow-related error."""

    pass


class StorageError(TasksError):
    """Storage backend error."""

    pass


class OperationError(TasksError):
    """Operation execution error."""

    pass


class CompensationError(TasksError):
    """Compensation execution error."""

    pass


# Type guards and validation helpers


def is_valid_step_definition(obj: Any) -> bool:
    """Check if object is a valid step definition."""
    if not isinstance(obj, dict):
        return False

    required_fields = ["name", "operation"]
    return all(field in obj for field in required_fields)


def is_valid_saga_definition(obj: Any) -> bool:
    """Check if object is a valid saga workflow definition."""
    if not isinstance(obj, dict):
        return False

    required_fields = ["tenant_id", "workflow_type", "steps"]
    if not all(field in obj for field in required_fields):
        return False

    # Validate steps
    steps = obj.get("steps", [])
    if not isinstance(steps, list):
        return False

    return all(is_valid_step_definition(step) for step in steps)


def validate_operation_result(result: Any) -> OperationResult:
    """Validate and normalize operation result."""
    if result is None:
        return {"status": "success", "data": None}

    if isinstance(result, dict):
        # Ensure required fields
        if "status" not in result:
            result["status"] = "success"
        return result

    # Convert simple values to structured result
    return {
        "status": "success",
        "data": result,
    }


# Decorator types for handler registration

HandlerDecorator = Callable[[OperationCallback], OperationCallback]
CompensationDecorator = Callable[[CompensationCallback], CompensationCallback]

# Factory types for creating instances - using forward references
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import BackgroundOperationsManager
    from .storage.base import Storage

ManagerFactory = Callable[..., "BackgroundOperationsManager"]
StorageFactory = Callable[..., "Storage"]
