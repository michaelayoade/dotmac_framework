"""
Coordination utilities for dotmac-database.

Provides distributed locking and coordination primitives
for multi-instance applications using Redis and PostgreSQL.
"""

from .locks import (
    RedisLock,
    PgAdvisoryLock,
    LockError,
    LockTimeout,
    LockNotAcquired,
)

__all__ = [
    "RedisLock",
    "PgAdvisoryLock", 
    "LockError",
    "LockTimeout",
    "LockNotAcquired",
]