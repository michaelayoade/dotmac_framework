"""In-memory storage implementations."""
from __future__ import annotations

import asyncio
import threading
import time
from contextlib import asynccontextmanager, contextmanager, suppress
from typing import TYPE_CHECKING, Any

from .base import SyncIdempotencyStore, SyncLockStore

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator


class MemoryIdempotencyStore:
    """Thread-safe in-memory idempotency store."""

    def __init__(self):
        self._data: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.RLock()

    async def get(self, key: str) -> Any | None:
        """Get a stored result by key."""
        with self._lock:
            if key not in self._data:
                return None

            value, expires_at = self._data[key]

            # Check expiration
            if expires_at is not None and time.time() > expires_at:
                del self._data[key]
                return None

            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a result with optional TTL in seconds."""
        with self._lock:
            expires_at = time.time() + ttl if ttl else None
            self._data[key] = (value, expires_at)

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the store."""
        result = await self.get(key)
        return result is not None

    async def delete(self, key: str) -> None:
        """Delete a key from the store."""
        with self._lock:
            self._data.pop(key, None)

    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        with self._lock:
            expired_keys = [
                key for key, (_, expires_at) in self._data.items()
                if expires_at is not None and current_time > expires_at
            ]
            for key in expired_keys:
                del self._data[key]


class MemoryLockStore:
    """Thread-safe in-memory lock store."""

    def __init__(self):
        self._locks: dict[str, tuple[asyncio.Lock, float]] = {}
        self._global_lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire_lock(
        self,
        key: str,
        timeout: float = 10.0,
        ttl: float = 60.0,
    ) -> AsyncIterator[bool]:
        """Acquire a distributed lock."""
        acquired = False

        try:
            # Clean up expired locks first
            await self._cleanup_expired()

            async with self._global_lock:
                if key in self._locks:
                    lock, _ = self._locks[key]
                else:
                    lock = asyncio.Lock()
                    expires_at = time.time() + ttl
                    self._locks[key] = (lock, expires_at)

            # Try to acquire the lock with timeout
            try:
                await asyncio.wait_for(lock.acquire(), timeout=timeout)
                acquired = True

                # Update expiration time
                async with self._global_lock:
                    if key in self._locks:
                        expires_at = time.time() + ttl
                        self._locks[key] = (lock, expires_at)

                yield True

            except asyncio.TimeoutError:
                yield False

        finally:
            if acquired:
                try:
                    async with self._global_lock:
                        if key in self._locks:
                            lock, _ = self._locks[key]
                            if lock.locked():
                                lock.release()
                except Exception:  # noqa: BLE001
                    pass  # Ignore errors during cleanup

    async def is_locked(self, key: str) -> bool:
        """Check if a lock is currently held."""
        await self._cleanup_expired()

        async with self._global_lock:
            if key not in self._locks:
                return False

            lock, _ = self._locks[key]
            return lock.locked()

    async def release_lock(self, key: str) -> None:
        """Force release a lock (use with caution)."""
        async with self._global_lock:
            if key in self._locks:
                lock, _ = self._locks[key]
                if lock.locked():
                    lock.release()

    async def _cleanup_expired(self) -> None:
        """Remove expired locks."""
        current_time = time.time()

        async with self._global_lock:
            expired_keys = [
                key for key, (_, expires_at) in self._locks.items()
                if current_time > expires_at
            ]

            for key in expired_keys:
                lock, _ = self._locks[key]
                if not lock.locked():  # Only remove if not actively held
                    del self._locks[key]


class SyncMemoryIdempotencyStore(SyncIdempotencyStore):
    """Synchronous version of memory idempotency store."""

    def __init__(self):
        self._data: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        """Get a stored result by key."""
        with self._lock:
            if key not in self._data:
                return None

            value, expires_at = self._data[key]

            # Check expiration
            if expires_at is not None and time.time() > expires_at:
                del self._data[key]
                return None

            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a result with optional TTL in seconds."""
        with self._lock:
            expires_at = time.time() + ttl if ttl else None
            self._data[key] = (value, expires_at)

    def exists(self, key: str) -> bool:
        """Check if a key exists in the store."""
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        """Delete a key from the store."""
        with self._lock:
            self._data.pop(key, None)


class SyncMemoryLockStore(SyncLockStore):
    """Synchronous version of memory lock store."""

    def __init__(self):
        self._locks: dict[str, tuple[threading.Lock, float]] = {}
        self._global_lock = threading.RLock()

    @contextmanager
    def acquire_lock(
        self,
        key: str,
        timeout: float = 10.0,
        ttl: float = 60.0,
    ) -> Iterator[bool]:
        """Acquire a distributed lock."""
        acquired = False

        try:
            # Clean up expired locks first
            self._cleanup_expired()

            with self._global_lock:
                if key in self._locks:
                    lock, _ = self._locks[key]
                else:
                    lock = threading.Lock()
                    expires_at = time.time() + ttl
                    self._locks[key] = (lock, expires_at)

            # Try to acquire the lock with timeout
            acquired = lock.acquire(timeout=timeout)

            if acquired:
                # Update expiration time
                with self._global_lock:
                    if key in self._locks:
                        expires_at = time.time() + ttl
                        self._locks[key] = (lock, expires_at)

                yield True
            else:
                yield False

        finally:
            if acquired:
                with suppress(Exception):
                    lock.release()

    def is_locked(self, key: str) -> bool:
        """Check if a lock is currently held."""
        self._cleanup_expired()

        with self._global_lock:
            if key not in self._locks:
                return False

            lock, _ = self._locks[key]
            return lock.locked()

    def release_lock(self, key: str) -> None:
        """Force release a lock (use with caution)."""
        with self._global_lock:
            if key in self._locks:
                lock, _ = self._locks[key]
                if lock.locked():
                    lock.release()

    def _cleanup_expired(self) -> None:
        """Remove expired locks."""
        current_time = time.time()

        with self._global_lock:
            expired_keys = [
                key for key, (_, expires_at) in self._locks.items()
                if current_time > expires_at
            ]

            for key in expired_keys:
                lock, _ = self._locks[key]
                if not lock.locked():  # Only remove if not actively held
                    del self._locks[key]
