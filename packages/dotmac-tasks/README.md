# dotmac.tasks

A standalone background operations package providing idempotent operations, saga workflows, and HTTP middleware for the DotMac platform.

## Features

- **Idempotent Operations**: Ensure operations run exactly once using deterministic keys
- **Saga Workflows**: Distributed transaction pattern with automatic compensation on failure
- **HTTP Middleware**: Automatic idempotency enforcement for FastAPI applications
- **Pluggable Storage**: Support for Redis (production) and in-memory (development) backends
- **Distributed Locking**: Prevent concurrent execution of critical operations
- **Comprehensive Testing**: Full test coverage for all components

## Installation

```bash
# Basic installation
pip install dotmac-tasks

# With Redis support (recommended for production)
pip install dotmac-tasks[redis]
```

## Quick Start

### Basic Usage

```python
from dotmac.tasks import BackgroundOperationsManager, MemoryStorage

# Create manager with in-memory storage
storage = MemoryStorage()
manager = BackgroundOperationsManager(storage=storage)
await manager.start()

# Create an idempotency key
key = await manager.create_idempotency_key(
    tenant_id="tenant1",
    user_id="user1", 
    operation_type="send_email",
    parameters={"to": "user@example.com", "subject": "Welcome"}
)

# Complete the operation
result = {"message_id": "123", "status": "sent"}
await manager.complete_idempotent_operation(key.key, result)
```

### With Redis Storage

```python
from dotmac.tasks import BackgroundOperationsManager
from dotmac.tasks.storage.redis import RedisStorage

# Create Redis storage backend
storage = RedisStorage(redis_url="redis://localhost:6379/0")
manager = BackgroundOperationsManager(storage=storage)
await manager.start()
```

### HTTP Middleware

```python
from fastapi import FastAPI, Request
from dotmac.tasks import add_background_operations_middleware, get_idempotency_key, set_operation_result

app = FastAPI()

# Add middleware (returns the manager instance)
manager = add_background_operations_middleware(app)

@app.post("/api/send-email")
async def send_email(request: Request, email_data: dict):
    idempotency_key = get_idempotency_key(request)
    
    # Your business logic here
    result = {"message_id": "123", "status": "sent"}
    
    # Cache result for future requests
    set_operation_result(request, result)
    
    return result
```

### Saga Workflows

```python
# Register operation handlers
async def send_email_handler(params):
    # Send email logic
    return {"message_id": "123", "status": "sent"}

async def create_user_handler(params):
    # Create user logic
    return {"user_id": "456", "status": "created"}

async def email_compensation_handler(params):
    # Cancel email logic
    pass

manager.register_operation_handler("send_email", send_email_handler)
manager.register_operation_handler("create_user", create_user_handler)
manager.register_compensation_handler("send_email", email_compensation_handler)

# Create saga workflow
steps = [
    {
        "name": "Create User Account",
        "operation": "create_user",
        "parameters": {"username": "testuser", "email": "test@example.com"},
        "compensation_operation": "send_email",
        "compensation_parameters": {"to": "test@example.com", "template": "cancelled"},
        "max_retries": 3
    },
    {
        "name": "Send Welcome Email", 
        "operation": "send_email",
        "parameters": {"to": "test@example.com", "template": "welcome"}
    }
]

saga = await manager.create_saga_workflow(
    tenant_id="tenant1",
    workflow_type="user_onboarding",
    steps=steps
)

# Execute saga
success = await manager.execute_saga_workflow(saga.saga_id)
```

## Configuration

### Environment Variables

- `REDIS_URL`: Redis connection URL (when using RedisStorage)
- `DOTMAC_TASKS_DEFAULT_TTL`: Default idempotency key TTL in seconds (default: 86400)
- `DOTMAC_TASKS_CLEANUP_INTERVAL`: Cleanup task interval in seconds (default: 300)

### Storage Backends

#### Memory Storage (Development)

```python
from dotmac.tasks.storage.memory import MemoryStorage

storage = MemoryStorage()
```

#### Redis Storage (Production)

```python
from dotmac.tasks.storage.redis import RedisStorage

storage = RedisStorage(
    redis_url="redis://localhost:6379/0",
    prefix="myapp_bgops",  # Key prefix
    socket_timeout=5.0,
    retry_on_timeout=True
)
```

### Middleware Configuration

