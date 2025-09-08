"""
DotMac Tasks Utils - Task utilities for idempotency, retries, and distributed locking.

This package provides utilities for building reliable task processing:
- Idempotency to ensure operations run exactly once
- Retry mechanisms with configurable backoff strategies
- Distributed locking for coordination across processes
- Multiple storage backends (memory, Redis)
- Observability with structured logging and metrics
- Configuration management and health monitoring
"""

__version__ = "1.0.0"

from .config import ConfigManager, DotmacTasksConfig
from .idempotency import with_idempotency
from .retry import retry_async, retry_sync

__all__ = [
    "ConfigManager",
    "DotmacTasksConfig",
    "retry_async",
    "retry_sync",
    "with_idempotency",
]

# Optional Redis imports (available when redis extra is installed)
try:
    from .storage.redis import RedisIdempotencyStore, RedisLockStore
    REDIS_AVAILABLE = True
    __all__ += ["REDIS_AVAILABLE", "RedisIdempotencyStore", "RedisLockStore"]
except ImportError:
    REDIS_AVAILABLE = False
    RedisIdempotencyStore = RedisLockStore = None
