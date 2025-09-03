# dotmac.tasks Examples

This directory contains practical examples demonstrating how to use the dotmac.tasks package.

## Examples Overview

### 1. `basic_usage.py`
Demonstrates fundamental idempotency concepts:
- Creating and checking idempotency keys
- Completing operations with results and errors
- Deterministic key generation
- Custom key usage

**Run with:**
```bash
python basic_usage.py
```

### 2. `saga_example.py`
Shows saga workflow patterns:
- Multi-step distributed transactions
- Automatic compensation on failure
- Retry logic for flaky operations
- Operation and compensation handler registration

**Run with:**
```bash
python saga_example.py
```

### 3. `fastapi_integration.py`
Complete FastAPI application example:
- HTTP middleware integration
- Idempotent API endpoints
- Saga workflows in web context
- Operation status monitoring

**Run with:**
```bash
# Install FastAPI if not already installed
pip install fastapi uvicorn

# Run the server
python fastapi_integration.py
```

Then test with curl commands shown in the output.

## Key Concepts Demonstrated

### Idempotency
- **Deterministic Keys**: Same input parameters always generate the same key
- **Duplicate Detection**: Prevents duplicate execution of identical operations
- **Result Caching**: Completed operations return cached results instantly
- **TTL Management**: Keys expire automatically to prevent storage bloat

### Saga Workflows
- **Sequential Execution**: Steps execute in order with state persistence
- **Compensation Pattern**: Failed workflows trigger reverse-order compensation
- **Retry Logic**: Configurable retry attempts for transient failures
- **Error Isolation**: Individual step failures don't affect compensation of other steps

### HTTP Integration
- **Automatic Processing**: Middleware handles idempotency headers transparently
- **Status Codes**: 
  - 200: Cached result from completed operation
  - 202: Operation in progress
  - 400/500: Operation failed
- **Header Management**: Response includes idempotency and cache-hit headers

## Testing Different Scenarios

### Test Idempotency
```bash
# First request - executes operation
curl -X POST 'http://localhost:8000/api/send-email' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: test-123' \
  -d '{"to":"user@example.com","subject":"Test","body":"Hello!"}'

# Second request - returns cached result
curl -X POST 'http://localhost:8000/api/send-email' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: test-123' \
  -d '{"to":"user@example.com","subject":"Test","body":"Hello!"}'
```

### Test Saga Success
```bash
curl -X POST 'http://localhost:8000/api/register-user' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: user-success-123' \
  -d '{"username":"johndoe","email":"john@example.com","full_name":"John Doe","send_welcome_email":true}'
```

### Monitor Operation Status
```bash
# Check status by idempotency key
curl 'http://localhost:8000/api/status/test-123'

# Check storage statistics
curl 'http://localhost:8000/api/debug/storage-stats'
```

## Advanced Usage Patterns

### Custom Storage Backend
```python
# Use Redis for production
from dotmac.tasks.storage.redis import RedisStorage

storage = RedisStorage(
    redis_url="redis://localhost:6379/0",
    prefix="myapp",
    socket_timeout=5.0
)
manager = BackgroundOperationsManager(storage=storage)
```

### Error Handling
```python
try:
    saga = await manager.create_saga_workflow(tenant_id, workflow_type, steps)
    success = await manager.execute_saga_workflow(saga.saga_id)
    
    if not success:
        # Get error details from saga
        saga_data = await manager.storage.get_saga(saga.saga_id)
        # Handle failure...
        
except Exception as e:
    # Handle creation/execution errors
    logger.error(f"Saga workflow failed: {e}")
```

### Middleware Customization
```python
app.add_middleware(
    BackgroundOperationsMiddleware,
    manager=manager,
    exempt_paths={"/health", "/metrics", "/admin/*"},
    idempotency_header="X-Request-ID",
    cache_hit_header="X-From-Cache"
)
```

## Production Considerations

1. **Storage Backend**: Use Redis in production for persistence and scalability
2. **Error Handling**: Implement proper error handling and monitoring
3. **Timeouts**: Configure appropriate timeouts for operations and locks
4. **Monitoring**: Use metrics hooks to integrate with observability systems
5. **Security**: Validate tenant isolation and parameter sanitization

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**: Ensure Redis is running and accessible
2. **Lock Timeouts**: Increase timeout values for long-running operations  
3. **Memory Usage**: Monitor TTL settings and cleanup intervals
4. **Compensation Failures**: Ensure compensation handlers are idempotent

### Debugging Tips

1. **Enable Debug Logging**: Set log level to DEBUG for detailed information
2. **Check Storage Stats**: Use health check endpoints to monitor storage state
3. **Inspect Saga History**: Use saga history API to trace execution
4. **Test Compensation**: Manually trigger failures to verify compensation logic

For more information, see the main README.md and API documentation.