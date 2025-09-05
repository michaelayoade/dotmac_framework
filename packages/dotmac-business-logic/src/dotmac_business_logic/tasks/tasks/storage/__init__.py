"""
Storage backends for background operations.
"""

from .base import (
    LockAcquisitionError,
    Storage,
    StorageConnectionError,
    StorageException,
    StorageTimeoutError,
)
from .memory import MemoryStorage

# Redis storage is optional - only import if available
try:
    from .redis import RedisStorage
except ImportError:
    # Redis not available
    RedisStorage = None

__all__ = [
    "Storage",
    "StorageException",
    "StorageConnectionError",
    "StorageTimeoutError",
    "LockAcquisitionError",
    "MemoryStorage",
    "RedisStorage",
]
