"""
Internal API for the tasks package.

This module provides internal interfaces and utilities that are
re-exported through the main __init__.py file.
"""

from typing import Any, Dict, List, Optional

from .manager import BackgroundOperationsManager
from .middleware import (
    BackgroundOperationsMiddleware,
    add_background_operations_middleware,
    get_idempotency_key,
    is_idempotent_request,
    set_operation_result,
)
from .models import (
    BackgroundOperation,
    IdempotencyKey,
    OperationStatus,
    SagaHistoryEntry,
    SagaStep,
    SagaStepStatus,
    SagaWorkflow,
)
from .storage import (
    MemoryStorage,
    RedisStorage,
    Storage,
    StorageConnectionError,
    StorageException,
    StorageTimeoutError,
)
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


class TasksAPI:
    """
    High-level API for the tasks package.
    
    This class provides a simplified interface for common operations
    and can be used as an alternative to using the manager directly.
    """

    def __init__(
        self,
        manager: Optional[BackgroundOperationsManager] = None,
        storage_config: Optional[StorageConfig] = None,
        manager_config: Optional[ManagerConfig] = None,
    ) -> None:
        """
        Initialize the Tasks API.
        
        Args:
            manager: BackgroundOperationsManager instance
            storage_config: Storage configuration
            manager_config: Manager configuration
        """
        if manager is None:
            # Create storage backend
            storage = self._create_storage(storage_config or {})
            
            # Create manager
            manager_kwargs = manager_config or {}
            manager = BackgroundOperationsManager(storage=storage, **manager_kwargs)
        
        self.manager = manager

    def _create_storage(self, config: StorageConfig) -> Storage:
        """Create storage backend from configuration."""
        backend = config.get('backend', 'memory')
        
        if backend == 'memory':
            return MemoryStorage()
        elif backend == 'redis':
            if RedisStorage is None:
                raise ImportError(
                    "Redis storage not available. Install with: pip install 'dotmac-tasks[redis]'"
                )
            
            redis_url = config.get('redis_url', 'redis://localhost:6379/0')
            prefix = config.get('prefix', 'bgops')
            max_connections = config.get('max_connections', 10)
            timeout = config.get('timeout', 5)
            
            return RedisStorage(
                redis_url=redis_url,
                prefix=prefix,
                max_connections=max_connections,
                socket_timeout=timeout,
                socket_connect_timeout=timeout,
            )
        else:
            raise ValueError(f"Unknown storage backend: {backend}")

    # High-level convenience methods

    async def start(self) -> None:
        """Start the tasks API and background services."""
        await self.manager.start()

    async def stop(self) -> None:
        """Stop the tasks API and background services."""
        await self.manager.stop()

    async def create_idempotent_operation(
        self,
        tenant_id: str,
        operation_type: str,
        parameters: Dict[str, Any],
        user_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """
        Create an idempotent operation.
        
        Args:
            tenant_id: Tenant identifier
            operation_type: Type of operation
            parameters: Operation parameters
            user_id: User identifier (optional)
            ttl: Time to live in seconds (optional)
            
        Returns:
            Generated idempotency key
        """
        key = self.manager.generate_idempotency_key(
            tenant_id, user_id, operation_type, parameters
        )
        
        await self.manager.create_idempotency_key(
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type=operation_type,
            key=key,
            ttl=ttl,
            parameters=parameters,
        )
        
        return key

    async def complete_operation(
        self,
        idempotency_key: str,
        result: Dict[str, Any],
        error: Optional[str] = None,
    ) -> bool:
        """
        Complete an idempotent operation.
        
        Args:
            idempotency_key: The idempotency key
            result: Operation result
            error: Error message if operation failed
            
        Returns:
            True if operation was completed successfully
        """
        return await self.manager.complete_idempotent_operation(
            idempotency_key, result, error
        )

    async def create_saga(
        self,
        tenant_id: str,
        workflow_type: str,
        steps: List[StepDefinition],
        idempotency_key: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> str:
        """
        Create and execute a saga workflow.
        
        Args:
            tenant_id: Tenant identifier
            workflow_type: Type of workflow
            steps: List of step definitions
            idempotency_key: Associated idempotency key (optional)
            timeout_seconds: Workflow timeout (optional)
            
        Returns:
            Saga ID
        """
        saga = await self.manager.create_saga_workflow(
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            steps=steps,
            idempotency_key=idempotency_key,
            timeout_seconds=timeout_seconds,
        )
        
        return saga.saga_id

    async def execute_saga(self, saga_id: str) -> bool:
        """
        Execute a saga workflow.
        
        Args:
            saga_id: The saga workflow ID
            
        Returns:
            True if saga completed successfully
        """
        return await self.manager.execute_saga_workflow(saga_id)

    async def get_saga_status(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """
        Get saga workflow status.
        
        Args:
            saga_id: The saga workflow ID
            
        Returns:
            Saga status dictionary or None if not found
        """
        saga_data = await self.manager.storage.get_saga(saga_id)
        if saga_data:
            saga = SagaWorkflow.from_dict(saga_data)
            return {
                "saga_id": saga.saga_id,
                "status": saga.status.value,
                "current_step": saga.current_step,
                "total_steps": len(saga.steps),
                "workflow_type": saga.workflow_type,
                "created_at": saga.created_at.isoformat() if saga.created_at else None,
                "updated_at": saga.updated_at.isoformat() if saga.updated_at else None,
            }
        return None

    async def get_saga_history(
        self, 
        saga_id: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get saga execution history.
        
        Args:
            saga_id: The saga workflow ID
            limit: Maximum number of entries to return
            
        Returns:
            List of history entries
        """
        return await self.manager.storage.get_saga_history(saga_id, limit)

    def register_handlers(
        self, 
        handlers: Dict[str, OperationCallback],
        compensations: Optional[Dict[str, CompensationCallback]] = None,
    ) -> None:
        """
        Register operation and compensation handlers.
        
        Args:
            handlers: Dictionary mapping operation types to handlers
            compensations: Dictionary mapping operation types to compensation handlers
        """
        for operation_type, handler in handlers.items():
            self.manager.register_operation_handler(operation_type, handler)
        
        if compensations:
            for operation_type, compensation in compensations.items():
                self.manager.register_compensation_handler(operation_type, compensation)

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the tasks system."""
        return await self.manager.health_check()

    async def get_tenant_operations(
        self, 
        tenant_id: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get background operations for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            limit: Maximum number of operations to return
            
        Returns:
            List of operation data
        """
        return await self.manager.storage.list_operations_by_tenant(
            tenant_id, limit
        )

    async def get_tenant_sagas(
        self, 
        tenant_id: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get saga workflows for a tenant.
        
        Args:
            tenant_id: Tenant identifier  
            limit: Maximum number of sagas to return
            
        Returns:
            List of saga data
        """
        return await self.manager.storage.list_sagas_by_tenant(tenant_id, limit)


# Factory functions

def create_tasks_api(
    storage_backend: str = "memory",
    **config_kwargs
) -> TasksAPI:
    """
    Create a TasksAPI instance with default configuration.
    
    Args:
        storage_backend: 'memory' or 'redis'
        **config_kwargs: Additional configuration parameters
        
    Returns:
        Configured TasksAPI instance
    """
    storage_config = {"backend": storage_backend, **config_kwargs}
    return TasksAPI(storage_config=storage_config)


def create_memory_tasks_api(**manager_kwargs) -> TasksAPI:
    """Create TasksAPI with in-memory storage."""
    return TasksAPI(
        storage_config={"backend": "memory"},
        manager_config=manager_kwargs,
    )


def create_redis_tasks_api(
    redis_url: str = "redis://localhost:6379/0",
    **kwargs
) -> TasksAPI:
    """
    Create TasksAPI with Redis storage.
    
    Args:
        redis_url: Redis connection URL
        **kwargs: Additional configuration parameters
        
    Returns:
        TasksAPI instance with Redis storage
    """
    storage_config = {
        "backend": "redis",
        "redis_url": redis_url,
        **kwargs
    }
    return TasksAPI(storage_config=storage_config)


# Decorator helpers for handler registration

def operation_handler(operation_type: str, api: TasksAPI):
    """
    Decorator for registering operation handlers.
    
    Args:
        operation_type: Type of operation
        api: TasksAPI instance
        
    Returns:
        Decorator function
    """
    def decorator(func: OperationCallback) -> OperationCallback:
        api.manager.register_operation_handler(operation_type, func)
        return func
    return decorator


def compensation_handler(operation_type: str, api: TasksAPI):
    """
    Decorator for registering compensation handlers.
    
    Args:
        operation_type: Type of operation
        api: TasksAPI instance
        
    Returns:
        Decorator function
    """
    def decorator(func: CompensationCallback) -> CompensationCallback:
        api.manager.register_compensation_handler(operation_type, func)
        return func
    return decorator