```python
from dotmac.tasks import BackgroundOperationsMiddleware

# Custom configuration
app.add_middleware(
    BackgroundOperationsMiddleware,
    manager=manager,
    exempt_paths={"/health", "/metrics", "/docs"},
    idempotency_header="Custom-Idempotency-Key",
    cache_hit_header="Custom-Cache-Hit"
)
```

## API Reference

### BackgroundOperationsManager

The main orchestrator for background operations.

#### Methods

- `create_idempotency_key(tenant_id, user_id, operation_type, key=None, parameters=None, ttl=None)`: Create idempotency key
- `check_idempotency(key)`: Check if operation exists
- `complete_idempotent_operation(key, result, error=None)`: Complete operation
- `create_saga_workflow(tenant_id, workflow_type, steps, idempotency_key=None)`: Create saga
- `execute_saga_workflow(saga_id)`: Execute saga workflow
- `register_operation_handler(operation_type, handler)`: Register operation handler
- `register_compensation_handler(operation_type, handler)`: Register compensation handler

### Storage Interface

All storage backends implement the `StorageProtocol` interface:

- `set_idempotency(key, data, ttl)`: Store idempotency key
- `get_idempotency(key)`: Retrieve idempotency key
- `delete_idempotency(key)`: Delete idempotency key
- `set_saga(saga_id, data)`: Store saga workflow
- `get_saga(saga_id)`: Retrieve saga workflow
- `append_saga_history(saga_id, entry)`: Add saga history entry
- `acquire_lock(key, timeout_seconds)`: Acquire distributed lock
- `release_lock(key)`: Release distributed lock

### Models

#### IdempotencyKey
```python
@dataclass
class IdempotencyKey:
    key: str
    tenant_id: str
    user_id: Optional[str]
    operation_type: str
    created_at: datetime
    expires_at: datetime
    status: OperationStatus = OperationStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
```

#### SagaWorkflow
```python
@dataclass  
class SagaWorkflow:
    saga_id: str
    tenant_id: str
    workflow_type: str
    steps: List[SagaStep]
    status: OperationStatus = OperationStatus.PENDING
    current_step: int = 0
    created_at: datetime
    updated_at: datetime
    timeout_seconds: Optional[int] = None
    idempotency_key: Optional[str] = None
```

## Testing

Run tests with pytest:

```bash
# All tests
pytest

# Specific test categories
pytest -m "not redis"  # Skip Redis tests
pytest -m redis        # Only Redis tests (requires Redis server)

# With coverage
pytest --cov=dotmac.tasks --cov-report=html
```

Redis tests require a running Redis server and are marked with `@pytest.mark.redis`.

## Production Considerations

### Redis Configuration

For production deployments:

1. **Use Redis persistence**: Configure Redis with both AOF and RDB persistence
2. **Set appropriate timeouts**: Configure socket timeouts based on network conditions
3. **Monitor Redis health**: Use Redis INFO command for monitoring
4. **Key expiration**: Set appropriate TTL values for idempotency keys
5. **Memory management**: Monitor Redis memory usage and configure maxmemory policies

### Error Handling

The package provides robust error handling:

- Operations continue on storage backend failures when possible
- Distributed locks have automatic timeout and cleanup
- Saga compensation handles partial failures gracefully
- Middleware gracefully degrades on storage errors

### Observability

Hook into the metrics system for monitoring:

```python
from dotmac.tasks.metrics import register_metrics_hooks

def my_counter_hook(operation_type, tenant_id):
    # Your metrics logic
    pass

register_metrics_hooks(
    idempotency_key_created_hook=my_counter_hook,
    saga_step_completed_hook=my_counter_hook,
    # ... other hooks
)
```

### Scaling

- **Horizontal scaling**: Multiple application instances can safely share Redis backend
- **Tenant isolation**: Idempotency keys are isolated by tenant_id
- **Performance**: Redis operations are optimized with pipelining and proper data structures

## Migration from dotmac_shared

If migrating from the legacy `dotmac_shared.middleware.background_operations`:

```python
# Old (deprecated)
from dotmac_shared.middleware.background_operations import BackgroundOperationsManager

# New
from dotmac.tasks import BackgroundOperationsManager
```

The API is largely compatible, with these improvements:
- Enhanced Redis persistence with proper error handling
- Distributed locking for saga execution
- Better typing and error handling
- Comprehensive test coverage
- Pluggable storage backends

## Contributing

1. Install development dependencies: `poetry install --with dev`
2. Run tests: `pytest`
3. Run linting: `ruff check`
4. Run formatting: `ruff format`

## License

This project is licensed under the same terms as the DotMac platform.