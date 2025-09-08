# DotMac Tasks Utils

Task utilities for DotMac applications, providing idempotency, retry mechanisms, and distributed locking.

## Features

- **Idempotency**: Ensure operations run exactly once using configurable storage backends
- **Retry Logic**: Flexible retry mechanisms with exponential backoff and custom strategies
- **Distributed Locking**: Coordinate access to shared resources across multiple processes
- **Storage Backends**: In-memory and Redis-based storage implementations
- **Async/Sync Support**: Works with both synchronous and asynchronous code

## Installation

```bash
pip install dotmac-tasks-utils
```

For Redis support:
```bash
pip install dotmac-tasks-utils[redis]
```

## Quick Start

### Idempotency

```python
from dotmac_tasks_utils import with_idempotency
from dotmac_tasks_utils.storage import MemoryIdempotencyStore

store = MemoryIdempotencyStore()

@with_idempotency(store, key="user_signup", ttl=300)
async def signup_user(email: str):
    # This will only run once per email within 300 seconds
    return create_user_account(email)

result = await signup_user("user@example.com")
```

### Retry Logic

```python
from dotmac_tasks_utils import retry_async

@retry_async(max_attempts=3, backoff_factor=2.0)
async def flaky_api_call():
    response = await httpx.get("https://api.example.com/data")
    response.raise_for_status()
    return response.json()
```

## Storage Backends

### Memory Store (Default)
- Fast, in-process storage
- Good for single-instance applications
- Data is lost on restart

### Redis Store (Optional)
- Distributed storage across multiple instances
- Persistent storage
- Requires Redis server

```python
from dotmac_tasks_utils.storage import RedisIdempotencyStore

# Requires pip install dotmac-tasks-utils[redis]
store = RedisIdempotencyStore(redis_url="redis://localhost:6379")
```

## License

MIT